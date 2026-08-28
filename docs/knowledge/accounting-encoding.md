# Accounting Encoding Specification

## Scope and status

This document specifies how the DoCTA account-book pilot represents the objects defined in `EDITORIAL-MODEL.md` as JSON, inline TEI and RDF. It also assigns each validation rule to JSON Schema, RELAX NG, Schematron, deterministic pipeline checks or SHACL.

The document defines an intended pilot specification. No current DoCTA account-book transcription, accounting annotation, TEI file or RDF graph has been facsimile-verified and editorially accepted under this specification. Existing model runs remain unrevised machine output.

The pilot uses a hand-written project RELAX NG schema and a separate Schematron schema. A TEI ODD is deferred beyond the pilot. The schema sources, generated artefacts and validator versions must remain pinned and reproducible.

Part of this specification has an executable counterpart in `pipeline/accounts/`, the module that turns those rules into code a test can hold to. Implemented there are the PAGE-derived anchoring and its identity and digest rules, the JSON records for Transcription Revision, annotation proposal and review decision with the status axes of `EDITORIAL-MODEL.md` kept separate, the staleness rule that invalidates an anchor when its text digest changes, and the validation of TEI and RDF against the project RELAX NG, the Schematron rules and the SHACL shapes.

The remainder is prose specification. Annotation Sets and their set hash, the Edition Build Manifest, and the generation and comparison steps of the deterministic build below, from TEI generation through the byte-for-byte clean rebuild, describe an intended build that does not exist yet. A set hash and a manifest are testable only against the build that reads them, so they stay specification until such a consumer is written, and this document remains the authority for their form.

## Authoritative layers

| Concern | Authoritative representation |
|---|---|
| Source image identity and layout | Source manifest and PAGE-derived anchor data |
| Text | Immutable Transcription Revision |
| Mentions and proposed Assertions | Versioned JSON annotation records |
| Editorial decisions | Versioned review records bound to an input digest |
| Released XML edition | Deterministically generated TEI |
| Semantic graph | Deterministically generated RDF |
| XML grammar | TEI P5 schema and project RELAX NG |
| Cross-element XML rules | Schematron |
| RDF graph constraints | SHACL |

Language models may produce candidate Transcription Revisions, Mentions and Assertions. They do not write released TEI or RDF. The publication build runs without model calls and consumes only pinned inputs.

## Identifiers and anchoring

Every source-bound record carries stable identifiers for the Archival Source, document, page, region and line. Character spans use offsets into the exact Unicode string of a named Transcription Revision. Each evidence object contains the quoted substring as an additional deterministic check.

An annotation anchor is valid only when all of the following conditions hold:

- the Transcription Revision digest matches;
- the page, region and line identifiers resolve;
- the character offsets fall within the named line;
- the substring selected by the offsets equals the stored quotation;
- the linked facsimile zone resolves where layout coordinates exist.

A changed text digest makes every dependent anchor stale. Re-anchoring produces a new annotation revision and preserves the earlier record.

## JSON specifications

### Transcription Revision

A Transcription Revision record contains:

- JSON Schema and specification versions;
- source, document and page identifiers;
- image and layout provenance;
- transcription convention identifier;
- immutable lines in reading order;
- a stable identifier and text digest;
- generating or editing responsibility;
- artefact provenance;
- verification status;
- editorial decision;
- formal validation results;
- publication status.

Machine and human provenance are attributes of the revision. The artefact type remains `Transcription Revision` in both cases.

### Annotation package

An annotation package is bound to one Transcription Revision digest and one version of the Editorial Model and Accounting Encoding Specification. It contains Mentions, Entities referenced from an authority snapshot, Assertions and review decisions.

Every Mention contains:

- a stable local identifier;
- an evidence anchor;
- a mention type;
- the verbatim source form;
- creation provenance;
- independent status values.

Every Assertion contains:

- a stable identifier;
- subject, predicate and object;
- one or more evidence references;
- the responsible agent or process;
- the input revision digest;
- independent status values;
- optional alternatives or a reason for withholding a decision.

Model confidence is excluded from the editorial status. A model may report uncertainty as a triage signal. Acceptance remains an explicit review decision.

### Edition Build Manifest

The publication build consumes an Edition Build Manifest that pins:

- the source and image manifest;
- the selected Transcription Revision for every page;
- authority-register snapshots;
- unit and taxonomy versions;
- editorially accepted annotation and review revisions;
- the encoding profile and ontology-crosswalk versions;
- the generator and validator versions.

