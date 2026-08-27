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
        <div class="small">CER fair, reference pages: <strong class="tnum">${pct(cer)}</strong>
          &nbsp;·&nbsp; number consistency (account book): <strong class="tnum">${nums != null ? nums.toFixed(2) : "–"}</strong>
          &nbsp;·&nbsp; word consistency: <strong class="tnum">${words != null ? words.toFixed(2) : "–"}</strong></div>
      </div>
    </div>`;
  }).join("");
  $("#agg-note").textContent = (excluded.length
    ? `Excluding ${excluded.join(", ")}: reference nearly empty, flagged for adjudication. ` : "")
    + `Model ${summary.model}, as of ${summary.generated}.`;
}

/* The metric tables repeat the same measures once per prompt iteration. Two
 * header rows group them: iteration above, measure below, so a reader compares
 * iterations side by side instead of decoding a flat run of column labels. */
function metricHead(fixed, its, measures) {
  const top = fixed.map((f) => `<th scope="col" rowspan="2">${esc(f)}</th>`).join("") +
    its.map((it) => `<th scope="colgroup" colspan="${measures.length}" class="col-group group-start">${esc(it)}</th>`).join("");
  const sub = its.map(() =>
    measures.map((m, i) => `<th scope="col"${i === 0 ? ' class="group-start"' : ""}>${esc(m)}</th>`).join("")
  ).join("");
  return `<thead class="table-light"><tr>${top}</tr><tr>${sub}</tr></thead>`;
}

function metricCells(its, cellsFor) {
  return its.map((it) =>
    cellsFor(it).map((v, i) => `<td class="num${i === 0 ? " group-start" : ""}">${v}</td>`).join("")
  ).join("");
}

function renderRefTable(summary, its) {
  const rows = Object.entries(summary.pages).filter(([, p]) => p.gt_lines);
  const head = metricHead(["Page", "Folio"], its, ["CER fair", "CER strict"]);
  const body = rows.map(([id, p]) => {
    const bad = Object.values(p.iterations).some((e) => (e.cer_fair?.mean ?? 0) >= 1);
    // The warning row tint alone carries no meaning for non-sighted readers
    const flag = bad ? ` <span class="flag" title="Reference nearly empty, flagged for adjudication">⚠<span class="visually-hidden"> flagged for adjudication</span></span>` : "";
    return `<tr${bad ? ' class="table-warning"' : ""}>` +
      `<th scope="row">${esc(id)}${flag}</th>` +
      `<td class="small">${esc(p.folio)}</td>` +
      metricCells(its, (it) => [fmtCer(p.iterations[it]?.cer_fair), fmtCer(p.iterations[it]?.cer_strict)]) +
      `</tr>`;
  }).join("");
  $("#ref-table").innerHTML =
    `<caption class="visually-hidden">Character error rate per reference page and prompt iteration</caption>` +
    head + `<tbody>${body}</tbody>`;
}

function renderConsTable(summary, its) {
  const rows = Object.entries(summary.pages).filter(([, p]) => !p.gt_lines);
  const head = metricHead(["Page", "Folio", "Phenomena"], its, ["words", "numbers", "lines"]);
  const body = rows.map(([id, p]) => {
    return `<tr><th scope="row">${esc(id)}</th>` +
      `<td class="small">${esc(p.folio)}</td>` +
      `<td class="small text-body-secondary">${esc(p.phenomena.join(", "))}</td>` +
      metricCells(its, (it) => [
        p.iterations[it]?.consistency_words ?? "–",
        p.iterations[it]?.consistency_numbers ?? "–",
        range(p.iterations[it]?.lines),
      ]) + `</tr>`;
  }).join("");
  $("#cons-table").innerHTML =
    `<caption class="visually-hidden">Agreement between repeated runs per page and prompt iteration</caption>` +
    head + `<tbody>${body}</tbody>`;
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
