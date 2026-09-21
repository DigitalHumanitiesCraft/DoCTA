import { escapeHTML, escapeAttr, lsGet, lsSet } from './utils.js';

// Working tags locate evidence. They do not assert an accepted entity or event.
export function createTagEditor(container, local, { hasReviewDraft, refreshSource }) {
  let doc = null;
  let pageNr = null;
  let state = null;
  let request = 0;
  let busy = false;
  let expanded = false;
  const drafts = new Map();
  const messages = new Map();
  const draftKey = () => `docta-tags-draft-${doc.docId}-${pageNr}`;
  const page = () => doc?.pages.find(item => item.pageNr === pageNr);
  const lines = () => (page()?.regions || []).flatMap(region => region.lines || []);

  function readDraft() {
    const key = draftKey();
    if (!drafts.has(key)) {
      try { drafts.set(key, JSON.parse(lsGet(key) || 'null')); } catch { drafts.set(key, null); }
    }
    return drafts.get(key) || { lineId: '', tag: '', note: '',
      reviewer: lsGet('docta-tag-reviewer') || lsGet('docta-review-reviewer') || '',
      sourceRevision: doc.revision };
  }

  function remember(form, sourceRevision) {
    const draft = { sourceRevision, ...Object.fromEntries(
      ['lineId', 'tag', 'note', 'reviewer'].map(name => [name, form.elements[name].value])) };
    drafts.set(draftKey(), draft);
    if (!lsSet(draftKey(), JSON.stringify(draft))) {
      form.querySelector('[role="status"]').textContent = 'Browserentwurf nicht gesichert. Diesen Tab offen lassen.';
    }
    return draft;
  }

  function sync() {
    const form = container.querySelector('form');
    if (!form || !doc || !state) return;
    const staleDraft = readDraft().sourceRevision !== doc.revision;
    const staleSource = state.sourceRevision !== doc.revision;
    const warning = container.querySelector('.tag-editor__warning');
    warning.textContent = hasReviewDraft()
      ? 'Zuerst die Transkriptionskorrekturen speichern. Schlagwörter beziehen sich auf die gespeicherte Lesung.'
      : staleSource ? 'Die Quelle wurde inzwischen geändert. Gespeicherten Stand neu laden.'
      : staleDraft ? 'Die Lesung hat sich geändert. Bezugsstelle prüfen und den Entwurf neu zuordnen.' : '';
    form.querySelector('[type="submit"]').disabled = busy || hasReviewDraft() || staleDraft || staleSource;
    form.querySelector('[data-rebase]').hidden = !staleDraft;
  }

  function render(message = '') {
    container.hidden = !local.enabled || !state || !page();
    if (container.hidden) return;
    const draft = readDraft();
    const sourceLines = lines();
    container.innerHTML = `<details${expanded ? ' open' : ''}><summary>Schlagwörter</summary>
      <form class="tag-editor">
        <label>Bezugsstelle<select name="lineId"><option value="">Ganze Seite ${pageNr}</option>${sourceLines.map((line, index) =>
          `<option value="${escapeAttr(line.id)}">Zeile ${index + 1} · ${escapeHTML(line.text.slice(0, 100))}</option>`).join('')}</select></label>
        <label>Schlagwort<input name="tag" list="research-tag-suggestions" maxlength="100" required></label>
        <datalist id="research-tag-suggestions">${['Inventarisierung', 'Übergabe', 'Kauf / Beschaffung', 'Zahlung', 'Besitz / Verwahrung', 'Raumnutzung', 'Zeugenschaft'].map(tag =>
          `<option value="${tag}"></option>`).join('')}</datalist>
        <label>Notiz<textarea name="note" rows="2" maxlength="2000"></textarea></label>
        <label>Bearbeiter<input name="reviewer" maxlength="100" required></label>
        <div class="tag-editor__warning" role="status"></div>
        <button type="button" class="review-btn" data-rebase hidden>Aktuelle Lesung verwenden</button>
        <button type="submit" class="review-btn">Schlagwort lokal speichern</button>
        <button type="button" class="review-btn" data-discard>Schlagwortentwurf verwerfen</button>
        <span role="status" class="tag-editor__message">${escapeHTML(message || messages.get(String(doc.docId)) || '')}</span>
      </form>
      <div class="tag-editor__actions"><label>Gespeicherte Schlagwörter dieser Seite filtern<input type="search" name="tagFilter"></label>
        <button type="button" class="review-btn" data-refresh>Gespeicherten Stand neu laden</button>
        <button type="button" class="review-btn" data-export>Dokumentschlagwörter exportieren</button></div>
      <ul class="tag-editor__list"></ul></details>`;
    const details = container.querySelector('details');
    details.addEventListener('toggle', () => { expanded = details.open; });
    const form = container.querySelector('form');
    for (const name of ['lineId', 'tag', 'note', 'reviewer']) form.elements[name].value = draft[name];
    if (!form.elements.lineId.value && draft.lineId) {
      const option = new Option('Bezugszeile nicht mehr vorhanden. Neu auswählen.', draft.lineId, true, true);
      form.elements.lineId.add(option);
    }
    form.addEventListener('input', () => remember(form, readDraft().sourceRevision));
    form.querySelector('[data-rebase]').addEventListener('click', () => {
      remember(form, doc.revision);
      sync();
    });
    form.querySelector('[data-discard]').addEventListener('click', () => {
      drafts.delete(draftKey());
      try { window.localStorage.removeItem(draftKey()); } catch { /* The in-memory form can still be cleared. */ }
      render('Schlagwortentwurf verworfen.');
    });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (busy || hasReviewDraft() || readDraft().sourceRevision !== doc.revision || state.sourceRevision !== doc.revision) return;
      const savedDraft = remember(form, readDraft().sourceRevision);
      await mutate({ action: 'add', tag: { pageNr, lineId: savedDraft.lineId || null,
        tag: savedDraft.tag.trim(), note: savedDraft.note.trim(), reviewer: savedDraft.reviewer.trim() } }, true);
    });
    container.querySelector('[data-refresh]').addEventListener('click', async () => {
      if (busy) return;
      remember(form, readDraft().sourceRevision);
      try { await refreshSource(); } catch (error) {
        form.querySelector('.tag-editor__message').textContent = `Nicht geladen: ${error.message}`;
      }
    });
    container.querySelector('[data-export]').addEventListener('click', () => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `docta-tags-${doc.docId}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    container.querySelector('[name="tagFilter"]').addEventListener('input', renderList);
    renderList();
    if (busy) for (const control of container.querySelectorAll('input, select, textarea, button')) control.disabled = true;
    sync();
  }

  function renderList() {
    const filter = container.querySelector('[name="tagFilter"]').value.trim().toLocaleLowerCase('de');
    const items = state.tags.filter(item => item.pageNr === pageNr &&
      `${item.tag} ${item.note} ${item.text}`.toLocaleLowerCase('de').includes(filter));
    const list = container.querySelector('.tag-editor__list');
    list.innerHTML = items.map(item => {
      const index = lines().findIndex(line => line.id === item.lineId);
      const anchor = item.lineId === null ? `Seite ${item.pageNr}` : index < 0 ? 'Bezugszeile fehlt' : `Zeile ${index + 1}`;
      return `<li><div>${escapeHTML(item.tag)} · ${anchor} · ${escapeHTML(item.reviewer)}</div>
        <blockquote>${escapeHTML(item.text)}</blockquote>${item.note ? `<p>${escapeHTML(item.note)}</p>` : ''}
        ${item.stale ? `<p>Lesung geändert. Aktuelle Lesung</p><blockquote>${escapeHTML(item.lineId === null
          ? lines().map(line => line.text).join('\n') : lines().find(line => line.id === item.lineId)?.text ?? 'Bezugszeile fehlt.')}</blockquote>` : ''}
        ${item.stale ? `<button type="button" class="review-btn" data-recheck="${escapeAttr(item.id)}">Zuordnung bestätigen</button>` : ''}
        <button type="button" class="review-btn" data-delete="${escapeAttr(item.id)}" aria-label="${escapeAttr(`Schlagwort ${item.tag} entfernen`)}">Entfernen</button></li>`;
    }).join('') || '<li>Keine gespeicherten Schlagwörter für diese Auswahl.</li>';
    for (const button of list.querySelectorAll('[data-delete]')) {
      button.addEventListener('click', () => mutate({ action: 'delete', id: button.dataset.delete }));
    }
    for (const button of list.querySelectorAll('[data-recheck]')) {
      button.addEventListener('click', () => {
        const form = container.querySelector('form');
        const reviewer = form.elements.reviewer.value.trim();
        if (!reviewer) { form.elements.reviewer.reportValidity(); return; }
        if (hasReviewDraft()) { sync(); return; }
        mutate({ action: 'recheck', id: button.dataset.recheck, reviewer });
      });
    }
  }

  async function mutate(change, clearDraft = false) {
    if (busy) return;
    const docId = Number(doc.docId);
    const originPage = pageNr;
    const key = draftKey();
    const generation = request;
    const form = container.querySelector('form');
    const draft = remember(form, readDraft().sourceRevision);
    busy = true;
    for (const control of container.querySelectorAll('input, select, textarea, button')) control.disabled = true;
    try {
      const result = await local.saveTags({ docId, baseRevision: state.revision,
        sourceRevision: doc.revision, ...change });
      if (clearDraft) {
        drafts.delete(key);
        try { window.localStorage.removeItem(key); } catch { /* The sidecar holds the saved annotation. */ }
        lsSet('docta-tag-reviewer', draft.reviewer);
      }
      const message = change.action === 'delete'
        ? `Schlagwort auf Seite ${originPage} entfernt.` : `Schlagwort auf Seite ${originPage} lokal gespeichert.`;
      messages.set(String(docId), message);
      if (generation !== request) return;
      state = result.tags;
      render(message);
    } catch (error) {
      const action = change.action === 'delete' ? 'Entfernen' : change.action === 'recheck' ? 'Erneute Zuordnung' : 'Speichern';
      const message = `${action} auf Seite ${originPage} fehlgeschlagen: ${error.message}. Gespeicherten Stand neu laden und erneut prüfen.`;
      messages.set(String(docId), message);
      if (generation !== request) return;
      // Page navigation may have replaced the form while the request was pending.
      const status = container.querySelector('.tag-editor__message');
      if (status) status.textContent = message;
    } finally {
      busy = false;
      for (const control of container.querySelectorAll('input, select, textarea, button')) control.disabled = false;
      sync();
    }
  }

  window.addEventListener('beforeunload', event => {
    if ([...drafts.values()].some(draft => draft?.tag?.trim() || draft?.note?.trim())) {
      event.preventDefault();
      event.returnValue = '';
    }
  });

  return {
    async load(documentData) {
      const token = ++request;
      doc = documentData;
      state = null;
      container.hidden = true;
      if (!local.enabled) return;
      try {
        const result = await local.tags(doc.docId);
        if (token !== request) return;
        state = result;
        render();
      } catch (error) {
        if (token !== request) return;
        container.hidden = false;
        container.textContent = `Schlagwörter nicht geladen: ${error.message}`;
      }
    },
    page(nr) { pageNr = nr; if (state) render(); },
    sync,
  };
}
