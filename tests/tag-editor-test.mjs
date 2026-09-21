import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from 'playwright';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DOCS = path.join(ROOT, 'docs');
const fixturePath = path.join(DOCS, 'data', 'transcriptions', '11328300.json');
const fixtureBytes = fs.readFileSync(fixturePath);
const documentData = JSON.parse(fixtureBytes);
documentData.revision = crypto.createHash('sha256').update(fixtureBytes).digest('hex');

const MIME = {
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
};

const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
  if (pathname === '/tag-editor-test.html') {
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    response.end('<!doctype html><html><body><section id="tags"></section></body></html>');
    return;
  }
  const file = path.resolve(DOCS, `.${pathname}`);
  if (!file.startsWith(`${DOCS}${path.sep}`)) {
    response.writeHead(403);
    response.end();
    return;
  }
  fs.readFile(file, (error, body) => {
    if (error) {
      response.writeHead(404);
      response.end();
      return;
    }
    response.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    response.end(body);
  });
});

await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const port = server.address().port;
const browser = await chromium.launch();

try {
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${port}/tag-editor-test.html`);
  await page.evaluate(async doc => {
    const { createTagEditor } = await import('/js/viewer-tags.js');
    let reviewDraft = false;
    let tags = [];
    let revision = 'empty';
    let deferred = null;
    const clone = value => JSON.parse(JSON.stringify(value));
    const local = {
      enabled: true,
      async tags() {
        return { docId: doc.docId, revision, sourceRevision: doc.revision, tags: clone(tags) };
      },
      async saveTags(payload) {
        window.__saveCalls.push(clone(payload));
        if (deferred) return deferred.promise;
        if (payload.action === 'add') {
          const line = doc.pages.find(item => item.pageNr === payload.tag.pageNr).regions
            .flatMap(region => region.lines).find(item => item.id === payload.tag.lineId);
          tags.push({ ...payload.tag, id: `tag-${tags.length + 1}`, text: line.text,
            textDigest: 'fixture', created: 'fixture', stale: false });
        }
        revision = `revision-${window.__saveCalls.length}`;
        return { tags: { docId: doc.docId, revision, sourceRevision: doc.revision, tags: clone(tags) } };
      },
    };
    window.__saveCalls = [];
    window.__setReviewDraft = value => { reviewDraft = value; };
    window.__deferSave = () => {
      let reject;
      const promise = new Promise((resolve, rejectPromise) => { reject = rejectPromise; });
      deferred = { promise, reject };
    };
    window.__rejectSave = message => {
      const pending = deferred;
      deferred = null;
      pending.reject(new Error(message));
    };
    window.__addStaleTag = tag => { tags.push(clone(tag)); };
    window.__editor = createTagEditor(document.getElementById('tags'), local, {
      hasReviewDraft: () => reviewDraft,
      refreshSource: async () => {},
    });
    window.__doc = doc;
    window.__editor.page(doc.pages[0].pageNr);
    await window.__editor.load(doc);
  }, documentData);

  await page.getByText('Schlagwörter', { exact: true }).click();
  const form = page.locator('.tag-editor');
  await form.locator('[name="lineId"]').selectOption(documentData.pages[0].regions[0].lines[0].id);
  await form.locator('[name="tag"]').fill('Inventarisierung');
  await form.locator('[name="reviewer"]').fill('XY');
  await page.evaluate(() => { window.__setReviewDraft(true); window.__editor.sync(); });
  await form.locator('[type="submit"]').click({ force: true });
  assert.equal(await page.evaluate(() => window.__saveCalls.length), 0);
  assert.match(await form.locator('.tag-editor__warning').textContent(), /Transkriptionskorrekturen speichern/);

  await page.evaluate(() => { window.__setReviewDraft(false); window.__editor.sync(); });
  await form.locator('[type="submit"]').click();
  await page.locator('.tag-editor__list').getByText('Inventarisierung').waitFor();

  await page.evaluate(async () => {
    await window.__editor.load(window.__doc);
    window.__editor.page(window.__doc.pages[0].pageNr);
  });
  const filter = page.locator('[name="tagFilter"]');
  await filter.fill('Inventarisierung');
  assert.equal(await page.locator('.tag-editor__list li').count(), 1);
  await filter.fill('Übergabe');
  await page.locator('.tag-editor__list').getByText('Keine gespeicherten Schlagwörter').waitFor();

  const firstLine = documentData.pages[0].regions[0].lines[0];
  await page.evaluate(tag => window.__addStaleTag(tag), {
    id: 'stale-tag', pageNr: documentData.pages[0].pageNr, lineId: firstLine.id,
    tag: 'Inventarisierung', note: '', reviewer: 'XY', text: firstLine.text,
    textDigest: 'fixture', created: 'fixture', stale: true,
  });
  await page.evaluate(async () => {
    await window.__editor.load(window.__doc);
    window.__editor.page(window.__doc.pages[0].pageNr);
  });

  for (const action of ['delete', 'recheck']) {
    await page.evaluate(() => window.__deferSave());
    if (action === 'delete') {
      await page.locator('[data-delete]').first().click();
    } else {
      await page.locator('[name="reviewer"]').fill('XY');
      await page.locator('[data-recheck="stale-tag"]').click();
    }
    await page.evaluate(() => window.__editor.page(window.__doc.pages[1].pageNr));
    await page.evaluate(label => window.__rejectSave(`${label} failed`), action);
    await page.locator('.tag-editor__message').getByText(/fehlgeschlagen/).waitFor();
    assert.match(await page.locator('.tag-editor__message').textContent(), new RegExp(`Seite ${documentData.pages[0].pageNr}`));
    await page.evaluate(() => window.__editor.page(window.__doc.pages[0].pageNr));
  }

  const draftKey = `docta-tags-draft-${documentData.docId}-${documentData.pages[0].pageNr}`;
  await page.evaluate(({ key, lineId }) => {
    localStorage.setItem(key, JSON.stringify({ lineId, tag: 'Inventarisierung', note: '',
      reviewer: 'XY', sourceRevision: 'older-source-revision' }));
  }, { key: draftKey, lineId: firstLine.id });
  await page.reload();
  await page.evaluate(async doc => {
    const { createTagEditor } = await import('/js/viewer-tags.js');
    const local = { enabled: true, tags: async () => ({ docId: doc.docId, revision: 'empty',
      sourceRevision: doc.revision, tags: [] }), saveTags: async () => { throw new Error('unexpected save'); } };
    window.__editor = createTagEditor(document.getElementById('tags'), local, {
      hasReviewDraft: () => false, refreshSource: async () => {},
    });
    window.__editor.page(doc.pages[0].pageNr);
    await window.__editor.load(doc);
  }, documentData);
  await page.getByText('Schlagwörter', { exact: true }).click();
  assert.equal(await page.locator('[type="submit"]').isDisabled(), true);
  await page.locator('[data-rebase]').click();
  assert.equal(await page.locator('[type="submit"]').isEnabled(), true);

  console.log('OK tag editor component behavior');
} finally {
  await browser.close();
  await new Promise(resolve => server.close(resolve));
}
