import { escapeHTML, escapeAttr, lsGet, lsSet } from './utils.js';

async function digest(text) {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, '0')).join('');
}

// Decisions keep their own revision and the exact text on which they were made.
export function createAnnotationEditor(container, local, { hasDraft = () => false, workspace }) {
  let request = 0;
  let document = null;
  let extraction = null;
  let state = null;
  let pageNr = null;
  let busy = false;
  let dirty = false;
  let selectedId = null;
  let populateRequest = 0;
  const section = container.closest('#entities-dialog');
  const drafts = new Map();
  const key = (entity) => `docta-annotation-${document.docId}-${entity.id}`;
  const typeLabels = { person: 'Person', place: 'Ort', object: 'Begriff', time: 'Datumsangabe' };
  const statusLabels = { pending: 'Offen', accepted: 'Angenommen', rejected: 'Verworfen' };

  function message(text) {
    const target = container.querySelector('[role="status"]');
    if (target) target.textContent = text;
  }

  function canLeave() {
    if (busy || dirty) {
      message(busy ? 'Speichern läuft.' : 'Ungespeicherte Eingaben. Speichern oder Eingaben verwerfen.');
      return false;
    }
    return true;
  }

  workspace.addBeforeChange(canLeave);
  workspace.addBeforeHide(() => !busy);
  workspace.onContext(showContext);
  window.addEventListener('beforeunload', event => {
    if (dirty || busy) { event.preventDefault(); event.returnValue = ''; }
  });

  function entities() {
    return (extraction?.entities || []).filter(entity => entity.pageNr === pageNr);
  }

  function source(id = selectedId) {
    const entity = id ? entities().find(item => item.id === id) : entities()[0];
    const line = entity && lineFor(entity);
    if (!line) return null;
    const start = line.text.indexOf(entity.text);
    if (start < 0 || line.text.indexOf(entity.text, start + 1) >= 0) return null;
    return {
      docId: Number(document.docId), pageNr: entity.pageNr, lineId: entity.lineId,
      start, end: start + entity.text.length, quote: entity.text, lineText: line.text,
      kind: ({ object: 'term', time: 'date' })[entity.type] || entity.type,
    };
  }

  function showContext(context, refreshForm = true) {
    const entity = Number(context?.docId) === Number(document?.docId) &&
      entities().find(item => {
        const line = lineFor(item);
        if (!line) return false;
        const start = line?.text.indexOf(item.text);
        return item.lineId === context.lineId && item.pageNr === context.pageNr &&
          item.text === context.quote && start === context.start &&
          line.text.indexOf(item.text, start + 1) < 0;
      });
    section.hidden = !entity;
    const tools = section.querySelector('#entity-tools');
    if (tools) tools.hidden = !entity;
    if (!entity) return;
    selectedId = entity.id;
    const decision = state?.decisions.find(item => item.id === entity.id);
    window.document.getElementById('annotation-proposal-summary').textContent =
      `Modellvorschlag ${typeLabels[entity.type] || entity.type}, ${decision?.normalized || entity.normalized || entity.text}, ${statusLabels[decision?.status || 'pending']}`;
    const evidence = section.querySelector('#entity-legend');
    if (evidence) evidence.innerHTML = '<dl class="annotation-evidence">' + [
      ['Erzeugt mit', extraction.model || 'LLM nicht dokumentiert'],
      ['Ursprünglicher Vorschlag', entity.normalized || entity.text],
      ...(entity.date ? [['Datierung im Vorschlag', entity.date]] : []),
    ].map(([label, value]) => `<dt>${escapeHTML(label)}</dt><dd>${escapeHTML(value)}</dd>`).join('') + '</dl>';
    if (refreshForm && !dirty) render();
  }

  function render() {
    container.hidden = !local.enabled || !entities().length;
    if (container.hidden) return;
    if (!state) {
      container.textContent = 'Annotationsdaten werden geladen.';
      return;
    }
    container.innerHTML = '<form class="annotation-editor">' +
      '<label hidden>Fundstelle<select name="entity">' + entities().map(entity =>
        `<option value="${escapeAttr(entity.id)}">${escapeHTML(typeLabels[entity.type] || entity.type)} ${escapeHTML(entity.text)}</option>`).join('') +
      '</select></label><label>Normalisierte Form<input name="normalized" required></label>' +
      '<label>Entscheidung<select name="status"><option value="pending">Offen</option>' +
      '<option value="accepted">Angenommen</option><option value="rejected">Verworfen</option></select></label>' +
      '<label>Begründung<input name="reason" maxlength="2000"></label>' +
      '<details class="annotation-extra"><summary>Normdaten verknüpfen</summary><label>Normdaten-URI<input name="authority" type="url"></label></details>' +
      '<label>Dein Kürzel<input name="reviewer" required maxlength="40"></label>' +
      '<button class="review-btn" type="submit">Annotation lokal speichern</button>' +
      '<button class="review-btn" type="button" data-discard-annotation>Eingaben verwerfen</button>' +
      '<span role="status"></span></form>';
    const form = container.querySelector('form');
    let sourceText = null;
    if (entities().some(entity => entity.id === selectedId)) form.elements.entity.value = selectedId;
    form.elements.reviewer.value = window.document.getElementById('review-initials').value;
    const message = form.querySelector('[role="status"]');
    const populate = async () => {
      const token = ++populateRequest;
      const entity = entities().find(item => item.id === form.elements.entity.value);
      selectedId = entity.id;
      const decision = state.decisions.find(item => item.id === entity.id);
      let savedDraft = drafts.get(key(entity));
      if (!savedDraft) {
        try { savedDraft = JSON.parse(lsGet(key(entity)) || 'null'); } catch { savedDraft = null; }
      }
      form.elements.normalized.value = decision?.normalized ?? entity.normalized ?? entity.text;
      form.elements.authority.value = decision?.authority ?? '';
      form.elements.status.value = decision?.status ?? 'pending';
      form.elements.reason.value = decision?.reason ?? '';
      if (savedDraft) {
        for (const name of ['normalized', 'authority', 'status', 'reason', 'reviewer']) {
          if (typeof savedDraft[name] === 'string') form.elements[name].value = savedDraft[name];
        }
      }
      dirty = Boolean(savedDraft);
      form.elements.entity.disabled = dirty;
      renderHistory();
      const line = lineFor(entity);
      // A draft belongs to the reading visible when it was created, even after a text save.
      sourceText = savedDraft ? savedDraft.sourceText ?? null : line?.text;
      const stale = line && decision && decision.textDigest !== await digest(line.text);
      if (token !== populateRequest) return;
      if (dirty && message.textContent) return;
      message.textContent = savedDraft ? 'Ungespeicherter Annotationsentwurf.' : !line ? 'Quellenzeile nicht verfügbar.' : stale
        ? 'Der Quellentext hat sich geändert. Zuordnung vor dem Speichern erneut prüfen.' : '';
    };
    form.elements.entity.addEventListener('change', populate);
    form.addEventListener('input', event => {
      if (event.target === form.elements.entity) return;
      const entity = entities().find(item => item.id === form.elements.entity.value);
      const values = Object.fromEntries(['normalized', 'authority', 'status', 'reason', 'reviewer']
        .map(name => [name, form.elements[name].value]));
      values.sourceText = sourceText;
      dirty = true;
      form.elements.entity.disabled = true;
      drafts.set(key(entity), values);
      message.textContent = lsSet(key(entity), JSON.stringify(values))
        ? 'Ungespeicherter Annotationsentwurf.'
        : 'Browserentwurf konnte nicht gesichert werden. Bitte lokal speichern und den Tab geöffnet lassen.';
    });
    form.querySelector('[data-discard-annotation]').addEventListener('click', () => {
      if (busy) return;
      const entity = entities().find(item => item.id === selectedId);
      drafts.delete(key(entity));
      try { window.localStorage.removeItem(key(entity)); } catch { /* Memory still retains the saved state. */ }
      dirty = false;
      populate();
      section.open = false;
    });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (busy) return;
      if (hasDraft()) { message.textContent = 'Bitte zuerst die Textänderungen speichern.'; return; }
      const docId = Number(document.docId);
      const entity = entities().find(item => item.id === form.elements.entity.value);
      const line = lineFor(entity);
      if (!line) { message.textContent = 'Quellenzeile nicht verfügbar.'; return; }
      if (sourceText !== line.text) {
        message.textContent = 'Der Quellentext hat sich seit Beginn der Annotation geändert. Eingaben vor dem Verwerfen sichern und die neue Lesung erneut prüfen.';
        return;
      }
      const baseRevision = state.revision;
      const previous = state.decisions;
      const values = {
        normalized: form.elements.normalized.value.trim(),
        authority: form.elements.authority.value.trim() || null,
        status: form.elements.status.value,
        reason: form.elements.reason.value.trim() || null,
      };
      busy = true;
      for (const control of form.elements) control.disabled = true;
      try {
        const decision = {
          id: entity.id, kind: entity.type,
          ...values,
          textDigest: await digest(line.text),
        };
        const decisions = previous.filter(item => item.id !== entity.id).concat(decision);
        const result = await local.saveAnnotations({ docId, baseRevision, decisions, reviewer: form.elements.reviewer.value.trim() });
        dirty = false;
        drafts.delete(`docta-annotation-${docId}-${entity.id}`);
        try { window.localStorage.removeItem(`docta-annotation-${docId}-${entity.id}`); } catch { /* Saved sidecar is authoritative. */ }
        if (Number(document.docId) === docId) state = result.annotations;
        message.textContent = 'Annotation lokal gespeichert.';
        renderHistory();
        showContext(workspace.context, false);
      } catch (error) {
        message.textContent = `Nicht gespeichert: ${error.message}. Formular geöffnet lassen oder die Entscheidung vor dem Neuladen kopieren.`;
      } finally {
        busy = false;
        for (const control of form.elements) control.disabled = false;
        form.elements.entity.disabled = dirty;
      }
    });
    populate();
    renderHistory();
  }

  function renderHistory() {
    let history = container.querySelector('.annotation-history');
    if (!history) { history = window.document.createElement('details'); history.className = 'annotation-history'; container.append(history); }
    const records = value => Array.isArray(value) ? value : value?.decisions || (value ? [value] : []);
    const matching = (state?.history || []).filter(event =>
      [...records(event.before), ...records(event.after)].some(item => item.id === selectedId));
    history.innerHTML = '<summary>Änderungsverlauf</summary>' + matching.map(event => {
      const describe = value => {
        return records(value).filter(item => item.id === selectedId)
          .map(item => [item.normalized, statusLabels[item.status] || item.status, item.reason].filter(Boolean).join(', ')).join('\n');
      };
      const timestamp = new Date(event.timestamp);
      const date = Number.isNaN(timestamp.valueOf()) ? event.timestamp : timestamp.toLocaleString('de-AT');
      return `<details><summary>${escapeHTML(event.reviewer || event.actor || '')}, ${escapeHTML(date || '')}</summary><dl><dt>Vorher</dt><dd>${escapeHTML(describe(event.before))}</dd><dt>Nachher</dt><dd>${escapeHTML(describe(event.after))}</dd></dl></details>`;
    }).join('');
  }

  function lineFor(entity) {
    return document.pages.find(page => page.pageNr === entity.pageNr)?.regions
      .flatMap(region => region.lines || []).find(line => line.id === entity.lineId);
  }

  return {
    async load(doc, extracted) {
      const token = ++request;
      document = doc;
      extraction = extracted;
      state = null;
      selectedId = null;
      dirty = false;
      section.hidden = true;
      container.hidden = true;
      if (!local.enabled || !extraction?.entities?.length) return;
      try {
        const result = await local.annotations(doc.docId);
        if (token !== request) return;
        state = result;
        showContext(workspace.context);
      } catch (error) {
        if (token !== request) return;
        container.hidden = false;
        container.textContent = `Annotationen nicht verfügbar: ${error.message}`;
      }
    },
    select(id) {
      const select = container.querySelector('[name="entity"]');
      if (!select || !entities().some(entity => entity.id === id)) return;
      select.value = id;
      select.dispatchEvent(new Event('change'));
    },
    open(id, anchor) {
      if (!canLeave()) return false;
      const context = source(id);
      if (!context || !workspace.open({ context, anchor, origin: anchor })) return false;
      showContext(context);
      section.open = true;
      container.querySelector('[name="normalized"]')?.focus({ preventScroll: true });
      return true;
    },
    beforeNavigate() {
      if (!canLeave()) return false;
      workspace.hide({ restoreFocus: false });
      return true;
    },
    get hasDraft() { return dirty || busy; },
    source,
    page(nr) {
      if (pageNr === nr) return;
      pageNr = nr;
      selectedId = null;
      if (state) showContext(workspace.context);
    },
    update(doc) { document = doc; if (state && !dirty) render(); },
  };
}
