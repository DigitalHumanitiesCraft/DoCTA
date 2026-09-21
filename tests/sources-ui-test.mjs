// Read-only browser checks against the actual source catalogue and projections.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = path.join(REPO, 'docs');
const read = relative => JSON.parse(fs.readFileSync(path.join(ROOT, relative), 'utf8'));
const sources = read('data/sources.json');
const documents = read('data/pipeline/register_summary.json').documents;
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.xml': 'application/xml' };
const server = http.createServer((req, res) => {
  if (req.method !== 'GET') { res.writeHead(405); res.end(); return; }
  const file = path.resolve(ROOT, `.${decodeURIComponent(new URL(req.url, 'http://localhost').pathname)}`);
  if (!file.startsWith(`${ROOT}${path.sep}`)) { res.writeHead(403); res.end(); return; }
  fs.readFile(file, (error, body) => {
    res.writeHead(error ? 404 : 200, { 'Content-Type': `${MIME[path.extname(file)] || 'application/octet-stream'}; charset=utf-8` });
    res.end(error ? 'Not found' : body);
  });
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on('pageerror', error => errors.push(String(error)));
const checks = [];
const check = (condition, label) => { assert.ok(condition, label); checks.push(label); };
const output = path.join(REPO, 'output', 'sources-acceptance');
fs.mkdirSync(output, { recursive: true });
const row = source => page.locator('#sources-list .src-row').filter({ has: page.locator('.src-sig', { hasText: source.signatur }) });

try {
  await page.goto(`${base}/index.html`, { waitUntil: 'networkidle' });
  await page.locator('#sources-list .src-row').first().waitFor();
  check(await page.locator('html').getAttribute('lang') === 'de', 'source catalogue declares German');
  check(await page.locator('#sources-list .src-row').count() === sources.length, 'unfiltered source list covers the stored catalogue');
  check(await page.locator('#research-preview').textContent() === 'Research preview', 'Research preview identifies the working site beside the brand');
  check(await page.locator('#research-preview').getAttribute('href') === 'about.html#current-scope', 'Research preview links to the stated working scope');
  check(await page.locator('#beta-badge, .progress-block, .stages, .hero').count() === 0, 'source overview has no former badge, hero or pipeline progress strip');
  check(!(await page.locator('main').textContent()).includes('·'), 'source metadata uses no middle-dot separators');
  const options = await page.locator('#filter-availability option').allTextContents();
  check(options.includes('Mit Transkription') && options.includes('Nur Digitalisat') && options.includes('Nur Katalognachweis'), 'availability filters name the actual German source states');

  const vlmDocuments = documents.filter(doc => doc.transcription_source === 'vlm');
  check(vlmDocuments.length > 0, 'actual corpus provides VLM transcription fixtures');
  await page.locator('#filter-availability').selectOption('text');
  for (const doc of vlmDocuments) {
    const projection = read(`data/pipeline/transcriptions/${doc.docId}.json`);
    assert.ok(projection.pages.some(p => p.regions?.some(r => r.lines?.some(l => l.text?.trim()))));
    const source = sources.find(s => s.transkribus_docs.some(d => Number(d.doc_id) === doc.docId));
    check(await row(source).count() === 1 && await row(source).locator(`a[href*="doc=${doc.docId}"]`).count() > 0,
      `text filter includes the actual VLM projection ${doc.docId}`);
    check((await row(source).locator('.src-provenance').textContent()).includes('Maschinelle Ausgangstranskription'),
      `VLM source ${doc.docId} identifies its initial text provenance`);
  }
  const credited = documents.find(doc => doc.transcription_by === 'Inventaria' && doc.edition_url);
  const creditedSource = sources.find(s => s.transkribus_docs.some(d => Number(d.doc_id) === credited.docId));
  check(await row(creditedSource).locator(`a[href="${credited.edition_url}"]`).count() === 1,
    'existing transcription credit links to its stored edition provenance');
  const creditedDocs = creditedSource.transkribus_docs.map(doc => documents.find(value => value.docId === Number(doc.doc_id)))
    .filter(doc => doc?.transcription_by === 'Inventaria');
  const allCorrected = creditedDocs.every(doc => doc.pages_total > 0 && doc.done_pages >= doc.pages_total);
  const someCorrected = creditedDocs.some(doc => doc.done_pages > 0);
  const expectedCredit = `Transkription Inventaria${allCorrected ? ', korrigiert' : someCorrected ? ', teilweise korrigiert' : ''}`;
  check(await row(creditedSource).locator(`a[href="${credited.edition_url}"]`).textContent() === expectedCredit,
    'transcription attribution claims correction only when the recorded page states support it');
  await page.waitForFunction(() => [...document.querySelectorAll('#sources-list img')]
    .filter(image => image.getBoundingClientRect().top < innerHeight)
    .every(image => image.complete && image.naturalWidth > 0));
  await page.screenshot({ path: path.join(output, 'sources-text.png'), fullPage: false });

  await page.locator('#filter-availability').selectOption('catalogue');
  const catalogue = sources.find(s => !s.transkribus_docs.length && !s.digital_images && s.tier === 3);
  check(await row(catalogue).count() === 1 && await row(catalogue).locator('a.src-title').count() === 0,
    'catalogue-only source remains findable without an invented viewer target');
  await page.locator('#filter-availability').selectOption('images');
  const imageOnly = documents.find(doc => doc.transcription_source !== 'vlm' && !doc.effective_transcription &&
    !fs.existsSync(path.join(ROOT, 'data/transcriptions', `${doc.docId}.json`)) &&
    sources.some(s => s.transkribus_docs.some(d => Number(d.doc_id) === doc.docId && !d.has_text)));
  assert.ok(imageOnly, 'actual corpus provides an image-only document');
  const imageSource = sources.find(s => s.transkribus_docs.some(d => Number(d.doc_id) === imageOnly.docId));
  check(await row(imageSource).locator(`a.src-title[href*="doc=${imageOnly.docId}"]`).count() === 1,
    'image-only source has a direct viewer link despite lacking a transcription file');
  const imageUrl = new URL(await row(imageSource).locator('a.src-title').getAttribute('href'), base).href;

  await page.locator('#filter-availability').selectOption('');
  await page.locator('#search-input').fill(creditedSource.signatur);
  await page.waitForFunction(() => document.querySelectorAll('#sources-list .src-row').length === 1);
  check(await row(creditedSource).count() === 1, 'German source search resolves an exact stored shelfmark');
  await page.locator('#search-input').fill('zzzzqqq');
  await page.locator('.src-empty').waitFor();
  check((await page.locator('.src-empty').textContent()).includes('Keine'), 'empty source search reports its result in German');
  await page.locator('#search-input').fill('');
  await page.waitForFunction(count => document.querySelectorAll('#sources-list .src-row').length === count, sources.length);
  const category = creditedSource.kategorie;
  await page.locator('#category-chips button').filter({ hasText: category }).click();
  check(await page.locator('#sources-list .src-row').count() === sources.filter(source => source.kategorie === category).length, 'German source category filter matches the actual catalogue category');
  await page.locator('#category-chips button[data-kat=""]').click();
  await page.screenshot({ path: path.join(output, 'sources.png'), fullPage: false });
  await page.setViewportSize({ width: 640, height: 500 });
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  check(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), 'source catalogue has no horizontal overflow at narrow 200 percent');
  check(await page.evaluate(() => {
    const preview = document.getElementById('research-preview').getBoundingClientRect();
    const button = document.querySelector('.navbar-toggler').getBoundingClientRect();
    return preview.right <= button.left || preview.left >= button.right || preview.bottom <= button.top || preview.top >= button.bottom;
  }), 'Research preview does not overlap the mobile navigation toggle');
  await page.locator('.navbar-toggler').click();
  check(await page.locator('#main-nav a[href="register.html"]').isVisible(), 'mobile navigation exposes the editorial Index');
  await page.waitForFunction(() => !document.querySelector('.navbar .collapsing'));
  await page.locator('.navbar-toggler').click();
  await page.waitForFunction(() => !document.querySelector('.navbar .collapsing'));
  await page.locator('#search-input').fill(imageSource.signatur);
  await page.waitForFunction(() => document.querySelectorAll('#sources-list .src-row').length === 1);
  await page.screenshot({ path: path.join(output, 'sources-narrow.png'), fullPage: true });

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(imageUrl, { waitUntil: 'networkidle' });
  check(await page.locator('#doc-selector').inputValue() === String(imageOnly.docId), 'image-only source opens its exact document in the viewer');
  check((await page.locator('#page-total').textContent()).includes(String(imageOnly.pages_total)), 'image-only viewer reports the recorded document extent');
  check((await page.locator('#transcription-container').textContent()).includes('dieses Digitalisat liegt keine Transkription vor.'), 'image-only viewer accurately states missing transcription');
  check(await page.locator('#btn-review').isHidden() && await page.locator('#btn-more').isHidden(), 'image-only viewer hides unavailable review and text tools');
  check(await page.locator(`a[href="data/tei/${imageOnly.docId}.xml"]`).count() === 0,
    'image-only viewer does not retain a dead TEI export link');
  check(await page.locator('#page-input').getAttribute('max') === '1' && await page.locator('#btn-next-page').isDisabled(), 'image-only viewer offers only the image URL actually recorded, without invented pages');
  check(await page.locator('#btn-tags, #tags-dialog, #btn-entities, #entities-dialog').count() === 0, 'image-only viewer exposes no removed machine or tag controls');
  await page.screenshot({ path: path.join(output, 'image-only-viewer.png'), fullPage: false });
  check(errors.length === 0, `no browser JavaScript errors: ${errors.join(' | ')}`);
  console.log(JSON.stringify({ checks: checks.length, results: checks }, null, 2));
} finally {
  await browser.close();
  await new Promise(resolve => server.close(resolve));
}
