/**
 * DoCTA viewer - the unclear-reading notation of a line.
 *
 * [?] marks an illegible passage, and the dot and dash forms of the Transkribus
 * layer ([..], [- - -]) mean the same; [word?] marks an uncertain reading. Any
 * other bracket, a folio mark such as [fol.1r] or a supplied [er], is text. The
 * patterns are those of GAP_MARK and UNCLEAR_MARK in pipeline/build_tei.py, so
 * the viewer marks exactly what the TEI encodes.
 *
 * The marks stay as written, so the line text and every offset into it are
 * unchanged. In a machine transcription the brackets are the model's own
 * uncertainty and get one neutral tooltip; they become notation once a
 * reviewer saves the line.
 */

import { escapeHTML, escapeAttr } from './utils.js';
import { READINGS } from './strings.js';

const MARK = /\[(?:\?|\.{1,5}|-(?: -)*|-{2,})\]|\[([^[\]?]*[^[\]?\s.-][^[\]?]*)\?\]/g;

/**
 * The line as consecutive segments; joining their text gives the line back.
 * @param {string} text
 * @returns {{ text: string, kind: 'gap'|'unclear'|null }[]}
 */
export function readingSegments(text) {
  const out = [];
  let pos = 0;
  for (const m of text.matchAll(MARK)) {
    if (m.index > pos) out.push({ text: text.slice(pos, m.index), kind: null });
    out.push({ text: m[0], kind: m[1] === undefined ? 'gap' : 'unclear' });
    pos = m.index + m[0].length;
  }
  if (pos < text.length) out.push({ text: text.slice(pos), kind: null });
  return out;
}

/**
 * Escaped line markup with every unclear mark wrapped and named.
 * @param {string} text
 * @param {boolean} machine the line is unrevised machine transcription
 */
export function readingsHTML(text, machine) {
  return readingSegments(text).map(({ text: part, kind }) => {
    if (!kind) return escapeHTML(part);
    const state = machine ? 'machine' : kind;
    return `<span class="reading-mark" data-reading="${state}" title="${escapeAttr(READINGS[state])}">` +
      `${escapeHTML(part)}</span>`;
  }).join('');
}

/**
 * The input value after Mark as unclear: the selection becomes [selection?],
 * an empty selection an illegible [?]. Returns the new value and caret.
 * @param {string} value
 * @param {number} start
 * @param {number} end
 */
export function markUnclear(value, start, end) {
  const selected = value.slice(start, end).trim();
  const lead = value.slice(start, end).length - value.slice(start, end).trimStart().length;
  const from = start + lead;
  const to = from + selected.length;
  const mark = selected && !/[[\]?]/.test(selected) ? `[${selected}?]` : '[?]';
  const next = selected && mark === '[?]' ? value : value.slice(0, from) + mark + value.slice(to);
  return { value: next, caret: next === value ? end : from + mark.length };
}
