// Loads every page of the site and collects console errors, page errors and
// failed network requests.
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { useCachedFacsimiles } from './facsimile-fixtures.mjs';

// Repo root, independent of the caller's working directory.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'docs');
// Port 0 lets the system choose a free port, so suites can run concurrently.
let BASE = '';

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

// Language guard. The interface is English; these German interface words were
// translated and must not return. Source text, shelfmarks, catalogue titles and
// extracted entity forms stay German and are excluded by their containers.
const GERMAN_UI = [
  'Quelle', 'Quellen', 'Quellenangaben', 'Anleitung', 'Bearbeiten', 'speichern', 'gespeichert',
  'verwerfen', 'Schließen', 'Seite', 'Seiten', 'Fundstelle', 'Fundstellen', 'Kürzel', 'Eintrag',
  'Einträge', 'Registereintrag', 'Begriff', 'Begriffe', 'Datumsangabe', 'Datierung', 'Signatur',
  'Transkription', 'Faksimile', 'Lesetext', 'Digitalisat', 'Digitalisate', 'Weitere Funktionen',
  'Zum Inhalt', 'Über das Projekt', 'Ganze Seite', 'Bitte', 'nicht', 'Keine', 'Änderungen',
  'Auswahl', 'annotieren', 'Notiz', 'Oberbegriff', 'Schreibweisen', 'Zeile', 'öffnen',
  'Vergrößern', 'Verkleinern', 'Vollbild', 'Hälfte', 'Gesamtbild', 'Sortierung', 'Verfügbarkeit',
];
const GERMAN_RE = new RegExp(String.raw`(?<!\p{L})(${GERMAN_UI.join('|')})(?!\p{L})`, 'u');
const SOURCE_TEXT = [
  'body [lang]:not([lang="en"])', '#transcription-container', '#source-title', '#source-shelfmark',
  '#source-details', '#doc-selector', '.src-title', '.src-sig', '#annotation-workspace-title',
  '.exp-table', '.exp-attest', '.net-svg', '.net-card', '.net-list', 'select', 'option',
].join(',');

async function germanInterfaceText(p) {
  return p.evaluate(({ pattern, flags, exclude }) => {
    const re = new RegExp(pattern, flags);
    const found = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      const parent = node.parentElement;
      if (!parent || parent.closest(exclude) || !parent.checkVisibility()) continue;
      const match = re.exec(node.textContent);
      if (match) found.push(`text "${match[1]}" in ${node.textContent.trim().slice(0, 80)}`);
    }
    for (const el of document.querySelectorAll('[aria-label], [title], [placeholder], [alt]')) {
      if (el.closest(exclude)) continue;
      for (const name of ['aria-label', 'title', 'placeholder', 'alt']) {
        const match = re.exec(el.getAttribute(name) || '');
        if (match) found.push(`${name} "${match[1]}" on ${el.tagName.toLowerCase()}#${el.id}`);
      }
    }
    const meta = document.querySelector('meta[name="description"]')?.content || '';
    for (const [label, value] of [['title', document.title], ['meta description', meta]]) {
      const match = re.exec(value);
      if (match) found.push(`${label} "${match[1]}"`);
    }
    return found;
  }, { pattern: GERMAN_RE.source, flags: GERMAN_RE.flags, exclude: SOURCE_TEXT });
}

async function middleDots(p) {
  return p.evaluate(exclude => {
    const found = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const parent = walker.currentNode.parentElement;
      if (!parent || parent.closest(exclude) || !walker.currentNode.textContent.includes('·')) continue;
      found.push(walker.currentNode.textContent.trim().slice(0, 80));
    }
    return found;
  }, SOURCE_TEXT);
}

await new Promise(r => server.listen(0, '127.0.0.1', r));
BASE = `http://127.0.0.1:${server.address().port}/DoCTA/`;
const browser = await chromium.launch();
const report = {};

for (const { url: page, nonempty = [], check } of TARGETS) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  await useCachedFacsimiles(ctx);
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
  const lang = await p.evaluate(() => document.documentElement.lang).catch(() => '');
  if (lang !== 'en') missing.push(`html lang is "${lang}", not "en"`);
  missing.push(...(await germanInterfaceText(p).catch(e => [String(e).slice(0, 120)]))
    .map(item => `German interface word: ${item}`));
  // The operator excluded middle-dot separators from the whole interface.
  missing.push(...(await middleDots(p).catch(e => [String(e).slice(0, 120)]))
    .map(item => `middle-dot separator: ${item}`));

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

// The same denylist over the string literals of the site scripts, so a German
// message that only appears in a rare state cannot slip past the page loads.
// Comments are dropped first; the vocabulary mappings name no denylisted word.
const scriptFindings = [];
for (const name of fs.readdirSync(path.join(ROOT, 'js')).filter(f => f.endsWith('.js'))) {
  const code = fs.readFileSync(path.join(ROOT, 'js', name), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|\s)\/\/.*$/gm, '$1');
  for (const literal of code.match(/'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`/g) || []) {
    const match = GERMAN_RE.exec(literal);
    if (match) scriptFindings.push(`js/${name}: "${match[1]}" in ${literal.slice(0, 80)}`);
    if (literal.includes('·') || literal.includes('·')) scriptFindings.push(`js/${name}: middle dot in ${literal.slice(0, 80)}`);
  }
}
report['docs/js/*.js :: German string literals'] = { errors: [], failed: [], deadLinks: [], textLen: 1,
  missing: scriptFindings };

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
