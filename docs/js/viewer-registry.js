import { escapeHTML as esc, escapeAttr as attr } from './utils.js';
import { searchKeys, describeEntry, mentionLink, historyMarkup } from './viewer-registry-display.js';
import { renderRegistryMarks } from './viewer-registry-anchors.js';
import { KIND_LABELS, registryMarkup, mentionMarkup } from './viewer-registry-markup.js';

async function digest(text) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))), byte => byte.toString(16).padStart(2, '0')).join('');
}

/** Editor-owned identities and exact mentions, separate from machine extraction. */
export function createRegistryEditor(local, { context, rerender, workspace, beforeOpen = () => true }) {
  let state = null;
  let selectedEntry = null;
  let mention = null;
  let busy = false;
  let indexed = [];
  let inlineEntry = null;
  let sourceRequest = 0;
  let registryGeneration = 0;
  const toolbar = document.querySelector('.transcription-tools');
  const button = document.createElement('button');
  button.id = 'btn-registry';
  button.className = 'review-btn';
  button.textContent = 'Register';
  button.hidden = true;
  const annotate = document.createElement('button');
  annotate.id = 'btn-annotate-selection';
  annotate.className = 'review-btn';
  annotate.textContent = 'Auswahl annotieren';
  annotate.hidden = true;
  annotate.title = 'Ausgewählten Text annotieren (Alt+A)';
  toolbar.append(button, annotate);
  const dialog = makeSurface('registry-dialog', 'Register', 'aside');
  const mentionDialog = workspace.manual;
  dialog.classList.add('registry-sidebar');
  document.querySelector('.viewer-layout').append(dialog);
  dialog.querySelector('.registry-content').innerHTML = registryMarkup;
  mentionDialog.querySelector('.registry-content').innerHTML = mentionMarkup;
  const selectionToolbar = workspace.selection;
  selectionToolbar.innerHTML = Object.entries(KIND_LABELS).map(([kind, label]) =>
    `<button type="button" class="review-btn" data-kind="${kind}">${label}</button>`).join('');
  let selectionSnapshot = null;
  let mentionAnchor = null;
  button.setAttribute('aria-controls', dialog.id);
  button.setAttribute('aria-expanded', 'false');
  const form = dialog.querySelector('form');
  const mentionForm = mentionDialog.querySelector('form');
  const inlinePanel = document.getElementById('mention-inline-entry');
  const inlineForm = document.getElementById('mention-entry-form');
  const dirty = new Set();
  workspace.addBeforeHide(() => !busy);
  workspace.onHide(updateDraftButton);
  workspace.addBeforeChange(() => {
    if (!dirty.size && !busy) return true;
    const target = dirty.has(dialog) ? dialog : mentionDialog;
    if (target === dialog) open(dialog, button);
    message(target, 'Bitte die Eingaben zuerst speichern oder verwerfen.');
    return false;
  });
  for (const element of [dialog, mentionDialog]) {
    element.querySelector('form').addEventListener('input', event => {
      if (event.target.name !== 'search') dirty.add(element);
      updateDraftButton();
    });
    const discard = document.createElement('button');
    discard.type = 'button';
    discard.className = 'review-btn';
    discard.textContent = 'Eingaben verwerfen';
    discard.addEventListener('click', () => {
      if (busy) return;
      if (element === mentionDialog && dirty.has(inlinePanel)) {
        showInlineEntry(inlineEntry);
        return;
      }
      dirty.delete(element);
      if (element === dialog && state) showEntry(selectedEntry);
      if (element === mentionDialog && mention) showMention(mention, mentionAnchor);
      message(element, 'Eingaben verworfen.');
      closeSurface(element);
      updateDraftButton();
    });
    const actions = element === mentionDialog
      ? mentionForm.querySelector(':scope > .annotation-actions')
      : element.querySelector('.registry-content');
    actions.append(discard);
    element.querySelector('[data-close-surface]')?.addEventListener('click', () => closeSurface(element));
  }
  window.addEventListener('beforeunload', event => {
    if (!dirty.size) return;
    event.preventDefault();
    event.returnValue = '';
  });
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      closeSurface(dialog);
    }
  });
  const reviewer = () => document.getElementById('review-initials').value.trim();

  function message(target, value) {
    target.querySelector(':scope > [role="status"], :scope > .registry-content > [role="status"]').textContent = value;
  }
  function sourceContext(item) {
    if (!item) return null;
    const { doc } = context();
    const page = doc?.pages.find(value => value.pageNr === item.pageNr);
    const line = page?.regions.flatMap(region => region.lines || []).find(value => value.id === item.lineId);
    return { ...item, lineText: line?.text || item.lineText || '' };
  }
  function makeSurface(id, title, tag) {
    const element = document.createElement(tag);
    element.id = id;
    element.hidden = true;
    element.setAttribute('aria-labelledby', `${id}-title`);
    element.innerHTML = `<div class="viewer-dialog__header"><h2 id="${id}-title">${title}</h2><button type="button" class="review-btn" data-close-surface>Schließen</button></div><div class="registry-content"></div>`;
    document.body.append(element);
    return element;
  }
  function updateDraftButton() {
    annotate.textContent = dirty.has(mentionDialog) || dirty.has(inlinePanel) ? 'Annotation fortsetzen' : 'Auswahl annotieren';
  }
  function closeSurface(element) {
    if (busy) return;
    if (element === mentionDialog) workspace.hide();
    else {
      dialog.hidden = true;
      document.querySelector('.viewer-layout').classList.remove('viewer-layout--registry');
      button.setAttribute('aria-expanded', 'false');
      button.focus();
    }
  }
  function open(element, origin = document.activeElement) {
    if (element === mentionDialog) {
      workspace.open({ anchor: mentionAnchor || origin, origin: origin instanceof Element ? origin : annotate, context: sourceContext(mention) });
      mentionDialog.hidden = false;
      selectionToolbar.hidden = true;
      return;
    }
    dialog.hidden = false;
    document.querySelector('.viewer-layout').classList.add('viewer-layout--registry');
    button.setAttribute('aria-expanded', 'true');
    if (!dialog.contains(document.activeElement)) document.getElementById('registry-search').focus();
  }
  function refreshRegistry() {
    indexState();
    results();
    history();
    unresolved();
  }
  async function fetchRegistry() {
    const generation = ++registryGeneration;
    const current = () => generation === registryGeneration && !busy && !dirty.size;
    try {
      const registry = await local.registry();
      if (!current()) return false;
      state = registry;
      refreshRegistry();
      return true;
    } catch (error) {
      if (!current()) return false;
      throw error;
    }
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
    document.getElementById('registry-results').innerHTML = matches(query, document.getElementById('registry-kind').value || null).map(entry => `<button type="button" class="review-btn" data-entry-id="${attr(entry.id)}">${esc(entryDescription(entry))} (${KIND_LABELS[entry.kind]})</button>`).join('') || '<p>Keine Einträge gefunden.</p>';
  }
  function entryDescription(entry) {
    return describeEntry(entry, state.entries);
  }
  function mentionLinks(mentions) {
    const { doc, pageNr } = context();
    return mentions.map(item => mentionLink(item, doc, pageNr)).join('');
  }
  function unresolved() {
    const mentions = state.mentions.filter(item => !item.entryId && item.kind !== 'date');
    document.getElementById('registry-unresolved').innerHTML =
      '<details><summary>Nicht zugeordnete Fundstellen</summary>' + mentionLinks(mentions) + '</details>';
  }
  function parentOptions() {
    const value = form.elements.broaderId.value;
    form.elements.broaderId.innerHTML = '<option value="">Kein Oberbegriff</option>' + state.entries.filter(entry => entry.kind === 'term' && entry.id !== selectedEntry?.id).map(entry => `<option value="${attr(entry.id)}">${esc(entryDescription(entry))}</option>`).join('');
    form.elements.broaderId.value = value;
    document.getElementById('registry-parent-label').hidden = form.elements.kind.value !== 'term';
  }
  function history() {
    const events = state.history.filter(event => !selectedEntry || JSON.stringify(event).includes(selectedEntry.id));
    document.querySelector('#registry-history > div').innerHTML = historyMarkup(events);
  }
  function showEntry(entry) {
    if (!beforeOpen()) return;
    if (dirty.has(dialog)) {
      message(dialog, 'Bitte den geöffneten Eintrag zuerst speichern oder Eingaben verwerfen.');
      return;
    }
    selectedEntry = entry;
    form.hidden = false;
    form.reset();
    form.elements.kind.value = entry?.kind || 'person';
    form.elements.kind.disabled = !!entry;
    for (const name of ['label', 'note']) form.elements[name].value = entry?.[name] || '';
    form.elements.aliases.value = (entry?.aliases || []).join('\n');
    form.elements.reviewer.value = reviewer();
    parentOptions();
    form.elements.broaderId.value = entry?.broaderId || '';
    const mentions = state.mentions.filter(item => entry && item.entryId === entry.id);
    document.getElementById('registry-mentions').innerHTML = entry
      ? '<h3>Fundstellen</h3>' + (mentionLinks(mentions) || '<p>Keine Fundstellen zugeordnet.</p>')
      : '';
    history();
  }
  async function save(action, fields, target) {
    if (busy) return false;
    // Reads begun before a write must never replace its resulting revision.
    registryGeneration += 1;
    busy = true;
    const targetForm = target.querySelector('form');
    const actor = targetForm.elements.reviewer.value.trim();
    for (const control of targetForm.elements) control.disabled = true;
    try {
      const result = await local.saveRegistry({ baseRevision: state.revision, reviewer: actor, action, ...fields });
      dirty.delete(target);
      state = result.registry;
      refreshRegistry();
      rerender();
      updateDraftButton();
      message(target, 'Lokal gespeichert.');
      return true;
    } catch (error) {
      message(target, `Nicht gespeichert. ${error.message}`);
      return false;
    }
    finally {
      busy = false;
      for (const control of targetForm.elements) control.disabled = false;
      targetForm.elements.kind.disabled = target === dialog ? !!selectedEntry : target === inlinePanel ? false : !!mention?.id;
    }
  }
  function entryOptions() {
    const date = mentionForm.elements.kind.value === 'date';
    document.getElementById('mention-entry-fields').hidden = date;
    document.getElementById('mention-date-fields').hidden = !date;
    const chosen = mentionForm.elements.entryId.options.length ? mentionForm.elements.entryId.value : mention?.entryId || '';
    const entries = matches(mentionForm.elements.search.value, mentionForm.elements.kind.value);
    const selected = state.entries.find(entry => entry.id === chosen && entry.kind === mentionForm.elements.kind.value);
    if (selected && !entries.includes(selected)) entries.unshift(selected);
    mentionForm.elements.entryId.innerHTML = '<option value="">Noch nicht zugeordnet</option>' + entries.map(entry => `<option value="${attr(entry.id)}">${esc(entryDescription(entry))}</option>`).join('');
    if (entries.some(entry => entry.id === chosen)) mentionForm.elements.entryId.value = chosen;
    entrySummary();
  }
  function entrySummary() {
    const entry = state.entries.find(item => item.id === mentionForm.elements.entryId.value);
    document.getElementById('mention-edit-entry').hidden = !entry;
    document.getElementById('mention-entry-summary').textContent = entry
      ? [entry.aliases.length ? entry.aliases.join(', ') : '', entry.note].filter(Boolean).join(', ')
      : '';
    const ids = [mention?.id, entry?.id].filter(Boolean);
    const events = state.history.filter(event => ids.some(id => JSON.stringify(event).includes(id)));
    document.querySelector('#mention-history > div').innerHTML = historyMarkup(events);
    document.getElementById('mention-history').hidden = !events.length;
    workspace.reposition();
  }
  function showInlineEntry(entry) {
    if (busy) return;
    if (dirty.has(inlinePanel)) {
      inlinePanel.hidden = false;
      mentionForm.hidden = true;
      message(inlinePanel, 'Bitte die Eingaben zuerst speichern oder verwerfen.');
      return;
    }
    inlineEntry = entry;
    inlineForm.reset();
    inlineForm.elements.kind.value = entry?.kind || mentionForm.elements.kind.value;
    inlineForm.elements.label.value = entry?.label || mention.quote;
    inlineForm.elements.aliases.value = (entry?.aliases || []).join('\n');
    inlineForm.elements.note.value = entry?.note || '';
    inlineForm.elements.reviewer.value = mentionForm.elements.reviewer.value || reviewer();
    inlineForm.elements.broaderId.innerHTML = '<option value="">Kein Oberbegriff</option>'
      + state.entries.filter(item => item.kind === 'term' && item.id !== entry?.id)
        .map(item => `<option value="${attr(item.id)}">${esc(entryDescription(item))}</option>`).join('');
    inlineForm.elements.broaderId.value = entry?.broaderId || '';
    document.getElementById('mention-entry-parent').hidden = inlineForm.elements.kind.value !== 'term';
    inlinePanel.hidden = false;
    mentionForm.hidden = true;
    message(inlinePanel, '');
    if (!entry) dirty.add(inlinePanel);
    updateDraftButton();
    workspace.reposition();
    inlineForm.elements.label.focus();
  }
  function returnToMention() {
    inlinePanel.hidden = true;
    mentionForm.hidden = false;
    workspace.reposition();
    mentionForm.elements.entryId.focus();
  }
  inlineForm.addEventListener('input', () => {
    dirty.add(inlinePanel);
    updateDraftButton();
  });
  document.getElementById('mention-entry-back').addEventListener('click', returnToMention);
  document.getElementById('mention-entry-discard').addEventListener('click', () => {
    if (busy) return;
    dirty.delete(inlinePanel);
    returnToMention();
    updateDraftButton();
  });
  inlineForm.addEventListener('submit', saveInlineEntry);
  async function saveInlineEntry(event) {
    event.preventDefault();
    const entry = {
      ...(inlineEntry ? { id: inlineEntry.id } : {}),
      kind: inlineForm.elements.kind.value,
      label: inlineForm.elements.label.value.trim(),
      aliases: inlineForm.elements.aliases.value.split(/\n/).map(value => value.trim()).filter(Boolean),
      note: inlineForm.elements.note.value.trim(),
      broaderId: inlineForm.elements.kind.value === 'term' ? inlineForm.elements.broaderId.value || null : null,
    };
    if (!await save('save-entry', { entry }, inlinePanel)) return;
    const saved = state.entries.find(item => entry.id ? item.id === entry.id : item.id === state.entries.at(-1).id);
    mentionForm.elements.search.value = '';
    entryOptions();
    mentionForm.elements.entryId.value = saved.id;
    mentionForm.elements.reviewer.value = inlineForm.elements.reviewer.value;
    dirty.add(mentionDialog);
    entrySummary();
    returnToMention();
    updateDraftButton();
    message(mentionDialog, 'Registereintrag gespeichert. Die Fundstelle ist noch nicht gespeichert.');
  }
  function showMention(item, origin) {
    sourceRequest += 1;
    if (!beforeOpen() || busy) return;
    if (dirty.has(mentionDialog) || dirty.has(inlinePanel)) {
      open(mentionDialog, origin);
      message(mentionDialog, 'Bitte die geöffnete Fundstelle zuerst speichern oder Eingaben verwerfen.');
      return;
    }
    if (!item) return;
    if (!workspace.open({ anchor: origin || mentionAnchor, origin: origin instanceof Element ? origin : annotate, context: sourceContext(item) })) return;
    mentionDialog.hidden = false;
    selectionToolbar.hidden = true;
    inlinePanel.hidden = true;
    mentionAnchor = origin || mentionAnchor || annotate;
    mentionForm.hidden = false;
    mention = { ...item };
    mentionForm.reset();
    mentionForm.elements.kind.value = item.kind || 'person';
    mentionForm.elements.entryId.replaceChildren();
    mentionForm.elements.note.value = item.note || '';
    document.getElementById('mention-note').open = !!item.note;
    mentionForm.elements.reviewer.value = reviewer();
    mentionForm.elements.kind.disabled = !!item.id;
    for (const name of ['when', 'notBefore', 'notAfter']) mentionForm.elements[name].value = item[name] || '';
    mentionForm.elements.uncertain.checked = !!item.uncertain;
    mentionForm.elements.dateMode.value = item.notBefore || item.notAfter ? 'range' : 'exact';
    dateFields();
    entryOptions();
    document.getElementById('mention-remove').hidden = !item.id;
    mentionForm.querySelector('[type="submit"]').hidden = !!item.stale;
    message(mentionDialog, item.stale ? 'Der Quellentext wurde geändert. Diese Fundstelle bleibt an ihrem alten Wortlaut verankert. Für eine neue Zuordnung Text erneut auswählen.' : '');
    open(mentionDialog, origin);
  }
  function dateFields() {
    const range = mentionForm.elements.dateMode.value === 'range';
    document.getElementById('mention-when').hidden = range;
    document.getElementById('mention-date-range').hidden = !range;
    workspace.reposition();
  }
  function readSelection() {
    const { doc, pageNr, viewMode } = context();
    if (!state || !local.enabled || !doc || viewMode !== 'synopsis') return null;
    const selection = window.getSelection();
    if (!selection?.rangeCount || selection.isCollapsed) return null;
    const range = selection.getRangeAt(0).cloneRange();
    const parent = node => (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement)?.closest('.transcription__line-text');
    const lineEl = parent(range.startContainer);
    if (!lineEl || lineEl !== parent(range.endContainer)) return null;
    const lineId = lineEl.closest('[data-line-id]').dataset.lineId;
    const line = doc.pages.find(page => page.pageNr === pageNr)?.regions.flatMap(region => region.lines || []).find(value => value.id === lineId);
    const before = range.cloneRange();
    before.selectNodeContents(lineEl);
    before.setEnd(range.startContainer, range.startOffset);
    const start = before.toString().length;
    const end = start + range.toString().length;
    if (!line || !range.toString().trim() || line.text.slice(start, end) !== range.toString()) return null;
    return { range, lineText: line.text, docId: Number(doc.docId), pageNr, lineId, start, end, quote: range.toString() };
  }
  function captureSelection({ focus = true } = {}) {
    if (!local.enabled || !state || !beforeOpen() || busy) return;
    if (dirty.has(mentionDialog) || dirty.has(inlinePanel)) {
      open(mentionDialog, annotate);
      if (dirty.has(inlinePanel)) {
        inlinePanel.hidden = false;
        mentionForm.hidden = true;
      }
      if (focus) (dirty.has(inlinePanel) ? inlineForm.elements.label : mentionForm.elements.reviewer).focus();
      return;
    }
    const snapshot = readSelection();
    if (!snapshot) return;
    selectionSnapshot = snapshot;
    sourceRequest += 1;
    if (!workspace.open({ anchor: snapshot.range, origin: annotate, context: snapshot })) return;
    selectionToolbar.hidden = false;
    mentionDialog.hidden = true;
    if (focus) selectionToolbar.querySelector('button').focus();
  }
  async function annotateSelection(kind) {
    if (!selectionSnapshot || !beforeOpen() || busy) return;
    const request = ++sourceRequest;
    const { range, lineText, ...snapshot } = selectionSnapshot;
    selectionToolbar.hidden = true;
    if (context().hasDraft) {
      mentionAnchor = range;
      open(mentionDialog, annotate);
      mentionForm.hidden = true;
      message(mentionDialog, 'Bitte zuerst die Textänderungen speichern.');
      return;
    }
    const textDigest = await digest(lineText);
    if (request !== sourceRequest) return;
    if (Number(context().doc?.docId) !== snapshot.docId || context().pageNr !== snapshot.pageNr) return;
    showMention({ ...snapshot, textDigest, entryId: null, kind, note: '' }, range);
    dirty.add(mentionDialog);
    updateDraftButton();
    mentionForm.elements[kind === 'date' ? 'when' : 'search'].focus();
  }
  button.addEventListener('click', async () => {
    if (!dialog.hidden) {
      closeSurface(dialog);
      return;
    }
    open(dialog, button);
    if (dirty.size || busy) return;
    try {
      await fetchRegistry();
    } catch (error) {
      message(dialog, error.message);
    }
  });
  document.getElementById('registry-export').addEventListener('click', () => {
    if (!state) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'docta-editorial-registry.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.getElementById('registry-search').addEventListener('input', results);
  document.getElementById('registry-kind').addEventListener('change', results);
  document.getElementById('registry-new').addEventListener('click', () => {
    showEntry(null);
    form.elements.label.focus();
  });
  dialog.addEventListener('click', event => {
    const entry = event.target.closest('[data-entry-id]');
    if (entry) showEntry(state.entries.find(item => item.id === entry.dataset.entryId));
    const edit = event.target.closest('[data-edit-mention]');
    if (edit) showMention(state.mentions.find(item => item.id === edit.dataset.editMention), edit);
  });
  form.elements.kind.addEventListener('change', parentOptions);
  form.addEventListener('submit', saveEntry);
  async function saveEntry(event) {
    event.preventDefault();
    const entry = {
      ...(selectedEntry ? { id: selectedEntry.id } : {}),
      kind: form.elements.kind.value,
      label: form.elements.label.value.trim(),
      aliases: form.elements.aliases.value.split(/\n/).map(value => value.trim()).filter(Boolean),
      note: form.elements.note.value.trim(),
      broaderId: form.elements.kind.value === 'term' ? form.elements.broaderId.value || null : null,
    };
    if (await save('save-entry', { entry }, dialog)) {
      const saved = state.entries.find(item => entry.id ? item.id === entry.id : item.id === state.entries.at(-1).id);
      showEntry(saved);

    }
  }
  annotate.addEventListener('mousedown', event => event.preventDefault());
  annotate.addEventListener('click', () => captureSelection());
  selectionToolbar.addEventListener('pointerdown', event => event.preventDefault());
  selectionToolbar.addEventListener('click', event => {
    const control = event.target.closest('[data-kind]');
    if (control) annotateSelection(control.dataset.kind);
  });
  const transcription = document.getElementById('transcription-container');
  transcription.addEventListener('pointerup', () => setTimeout(() => captureSelection({ focus: false }), 0));
  transcription.addEventListener('keyup', event => {
    if (event.shiftKey) captureSelection({ focus: false });
  });
  transcription.addEventListener('contextmenu', event => {
    const mark = event.target.closest('[data-mention-id]');
    if (readSelection()) {
      event.preventDefault();
      captureSelection();
    } else if (mark && state) {
      event.preventDefault();
      showMention(state.mentions.find(item => item.id === mark.dataset.mentionId), mark);
    }
  });
  mentionForm.elements.dateMode.addEventListener('change', dateFields);
  document.getElementById('mention-new-entry').addEventListener('click', () => showInlineEntry(null));
  document.getElementById('mention-edit-entry').addEventListener('click', () => {
    const entry = state.entries.find(item => item.id === mentionForm.elements.entryId.value);
    if (entry) showInlineEntry(entry);
  });
  mentionForm.elements.entryId.addEventListener('change', entrySummary);
  document.addEventListener('keydown', event => {
    if (!event.altKey || event.key.toLowerCase() !== 'a') return;
    event.preventDefault();
    captureSelection();
  });
  mentionForm.elements.search.addEventListener('input', entryOptions);
  mentionForm.elements.kind.addEventListener('change', () => {
    if (dirty.has(inlinePanel)) {
      mentionForm.elements.kind.value = inlineForm.elements.kind.value;
      showInlineEntry(inlineEntry);
      return;
    }
    mention.entryId = null;
    mentionForm.elements.entryId.value = '';
    entryOptions();
  });
  mentionForm.addEventListener('submit', saveMention);
  async function saveMention(event) {
    event.preventDefault();
    if (dirty.has(inlinePanel)) {
      inlinePanel.hidden = false;
      mentionForm.hidden = true;
      message(inlinePanel, 'Bitte den Registereintrag zuerst speichern oder verwerfen.');
      workspace.reposition();
      return;
    }
    if (context().hasDraft) {
      message(mentionDialog, 'Bitte zuerst die Textänderungen speichern.');
      return;
    }
    const payload = {
      ...mention,
      kind: mentionForm.elements.kind.value,
      entryId: mentionForm.elements.entryId.value || null,
      note: mentionForm.elements.note.value.trim(),
    };
    if (payload.kind === 'date') {
      payload.entryId = null;
      const range = mentionForm.elements.dateMode.value === 'range';
      payload.when = range ? null : mentionForm.elements.when.value.trim() || null;
      payload.notBefore = range ? mentionForm.elements.notBefore.value.trim() || null : null;
      payload.notAfter = range ? mentionForm.elements.notAfter.value.trim() || null : null;
      payload.uncertain = mentionForm.elements.uncertain.checked;
    }
    delete payload.stale;
    if (await save('save-mention', { mention: payload }, mentionDialog)) finishMentionSave();
  }
  function finishMentionSave() {
    workspace.hide();
    if (selectedEntry) showEntry(state.entries.find(entry => entry.id === selectedEntry.id));
  }
  document.getElementById('mention-remove').addEventListener('click', removeMention);
  async function removeMention() {
    if (dirty.has(inlinePanel)) {
      showInlineEntry(inlineEntry);
      return;
    }
    if (!mentionForm.elements.reviewer.reportValidity()) return;
    if (await save('remove-mention', { id: mention.id }, mentionDialog)) finishMentionSave();
  }
  document.getElementById('transcription-container').addEventListener('click', event => {
    const mark = event.target.closest('[data-mention-id]');
    if (!mark) return;
    event.stopPropagation();
    showMention(state.mentions.find(item => item.id === mark.dataset.mentionId), mark);
  });
  document.getElementById('transcription-container').addEventListener('keydown', event => {
    const mark = event.target.closest('[data-mention-id]');
    if (!mark || !['Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    event.stopPropagation();
    mark.click();
  });
  return {
    get hasDraft() { return dirty.size > 0; },
    beforeNavigate() {
      if (dirty.size || busy) {
        const target = dirty.has(mentionDialog) || dirty.has(inlinePanel) ? mentionDialog : dialog;
        open(target, annotate);
        message(target, 'Bitte die Eingaben zuerst speichern oder verwerfen.');
        return false;
      }
      workspace.hide({ restoreFocus: false });
      sourceRequest += 1;
      selectionToolbar.hidden = true;
      return true;
    },
    openSelection: captureSelection,
    async load() {
      button.hidden = annotate.hidden = !local.enabled;
      if (!local.enabled || dirty.size || busy) return;
      try {
        if (await fetchRegistry()) rerender();
      } catch (error) {
        if (!state) button.hidden = annotate.hidden = true;
        console.error(error);
      }
    },
    render() {
      annotate.hidden = !local.enabled || context().viewMode !== 'synopsis';
      if (!state || !context().doc || context().viewMode !== 'synopsis') return;
      const { doc, pageNr } = context();
      const marks = state.mentions.filter(item => Number(item.docId) === Number(doc.docId) && item.pageNr === pageNr);
      renderRegistryMarks(marks, state.entries, KIND_LABELS);
      const linked = new URLSearchParams(location.search).get('mention');
      const item = linked && marks.find(value => value.id === linked);
      if (item) {
        const anchor = Array.from(document.querySelectorAll('[data-mention-id]'))
          .find(mark => mark.dataset.mentionId === item.id);
        showMention(item, anchor || button);
        const url = new URL(location);
        url.searchParams.delete('mention');
        window.history.replaceState(null, '', url);
      }
    },
  };
}
