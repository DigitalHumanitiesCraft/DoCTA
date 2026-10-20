export const KIND_LABELS = { person: 'Person', term: 'Term', place: 'Place', date: 'Date' };
const kinds = Object.entries(KIND_LABELS).map(([kind, label]) => `<option value="${kind}">${label}</option>`);

export const registryMarkup = `
  <label>Search<input id="registry-search" type="search"></label>
  <label>Type<select id="registry-kind"><option value="">All</option>${kinds.slice(0, 3).join('')}</select></label>
  <div id="registry-results"></div>
  <button type="button" id="registry-new" class="review-btn">New entry</button>
  <form id="registry-entry-form" hidden>
    <label>Type<select name="kind">${kinds.slice(0, 3).join('')}</select></label>
    <label>Name<input name="label" required maxlength="300"></label>
    <label>Other spellings<textarea name="aliases" rows="2"></textarea></label>
    <label>Note<textarea name="note" rows="2"></textarea></label>
    <label id="registry-parent-label">Broader term<select name="broaderId"></select></label>
    <label>Your initials<input name="reviewer" required maxlength="40"></label>
    <button class="review-btn review-btn--primary" type="submit">Save entry</button>
  </form>
  <div id="registry-mentions"></div>
  <div id="registry-unresolved"></div>
  <details id="registry-history"><summary>Change history</summary><div></div></details>
  <button type="button" id="registry-export" class="review-btn">Export register as JSON</button>
  <p role="status"></p>`;

export const mentionMarkup = `
  <form id="mention-form">
    <div class="annotation-field-row">
      <label>Type<select name="kind">${kinds.join('')}</select></label>
      <label>Your initials<input name="reviewer" required maxlength="40"></label>
    </div>
    <div id="mention-entry-fields">
      <div class="annotation-field-row">
        <label>Search entries<input name="search" type="search"></label>
        <label>Assignment<select name="entryId"></select></label>
      </div>
      <div class="annotation-actions">
        <button type="button" id="mention-new-entry" class="review-btn">New register entry</button>
        <button type="button" id="mention-edit-entry" class="review-btn" hidden>Edit register entry</button>
      </div>
      <div id="mention-entry-summary"></div>
    </div>
    <fieldset id="mention-date-fields" hidden>
      <legend>Dating</legend>
      <label>Date form<select name="dateMode"><option value="exact">Single date</option><option value="range">Period</option></select></label>
      <label id="mention-when">Date<input name="when" placeholder="YYYY / YYYY-MM / YYYY-MM-DD" autocomplete="off"></label>
      <div id="mention-date-range" class="annotation-field-row" hidden>
        <label>Not before<input name="notBefore" placeholder="YYYY / YYYY-MM / YYYY-MM-DD" autocomplete="off"></label>
        <label>Not after<input name="notAfter" placeholder="YYYY / YYYY-MM / YYYY-MM-DD" autocomplete="off"></label>
      </div>
      <label class="registry-checkbox"><input name="uncertain" type="checkbox">Uncertain date</label>
    </fieldset>
    <details id="mention-note"><summary>Note</summary><label><span class="visually-hidden">Note</span><textarea name="note" rows="2"></textarea></label></details>
    <div class="annotation-actions">
      <button type="submit" class="review-btn review-btn--primary">Save occurrence</button>
      <button id="mention-remove" type="button" class="review-btn" hidden>Remove occurrence</button>
    </div>
  </form>
  <section id="mention-inline-entry" hidden aria-labelledby="mention-inline-entry-title">
    <h3 id="mention-inline-entry-title">Register entry</h3>
    <form id="mention-entry-form">
      <input type="hidden" name="kind">
      <div class="annotation-field-row">
        <label>Name<input name="label" required maxlength="300"></label>
        <label>Your initials<input name="reviewer" required maxlength="40"></label>
      </div>
      <label>Other spellings<textarea name="aliases" rows="2"></textarea></label>
      <label>Note<textarea name="note" rows="2"></textarea></label>
      <label id="mention-entry-parent">Broader term<select name="broaderId"></select></label>
      <div class="annotation-actions">
        <button type="submit" class="review-btn review-btn--primary">Save entry</button>
        <button type="button" id="mention-entry-discard" class="review-btn">Discard input</button>
        <button type="button" id="mention-entry-back" class="review-btn">Back to occurrence</button>
      </div>
    </form>
    <p role="status"></p>
  </section>
  <details id="mention-history"><summary>Change history</summary><div></div></details>
  <p role="status"></p>`;
