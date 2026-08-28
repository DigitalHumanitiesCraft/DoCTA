/* Image-text synopsis viewer for the versioned HTR prompt benchmark.
 * Data: summary.json (metrics, run filenames, GT lines, IIIF URL) plus the
 * individual run files under runs/, fetched lazily and cached.
 * Serve from the repo root (e.g. python -m http.server 8742) so the vendored
 * OpenSeadragon build under docs/lib/ resolves. */

const state = { summary: null, ids: [], id: null, tab: null, repeat: {} };
const runCache = new Map();
let osd = null;

const $ = (sel) => document.querySelector(sel);

/* Escapes text and attribute values alike, so a quote in the data cannot break
 * out of an attribute. */
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* One alternation over all uncertain words, applied in a single pass, so
 * inserted markup is never searched again. Longest first, or a longer word is
 * cut short by a shorter one contained in it. */
function markUncertain(text, words) {
  const html = esc(text);
  const keys = [...new Set((words || []).filter(Boolean).map((w) => esc(w)))]
    .sort((a, b) => b.length - a.length);
  if (!keys.length) return html;
  const re = new RegExp(keys.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "g");
  return html.replace(re, (m) => `<mark class="uncertain">${m}</mark>`);
}

function page() { return state.summary.pages[state.id]; }

/* ---------- transcript rendering ---------- */

function renderLine(line) {
  let html = markUncertain(line.text || "", line.uncertain);
  if (line.amount && (line.amount.numeral || line.amount.unit)) {
    const a = line.amount;
    html += ` <span class="amount-tag">[${esc([a.multiplier, a.numeral, a.unit].filter(Boolean).join(" "))}]</span>`;
  }
  const kind = (line.kind || "entry").toLowerCase();
  return `<li class="kind-${esc(kind)}">${html}</li>`;
}

function renderRun(rec) {
  const prov = `<div class="provenance">${esc(rec.model)} · ${rec.duration_s}s · ` +
    `Prompt ${esc(rec.iteration)} (${esc(rec.prompt_hash)}) · ${esc(rec.timestamp)}</div>`;
  let html = prov;
  for (const pg of rec.parsed.pages || []) {
    html += `<div class="page-label">${esc(pg.label || "Seite")}</div>`;
    if (!(pg.lines || []).length) { html += `<p class="empty-note">leer gemeldet</p>`; continue; }
    html += `<ol>${pg.lines.map(renderLine).join("")}</ol>`;
  }
  if (rec.parsed.notes) html += `<div class="notes">${esc(rec.parsed.notes)}</div>`;
  return html;
}

function renderGT() {
  const gt = page().gt_lines || [];
  return `<div class="provenance">Transkribus-Referenz (Status DONE)</div>` +
    `<ol>${gt.map((t) => renderLine({ text: t })).join("")}</ol>`;
}

async function fetchRun(name) {
  if (!runCache.has(name)) {
    const r = await fetch(`runs/${name}`);
    runCache.set(name, r.ok ? await r.json() : null);
  }
  return runCache.get(name);
}

function runName(it) {
  const runs = page().iterations[it]?.runs || [];
  const idx = Math.min(state.repeat[it] || 0, runs.length - 1);
  return runs[idx] ?? null;
}

/* ---------- metrics table: one row per iteration ---------- */

function fmtCer(m) {
  if (!m) return "";
  return `${(m.mean * 100).toFixed(1)}% <span class="meta">(${(m.min * 100).toFixed(1)}–${(m.max * 100).toFixed(1)})</span>`;
}

function renderMetrics() {
  const p = page();
  const its = Object.keys(p.iterations);
  const hasGT = !!p.gt_lines;
  const head = `<tr><th>Iteration</th><th>k</th><th>Zeilen</th><th>uncertain</th>` +
    `<th>Konsistenz W&ouml;rter</th><th>Konsistenz Zahlen</th>` +
    (hasGT ? `<th>CER fair</th><th>CER strikt</th>` : ``) + `</tr>`;
  const bestFair = hasGT
    ? Math.min(...its.map((it) => p.iterations[it].cer_fair?.mean ?? Infinity)) : null;
  const rows = its.map((it) => {
    const e = p.iterations[it];
    const fairCls = e.cer_fair
      ? (e.cer_fair.mean === bestFair ? "best" : (e.cer_fair.mean >= 1 ? "cer-bad" : "")) : "";
    return `<tr><th>${esc(it)}</th><td>${e.k}</td>` +
      `<td>${e.lines.join(" / ")}</td><td>${e.uncertain.join(" / ")}</td>` +
      `<td>${e.consistency_words ?? ""}</td><td>${e.consistency_numbers ?? ""}</td>` +
      (hasGT ? `<td class="${fairCls}">${fmtCer(e.cer_fair)}</td><td>${fmtCer(e.cer_strict)}</td>` : ``) +
      `</tr>`;
  }).join("");
  $("#metrics").innerHTML = `<table>${head}${rows}</table>`;
}

/* ---------- tabs and repeat selector ---------- */

function tabList() {
  const p = page();
  const list = [];
  if (p.gt_lines) list.push({ key: "__gt", label: "Referenz", cls: "gt-tab" });
  for (const it of Object.keys(p.iterations)) list.push({ key: it, label: it, cls: "" });
  const its = Object.keys(p.iterations);
  if (its.length >= 2) list.push({ key: "__cmp", label: `${its[0]} vs ${its[1]}`, cls: "" });
  if (p.gt_lines) list.push({ key: "__gtcmp", label: "Referenz vs Lauf", cls: "" });
  return list;
}

