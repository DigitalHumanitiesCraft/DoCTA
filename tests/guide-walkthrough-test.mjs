// Exercise the real loopback write service against copies of corpus fixtures.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'docta-guide-browser-'));
const DOC_ID = 11328300;
const DOCS = path.join(REPO, 'docs');
const guardedDirectories = ['pipeline/pages', 'pipeline/annotations', 'pipeline/reviews', 'pipeline/registry', 'pipeline/tags', 'docs/data/tei', 'docs/data/entities', 'docs/data/transcriptions'];
const storedFiles = directory => fs.existsSync(directory) ? fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => entry.isDirectory() ? storedFiles(path.join(directory, entry.name)) : [path.join(directory, entry.name)]) : [];
const protectedPaths = [...new Set([...guardedDirectories.flatMap(relative => storedFiles(path.join(REPO, relative))),
  path.join(REPO, 'pipeline/pages', `${DOC_ID}.json`),
  path.join(DOCS, 'data/transcriptions', `${DOC_ID}.json`),
  path.join(DOCS, 'data/entities', `${DOC_ID}.json`),
])];
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const before = protectedPaths.map(digest);
function copy(relative) {
  const destination = path.join(ROOT, relative);
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.cpSync(path.join(REPO, relative), destination, { recursive: true });
}
for (const item of fs.readdirSync(DOCS, { withFileTypes: true })) {
  if (item.name !== 'data' && item.name !== 'knowledge') copy(`docs/${item.name}`);
}
for (const item of fs.readdirSync(path.join(DOCS, 'data'), { withFileTypes: true })) {
  if (item.isFile()) copy(`docs/data/${item.name}`);
}
for (const relative of [
  `docs/data/transcriptions/${DOC_ID}.json`, `docs/data/entities/${DOC_ID}.json`,
  'docs/data/pipeline/register_summary.json', `pipeline/pages/${DOC_ID}.json`,
]) copy(relative);

