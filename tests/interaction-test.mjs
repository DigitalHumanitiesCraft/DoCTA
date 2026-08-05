// Klickt auf jeder Seite systematisch durch die interaktiven Elemente und
// sammelt JS-Fehler und fehlgeschlagene Requests. Navigation wird ausgespart
// bzw. rückgängig gemacht, damit der Test auf der Zielseite bleibt.
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Repo-Wurzel, unabhaengig vom Arbeitsverzeichnis des Aufrufers.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORT = 8733;
const BASE = `http://127.0.0.1:${PORT}/DoCTA/`;
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml',
  '.md': 'text/markdown; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg' };

const server = http.createServer((req, res) => {
  let rel = decodeURIComponent(req.url.split('?')[0]);
  if (!rel.startsWith('/DoCTA/')) { res.writeHead(404); return res.end(); }
  rel = rel.slice('/DoCTA/'.length) || 'index.html';
  const file = path.join(ROOT, rel);
  if (!file.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (err, buf) => {
    if (err) { res.writeHead(404); return res.end('not found: ' + rel); }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(buf);
  });
});

const PAGES = ['index.html', 'pipeline.html', 'sources.html', 'search.html',
               'viewer.html', 'network.html', 'knowledge.html', 'help.html'];

await new Promise(r => server.listen(PORT, '127.0.0.1', r));
const browser = await chromium.launch();
const report = {};

const labelOf = el => el.evaluate(e =>
  (e.innerText || e.getAttribute('aria-label') || e.getAttribute('title') ||
   e.value || e.className || e.tagName).toString().replace(/\s+/g, ' ').trim().slice(0, 50)
).catch(() => '?');

for (const page of PAGES) {
  const url = BASE + page;
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  const errors = [], failed = [];
  p.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 250)); });
  p.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0, 250)));
  p.on('requestfailed', r => failed.push(`${r.url().slice(0, 140)} :: ${r.failure()?.errorText}`));
  p.on('response', r => { if (r.status() >= 400) failed.push(`HTTP ${r.status()} ${r.url().slice(0, 140)}`); });

  await p.goto(url, { waitUntil: 'networkidle', timeout: 45000 }).catch(e =>
    errors.push('NAV: ' + String(e).slice(0, 150)));

  const baseText = await p.evaluate(() => document.body.innerText.trim().length).catch(() => 0);
  const actions = [], navAway = [];

  const backIfNavigated = async (what) => {
    if (!p.url().endsWith(page)) {
      navAway.push(`${what} -> ${p.url().replace(BASE, '')}`);
      await p.goto(url, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
      return true;
    }
    return false;
  };

  // Buttons und Bootstrap-Toggles ausserhalb der Seitennavigation.
  const sel = 'main button:visible, main [data-bs-toggle]:visible, main [role="button"]:visible, ' +
              '.modal button:visible, body > button:visible';
  const buttons = await p.$$(sel);
  for (let i = 0; i < Math.min(buttons.length, 30); i++) {
    const label = await labelOf(buttons[i]);
    try {
      await buttons[i].click({ timeout: 3000 });
      await p.waitForTimeout(400);
      const len = await p.evaluate(() => document.body.innerText.trim().length).catch(() => -1);
      actions.push(`click "${label}" -> ${len}`);
      await backIfNavigated(`click "${label}"`);
    } catch (e) {
      actions.push(`SKIP "${label}": ${String(e.message || e).split('\n')[0].slice(0, 60)}`);
    }
  }

  const selects = await p.$$('select:visible');
  for (const s of selects.slice(0, 8)) {
    const name = await labelOf(s);
    const opts = await s.$$eval('option', os => os.map(o => o.value)).catch(() => []);
    for (const v of opts.slice(0, 4)) {
      try {
        await s.selectOption(v, { timeout: 3000 });
        await p.waitForTimeout(400);
        const len = await p.evaluate(() => document.body.innerText.trim().length);
        actions.push(`select[${name}]="${v}" -> ${len}`);
      } catch {}
    }
  }

  const inputs = await p.$$('input[type="text"]:visible, input[type="search"]:visible');
  for (const inp of inputs.slice(0, 3)) {
    const name = await labelOf(inp);
    for (const term of ['Sigmund', 'zzzzqqq']) {
      try {
        await inp.fill(term, { timeout: 3000 });
        await inp.press('Enter').catch(() => {});
        await p.waitForTimeout(900);
        const len = await p.evaluate(() => document.body.innerText.trim().length);
        actions.push(`input[${name}]="${term}" -> ${len}`);
      } catch {}
    }
    await inp.fill('').catch(() => {});
    await p.waitForTimeout(400);
  }

  const boxes = await p.$$('input[type="checkbox"]:visible, input[type="radio"]:visible');
  for (const b of boxes.slice(0, 10)) {
    const name = await labelOf(b);
    try {
      await b.click({ timeout: 2500 });
      await p.waitForTimeout(350);
      const len = await p.evaluate(() => document.body.innerText.trim().length);
      actions.push(`toggle[${name}] -> ${len}`);
    } catch {}
  }

  await p.waitForTimeout(1000);
  const finalText = await p.evaluate(() => document.body.innerText.trim().length).catch(() => 0);
  report[page] = { baseText, finalText, navAway, errors: [...new Set(errors)],
                   failed: [...new Set(failed)], actions };
  await ctx.close();
}

await browser.close();
server.close();
console.log(JSON.stringify(report, null, 1));
