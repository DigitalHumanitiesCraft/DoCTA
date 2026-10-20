// Focused regression checks for the viewer's information hierarchy, dialogs,
// responsive layout and review persistence. The local editor API is emulated
// in memory, so this test never writes to the repository review register.
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { useCachedFacsimiles } from './facsimile-fixtures.mjs';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = path.join(REPO, 'docs');
const DOC_ID = 11328300;
// Port 0 lets the system choose a free port, so suites can run concurrently.
let BASE = 'http://127.0.0.1/';
const TOKEN = 'viewer-ui-test-token';
const output = path.join(REPO, 'output', 'readiness-check');
fs.mkdirSync(output, { recursive: true });
const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml', '.xml': 'application/xml; charset=utf-8',
  '.png': 'image/png', '.jpg': 'image/jpeg',
};

const fixture = JSON.parse(fs.readFileSync(
  path.join(ROOT, 'data', 'transcriptions', `${DOC_ID}.json`), 'utf8'));
const revision = 'viewer-ui-fixture-revision';
let saved = null;
let posts = 0;
let lastPayload = null;

function documentPayload() {
  const doc = structuredClone(fixture);
  doc.revision = saved?.revision || revision;
  doc.reviewState = saved?.reviewState || Object.fromEntries(
    doc.pages.map(page => [String(page.pageNr), { status: 'unbearbeitet' }]));
  if (saved?.lines) {
    for (const page of doc.pages) {
      const changes = saved.lines[String(page.pageNr)] || {};
      for (const region of page.regions || []) {
        for (const line of region.lines || []) {
          const direct = Object.hasOwn(changes, line.id) ? changes[line.id] : undefined;
          const corrected = direct ?? Object.entries(changes)
            .find(([id]) => id.endsWith(`-${line.id}`))?.[1];
          if (corrected !== undefined) line.text = corrected;
        }
      }
    }
  }
  return doc;
}

function json(res, status, payload, headers = {}) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body), ...headers,
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, BASE);
  // A context sending this header sees a plain static host, like GitHub Pages.
  const staticHost = req.headers['x-docta-static'] === '1';
  if (url.pathname.startsWith('/api/') && staticHost) {
    res.writeHead(404);
    return res.end('not found');
  }
  if (url.pathname === '/api/session') {
    return json(res, 200, { write_enabled: true, token: TOKEN });
  }
  if (url.pathname === `/api/documents/${DOC_ID}`) {
    return json(res, 200, documentPayload());
  }
  if (url.pathname === '/api/registry' && req.method === 'GET') {
    return json(res, 200, { schemaVersion: 1, revision, entries: [], mentions: [], history: [] });
  }
  if (url.pathname === '/api/review' && req.method === 'POST') {
    let raw = '';
    req.on('data', chunk => { raw += chunk; });
    return req.on('end', () => {
      if (req.headers['x-docta-token'] !== TOKEN) {
        return json(res, 403, { error: 'write authorization failed' });
      }
      const payload = JSON.parse(raw);
      lastPayload = payload;
      posts += 1;
      const lines = {};
      const reviewState = {};
      for (const [pageNr, page] of Object.entries(payload.pages || {})) {
        lines[pageNr] = Object.fromEntries((page.lines || []).map(line =>
          [line.id, line.corrected]));
        reviewState[pageNr] = {
          status: page.status == null && page.lines?.length
            ? 'gesichtet' : page.status,
          reason: page.lines?.length ? 'text-corrected' : null,
          reviewer: payload.reviewer, date: page.date,
        };
      }
      saved = { revision: `${revision}-${posts}`, lines, reviewState };
      return json(res, 200, {
        saved: true, revision: saved.revision, document: documentPayload(),
      });
    });
  }

  const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '') || 'index.html';
  const file = path.resolve(ROOT, rel);
  if (!file.startsWith(ROOT + path.sep)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (error, body) => {
    if (error) { res.writeHead(404); return res.end('not found'); }
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(file)] || 'application/octet-stream',
      // createLocalEditor recognises the local capability from this header.
      ...(staticHost ? {} : { Server: 'DoCTALocalEditor/1' }),
    });
    res.end(body);
  });
});

