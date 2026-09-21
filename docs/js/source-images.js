// Collection metadata records only the first image, not a complete page list.
export function imageDocument(entry) {
  if (!Number.isSafeInteger(entry?.docId) || entry.docId <= 0) return null;
  let url;
  try { url = new URL(entry.url); } catch { return null; }
  const key = url.searchParams.get('id');
  if (url.origin !== 'https://files.transkribus.eu' || url.pathname !== '/Get' ||
      !/^[A-Za-z0-9_-]+$/.test(key || '')) return null;
  if (!Number.isSafeInteger(entry.nrOfPages) || entry.nrOfPages < 1) return null;
  const total = entry.nrOfPages;
  return {
    docId: entry.docId, title: entry.title || '', imageOnly: true,
    provenance: { pagesInDocument: total, pagesTranscribed: 0 },
    pages: [{ pageNr: 1, regions: [],
      iiif: `https://files.transkribus.eu/iiif/2/${key}/full/max/0/default.jpg` }],
  };
}
