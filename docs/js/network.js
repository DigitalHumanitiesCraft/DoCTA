/**
 * DoCTA Exploration - network view over data/graph.jsonld.
 *
 * D3 v7 is vendored as a classic script and used through the global `d3`;
 * the pinned single-file dist build is UMD and the runtime stays bundler-free.
 *
 * The view renders three resource kinds of the aggregated graph: documents,
 * entities (person, place, object) and the co-occurrence of two entities in one
 * transcription line. Everything shown carries its provenance in the detail
 * card, identification per document and aggregation for the merge step.
 */

import { escapeHTML, escapeAttr } from './utils.js';
import { shortDoc, documentIndex, attestationList } from './entity-view.js';

const TYPES = [
  { key: 'person', rdf: 'docta:Person', label: 'Person', token: '--ent-person' },
  { key: 'place', rdf: 'docta:Place', label: 'Place', token: '--ent-place' },
  { key: 'object', rdf: 'docta:Object', label: 'Object', token: '--ent-object' },
  { key: 'document', rdf: 'docta:Document', label: 'Document', token: '--text-primary' },
];
const TYPE_BY_RDF = new Map(TYPES.map(t => [t.rdf, t]));

/* Objects outnumber the other types by an order of magnitude and drown the
   layout, so they start hidden and are switched on deliberately. */
const DEFAULT_TYPES = ['person', 'place', 'document'];

const LABEL_MAX = 26;
const MIN_OBJECT_LABEL_COUNT = 2;

/* Home page of a transcription project the graph names in `transcriptionBy`.
   A name without an entry here renders as plain text rather than a wrong link. */
const TEXT_BASIS_URL = { Inventaria: 'https://www.inventaria.at/' };

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

/** Split the graph into its three resource kinds. */
function partition(graph) {
  const docs = [];
  const entities = [];
  const coocs = [];
  for (const r of graph['@graph'] || []) {
    if (r['@type'] === 'docta:Document') docs.push(r);
    else if (r['@type'] === 'docta:LineCoOccurrence') coocs.push(r);
    else if (TYPE_BY_RDF.has(r['@type'])) entities.push(r);
  }
  docs.sort((a, b) => String(a.label).localeCompare(String(b.label), 'de'));
  return { docs, entities, coocs };
}

/**
 * Canvas label of a document: place and year, which is what distinguishes the
 * sources from each other. The shelfmark stays in the tooltip and the card.
 * "Kronburg, TLA Inventare A 144.1 (1478)" becomes "Kronburg (1478)".
 */
function docNodeLabel(label) {
  const place = shortDoc(label);
  const year = String(label || '').match(/\(([^)]*)\)\s*$/);
  return year ? `${place} (${year[1]})` : place;
}

function clip(text, max = LABEL_MAX) {
  const s = String(text || '');
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

/**
 * Separates the label boxes of two nodes along the axis of smaller overlap.
 * A circular collision force cannot do this, because a label is much wider than
 * it is tall, and overlapping labels were the readability problem. Each node
 * carries `hw` and `hh`, half the width and half the height of the box that its
 * mark and its label occupy together.
 */
function forceLabelBox(strength = 0.9) {
  let nodes = [];
  function force(alpha) {
    const k = alpha * strength;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const ox = a.hw + b.hw - Math.abs(dx);
        if (ox <= 0) continue;
        const oy = a.hh + b.hh - Math.abs(dy);
        if (oy <= 0) continue;
        if (ox < oy) {
          const s = (dx < 0 ? -1 : 1) * ox * k * 0.5;
          a.vx -= s;
          b.vx += s;
        } else {
          const s = (dy < 0 ? -1 : 1) * oy * k * 0.5;
          a.vy -= s;
          b.vy += s;
        }
      }
    }
  }
  force.initialize = _ => { nodes = _; };
  return force;
}

/**
 * Resolves the remaining label overlaps once the layout has settled, by moving
 * the two nodes of an overlapping pair apart along the axis of smaller overlap.
 * The force above works against a decaying alpha and cannot close the last few
 * pixels; this pass runs at full strength and terminates when nothing overlaps.
 * @returns {boolean} true when the layout came out free of overlaps
 */
function separateLabels(nodes, iterations = 120) {
  for (let it = 0; it < iterations; it++) {
    let moved = false;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const ox = a.hw + b.hw - Math.abs(dx);
        if (ox <= 0) continue;
        const oy = a.hh + b.hh - Math.abs(dy);
        if (oy <= 0) continue;
        moved = true;
        if (ox < oy) {
          const s = (dx < 0 ? -1 : 1) * (ox / 2 + 0.5);
          a.x -= s;
          b.x += s;
        } else {
          const s = (dy < 0 ? -1 : 1) * (oy / 2 + 0.5);
          a.y -= s;
          b.y += s;
        }
      }
    }
    if (!moved) return true;
  }
  return false;
}