function renderRepeatBar() {
  const el = $("#repeats");
  const its = Object.keys(page().iterations);
  let show = [];
  if (page().iterations[state.tab]) show = [state.tab];
  else if (state.tab === "__cmp") show = its.slice(0, 2);
  else if (state.tab === "__gtcmp") show = its.slice(-1);
  if (!show.length) { el.innerHTML = ""; el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = show.map((it) => {
    const runs = page().iterations[it].runs || [];
    return `<span class="label">${esc(it)}:</span>` + runs.map((name, i) => {
      const on = (state.repeat[it] || 0) === i;
      const m = name.match(/__r(\d+)\.json$/);
      return `<button type="button" data-it="${esc(it)}" data-i="${i}" aria-pressed="${on}">r${m ? m[1] : i + 1}</button>`;
    }).join("");
  }).join(" ");
  el.querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => { state.repeat[b.dataset.it] = +b.dataset.i; selectTab(state.tab); }));
}

async function selectTab(key) {
  state.tab = key;
  document.querySelectorAll("[role=tab]").forEach((el) => {
    const on = el.dataset.key === key;
    el.setAttribute("aria-selected", on ? "true" : "false");
    el.tabIndex = on ? 0 : -1;
  });
  renderRepeatBar();
  const p = page();
  const its = Object.keys(p.iterations);
  const box = $("#transcript");
  const runHtml = async (it) => {
    const name = runName(it);
    const rec = name && await fetchRun(name);
    return rec ? renderRun(rec) : `<p class="empty-note">kein Lauf vorhanden</p>`;
  };
  if (key === "__gt") box.innerHTML = renderGT();
  else if (key === "__cmp" && its.length >= 2) {
    box.innerHTML = `<div class="compare"><div><h3>${esc(its[0])}</h3>${await runHtml(its[0])}</div>` +
      `<div><h3>${esc(its[1])}</h3>${await runHtml(its[1])}</div></div>`;
  } else if (key === "__gtcmp") {
    const it = its[its.length - 1];
    box.innerHTML = `<div class="compare"><div><h3>Referenz</h3>${renderGT()}</div>` +
      `<div><h3>${esc(it)}</h3>${await runHtml(it)}</div></div>`;
  } else box.innerHTML = await runHtml(key);
}

function renderTabs() {
  const el = $("#tabs");
  el.innerHTML = "";
  for (const t of tabList()) {
    const b = document.createElement("button");
    b.type = "button";
    b.setAttribute("role", "tab");
    b.className = t.cls;
    b.dataset.key = t.key;
    b.textContent = t.label;
    b.addEventListener("click", () => selectTab(t.key));
    el.appendChild(b);
  }
}

/* ---------- page selection ---------- */

function selectItem(id) {
  state.id = id;
  state.repeat = {};
  $("#item-select").value = id;
  const p = page();
  $("#page-meta").textContent = `${p.folio} · ${p.source} · ${p.phenomena.join(", ")}`;
  // Local cache first (runner downloads under images/, gitignored); IIIF as fallback.
  osd.open({ type: "image", url: `images/${id}.jpg` });
  osd.addOnceHandler("open-failed", () => osd.open({ type: "image", url: p.iiif, crossOriginPolicy: false }));
  renderMetrics();
  renderTabs();
  selectTab(p.gt_lines ? "__gtcmp" : Object.keys(p.iterations)[0]);
}

function step(delta) {
  const i = (state.ids.indexOf(state.id) + delta + state.ids.length) % state.ids.length;
  selectItem(state.ids[i]);
}

async function init() {
  try {
    const res = await fetch("summary.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.summary = await res.json();
  } catch (err) {
    $("#metrics").textContent = `summary.json konnte nicht geladen werden: ${err.message}`;
    return;
  }
  state.ids = Object.keys(state.summary.pages);
  $("#generated").textContent = `Stand ${state.summary.generated} · ${state.summary.model}`;
  const sel = $("#item-select");
  for (const id of state.ids) {
    const p = state.summary.pages[id];
    const o = document.createElement("option");
    o.value = id;
    o.textContent = `${id} (${p.folio})${p.gt_lines ? " · Ref" : ""}`;
    sel.appendChild(o);
  }
  sel.addEventListener("change", () => selectItem(sel.value));
  $("#prev").addEventListener("click", () => step(-1));
  $("#next").addEventListener("click", () => step(1));
  $("#tabs").addEventListener("keydown", (e) => {
    const all = [...document.querySelectorAll("[role=tab]")];
    const i = all.findIndex((x) => x.dataset.key === state.tab);
    let j = null;
    if (e.key === "ArrowRight") j = (i + 1) % all.length;
    if (e.key === "ArrowLeft") j = (i - 1 + all.length) % all.length;
    if (e.key === "Home") j = 0;
    if (e.key === "End") j = all.length - 1;
    if (j !== null) { e.preventDefault(); all[j].focus(); selectTab(all[j].dataset.key); }
  });
  osd = OpenSeadragon({
    id: "osd",
    showNavigationControl: false, // own buttons; OSD button images are not vendored
    visibilityRatio: 1,
    minZoomLevel: 0.5,
    maxZoomPixelRatio: 2.5,
    gestureSettingsMouse: { clickToZoom: false, scrollToZoom: true },
  });
  $("#zoom-in").addEventListener("click", () => { osd.viewport.zoomBy(1.3); osd.viewport.applyConstraints(); });
  $("#zoom-out").addEventListener("click", () => { osd.viewport.zoomBy(1 / 1.3); osd.viewport.applyConstraints(); });
  $("#zoom-fit").addEventListener("click", () => osd.viewport.goHome());
  selectItem(state.ids[0]);
}

init();