Assertions with the decisions `ambiguous`, `withheld`, `rejected`, `stale` or `superseded` remain in provenance data and are excluded from released TEI and RDF. Released Assertions carry the machine value `accepted`; prose describes them as editorially accepted.

## TEI document structure

The account-book TEI extends the existing DoCTA facsimile and line structure. Each page retains `<pb>`, `<surface>`, `<zone>` and `<lb>` links. A layout region remains an `<ab>`. Accounting structure is encoded inside the region with `<seg>`.

### Inline annotations

Inline encoding is the default for source-bound structures whose textual extents can be represented without overlap.

| Editorial object | TEI representation |
|---|---|
| Entry | `<seg ana="bk:Entry">` |
| Transaction | `<seg ana="bk:Transaction">` |
| Transfer | `<seg ana="bk:Transfer">` |
| Person Mention | `<persName ref="#person-id">` |
| Organisation Mention | `<orgName ref="#org-id">` |
| Place Mention | `<placeName ref="#place-id">` |
| Date Mention | `<date>` with the attested text and an editorially accepted normalisation where available |
| Measure | `<measure>` with attested text and editorially accepted quantity fields where available |
| Unit Mention | Text inside `<measure>` linked through `@unitRef` after unit resolution |
| Source Rubric | A source-bound `<seg>` or `<head>` classified through the source-rubric taxonomy |

The Entry segment carries the documentary boundary. A Transaction segment is added when the source passage and editorially accepted interpretation support a coherent transaction. A Transfer segment identifies one resource flow within that Transaction. A source passage may remain an Entry without any Transaction or Transfer annotation.

TEI nesting supplies the local inline representation. The JSON identifiers and reciprocal `@corresp` references carry the accounting cardinality. An Entry documents zero or more Transactions, and a Transaction is evidenced by one or more Entries. A Transaction supported by several Entries is generated once and lists every supporting Entry. Each supporting Entry lists the same Transaction identifier.

The following fragment is synthetic and illustrates the nesting specification. It is a Test Fixture candidate and has no status as a Reference Example. The DoCTA profile fixes `bk:Entry`, `bk:Transaction` and `bk:Transfer` as class annotations. Lowercase tokens identify properties and roles, including `bk:from` and `bk:to`.

```xml
<ab xml:id="ab-rb2-p28-r3">
  <lb xml:id="line-rb2-p28-r3-l7" facs="#zone-rb2-p28-r3-l7"/>
  <seg xml:id="entry-rb2-p28-e1"
       ana="bk:Entry #rubric-provisions"
       corresp="#transaction-rb2-p28-t1">
    <seg xml:id="transaction-rb2-p28-t1"
         ana="bk:Transaction"
         corresp="#entry-rb2-p28-e1">
      <seg xml:id="transfer-rb2-p28-tf1" ana="bk:Transfer">
        von
        <persName ref="#person-1" ana="bk:from">Hannsen</persName>
        <measure ana="bk:EconomicGood #commodity-rye"
                 quantity="2"
                 unitRef="#unit-star">ij star roggen</measure>
        an die
        <orgName ref="#org-1" ana="bk:to">hofhaltung</orgName>
      </seg>
    </seg>
  </seg>
</ab>
```

The source wording remains element content. `@quantity`, `@when`, resolved references and category assignments express editorially accepted interpretations. An unresolved reading retains the diplomatic form and uses TEI mechanisms such as `<unclear>`, `<choice>`, `<gap>` or `<supplied>` according to the editorial convention.

A money Measure does not establish a money Transfer by itself. A price, balance, subtotal or total receives its documentary and accounting function through an explicit, editorially accepted Assertion.

### Registers in `standOff`

Resolved people, organisations and places are stored in TEI registers. Inline Mentions point to these records.

```xml
<standOff type="registers">
  <listPerson>
    <person xml:id="person-1">
      <persName>Hans</persName>
    </person>
  </listPerson>
  <listOrg>
    <org xml:id="org-1">
      <orgName>Hofhaltung</orgName>
    </org>
  </listOrg>
  <listPlace>
    <place xml:id="place-1">
      <placeName>Rattenberg</placeName>
    </place>
  </listPlace>
</standOff>
```

Register labels record preferred project forms and source-supported variants. An inline Mention preserves its exact wording. Every link between Mention and Entity is recoverable as an Assertion with responsibility and status.

### Units in the TEI header

Historical units and currencies are declared in `<unitDecl>` with one `<unitDef>` per distinct Unit. Each definition records labels, abbreviations, unit type, applicable place and period where known, and bibliographic or archival evidence.