/** Width of a label in the canvas font, measured once per node. */
const measureLabel = (() => {
  const ctx = document.createElement('canvas').getContext('2d');
  ctx.font = '10px system-ui, -apple-system, "Segoe UI", sans-serif';
  return text => ctx.measureText(String(text || '')).width;
})();

/** Link to the project that produced the transcription, name only where unknown. */
function textBasisHTML(name) {
  const url = TEXT_BASIS_URL[name];
  return url
    ? `<a href="${escapeAttr(url)}" target="_blank" rel="noopener">${escapeHTML(name)}</a>`
    : escapeHTML(name);
}

/**
 * Provenance of the records a card shows: the text basis the reading rests on,
 * identification per source document, aggregation once for the merge. Every
 * string comes from the graph file.
 * @param {any} graph
 * @param {Set<number>|null} docIds - restricts identification to these sources
 * @param {string[]} bases - transcription projects behind those sources
 */
function provenanceHTML(graph, docIds, bases = []) {
  const prov = graph.provenance || {};
  const all = Array.isArray(prov.identification) ? prov.identification : [];
  const ident = docIds ? all.filter(e => docIds.has(e.docId)) : all;
  const use = ident.length ? ident : all;

  const sources = [...new Set(use.map(e => e.source).filter(Boolean))];
  const models = [...new Set(use.map(e => e.model).filter(Boolean))];
  const sourceLabel = sources.length === 1 && sources[0] === 'llm'
    ? 'LLM'
    : (sources.join(', ') || 'unknown');
  const isLLM = sources.length === 1 && sources[0] === 'llm';
  const identText = `${sourceLabel}${models.length ? ` (${models.join(', ')})` : ''}` +
    (isLLM ? ', unverified' : '');
  const identTitle = use.length && use[0].prompt
    ? `Prompt ${use[0].prompt}, ${use[0].date || 'undated'}`
    : 'Identification step of this record';
  const identClass = isLLM ? 'llm' : 'human';

  const agg = prov.aggregation || {};
  const aggText = agg.source === 'workflow'
    ? 'Workflow (deterministic)'
    : `${agg.source || 'unknown'}`;
  const aggTitle = agg.method || agg.generator || 'Aggregation step of this record';

  return '<div class="net-prov">' +
    (bases.length
      ? '<div class="net-prov__row"><span class="net-prov__key">Text basis</span>' +
        `<span>${bases.map(textBasisHTML).join(', ')}</span></div>`
      : '') +
    '<div class="net-prov__row"><span class="net-prov__key">Identification</span>' +
    `<span class="prov-chip prov-chip--${identClass}" title="${escapeAttr(identTitle)}">` +
    `${escapeHTML(identText)}</span></div>` +
    '<div class="net-prov__row"><span class="net-prov__key">Aggregation</span>' +
    `<span class="prov-chip prov-chip--workflow" title="${escapeAttr(aggTitle)}">` +
    `${escapeHTML(aggText)}</span></div>` +
    (agg.generator ? `<div class="net-prov__gen">${escapeHTML(agg.generator)}</div>` : '') +
    '</div>';
}

/* The detail card has room beside the link, so the line and the attested
   form stand there as visible meta text rather than in the link title. */
const attestationsHTML = (atts, docLabel) =>
  attestationList(atts, docLabel, { className: 'net-att', detail: 'meta' });

/**
 * Build the network view into `panel` with its controls in `controls`.
 * @param {HTMLElement} panel
 * @param {HTMLElement} controls - sidebar container, controls only
 * @param {any} graph - parsed data/graph.jsonld
 * @returns {{ onShow: () => void }}
 */
