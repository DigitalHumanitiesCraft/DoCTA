/**
 * Interface strings whose wording is itself a requirement: provenance
 * statements and the read-only state. The pages and the browser tests read
 * them from here, so a test asserts the shipped wording rather than a copy.
 */
const lines = n => (n === 1 ? '1 line' : `${n} lines`);

export const PROVENANCE = {
  // The status pill beside the transcription title. The document's text
  // attribution comes first, the current page's state qualifies it, so the
  // two never appear as separate, contradicting statements.
  vlm: 'Machine transcription, unrevised',
  vlmCorrected: n => `Machine transcription, ${lines(n)} corrected`,
  // A saved correction whose line count the served data cannot establish.
  vlmCorrectedUncounted: 'Machine transcription, corrections saved',
  // The published projection carries corrected text without naming its page.
  vlmPartlyCorrected: 'Machine transcription, partly corrected, otherwise unrevised',
  transkribusUnrecorded: 'Transkribus HTR, correction not recorded',
  transkribusUnrecordedCorrected: n => `Transkribus HTR, ${lines(n)} corrected`,
  transkribusUnrecordedCorrectedUncounted: 'Transkribus HTR, corrections saved',
  inventariaCorrected: 'Inventaria, corrected',
  transkribusCorrected: 'Transkribus, corrected',
  // A DoCTA correction on text that was already corrected at its source.
  changedInDocta: (base, n) => `${base}, ${lines(n)} changed in DoCTA`,
  partlyCorrected: (done, total) =>
    `Transkribus, ${done} of ${total} pages corrected, otherwise unrevised`,
  sourceListVlm: 'Initial machine transcription, unrevised',
};

/** Field labels, values and notes of the status details surface. */
export const STATUS_DETAILS = {
  title: 'Text status',
  fields: {
    layer: 'Text layer', model: 'Model', transcribed: 'Transcribed', edition: 'Edition',
    page: 'This page', document: 'Document', correctedBy: 'Corrected by', coverage: 'Coverage',
  },
  layer: {
    vlm: 'Machine transcription, DoCTA pipeline',
    unrecorded: 'Transkribus HTR, correction not recorded',
  },
  vlmNote: 'Transcribed by a vision-language model; Transkribus holds no transcription of this source. ' +
    'Lines without a saved correction are unrevised machine transcription.',
  unrecordedNote: 'No page of this document is marked done in Transkribus, so no human correction ' +
    'is documented. The text may have been worked on without the status being set.',
  corrected: (by, total) => `All ${total} pages corrected${by ? ` by ${by}` : ''} and marked done in Transkribus.`,
  partlyCorrected: (by, done, total) => `${done} of ${total} pages corrected${by ? ` by ${by}` : ''} ` +
    'and marked done in Transkribus; the remaining pages are the unrevised Transkribus HTR layer.',
  modelUndocumented: 'not documented',
  transkribusExport: 'Transkribus HTR, model not documented',
  editionLink: 'Edition by Inventaria',
  editionLinkName: 'Open the Inventaria edition',
  noCorrection: 'No saved correction',
  correctionCount: n => `${lines(n)} corrected`,
  correctionUncounted: 'Corrections saved',
  correctionUnlocated: 'Corrections saved, pages not recorded',
  notApproval: 'A saved correction records a text change. It is not a scholarly approval.',
  coverage: (done, total) => `${done} of ${total} pages transcribed`,
  draft: 'This page has unsaved changes. Save or discard them in the edit bar.',
};

export const DRAFT_BADGE = 'Unsaved changes';
