/** Near-text surface with a native top layer and a fixed-position fallback. */
export function createAnchoredPopover(element, { onHide = () => {}, beforeHide = () => true } = {}) {
  const native = typeof element.showPopover === 'function';
  let anchor = null;
  let origin = null;
  let opened = false;
  element.classList.add('annotation-popover');
  element.hidden = true;
  if (native) element.setAttribute('popover', 'manual');

  function reposition() {
    if (!opened) return;
    const rect = anchor?.getBoundingClientRect?.() || anchor;
    const gap = 8;
    const viewport = window.visualViewport;
    const width = viewport?.width || window.innerWidth;
    const height = viewport?.height || window.innerHeight;
    const left = viewport?.offsetLeft || 0;
    const top = viewport?.offsetTop || 0;
    const measured = element.getBoundingClientRect();
    const scale = element.offsetWidth ? measured.width / element.offsetWidth : 1;
    element.style.maxInlineSize = `${(width - gap * 2) / scale}px`;
    const belowRoom = top + height - (rect?.bottom ?? top) - gap * 2;
    const aboveRoom = (rect?.top ?? top) - top - gap * 2;
    // Keep the cited passage visible when the form needs its own scroll area.
    element.style.maxBlockSize = `${Math.max(120, Math.min(height - gap * 2, Math.max(belowRoom, aboveRoom))) / scale}px`;
    const box = element.getBoundingClientRect();
    const x = Math.max(left + gap, Math.min(rect?.left ?? left + gap, left + width - box.width - gap));
    const below = (rect?.bottom ?? top) + gap;
    const above = (rect?.top ?? top) - box.height - gap;
    const y = below + box.height <= top + height - gap ? below : Math.max(top + gap, above);
    element.style.insetInlineStart = `${x / scale}px`;
    element.style.insetBlockStart = `${Math.min(y, top + height - box.height - gap) / scale}px`;
  }

  function hide({ restoreFocus = true } = {}) {
    if (!opened) return true;
    if (beforeHide() === false) return false;
    opened = false;
    if (native && element.matches(':popover-open')) element.hidePopover();
    element.hidden = true;
    if (restoreFocus && origin?.isConnected) origin.focus({ preventScroll: true });
    onHide();
    return true;
  }

  function open(nextAnchor, nextOrigin = document.activeElement) {
    anchor = nextAnchor || nextOrigin;
    origin = nextOrigin;
    element.hidden = false;
    if (native && !element.matches(':popover-open')) element.showPopover();
    opened = true;
    reposition();
  }

  document.addEventListener('pointerdown', event => {
    if (opened && !element.contains(event.target) && !origin?.contains?.(event.target)) hide({ restoreFocus: false });
  });
  document.addEventListener('keydown', event => {
    if (opened && event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      hide();
    }
  });
  window.addEventListener('resize', reposition);
  document.addEventListener('scroll', reposition, true);
  window.visualViewport?.addEventListener('resize', reposition);
  if (typeof ResizeObserver === 'function') new ResizeObserver(reposition).observe(element);
  return { open, hide, reposition, get isOpen() { return opened; } };
}