export function createNetworkView(panel, controls, graph) {
  const { docs, entities, coocs } = partition(graph);
  const { byId: docById, label: docLabel } = documentIndex(docs);
  /* The transcriptions the extraction read are not this project's own work;
     the graph names their origin per document, the card repeats it. */
  const basisOf = docIds => [...new Set([...docIds]
    .map(id => docById.get(Number(id))?.transcriptionBy)
    .filter(Boolean))];

  // --- markup ---------------------------------------------------------------
  const wrap = document.createElement('div');
  wrap.className = 'net-wrap';
  wrap.innerHTML =
    '<svg class="net-svg" role="img" ' +
    'aria-label="Force-directed network of the entities and documents of the aggregated research data">' +
    '<g class="net-zoom">' +
    '<g class="net-layer net-layer--attest"></g>' +
    '<g class="net-layer net-layer--cooc"></g>' +
    '<g class="net-layer net-layer--nodes"></g>' +
    '</g></svg>' +
    '<div class="net-legend" id="net-legend" hidden></div>' +
    '<div class="ent-tip net-tip" id="net-tip" hidden></div>' +
    '<div class="net-card" id="net-card" role="dialog" aria-labelledby="net-card-title" tabindex="-1" hidden>' +
    '<div class="net-card__head"><h2 class="net-card__title" id="net-card-title"></h2>' +
    '<button type="button" class="net-card__close" id="net-card-close" ' +
    'aria-label="Close the detail card" title="Close">' +
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" ' +
    'aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8"/></svg></button></div>' +
    '<div class="net-card__body" id="net-card-body"></div></div>' +
    '<div class="visually-hidden" aria-live="polite" id="net-status"></div>' +
    '<div class="visually-hidden-focusable net-list" id="net-list"></div>';
  panel.appendChild(wrap);

  const svgEl = wrap.querySelector('.net-svg');
  const svg = d3.select(svgEl);
  const zoomG = svg.select('.net-zoom');
  const layerAttest = svg.select('.net-layer--attest');
  const layerCooc = svg.select('.net-layer--cooc');
  const layerNodes = svg.select('.net-layer--nodes');
  const legendEl = wrap.querySelector('#net-legend');
  const tipEl = wrap.querySelector('#net-tip');
  const card = wrap.querySelector('#net-card');
  const cardTitle = wrap.querySelector('#net-card-title');
  const cardBody = wrap.querySelector('#net-card-body');
  const cardClose = wrap.querySelector('#net-card-close');
  const status = wrap.querySelector('#net-status');
  const listEl = wrap.querySelector('#net-list');

  // --- controls -------------------------------------------------------------
  controls.innerHTML =
    '<fieldset class="exp-ctrl"><legend class="exp-ctrl__legend">Types</legend>' +
    '<div class="net-filters" id="net-filters">' +
    TYPES.map(t =>
      `<button type="button" class="net-filter" data-type="${escapeAttr(t.key)}" ` +
      `aria-pressed="${DEFAULT_TYPES.includes(t.key)}">` +
      `<span class="net-filter__dot net-filter__dot--${escapeAttr(t.key)}" aria-hidden="true"></span>` +
      `${escapeHTML(t.label)}</button>`).join('') +
    '</div></fieldset>' +
    '<div class="exp-ctrl"><label class="exp-ctrl__legend" for="net-source">Source</label>' +
    '<select class="exp-select" id="net-source">' +
    '<option value="">All sources</option>' +
    docs.map(d => `<option value="${escapeAttr(String(d.transkribusDocId))}">` +
      `${escapeHTML(d.label)}</option>`).join('') +
    '</select></div>' +
    '<div class="exp-ctrl">' +
    '<button type="button" class="vt-btn exp-ctrl__btn" id="btn-net-fit" title="Fit the network to the view">' +
    '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="M2 5.75V2h3.75M10.25 2H14v3.75M14 10.25V14h-3.75M5.75 14H2v-3.75"/>' +
    '</svg> Fit to view</button></div>';

  const filterHost = controls.querySelector('#net-filters');
  const sourceSel = controls.querySelector('#net-source');
  const fitBtn = controls.querySelector('#btn-net-fit');

  const state = {
    types: new Set(DEFAULT_TYPES),
    docId: null,
  };

  // --- colours from the token set ------------------------------------------
  function palette() {
    const css = getComputedStyle(document.documentElement);
    const out = {};
    for (const t of TYPES) out[t.key] = css.getPropertyValue(t.token).trim();
    out.bg = css.getPropertyValue('--bg-primary').trim();
    return out;
  }

  // --- tooltip --------------------------------------------------------------
  /* A native <title> appears after a delay and cannot carry structure, and the
     svg is role="img", so its titles reach no assistive technology anyway. This
     is the same floating tooltip the viewer uses for entity marks. */
  function tipRows(head, ...rows) {
    return `<span class="ent-tip__head">${escapeHTML(head)}</span>` +
      rows.filter(Boolean).map(r => `<span class="ent-tip__prov">${escapeHTML(r)}</span>`).join('') +
      '<span class="ent-tip__prov net-tip__hint">Click for details, attestations and provenance</span>';
  }

  function moveTip(evt) {
    const pad = 14;
    const box = tipEl.getBoundingClientRect();
    const x = evt.clientX + pad + box.width > window.innerWidth - 8
      ? evt.clientX - pad - box.width : evt.clientX + pad;
    const y = evt.clientY + pad + box.height > window.innerHeight - 8
      ? evt.clientY - pad - box.height : evt.clientY + pad;
    tipEl.style.left = `${Math.max(8, x)}px`;
    tipEl.style.top = `${Math.max(8, y)}px`;
  }

  function showTip(html, evt) {
    tipEl.innerHTML = html;
    tipEl.hidden = false;
    moveTip(evt);
  }

  const hideTip = () => { tipEl.hidden = true; };

  function nodeTip(d) {
    const typeLabel = TYPES.find(t => t.key === d.type)?.label || d.type;
    if (d.kind === 'document') {
      return tipRows(d.label, `${typeLabel} · Transkribus ${d.docId}`,
        d.res.transcriptionBy ? `Transcription: ${d.res.transcriptionBy}` : '',
        `${d.count} entity attestation${d.count === 1 ? '' : 's'}`);
    }
    const inDocs = (d.res?.attestedIn || []).length;
    const roles = d.res?.role || [];
    return tipRows(d.label,
      `${typeLabel} · ${d.count} attestation${d.count === 1 ? '' : 's'}` +
        (inDocs ? ` in ${inDocs} document${inDocs === 1 ? '' : 's'}` : ''),
      roles.length ? roles.join(', ') : '');
  }

  function linkTip(l) {
    const kind = l.kind === 'cooc'
      ? 'Co-occurrence in one transcription line'
      : 'Attestation of an entity in a document';
    return tipRows(`${l.source.label} — ${l.target.label}`, `${kind} · ${l.count}×`);
  }

  // --- neighbourhood isolation ---------------------------------------------
  /* Hovering or keyboard-focusing a node dims everything outside its immediate
     neighbourhood, which is the only way to read a single node's relations in a
     layout this dense. Dimming is reversible and carries no meaning of its own. */
  const idOf = x => (typeof x === 'object' && x !== null ? x.id : x);
  let neighbours = new Map();

  function isolate(n) {
    if (!nodeSel) return;
    const near = n ? neighbours.get(n.id) : null;
    nodeSel.classed('is-dim', d => !!near && !near.has(d.id));
    nodeSel.classed('is-near', d => !!near && near.has(d.id) && d !== n);
    nodeSel.classed('is-focus', d => d === n);
    if (linkSel) {
      linkSel.classed('is-dim', l => !!n && idOf(l.source) !== n.id && idOf(l.target) !== n.id);
      linkSel.classed('is-near', l => !!n && (idOf(l.source) === n.id || idOf(l.target) === n.id));
    }
  }

  // --- model of the current filter -----------------------------------------
  function model() {
    const inScope = a => state.docId === null || a.docId === state.docId;
    const nodes = [];
    const byId = new Map();

    if (state.types.has('document')) {
      for (const d of docs) {
        if (state.docId !== null && d.transkribusDocId !== state.docId) continue;
        const n = {
          id: d['@id'], kind: 'document', type: 'document', label: d.label,
          docId: d.transkribusDocId, res: d, count: 0,
        };
        nodes.push(n);
        byId.set(n.id, n);
      }
    }
    for (const e of entities) {
      const t = TYPE_BY_RDF.get(e['@type']);
      if (!t || !state.types.has(t.key)) continue;
      const atts = (e.attestation || []).filter(inScope);
      if (!atts.length) continue;
      const n = {
        id: e['@id'], kind: 'entity', type: t.key, label: e.label,
        atts, count: atts.length, res: e,
      };
      nodes.push(n);
      byId.set(n.id, n);
    }

    const links = [];
    for (const n of nodes) {
      if (n.kind !== 'entity') continue;
      const per = new Map();
      for (const a of n.atts) per.set(a.docId, (per.get(a.docId) || 0) + 1);
      for (const [docId, count] of per) {
        const target = byId.get(`docta:doc-${docId}`);
        if (!target) continue;
        links.push({ source: n.id, target: target.id, kind: 'attest', count, docId });
        target.count += count;
      }
    }
    for (const c of coocs) {
      const [a, b] = c.member || [];
      if (!byId.has(a) || !byId.has(b)) continue;
      const atts = (c.attestation || []).filter(inScope);
      if (!atts.length) continue;
      links.push({ source: a, target: b, kind: 'cooc', count: atts.length, atts, res: c });
    }

    for (const n of nodes) n.degree = 0;
    for (const l of links) {
      byId.get(l.source).degree += 1;
      byId.get(l.target).degree += 1;
    }

    const maxCount = nodes.reduce((m, n) => Math.max(m, n.kind === 'entity' ? n.count : 0), 1);
    const r = d3.scaleSqrt().domain([1, Math.max(maxCount, 2)]).range([5, 18]).clamp(true);
    for (const n of nodes) {
      n.r = n.kind === 'document' ? 13 : r(n.count);
      n.labelled = n.type !== 'object' || n.count >= MIN_OBJECT_LABEL_COUNT;
      n.text = n.type === 'document' ? docNodeLabel(n.label) : clip(n.label);
      // Box of mark plus label: the label sits centred under the mark
      n.hw = n.labelled ? Math.max(n.r, measureLabel(n.text) / 2) + 5 : n.r + 3;
      n.hh = (n.labelled ? n.r + 16 : n.r) + 3;
    }
    nodes.sort((a, b) => String(a.label).localeCompare(String(b.label), 'de'));
    return { nodes, links };
  }

  // --- detail card ----------------------------------------------------------
  let lastTrigger = null;

  function openCard(title, html, trigger) {
    lastTrigger = trigger || null;
    cardTitle.textContent = title;
    cardBody.innerHTML = html;
    card.hidden = false;
    card.focus();
  }

  /** Hide without moving focus; used when the whole view is rebuilt. */
  function resetCard() {
    card.hidden = true;
    lastTrigger = null;
    selected = null;
  }

  function closeCard() {
    if (card.hidden) return;
    card.hidden = true;
    selected = null;
    paintSelection();
    if (lastTrigger && lastTrigger.isConnected) lastTrigger.focus();
    lastTrigger = null;
  }

  cardClose.addEventListener('click', closeCard);
  // Escape closes wherever focus sits, as long as this view is the visible one
  document.addEventListener('keydown', evt => {
    if (evt.key !== 'Escape' || !panel.classList.contains('is-active')) return;
    hideTip();
    if (!card.hidden) closeCard();
  });

  function nodeCardHTML(n) {
    const rows = [];
    const typeLabel = TYPES.find(t => t.key === n.type)?.label || n.type;
    rows.push(`<div class="net-card__row"><span class="net-card__key">Type</span>` +
      `<span class="entity entity--${escapeAttr(n.type)}">${escapeHTML(typeLabel)}</span></div>`);
    if (n.kind === 'document') {
      rows.push(`<div class="net-card__row"><span class="net-card__key">Transkribus</span>` +
        `${escapeHTML(String(n.docId))}</div>`);
      rows.push(`<div class="net-card__row"><span class="net-card__key">Source</span>` +
        `<a class="exp-attest__link" href="viewer.html?doc=${encodeURIComponent(n.docId)}">Open in the viewer</a></div>`);
      if (n.res.tei) {
        rows.push(`<div class="net-card__row"><span class="net-card__key">TEI</span>` +
          `<a class="exp-attest__link" href="data/${escapeAttr(n.res.tei)}">${escapeHTML(n.res.tei)}</a></div>`);
      }
      if (n.res.transcriptionBy) {
        rows.push('<div class="net-card__row"><span class="net-card__key">Transcription</span>' +
          `${textBasisHTML(n.res.transcriptionBy)} project</div>`);
      }
      const ids = new Set([n.docId]);
      return rows.join('') + provenanceHTML(graph, ids, basisOf(ids));
    }
    const roles = n.res.role || [];
    if (roles.length) {
      rows.push(`<div class="net-card__row"><span class="net-card__key">Role</span>` +
        `${escapeHTML(roles.join(', '))}</div>`);
    }
    const forms = n.res.attestedForm || [];
    if (forms.length) {
      rows.push(`<div class="net-card__row"><span class="net-card__key">Spellings</span>` +
        `<span class="exp-src">${escapeHTML(forms.join(', '))}</span></div>`);
    }
    rows.push(`<div class="net-card__row"><span class="net-card__key">Attested</span>` +
      `${escapeHTML(String(n.count))}×</div>`);
    const docIds = new Set(n.atts.map(a => a.docId));
    return rows.join('') +
      '<h3 class="net-card__sub">Attestations</h3>' + attestationsHTML(n.atts, docLabel) +
      provenanceHTML(graph, docIds, basisOf(docIds));
  }

  function linkCardHTML(l) {
    const a = typeof l.source === 'object' ? l.source : null;
    const b = typeof l.target === 'object' ? l.target : null;
    const rows = [];
    rows.push('<div class="net-card__row"><span class="net-card__key">Edge</span>' +
      (l.kind === 'cooc'
        ? 'Co-occurrence in one transcription line'
        : 'Attestation of an entity in a document') + '</div>');
    rows.push('<div class="net-card__row"><span class="net-card__key">Members</span>' +
      `${escapeHTML(a ? a.label : '')} — ${escapeHTML(b ? b.label : '')}</div>`);
    rows.push(`<div class="net-card__row"><span class="net-card__key">Count</span>${escapeHTML(String(l.count))}</div>`);
    if (l.kind === 'cooc') {
      const docIds = new Set(l.atts.map(x => x.docId));
      return rows.join('') + '<h3 class="net-card__sub">Loci</h3>' +
        attestationsHTML(l.atts, docLabel) + provenanceHTML(graph, docIds, basisOf(docIds));
    }
    const atts = (a && a.kind === 'entity' ? a.atts : b.atts).filter(x => x.docId === l.docId);
    const ids = new Set([l.docId]);
    return rows.join('') + '<h3 class="net-card__sub">Loci</h3>' +
      attestationsHTML(atts, docLabel) + provenanceHTML(graph, ids, basisOf(ids));
  }

  // --- zoom -----------------------------------------------------------------
  /* The view fits itself while the layout settles, unless the reader has taken
     the viewport over by panning, zooming or dragging a node. */
  let autoFit = true;

  const zoom = d3.zoom().scaleExtent([0.1, 8])
    .on('zoom', evt => {
      zoomG.attr('transform', evt.transform);
      if (evt.sourceEvent) { autoFit = false; hideTip(); }
    });
  svg.call(zoom);
  svg.on('dblclick.zoom', null);

  function size() {
    const rect = svgEl.getBoundingClientRect();
    return { w: Math.max(rect.width, 320), h: Math.max(rect.height, 240) };
  }

  function fit() {
    const box = zoomG.node().getBBox();
    if (box.width < 2 || box.height < 2) return;
    const { w, h } = size();
    const scale = Math.min(8, Math.max(0.1, 0.9 * Math.min(w / box.width, h / box.height)));
    const t = d3.zoomIdentity
      .translate(w / 2 - scale * (box.x + box.width / 2), h / 2 - scale * (box.y + box.height / 2))
      .scale(scale);
    if (reducedMotion.matches) svg.call(zoom.transform, t);
    else svg.transition().duration(400).call(zoom.transform, t);
  }

  // --- drawing --------------------------------------------------------------
  let sim = null;
  let selected = null;
  let nodeSel = null;
  let linkSel = null;
  let nodeById = new Map();

  function paintSelection() {
    if (nodeSel) nodeSel.classed('is-selected', d => selected === d);
    if (linkSel) linkSel.classed('is-selected', d => selected === d);
  }

  function selectNode(d, trigger) {
    selected = d;
    paintSelection();
    openCard(d.label, nodeCardHTML(d), trigger);
  }

  function draw() {
    if (sim) sim.stop();
    resetCard();
    autoFit = true;
    const { nodes, links } = model();
    const colors = palette();
    const { w, h } = size();

    // Adjacency for the isolation, built while the endpoints are still ids
    neighbours = new Map(nodes.map(n => [n.id, new Set([n.id])]));
    for (const l of links) {
      neighbours.get(idOf(l.source))?.add(idOf(l.target));
      neighbours.get(idOf(l.target))?.add(idOf(l.source));
    }
    hideTip();

    layerAttest.selectAll('*').remove();
    layerCooc.selectAll('*').remove();
    layerNodes.selectAll('*').remove();

    const attest = links.filter(l => l.kind === 'attest');
    const cooc = links.filter(l => l.kind === 'cooc');
    const coocWidth = d3.scaleSqrt()
      .domain([1, Math.max(1, d3.max(cooc, l => l.count) || 1)]).range([1.2, 5]).clamp(true);

    const drawLinks = (layer, list, cls, widthOf) => layer.selectAll('g')
      .data(list).join('g').attr('class', `net-linkg ${cls}`)
      .call(g => {
        g.append('line').attr('class', 'net-hit');
        g.append('line').attr('class', 'net-link').attr('stroke-width', widthOf);
      })
      .on('click', (evt, l) => {
        evt.stopPropagation();
        hideTip();
        selected = l;
        paintSelection();
        const a = l.source.label;
        const b = l.target.label;
        openCard(`${a} — ${b}`, linkCardHTML(l), null);
      })
      .on('pointerenter', (evt, l) => showTip(linkTip(l), evt))
      .on('pointermove', moveTip)
      .on('pointerleave', hideTip);

    const attestSel = drawLinks(layerAttest, attest, 'net-linkg--attest', () => 1);
    const coocSel = drawLinks(layerCooc, cooc, 'net-linkg--cooc', l => coocWidth(l.count));
    linkSel = d3.selectAll([...attestSel.nodes(), ...coocSel.nodes()]);

    nodeSel = layerNodes.selectAll('g').data(nodes).join('g')
      .attr('class', d => `net-node net-node--${d.type}${d.labelled ? ' is-labelled' : ''}`);

    nodeSel.each(function (d) {
      const g = d3.select(this);
      const fill = colors[d.type];
      if (d.type === 'document') {
        g.append('rect').attr('class', 'net-node__shape')
          .attr('x', -d.r).attr('y', -d.r).attr('width', d.r * 2).attr('height', d.r * 2)
          .attr('rx', 2).attr('fill', fill);
      } else if (d.type === 'place') {
        const r = d.r * 1.2;
        g.append('path').attr('class', 'net-node__shape')
          .attr('d', `M0,${-r}L${r},0L0,${r}L${-r},0Z`).attr('fill', fill);
      } else if (d.type === 'object') {
        // Own shape rather than a differently coloured circle: the type has to
        // stay legible without colour, and person is the circle.
        const r = d.r * 1.3;
        g.append('path').attr('class', 'net-node__shape')
          .attr('d', `M0,${-r}L${(r * 0.87).toFixed(2)},${(r * 0.5).toFixed(2)}` +
            `L${(-r * 0.87).toFixed(2)},${(r * 0.5).toFixed(2)}Z`).attr('fill', fill);
      } else {
        g.append('circle').attr('class', 'net-node__shape').attr('r', d.r).attr('fill', fill);
      }
      const label = g.append('text').attr('class', 'net-label').attr('y', d.r + 11).text(d.text);
      // Exact advance width in the rendered font; the estimate stays as fallback
      // for a panel that is not displayed yet and reports zero.
      const tw = label.node().getComputedTextLength();
      if (d.labelled && tw > 0) d.hw = Math.max(d.r, tw / 2) + 5;
    });

    nodeSel
      .on('click', (evt, d) => { evt.stopPropagation(); hideTip(); selectNode(d, null); })
      // Bring the hovered node to the front so its label is not covered
      .on('pointerenter', function (evt, d) {
        this.parentNode.appendChild(this);
        isolate(d);
        showTip(nodeTip(d), evt);
      })
      .on('pointermove', moveTip)
      .on('pointerleave', () => { isolate(null); hideTip(); })
      .call(d3.drag()
        .on('start', (evt, d) => {
          autoFit = false;
          if (!evt.active && !reducedMotion.matches) sim.alphaTarget(0.2).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (evt, d) => {
          d.fx = evt.x; d.fy = evt.y;
          if (reducedMotion.matches) { d.x = evt.x; d.y = evt.y; ticked(); }
        })
        .on('end', (evt, d) => {
          if (!evt.active && !reducedMotion.matches) sim.alphaTarget(0);
          d.fx = null; d.fy = null;
        }));

    function ticked() {
      const place = sel => sel.each(function (l) {
        const g = this;
        for (const line of g.children) {
          if (line.tagName !== 'line') continue;
          line.setAttribute('x1', l.source.x);
          line.setAttribute('y1', l.source.y);
          line.setAttribute('x2', l.target.x);
          line.setAttribute('y2', l.target.y);
        }
      });
      place(attestSel);
      place(coocSel);
      nodeSel.attr('transform', d => `translate(${d.x},${d.y})`);
    }

    /* A node attested in exactly one document is a satellite of that document.
       Its spring is short and stiff and its repulsion weak, so it settles in a
       ring around its document instead of drifting into empty canvas. */
    const isSatellite = d => d.kind === 'entity' && d.degree <= 1;

    sim = d3.forceSimulation(nodes)
      .force('cooc', d3.forceLink(cooc).id(d => d.id)
        .distance(l => 34 + 26 / l.count)
        .strength(l => Math.min(0.85, 0.3 + l.count * 0.12)))
      .force('attest', d3.forceLink(attest).id(d => d.id)
        .distance(l => (isSatellite(l.source) ? 70 : 135))
        .strength(l => (isSatellite(l.source) ? 0.7 : 0.1 + Math.min(l.count, 12) * 0.01)))
      .force('charge', d3.forceManyBody()
        .strength(d => (isSatellite(d) ? -70 : -260)).distanceMax(600))
      .force('collide', d3.forceCollide().radius(d => d.r + 5).iterations(2))
      .force('label', forceLabelBox())
      .force('center', d3.forceCenter(w / 2, h / 2))
      .force('x', d3.forceX(w / 2).strength(0.02))
      .force('y', d3.forceY(h / 2).strength(0.02))
      // Faster decay: the layout is pre-ticked anyway and a long animated
      // settle only delays the point where the labels are readable.
      .alphaDecay(0.05);

    const settle = () => {
      separateLabels(nodes);
      ticked();
    };
    const settleSteps = Math.ceil(Math.log(sim.alphaMin()) / Math.log(1 - sim.alphaDecay()));
    if (reducedMotion.matches) {
      sim.stop();
      sim.tick(settleSteps);
      settle();
      fit();
    } else {
      /* Most of the layout is computed before the first paint, so the view opens
         on a spread graph that can be fitted at once instead of on a cluster at
         the origin. The rest of the settling stays animated. */
      sim.tick(Math.round(settleSteps * 0.6));
      settle();
      fit();
      sim.on('tick', ticked).on('end', () => {
        settle();
        if (autoFit) fit();
      });
    }

    /* Legend of what is on the canvas: the shape and colour of each node type
       currently drawn, and the two edge kinds, which the canvas distinguishes
       only by weight and colour. Shapes carry the type on their own, colour
       repeats it. Only what is actually drawn is listed. */
    const drawnTypes = new Set(nodes.map(n => n.type));
    const edgeKinds = [
      attest.length ? ['attest', 'Attested in a document'] : null,
      cooc.length ? ['cooc', 'Together in one transcription line'] : null,
    ].filter(Boolean);
    legendEl.hidden = !nodes.length;
    legendEl.innerHTML = '<h2 class="visually-hidden">Legend of the network</h2>' +
      '<ul class="net-legend__list">' +
      TYPES.filter(t => drawnTypes.has(t.key)).map(t =>
        `<li class="net-legend__item"><span class="net-legend__mark ` +
        `net-legend__mark--${escapeAttr(t.key)}" aria-hidden="true"></span>` +
        `${escapeHTML(t.label)}</li>`).join('') +
      edgeKinds.map(([k, label]) =>
        `<li class="net-legend__item"><span class="net-legend__edge ` +
        `net-legend__edge--${k}" aria-hidden="true"></span>${escapeHTML(label)}</li>`).join('') +
      '</ul>';

    // Keyboard equivalent of the canvas: every node reachable by tab, opening
    // the same detail card, isolating the same neighbourhood as a hover does
    // and reporting into the live region.
    listEl.innerHTML = '<h2 class="h6">Network nodes, keyboard equivalent of the canvas</h2>' +
      '<ul class="list-unstyled mb-0">' +
      nodes.map(n => `<li><button type="button" class="btn btn-link btn-sm p-0" ` +
        `data-node-id="${escapeAttr(n.id)}">${escapeHTML(n.label)} ` +
        `(${escapeHTML(TYPES.find(t => t.key === n.type)?.label || n.type)}, ` +
        `${escapeHTML(String(n.count))}×)</button></li>`).join('') +
      '</ul>';
    nodeById = new Map(nodes.map(n => [n.id, n]));

    svgEl.dataset.nodeCount = String(nodes.length);
    svgEl.dataset.linkCount = String(links.length);
    status.textContent = `${nodes.length} nodes and ${links.length} relations shown.`;
  }

  svg.on('click', () => closeCard());
  svg.on('pointerleave', () => { isolate(null); hideTip(); });

  /* Listeners of the keyboard list are registered once, on the container that
     survives every redraw. */
  const listNode = evt => {
    const btn = evt.target.closest('[data-node-id]');
    return btn ? [btn, nodeById.get(btn.dataset.nodeId)] : [null, null];
  };

  listEl.addEventListener('focusin', evt => {
    const [, n] = listNode(evt);
    if (!n) return;
    isolate(n);
    const rel = (neighbours.get(n.id)?.size || 1) - 1;
    status.textContent = `${n.label}, ${n.type}, ` +
      `${n.count} attestation${n.count === 1 ? '' : 's'}, ` +
      `${rel} direct relation${rel === 1 ? '' : 's'}`;
  });

  listEl.addEventListener('focusout', evt => {
    if (!listEl.contains(evt.relatedTarget)) isolate(null);
  });

  listEl.addEventListener('click', evt => {
    const [btn, n] = listNode(evt);
    if (n) selectNode(n, btn);
  });

  filterHost.addEventListener('click', evt => {
    const btn = evt.target.closest('[data-type]');
    if (!btn) return;
    const key = btn.dataset.type;
    if (state.types.has(key)) state.types.delete(key);
    else state.types.add(key);
    btn.setAttribute('aria-pressed', String(state.types.has(key)));
    draw();
  });

  sourceSel.addEventListener('change', () => {
    state.docId = sourceSel.value ? Number(sourceSel.value) : null;
    draw();
  });

  fitBtn.addEventListener('click', () => { autoFit = true; fit(); });

  draw();

  return {
    onShow() {
      if (!sim) return;
      const { w, h } = size();
      sim.force('center', d3.forceCenter(w / 2, h / 2));
      fit();
    },
  };
}
