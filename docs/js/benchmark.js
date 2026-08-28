/* HTR benchmark results page: aggregates and per-page tables from
 * data/benchmark/summary.json (exported from evaluation/benchmark).
 * Every figure on the page comes from that file at runtime; nothing is
 * hard-coded here. The image-text synopsis lives in the viewer, not here. */

import { escapeHTML, escapeAttr } from './utils.js';

const $ = (sel) => document.querySelector(sel);

/* Short human description per frozen prompt iteration. An iteration the map
 * does not know keeps its bare id, so a future it03 needs no code change. */
const ITERATION_NOTE = {
  it01: "baseline system prompt",
  it02: "shared core prompt + genre module",
};

/* Reference page ids encode the Transkribus document and its page number,
 * which is exactly what the viewer takes as query parameters. */
const PAGE_ID = /^inv_(\d+)_p(\d+)$/;

function mean(xs) { return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null; }

function pct(x) { return x != null ? (x * 100).toFixed(1) + "%" : "–"; }

function two(x) { return x != null ? x.toFixed(2) : "–"; }

function range(xs) {
  if (!xs || !xs.length) return "–";
  const lo = Math.min(...xs), hi = Math.max(...xs);
  return lo === hi ? String(lo) : `${lo}–${hi}`;
}

function pageLink(id) {
  const m = PAGE_ID.exec(id);
  if (!m) return escapeHTML(id);
  return `<a href="viewer.html?doc=${encodeURIComponent(m[1])}&amp;page=${encodeURIComponent(m[2])}"` +
    ` title="Open this page in the viewer">${escapeHTML(id)}</a>`;
}

function folioLink(p) {
  const label = escapeHTML(p.folio);
  if (!p.iiif) return label;
  return `<a href="${escapeAttr(p.iiif)}" target="_blank" rel="noopener"` +
    ` title="Facsimile image, opens in a new tab">${label}</a>`;
}

/* A page counts towards the CER aggregate only while its error rate stays
 * below 100%; above that the reference is too short for the measure to mean
 * anything (see the legend above the reference table). */
const validRef = (p) => p.gt_lines && Object.values(p.iterations).every((e) => (e.cer_fair?.mean ?? 0) < 1);

/* Repeated runs of a page that produced at most one line each carry no
 * agreement information; the same test decides aggregate and row flag. */
const validCons = (e) => e && e.consistency_numbers != null && e.lines.some((n) => n > 1);

function kRange(entries) {
  const ks = entries.map((e) => e.k).filter((k) => k != null);
  return ks.length ? range(ks) : "–";
}

/* A lead smaller than this is not called better anywhere on the page: one CER
 * point, or 0.05 of agreement, both well inside the scatter of repeated runs
 * at temperature 0. The rule is stated for the reader in the details block. */
const MIN_LEAD = { cer: 0.01, consistency: 0.05 };

const MEASURES = [
  { key: "cer_fair", label: "CER fair", scope: "reference pages", dir: -1, lead: MIN_LEAD.cer, fmt: pct },
  { key: "cer_strict", label: "CER strict", scope: "reference pages", dir: -1, lead: MIN_LEAD.cer, fmt: pct },
  { key: "words", label: "Word consistency", scope: "account book", dir: 1, lead: MIN_LEAD.consistency, fmt: two },
  { key: "numbers", label: "Number consistency", scope: "account book", dir: 1, lead: MIN_LEAD.consistency, fmt: two },
];

/* Index of the best value across iterations, -1 when nothing is comparable or
 * the lead over the runner-up stays inside the noise. Direction is per
 * measure: CER down, agreement up. */
function bestIndex(values, dir, lead = 0) {
  if (!dir) return -1;
  const defined = values.filter((v) => v != null).sort((a, b) => (dir < 0 ? a - b : b - a));
  if (defined.length < 2) return -1;
  const [target, runnerUp] = defined;
  if (Math.abs(runnerUp - target) <= lead) return -1;
  return values.findIndex((v) => v === target);
}

