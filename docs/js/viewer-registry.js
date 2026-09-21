import { escapeHTML as esc, escapeAttr as attr } from './utils.js';

const fold = text => text.toLocaleLowerCase('de').replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const searchKeys = text => [fold(text), text.toLocaleLowerCase('de').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ß/g, 'ss')];
async function digest(text) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))), byte => byte.toString(16).padStart(2, '0')).join('');
}

/** Editor-owned identities and exact mentions, separate from machine extraction. */
export function createRegistryEditor(local, { context, rerender }) {
  let state = null;
  let selectedEntry = null;
  let mention = null;
  let busy = false;
  let indexed = [];
  const toolbar = document.querySelector('.transcription-tools');
  const button = document.createElement('button');
  button.id = 'btn-registry'; button.className = 'review-btn'; button.textContent = 'Personen und Begriffe'; button.hidden = true;
  const annotate = document.createElement('button');
  annotate.id = 'btn-annotate-selection'; annotate.className = 'review-btn'; annotate.textContent = 'Auswahl annotieren'; annotate.hidden = true;
  annotate.title = 'Ausgewählten Text annotieren (Alt+A)';
  toolbar.append(button, annotate);
  const dialog = makeDialog('registry-dialog', 'Personen und Begriffe');
  const mentionDialog = makeDialog('mention-dialog', 'Fundstelle annotieren');
  const kinds = '<option value="person">Person</option><option value="term">Begriff</option>';
  dialog.querySelector('.registry-content').innerHTML = `<label>Suchen<input id="registry-search" type="search"></label><div id="registry-results"></div><div id="registry-unresolved"></div><button type="button" id="registry-export" class="review-btn">Register als JSON exportieren</button><button type="button" id="registry-new" class="review-btn">Neuer Eintrag</button><form id="registry-entry-form" hidden><label>Art<select name="kind">${kinds}</select></label><label>Bezeichnung<input name="label" required maxlength="300"></label><label>Weitere Schreibweisen<textarea name="aliases" rows="2"></textarea></label><label>Notiz<textarea name="note" rows="2"></textarea></label><label id="registry-parent-label">Oberbegriff<select name="broaderId"></select></label><label>Dein Kürzel<input name="reviewer" required maxlength="40"></label><button class="review-btn review-btn--primary" type="submit">Eintrag speichern</button></form><div id="registry-mentions"></div><details id="registry-history"><summary>Änderungsverlauf</summary><div></div></details><p role="status"></p>`;
  mentionDialog.querySelector('.registry-content').innerHTML = `<blockquote id="mention-quote"></blockquote><form id="mention-form"><label>Art<select name="kind">${kinds}</select></label><label>Eintrag suchen<input name="search" type="search"></label><label>Zuordnung<select name="entryId"></select></label><label>Notiz<textarea name="note" rows="2"></textarea></label><label>Dein Kürzel<input name="reviewer" required maxlength="40"></label><button type="submit" class="review-btn review-btn--primary">Fundstelle speichern</button><button id="mention-remove" type="button" class="review-btn" hidden>Fundstelle entfernen</button></form><p role="status"></p>`;
  const form = dialog.querySelector('form');
  const mentionForm = mentionDialog.querySelector('form');
  const dirty = new Set();
  for (const element of [dialog, mentionDialog]) {
    element.querySelector('form').addEventListener('input', event => { if (event.target.name !== 'search') dirty.add(element); });
    element.addEventListener('cancel', event => {
      if (dirty.has(element)) { event.preventDefault(); message(element, 'Ungespeicherte Eingaben. Speichern oder Eingaben verwerfen.'); }
    });
    element.querySelector('.viewer-dialog__header button').addEventListener('click', event => {
      if (dirty.has(element)) { event.stopImmediatePropagation(); message(element, 'Ungespeicherte Eingaben. Speichern oder Eingaben verwerfen.'); }
    }, { capture: true });
    const discard = document.createElement('button'); discard.type = 'button'; discard.className = 'review-btn'; discard.textContent = 'Eingaben verwerfen';
    discard.addEventListener('click', () => {
      dirty.delete(element);
      if (element === dialog && state) showEntry(selectedEntry);
      if (element === mentionDialog && mention) showMention(mention);
      message(element, 'Eingaben verworfen.');
      element.close();
    });
    element.querySelector('.registry-content').append(discard);
  }
  window.addEventListener('beforeunload', event => { if (dirty.size) { event.preventDefault(); event.returnValue = ''; } });
  const message = (target, value) => { target.querySelector('[role="status"]').textContent = value; };
  const reviewer = () => document.getElementById('review-initials').value.trim();

  function makeDialog(id, title) {
    const element = document.createElement('dialog');
    element.id = id; element.className = 'viewer-dialog registry-dialog'; element.setAttribute('aria-labelledby', `${id}-title`);
    element.innerHTML = `<div class="viewer-dialog__header"><h2 id="${id}-title">${title}</h2><button type="button" class="review-btn">Schließen</button></div><div class="registry-content"></div>`;
    element.querySelector('button').addEventListener('click', () => element.close());
    document.body.append(element);
    return element;
  }
  function open(element, origin = document.activeElement) {
    if (!element.open) element.showModal();
    element.addEventListener('close', () => { (origin?.isConnected ? origin : button).focus(); }, { once: true });
  }
  function indexState() {
    indexed = state.entries.map(entry => ({ entry, keys: searchKeys([entry.label, ...entry.aliases].join(' ')) }));
  }
  function matches(query, kind = null) {
    const keys = searchKeys(query);
    return indexed.filter(item => (!kind || item.entry.kind === kind) && keys.some(key => item.keys.some(value => value.includes(key)))).map(item => item.entry);
  }
  function results() {
    const query = document.getElementById('registry-search').value;
    document.getElementById('registry-results').innerHTML = matches(query).map(entry => `<button type="button" class="review-btn" data-entry-id="${attr(entry.id)}">${esc(entryDescription(entry))} (${entry.kind === 'person' ? 'Person' : 'Begriff'})</button>`).join('') || '<p>Keine Einträge gefunden.</p>';
  }
  function entryDescription(entry) {
    const describe = item => [item.label, item.aliases.length ? item.aliases.join(', ') : '', item.note ? item.note.slice(0, 90) + (item.note.length > 90 ? '…' : '') : ''].filter(Boolean).join(', ');
    const description = describe(entry);
    const same = state.entries.filter(item => item.kind === entry.kind && describe(item) === description);
    if (same.length < 2) return description;
    // Equal editorial descriptions remain distinct, even before a disambiguating note exists.
    let length = 8;
    while (same.some(item => item.id !== entry.id && item.id.slice(0, length) === entry.id.slice(0, length))) length += 1;
    return `${description} (${entry.id.slice(0, length)})`;
  }
  function unresolved() {
    document.getElementById('registry-unresolved').innerHTML = '<details><summary>Nicht zugeordnete Fundstellen</summary>' + state.mentions.filter(item => !item.entryId).map(item => `<div><a href="viewer.html?doc=${encodeURIComponent(item.docId)}&page=${encodeURIComponent(item.pageNr)}&mention=${encodeURIComponent(item.id)}">${esc(item.quote)}, ${esc(String(item.docId))}, Seite ${esc(String(item.pageNr))}</a>${item.stale ? ', Text geändert, prüfen' : ''}${Number(item.docId) === Number(context().doc?.docId) ? ` <button type="button" class="review-btn" data-edit-mention="${attr(item.id)}">Bearbeiten</button>` : ''}</div>`).join('') + '</details>';
  }
  function parentOptions() {
    const value = form.elements.broaderId.value;
    form.elements.broaderId.innerHTML = '<option value="">Kein Oberbegriff</option>' + state.entries.filter(entry => entry.kind === 'term' && entry.id !== selectedEntry?.id).map(entry => `<option value="${attr(entry.id)}">${esc(entryDescription(entry))}</option>`).join('');
    form.elements.broaderId.value = value;
    document.getElementById('registry-parent-label').hidden = form.elements.kind.value !== 'term';
  }
  function history() {
    const events = state.history.filter(event => !selectedEntry || JSON.stringify(event).includes(selectedEntry.id));
    const actions = { 'save-entry': 'Eintrag gespeichert', 'save-mention': 'Fundstelle gespeichert', 'remove-mention': 'Fundstelle entfernt' };
    const reading = record => record ? [record.label || record.quote, ...(record.aliases || []), record.note].filter(Boolean).join(', ') : 'Nicht vorhanden';
    document.querySelector('#registry-history > div').innerHTML = events.map(event => `<details><summary>${esc(actions[event.action] || 'Änderung')}, ${esc(event.reviewer || event.actor || '')}, ${esc(event.timestamp || event.date || '')}</summary><dl><dt>Vorher</dt><dd>${esc(reading(event.before))}</dd><dt>Nachher</dt><dd>${esc(reading(event.after))}</dd></dl></details>`).join('') || '<p>Noch keine Änderungen.</p>';
  }
  function showEntry(entry) {
    if (dirty.has(dialog)) { message(dialog, 'Bitte den geöffneten Eintrag zuerst speichern oder Eingaben verwerfen.'); return; }
    selectedEntry = entry; form.hidden = false; form.reset();
    form.elements.kind.value = entry?.kind || 'person';
    form.elements.kind.disabled = !!entry;
    for (const name of ['label', 'note']) form.elements[name].value = entry?.[name] || '';
    form.elements.aliases.value = (entry?.aliases || []).join('\n');
    form.elements.reviewer.value = reviewer(); parentOptions(); form.elements.broaderId.value = entry?.broaderId || '';
    const mentions = state.mentions.filter(item => entry && item.entryId === entry.id);
    document.getElementById('registry-mentions').innerHTML = entry ? '<h3>Fundstellen</h3>' + (mentions.map(item => `<div><a href="viewer.html?doc=${encodeURIComponent(item.docId)}&page=${encodeURIComponent(item.pageNr)}&mention=${encodeURIComponent(item.id)}">${esc(item.quote)}, Dokument ${esc(String(item.docId))}, Seite ${esc(String(item.pageNr))}, Zeile ${esc(item.lineId)}</a>${item.stale ? ', Text geändert, prüfen' : ''}${Number(item.docId) === Number(context().doc?.docId) ? ` <button type="button" class="review-btn" data-edit-mention="${attr(item.id)}">Bearbeiten</button>` : ''}</div>`).join('') || '<p>Keine Fundstellen zugeordnet.</p>') : '';
    history();
  }
  async function save(action, fields, target) {
    if (busy) return false;
    busy = true;
    const targetForm = target.querySelector('form');
    const actor = targetForm.elements.reviewer.value.trim();
    for (const control of targetForm.elements) control.disabled = true;
    try {
      const result = await local.saveRegistry({ baseRevision: state.revision, reviewer: actor, action, ...fields });
      dirty.delete(target);
      state = result.registry; indexState(); results(); history(); unresolved(); rerender();
      message(target, 'Lokal gespeichert.'); return true;
    } catch (error) { message(target, `Nicht gespeichert. ${error.message}`); return false; }
    finally {
      busy = false;
      for (const control of targetForm.elements) control.disabled = false;
      targetForm.elements.kind.disabled = target === dialog ? !!selectedEntry : !!mention?.id;
    }
  }
  function entryOptions() {
    const chosen = mentionForm.elements.entryId.value || mention?.entryId || '';
    const entries = matches(mentionForm.elements.search.value, mentionForm.elements.kind.value);
    mentionForm.elements.entryId.innerHTML = '<option value="">Noch nicht zugeordnet</option>' + entries.map(entry => `<option value="${attr(entry.id)}">${esc(entryDescription(entry))}</option>`).join('');
    if (entries.some(entry => entry.id === chosen)) mentionForm.elements.entryId.value = chosen;
  }
  function showMention(item, origin) {
    if (dirty.has(mentionDialog)) { open(mentionDialog, origin); message(mentionDialog, 'Bitte die geöffnete Fundstelle zuerst speichern oder Eingaben verwerfen.'); return; }
    mentionForm.hidden = false;
    mention = { ...item }; mentionForm.reset(); mentionForm.elements.kind.value = item.kind || 'person';
    mentionForm.elements.note.value = item.note || ''; mentionForm.elements.reviewer.value = reviewer();
    mentionForm.elements.kind.disabled = !!item.id;
    entryOptions(); document.getElementById('mention-quote').textContent = item.quote;
    document.getElementById('mention-remove').hidden = !item.id;
    mentionForm.querySelector('[type="submit"]').hidden = !!item.stale;
    message(mentionDialog, item.stale ? 'Der Quellentext wurde geändert. Diese Fundstelle bleibt an ihrem alten Wortlaut verankert. Für eine neue Zuordnung Text erneut auswählen.' : '');
    open(mentionDialog, origin);
  }
  async function captureSelection() {
    const { doc, pageNr, hasDraft, viewMode } = context();
    if (!local.enabled || !doc || viewMode !== 'synopsis') return;
    if (hasDraft) { open(mentionDialog, annotate); message(mentionDialog, 'Bitte zuerst die Textänderungen speichern.'); mentionForm.hidden = true; return; }
    const selection = window.getSelection();
    if (!selection?.rangeCount || selection.isCollapsed) { open(mentionDialog, annotate); message(mentionDialog, 'Bitte Text innerhalb einer Zeile auswählen.'); mentionForm.hidden = true; return; }
    const range = selection.getRangeAt(0);
    const parent = node => (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement)?.closest('.transcription__line-text');
    const lineEl = parent(range.startContainer);
    if (!lineEl || lineEl !== parent(range.endContainer)) { open(mentionDialog, annotate); message(mentionDialog, 'Bitte eine Fundstelle innerhalb einer einzigen Zeile auswählen.'); mentionForm.hidden = true; return; }
    const lineId = lineEl.closest('[data-line-id]').dataset.lineId;
    const line = doc.pages.find(page => page.pageNr === pageNr)?.regions.flatMap(region => region.lines || []).find(value => value.id === lineId);
    const before = range.cloneRange(); before.selectNodeContents(lineEl); before.setEnd(range.startContainer, range.startOffset);
    const start = before.toString().length; const end = start + range.toString().length;
    if (!line || line.text.slice(start, end) !== range.toString()) return;
    const snapshot = { docId: Number(doc.docId), pageNr, lineId, start, end, quote: line.text.slice(start, end), textDigest: await digest(line.text), entryId: null, kind: 'person', note: '' };
    mentionForm.hidden = false; showMention(snapshot, annotate);
  }
  button.addEventListener('click', async () => {
    open(dialog, button);
    try { state = await local.registry(); indexState(); results(); history(); unresolved(); } catch (error) { message(dialog, error.message); }
  });
  document.getElementById('registry-export').addEventListener('click', () => {
    if (!state) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = 'docta-editorial-registry.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.getElementById('registry-search').addEventListener('input', results);
  document.getElementById('registry-new').addEventListener('click', () => { showEntry(null); form.elements.label.focus(); });
  dialog.addEventListener('click', event => {
    const entry = event.target.closest('[data-entry-id]'); if (entry) showEntry(state.entries.find(item => item.id === entry.dataset.entryId));
    const edit = event.target.closest('[data-edit-mention]'); if (edit) { mentionForm.hidden = false; showMention(state.mentions.find(item => item.id === edit.dataset.editMention), edit); }
  });
  form.elements.kind.addEventListener('change', parentOptions);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const entry = { ...(selectedEntry ? { id: selectedEntry.id } : {}), kind: form.elements.kind.value, label: form.elements.label.value.trim(), aliases: form.elements.aliases.value.split(/\n/).map(value => value.trim()).filter(Boolean), note: form.elements.note.value.trim(), broaderId: form.elements.kind.value === 'term' ? form.elements.broaderId.value || null : null };
    if (await save('save-entry', { entry }, dialog)) showEntry(state.entries.find(item => entry.id ? item.id === entry.id : item.id === state.entries.at(-1).id));
  });
  annotate.addEventListener('mousedown', event => event.preventDefault());
  annotate.addEventListener('click', captureSelection);
  document.addEventListener('keydown', event => { if (event.altKey && event.key.toLowerCase() === 'a') { event.preventDefault(); captureSelection(); } });
  mentionForm.elements.search.addEventListener('input', entryOptions);
  mentionForm.elements.kind.addEventListener('change', () => { mention.entryId = null; entryOptions(); });
  mentionForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (context().hasDraft) { message(mentionDialog, 'Bitte zuerst die Textänderungen speichern.'); return; }
    const payload = { ...mention, kind: mentionForm.elements.kind.value, entryId: mentionForm.elements.entryId.value || null, note: mentionForm.elements.note.value.trim() };
    delete payload.stale;
    if (await save('save-mention', { mention: payload }, mentionDialog)) { mentionDialog.close(); if (selectedEntry) showEntry(state.entries.find(entry => entry.id === selectedEntry.id)); }
  });
  document.getElementById('mention-remove').addEventListener('click', async () => {
    if (!mentionForm.elements.reviewer.reportValidity()) return;
    if (await save('remove-mention', { id: mention.id }, mentionDialog)) { mentionDialog.close(); if (selectedEntry) showEntry(selectedEntry); }
  });
  document.getElementById('transcription-container').addEventListener('click', event => {
    const mark = event.target.closest('[data-mention-id]'); if (!mark) return;
    event.stopPropagation(); mentionForm.hidden = false; showMention(state.mentions.find(item => item.id === mark.dataset.mentionId), mark);
  });
  document.getElementById('transcription-container').addEventListener('keydown', event => {
    const mark = event.target.closest('[data-mention-id]'); if (mark && ['Enter', ' '].includes(event.key)) { event.preventDefault(); event.stopPropagation(); mark.click(); }
  });
  return {
    async load() {
      button.hidden = annotate.hidden = !local.enabled;
      if (!local.enabled) return;
      try { state = await local.registry(); indexState(); rerender(); } catch (error) { button.hidden = annotate.hidden = true; console.error(error); }
    },
    render() {
      annotate.hidden = !local.enabled || context().viewMode !== 'synopsis';
      if (!state || !context().doc || context().viewMode !== 'synopsis') return;
      const { doc, pageNr } = context();
      const marks = state.mentions.filter(item => Number(item.docId) === Number(doc.docId) && item.pageNr === pageNr);
      for (const item of marks) {
        if (item.stale) continue;
        const line = Array.from(document.querySelectorAll('.transcription__line[data-line-id]')).find(element => element.dataset.lineId === item.lineId);
        const text = line?.querySelector('.transcription__line-text');
        if (!text || text.textContent.slice(item.start, item.end) !== item.quote || line.classList.contains('transcription__line--corrected')) continue;
        const walker = document.createTreeWalker(text, NodeFilter.SHOW_TEXT); let offset = 0; let startNode; let endNode; let startOffset; let endOffset;
        while (walker.nextNode()) { const node = walker.currentNode; const next = offset + node.length; if (!startNode && item.start >= offset && item.start < next) { startNode = node; startOffset = item.start - offset; } if (item.end > offset && item.end <= next) { endNode = node; endOffset = item.end - offset; break; } offset = next; }
        if (!startNode || !endNode) continue;
        const range = document.createRange(); range.setStart(startNode, startOffset); range.setEnd(endNode, endOffset);
        const mark = document.createElement('span'); mark.className = 'registry-mention'; mark.dataset.mentionId = item.id; mark.tabIndex = 0; mark.setAttribute('role', 'button'); mark.setAttribute('aria-label', `${item.quote}, ${state.entries.find(entry => entry.id === item.entryId)?.label || 'noch nicht zugeordnet'}, Fundstelle bearbeiten`);
        mark.append(range.extractContents()); range.insertNode(mark);
      }
      const linked = new URLSearchParams(location.search).get('mention');
      if (linked) { const item = marks.find(value => value.id === linked); if (item) { mentionForm.hidden = false; showMention(item, button); const url = new URL(location); url.searchParams.delete('mention'); window.history.replaceState(null, '', url); } }
    },
  };
}
