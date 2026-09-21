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
const place = fixture.entities.find(entity => entity.type === 'place');
const date = fixture.entities.find(entity => entity.type === 'time' && /^\d{4}$/.test(entity.normalized));
const laterDate = fixture.entities.find(entity => entity.type === 'time' && /^\d{4}$/.test(entity.normalized) && entity.normalized > date.normalized);
const guardedDirectories = ['pipeline/pages', 'pipeline/annotations', 'pipeline/reviews', 'pipeline/registry', 'docs/data/entities', 'docs/data/transcriptions'];
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
const machineRequests = [];
page.on('request', request => { if (/\/data\/entities\/|\/api\/annotations(?:\/|$)/.test(request.url())) machineRequests.push(request.url()); });
page.on('pageerror', error => errors.push(String(error)));
const checks = [];
const output = path.join(REPO, 'output', 'manual-annotation');
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
async function openRegistry() {
  await page.locator('#btn-registry').click();
  await page.locator('#registry-dialog').waitFor();
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

try {
  await page.goto(`${BASE}/viewer.html?doc=${DOC_ID}&page=${person.pageNr}`, { waitUntil: 'networkidle' });
  await page.locator('.transcription__line[data-line-id]').first().waitFor();
  const initial = await state();
  check(initial.entries.length === 0 && initial.mentions.length === 0,
    'isolated registry starts empty and opening the viewer does not write');

  check(await page.locator('.entity, [data-ent-key], #entities-dialog, #btn-entities').count() === 0,
    'viewer exposes no machine marks, machine annotation panel or machine toolbar action');
  await page.locator('#btn-registry').focus();
  await page.keyboard.press('Enter');
  await page.locator('#registry-dialog').waitFor();
  await page.keyboard.press('Escape');
  check(await page.locator('#registry-dialog').isHidden(),
    'Escape closes the clean register sidebar');
  check(await page.locator('#btn-registry').evaluate(element => document.activeElement === element),
    'registry sidebar opens by keyboard and Escape restores trigger focus');

  await openRegistry();
  const entryForm = page.locator('#registry-entry-form');
  for (const [kind, entity] of [['person', person], ['term', term], ['place', place]]) {
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
  const placeEntry = registry.entries.find(entry => entry.kind === 'place');
  check(personEntry.label === person.normalized && termEntry.label === term.normalized && placeEntry.label === place.normalized,
    'person, controlled term and place are persisted by the real backend');

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

  // Hold a real pre-save GET response so its stale revision reaches the browser last.
  const raceEntryId = (await state()).entries.at(-1).id;
  await page.locator('#registry-dialog [data-close-surface]').click();
  let releaseRegistryRead;
  let registryReadCaptured;
  const readGate = new Promise(resolve => { releaseRegistryRead = resolve; });
  const readCaptured = new Promise(resolve => { registryReadCaptured = resolve; });
  let holdNextRegistryRead = true;
  const delayRegistryRead = async route => {
    if (route.request().method() !== 'GET' || !holdNextRegistryRead) { await route.continue(); return; }
    holdNextRegistryRead = false;
    const response = await route.fetch();
    registryReadCaptured();
    await readGate;
    await route.fulfill({ response });
  };
  await page.route(`${BASE}/api/registry`, delayRegistryRead);
  await openRegistry();
  await readCaptured;
  await entryForm.locator('[name="note"]').fill(term.text);
  await entryForm.locator('[name="reviewer"]').fill('QA');
  await save(entryForm);
  const latestRegistry = await state();
  const delayedReadResponse = page.waitForResponse(response => response.url() === `${BASE}/api/registry` && response.request().method() === 'GET');
  releaseRegistryRead();
  await delayedReadResponse;
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  check((await page.locator(`[data-entry-id="${raceEntryId}"]`).textContent()).includes(term.text),
    'late registry GET cannot overwrite the result of a newer entry save');
  const [registryDownload] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('#registry-export').click(),
  ]);
  const exportedRegistry = JSON.parse(fs.readFileSync(await registryDownload.path(), 'utf8'));
  check(exportedRegistry.revision === latestRegistry.revision && exportedRegistry.entries.find(entry => entry.id === raceEntryId).note === term.text,
    'registry export retains the current revision and saved entry after a delayed older GET');
  await page.unroute(`${BASE}/api/registry`, delayRegistryRead);
  await entryForm.locator('[name="note"]').fill('');
  await entryForm.locator('[name="reviewer"]').fill('QA');
  await save(entryForm);
  check((await state()).entries.find(entry => entry.id === raceEntryId).note === '',
    'the next entry save uses the current revision after the delayed read');

  await entryForm.locator('[name="note"]').fill(term.text);
  const draftPage = await page.locator('#page-input').inputValue();
  await page.locator('#btn-next-page').click();
  check(await page.locator('#page-input').inputValue() === draftPage &&
    await entryForm.locator('[name="note"]').inputValue() === term.text,
  'page navigation retains the unsaved sidebar entry and its source page');
  await page.keyboard.press('Escape');
  if (!await page.locator('#registry-dialog').isVisible()) await openRegistry();
  check(await entryForm.locator('[name="note"]').inputValue() === term.text,
    'Escape and reopening retain an unsaved sidebar entry');
  await page.locator('#registry-dialog').getByRole('button', { name: 'Eingaben verwerfen', exact: true }).click();
  check(!await page.locator('#registry-dialog').isVisible(), 'explicit discard closes the dirty sidebar');
  await openRegistry();
  check(await entryForm.locator('[name="note"]').inputValue() === '',
    'discard restores the persisted entry rather than retaining its unsaved note');
  await page.keyboard.press('Escape');

  await selectText(person);
  const mentionForm = page.locator('#mention-form');
  const placement = await page.evaluate(lineId => {
    const anchor = [...document.querySelectorAll('.transcription__line[data-line-id]')].find(line => line.dataset.lineId === lineId).getBoundingClientRect();
    const surface = document.getElementById('annotation-workspace').getBoundingClientRect();
    return { inside: surface.left >= 0 && surface.right <= innerWidth + 1 && surface.top >= 0 && surface.bottom <= innerHeight + 1,
      gap: Math.max(0, surface.top - anchor.bottom, anchor.top - surface.bottom) };
  }, person.lineId);
  check(placement.inside && placement.gap <= 32,
    'inline editor is clamped inside the viewport beside its source line');
  await page.screenshot({ path: path.join(output, 'person-inline.png'), fullPage: true });
  await workspaceScreenshot('person-detail.png', person);
  if (!await page.locator('#mention-note').evaluate(element => element.open)) await page.locator('#mention-note > summary').click();
  await mentionForm.locator('[name="note"]').fill(term.text);
  await mentionForm.locator('[name="kind"]').selectOption('term');
  check(await mentionForm.locator('[name="note"]').inputValue() === term.text &&
    await page.locator('#annotation-workspace-title').textContent() === person.text,
  'changing category cannot silently replace a manual draft or its source quote');
  await mentionForm.locator('[name="kind"]').selectOption('person');
  await mentionForm.locator('[name="search"]').fill(person.text);
  // Alias lookup must expose the stable identity, even when labels coincide.
  check(await mentionForm.locator(`[name="entryId"] option[value="${personEntry.id}"]`).count() === 1,
    'the attested alias finds its existing register entry');
  await mentionForm.locator('[name="entryId"]').selectOption(personEntry.id);
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  if (await page.locator('#mention-note').evaluate(element => element.open)) await page.locator('#mention-note > summary').click();
  await workspaceScreenshot('personexisting.png', person);
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
  await page.locator('#mention-dialog').waitFor();
  check(await page.locator('[popover]:popover-open').count() === 1 &&
    await page.locator('#mention-dialog').isVisible(),
  'saved manual mark opens the one shared workspace by keyboard');
  if (await page.locator('#mention-note').evaluate(element => element.open)) await page.locator('#mention-note > summary').click();
  const lateralActions = await mark.evaluate(anchor => {
    const surface = document.getElementById('annotation-workspace');
    const box = surface.getBoundingClientRect();
    const source = anchor.getBoundingClientRect();
    const save = document.querySelector('#mention-form [type="submit"]').getBoundingClientRect();
    return { lateralRoom: Math.max(source.left, innerWidth - source.right) - 16 >= box.width,
      saveVisible: save.top >= box.top && save.bottom <= box.bottom && save.left >= box.left && save.right <= box.right && save.bottom <= innerHeight,
      scrollTop: surface.scrollTop };
  });
  check(lateralActions.lateralRoom && lateralActions.saveVisible && lateralActions.scrollTop === 0,
    `collapsed source workspace shows Save without scrolling when lateral room exists ${JSON.stringify(lateralActions)}`);
  await workspaceScreenshot('person-clicked.png', person);
  if (!await page.locator('#mention-note').evaluate(element => element.open)) await page.locator('#mention-note > summary').click();
  await mentionForm.locator('[name="note"]').fill(person.text);
  await page.keyboard.press('Escape');
  if (!await page.locator('#mention-dialog').isVisible()) await page.locator('#btn-annotate-selection').click();
  check(await mentionForm.locator('[name="note"]').inputValue() === person.text,
    'Escape and resume retain an unsaved inline mention');
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
  await page.locator('#mention-dialog').waitFor();
  check(await page.locator('#annotation-workspace-title').textContent() === person.text &&
    await mentionForm.locator('[name="entryId"]').inputValue() === personEntry.id,
  'following a fundstelle opens the persisted source span and correct identity');
  await page.keyboard.press('Escape');

  await selectText(place, 'place', 'contextmenu');
  await page.locator('#mention-new-entry').click();
  const inlineEntryForm = page.locator('#mention-entry-form');
  await inlineEntryForm.locator('[name="label"]').fill(place.normalized);
  await inlineEntryForm.locator('[name="aliases"]').fill(place.text);
  await inlineEntryForm.locator('[name="reviewer"]').fill('QA');
  check(await page.locator('#registry-dialog').isHidden() &&
    await inlineEntryForm.evaluate(element => !!element.closest('#annotation-workspace')) &&
    await page.locator('[popover]:popover-open').count() === 1,
  'new register entry is edited inside the same source workspace without opening the sidebar');
  await workspaceScreenshot('inline-new-entry.png', place);
  await save(inlineEntryForm);
  const inlinePlaceId = await mentionForm.locator('[name="entryId"]').inputValue();
  check(inlinePlaceId !== placeEntry.id && (await state()).entries.some(entry => entry.id === inlinePlaceId && entry.label === place.normalized),
    'inline creation saves a separate stable identity and selects it for the current source span');
  await page.locator('#mention-edit-entry').click();
  await inlineEntryForm.locator('[name="note"]').fill(place.text);
  await save(inlineEntryForm);
  check((await state()).entries.find(entry => entry.id === inlinePlaceId).note === place.text &&
    await mentionForm.locator('[name="entryId"]').inputValue() === inlinePlaceId && await page.locator('#registry-dialog').isHidden(),
  'editing the selected register entry retains the same identity and source workspace');
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  await save(mentionForm);
  check((await state()).mentions.some(item => item.kind === 'place' && item.entryId === inlinePlaceId && item.quote === place.text),
    'right-click selection assigns a saved exact span to a place');

  await selectText(date, 'date', 'keyboard');
  await mentionForm.locator('[name="dateMode"]').selectOption('exact');
  await mentionForm.locator('[name="when"]').fill(date.normalized);
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  await page.screenshot({ path: path.join(output, 'date-inline.png'), fullPage: true });
  await save(mentionForm);
  let dateMention = (await state()).mentions.find(item => item.kind === 'date');
  check(dateMention?.when === date.normalized && dateMention.entryId === null,
    'date annotation persists a source-attested year without an invented register identity');
  await page.locator(`[data-mention-id="${dateMention.id}"]`).click();
  await mentionForm.locator('[name="dateMode"]').selectOption('range');
  await mentionForm.locator('[name="notBefore"]').fill(laterDate.normalized);
  await mentionForm.locator('[name="notAfter"]').fill(date.normalized);
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  await mentionForm.locator('[type="submit"]').click();
  await page.waitForFunction(() => {
    const form = document.getElementById('mention-form');
    return !form.checkValidity() || document.querySelector('#mention-dialog > .registry-content > [role=status]')?.textContent.trim();
  });
  check((await state()).mentions.find(item => item.id === dateMention.id).when === date.normalized,
    'inverted date bounds cannot replace the saved exact date');
  await mentionForm.locator('[name="notBefore"]').fill(date.normalized);
  await mentionForm.locator('[name="notAfter"]').fill(laterDate.normalized);
  await mentionForm.locator('[name="uncertain"]').check();
  await save(mentionForm);
  dateMention = (await state()).mentions.find(item => item.id === dateMention.id);
  check(dateMention.notBefore === date.normalized && dateMention.notAfter === laterDate.normalized && dateMention.uncertain && dateMention.when === null,
    'explicit uncertain date range replaces the exact value with valid saved bounds');

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
    'registry sidebar has no horizontal overflow at 200 percent');
  // Escape in a populated native search field first clears the query.
  await page.locator('#registry-dialog [data-close-surface]').click();
  await mark.scrollIntoViewIfNeeded();
  await mark.click();
  check(await mentionForm.locator('[name="entryId"]').inputValue() === personEntry.id,
    'inline person editor remains operable at narrow 200 percent zoom');
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  const narrowPlacement = await page.locator('#annotation-workspace').evaluate(element => {
    const rect = element.getBoundingClientRect();
    return { scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, left: rect.left, right: rect.right, viewport: innerWidth };
  });
  await page.screenshot({ path: path.join(output, 'inline-narrow.png'), fullPage: false });
  check(narrowPlacement.scrollWidth <= narrowPlacement.clientWidth + 1 && narrowPlacement.left >= 0 && narrowPlacement.right <= narrowPlacement.viewport + 1,
    `inline editor has no horizontal overflow at narrow 200 percent zoom ${JSON.stringify(narrowPlacement)}`);
  await save(mentionForm);
  check((await state()).mentions.some(item => item.id === mention.id && item.entryId === personEntry.id),
    'inline controls remain fillable and saveable at narrow 200 percent zoom');
  await page.evaluate(() => { document.documentElement.style.zoom = ''; });
  await page.setViewportSize({ width: 1280, height: 800 });

  // Acceptance images precede the deliberate source mutation below.
  await page.screenshot({ path: path.join(output, 'viewer.png'), fullPage: true });
  await openRegistry();
  await page.locator(`[data-entry-id="${personEntry.id}"]`).click();
  await page.screenshot({ path: path.join(output, 'registry.png'), fullPage: true });
  await page.keyboard.press('Escape');

  const indexPage = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  indexPage.on('pageerror', error => errors.push(String(error)));
  const beforeIndex = await state();
  await indexPage.goto(`${BASE}/register.html?entry=${personEntry.id}`, { waitUntil: 'networkidle' });
  await indexPage.locator('#register-results [data-entry-id]').first().waitFor();
  check(await indexPage.locator('#register-entry-title').textContent() === personEntry.label,
    'index direct link selects the persisted editorial identity');
  const indexDescriptions = await indexPage.locator('#register-results [data-entry-id]').allTextContents();
  check(new Set(indexDescriptions).size === indexDescriptions.length,
    'index distinguishes separate same-name identities');
  const indexAttestation = new URL(await indexPage.locator('.register-attestations a').first().getAttribute('href'), BASE);
  check(indexAttestation.searchParams.get('mention') === mention.id && indexAttestation.searchParams.get('doc') === String(DOC_ID) &&
    indexAttestation.searchParams.get('page') === String(person.pageNr), 'index links to the exact saved source mention');
  check((await indexPage.locator('#register-history').textContent()).includes('QA'),
    'index exposes persisted editorial change attribution');
  for (const [kind, entry] of [['person', personEntry], ['place', placeEntry], ['term', termEntry]]) {
    await indexPage.locator('#register-kind').selectOption(kind);
    await indexPage.locator('#register-search').fill(entry.aliases[0]);
    check(await indexPage.locator(`#register-results [data-entry-id="${entry.id}"]`).count() === 1,
      `index filters ${kind} and finds the persisted source spelling`);
  }
  await indexPage.locator('#register-kind').selectOption('');
  await indexPage.locator('#register-search').fill('');
  await indexPage.locator(`#register-results [data-entry-id="${personEntry.id}"]`).click();
  await indexPage.reload({ waitUntil: 'networkidle' });
  check(new URL(indexPage.url()).searchParams.get('entry') === personEntry.id &&
    await indexPage.locator('#register-entry-title').textContent() === personEntry.label,
    'index selected identity survives reload');
  await indexPage.screenshot({ path: path.join(output, 'index.png'), fullPage: true });
  const [indexDownload] = await Promise.all([indexPage.waitForEvent('download'), indexPage.locator('#register-export').click()]);
  assert.deepEqual(JSON.parse(fs.readFileSync(await indexDownload.path(), 'utf8')), beforeIndex);
  assert.deepEqual(await state(), beforeIndex, 'browsing and exporting the index writes no registry data');
  await indexPage.setViewportSize({ width: 640, height: 500 });
  await indexPage.evaluate(() => { document.documentElement.style.zoom = '2'; });
  check(await indexPage.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1),
    'index remains readable without horizontal overflow at narrow 200 percent zoom');
  check(await indexPage.locator('.navbar-toggler').isVisible() && await indexPage.evaluate(() => {
    const badge = document.getElementById('research-preview').getBoundingClientRect();
    const toggle = document.querySelector('.navbar-toggler').getBoundingClientRect();
    return badge.right <= toggle.left || badge.left >= toggle.right || badge.bottom <= toggle.top || badge.top >= toggle.bottom;
  }), 'mobile Research preview label does not overlap the visible navigation toggle at 200 percent');
  await indexPage.locator('.navbar-toggler').click();
  const indexNavLink = indexPage.locator('#main-nav').getByRole('link', { name: 'Index', exact: true });
  await indexNavLink.waitFor({ state: 'visible' });
  check(await indexNavLink.getAttribute('aria-current') === 'page',
    'expanded mobile navigation exposes the accessible current Index link');
  await indexNavLink.focus();
  await indexPage.keyboard.press('Enter');
  await indexPage.waitForURL(`${BASE}/register.html`);
  await indexPage.locator('#register-results [data-entry-id]').first().waitFor();
  check(new URL(indexPage.url()).pathname === '/register.html', 'mobile Index link is keyboard operable');
  await indexPage.locator(`#register-results [data-entry-id="${personEntry.id}"]`).click();
  await indexPage.evaluate(() => { document.documentElement.style.zoom = '2'; });
  await indexPage.screenshot({ path: path.join(output, 'index-narrow.png'), fullPage: true });
  await indexPage.close();

  await mark.click();
  await mentionForm.locator('[name="reviewer"]').fill('QA');
  const removeResponse = page.waitForResponse(response => response.url() === `${BASE}/api/registry` &&
    response.request().method() === 'POST');
  await page.locator('#mention-remove').click();
  assert.equal((await removeResponse).status(), 200);
  await page.reload({ waitUntil: 'networkidle' });
  check(!(await state()).mentions.some(item => item.id === mention.id),
    'manual mention deletion persists across reload');

  await selectText(term, 'term');
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
  check((await page.locator('#mention-dialog > .registry-content > [role="status"]').textContent()).includes('geändert'),
    'stale-source inline editor explains why a new selection is required');
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');

  const staticPage = await browser.newPage();
  staticPage.on('pageerror', error => errors.push(String(error)));
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
  check(await staticPage.locator('.entity, [data-ent-key], #entities-dialog, #btn-entities').count() === 0,
    'public static viewer also exposes no machine annotations');
  await staticPage.route('**/register.html*', async route => {
    const response = await route.fetch();
    const headers = response.headers();
    delete headers.server;
    await route.fulfill({ response, headers });
  });
  await staticPage.goto(`${BASE}/register.html`, { waitUntil: 'networkidle' });
  check(await staticPage.locator('#register-export').isHidden() && await staticPage.locator('#register-browser').isHidden() &&
    (await staticPage.locator('#register-status').textContent()).includes('lokalen Arbeitseditor'),
    'static index states local availability without dead export or editing controls');
  await staticPage.close();

  check((await state()).history.length > initial.history.length,
    'registry history survives mutation and reload');
  check(machineRequests.length === 0, 'editor does not request machine extractions or annotation decisions');
  check(errors.length === 0, `no browser JavaScript errors: ${errors.join(' | ')}`);
  console.log(JSON.stringify({ checks: checks.length, results: checks }, null, 2));
} catch (error) {
  console.error(JSON.stringify({ completed: checks, errors, dialogs: await page.locator('dialog[open], [role=dialog]:visible, #registry-dialog:visible').evaluateAll(
    elements => elements.map(element => ({ id: element.id, text: element.textContent, invalid: [...element.querySelectorAll(':invalid')].map(input => input.name) }))) }, null, 2));
  throw error;
} finally {
  await browser.close();
  const serverClosed = new Promise(resolve => processHandle.once('close', resolve));
  processHandle.kill();
  await serverClosed;
  assert.deepEqual(protectedPaths.map(digest), before, 'live corpus fixtures remain unchanged');
  fs.rmSync(ROOT, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}
