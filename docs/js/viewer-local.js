// A capability issued by the loopback server separates local writes from Pages.
export function createLocalEditor() {
  let token = null;
  let version = null;
  async function request(path, body) {
    const response = await fetch(path, {
      cache: 'no-store',
      ...(body === undefined ? {} : {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-DoCTA-Token': token },
        body: JSON.stringify(body),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }
  return {
    get enabled() { return token !== null; },
    get version() { return version; },
    async init() {
      if (!['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)) return;
      try {
        const page = await fetch(location.pathname, { cache: 'no-store' });
        await page.text();
        if (!page.headers.get('Server')?.includes('DoCTALocalEditor/')) return;
        const session = await request('/api/session');
        version = session.version || null;
        if (session.write_enabled && typeof session.token === 'string') token = session.token;
      } catch { /* A plain static preview remains an export-only viewer. */ }
    },
    load: (id) => request(`/api/documents/${id}`),
    save: (review) => request('/api/review', review),
    build: (date, docIds) => request('/api/build', { date, docIds }),
    registry: () => request('/api/registry'),
    saveRegistry: (payload) => request('/api/registry', payload),
  };
}
