// Lädt jede Seite des Prototyps unter dem Unterpfad /DoCTA/ und sammelt
// Konsolenfehler, Page-Errors und fehlgeschlagene Netzwerk-Requests.
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Repo-Wurzel, unabhaengig vom Arbeitsverzeichnis des Aufrufers.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'docs');
const PORT = 8731;
const BASE = `http://127.0.0.1:${PORT}/DoCTA/`;

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
  '.md': 'text/markdown; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg',
};

// Serviert das Repo bewusst unter /DoCTA/, damit Pfadfehler auffallen,
// die auf Domain-Root nicht sichtbar wären.
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

const PAGES = ['index.html', 'viewer.html', 'exploration.html',
               'benchmark.html', 'knowledge.html', 'about.html'];

await new Promise(r => server.listen(PORT, '127.0.0.1', r));
const browser = await chromium.launch();
const report = {};

for (const page of PAGES) {
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

  // Interne Links einsammeln, um tote Verweise zu finden.
  const links = await p.$$eval('a[href]', as => as.map(a => a.getAttribute('href')))
    .catch(() => []);

  // Bilder ohne alt-Text zählen (Accessibility).
  const imgNoAlt = await p.$$eval('img', is => is.filter(i => !i.hasAttribute('alt')).length)
    .catch(() => 0);
  const imgTotal = await p.$$eval('img', is => is.length).catch(() => 0);

  // Sichtbarer Text, um leere/kaputte Renderings zu erkennen.
  const textLen = await p.evaluate(() => document.body.innerText.trim().length).catch(() => 0);
  const title = await p.title().catch(() => '');

  report[page] = { loadMs, title, textLen, errors, warnings: warnings.slice(0, 5),
                   failed: [...new Set(failed)], links: [...new Set(links)], imgNoAlt, imgTotal };
  await ctx.close();
}

await browser.close();
server.close();

// Tote interne Links auflösen
const exists = f => fs.existsSync(path.join(ROOT, f.split('#')[0].split('?')[0]));
for (const [pg, r] of Object.entries(report)) {
  r.deadLinks = r.links.filter(h =>
    h && !/^(https?:|mailto:|#|javascript:)/.test(h) && !exists(h));
  delete r.links;
}

console.log(JSON.stringify(report, null, 1));
