// Browser regressions for machine-decision drafts and asynchronous loading.
// API responses stay in memory; source and entity values come from corpus files.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = relative => JSON.parse(fs.readFileSync(path.join(REPO, relative), 'utf8'));
const extraction = read('docs/data/entities/11328300.json');
const doc = read(`docs/data/transcriptions/${extraction.docId}.json`);
const entity = extraction.entities.find(item => item.type === 'person');
const sourceLine = doc.pages.find(page => page.pageNr === entity.pageNr).regions
  .flatMap(region => region.lines).find(line => line.id === entity.lineId);
const alternative = extraction.entities.find(item => item.pageNr === entity.pageNr && item.id !== entity.id);
assert.ok(sourceLine && alternative, 'Required source fixtures exist');
const revision = crypto.createHash('sha256').update('').digest('hex');
const browser = await chromium.launch();
const failures = [];
const checks = [];

async function setup({ delayed = false, decision = false, legacyDraft = false } = {}) {
  const page = await browser.newPage();
  page.on('pageerror', error => failures.push(String(error)));
  const modules = new Set(['viewer-annotations.js', 'viewer-annotation-popover.js', 'utils.js']);
  await page.route('http://localhost:49871/**', async route => {
    const name = new URL(route.request().url()).pathname.slice(1);
    if (modules.has(name)) {
      await route.fulfill({ contentType: 'text/javascript', body: fs.readFileSync(path.join(REPO, 'docs/js', name), 'utf8') });
    } else if (!name) {
      await route.fulfill({ contentType: 'text/html', body: '<!doctype html><html lang="de"><title>Annotation regression</title><input id="review-initials" value="XY"><button id="btn-close-entities">Schließen</button><div role="dialog"><div id="annotation-editor"></div></div><button id="anchor">Fundstelle</button></html>' });
    } else await route.abort();
  });
  await page.goto('http://localhost:49871/');
  await page.evaluate(async ({ doc, extraction, entity, revision, delayed, decision, legacyDraft, sourceText }) => {
    const { createAnnotationEditor } = await import('/viewer-annotations.js');
    const state = { revision, decisions: [], history: [] };
    if (decision) {
      const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(sourceText));
      const textDigest = Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, '0')).join('');
      state.decisions.push({ id: entity.id, kind: entity.type, normalized: entity.normalized, status: 'pending', textDigest });
    }
    const pending = [];
    const saves = [];
    const local = {
      enabled: true,
      annotations: () => delayed ? new Promise((resolve, reject) => pending.push({ resolve, reject })) : Promise.resolve(state),
      saveAnnotations: async payload => { saves.push(payload); return { annotations: { ...state, decisions: payload.decisions } }; },
    };
    const key = `docta-annotation-${doc.docId}-${entity.id}`;
    if (legacyDraft) localStorage.setItem(key, JSON.stringify({ normalized: entity.normalized, status: 'accepted', reviewer: 'XY' }));
    const editor = createAnnotationEditor(document.querySelector('#annotation-editor'), local);
    editor.page(entity.pageNr);
    const loading = editor.load(doc, extraction);
    window.test = { editor, pending, saves, state, loading, doc, extraction, entity, key };
    if (!delayed) await loading;
  }, { doc, extraction, entity, revision, delayed, decision, legacyDraft, sourceText: sourceLine.text });
  return page;
}

async function open(page) {
  await page.evaluate(() => test.editor.open(test.entity.id, document.querySelector('#anchor')));
}

