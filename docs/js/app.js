/**
 * DoCTA - Shared Application Module
 * Navigation, banner and footer, shared by every page of the site.
 */

const NAV_ITEMS = [
  { href: 'index.html', label: 'Home', id: 'dashboard' },
  { href: 'viewer.html', label: 'Viewer', id: 'viewer' },
  { href: 'exploration.html', label: 'Exploration', id: 'exploration' },
  { href: 'benchmark.html', label: 'Benchmark', id: 'benchmark' },
  // About sits flush right and carries the link into the knowledge base.
  { href: 'about.html', label: 'About', id: 'about', end: true },
];

/**
 * Initialize Bootstrap navbar navigation for the current page.
 * @param {string} activeId - ID of the current page
 */
export function initNav(activeId) {
  const nav = document.getElementById('main-nav');
  if (!nav) return;

  // --nav-height anchors sticky elements below the real navbar; measure it
  // instead of trusting the token's guess, or they overshoot.
  const navbar = document.querySelector('.navbar');
  if (navbar && 'ResizeObserver' in window) {
    const setNavHeight = () =>
      document.documentElement.style.setProperty('--nav-height', `${navbar.offsetHeight}px`);
    setNavHeight();
    new ResizeObserver(setNavHeight).observe(navbar);
  }

  nav.classList.add('w-100');
  nav.innerHTML = NAV_ITEMS.map(item => {
    const isActive = item.id === activeId;
    return `<li class="nav-item${item.end ? ' ms-lg-auto' : ''}"><a class="nav-link${isActive ? ' active' : ''}" href="${item.href}"${isActive ? ' aria-current="page"' : ''}>${item.label}</a></li>`;
  }).join('');

  initFooter(activeId);
}

/**
 * Compact BETA badge in the navbar.
 */
export function initBanner() {
  const brand = document.querySelector('.navbar-brand');
  if (!brand || document.getElementById('beta-badge')) return;
  const badge = document.createElement('span');
  badge.id = 'beta-badge';
  badge.className = 'beta-badge';
  badge.textContent = 'BETA';
  // The badge carries the site-wide disclaimer, so every page explains its
  // experimental status without repeating a banner.
  badge.title = 'Experimental agentic edition pipeline. This Promptotyping environment tests ' +
    'model-assisted transcription and annotation of fifteenth-century court records. ' +
    'Machine-generated content remains provisional until scholarly review and acceptance.';
  // The sticky navbar is already a containing block for the absolutely
  // positioned badge; the position-relative utility would kill the stickiness.
  const navbar = document.querySelector('.navbar');
  (navbar || brand.parentElement).appendChild(badge);
}

/* Official GitHub mark (octicon mark-github, MIT-licensed path data). */
const GITHUB_ICON =
  '<svg class="footer-icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="currentColor">' +
  '<path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 ' +
  '0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82' +
  '-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 ' +
  '0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 ' +
  '0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path></svg>';

/**
 * Shared footer: project, DHCraft (vendored logo), GitHub, imprint.
 * @param {string} activeId - current page id, to skip self-links
 */
function initFooter(activeId) {
  const footer = document.querySelector('footer');
  if (!footer) return;
  const about = activeId === 'about' ? '' :
    ` <span class="footer-sep">·</span> <a href="about.html">About &amp; Imprint</a>`;
  footer.innerHTML = `<p class="mb-0 footer-line">
    <span>DoCTA</span> <span class="footer-sep">·</span>
    <a href="https://dhcraft.org" target="_blank" rel="noopener" class="footer-brand">
      <img src="img/dhcraft-logo-48.png" alt="" width="18" height="18"> Digital Humanities Craft</a>
    <span class="footer-sep">·</span>
    <a href="https://github.com/DigitalHumanitiesCraft/DoCTA" target="_blank" rel="noopener" class="footer-brand">${GITHUB_ICON} GitHub</a>
    <span class="footer-sep">·</span>
    <a href="https://dhcraft.org/Promptotyping/" target="_blank" rel="noopener">Promptotyping</a>${about}
  </p>`;
}