function renderAggregate(summary, its, excluded) {
  const pages = Object.values(summary.pages);
  const refs = pages.filter(validRef);
  const stats = its.map((it) => {
    const cons = pages.filter((p) => p.source === "raitbuch2" && validCons(p.iterations[it]));
    return {
      it,
      cer_fair: mean(refs.map((p) => p.iterations[it]?.cer_fair?.mean).filter((x) => x != null)),
      cer_strict: mean(refs.map((p) => p.iterations[it]?.cer_strict?.mean).filter((x) => x != null)),
      words: mean(cons.map((p) => p.iterations[it].consistency_words)),
      numbers: mean(cons.map((p) => p.iterations[it].consistency_numbers)),
    };
  });
  const best = Object.fromEntries(
    MEASURES.map((m) => [m.key, bestIndex(stats.map((s) => s[m.key]), m.dir, m.lead)])
  );

  $("#agg-cards").innerHTML = stats.map((s, i) => {
    const rows = MEASURES.map((m) => {
      const marker = best[m.key] === i
        ? ` <span class="badge text-bg-light border fw-normal">better</span>`
        : "";
      return `<div class="d-flex justify-content-between align-items-baseline gap-3">
        <dt class="fw-normal text-body-secondary">${escapeHTML(m.label)}
          <span class="text-body-tertiary">· ${escapeHTML(m.scope)}</span></dt>
        <dd class="mb-0 text-end text-nowrap"><span class="tnum${best[m.key] === i ? " fw-bold" : ""}">${m.fmt(s[m.key])}</span>${marker}</dd>
      </div>`;
    }).join("");
    return `<div class="col-12 col-md-6">
      <div class="border rounded p-3 h-100">
        <div class="fw-bold">${escapeHTML(s.it)}</div>
        <div class="small text-body-secondary mb-3">${escapeHTML(ITERATION_NOTE[s.it] || "frozen prompt iteration")}</div>
        <dl class="small mb-0 d-grid gap-2">${rows}</dl>
      </div>
    </div>`;
  }).join("");

  renderExamples(summary, its);
  $("#agg-note").innerHTML = excluded.length
    ? `Excluded: ${excluded.map(pageLink).join(", ")} – reference nearly empty, see the table note.`
    : "";
}

/* One concrete anchor for the aggregate: which reference page the model reads
 * best and which it reads worst, averaged over the iterations. */
function renderExamples(summary, its) {
  const scored = Object.entries(summary.pages)
    .filter(([, p]) => validRef(p))
    .map(([id, p]) => ({
      id, p, cer: mean(its.map((it) => p.iterations[it]?.cer_fair?.mean).filter((x) => x != null)),
    }))
    .filter((e) => e.cer != null)
    .sort((a, b) => a.cer - b.cer);
  if (scored.length < 2) { $("#agg-examples").innerHTML = ""; return; }
  const lo = scored[0], hi = scored[scored.length - 1];
  $("#agg-examples").innerHTML =
    `Read best: ${pageLink(lo.id)} <span class="text-body-secondary">(${escapeHTML(lo.p.folio)}, ` +
    `${pct(lo.cer)} CER fair across iterations)</span>. ` +
    `Hardest: ${pageLink(hi.id)} <span class="text-body-secondary">(${escapeHTML(hi.p.folio)}, ${pct(hi.cer)})</span>.`;
}

/* The metric tables repeat the same measures once per prompt iteration. Two
 * header rows group them: iteration above, measure below, so a reader compares
 * iterations side by side instead of decoding a flat run of column labels. */
