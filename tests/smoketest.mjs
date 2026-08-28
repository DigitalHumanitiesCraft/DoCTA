// Loads every page of the site and collects console errors, page errors and
// failed network requests.
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Repo root, independent of the caller's working directory.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'docs');
const PORT = 8731;
const BASE = `http://127.0.0.1:${PORT}/DoCTA/`;

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
  '.md': 'text/markdown; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg',
};

// Served under /DoCTA/ like GitHub Pages, so that a path error which stays
// invisible on a domain root shows up here.
const server = http.createServer((req, res) => {
  let rel = decodeURIComponent(req.url.split('?')[0]);
  if (!rel.startsWith('/DoCTA/')) { res.writeHead(404); return res.end('outside base'); }
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

// The deep links of the site are addresses in their own right. A view or a page
// reached only through the URL is what a citation points at, and no plain page
// load covers that. The document behind them comes from the data on disk, so a
// changed corpus does not leave a dead id in the test.
function linkTarget() {
  const tei = fs.readdirSync(path.join(ROOT, 'data', 'tei'))
    .filter(f => /^\d+\.xml$/.test(f)).map(f => f.slice(0, -4)).sort();
  for (const id of tei) {
    const file = path.join(ROOT, 'data', 'transcriptions', `${id}.json`);
    if (!fs.existsSync(file)) continue;
    const pages = JSON.parse(fs.readFileSync(file, 'utf8')).pages || [];
    if (!pages.length) continue;
    return { docId: id, pageNr: pages[Math.min(2, pages.length - 1)].pageNr };
  }
  return null;
}

// nonempty: a selector that has to match an element carrying content, so a view
// that renders an empty shell counts as a finding rather than as a pass.
const target = linkTarget();
const DEEP_LINKS = [
  ...(target ? [
    { url: `viewer.html?doc=${target.docId}&view=tei`, nonempty: ['pre.tei-source'] },
    { url: `viewer.html?doc=${target.docId}&page=${target.pageNr}`,
      nonempty: ['.transcription__line'],
      check: async p => (await p.locator('#page-input').inputValue()) === String(target.pageNr)
        ? [] : ['the pager does not stand on the linked page'] },
  ] : []),
  ...['register', 'network', 'entities'].map(view => ({
    url: `exploration.html?view=${view}`,
    nonempty: [`#tab-${view}[aria-selected="true"]`, `#panel-${view}`],
  })),
];

const TARGETS = [...PAGES.map(url => ({ url })), ...DEEP_LINKS];

await new Promise(r => server.listen(PORT, '127.0.0.1', r));
const browser = await chromium.launch();
const report = {};

for (const { url: page, nonempty = [], check } of TARGETS) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  const errors = [], warnings = [], failed = [], slow = [];

  p.on('console', m => {
    if (m.type() === 'error') errors.push(m.text().slice(0, 300));
    if (m.type() === 'warning') warnings.push(m.text().slice(0, 200));
  });
  p.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0, 300)));
  p.on('requestfailed', r => failed.push(`${r.url().slice(0, 160)} :: ${r.failure()?.errorText}`));
  p.on('response', r => { if (r.status() >= 400) failed.push(`HTTP ${r.status()} ${r.url().slice(0, 160)}`); });

  const t0 = Date.now();
  try {
    await p.goto(BASE + page, { waitUntil: 'networkidle', timeout: 45000 });
  } catch (e) {
    errors.push('NAVIGATION: ' + String(e).slice(0, 200));
    try { await p.waitForTimeout(6000); } catch {}
  }
  const loadMs = Date.now() - t0;

  // Internal links, to find dead references.
  const links = await p.$$eval('a[href]', as => as.map(a => a.getAttribute('href')))
    .catch(() => []);

  // Images without alt text.
  const imgNoAlt = await p.$$eval('img', is => is.filter(i => !i.hasAttribute('alt')).length)
    .catch(() => 0);
  const imgTotal = await p.$$eval('img', is => is.length).catch(() => 0);

  // Visible text, to detect an empty or broken rendering.
  const textLen = await p.evaluate(() => document.body.innerText.trim().length).catch(() => 0);
  const title = await p.title().catch(() => '');

  // What the address promised has to be on the page. An element that is only a
  // shell, with neither text nor a child, does not count as rendered.
  const missing = [];
  for (const sel of nonempty) {
    const filled = await p.waitForSelector(sel, { timeout: 8000 })
      .then(el => el.evaluate(e => e.childElementCount > 0 || e.innerText.trim().length > 0))
      .catch(() => null);
    if (filled === null) missing.push(`${sel} is absent`);
    else if (!filled) missing.push(`${sel} rendered empty`);
  }
  if (check) missing.push(...await check(p).catch(e => [String(e).slice(0, 120)]));

  report[page] = { loadMs, title, textLen, errors, warnings: warnings.slice(0, 5),
                   failed: [...new Set(failed)], links: [...new Set(links)], imgNoAlt, imgTotal,
                   missing };
  await ctx.close();
}

await browser.close();
server.close();

const exists = f => fs.existsSync(path.join(ROOT, f.split('#')[0].split('?')[0]));
for (const [, r] of Object.entries(report)) {
  r.deadLinks = r.links.filter(h =>
    h && !/^(https?:|mailto:|#|javascript:)/.test(h) && !exists(h));
  delete r.links;
}

console.log(JSON.stringify(report, null, 1));

// Per-document data is optional: a missing file is the normal case and is caught
// in the client, so it does not decide the result.
const OPTIONAL = /\/data\/entities\/|\/data\/tei\//;
// The length of the rendered text is a gate. A page that renders nothing is
// broken even when it threw no error.
const blocking = Object.entries(report).filter(([, r]) =>
  r.errors.length || r.deadLinks.length || r.missing.length || !r.textLen ||
  r.failed.some(f => !OPTIONAL.test(f)));
if (blocking.length) {
  console.error('FAIL: ' + blocking.map(([pg]) => pg).join(', '));
  process.exitCode = 1;
}
