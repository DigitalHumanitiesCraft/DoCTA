/**
 * Interface strings whose wording is itself a requirement: provenance
 * statements and the read-only state. The pages and the browser tests read
 * them from here, so a test asserts the shipped wording rather than a copy.
 */
export const PROVENANCE = {
  vlm: 'Unrevised machine transcription by DoCTA',
  sourceListVlm: 'Initial machine transcription, unrevised',
  transkribusUnrecorded: 'Machine transcription (Transkribus HTR), correction not recorded',
  inventariaCorrected: 'Text source Inventaria, corrected',
  transkribusCorrected: 'Text source Transkribus, corrected',
  partlyCorrected: (done, total) =>
    `Text source partly corrected (${done}/${total} pages), remaining pages unrevised machine transcription`,
  localCorrection: 'Corrected locally',
};

export const DRAFT_BADGE = 'Unsaved changes';