function metricHead(fixed, its, measures) {
  const top = fixed.map((f) => `<th scope="col" rowspan="2">${escapeHTML(f)}</th>`).join("") +
    its.map((it) => {
      const note = ITERATION_NOTE[it] ? ` (${ITERATION_NOTE[it]})` : "";
      return `<th scope="colgroup" colspan="${measures.length}" class="col-group group-start"` +
        ` title="${escapeAttr(`Prompt iteration ${it}${note}`)}">${escapeHTML(it)}</th>`;
    }).join("");
  const sub = its.map(() =>
    measures.map((m, i) => `<th scope="col"${i === 0 ? ' class="group-start"' : ""}` +
      ` title="${escapeAttr(m.title)}">${escapeHTML(m.label)}</th>`).join("")
  ).join("");
  return `<thead class="table-light"><tr>${top}</tr><tr>${sub}</tr></thead>`;
}

/* Cells of one row across all iterations. Values are collected first so the
 * better iteration can be marked per measure; a flagged row is not compared,
 * because its numbers do not measure what the column header says. */
function metricCells(its, measures, cellFor, compare) {
  const cells = its.map((it) => measures.map((m) => cellFor(it, m)));
  const best = measures.map((m, i) =>
    compare ? bestIndex(cells.map((c) => c[i].value), m.dir, m.lead) : -1);
  return its.map((_, ii) => measures.map((m, i) => {
    const c = cells[ii][i];
    const cls = `num${i === 0 ? " group-start" : ""}${best[i] === ii ? " fw-bold" : ""}`;
    // The tooltip is a mouse affordance, so the same text is also read out
    const attr = c.hint ? ` title="${escapeAttr(c.hint)}"` : "";
    const spoken = c.hint ? `<span class="visually-hidden">, ${escapeHTML(c.hint)}</span>` : "";
    return `<td class="${cls}"${attr}>${c.text}${spoken}</td>`;
  }).join("")).join("");
}

function renderRefTable(summary, its) {
  const rows = Object.entries(summary.pages).filter(([, p]) => p.gt_lines);
  const measures = [
    {
      key: "cer_fair", label: "CER fair", dir: -1, lead: MIN_LEAD.cer,
      title: "Character error rate against the human reference transcription from the Inventaria edition, after the documented normalization profile. Lower is better.",
    },
    {
      key: "cer_strict", label: "CER strict", dir: -1, lead: MIN_LEAD.cer,
      title: "Character error rate against the same Inventaria reference on exact characters, without normalization. Lower is better.",
    },
  ];
  const head = metricHead(["Page", "Folio"], its, measures);
  const body = rows.map(([id, p]) => {
    const bad = Object.values(p.iterations).some((e) => (e.cer_fair?.mean ?? 0) >= 1);
    // The warning row tint alone carries no meaning for non-sighted readers
    const flag = bad
      ? ` <span class="flag" title="Reference nearly empty, error rate not meaningful, awaiting adjudication">⚠<span class="visually-hidden"> flagged, reference nearly empty</span></span>`
      : "";
    return `<tr${bad ? ' class="table-warning"' : ""}>` +
      `<th scope="row">${pageLink(id)}${flag}</th>` +
      `<td class="small">${folioLink(p)}</td>` +
      metricCells(its, measures, (it, m) => {
        const v = p.iterations[it]?.[m.key];
        if (!v) return { value: null, text: "–", hint: "" };
        return {
          value: v.mean,
          text: pct(v.mean),
          hint: `range over ${p.iterations[it].k} runs: ${pct(v.min)} to ${pct(v.max)}`,
        };
      }, !bad) +
      `</tr>`;
  }).join("");
  $("#ref-table").innerHTML =
    `<caption class="visually-hidden">Character error rate per reference page and prompt iteration, mean over the repeated runs</caption>` +
    head + `<tbody>${body}</tbody>`;
  // The Inventaria attribution belongs on the same line as the scope of the
  // table, because it says whose transcription the error rate is measured on.
  $("#ref-note").innerHTML =
    `${rows.length} pages · ` +
    `${kRange(rows.flatMap(([, p]) => its.map((it) => p.iterations[it]).filter(Boolean)))} runs per page and iteration · ` +
    `human references from the Inventaria project (Univ. Salzburg / Innsbruck), published at ` +
    `<a href="https://www.inventaria.at/" target="_blank" rel="noopener">inventaria.at</a> · ` +
    `spread in the cell tooltip`;
}

