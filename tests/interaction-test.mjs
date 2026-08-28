// Clicks through the interactive elements of every page and collects JS errors
// and failed requests. A navigation away from the page under test is undone, so
// the remaining elements are still exercised there. Two named flows follow the
// sweep: the source search of the home page and the review loop of the viewer,
// which the generic sweep can only touch and never assert.
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Repo root, independent of the caller's working directory.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'docs');
const PORT = 8733;
const BASE = `http://127.0.0.1:${PORT}/DoCTA/`;
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
  '.md': 'text/markdown; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg' };

const server = http.createServer((req, res) => {
  let rel = decodeURIComponent(req.url.split('?')[0]);
  if (!rel.startsWith('/DoCTA/')) { res.writeHead(404); return res.end(); }
  rel = rel.slice('/DoCTA/'.length) || 'index.html';
  const file = path.join(ROOT, rel);
  if (!file.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404); return res.end('not found: ' + rel); }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(buf);
  });
});

// Page list from the file system, so a new page is covered without maintenance.
const PAGES = fs.readdirSync(ROOT).filter(f => f.endsWith('.html')).sort();

// The document the review flow works on, one that carries both a transcription
// with line ids and a TEI file. It comes from the data on disk rather than being
// pinned, so a changed corpus does not leave a dead id behind.
function reviewDoc() {
  const tei = fs.readdirSync(path.join(ROOT, 'data', 'tei'))
    .filter(f => /^\d+\.xml$/.test(f)).map(f => f.slice(0, -4)).sort();
  for (const id of tei) {
    const file = path.join(ROOT, 'data', 'transcriptions', `${id}.json`);
    if (!fs.existsSync(file)) continue;
    const doc = JSON.parse(fs.readFileSync(file, 'utf8'));
    const page = (doc.pages || [])[0];
    const lines = (page?.regions || []).flatMap(r => r.lines || []).filter(l => l.id);
    if (lines.length >= 3) return { docId: id, pageNr: page.pageNr };
  }
  return null;
}

await new Promise(r => server.listen(PORT, '127.0.0.1', r));
const browser = await chromium.launch();
const report = {};

// No download ever reaches the file system. The review export is read from the
// Blob the page hands its anchor, and a stray export click is cancelled here.
const newContext = () => browser.newContext({
  viewport: { width: 1440, height: 900 }, acceptDownloads: false });

// null when the element is no longer there. The short timeout carries the
// weight, because a locator that resolves to nothing waits out the default half
// minute, and an index emptied by a re-render is the normal case here.
const labelOf = el => el.evaluate(e =>
  (e.innerText || e.getAttribute('aria-label') || e.getAttribute('title') ||
   e.value || e.className || e.tagName).toString().replace(/\s+/g, ' ').trim().slice(0, 50),
undefined, { timeout: 1500 }).catch(() => null);

const textLen = p => p.evaluate(() => document.body.innerText.trim().length).catch(() => -1);

// The page has settled once its rendered text stops changing. A fast render is
// answered immediately instead of being paid for with a fixed delay, and a slow
// one gets the whole budget.
async function settle(p, budget = 1500) {
  const until = Date.now() + budget;
  let last = await textLen(p);
  while (Date.now() < until) {
    await p.waitForTimeout(80);
    const now = await textLen(p);
    if (now === last) return now;
    last = now;
  }
  return last;
}

function watch(p, errors, failed) {
  p.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 250)); });
  p.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0, 250)));
  p.on('requestfailed', r => failed.push(`${r.url().slice(0, 140)} :: ${r.failure()?.errorText}`));
  p.on('response', r => { if (r.status() >= 400) failed.push(`HTTP ${r.status()} ${r.url().slice(0, 140)}`); });
}

// A page that renders nothing passes every click test, because there is nothing
// to click. The length of the rendered text is therefore a gate, not a note.
async function open(p, url, errors) {
  await p.goto(url, { waitUntil: 'networkidle', timeout: 45000 }).catch(e =>
    errors.push('NAV: ' + String(e).slice(0, 150)));
  const len = await textLen(p);
  if (len <= 0) errors.push(`EMPTY: ${url} rendered no text`);
  return len;
}