```xml
<unitDecl>
  <unitDef xml:id="unit-star" type="capacity">
    <label>Star</label>
  </unitDef>
  <unitDef xml:id="unit-lb-pfennig" type="currency">
    <label>Pfund Pfennig</label>
    <label type="abbr">lb. d.</label>
  </unitDef>
</unitDecl>
```

The abbreviated Unit Mention remains inside `<measure>`. `@unitRef` points to the editorially accepted Unit. Ambiguous unit resolution leaves `@unitRef` absent until an Assertion is editorially accepted.

Conversion statements require geographical, temporal and evidential scope. The build preserves original Measures even where editorially accepted conversions exist. Derived values are published as derived Assertions with their conversion rule and provenance.

### Separate taxonomies

`<classDecl>` contains separate taxonomies for different editorial functions.

| Taxonomy | Purpose |
|---|---|
| Source-rubric taxonomy | Historical headings and documentary organisation |
| Account taxonomy | Accounts and Account Categories used for analysis |
| Commodity taxonomy | Commodity Categories used to classify Economic Goods and Measures |

```xml
<classDecl>
  <taxonomy xml:id="tax-source-rubrics">
    <category xml:id="rubric-provisions">
      <catDesc>Provisioning rubric attested in the source</catDesc>
    </category>
  </taxonomy>
  <taxonomy xml:id="tax-accounts">
    <category xml:id="account-expenditure">
      <catDesc>Expenditure</catDesc>
    </category>
  </taxonomy>
  <taxonomy xml:id="tax-commodities">
    <category xml:id="commodity-grain">
      <catDesc>Grain</catDesc>
      <category xml:id="commodity-rye">
        <catDesc>Rye</catDesc>
      </category>
    </category>
  </taxonomy>
</classDecl>
```

A Source Rubric may be mapped to an Account or Account Category through an editorially accepted Assertion. The source-rubric taxonomy does not double as the analytical account taxonomy. Commodity-category links preserve the Measure and Economic Good that support the classification.

## DEPCHA and Bookkeeping Ontology crosswalk

DoCTA uses Bookkeeping Ontology 1.3 as the conceptual reference for its application profile. The pinned source is the HistInfo repository at commit `a662cd9759c49b1f2bad5fbc7679d899137923c6`. Its namespace is `https://gams.uni-graz.at/o:depcha.bookkeeping#`.

The ontology separates Transaction and Transfer from the documentation-layer Entry. It also distinguishes AgentMention from EconomicAgent and UnitMention from Unit. The DoCTA concepts Mention and Entity generalise the same distinction between a source form and an authority record beyond agents. The local Assertion object records responsibility, evidence and editorial decision for mappings and interpreted relations.

The DoCTA application profile fixes the following cardinality rule. An Entry documents zero or more Transactions, and a Transaction is evidenced by one or more Entries. Bookkeeping Ontology 1.3 specifies `bk:entry [1..1]` for a Transaction. DoCTA therefore changes the Transaction-to-Entry cardinality to `1..*` and defines the inverse Entry-to-Transaction cardinality as `0..*`.

The pilot still requires a pinned application-profile crosswalk. The crosswalk must identify:

- the exact TEI `@ana` tokens used by DoCTA;
- the mapping of every DoCTA class and relation;
- mappings classified as exact, narrower, broader or project extension;
- cardinalities used by TEI generation and RDF validation;
- every DoCTA cardinality that departs from Bookkeeping Ontology 1.3;
- treatment of totals, subtotals, liabilities, settlement and accounting activities.

The crosswalk and SHACL profile must pin this cardinality deviation before real account-book annotations are produced. Every further deviation requires documentation and editorial acceptance before release. DEPCHA production version 1.2 remains a separate legacy profile whose established TEI practice can inform examples. It is not the normative ontology profile for the DoCTA account-book pilot. DoCTA makes no release claim about application-profile conformance until the versioned crosswalk is editorially accepted and the mappings pass the Reference Examples.

The crosswalk must not impose debit and credit structures on a source that does not encode them. `bk:from` and `bk:to` express editorially accepted Transfer direction. They are withheld where direction remains unsupported.

## XML validation

The pilot validates TEI in two schema stages and one rule stage.

### TEI P5 RELAX NG

The vendored and pinned `tei_all.rng` checks general TEI P5 conformance. Its version is recorded with the validation result.

### Project RELAX NG

A hand-written `docta-accounts.rng` checks the permitted project grammar. It constrains the elements, attributes, nesting, identifier patterns and closed status vocabularies emitted by the deterministic generator.