const failures = [];
const checks = [];
const check = (condition, message) => {
  checks.push(message);
  if (!condition) failures.push(message);
};
const visible = async (page, selector) => page.locator(selector).isVisible().catch(() => false);

await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
BASE = `http://127.0.0.1:${server.address().port}/`;
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, acceptDownloads: false });
await useCachedFacsimiles(context);
await context.addInitScript(() => {
  window.__viewerFitCalls = 0;
  const timer = setInterval(() => {
    const proto = window.OpenSeadragon?.Viewport?.prototype;
    if (!proto || proto.__viewerUiWrapped) return;
    const goHome = proto.goHome;
    proto.goHome = function(...args) {
      window.__viewerFitCalls += 1;
      window.__viewerViewport = this;
      return goHome.apply(this, args);
    };
    proto.__viewerUiWrapped = true;
    clearInterval(timer);
  }, 0);
});
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });

try {
  await page.goto(`${BASE}viewer.html?doc=${DOC_ID}&page=1`, { waitUntil: 'networkidle' });
  await page.locator('.transcription__line[data-line-id]').first().waitFor();
  const strings = await page.evaluate(async () => {
    const { PROVENANCE, DRAFT_BADGE } = await import('./js/strings.js');
    return { PROVENANCE, DRAFT_BADGE };
  });
  check(await page.locator('[data-testid="readonly-hint"]').isHidden(),
    'the local working edition shows no read-only hint');
  // The expected wording is computed from the shipped strings in the page.
  const label = (key, ...args) => page.evaluate(async ([name, values]) => {
    const { PROVENANCE } = await import('./js/strings.js');
    const value = PROVENANCE[name];
    return typeof value === 'function' ? value(...values) : value;
  }, [key, args]);
  const sameRow = target => target.evaluate(() => {
    const boxes = ['#text-view-title', '#doc-provenance', '#btn-review', '#btn-more']
      .map(selector => document.querySelector(selector).getBoundingClientRect());
    return Math.max(...boxes.map(box => box.top)) < Math.min(...boxes.map(box => box.bottom));
  });
  const pill = page.locator('#doc-provenance');
  check(await pill.getAttribute('data-provenance') === 'corrected' &&
    (await pill.innerText()).trim() === await label('inventariaCorrected') &&
    await page.locator('#doc-edition-link').isVisible() &&
    (await page.locator('#doc-edition-link').getAttribute('href')).startsWith('http'),
  'an Inventaria-corrected page names Inventaria in the status pill and keeps the edition link visible');
  check(await sameRow(page), 'title, status pill and actions share one header row at 1280 px');
  check(await page.locator('#page-provenance, #draft-badge, #doc-meta').count() === 0,
    'the former meta strip, page provenance row and separate draft badge are gone');

  await pill.click();
  const details = page.locator('#text-status-details');
  check(await details.isVisible() && await pill.getAttribute('aria-expanded') === 'true',
    'the status pill opens its details surface by click');
  check((await details.innerText()).includes('Inventaria'),
    'the details surface names the text source');
  await pill.click();
  check(await details.isHidden() && await pill.getAttribute('aria-expanded') === 'false',
    'a second click on the pill closes the details surface');
  await pill.focus();
  await page.keyboard.press('Enter');
  check(await details.isVisible(), 'the status pill opens its details surface from the keyboard');
  await page.keyboard.press('Escape');
  check(await details.isHidden() && await pill.evaluate(el => el === document.activeElement) &&
    await pill.getAttribute('aria-expanded') === 'false',
  'Escape closes the details surface and returns focus to the pill');

  const teiRaces = await page.evaluate(async () => {
    const { createTeiView } = await import('./js/viewer-render.js');
    const originalFetch = window.fetch;
    const outcomes = [];
    try {
      for (const fails of [false, true]) {
        let settle;
        window.fetch = () => new Promise((resolve, reject) => {
          settle = () => fails ? reject(new Error('old request failed'))
            : resolve({ ok: true, text: async () => '<TEI>old output</TEI>' });
        });
        const container = document.createElement('div');
        const view = createTeiView(container, { getViewMode: () => 'tei', onRendered() {} });
        const pending = view.render('test');
        view.invalidate();
        settle();
        await pending;
        const remainsInvalidated = view.cached('test') === undefined;
        window.fetch = async () => ({ ok: true, text: async () => '<TEI>rebuilt output</TEI>' });
        await view.render('test');
        outcomes.push({ fails, remainsInvalidated,
          showsRebuilt: container.textContent === '<TEI>rebuilt output</TEI>' });
      }
    } finally { window.fetch = originalFetch; }
    return outcomes;
  });
  for (const outcome of teiRaces) {
    check(outcome.remainsInvalidated && outcome.showsRebuilt,
      `a delayed TEI ${outcome.fails ? 'failure' : 'success'} cannot repopulate an invalidated edition cache`);
  }

  check(await page.locator('#btn-review-save').isDisabled(),
    'local save is disabled before a draft exists');
  check(posts === 0, 'opening a local document performs no review write');
  check(await page.locator('.entity, [data-ent-key], #btn-entities, #entities-dialog').count() === 0,
    'viewer contains no machine annotation marks or controls');
  check(await page.locator('#btn-tags, #tags-dialog, #tag-editor').count() === 0,
    'viewer contains no obsolete tag editing controls');
  await page.locator('#transcription-container').focus();
  await page.keyboard.press('Shift+ArrowRight');
  const selectionPage = await page.locator('#page-input').inputValue();
  check(selectionPage === '1', 'Shift+ArrowRight preserves the source page for native text selection');
  if (selectionPage !== '1') await page.locator('#btn-prev-page').click();

  const expectedSource = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'sources.json'), 'utf8'))
    .find(source => source.transkribus_docs?.some(doc => doc.doc_id === DOC_ID));
  check((await page.locator('#source-title').textContent()).includes(expectedSource.titel),
    'source title comes from the 11328300 source fixture');
  check((await page.locator('#source-shelfmark').textContent()).includes(expectedSource.signatur),
    'source shelfmark comes from the 11328300 source fixture');
  check((await page.locator('#source-date').textContent()).includes(String(expectedSource.datierung.start)),
    'source date comes from the 11328300 source fixture');

  for (const [button, dialog, label] of [
    ['#btn-source-details', '#source-dialog', 'source'],
    ['#btn-more', '#viewer-more', 'more'],
  ]) {
    await page.locator(button).focus();
    await page.keyboard.press('Enter');
    await page.locator(dialog).waitFor({ state: 'visible' });
    check(await visible(page, dialog), `${label} surface opens from the keyboard`);
    await page.keyboard.press('Escape');
    await page.locator(dialog).waitFor({ state: 'hidden' });
    await page.waitForFunction(selector => document.querySelector(selector) === document.activeElement, button);
    check(!await visible(page, dialog), `${label} surface closes with Escape`);
    check(await page.locator(button).evaluate(el => el === document.activeElement),
      `${label} surface returns focus to its trigger`);
  }

  check(!await visible(page, '#btn-view-synopsis'),
    'synopsis return control is hidden while synopsis is active');
  await page.click('#btn-more');
  await page.click('#btn-view-reading');
  check(await visible(page, '#btn-view-synopsis'),
    'synopsis return control is visible outside synopsis');
  await page.click('#btn-view-synopsis');

  check((await page.locator('#btn-zoom-fit').innerText()).trim().length > 0,
    'fit control carries a visible label');
  check(await page.locator('#osd-viewer canvas').count() > 0,
    'initial synopsis renders the complete-image OpenSeadragon surface');
  await page.waitForFunction(() => window.__viewerFitCalls > 0);
  const initialFitCalls = await page.evaluate(() => window.__viewerFitCalls);
  const imageFitsViewport = () => page.evaluate(() => {
    const viewport = window.__viewerViewport;
    const image = viewport?.viewer?.world?.getItemAt(0);
    if (!viewport || !image) return false;
    const visible = viewport.getBounds(true);
    const bounds = image.getBounds();
    const epsilon = 0.000001;
    return visible.x <= bounds.x + epsilon && visible.y <= bounds.y + epsilon &&
      visible.x + visible.width >= bounds.x + bounds.width - epsilon &&
      visible.y + visible.height >= bounds.y + bounds.height - epsilon;
  });
  const waitForImageFit = async () => {
    for (let attempt = 0; attempt < 20; attempt++) {
      if (await imageFitsViewport()) return true;
      await page.waitForTimeout(50);
    }
    return false;
  };
  check(await waitForImageFit(), 'initial viewport contains the complete image');
  check((await page.locator('#image-focus').inputValue()) === 'spread',
    'initial image opens in whole-page mode');
  await page.click('#btn-next-page');
  await page.waitForFunction(previous => window.__viewerFitCalls > previous, initialFitCalls);
  check(await page.locator('#osd-viewer canvas').count() > 0,
    'page change retains the complete-image OpenSeadragon surface');
  check(await waitForImageFit(), 'viewport contains the complete image after page change');
  check((await page.locator('#image-focus').inputValue()) === 'spread',
    'page change resets the image to whole-page mode');
  await page.click('#btn-zoom-in');
  await page.click('#btn-zoom-fit');
  await page.waitForTimeout(1400);
  check(await waitForImageFit(), 'the whole-page control restores the complete image after zooming');

  await page.setViewportSize({ width: 640, height: 400 });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  check(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1),
    'narrow 200 percent equivalent viewport has no horizontal document overflow');
  check(await visible(page, '#btn-source-details') && await visible(page, '#btn-more'),
    'details controls remain reachable in the narrow 200 percent equivalent viewport');
  await page.evaluate(() => { document.documentElement.style.zoom = ''; });
  await page.setViewportSize({ width: 1280, height: 800 });

  await page.click('#btn-review');
  check(await page.locator('#review-options, #btn-review-timer, #btn-status-approved').count() === 0,
    'the editor contains no approval or timing controls');
  await page.fill('#review-initials', 'QA');
  const first = page.locator('.transcription__line[data-line-id][data-original]').first();
  const original = await first.getAttribute('data-original');
  const corrected = `${original} [QA]`;
  await first.click();
  await first.locator('.transcription__line-edit').fill(`${original} [cancelled]`);
  await page.keyboard.press('Escape');
  check(await first.locator('.transcription__line-text').textContent() === original &&
    await page.evaluate(id => localStorage.getItem(`docta-review-${id}`) === null, DOC_ID),
  'Escape cancels a focused correction without creating a browser draft');
  await first.click();
  await first.locator('.transcription__line-edit').fill(corrected);
  await page.screenshot({ path: path.join(output, 'focused-correction-wide.png'), fullPage: false });
  await page.setViewportSize({ width: 640, height: 400 });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  await first.locator('.transcription__line-edit').scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(output, 'focused-correction-narrow.png'), fullPage: false });
  await page.evaluate(() => { document.documentElement.style.zoom = ''; });
  await page.setViewportSize({ width: 1280, height: 800 });
  const protectedInput = await page.evaluate((id) => {
    const event = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(event);
    return { prevented: event.defaultPrevented,
      draft: JSON.parse(localStorage.getItem(`docta-review-${id}`)) };
  }, DOC_ID);
  check(protectedInput.prevented && Object.values(protectedInput.draft?.pages || {})
    .some(value => value.lines.some(line => line.corrected === corrected)),
  'unloading with a focused changed correction protects and persists its browser draft without blur or Enter');
  const persistedDraft = await page.evaluate(id => localStorage.getItem(`docta-review-${id}`), DOC_ID);
  await first.click();
  await first.locator('.transcription__line-edit').fill(`${original} [cancelled replacement]`);
  await page.keyboard.press('Escape');
  check(await first.locator('.transcription__line-text').textContent() === corrected &&
    await page.evaluate(id => localStorage.getItem(`docta-review-${id}`), DOC_ID) === persistedDraft,
  'Escape retains an existing browser correction and its persisted draft');
  check(await pill.getAttribute('data-state') === 'dirty' &&
    (await pill.innerText()).trim() === strings.DRAFT_BADGE &&
    await pill.isVisible(),
  'a correction switches the status pill to the unsaved state');
  check((await page.locator('#btn-review-save').textContent()).trim().length > 0,
    'local save control has an explicit label');
  const saveResponse = page.waitForResponse(response =>
    response.url() === `${BASE}api/review` && response.request().method() === 'POST');
  await page.click('#btn-review-save');
  check((await saveResponse).ok(), 'in-memory review API accepted the save');
  check(posts === 1, 'review save used the in-memory API exactly once');
  check(lastPayload.effort == null && Object.values(lastPayload.pages).every(item => item.status === null),
    'new corrections carry neither effort measurements nor page approval decisions');
  check(await page.locator('#review-hint').getAttribute('data-state') === 'saved',
    'successful local save is confirmed in the review bar');
  await page.reload({ waitUntil: 'networkidle' });
  await page.locator('.transcription__line[data-line-id]').first().waitFor();
  await page.waitForFunction(() => document.getElementById('doc-provenance').dataset.pageState === 'counted');
  check((await pill.innerText()).trim() === await label('changedInDocta', await label('inventariaCorrected'), 1) &&
    await pill.getAttribute('data-state') === 'corrected',
  'the saved correction qualifies the page attribution with its counted line');
  await pill.click();
  check((await details.innerText()).includes('not a scholarly approval') &&
    (await details.innerText()).includes('QA'),
  'the details name the corrector and state that a correction is no scholarly approval');
  await page.keyboard.press('Escape');
  check((await page.locator('.transcription__line[data-line-id][data-original]').first().textContent()).includes(corrected),
    'saved correction survives reload from the in-memory API');

  const staticContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, acceptDownloads: true,
    extraHTTPHeaders: { 'x-docta-static': '1' } });
  await useCachedFacsimiles(staticContext);
  const staticPage = await staticContext.newPage();
  await staticPage.goto(`${BASE}viewer.html?doc=${DOC_ID}&page=1`, { waitUntil: 'networkidle' });
  await staticPage.locator('.transcription__line[data-line-id]').first().waitFor();
  const hint = staticPage.locator('[data-testid="readonly-hint"]');
  check(await hint.isVisible() && (await hint.textContent()).includes('local working edition'),
    'static mode states persistently that annotating and saving require the local working edition');
  check(await hint.getByRole('link').getAttribute('href') === 'guide.html#launch',
    'the read-only hint links to the guide section on starting the local working edition');
  check(await staticPage.locator('#btn-annotate-selection, #btn-registry').evaluateAll(items => items.every(item => item.hidden)),
    'static mode offers no annotation controls');
  await staticPage.click('#btn-review');
  check(!await visible(staticPage, '#btn-review-save'),
    'static mode keeps the local save control hidden while editing');
  await staticPage.click('#btn-review');
  const vlmDoc = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'pipeline', 'register_summary.json'), 'utf8'))
    .documents.find(doc => doc.transcription_source === 'vlm');
  await staticPage.goto(`${BASE}viewer.html?doc=${vlmDoc.docId}&page=1`, { waitUntil: 'networkidle' });
  const chip = staticPage.locator('#doc-provenance');
  await chip.waitFor();
  check(await chip.getAttribute('data-provenance') === 'machine-unrevised' &&
    await chip.getAttribute('data-state') === 'machine' &&
    (await chip.innerText()).trim() === strings.PROVENANCE.vlm &&
    strings.PROVENANCE.vlm.toLowerCase().includes('unrevised'),
  'an uncorrected DoCTA machine transcription states unrevised in the visible pill text');
  await staticPage.click('#btn-more');
  check(await visible(staticPage, '#btn-review-export'),
    'static mode exposes review export in the more dialog');
  check(!await visible(staticPage, '#btn-review-save'),
    'static mode does not expose the local save control');
  await staticPage.keyboard.press('Escape');

  const summary = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'pipeline', 'register_summary.json'), 'utf8')).documents;
  const staticLabel = key => staticPage.evaluate(async name => (await import('./js/strings.js')).PROVENANCE[name], key);
  const unrecorded = summary.find(doc => doc.transcription_source === 'transkribus' && !doc.done_pages);
  await staticPage.goto(`${BASE}viewer.html?doc=${unrecorded.docId}&page=1`, { waitUntil: 'networkidle' });
  await chip.waitFor();
  check(await chip.getAttribute('data-provenance') === 'correction-unrecorded' &&
    (await chip.innerText()).trim() === await staticLabel('transkribusUnrecorded'),
  'a Transkribus document without done pages states that correction is not recorded');

  // A DoCTA transcription covering part of its source names the coverage only in the details.
  const partial = summary.filter(doc => doc.transcription_source === 'vlm').find(doc => {
    const file = path.join(ROOT, 'data', 'pipeline', 'transcriptions', `${doc.docId}.json`);
    const prov = fs.existsSync(file) && JSON.parse(fs.readFileSync(file, 'utf8')).provenance;
    return prov && prov.pagesTranscribed < prov.pagesInDocument;
  });
  check(Boolean(partial), 'the corpus holds a partly transcribed DoCTA document for the coverage check');
  if (partial) {
    await staticPage.goto(`${BASE}viewer.html?doc=${partial.docId}&page=1`, { waitUntil: 'networkidle' });
    await chip.waitFor();
    const outside = await staticPage.evaluate(() => {
      const clone = document.body.cloneNode(true);
      clone.querySelector('#text-status-details')?.remove();
      return clone.textContent.includes('pages transcribed');
    });
    check(!outside, 'no page coverage text appears outside the status details');
    await chip.click();
    check((await staticPage.locator('#text-status-details').innerText()).includes('pages transcribed'),
      'the status details state the page coverage');
    check((await chip.innerText()).toLowerCase().includes('unrevised'),
      'a DoCTA machine transcription keeps the word unrevised in the pill');
    await staticPage.keyboard.press('Escape');
    await staticPage.setViewportSize({ width: 640, height: 900 });
    check(await sameRow(staticPage), 'title, status pill and actions share one header row at 640 px');
    check(await staticPage.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1),
      'the narrow header causes no horizontal document overflow');
    check(await staticPage.locator('#btn-more').evaluate(button =>
      button.querySelector('.action-label').getBoundingClientRect().width <= 1 && button.title.length > 0),
    'narrow actions are icon-only and keep a tooltip');
  }
  await staticContext.close();
} finally {
  await context.close();
  await browser.close();
  await new Promise(resolve => server.close(resolve));
}

check(errors.length === 0, `viewer emitted no JavaScript errors${errors.length ? `: ${errors.join(' | ')}` : ''}`);
console.log(JSON.stringify({ checks: checks.length, failures, posts }, null, 2));
if (failures.length) process.exitCode = 1;
