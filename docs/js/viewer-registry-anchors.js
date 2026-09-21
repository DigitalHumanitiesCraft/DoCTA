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
    const line = lines.find(element => element.dataset.lineId === mention.lineId);
    const text = line?.querySelector('.transcription__line-text');
    if (!text || line.classList.contains('transcription__line--corrected')) continue;
    if (text.textContent.slice(mention.start, mention.end) !== mention.quote) continue;
    if (Array.from(text.querySelectorAll('[data-mention-id]')).some(mark => mark.dataset.mentionId === mention.id)) continue;
    const range = rangeAtOffsets(text, mention.start, mention.end);
    if (!range) continue;
    const entry = entries.find(value => value.id === mention.entryId);
    const description = entry?.label || labels[mention.kind];
    const mark = document.createElement('span');
    mark.className = 'registry-mention';
    mark.dataset.kind = mention.kind;
    mark.dataset.mentionId = mention.id;
    mark.tabIndex = 0;
    mark.setAttribute('role', 'button');
    mark.setAttribute('aria-label', `${mention.quote}, ${description}, Fundstelle bearbeiten`);
    mark.append(range.extractContents());
    range.insertNode(mark);
  }
}