// A disabled control is not a control to click; waiting for it to become
// enabled only burns the click timeout.
const CLICKABLE =
  'main button:not([disabled]):visible, main [data-bs-toggle]:visible, ' +
  'main [role="button"]:visible, .modal button:not([disabled]):visible, ' +
  'body > button:not([disabled]):visible';
const CLICK_BUDGET = 30;
const ROUNDS = 3;

for (const page of PAGES) {
  const url = BASE + page;
  const ctx = await newContext();
  const p = await ctx.newPage();
  const errors = [], failed = [];
  watch(p, errors, failed);

  const t0 = Date.now();
  const baseText = await open(p, url, errors);
  const actions = [], navAway = [];
  let clicked = 0, skipped = 0;

  // The viewer writes the document and page it stands on into the URL, so only
  // a changed path counts as leaving the page. Treating the query string as a
  // navigation used to reload after the first click and detach everything.
  const backIfNavigated = async (what) => {
    if (new URL(p.url()).pathname.endsWith(page)) return false;
    navAway.push(`${what} -> ${p.url().replace(BASE, '')}`);
    await p.goto(url, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
    return true;
  };

  // Controls are re-queried per action instead of collected once up front. A
  // click can re-render its container, and a handle taken before that points
  // into a detached subtree, which used to be recorded as a skip and hid the
  // fact that nothing was exercised. Several rounds over the freshly queried
  // set reach the controls a click brings into existence, such as a view that
  // replaces the controls of the view before it.
  const seen = new Set();
  for (let round = 0; round < ROUNDS && clicked + skipped < CLICK_BUDGET; round++) {
    // A view can put hundreds of controls on the page (one per register entry);
    // reading a label off every one of them costs a round trip each, so the
    // scan per round is bounded like the click budget is.
    const count = Math.min(await p.locator(CLICKABLE).count(), 40);
    let fresh = 0;
    for (let i = 0; i < count && clicked + skipped < CLICK_BUDGET; i++) {
      const btn = p.locator(CLICKABLE).nth(i);
      const label = await labelOf(btn);
      if (label === null || seen.has(label)) continue;
      seen.add(label);
      fresh++;
      try {
        await btn.click({ timeout: 3000 });
        const len = await settle(p);
        actions.push(`click "${label}" -> ${len}`);
        clicked++;
        // A control that puts the page into fullscreen would hide every control
        // outside its element from the rest of the sweep.
        await p.evaluate(() => { if (document.fullscreenElement) document.exitFullscreen(); })
          .catch(() => {});
        await backIfNavigated(`click "${label}"`);
      } catch (e) {
        skipped++;
        actions.push(`SKIP "${label}": ${String(e.message || e).split('\n')[0].slice(0, 60)}`);
      }
    }
    if (!fresh) break;
  }

  const selects = p.locator('select:visible');
  const selectCount = Math.min(await selects.count(), 8);
  for (let i = 0; i < selectCount; i++) {
    const name = await labelOf(selects.nth(i)) ?? '?';
    const opts = await selects.nth(i)
      .evaluate(s => [...s.options].map(o => o.value), undefined, { timeout: 1500 })
      .catch(() => []);
    for (const v of opts.slice(0, 4)) {
      try {
        await selects.nth(i).selectOption(v, { timeout: 3000 });
        actions.push(`select[${name}]="${v}" -> ${await settle(p)}`);
      } catch { /* option gone after a re-render, reported by the next round */ }
    }
  }

  // "Inventare" is a real shelfmark fragment of the corpus, so a filter that
  // works narrows the page; the nonsense term is its counterpart.
  const inputs = p.locator('input[type="text"]:visible, input[type="search"]:visible');
  const inputCount = Math.min(await inputs.count(), 3);
  for (let i = 0; i < inputCount; i++) {
    const name = await labelOf(inputs.nth(i)) ?? '?';
    for (const term of ['Inventare', 'zzzzqqq']) {
      try {
        await inputs.nth(i).fill(term, { timeout: 3000 });
        await inputs.nth(i).press('Enter', { timeout: 2000 }).catch(() => {});
        actions.push(`input[${name}]="${term}" -> ${await settle(p)}`);
      } catch { /* field replaced by a re-render */ }
    }
    await inputs.nth(i).fill('', { timeout: 2000 }).catch(() => {});
    await settle(p, 600);
  }

  const boxes = p.locator('input[type="checkbox"]:visible, input[type="radio"]:visible');
  const boxCount = Math.min(await boxes.count(), 10);
  for (let i = 0; i < boxCount; i++) {
    const name = await labelOf(boxes.nth(i)) ?? '?';
    try {
      await boxes.nth(i).click({ timeout: 2500 });
      actions.push(`toggle[${name}] -> ${await settle(p)}`);
    } catch { /* control gone after a re-render */ }
  }

  const finalText = await settle(p);
  report[page] = { ms: Date.now() - t0, baseText, finalText, clicked, skipped, navAway,
                   failures: [], errors: [...new Set(errors)],
                   failed: [...new Set(failed)], actions };
  await ctx.close();
}

// === Source search of the home page ===
// The generic sweep types into the field and reports a length; whether the
// list actually narrowed is asserted here, against a shelfmark fragment the
// corpus really carries.
async function searchFlow() {
  const ctx = await newContext();
  const p = await ctx.newPage();
  const errors = [], failed = [], failures = [], actions = [];
  watch(p, errors, failed);
  const t0 = Date.now();
  const baseText = await open(p, BASE + 'index.html', errors);

  const rows = () => p.locator('#sources-list li.src-row').count();
  const total = await rows();
  if (!total) failures.push('the source list rendered no row');

  const term = 'Inventare A';
  await p.fill('#search-input', term);
  await p.waitForFunction(n => document.querySelectorAll('#sources-list li.src-row').length !== n,
    total, { timeout: 5000 }).catch(() => {});
  const hits = await rows();
  actions.push(`search "${term}" -> ${hits} of ${total} rows`);
  if (!(hits > 0 && hits < total)) {
    failures.push(`search "${term}" did not narrow the list: ${hits} of ${total} rows`);
  }
  const counter = (await p.locator('#result-count').innerText().catch(() => '')).trim();
  actions.push(`result count "${counter}"`);
  if (!counter) failures.push('a narrowed list reports no result count');

  await p.fill('#search-input', 'zzzzqqq');
  await p.waitForSelector('#sources-list li.src-empty', { timeout: 5000 })
    .catch(() => failures.push('a term without a match left rows standing'));
  actions.push('search "zzzzqqq" -> empty state');

  await p.fill('#search-input', '');
  await p.waitForFunction(n => document.querySelectorAll('#sources-list li.src-row').length === n,
    total, { timeout: 5000 })
    .catch(() => failures.push('clearing the search did not restore the full list'));
  actions.push(`cleared -> ${await rows()} rows`);

  const finalText = await textLen(p);
  await ctx.close();
  return { ms: Date.now() - t0, baseText, finalText, clicked: 0, skipped: 0,
           navAway: [], failures, errors: [...new Set(errors)],
           failed: [...new Set(failed)], actions };
}

// === Review loop of the viewer ===
// Review mode, a line correction, the two decision buttons and the export in
// one pass: everything the review bar promises, from a state the generic sweep
// never reaches because the bar does not exist before the toggle is pressed.
async function reviewFlow(target) {
  const ctx = await newContext();
  const p = await ctx.newPage();
  const errors = [], failed = [], failures = [], actions = [];
  // The export hands a Blob to an anchor. Keeping the Blob lets the test read
  // the exported JSON without a file ever being written.
  await p.addInitScript(() => {
    window.__exported = [];
    const create = URL.createObjectURL.bind(URL);
    URL.createObjectURL = (obj) => { window.__exported.push(obj); return create(obj); };
  });
  watch(p, errors, failed);
  const { docId, pageNr } = target;
  const t0 = Date.now();
  const baseText = await open(p,
    `${BASE}viewer.html?doc=${docId}&page=${pageNr}`, errors);

  const lines = p.locator('.transcription__line[data-line-id][data-original]');
  await lines.first().waitFor({ timeout: 20000 })
    .catch(() => failures.push('the synopsis rendered no editable line'));

  await p.click('#btn-review');
  if (await p.locator('#review-bar').isHidden()) {
    failures.push('the review bar stayed hidden after the Review toggle');
  }
  await p.fill('#review-initials', 'QA');

  const first = lines.nth(0), second = lines.nth(1);
  const original = await first.getAttribute('data-original');
  const corrected = `${original} [QA]`;
  await first.click();
  const editor = first.locator('.transcription__line-edit');
  await editor.waitFor({ timeout: 3000 })
    .catch(() => failures.push('a click on a line opened no editor'));
  await editor.fill(corrected).catch(() => {});

  // Committing by clicking the next line is the regression guard. The blur
  // commits the correction, and the same click has to open the editor of the
  // line it landed on, without a second click.
  await second.click();
  await second.locator('.transcription__line-edit').waitFor({ timeout: 3000 })
    .catch(() => failures.push('committing by clicking the next line opened no second editor'));
  await p.keyboard.press('Escape');
  const firstClass = (await first.getAttribute('class')) || '';
  if (!firstClass.includes('transcription__line--corrected')) {
    failures.push('the committed line is not marked as corrected');
  }
  actions.push(`corrected line -> "${corrected.slice(0, 40)}"`);

  const pressed = sel => p.locator(sel).getAttribute('aria-pressed');
  await p.click('#btn-status-reviewed');
  if (await pressed('#btn-status-reviewed') !== 'true') {
    failures.push('Reviewed did not report itself as pressed');
  }
  if (await pressed('#btn-status-approved') !== 'false') {
    failures.push('Reviewed pressed Approved along with it');
  }
  await p.click('#btn-status-approved');
  if (await pressed('#btn-status-approved') !== 'true' ||
      await pressed('#btn-status-reviewed') !== 'true') {
    failures.push('Approved does not report the reviewed state it implies');
  }
  // Approved implies reviewed, so a press on Reviewed must leave the approval
  // standing instead of silently downgrading it into the export.
  await p.click('#btn-status-reviewed');
  if (await pressed('#btn-status-approved') !== 'true') {
    failures.push('a press on Reviewed demoted an approved page');
  }
  actions.push('status reviewed -> approved -> reviewed, approval held');

  await p.click('#btn-review-export');
  const raw = await p.evaluate(() => {
    const blob = window.__exported[window.__exported.length - 1];
    return blob ? blob.text() : null;
  }).catch(() => null);
  let payload = null;
  try { payload = JSON.parse(raw); } catch { failures.push('the export produced no parsable JSON'); }
  if (payload) {
    if (typeof payload.version !== 'number') failures.push('the export carries no version');
    if (String(payload.docId) !== String(docId)) failures.push('the export names another document');
    const exported = payload.pages && payload.pages[String(pageNr)];
    if (!exported) failures.push(`the export carries no page ${pageNr}`);
    else {
      if (exported.status !== 'abgenommen') {
        failures.push(`the exported page carries status ${exported.status}`);
      }
      if (!(exported.lines || []).some(l => l.corrected === corrected)) {
        failures.push('the export does not carry the corrected line');
      }
    }
    actions.push(`export -> version ${payload.version}, ` +
                 `${Object.keys(payload.pages || {}).length} page(s), ` +
                 `page ${pageNr} ${exported?.status}, ` +
                 `${(exported?.lines || []).length} corrected line(s)`);
  }

  const finalText = await textLen(p);
  await ctx.close();
  return { ms: Date.now() - t0, baseText, finalText, clicked: 0, skipped: 0,
           navAway: [], failures, errors: [...new Set(errors)],
           failed: [...new Set(failed)], actions };
}

report['index.html :: source search'] = await searchFlow();
const target = reviewDoc();
report['viewer.html :: review loop'] = target
  ? await reviewFlow(target)
  : { ms: 0, baseText: 0, finalText: 0, clicked: 0, skipped: 0, navAway: [], actions: [],
      errors: [], failed: [], failures: ['no document with a line-addressed transcription found'] };

await browser.close();
server.close();
console.log(JSON.stringify(report, null, 1));

// Per-document data is optional: a missing file is the normal case and is caught
// in the client, so it does not decide the result.
const OPTIONAL = /\/data\/entities\/|\/data\/tei\//;
const blocking = Object.entries(report).filter(([, r]) =>
  r.errors.length || r.failures.length || r.failed.some(f => !OPTIONAL.test(f)) ||
  // More skipped controls than clicked ones means the sweep lost its footing
  // on that page and exercised almost nothing.
  r.skipped > r.clicked);
if (blocking.length) {
  console.error('FAIL: ' + blocking.map(([pg]) => pg).join(', '));
  process.exitCode = 1;
}
