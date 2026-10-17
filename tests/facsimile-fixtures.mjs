// Reuse real, gitignored facsimiles for UI checks when they are already cached.
// Uncached images still use their original URL; this does not verify the archive service.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const directory = path.join(repo, 'evaluation', 'benchmark', 'images');
const images = new Map();
if (fs.existsSync(directory)) {
  for (const name of fs.readdirSync(directory)) {
    const match = /^(?:edition_|pilot_)?inv_(\d+)_p(\d+)\.jpg$/.exec(name);
    if (!match) continue;
    const register = path.join(repo, 'pipeline', 'pages', `${match[1]}.json`);
    if (!fs.existsSync(register)) continue;
    const page = JSON.parse(fs.readFileSync(register, 'utf8')).pages
      .find(item => item.pageNr === Number(match[2]));
    const key = page?.iiif?.match(/\/iiif\/2\/([^/]+)/)?.[1];
    if (key) images.set(key, path.join(directory, name));
  }
}

export async function useCachedFacsimiles(surface) {
  if (!images.size) return;
  await surface.route('https://files.transkribus.eu/iiif/2/**', async route => {
    const key = new URL(route.request().url()).pathname.split('/')[3];
    const image = images.get(key);
    if (image) await route.fulfill({ path: image, contentType: 'image/jpeg' });
    else await route.continue();
  });
}
