import { escapeHTML, escapeAttr, lsGet, lsSet } from './utils.js';

async function digest(text) {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, '0')).join('');
}

// Decisions keep their own revision and the exact text on which they were made.
export function createAnnotationEditor(container, local) {
  let request = 0;
  let document = null;
  let extraction = null;
  let state = null;
  let pageNr = null;
  let busy = false;
  const drafts = new Map();
  const key = (entity) => `docta-annotation-${document.docId}-${entity.id}`;

  function entities() {
    return (extraction?.entities || []).filter(entity => entity.pageNr === pageNr);
  }

  function render() {
    container.hidden = !local.enabled || !entities().length;
    if (container.hidden) return;
    container.innerHTML = '<form class="annotation-editor">' +
      '<label>Fundstelle<select name="entity">' + entities().map(entity =>
        `<option value="${escapeAttr(entity.id)}">${escapeHTML(entity.type)} ${escapeHTML(entity.text)}</option>`).join('') +
      '</select></label><label>Normalisierte Form<input name="normalized" required></label>' +
      '<label>Normdaten-URI<input name="authority" type="url"></label>' +
      '<label>Entscheidung<select name="status"><option value="pending">Offen</option>' +
      '<option value="accepted">Angenommen</option><option value="rejected">Verworfen</option></select></label>' +
      '<label>Begründung<input name="reason" maxlength="2000"></label>' +
      '<button class="review-btn" type="submit">Annotation lokal speichern</button>' +
      '<span role="status"></span></form>';
    const form = container.querySelector('form');
    const message = form.querySelector('[role="status"]');
    const populate = async () => {
      const entity = entities().find(item => item.id === form.elements.entity.value);
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
        for (const name of ['normalized', 'authority', 'status', 'reason']) {
          if (typeof savedDraft[name] === 'string') form.elements[name].value = savedDraft[name];
        }
      }
      const line = lineFor(entity);
      message.textContent = !line ? 'Quellenzeile nicht verfügbar.' : decision && decision.textDigest !== await digest(line.text)
        ? 'Der Quellentext hat sich geändert. Zuordnung vor dem Speichern erneut prüfen.' : '';
    };
    form.elements.entity.addEventListener('change', populate);
    form.addEventListener('input', () => {
      const entity = entities().find(item => item.id === form.elements.entity.value);
      const values = Object.fromEntries(['normalized', 'authority', 'status', 'reason']
        .map(name => [name, form.elements[name].value]));
      drafts.set(key(entity), values);
      message.textContent = lsSet(key(entity), JSON.stringify(values))
        ? 'Ungespeicherter Annotationsentwurf.'
        : 'Browserentwurf konnte nicht gesichert werden. Bitte lokal speichern und den Tab geöffnet lassen.';
    });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (busy) return;
      const docId = Number(document.docId);
      const entity = entities().find(item => item.id === form.elements.entity.value);
      const line = lineFor(entity);
      if (!line) { message.textContent = 'Quellenzeile nicht verfügbar.'; return; }
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
        const result = await local.saveAnnotations({ docId, baseRevision, decisions });
        drafts.delete(`docta-annotation-${docId}-${entity.id}`);
        try { window.localStorage.removeItem(`docta-annotation-${docId}-${entity.id}`); } catch { /* Saved sidecar is authoritative. */ }
        if (Number(document.docId) === docId) state = result.annotations;
        message.textContent = 'Annotation lokal gespeichert.';
      } catch (error) {
        message.textContent = `Nicht gespeichert: ${error.message}. Formular geöffnet lassen oder die Entscheidung vor dem Neuladen kopieren.`;
      } finally {
        busy = false;
        for (const control of form.elements) control.disabled = false;
      }
    });
    populate();
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
      container.hidden = true;
      if (!local.enabled || !extraction?.entities?.length) return;
      try {
        const result = await local.annotations(doc.docId);
        if (token !== request) return;
        state = result;
        render();
      } catch (error) {
        container.hidden = false;
        container.textContent = `Annotations unavailable: ${error.message}`;
      }
    },
    page(nr) { pageNr = nr; if (state) render(); },
    update(doc) { document = doc; if (state) render(); },
  };
}
