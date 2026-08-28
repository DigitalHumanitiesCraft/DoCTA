# Editorial Model

## Scope and status

This document defines the editorial objects, evidence relations and responsible decisions used by the DoCTA account-book pilot. It supplies the vocabulary shared by transcription, semantic annotation, TEI encoding, RDF generation and the later exploration interface.

The model describes an intended specification. The present DoCTA account-book material consists of unrevised machine transcriptions and has no facsimile-verified or editorially accepted accounting layer. Conformance to this document will require implementation and scholarly acceptance.

`HTR-EVALUATION.md` remains authoritative for recognition experiments, metrics and test-set design. `ACCOUNTING-ENCODING.md` defines the machine-readable representations of the objects introduced here.

## Editorial layers

DoCTA distinguishes the historical source, its digital representation, textual revisions and scholarly interpretation.

| Layer | Object | Function |
|---|---|---|
| Historical record | Archival Source | Material document preserved by an archive |
| Image evidence | Digital Facsimile | Digital visual representation used for reading and verification |
| Text | Transcription Revision | Immutable version of transcribed text with stable anchors and provenance |
| Source reference | Mention, Entry, Measure, Unit Mention, Source Rubric | Addressable feature attested in a Transcription Revision |
| Authority data | Entity, Unit, Account, Account Category, Commodity Category | Resolved authority record or controlled concept |
| Interpretation | Annotation, Assertion, Transaction, Transfer, Economic Good | Explicit editorial analysis supported by source evidence |

An artefact type states what an object is. Its verification status, editorial decision, formal validation and publication status are stored separately.

## Source and text objects

### Archival Source

An **Archival Source** is the historical record identified by an archival repository and shelfmark. It may comprise a volume, a file, a leaf, an inserted slip or a fragment. The archival object remains distinct from every image, transcription and edition derived from it.

### Digital Facsimile

A **Digital Facsimile** is an image-based representation of an Archival Source. It carries a stable image identifier, provenance and, where available, a checksum and an IIIF address. A facsimile can support verification only within its visible scope and image quality.

### Transcription Revision

A **Transcription Revision** is an immutable textual artefact derived from a named source image or image region. It records the transcription convention, stable page, region and line anchors, the generating or editing responsibility and a digest of its content.

`Transcription Revision` is the artefact name for machine-produced and human-edited text alike. Terms such as `verified transcription` and `editorially accepted text` describe status or editorial role and never replace the artefact type.

A revised reading creates a new Transcription Revision. Earlier revisions remain available for provenance and comparison. An annotation bound to a superseded revision requires re-anchoring and a new editorial decision before release.

## Source-bound and authority objects

### Mention

A **Mention** is an addressable span in one Transcription Revision. It preserves the source wording and points to exact textual and facsimile evidence. A Mention may indicate a person name, organisation name, place name, date, resource expression, office, account label or another relevant source expression.

A Mention does not establish identity. Several Mentions may refer to one Entity, and one unresolved Mention may have several proposed Entity candidates.

### Entity

An **Entity** is an authority-register record for an identifiable person, organisation, place or other project entity. It may aggregate several source forms while preserving every Mention that supports the identification. An Entity can carry external identifiers, variant names, temporal scope and provenance.

The link between a Mention and an Entity is an Assertion. The Entity record does not inherit the verification status of every linked Mention.

### Annotation

An **Annotation** is an encoded association between an addressable source feature and a category, role, value or other analytical description. Inline TEI elements and JSON annotation records are serialisations of annotations.

An Annotation may contain one or more Assertions. Its presence in valid XML records an encoding operation. Historical validity follows from the status of the Assertions that the Annotation expresses.

### Assertion

An **Assertion** is a proposition made by a named editorial or computational responsibility and supported by explicit evidence. Assertions include entity links, role assignments, normalised dates, interpreted quantities, category assignments, Entry boundaries, Transaction reconstructions and Transfer directions.

Every Assertion records:

