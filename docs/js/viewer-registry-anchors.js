import { mentionSegments, mentionQuote } from './viewer-registry-display.js?v=20261020-segments';

/** UTF-16 offsets deliberately match both the DOM range and the registry API. */
export function rangeAtOffsets(text, start, end) {
  const walker = document.createTreeWalker(text, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let offset = 0;
  let foundStart = false;
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const next = offset + node.length;
    if (!foundStart && start >= offset && start < next) {
      range.setStart(node, start - offset);
      foundStart = true;
    }
    if (foundStart && end > offset && end <= next) {
      range.setEnd(node, end - offset);
      return range;
    }
    offset = next;
  }
  return null;
}

export function renderRegistryMarks(mentions, entries, labels) {
  const lines = Array.from(document.querySelectorAll('.transcription__line[data-line-id]'));
  for (const mention of mentions) {
    if (mention.stale) continue;
    const entry = entries.find(value => value.id === mention.entryId);
    const description = entry?.label || labels[mention.kind];
    // Every segment of a mention across a line break gets its own mark; the
    // first is the one keyboard stop, the further ones answer the pointer.
    mentionSegments(mention).forEach((segment, index) => {
      const line = lines.find(element => element.dataset.lineId === segment.lineId);
      const text = line?.querySelector('.transcription__line-text');
      if (!text || line.classList.contains('transcription__line--corrected')) return;
      if (text.textContent.slice(segment.start, segment.end) !== segment.quote) return;
      if (Array.from(text.querySelectorAll('[data-mention-id]')).some(mark => mark.dataset.mentionId === mention.id)) return;
      const range = rangeAtOffsets(text, segment.start, segment.end);
      if (!range) return;
      const mark = document.createElement('span');
      mark.className = 'registry-mention';
      mark.dataset.kind = mention.kind;
      mark.dataset.mentionId = mention.id;
      mark.dataset.segment = String(index);
      if (index === 0) {
        mark.tabIndex = 0;
        mark.setAttribute('role', 'button');
        mark.setAttribute('aria-label', `${mentionQuote(mention)}, ${description}, edit occurrence`);
      } else {
        mark.setAttribute('aria-hidden', 'true');
      }
      mark.append(range.extractContents());
      range.insertNode(mark);
    });
  }
}
