/* HTR benchmark page: aggregate view plus image-text synopsis.
 * Data: data/benchmark/summary.json and the run files under data/benchmark/runs/,
 * exported from experiments/benchmark. Facsimiles load from Transkribus IIIF. */

const state = { summary: null, ids: [], id: null, tab: null, repeat: {} };
const runCache = new Map();
let osd = null;

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function page() { return state.summary.pages[state.id]; }

/* ---------- aggregate cards ---------- */

function mean(xs) { return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null; }

function renderAggregate() {
  const pages = Object.values(state.summary.pages);
  const its = [...new Set(pages.flatMap((p) => Object.keys(p.iterations)))].sort();
  const excluded = Object.entries(state.summary.pages)
    .filter(([, p]) => p.gt_lines && Object.values(p.iterations).some((e) => (e.cer_fair?.mean ?? 0) >= 1))
    .map(([id]) => id);
  const validRef = (p) => p.gt_lines && Object.values(p.iterations).every((e) => (e.cer_fair?.mean ?? 0) < 1);
  const cards = its.map((it) => {
    const cer = mean(pages.filter(validRef).map((p) => p.iterations[it]?.cer_fair?.mean).filter((x) => x != null));
    const rb = pages.filter((p) => p.source === "raitbuch2" && p.iterations[it]?.consistency_numbers != null
      && p.iterations[it].lines.some((n) => n > 1));
    const nums = mean(rb.map((p) => p.iterations[it].consistency_numbers));
    const words = mean(rb.map((p) => p.iterations[it].consistency_words));
    return `<div class="col-12 col-md-6">
      <div class="border rounded p-2">
        <div class="fw-bold mb-1">${esc(it)}</div>
        <div class="small">CER fair, Referenzseiten: <strong>${cer != null ? (cer * 100).toFixed(1) + "%" : "–"}</strong>
          &nbsp;·&nbsp; Zahlen-Konsistenz Raitbuch: <strong>${nums != null ? nums.toFixed(2) : "–"}</strong>
          &nbsp;·&nbsp; Wort-Konsistenz: <strong>${words != null ? words.toFixed(2) : "–"}</strong></div>
      </div>
    </div>`;
  }).join("");
  $("#agg-cards").innerHTML = cards;
  $("#agg-note").textContent = excluded.length
    ? `Ohne ${excluded.join(", ")}: Referenz fast leer, zur Adjudikation vorgemerkt.` : "";
}

/* ---------- transcript rendering ---------- */

function renderLine(line) {
  let html = esc(line.text || "");
  for (const w of line.uncertain || []) {
    if (!w) continue;
    const escaped = esc(w).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    html = html.replace(new RegExp(escaped, "g"), `<mark class="uncertain">${esc(w)}</mark>`);
  }
  if (line.amount && (line.amount.numeral || line.amount.unit)) {
    const a = line.amount;
    html += ` <span class="amount-tag">[${esc([a.multiplier, a.numeral, a.unit].filter(Boolean).join(" "))}]</span>`;
  }
  const kind = (line.kind || "entry").toLowerCase();
  return `<li class="kind-${esc(kind)}">${html}</li>`;
}

function renderRun(rec) {
  let html = `<div class="provenance">${esc(rec.model)} · ${rec.duration_s}s · ` +
    `Prompt ${esc(rec.iteration)} (${esc(rec.prompt_hash)})</div>`;
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
    const r = await fetch(`data/benchmark/runs/${name}`);
    runCache.set(name, r.ok ? await r.json() : null);
  }
  return runCache.get(name);
}

function runName(it) {
  const runs = page().iterations[it]?.runs || [];
  const idx = Math.min(state.repeat[it] || 0, runs.length - 1);
  return runs[idx] ?? null;
}

/* ---------- per-page metrics ---------- */

function fmtCer(m) {
  if (!m) return "";
  return `${(m.mean * 100).toFixed(1)}% <span class="text-body-secondary">(${(m.min * 100).toFixed(1)}–${(m.max * 100).toFixed(1)})</span>`;
}

function renderMetrics() {
  const p = page();
  const its = Object.keys(p.iterations);
  const hasGT = !!p.gt_lines;
  const head = `<tr><th>Iteration</th><th>k</th><th>Zeilen</th><th>uncertain</th>` +
    `<th>Konsistenz Wörter</th><th>Konsistenz Zahlen</th>` +
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

/* ---------- tabs and repeats ---------- */

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
  const its = Object.keys(page().iterations);
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
  osd.open({ type: "image", url: p.iiif, crossOriginPolicy: false });
  renderMetrics();
  renderTabs();
  selectTab(p.gt_lines ? "__gtcmp" : Object.keys(p.iterations)[0]);
}

function step(delta) {
  const i = (state.ids.indexOf(state.id) + delta + state.ids.length) % state.ids.length;
  selectItem(state.ids[i]);
}

async function init() {
  state.summary = await (await fetch("data/benchmark/summary.json")).json();
  state.ids = Object.keys(state.summary.pages);
  renderAggregate();
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
