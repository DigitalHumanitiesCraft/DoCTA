import { createAnchoredPopover } from './viewer-annotation-popover.js';

/** One source context owns selection, editorial assignment and machine evidence. */
export function createAnnotationWorkspace() {
  const surface = document.createElement('section');
  surface.id = 'annotation-workspace';
  surface.setAttribute('role', 'dialog');
  surface.setAttribute('aria-modal', 'false');
  surface.setAttribute('aria-labelledby', 'annotation-workspace-title');
  surface.innerHTML = `
    <div class="viewer-dialog__header">
      <h2 id="annotation-workspace-title">Textstelle annotieren</h2>
      <button type="button" class="review-btn" id="annotation-workspace-close">Schließen</button>
    </div>
    <div id="annotation-source-location"></div>
    <div id="annotation-selection-toolbar" role="group" aria-label="Auswahl annotieren" hidden></div>
    <div id="mention-dialog" hidden><div class="registry-content"></div></div>`;
  document.body.append(surface);
  const manual = surface.querySelector('#mention-dialog');
  const selection = surface.querySelector('#annotation-selection-toolbar');
  const machine = document.getElementById('entities-dialog');
  if (machine) surface.insertBefore(machine, manual);
  const beforeChange = [];
  const beforeHide = [];
  const listeners = [];
  const hideListeners = [];
  let context = null;
  let anchor = null;
  let origin = null;
  const identity = value => value && [value.docId, value.pageNr, value.lineId, value.start, value.end].join('/');
  const popover = createAnchoredPopover(surface, {
    beforeHide: () => beforeHide.every(check => check() !== false),
    onHide: () => hideListeners.forEach(notify => notify()),
  });

  function open(next) {
    const changed = identity(next.context) !== identity(context);
    if (changed && beforeChange.some(check => check() === false)) {
      if (context) popover.open(anchor, origin);
      return false;
    }
    anchor = next.anchor || anchor;
    origin = next.origin instanceof Element ? next.origin : origin || document.activeElement;
    context = next.context || context;
    surface.querySelector('h2').textContent = context?.quote || 'Textstelle annotieren';
    surface.querySelector('#annotation-source-location').textContent = context?.pageNr ? `Seite ${context.pageNr}` : '';
    if (changed) listeners.forEach(notify => notify(context));
    popover.open(anchor, origin);
    return true;
  }

  surface.querySelector('#annotation-workspace-close').addEventListener('click', () => popover.hide());
  return {
    surface, manual, selection, open,
    hide: options => popover.hide(options),
    reposition: () => popover.reposition(),
    onContext: callback => listeners.push(callback),
    onHide: callback => hideListeners.push(callback),
    addBeforeChange: callback => beforeChange.push(callback),
    addBeforeHide: callback => beforeHide.push(callback),
    get context() { return context; },
    get isOpen() { return popover.isOpen; },
  };
}