function renderConsTable(summary, its) {
  const rows = Object.entries(summary.pages).filter(([, p]) => !p.gt_lines);
  const measures = [
    {
      key: "consistency_words", label: "words", dir: 1, lead: MIN_LEAD.consistency,
      title: "Position-wise agreement of word tokens between the repeated runs, 0 to 1. Higher is more stable, which is not the same as correct.",
    },
    {
      key: "consistency_numbers", label: "numbers", dir: 1, lead: MIN_LEAD.consistency,
      title: "The same agreement restricted to number and currency tokens, 0 to 1. Higher is more stable.",
    },
    {
      key: "lines", label: "lines", dir: 0,
      title: "Line count of the individual runs. A spread signals unstable segmentation of the page.",
    },
  ];
  const head = metricHead(["Page", "Folio", "Phenomena"], its, measures);
  const body = rows.map(([id, p]) => {
    const bad = Object.values(p.iterations).every((e) => !e.lines.some((n) => n > 1));
    const flag = bad
      ? ` <span class="flag" title="Every run returned at most one line, agreement not meaningful">⚠<span class="visually-hidden"> flagged, at most one line per run</span></span>`
      : "";
    return `<tr${bad ? ' class="table-warning"' : ""}>` +
      `<th scope="row">${pageLink(id)}${flag}</th>` +
      `<td class="small">${folioLink(p)}</td>` +
      `<td class="small text-body-secondary">${escapeHTML(p.phenomena.join(", "))}</td>` +
      metricCells(its, measures, (it, m) => {
        const e = p.iterations[it];
        if (!e) return { value: null, text: "–", hint: "" };
        if (m.key === "lines") {
          return { value: null, text: range(e.lines), hint: `line count per run: ${e.lines.join(", ")}` };
        }
        const v = e[m.key];
        return { value: v ?? null, text: two(v), hint: `over ${e.k} runs` };
      }, !bad) + `</tr>`;
  }).join("");
  $("#cons-table").innerHTML =
    `<caption class="visually-hidden">Agreement between the repeated runs per page and prompt iteration</caption>` +
    head + `<tbody>${body}</tbody>`;
  $("#cons-note").textContent =
    `${rows.length} pages chosen for one phenomenon each, without a human reference · ` +
    `${kRange(rows.flatMap(([, p]) => its.map((it) => p.iterations[it]).filter(Boolean)))} runs per page and iteration · ` +
    `agreement between those runs, higher is more stable.`;
}

function renderIntro(summary, its) {
  const pages = Object.values(summary.pages);
  const refs = pages.filter((p) => p.gt_lines).length;
  const entries = pages.flatMap((p) => its.map((it) => p.iterations[it]).filter(Boolean));
  $("#intro-facts").textContent =
    `Model ${summary.model} · ${its.length} prompt iterations (${its.join(", ")}) · ` +
    `${pages.length} pages, ${refs} of them with a human reference transcription · ` +
    `${kRange(entries)} runs per page and iteration · data as of ${summary.generated.slice(0, 10)}.`;
}

async function init() {
  try {
    const res = await fetch("data/benchmark/summary.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const summary = await res.json();
    const its = [...new Set(Object.values(summary.pages).flatMap((p) => Object.keys(p.iterations)))].sort();
    const excluded = Object.entries(summary.pages)
      .filter(([, p]) => p.gt_lines && !validRef(p))
      .map(([id]) => id);
    renderIntro(summary, its);
    renderAggregate(summary, its, excluded);
    renderRefTable(summary, its);
    renderConsTable(summary, its);
  } catch (err) {
    const msg = document.createElement("p");
    msg.className = "col-12 mb-0 text-body-secondary";
    msg.textContent = `Benchmark results could not be loaded: ${err.message}`;
    $("#agg-cards").replaceChildren(msg);
  }
}

init();
