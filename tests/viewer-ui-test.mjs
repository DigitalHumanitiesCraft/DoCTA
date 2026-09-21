// Focused regression checks for the viewer's information hierarchy, dialogs,
// responsive layout and review persistence. The local editor API is emulated
// in memory, so this test never writes to the repository review register.
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = path.join(REPO, 'docs');
const DOC_ID = 11328300;
const PORT = 8736;
const BASE = `http://127.0.0.1:${PORT}/`;
const TOKEN = 'viewer-ui-test-token';
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
  if (url.pathname === '/api/session') {
    return json(res, 200, { write_enabled: true, token: TOKEN });
  }
  if (url.pathname === `/api/documents/${DOC_ID}`) {
    return json(res, 200, documentPayload());
  }
  if (url.pathname === `/api/annotations/${DOC_ID}`) {
    return json(res, 200, { revision, decisions: [] });
  }
  if (url.pathname === `/api/tags/${DOC_ID}`) {
    return json(res, 200, { revision, tags: [] });
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
      ...(url.searchParams.has('static') ? {} : { Server: 'DoCTALocalEditor/1' }),
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

await new Promise(resolve => server.listen(PORT, '127.0.0.1', resolve));
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, acceptDownloads: false });
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

  check(await page.locator('#btn-review-save').isDisabled(),
    'local save is disabled before a draft exists');
  check(posts === 0, 'opening a local document performs no review write');

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
    ['#btn-tags', '#tags-dialog', 'tags'],
    ['#btn-entities', '#entities-dialog', 'entities'],
  ]) {
    await page.locator(button).focus();
    await page.keyboard.press('Enter');
    check(await visible(page, `${dialog}[open]`), `${label} dialog opens from the keyboard`);
    if (label === 'tags') check(await visible(page, '#tag-editor form'), 'tag form is accessible inside its dialog');
    if (label === 'entities') check(await visible(page, '#annotation-editor form'), 'annotation form is accessible inside its dialog');
    await page.keyboard.press('Escape');
    check(!await visible(page, `${dialog}[open]`), `${label} dialog closes with Escape`);
    check(await page.locator(button).evaluate(el => el === document.activeElement),
      `${label} dialog returns focus to its trigger`);
  }

  check(!await visible(page, '#btn-view-synopsis'),
    'synopsis return control is hidden while synopsis is active');
  await page.click('#btn-more');
  await page.click('#btn-view-reading');
  check(await visible(page, '#btn-view-synopsis'),
    'synopsis return control is visible outside synopsis');
  await page.click('#btn-view-synopsis');

  check((await page.locator('#btn-zoom-fit').innerText()).trim() === 'Ganze Seite',
    'fit control is labelled Ganze Seite');
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
  check(await waitForImageFit(), 'Ganze Seite restores the complete image after zooming');

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
  await first.locator('.transcription__line-edit').fill(corrected);
  await page.keyboard.press('Enter');
  check((await page.locator('#draft-badge').textContent()).trim() === 'Ungespeicherte Änderungen' &&
    await page.locator('#draft-badge').isVisible(),
  'a correction has a visible dirty-state indicator');
  check((await page.locator('#btn-review-save').textContent()).trim().length > 0,
    'local save control has an explicit label');
  const saveResponse = page.waitForResponse(response =>
    response.url() === `${BASE}api/review` && response.request().method() === 'POST');
  await page.click('#btn-review-save');
  check((await saveResponse).ok(), 'in-memory review API accepted the save');
  check(posts === 1, 'review save used the in-memory API exactly once');
  check(lastPayload.effort == null && Object.values(lastPayload.pages).every(item => item.status === null),
    'new corrections carry neither effort measurements nor page approval decisions');
  check((await page.locator('#review-hint').textContent()).includes('lokal gespeichert'),
    'successful local save is confirmed in the review bar');
  await page.reload({ waitUntil: 'networkidle' });
  await page.locator('.transcription__line[data-line-id]').first().waitFor();
  check(await page.locator('#review-chip').textContent() === 'Lokal korrigiert',
    'the saved correction is described without implying scholarly approval');
  check((await page.locator('.transcription__line[data-line-id][data-original]').first().textContent()).includes(corrected),
    'saved correction survives reload from the in-memory API');

  const staticContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, acceptDownloads: true });
  const staticPage = await staticContext.newPage();
  await staticPage.goto(`${BASE}viewer.html?static=1&doc=${DOC_ID}&page=1`, { waitUntil: 'networkidle' });
  await staticPage.locator('.transcription__line[data-line-id]').first().waitFor();
  await staticPage.click('#btn-more');
  check(await visible(staticPage, '#btn-review-export'),
    'static mode exposes review export in the more dialog');
  check(!await visible(staticPage, '#btn-review-save'),
    'static mode does not expose the local save control');
  await staticContext.close();
} finally {
  await context.close();
  await browser.close();
  await new Promise(resolve => server.close(resolve));
}

check(errors.length === 0, `viewer emitted no JavaScript errors${errors.length ? `: ${errors.join(' | ')}` : ''}`);
console.log(JSON.stringify({ checks: checks.length, failures, posts }, null, 2));
if (failures.length) process.exitCode = 1;