- a stable identifier;
- the Transcription Revision on which it depends;
- one or more evidence anchors;
- the asserted predicate and object;
- provenance for its creation;
- verification status;
- editorial decision;
- formal validation results;
- publication status.

Language models produce proposed Assertions. Deterministic checks establish formal properties. A responsible editor establishes facsimile verification and editorial acceptance.

## Accounting objects

### Entry

An **Entry** is a source-bound accounting unit represented by a continuous or explicitly linked segment of a Transcription Revision. It preserves the documentary wording, order, position and source rubric.

Entry boundaries are editorial Assertions about the organisation of the record. The DoCTA application profile defines that an Entry documents zero or more Transactions. This rule accommodates rubrics, totals, balance statements and other accounting acts that document no Transaction.

### Transaction

A **Transaction** is an editorial reconstruction of an economic occurrence evidenced by one or more Entries. It groups the Transfers that together express the reconstructed occurrence and carries links to every supporting Entry. Additional source passages may supply further evidence.

A Transaction may remain partial when the source omits an agent, date, place or counterpart. Missing information is represented as absent or unresolved evidence. It receives no invented value.

### Transfer

A **Transfer** is an atomic movement of a resource within a Transaction. A Transfer may identify a source agent, a target agent, a resource and a quantity. Direction remains unresolved when the source does not establish it.

Money, goods, rights, liabilities and services can serve as transferred resources. A stated price or account balance does not by itself establish a money Transfer. The Transfer Assertion requires source evidence for the economic relation.

### Measure

A **Measure** is a source-bound quantitative expression. It preserves the attested wording and may carry proposed or editorially accepted interpretations of numerical value, resource and unit. The original expression remains available when a normalised value is editorially accepted.

A Measure can state money, a count, weight, capacity, length or another historical quantity. A Measure may lack a resolved Unit when the notation remains ambiguous.

### Unit Mention

A **Unit Mention** is the exact source expression that names or abbreviates a unit within a Measure. It is a Mention and retains spelling, abbreviation marks and uncertainty.

The connection from a Unit Mention to a Unit is an Assertion. The original form remains distinct from its resolved unit definition.

### Unit

A **Unit** is a project definition of a historical measure or currency unit. It records the label, unit type, geographical and temporal scope, sources and any evidenced conversion rules.

Two identically named units receive separate records when their values or scopes differ. A conversion applies only within the scope supported by its evidence.

### Source Rubric

A **Source Rubric** is a heading, marginal label or organising expression attested in the source. It can govern several Entries through an explicit documentary relation.

Source Rubrics preserve the historical organisation of the account. Their mapping to Accounts or Account Categories is represented by Assertions.

### Account

An **Account** is a source-defined or editorially reconstructed grouping of Entries within an accounting record. It may correspond to a named section, responsible office, person, revenue stream, expenditure stream or another documented organising principle.

The Account concept carries no assumption of double-entry bookkeeping. Debit and credit roles are used only where the source establishes them.

### Account Category

An **Account Category** is a controlled analytical class used to compare Accounts or Entries across source structures. Account Categories form a project taxonomy with stable identifiers and documented scope notes.

Source Rubrics and Account Categories remain separate. A mapping between them is an editorial Assertion with its own evidence and decision status.

### Economic Good

An **Economic Good** is a resource whose movement or valuation participates in a Transaction or Transfer. It may refer to a particular object, a quantity of fungible material or a class of goods when the source supports only that level of identification.

An Economic Good retains its source Mentions and may receive one or more Commodity Category assignments.

### Commodity Category

A **Commodity Category** is a controlled class in a hierarchy of goods. It supports aggregation and exploration across variant source expressions. Its scope note defines the historical and analytical criteria for membership.

The category hierarchy does not replace the source wording. Assigning an Economic Good or Measure to a Commodity Category is an Assertion.

## Independent status axes

### Verification status

Verification records the relation between an artefact or Assertion and its evidence.

