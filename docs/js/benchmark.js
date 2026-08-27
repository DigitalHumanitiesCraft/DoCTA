/* HTR benchmark results page: aggregates and per-page tables from
 * data/benchmark/summary.json (exported from experiments/benchmark).
 * The image-text synopsis lives in the viewer, not here. */

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function mean(xs) { return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null; }

function pct(x) { return x != null ? (x * 100).toFixed(1) + "%" : "–"; }

function fmtCer(m) {
  if (!m) return "–";
  return `${(m.mean * 100).toFixed(1)}% <span class="text-body-secondary">(${(m.min * 100).toFixed(1)}–${(m.max * 100).toFixed(1)})</span>`;
}

function range(xs) {
  if (!xs || !xs.length) return "–";
  const lo = Math.min(...xs), hi = Math.max(...xs);
  return lo === hi ? String(lo) : `${lo}–${hi}`;
}

function renderAggregate(summary, excluded) {
  const pages = Object.values(summary.pages);
  const its = [...new Set(pages.flatMap((p) => Object.keys(p.iterations)))].sort();
  const validRef = (p) => p.gt_lines && Object.values(p.iterations).every((e) => (e.cer_fair?.mean ?? 0) < 1);
  $("#agg-cards").innerHTML = its.map((it) => {
    const cer = mean(pages.filter(validRef).map((p) => p.iterations[it]?.cer_fair?.mean).filter((x) => x != null));
    const rb = pages.filter((p) => p.source === "raitbuch2" && p.iterations[it]?.consistency_numbers != null
      && p.iterations[it].lines.some((n) => n > 1));
    const nums = mean(rb.map((p) => p.iterations[it].consistency_numbers));
    const words = mean(rb.map((p) => p.iterations[it].consistency_words));
    return `<div class="col-12 col-md-6">
      <div class="border rounded p-2">
        <div class="fw-bold mb-1">${esc(it)}</div>
        <div class="small">CER fair, reference pages: <strong>${pct(cer)}</strong>
          &nbsp;·&nbsp; number consistency (account book): <strong>${nums != null ? nums.toFixed(2) : "–"}</strong>
          &nbsp;·&nbsp; word consistency: <strong>${words != null ? words.toFixed(2) : "–"}</strong></div>
      </div>
    </div>`;
  }).join("");
  $("#agg-note").textContent = (excluded.length
    ? `Excluding ${excluded.join(", ")}: reference nearly empty, flagged for adjudication. ` : "")
    + `Model ${summary.model}, as of ${summary.generated}.`;
}

function renderRefTable(summary, its) {
  const rows = Object.entries(summary.pages).filter(([, p]) => p.gt_lines);
  const head = `<thead class="table-light"><tr><th>Page</th><th>Folio</th>` +
    its.map((it) => `<th>CER fair ${esc(it)}</th>`).join("") +
    its.map((it) => `<th>CER strict ${esc(it)}</th>`).join("") + `</tr></thead>`;
  const body = rows.map(([id, p]) => {
    const bad = Object.values(p.iterations).some((e) => (e.cer_fair?.mean ?? 0) >= 1);
    return `<tr${bad ? ' class="table-warning"' : ""}><td class="font-monospace small">${esc(id)}</td>` +
      `<td class="small">${esc(p.folio)}</td>` +
      its.map((it) => `<td>${fmtCer(p.iterations[it]?.cer_fair)}</td>`).join("") +
      its.map((it) => `<td>${fmtCer(p.iterations[it]?.cer_strict)}</td>`).join("") + `</tr>`;
  }).join("");
  $("#ref-table").innerHTML = head + `<tbody>${body}</tbody>`;
}

function renderConsTable(summary, its) {
  const rows = Object.entries(summary.pages).filter(([, p]) => !p.gt_lines);
  const head = `<thead class="table-light"><tr><th>Page</th><th>Folio</th><th>Phenomena</th>` +
    its.map((it) => `<th>words ${esc(it)}</th>`).join("") +
    its.map((it) => `<th>numbers ${esc(it)}</th>`).join("") +
    its.map((it) => `<th>lines ${esc(it)}</th>`).join("") + `</tr></thead>`;
  const body = rows.map(([id, p]) => {
    return `<tr><td class="font-monospace small">${esc(id)}</td>` +
      `<td class="small">${esc(p.folio)}</td>` +
      `<td class="small text-body-secondary">${esc(p.phenomena.join(", "))}</td>` +
      its.map((it) => `<td>${p.iterations[it]?.consistency_words ?? "–"}</td>`).join("") +
      its.map((it) => `<td>${p.iterations[it]?.consistency_numbers ?? "–"}</td>`).join("") +
      its.map((it) => `<td class="small">${range(p.iterations[it]?.lines)}</td>`).join("") + `</tr>`;
  }).join("");
  $("#cons-table").innerHTML = head + `<tbody>${body}</tbody>`;
}

async function init() {
  const summary = await (await fetch("data/benchmark/summary.json")).json();
  const its = [...new Set(Object.values(summary.pages).flatMap((p) => Object.keys(p.iterations)))].sort();
  const excluded = Object.entries(summary.pages)
    .filter(([, p]) => p.gt_lines && Object.values(p.iterations).some((e) => (e.cer_fair?.mean ?? 0) >= 1))
    .map(([id]) => id);
  renderAggregate(summary, excluded);
  renderRefTable(summary, its);
  renderConsTable(summary, its);
}

init();
