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

/* Inventory page ids encode the Transkribus document and its page number, which
 * is exactly what the viewer takes as query parameters. A page id of another set
 * (the account book) matches nothing here and stays plain text. */
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

/* A page carrying a reference at all, by the class the summary states rather
 * than by the presence of a text field. */
const isReference = (p) => p.reference_class === "transkribus-done";

/* The exclusion reads a property of the reference text. summary.json marks a
 * reference too short to carry an error rate as `reference_degenerate`, so a
 * page is never dropped for the value it happened to measure. */
const validRef = (p) => isReference(p) && !p.reference_degenerate;

/* Repeated runs of a page that produced at most one line each carry no
 * agreement information; the same test decides aggregate and row flag. */
const validCons = (e) => e && e.consistency_numbers != null && e.lines.some((n) => n > 1);

function kRange(entries) {
  const ks = entries.map((e) => e.k).filter((k) => k != null);
  return ks.length ? range(ks) : "–";
}

/* Edit distance summed over every run of every page, divided by the reference
 * length summed the same way. A page then weighs as much as it is long, where
 * the mean of the page means weighs a label page like a dense folio. Both are
 * shown, because they answer different questions. */
function microCER(refs, it, key) {
  let dist = 0;
  let len = 0;
  for (const p of refs) {
    const e = p.iterations[it]?.[key];
    if (!e) continue;
    dist += e.dist.reduce((a, b) => a + b, 0);
    len += e.ref_len * e.dist.length;
  }
  return len ? dist / len : null;
}

function pageMeanCER(refs, it, key) {
  return mean(refs.map((p) => p.iterations[it]?.[key]?.mean).filter((x) => x != null));
}

/* Entries of one iteration across the given pages, for a k range. */
function iterationEntries(pages, it) {
  return pages.map((p) => p.iterations[it]).filter(Boolean);
}

/* How often the later iteration reads a page better than the earlier one, each
 * page compared with itself. The direction of a paired comparison carries its
 * own error control, so it replaces the noise threshold this page used to apply
 * to the difference of two averages. */
function pairedTally(refs, first, last, key) {
  let better = 0;
  let decided = 0;
  for (const p of refs) {
    const a = p.iterations[first]?.[key]?.mean;
    const b = p.iterations[last]?.[key]?.mean;
    if (a == null || b == null) continue;
    decided += 1;
    if (b < a) better += 1;
  }
  return { better, decided };
}

const MEASURES = [
  { key: "cer_fair", label: "CER fair", scope: "reference pages, length-weighted", secondary: "Page mean", fmt: pct },
  { key: "cer_strict", label: "CER strict", scope: "reference pages, length-weighted", secondary: "Page mean", fmt: pct },
  { key: "words", label: "Word consistency", scope: "pages without reference", fmt: two },
  { key: "numbers", label: "Number consistency", scope: "pages without reference", fmt: two },
];

