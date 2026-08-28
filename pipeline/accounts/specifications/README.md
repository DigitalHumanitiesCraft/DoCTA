# DoCTA Accounts Core Data Specification

The accounts core separates artifacts from the statuses assigned to them. It
contains no ontology-specific Entry, Transaction, Transfer, total or liability
payload. Those concepts belong to a later versioned annotation profile.

## Normative implementation

`pipeline/accounts/models.py` is the executable boundary specification. Its
Pydantic v2 models reject unknown fields and serialize camelCase JSON. The
machine-readable `core-v1.json` records the public models and controlled status
vocabularies. The test suite verifies that the file and the implementation stay
aligned.

## Core artifacts

- `SourceAnchor`: an exact quote and character range in one transcription
  revision, qualified by document, scan, side, PAGE region and PAGE line.
- `TranscriptionLine`: source text plus PAGE geometry and reading order.
- `TranscriptionRevision`: an ordered transcription state with an independent
  verification and publication status.
- `AnnotationProposal`: an immutable candidate tied to the exact transcription
  revision and source anchor it was created from.
- `ReviewDecision`: a separate human decision on one proposal.
- `AnnotationSet`: the accepted proposals for one transcription revision.
- `EditionBuildManifest`: a deterministic lock of accepted inputs and versioned
  specifications.

## Status dimensions

`verification` describes human comparison of a transcription with the
facsimile. `editorialDecision` describes a decision on an annotation proposal.
`publication` describes public availability. Passing a schema or hash check
changes none of these statuses.

## Reference examples and test fixtures

The files below `tests/fixtures/core/` are synthetic software fixtures. They are
not scholarly verified reference examples and do not constitute ground truth.
