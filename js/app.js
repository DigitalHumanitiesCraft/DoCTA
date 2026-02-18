/**
 * DoCTA Prototype - Shared Application Module
 * Navigation, global state, page initialization.
 */

const NAV_ITEMS = [
  { href: 'index.html', label: 'Dashboard', id: 'dashboard' },
  { href: 'pipeline.html', label: 'Pipeline', id: 'pipeline' },
  { href: 'sources.html', label: 'Quellen', id: 'sources' },
  { href: 'search.html', label: 'Suche', id: 'search' },
  { href: 'viewer.html', label: 'Viewer', id: 'viewer' },
  { href: 'network.html', label: 'Netzwerk', id: 'network' },
  { href: 'knowledge.html', label: 'Knowledge', id: 'knowledge' },
  { href: 'help.html', label: 'Hilfe', id: 'help' },
];

/**
 * Initialize Bootstrap navbar navigation for the current page.
 * @param {string} activeId - ID of the current page
 */
export function initNav(activeId) {
  const nav = document.getElementById('main-nav');
  if (!nav) return;

  nav.innerHTML = NAV_ITEMS.map(item => {
    const isActive = item.id === activeId;
    return `<li class="nav-item"><a class="nav-link${isActive ? ' active' : ''}" href="${item.href}"${isActive ? ' aria-current="page"' : ''}>${item.label}</a></li>`;
  }).join('');
}

/**
 * Initialize the WIP/BETA banner below the navbar.
 * Dismissible via localStorage.
 */
export function initBanner() {
  if (localStorage.getItem('docta-banner-dismissed') === '1') return;

  const banner = document.createElement('div');
  banner.className = 'wip-banner';
  banner.id = 'wip-banner';
  banner.innerHTML = `
    <span class="wip-badge">BETA</span>
    <span>Work in Progress – Developed with <a href="https://lisa.gerda-henkel-stiftung.de/digitale_geschichte_pollin" target="_blank" rel="noopener">Promptotyping</a></span>
    <span class="wip-right">
      <a href="https://github.com/DigitalHumanitiesCraft" target="_blank" rel="noopener">GitHub</a>
      <button class="wip-close" aria-label="Schließen">×</button>
    </span>
  `;

  banner.querySelector('.wip-close').addEventListener('click', () => {
    banner.remove();
    localStorage.setItem('docta-banner-dismissed', '1');
  });

  document.querySelector('.navbar')?.after(banner);
}

/**
 * Show a loading indicator in a container.
 * @param {HTMLElement} container
 * @param {string} [message='Daten werden geladen...']
 */
export function showLoading(container, message = 'Daten werden geladen...') {
  container.innerHTML = `<div class="loading"><div class="loading__spinner"></div>${message}</div>`;
}

/**
 * Format a number with locale-aware separators.
 * @param {number} n
 * @returns {string}
 */
export function formatNumber(n) {
  if (n == null) return '–';
  return n.toLocaleString('de-AT');
}
