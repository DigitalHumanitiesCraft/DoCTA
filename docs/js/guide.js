import { initNav, initBanner } from './app.js';
import { createLocalEditor } from './viewer-local.js';

initNav('guide');
initBanner();

const local = createLocalEditor();
await local.init();
document.getElementById('guide-online').hidden = local.enabled;
document.getElementById('guide-local').hidden = !local.enabled;