The project schema covers the inline `seg` structure, name elements, date and measure encoding, `standOff` registers, `unitDecl` and the three taxonomy functions. It remains a pilot-specific schema. The existing inventory schema retains its current scope.

### Schematron

A standalone `docta-accounts.sch` checks relations that RELAX NG cannot express adequately. Its rules include:

- resolution of every `@ref`, `@unitRef`, `@corresp`, `@facs` and local `@ana` pointer;
- correct target types for person, organisation, place, Unit and taxonomy references;
- stable identifiers for Entries, Transactions and Transfers;
- one or more Entry references on every Transaction and reciprocal Transaction references on every supporting Entry;
- containment of each Transfer in an editorially accepted Transaction representation;
- at least one source evidence link for every released Transaction and Transfer;
- consistency between Measure interpretation and Unit declaration;
- separation of Source Rubric, Account and Account Category references;
- exclusion of stale, rejected and superseded Assertions from released TEI;
- consistency between declared status, responsibility and revision provenance.

Passing RELAX NG and Schematron establishes formal validity. It does not establish a correct reading, Entity identity, Transfer direction or historical interpretation.

## RDF projection

The RDF graph is a deterministic projection of the released TEI and its pinned crosswalk. TEI `xml:id` values generate stable project IRIs. Inline Mentions retain links to the Transcription Revision and facsimile evidence. Register entries generate Entity resources. Editorially accepted accounting segments and relations generate Entry, Transaction, Transfer, Measure, Unit, Account and category resources.

The projection preserves:

- the relation between every RDF resource and its TEI source element;
- the relation between every source-bound Assertion and its facsimile evidence;
- provenance for Transcription Revisions, annotations, editorial decisions and generation;
- original Measure and Unit Mention text alongside editorially accepted normalisations;
- hierarchy and labels for account and commodity categories.

The mapper creates no inferred agent, direction, unit, conversion or category. Reasoning and exploratory aggregation run over the explicit graph or a separately identified derived graph.

## SHACL validation

SHACL validates the structure of the RDF projection against the pinned DoCTA profile. Shapes cover at least the following constraints:

- every Transaction is evidenced by one or more Entry resources and has at least one Transfer;
- every Transfer belongs to a Transaction and identifies at least one transferred resource;
- every Measure preserves a source Mention and links to a Unit when unit resolution is editorially accepted;
- every Entity link can be traced to a Mention and an editorially accepted Assertion;
- every Account Category and Commodity Category belongs to its declared scheme;
- every published Assertion is editorially accepted and derived from the Transcription Revision named in the Edition Build Manifest;
- every TEI-derived IRI resolves back to the expected TEI identifier.

Missing source or target agents can be valid when the source leaves them unidentified. SHACL records these cases as warnings where the research use benefits from explicit incompleteness. Missing source evidence, transferred resource or provenance is a validation failure.

SHACL establishes conformance of the graph to the profile. Historical validity remains an editorial responsibility.

## Deterministic build

The publication build performs the following operations in a fixed order:

1. Load the Edition Build Manifest and verify every input digest.
2. Validate Transcription Revisions, Mentions, Assertions, register snapshots, units and taxonomies against their JSON Schemas.
3. Exclude records whose editorial decision or revision dependency prevents release.
4. Generate TEI with stable identifiers and deterministic ordering.
5. Validate TEI against the pinned TEI P5 RELAX NG, project RELAX NG and Schematron.
6. Generate RDF from the valid TEI and pinned crosswalk.
7. Validate RDF with SHACL.
8. Compare object counts, identifiers and source links across the Edition Build Manifest, TEI and RDF.
9. Rebuild in a clean temporary directory and compare outputs byte for byte.

The build uses explicit dates and versions from its inputs. System time, filesystem order and network responses cannot alter released bytes. A model call, unresolved reference, failed validation or stale Assertion stops the release build.

## Reference Examples and Test Fixtures

A Reference Example supplies a bounded, source-backed and editorially accepted instance of the model. It records the Digital Facsimile, Transcription Revision, Mentions, Assertions, TEI and expected RDF interpretation.

A Test Fixture supplies frozen machine-readable input and expected output for an automated test. A fixture may implement a Reference Example or a synthetic edge case. The fixture inherits scholarly status only through an explicit link to a Reference Example and its editorially accepted version.

The encoding specification requires candidate examples for simple payment, commodity flow, liability, settlement, missing agent, multiple Transfers, compound currency, uncertain numeral, rubric inheritance, total or subtotal and cancellation. A candidate becomes a Reference Example only after it has been checked against its Digital Facsimile and editorially accepted by the responsible editor.