function renderAggregate(summary, its, excluded) {
  const pages = Object.values(summary.pages);
  const refs = pages.filter(validRef);
  const stats = its.map((it) => {
    // A page without a reference is where agreement is the measure at all, the
    // same test the phenomenon table below uses to select its rows.
    const cons = pages.filter((p) => !isReference(p) && validCons(p.iterations[it]));
    return {
      it,
      cer_fair: microCER(refs, it, "cer_fair"),
      cer_fair_pages: pageMeanCER(refs, it, "cer_fair"),
      cer_strict: microCER(refs, it, "cer_strict"),
      cer_strict_pages: pageMeanCER(refs, it, "cer_strict"),
      words: mean(cons.map((p) => p.iterations[it].consistency_words)),
      numbers: mean(cons.map((p) => p.iterations[it].consistency_numbers)),
    };
  });

  $("#agg-cards").innerHTML = stats.map((s) => {
    const rows = MEASURES.map((m) => {
      const second = m.secondary && s[`${m.key}_pages`] != null
        ? `<div class="text-body-tertiary tnum">${escapeHTML(m.secondary)} ${m.fmt(s[`${m.key}_pages`])}</div>`
        : "";
      return `<div class="d-flex justify-content-between align-items-baseline gap-3">
        <dt class="fw-normal text-body-secondary">${escapeHTML(m.label)}
          <span class="text-body-tertiary">· ${escapeHTML(m.scope)}</span></dt>
        <dd class="mb-0 text-end text-nowrap"><span class="tnum">${m.fmt(s[m.key])}</span>${second}</dd>
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

  renderPaired(refs, its);
  renderExamples(summary, its);
  $("#agg-note").innerHTML = excluded.length
    ? `Excluded from both aggregates: ${excluded.map(pageLink).join(", ")}, flagged in the data as a reference too short to carry an error rate.`
    : "";
}

/* The comparison the page can defend, how many of the n reference pages the
 * later iteration reads better, stated with the sample sizes it rests on. */
function renderPaired(refs, its) {
  const target = $("#agg-paired");
  if (!target) return;
  if (its.length < 2 || !refs.length) { target.innerHTML = ""; return; }
  const first = its[0];
  const last = its[its.length - 1];
  const strict = pairedTally(refs, first, last, "cer_strict");
  const fair = pairedTally(refs, first, last, "cer_fair");
  const ks = kRange(iterationEntries(refs, last));
  target.innerHTML =
    `Page by page, ${escapeHTML(last)} reaches a lower strict CER on ` +
    `${strict.better} of ${strict.decided} reference pages and a lower fair CER on ` +
    `${fair.better} of ${fair.decided}. ` +
    `<span class="text-body-secondary">n = ${refs.length} reference pages, k = ${escapeHTML(ks)} runs per page.</span>`;
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

/* Cells of one row across all iterations. No cell is marked as the better one
 * here. Marking rested on a fixed lead over the runner-up, which is a threshold
 * on a single page whose repeated runs already scatter; the defensible statement
 * about the two iterations is the paired tally over all reference pages. */
function metricCells(its, measures, cellFor) {
  return its.map((_, ii) => measures.map((m, i) => {
    const c = cellFor(its[ii], m);
    // The tooltip is a mouse affordance, so the same text is also read out
    const attr = c.hint ? ` title="${escapeAttr(c.hint)}"` : "";
    const spoken = c.hint ? `<span class="visually-hidden">, ${escapeHTML(c.hint)}</span>` : "";
    return `<td class="num${i === 0 ? " group-start" : ""}"${attr}>${c.text}${spoken}</td>`;
  }).join("")).join("");
}

function renderRefTable(summary, its) {
  const rows = Object.entries(summary.pages).filter(([, p]) => isReference(p));
  const measures = [
    {
      key: "cer_fair", label: "CER fair",
      title: "Character error rate against the Transkribus transcript that carries workflow status DONE in the Inventaria project's collection, after the documented normalization profile. Lower is better.",
    },
    {
      key: "cer_strict", label: "CER strict",
      title: "The same comparison against that Transkribus transcript on exact characters, without normalization. Lower is better.",
    },
  ];
  const head = metricHead(["Page", "Folio"], its, measures);
  const body = rows.map(([id, p]) => {
    // A property of the reference text, read from the data rather than derived
    // from the rate the page happened to produce
    const bad = p.reference_degenerate === true;
    // The warning row tint alone carries no meaning for non-sighted readers
    const flag = bad
      ? ` <span class="flag" title="Reference too short to carry an error rate, awaiting adjudication">⚠<span class="visually-hidden"> flagged, reference too short</span></span>`
      : "";
    return `<tr${bad ? ' class="table-warning"' : ""}>` +
      `<th scope="row">${pageLink(id)}${flag}</th>` +
      `<td class="small">${folioLink(p)}</td>` +
      metricCells(its, measures, (it, m) => {
        const v = p.iterations[it]?.[m.key];
        if (!v) return { text: "–", hint: "" };
        return {
          text: pct(v.mean),
          hint: `range over ${p.iterations[it].k} runs: ${pct(v.min)} to ${pct(v.max)}`,
        };
      }) +
      `</tr>`;
  }).join("");
  $("#ref-table").innerHTML =
    `<caption class="visually-hidden">Character error rate per reference page and prompt iteration, mean over the repeated runs</caption>` +
    head + `<tbody>${body}</tbody>`;
  // The Inventaria attribution belongs on the same line as the scope of the
  // table, because it says whose transcription the error rate is measured on,
  // and beside it what the DONE status does and does not certify.
  $("#ref-note").innerHTML =
    `${rows.length} pages · ` +
    `${kRange(rows.flatMap(([, p]) => its.map((it) => p.iterations[it]).filter(Boolean)))} runs per page and iteration · ` +
    `measured against the Transkribus transcript with workflow status DONE in the collection of the ` +
    `Inventaria project (Univ. Salzburg / Innsbruck), <a href="https://www.inventaria.at/" target="_blank" rel="noopener">inventaria.at</a>. ` +
    `DONE records a completed workflow step; editorial approval is a separate decision, so every rate here is a comparison signal · ` +
    `spread in the cell tooltip`;
}

function renderConsTable(summary, its) {
  const rows = Object.entries(summary.pages).filter(([, p]) => !isReference(p));
  const measures = [
    {
      key: "consistency_words", label: "words",
      title: "Position-wise agreement of word tokens between the repeated runs, 0 to 1. Higher is more stable, which is not the same as correct.",
    },
    {
      key: "consistency_numbers", label: "numbers",
      title: "The same agreement restricted to number and currency tokens, 0 to 1. Higher is more stable.",
    },
    {
      key: "lines", label: "lines",
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
        if (!e) return { text: "–", hint: "" };
        if (m.key === "lines") {
          return { text: range(e.lines), hint: `line count per run: ${e.lines.join(", ")}` };
        }
        return { text: two(e[m.key]), hint: `over ${e.k} runs` };
      }) + `</tr>`;
  }).join("");
  $("#cons-table").innerHTML =
    `<caption class="visually-hidden">Agreement between the repeated runs per page and prompt iteration</caption>` +
    head + `<tbody>${body}</tbody>`;
  $("#cons-note").textContent =
    `${rows.length} pages chosen for one phenomenon each, with no reference transcription of any class · ` +
    `${kRange(rows.flatMap(([, p]) => its.map((it) => p.iterations[it]).filter(Boolean)))} runs per page and iteration · ` +
    `agreement between those runs, higher is more stable.`;
}

function renderIntro(summary, its) {
  const pages = Object.values(summary.pages);
  const refs = pages.filter(isReference).length;
  const entries = pages.flatMap((p) => its.map((it) => p.iterations[it]).filter(Boolean));
  $("#intro-facts").textContent =
    `Model ${summary.model} · ${its.length} prompt iterations (${its.join(", ")}) · ` +
    `${pages.length} pages, ${refs} of them with a Transkribus DONE reference · ` +
    `${kRange(entries)} runs per page and iteration · data as of ${summary.generated.slice(0, 10)}.`;
}

async function init() {
  try {
    const res = await fetch("data/benchmark/summary.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const summary = await res.json();
    const its = [...new Set(Object.values(summary.pages).flatMap((p) => Object.keys(p.iterations)))].sort();
    const excluded = Object.entries(summary.pages)
      .filter(([, p]) => isReference(p) && !validRef(p))
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
