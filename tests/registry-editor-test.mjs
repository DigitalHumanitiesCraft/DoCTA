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
const ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'docta-registry-browser-'));
const DOC_ID = 11328300;
const DOCS = path.join(REPO, 'docs');
const fixture = JSON.parse(fs.readFileSync(path.join(DOCS, 'data/entities', `${DOC_ID}.json`), 'utf8'));
const person = fixture.entities.find(entity => entity.type === 'person');
const term = fixture.entities.find(entity => entity.type === 'object');
const protectedPaths = [
  path.join(REPO, 'pipeline/pages', `${DOC_ID}.json`),
  path.join(DOCS, 'data/transcriptions', `${DOC_ID}.json`),
  path.join(DOCS, 'data/entities', `${DOC_ID}.json`),
];
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
const processHandle = spawn(fs.existsSync(venv) ? venv : 'python',
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
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
const checks = [];
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
async function openRegistry() {
  await page.locator('#btn-registry').click();
  await page.locator('#registry-dialog[open]').waitFor();
}
async function selectText(entity) {
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
  }, entity.text);
  await page.locator('#btn-annotate-selection').click();
  await page.locator('#mention-dialog[open]').waitFor();
}

try {
  await page.goto(`${BASE}/viewer.html?doc=${DOC_ID}&page=${person.pageNr}`, { waitUntil: 'networkidle' });
  await page.locator('.transcription__line[data-line-id]').first().waitFor();
  const initial = await state();
  check(initial.entries.length === 0 && initial.mentions.length === 0,
    'isolated registry starts empty and opening the viewer does not write');

  const repeated = fixture.entities.filter(entity => entity.type === 'person' &&
    fixture.entities.some(other => other.id !== entity.id && other.text === entity.text));
  check(repeated.length > 1, 'real fixture contains repeated same-name machine occurrences');
  for (const entity of repeated) {
    await page.goto(`${BASE}/viewer.html?doc=${DOC_ID}&page=${entity.pageNr}`, { waitUntil: 'networkidle' });
    const machineMark = page.locator(`.transcription__line[data-line-id="${entity.lineId}"] [data-ent-key="${entity.id}"]`);
    await machineMark.waitFor();
    await machineMark.focus();
    await page.keyboard.press('Enter');
    await page.locator('#entities-dialog[open]').waitFor();
    check(await page.locator('#annotation-editor [name="entity"]').inputValue() === entity.id,
      `same-name machine mark opens its own occurrence ${entity.id} on page ${entity.pageNr}`);
    await page.keyboard.press('Escape');
    check(await machineMark.evaluate(element => document.activeElement === element),
      `machine dialog restores focus to occurrence ${entity.id}`);
  }
  await page.goto(`${BASE}/viewer.html?doc=${DOC_ID}&page=${person.pageNr}`, { waitUntil: 'networkidle' });

  await page.locator('#btn-registry').focus();
  await page.keyboard.press('Enter');
  await page.locator('#registry-dialog[open]').waitFor();
  await page.keyboard.press('Escape');
  check(await page.locator('#btn-registry').evaluate(element => document.activeElement === element),
    'registry dialog opens by keyboard and Escape restores trigger focus');

  await openRegistry();
  const entryForm = page.locator('#registry-entry-form');
  for (const [kind, entity] of [['person', person], ['term', term]]) {
    await page.locator('#registry-new').click();
    await entryForm.locator('[name="kind"]').selectOption(kind);
    await entryForm.locator('[name="label"]').fill(entity.normalized);
    await entryForm.locator('[name="aliases"]').fill(entity.text);
    await entryForm.locator('[name="reviewer"]').fill('QA');
    await save(entryForm);
  }
  let registry = await state();
  const personEntry = registry.entries.find(entry => entry.kind === 'person');
  const termEntry = registry.entries.find(entry => entry.kind === 'term');
  check(personEntry.label === person.normalized && termEntry.label === term.normalized,
    'person and controlled term are persisted by the real backend');

  await page.locator('#registry-new').click();
  await entryForm.locator('[name="kind"]').selectOption('person');
  await entryForm.locator('[name="label"]').fill(person.normalized);
  await entryForm.locator('[name="reviewer"]').fill('QA');
  await save(entryForm);
  registry = await state();
  const sameNames = registry.entries.filter(entry => entry.kind === 'person' && entry.label === person.normalized);
  check(sameNames.length === 2 && new Set(sameNames.map(entry => entry.id)).size === 2,
    'two persons with the same name retain separate identities');
  const descriptions = await Promise.all(sameNames.map(entry =>
    page.locator(`[data-entry-id="${entry.id}"]`).textContent()));
  check(new Set(descriptions).size === 2,
    'same-name persons have visibly distinct descriptions through their aliases');
  await page.locator('#registry-new').click();
  await entryForm.locator('[name="label"]').fill(person.normalized);
  await entryForm.locator('[name="reviewer"]').fill('QA');
  await save(entryForm);
  const identicalDescriptions = (await state()).entries.filter(entry => entry.kind === 'person' && !entry.aliases.length);
  const identicalLabels = await Promise.all(identicalDescriptions.map(entry =>
    page.locator(`[data-entry-id="${entry.id}"]`).textContent()));
  check(identicalLabels.length === 2 && new Set(identicalLabels).size === 2,
    'identical person labels without aliases remain visibly distinguishable by identity');

  await entryForm.locator('[name="note"]').fill(term.text);
  await page.keyboard.press('Escape');
  check(await page.locator('#registry-dialog').isVisible() &&
    await entryForm.locator('[name="note"]').inputValue() === term.text,
  'Escape retains an unsaved entry draft inside its open dialog');
  await page.locator('#registry-dialog').getByRole('button', { name: 'Eingaben verwerfen', exact: true }).click();
  check(!await page.locator('#registry-dialog').isVisible(), 'explicit discard closes the dirty dialog');
  await openRegistry();
  check(await entryForm.locator('[name="note"]').inputValue() === '',
    'discard restores the persisted entry rather than retaining its unsaved note');
  await page.keyboard.press('Escape');

  await selectText(person);
  const mentionForm = page.locator('#mention-form');
  await mentionForm.locator('[name="kind"]').selectOption('person');
  await mentionForm.locator('[name="search"]').fill(person.text);
  // Alias lookup must expose the stable identity, even when labels coincide.
  check(await mentionForm.locator(`[name="entryId"] option[value="${personEntry.id}"]`).count() === 1,
    'the attested alias finds its existing register entry');
  await mentionForm.locator('[name="entryId"]').selectOption(personEntry.id);
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  await save(mentionForm);
  registry = await state();
  const mention = registry.mentions[0];
  check(mention.entryId === personEntry.id && mention.lineId === person.lineId &&
    mention.pageNr === person.pageNr && mention.quote === person.text,
  'alias autocomplete saves the selected exact line span against its stable person identity');

  await page.reload({ waitUntil: 'networkidle' });
  const mark = page.locator(`.transcription__line [data-mention-id="${mention.id}"]`);
  await mark.waitFor();
  await mark.focus();
  await page.keyboard.press('Enter');
  await page.locator('#mention-dialog[open]').waitFor();
  await mentionForm.locator('[name="note"]').fill(person.text);
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  await save(mentionForm);
  check((await state()).mentions.find(item => item.id === mention.id).note === person.text,
    'manual mention opens by keyboard and its edit survives a backend read');

  await openRegistry();
  await page.locator(`[data-entry-id="${personEntry.id}"]`).click();
  const href = await page.locator('#registry-mentions a').first().getAttribute('href');
  const target = new URL(href, BASE);
  check(target.searchParams.get('doc') === String(DOC_ID) && target.searchParams.get('page') === String(person.pageNr) &&
    target.searchParams.get('mention') === mention.id,
  'fundstelle points to the exact source document, page and mention');
  check((await page.locator('#registry-history').textContent()).includes('QA'),
    'entry detail exposes persisted change attribution');
  await page.keyboard.press('Escape');

  await page.goto(target.href, { waitUntil: 'networkidle' });
  await page.locator('#mention-dialog[open]').waitFor();
  check(await page.locator('#mention-quote').textContent() === person.text &&
    await mentionForm.locator('[name="entryId"]').inputValue() === personEntry.id,
  'following a fundstelle opens the persisted source span and correct identity');
  await page.keyboard.press('Escape');

  await page.setViewportSize({ width: 640, height: 500 });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  await openRegistry();
  await page.locator('#registry-search').fill(person.text);
  check(await page.locator(`[data-entry-id="${personEntry.id}"]`).isVisible(),
    'alias search remains functional in a narrow 200 percent viewport');
  await page.locator(`[data-entry-id="${personEntry.id}"]`).click();
  check(await entryForm.locator('[name="label"]').inputValue() === person.normalized,
    'entry form remains operable in a narrow 200 percent viewport');
  check(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1),
    'narrow 200 percent viewport has no horizontal document overflow');
  check(await page.locator('#registry-dialog').evaluate(element => element.scrollWidth <= element.clientWidth + 1),
    'registry dialog has no horizontal overflow at 200 percent');
  // Escape in a populated native search field first clears the query.
  await page.locator('#registry-dialog .viewer-dialog__header button').click();
  await page.evaluate(() => { document.documentElement.style.zoom = ''; });
  await page.setViewportSize({ width: 1280, height: 800 });

  await mark.click();
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  const removeResponse = page.waitForResponse(response => response.url() === `${BASE}/api/registry` &&
    response.request().method() === 'POST');
  await page.locator('#mention-remove').click();
  assert.equal((await removeResponse).status(), 200);
  await page.reload({ waitUntil: 'networkidle' });
  check(!(await state()).mentions.some(item => item.id === mention.id),
    'manual mention deletion persists across reload');

  await selectText(term);
  await mentionForm.locator('[name="kind"]').selectOption('term');
  await mentionForm.locator('[name="search"]').fill(term.text);
  await mentionForm.locator('[name="entryId"]').selectOption(termEntry.id);
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  await save(mentionForm);
  const termMention = (await state()).mentions.find(item => item.entryId === termEntry.id);
  check(termMention?.quote === term.text, 'an exact span can reference the controlled term register');

  const doc = await (await page.request.get(`${BASE}/api/documents/${DOC_ID}`)).json();
  const sourceLine = doc.pages.find(item => item.pageNr === term.pageNr).regions
    .flatMap(region => region.lines).find(line => line.id === term.lineId);
  const corrected = `${sourceLine.text} ${term.text}`;
  const reviewResponse = await page.request.post(`${BASE}/api/review`, {
    headers: { Origin: BASE, 'X-DoCTA-Token': 'isolated-browser-fixture' },
    data: { docId: DOC_ID, baseRevision: doc.revision, reviewer: 'QA', pages: {
      [term.pageNr]: { status: null, date: new Date().toISOString().slice(0, 10),
        lines: [{ id: sourceLine.id, original: sourceLine.text, corrected }] },
    }, effort: null },
  });
  assert.equal(reviewResponse.status(), 200, await reviewResponse.text());
  await page.reload({ waitUntil: 'networkidle' });
  check((await state()).mentions.find(item => item.id === termMention.id).stale,
    'a real transcription save invalidates the stored full-line source digest');
  check(await page.locator(`.transcription__line [data-mention-id="${termMention.id}"]`).count() === 0,
    'stale mention is not silently redrawn on changed text');
  await openRegistry();
  await page.locator(`[data-entry-id="${termEntry.id}"]`).click();
  check((await page.locator('#registry-mentions').textContent()).includes('Text geändert'),
    'the term fundstelle visibly identifies its changed source');
  await page.locator(`[data-edit-mention="${termMention.id}"]`).click();
  check(await mentionForm.locator('[type="submit"]').isHidden(),
    'stale mention cannot be silently resaved against the changed source');
  check((await page.locator('#mention-dialog [role="status"]').textContent()).includes('geändert'),
    'stale-source dialog explains why a new selection is required');
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');

  const staticPage = await browser.newPage();
  await staticPage.route('**/viewer.html*', async route => {
    const response = await route.fetch();
    const headers = response.headers();
    delete headers.server;
    await route.fulfill({ response, headers });
  });
  await staticPage.goto(`${BASE}/viewer.html?doc=${DOC_ID}&page=${person.pageNr}`, { waitUntil: 'networkidle' });
  await staticPage.locator('.transcription__line[data-line-id]').first().waitFor();
  check(await staticPage.locator('#btn-registry').isHidden() &&
    await staticPage.locator('#btn-annotate-selection').isHidden(),
  'static viewer hides unavailable registry and manual annotation actions');
  await staticPage.close();

  check((await state()).history.length > initial.history.length,
    'registry history survives mutation and reload');
  check(errors.length === 0, `no browser JavaScript errors: ${errors.join(' | ')}`);
  const output = path.join(REPO, 'output', 'registry-browser');
  fs.mkdirSync(output, { recursive: true });
  await page.screenshot({ path: path.join(output, 'viewer.png'), fullPage: true });
  await openRegistry();
  await page.locator(`[data-entry-id="${termEntry.id}"]`).click();
  await page.screenshot({ path: path.join(output, 'registry.png'), fullPage: true });
  console.log(JSON.stringify({ checks: checks.length, results: checks }, null, 2));
} catch (error) {
  console.error(JSON.stringify({ completed: checks, errors, dialogs: await page.locator('dialog[open]').evaluateAll(
    elements => elements.map(element => ({ id: element.id, text: element.textContent, invalid: [...element.querySelectorAll(':invalid')].map(input => input.name) }))) }, null, 2));
  throw error;
} finally {
  await browser.close();
  processHandle.kill();
  await new Promise(resolve => processHandle.exitCode !== null ? resolve() : processHandle.once('exit', resolve));
  assert.deepEqual(protectedPaths.map(digest), before, 'live corpus fixtures remain unchanged');
  fs.rmSync(ROOT, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}