| Value | Definition |
|---|---|
| `unreviewed` | No qualified comparison with the Digital Facsimile has been recorded. |
| `facsimile-reviewed` | A qualified editor has compared the item with the Digital Facsimile. Open readings or unresolved findings may remain. |
| `facsimile-verified` | The item has been checked against the Digital Facsimile for the declared scope, and every unresolved reading within that scope is explicitly represented. |

`verified` appears only with its evidence basis and scope. Model agreement, arithmetic consistency and schema conformance do not establish facsimile verification.

### Editorial decision

Editorial decision records the accountable treatment of an artefact or Assertion.

| Value | Definition |
|---|---|
| `proposed` | The object is available for assessment and has no editorial acceptance. |
| `accepted` | A named responsible editor has editorially accepted the object for a specified edition or dataset version. |
| `ambiguous` | The evidence supports more than one interpretation, and the responsible editor records the alternatives without selecting one. |
| `withheld` | The responsible editor records that the available evidence or declared scope does not support an assertion. |
| `rejected` | A named responsible editor has declined the proposal. |
| `stale` | A dependency has changed, so the earlier decision cannot be used until it has been reconsidered. |
| `superseded` | A later editorially accepted object replaces the object for current use while provenance is preserved. |

Editorial acceptance states a responsible decision. It does not imply publication.

### Formal validation

Formal validation records conformance to a named, versioned machine-readable specification.

| Value | Definition |
|---|---|
| `not-checked` | The named validation procedure has not run. |
| `valid` | The artefact conforms to the named schema, shape or deterministic specification. |
| `invalid` | The artefact violates the named schema, shape or deterministic specification. |

Every validation result identifies the schema, shape or deterministic check and its version. `Validated` is reserved for this formal meaning. A formally valid transcription or graph may remain unreviewed and proposed.

### Publication status

Publication status records public availability of an identifiable version.

| Value | Definition |
|---|---|
| `unpublished` | The version has no public release. |
| `published` | The version is publicly available through a stable release or edition reference. |
| `withdrawn` | A previously published version has been removed from current use with the reason preserved. |

Publication records availability. It confers no additional verification or editorial status.

## Evaluation and testing terms

Reference Transcription and Ground-Truth Transcription are roles assigned to a Transcription Revision for a named evaluation. They are not separate artefact types.

### Reference Transcription

The **Reference Transcription** role designates a fixed Transcription Revision used for comparison. Its verification status and editorial decision are always stated. A provisional or facsimile-reviewed Reference Transcription can support error discovery. Defensible recognition accuracy requires a ground-truth transcription.

### Ground-Truth Transcription

The **Ground-Truth Transcription** role designates a versioned, line-anchored Reference Transcription that follows a fixed convention, is facsimile-verified, is editorially accepted and belongs to a defined evaluation sample. The designation makes no general claim of finality beyond that convention, source scope and version.

### Reference Example

A **Reference Example** is a bounded, source-backed scholarly example whose reading, modelling decision and encoding have been editorially accepted for a declared scope. It identifies its Digital Facsimile, evidence anchors, responsible editor and editorially accepted version. A Reference Example can support discussion and acceptance testing without belonging to an evaluation sample.

### Test Fixture

A **Test Fixture** is a frozen machine-readable input, expected output or paired input and output used by an automated test. It may be derived from a Reference Example or be entirely synthetic. Fixture status establishes reproducibility of a test and carries no scholarly acceptance by itself.

## Invariants

- Every source-bound object identifies its Transcription Revision and evidence anchors.
- Every semantic link is an Assertion with provenance and independent statuses.
- Mentions preserve source wording; Entities provide resolved identity in authority registers.
- Entry, Transaction and Transfer remain distinct editorial objects.
- Normalised quantities preserve the attested Measure and Unit Mention.
- Source Rubrics remain distinct from Accounts and Account Categories.
- Commodity Categories remain distinct from Economic Goods and their Mentions.
- A changed Transcription Revision invalidates the currency of dependent Assertions until they are re-anchored and reconsidered.
- Formal validity never substitutes for facsimile verification or editorial acceptance.
