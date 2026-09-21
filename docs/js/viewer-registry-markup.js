export const KIND_LABELS = { person: 'Person', term: 'Begriff', place: 'Ort', date: 'Datumsangabe' };
const kinds = Object.entries(KIND_LABELS).map(([kind, label]) => `<option value="${kind}">${label}</option>`);

export const registryMarkup = `
  <label>Suchen<input id="registry-search" type="search"></label>
  <label>Art<select id="registry-kind"><option value="">Alle</option>${kinds.slice(0, 3).join('')}</select></label>
  <div id="registry-results"></div>
  <button type="button" id="registry-new" class="review-btn">Neuer Eintrag</button>
  <form id="registry-entry-form" hidden>
    <label>Art<select name="kind">${kinds.slice(0, 3).join('')}</select></label>
    <label>Bezeichnung<input name="label" required maxlength="300"></label>
    <label>Weitere Schreibweisen<textarea name="aliases" rows="2"></textarea></label>
    <label>Notiz<textarea name="note" rows="2"></textarea></label>
    <label id="registry-parent-label">Oberbegriff<select name="broaderId"></select></label>
    <label>Dein Kürzel<input name="reviewer" required maxlength="40"></label>
    <button class="review-btn review-btn--primary" type="submit">Eintrag speichern</button>
  </form>
  <div id="registry-mentions"></div>
  <div id="registry-unresolved"></div>
  <details id="registry-history"><summary>Änderungsverlauf</summary><div></div></details>
  <button type="button" id="registry-export" class="review-btn">Register als JSON exportieren</button>
  <p role="status"></p>`;

export const mentionMarkup = `
  <form id="mention-form">
    <div class="annotation-field-row">
      <label>Art<select name="kind">${kinds.join('')}</select></label>
      <label>Dein Kürzel<input name="reviewer" required maxlength="40"></label>
    </div>
    <div id="mention-entry-fields">
      <div class="annotation-field-row">
        <label>Eintrag suchen<input name="search" type="search"></label>
        <label>Zuordnung<select name="entryId"></select></label>
      </div>
      <div class="annotation-actions">
        <button type="button" id="mention-new-entry" class="review-btn">Neuer Registereintrag</button>
        <button type="button" id="mention-edit-entry" class="review-btn" hidden>Registereintrag bearbeiten</button>
      </div>
      <div id="mention-entry-summary"></div>
    </div>
    <fieldset id="mention-date-fields" hidden>
      <legend>Datierung</legend>
      <label>Datumsform<select name="dateMode"><option value="exact">Einzelangabe</option><option value="range">Zeitraum</option></select></label>
      <label id="mention-when">Datum<input name="when" placeholder="JJJJ / JJJJ-MM / JJJJ-MM-TT" autocomplete="off"></label>
      <div id="mention-date-range" class="annotation-field-row" hidden>
        <label>Frühestens<input name="notBefore" placeholder="JJJJ / JJJJ-MM / JJJJ-MM-TT" autocomplete="off"></label>
        <label>Spätestens<input name="notAfter" placeholder="JJJJ / JJJJ-MM / JJJJ-MM-TT" autocomplete="off"></label>
      </div>
      <label class="registry-checkbox"><input name="uncertain" type="checkbox">Unsichere Datierung</label>
    </fieldset>
    <details id="mention-note"><summary>Notiz</summary><label><span class="visually-hidden">Notiz</span><textarea name="note" rows="2"></textarea></label></details>
    <div class="annotation-actions">
      <button type="submit" class="review-btn review-btn--primary">Fundstelle speichern</button>
      <button id="mention-remove" type="button" class="review-btn" hidden>Fundstelle entfernen</button>
    </div>
  </form>
  <section id="mention-inline-entry" hidden aria-labelledby="mention-inline-entry-title">
    <h3 id="mention-inline-entry-title">Registereintrag</h3>
    <form id="mention-entry-form">
      <input type="hidden" name="kind">
      <div class="annotation-field-row">
        <label>Bezeichnung<input name="label" required maxlength="300"></label>
        <label>Dein Kürzel<input name="reviewer" required maxlength="40"></label>
      </div>
      <label>Weitere Schreibweisen<textarea name="aliases" rows="2"></textarea></label>
      <label>Notiz<textarea name="note" rows="2"></textarea></label>
      <label id="mention-entry-parent">Oberbegriff<select name="broaderId"></select></label>
      <div class="annotation-actions">
        <button type="submit" class="review-btn review-btn--primary">Eintrag speichern</button>
        <button type="button" id="mention-entry-discard" class="review-btn">Eingaben verwerfen</button>
        <button type="button" id="mention-entry-back" class="review-btn">Zur Fundstelle</button>
      </div>
    </form>
    <p role="status"></p>
  </section>
  <details id="mention-history"><summary>Änderungsverlauf</summary><div></div></details>
  <p role="status"></p>`;