try {
  const loading = await setup({ delayed: true });
  await open(loading);
  assert.match(await loading.locator('#annotation-editor').textContent(), /werden geladen/);
  await loading.evaluate(async () => { test.pending[0].resolve(test.state); await test.loading; });
  assert.equal(await loading.locator('[name="normalized"]').inputValue(), entity.normalized);
  checks.push('Opening while GET is pending renders a form after the response without rejection');
  await loading.close();

  const changed = await setup();
  await open(changed);
  await changed.locator('[name="normalized"]').fill(alternative.normalized);
  await changed.evaluate(({ replacement }) => {
    const next = structuredClone(test.doc);
    next.pages.find(page => page.pageNr === test.entity.pageNr).regions.flatMap(region => region.lines)
      .find(line => line.id === test.entity.lineId).text = replacement;
    test.editor.update(next);
  }, { replacement: alternative.text });
  await changed.locator('button[type="submit"]').click();
  assert.match(await changed.locator('[role="status"]').textContent(), /Quellentext.*geändert/);
  assert.equal(await changed.evaluate(() => test.saves.length), 0);
  assert.equal(await changed.locator('[name="normalized"]').inputValue(), alternative.normalized);
  assert.equal(await changed.evaluate(() => JSON.parse(localStorage.getItem(test.key)).sourceText), sourceLine.text);
  checks.push('Source changes reject a dirty decision without losing its source snapshot or form values');
  await changed.close();

  const legacy = await setup({ legacyDraft: true });
  await open(legacy);
  await legacy.locator('button[type="submit"]').click();
  assert.equal(await legacy.evaluate(() => test.saves.length), 0);
  assert.ok(await legacy.evaluate(() => localStorage.getItem(test.key)));
  await legacy.locator('[data-discard-annotation]').click();
  await open(legacy);
  await legacy.locator('button[type="submit"]').click();
  await legacy.waitForFunction(() => test.saves.length === 1 && !test.editor.hasDraft);
  assert.equal(await legacy.evaluate(() => test.saves[0].decisions[0].textDigest), crypto.createHash('sha256').update(sourceLine.text).digest('hex'));
  checks.push('Legacy drafts require discard and rechecking; the fresh decision saves the exact source digest');
  await legacy.close();

  const outdated = await setup({ delayed: true });
  await outdated.evaluate(async () => {
    const latest = test.editor.load(test.doc, test.extraction);
    test.pending[1].resolve(test.state);
    await latest;
  });
  await open(outdated);
  await outdated.locator('[name="normalized"]').fill(alternative.normalized);
  await outdated.evaluate(async () => { test.pending[0].reject(new Error('superseded request')); await test.loading; });
  assert.equal(await outdated.locator('[name="normalized"]').inputValue(), alternative.normalized);
  assert.equal(await outdated.evaluate(() => test.editor.hasDraft), true);
  await outdated.locator('[data-discard-annotation]').click();
  assert.equal(await outdated.evaluate(() => test.editor.beforeNavigate()), true);
  checks.push('A superseded GET failure cannot replace the current dirty form or trap navigation');
  await outdated.close();

  const digestRace = await setup({ decision: true });
  await digestRace.evaluate(() => {
    const original = crypto.subtle.digest.bind(crypto.subtle);
    test.digests = [];
    crypto.subtle.digest = (...args) => new Promise(resolve => test.digests.push(() => original(...args).then(resolve)));
  });
  await open(digestRace);
  await digestRace.evaluate(() => { test.editor.beforeNavigate(); test.editor.open(test.entity.id, document.querySelector('#anchor')); });
  await digestRace.locator('[name="normalized"]').fill(alternative.normalized);
  await digestRace.evaluate(async () => { for (const resolve of test.digests.toReversed()) await resolve(); });
  assert.equal(await digestRace.locator('[name="normalized"]').inputValue(), alternative.normalized);
  assert.equal(await digestRace.evaluate(() => test.editor.hasDraft), true);
  assert.match(await digestRace.locator('[role="status"]').textContent(), /Ungespeicherter Annotationsentwurf/);
  checks.push('Out-of-order digest completion preserves edited form values and draft state');
  await digestRace.close();

  assert.deepEqual(failures, [], 'No browser errors or unhandled promise rejections');
  console.log(checks.map(check => `PASS ${check}`).join('\n'));
} finally {
  await browser.close();
}