// Every writable handler path is rooted in the copy, including paths unused by
// the current checks. br.DATA also keeps transcription reads inside the copy.
const bootstrap = `
import sys
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0, sys.argv[1])
import local_editor as le
root = Path(sys.argv[2])
le.br.DATA = root / 'docs' / 'data'
handler = le.EditorHandler
handler.docs_dir = root / 'docs'
handler.data_dir = root / 'docs' / 'data'
handler.register_dir = root / 'pipeline' / 'pages'
handler.review_dir = root / 'pipeline' / 'reviews'
handler.annotation_dir = root / 'pipeline' / 'annotations'
handler.tag_dir = root / 'pipeline' / 'tags'
handler.token = 'isolated-browser-fixture'
server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
print(server.server_port, flush=True)
server.serve_forever()
`;
const venv = path.join(REPO, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const processHandle = spawn(process.env.DOCTA_TEST_PYTHON || (fs.existsSync(venv) ? venv : 'python'),
  ['-u', '-c', bootstrap, path.join(REPO, 'pipeline'), ROOT], { cwd: ROOT, windowsHide: true });
let serverLog = '';
processHandle.stderr.on('data', chunk => { serverLog += chunk; });
const port = await new Promise((resolve, reject) => {
  const timeout = setTimeout(() => reject(new Error(`Backend did not start: ${serverLog}`)), 20000);
  processHandle.once('error', reject);
  processHandle.once('exit', code => reject(new Error(`Backend exited ${code}: ${serverLog}`)));
  processHandle.stdout.once('data', chunk => {
    clearTimeout(timeout);
    resolve(Number(String(chunk).trim()));
  });
});
const BASE = `http://127.0.0.1:${port}`;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
const machineRequests = [];
page.on('request', request => { if (/\/data\/entities\/|\/api\/annotations(?:\/|$)/.test(request.url())) machineRequests.push(request.url()); });
page.on('pageerror', error => errors.push(String(error)));
const checks = [];
const output = path.join(REPO, 'output', 'guide-check');
fs.mkdirSync(output, { recursive: true });
function check(condition, label) {
  assert.ok(condition, label);
  checks.push(label);
}
async function state() {
  const response = await page.request.get(`${BASE}/api/registry`);
  assert.equal(response.status(), 200);
  return response.json();
}
async function save(form) {
  const [result] = await Promise.all([
    page.waitForResponse(response => response.url() === `${BASE}/api/registry` && response.request().method() === 'POST'),
    form.locator('[type="submit"]').click(),
  ]);
  assert.equal(result.status(), 200, await result.text());
  return result.json();
}
async function workspaceScreenshot(name, entity) {
  const clip = await page.evaluate(lineId => {
    const popup = document.getElementById('annotation-workspace').getBoundingClientRect();
    const source = [...document.querySelectorAll('.transcription__line[data-line-id]')]
      .find(line => line.dataset.lineId === lineId).getBoundingClientRect();
    const left = Math.max(0, Math.min(popup.left, source.left) - 12);
    const top = Math.max(0, Math.min(popup.top, source.top) - 12);
    const right = Math.min(innerWidth, Math.max(popup.right, source.right) + 12);
    const bottom = Math.min(innerHeight, Math.max(popup.bottom, source.bottom) + 12);
    return { x: left + scrollX, y: top + scrollY, width: right - left, height: bottom - top };
  }, entity.lineId);
  await page.screenshot({ path: path.join(output, name), clip });
}
async function selectText(entity, kind = 'person', route = 'toolbar') {
  await page.locator(`.transcription__line[data-line-id="${entity.lineId}"]`).scrollIntoViewIfNeeded();
  await page.locator(`.transcription__line[data-line-id="${entity.lineId}"]`).evaluate((line, text) => {
    const root = line.querySelector('.transcription__line-text');
    const full = root.textContent;
    const start = full.indexOf(text);
    if (start < 0) throw new Error(`Fixture span is missing: ${text}`);
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    let offset = 0;
    let node;
    while ((node = walker.nextNode())) {
      const end = offset + node.textContent.length;
      if (start >= offset && start < end) range.setStart(node, start - offset);
      if (start + text.length > offset && start + text.length <= end) {
        range.setEnd(node, start + text.length - offset);
        break;
      }
      offset = end;
    }
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    document.dispatchEvent(new Event('selectionchange'));
    line.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
  }, entity.text);
  if (route === 'keyboard') await page.keyboard.press('Alt+a');
  if (route === 'contextmenu') {
    const box = await page.evaluate(() => {
      const rect = window.getSelection().getRangeAt(0).getBoundingClientRect();
      return { x: rect.x + Math.min(rect.width / 2, 8), y: rect.y + rect.height / 2 };
    });
    await page.mouse.click(box.x, box.y, { button: 'right' });
  }
  check(await page.locator('#annotation-selection-toolbar [data-kind]').count() === 4,
    'selection toolbar exposes the four manual annotation categories');
  await page.locator('#annotation-workspace').waitFor();
  await page.locator('#annotation-workspace').evaluate(element => { window.__selectionWorkspace = element; });
  if (kind === 'person') {
    await page.screenshot({ path: path.join(output, 'selection-toolbar.png'), fullPage: true });
    await workspaceScreenshot('selection.png', entity);
  }
  await page.locator(`#annotation-selection-toolbar [data-kind="${kind}"]`).click();
  await page.locator('#mention-dialog').waitFor();
  check(await page.locator('#annotation-workspace').evaluate(element => element === window.__selectionWorkspace) &&
    await page.locator('[popover]:popover-open').count() === 1,
  'category selection reuses the single physical annotation workspace');
  check(await page.locator('#annotation-workspace-title').textContent() === entity.text,
    `${route} category selection preserves the exact ${kind} source span`);
  check(await page.locator('#mention-dialog').evaluate(element => !element.hasAttribute('popover') && !!element.closest('#annotation-workspace')),
    `${kind} editor is a child of the shared workspace without its own popover`);
}
async function screenshot(name, narrow = false) {
  await page.setViewportSize(narrow ? { width: 640, height: 800 } : { width: 1280, height: 900 });
  await page.evaluate(zoom => { document.documentElement.style.zoom = zoom; }, narrow ? '2' : '');
  check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${name} has no horizontal overflow`);
  await page.screenshot({ path: path.join(output, name), fullPage: false });
}
async function saveCorrection(text, lineId) {
  if (await page.locator('#btn-review').getAttribute('aria-pressed') !== 'true') await page.locator('#btn-review').click();
  await page.locator('#review-initials').fill('QA');
  const line = page.locator(`.transcription__line[data-line-id="${lineId}"]`);
  await line.click();
  await line.locator('.transcription__line-edit').fill(text);
  await page.keyboard.press('Enter');
  const response = page.waitForResponse(result => result.url() === `${BASE}/api/review` && result.request().method() === 'POST');
  await page.locator('#btn-review-save').click();
  assert.equal((await response).status(), 200);
  await page.reload({ waitUntil: 'networkidle' });
  check(await page.locator(`.transcription__line[data-line-id="${lineId}"] .transcription__line-text`).textContent() === text,
    'correction persists through real backend and reload');
}
try {
  const staticPage = await browser.newPage();
  await staticPage.route('**/guide.html*', async route => {
    const response = await route.fetch();
    const headers = response.headers();
    delete headers.server;
    await route.fulfill({ response, headers });
  });
  await staticPage.goto(`${BASE}/guide.html`, { waitUntil: 'networkidle' });
  check(await staticPage.locator('#guide-online').isVisible() && await staticPage.locator('#guide-local').isHidden(),
    'static guide shows online instructions without a visible local example link');
  await staticPage.close();
  await page.goto(`${BASE}/guide.html`, { waitUntil: 'networkidle' });
  check(await page.locator('#guide-local').isVisible() && await page.locator('#guide-online').isHidden(),
    'real local guide shows the working example instead of online setup guidance');
  check(await page.locator('[aria-current="page"]').textContent() === 'Anleitung', 'guide navigation identifies current page');
  for (const href of await page.locator('.guide-sections a').evaluateAll(links => links.map(link => link.getAttribute('href')))) {
    check(await page.locator(href).count() === 1, `guide section ${href} exists`);
  }
  await page.locator('.guide-sections a[href="#exercise"]').focus();
  await page.keyboard.press('Enter');
  check(new URL(page.url()).hash === '#exercise', 'guide section link works with keyboard');
  await page.evaluate(() => window.scrollTo(0, 0));
  await screenshot('guide.png');
  await screenshot('guide-narrow.png', true);
  await page.locator('.navbar-toggler').focus();
  await page.keyboard.press('Enter');
  await page.locator('#main-nav a[aria-current="page"]').waitFor({ state: 'visible' });
  check(await page.locator('#main-nav a[aria-current="page"]').isVisible(), 'narrow guide navigation opens with keyboard');
  await page.evaluate(() => { document.documentElement.style.zoom = ''; });
  await page.setViewportSize({ width: 1280, height: 900 });
  const example = page.locator('#guide-local a');
  check(new URL(await example.getAttribute('href'), BASE).origin === BASE, 'local example preserves editor origin');
  await example.click();
  await page.locator('.transcription__line[data-line-id]').first().waitFor();
  check(new URL(page.url()).searchParams.get('doc') === String(DOC_ID) && new URL(page.url()).searchParams.get('page') === '1',
    'guide opens Thaur on page one');
  const line = page.locator('.transcription__line[data-line-id]').filter({ hasText: 'Hannsen Ramung' });
  const person = { lineId: await line.getAttribute('data-line-id'), text: 'Hannsen Ramung' };
  const originalText = await line.locator('.transcription__line-text').textContent();
  check(originalText.includes('durch Hannsen Ramung,'), 'exact documented source phrase exists');
  await selectText(person);
  const mentionForm = page.locator('#mention-form');
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  await page.locator('#mention-new-entry').click();
  const entryForm = page.locator('#mention-entry-form');
  await entryForm.locator('[name="label"]').fill(person.text);
  check(await entryForm.locator('[name="reviewer"]').inputValue() === 'QA', 'initials carry into the new entry form');
  await save(entryForm);
  const entry = (await state()).entries.find(item => item.label === person.text);
  check(entry?.kind === 'person' && await mentionForm.locator('[name="entryId"]').inputValue() === entry.id,
    'saving raw source label creates and selects the person identity');
  await screenshot('annotation.png');
  await screenshot('annotation-narrow.png', true);
  const bounds = await page.locator('#annotation-workspace').evaluate(element => {
    const box = element.getBoundingClientRect();
    return { left: box.left, right: box.right, viewport: innerWidth };
  });
  check(bounds.left >= 0 && bounds.right <= bounds.viewport + 1, 'annotation stays inside narrow viewport at 200 percent');
  await save(mentionForm);
  const mention = (await state()).mentions.find(item => item.entryId === entry.id);
  check(mention?.quote === person.text, 'explicit second save persists exact source mention');
  await page.evaluate(() => { document.documentElement.style.zoom = ''; });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.reload({ waitUntil: 'networkidle' });
  check(await page.locator(`[data-mention-id="${mention.id}"]`).count() === 1, 'saved annotation is restored after reload');
  await page.locator('#main-nav').getByRole('link', { name: 'Index', exact: true }).click();
  await page.locator('#register-search').fill(person.text);
  await page.locator(`#register-results [data-entry-id="${entry.id}"]`).click();
  check(await page.locator('#register-entry-title').textContent() === person.text, 'Index search finds the manually chosen source label');
  check(new URL(await page.locator('.register-attestations a').first().getAttribute('href'), BASE).searchParams.get('mention') === mention.id,
    'Index backlink addresses the exact occurrence');
  await screenshot('index.png');
  await page.locator('.register-attestations a').first().click();
  await page.locator(`#annotation-workspace`).waitFor();
  check(await mentionForm.locator('[name="entryId"]').inputValue() === entry.id && await page.locator('#annotation-workspace-title').textContent() === person.text,
    'Index backlink opens the saved occurrence editor');
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  await page.locator('#mention-note summary').click();
  await mentionForm.locator('[name="note"]').fill('QA');
  await save(mentionForm);
  check((await state()).mentions.find(item => item.id === mention.id).note === 'QA', 'occurrence note edit persists');
  await page.locator(`[data-mention-id="${mention.id}"]`).click();
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  const removal = page.waitForResponse(response => response.url() === `${BASE}/api/registry` && response.request().method() === 'POST');
  await page.locator('#mention-remove').click();
  assert.equal((await removal).status(), 200);
  await page.reload({ waitUntil: 'networkidle' });
  const afterRemoval = await state();
  check(!afterRemoval.mentions.some(item => item.id === mention.id) && afterRemoval.entries.some(item => item.id === entry.id) &&
    afterRemoval.history.length >= 4, 'removing occurrence preserves identity and change history');
  check(await line.locator('.transcription__line-text').textContent() === originalText, 'removing annotation leaves source text intact');
  await saveCorrection(`${originalText} [QA]`, person.lineId);
  await saveCorrection(originalText, person.lineId);
  if (await page.locator('#btn-review').getAttribute('aria-pressed') === 'true') await page.locator('#btn-review').click();
  check(await page.locator('#btn-review').getAttribute('aria-pressed') === 'false', 'Bearbeiten switches off before further annotation');
  await selectText(person);
  check(await mentionForm.isVisible(), 'annotation selection works after correction and restoration');
  check(machineRequests.length === 0, 'walkthrough loads no machine annotation suggestions');
  check(errors.length === 0, `no JavaScript errors: ${errors.join(' | ')}`);
  const report = JSON.stringify({ checks: checks.length, results: checks }, null, 2);
  fs.writeFileSync(path.join(output, 'results.json'), report);
  console.log(report);
} finally {
  await browser.close();
  const serverClosed = new Promise(resolve => processHandle.once('close', resolve));
  processHandle.kill();
  await serverClosed;
  assert.deepEqual(protectedPaths.map(digest), before, 'live corpus files remain unchanged');
  assert.deepEqual([...new Set(guardedDirectories.flatMap(relative => storedFiles(path.join(REPO, relative))))].sort(), protectedPaths.sort(),
    'no real research files were created or removed');
  fs.writeFileSync(path.join(output, 'server.log'), serverLog);
  const resolvedRoot = fs.realpathSync(ROOT);
  assert.ok(path.basename(resolvedRoot).startsWith('docta-guide-browser-') && path.dirname(resolvedRoot) === fs.realpathSync(os.tmpdir()));
  fs.rmSync(resolvedRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}
