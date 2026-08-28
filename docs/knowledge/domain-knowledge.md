# CONTEXT: Domain Knowledge, Methods, Epistemology

## Hypothesis

Semantic annotation and event modelling make it possible to reconstruct patterns of action that stay invisible under conventional source analysis.

## Three analytical dimensions

| Dimension | Question | Methods |
|-----------|----------|---------|
| Court practices | How did practices work in the courtly environment? | Network analysis, event extraction |
| Possession and object movement | How did possession and the transfer of objects contribute to practices? | Patterns of circulation (purchase, gift, pledge) |
| Spatial structures | Which hierarchies existed and how did they shape interaction? | Movement patterns, access, use of space |

## The SiCPAS data model

**SiCPAS** stands for Sigmund's Court Practices and Structures.

### Entities

| Entity | Information captured | In the prototype |
|--------|----------------------|------------------|
| **person** | Names, titles, roles. Agent or patient in events. | Yes |
| **place** | Geographical places (Innsbruck, Sigmundsberg) | Yes |
| **space** | Functional spaces (chamber, kitchen, stable, women's quarters) | Merged with place |
| **thing** | Objects of everyday use (bread, wine, wood) and of value (gold, silk, jewellery). Attributes: size, number, material, category, quality, colour, function. | Yes, under the label `object` |
| **time** | Datings and periods | Yes |
| **practice** | Actions as trigger verbs (predicates and verb forms) | Not as an entity type, see below |
| **group** | Institutions (council, chancery, kitchen staff) | After the prototype |
| **court** | Court affiliation (social group, profession) | After the prototype |
| **source** | Source genre and metadata | After the prototype |

**The prototype set uses four entity types.** The entity-extraction demo (`data/demo/thaur_entities.json`, the Thaur inventory A 49.1 of 1471) annotates `object`, `person`, `place` and `time`.

Two departures from the SiCPAS model need to be named, because they read easily as carelessness.

1. **`object` instead of `thing`.** The demo uses the coarser label that SiCPAS deliberately leaves behind (see the category discrepancy below). This is a legacy of the first annotation round rather than a modelling decision. In the full project `thing` holds, with the attributes size, number, material, category, quality, colour and function.
2. **`practice` is not a separate entity type in the prototype.** Practices appear instead as predicates of the extracted relations (`data/demo/thaur_relations.json`, with a `predicateType` drawn from eight classes such as inventorying, possession, handover, object transfer, habitation and testimony). The reference to action is present, modelled at the edge rather than at the node. Whether practices have to become nodes of their own is decided by the mapping between practice and BeNASch.

The finer distinctions place versus space and group versus court are not implemented in the prototype and are presented in the proposal as a planned extension.

**Category discrepancy.** The proposal for the first submission defined six categories in its Table 2, among them "object" and "organization". SiCPAS differentiates more finely, with "thing" in place of "object" and "group" and "court" in place of "organization". The prototype set is a pragmatic compromise and still sits terminologically at the level of the proposal.

### Relations

| Type | Meaning |
|------|---------|
| belongs_to | Ownership |
| located_in | Spatial assignment |
| related_to | General (kinship, hierarchy) |
| part_of | Part and whole |
| used_by | Relation of use |

### Event modelling

Two conceptual levels:

| Level | Definition | Example | Who annotates |
|-------|------------|---------|---------------|
| **Practice** | A single action, a trigger verb, agent and patient | "buy", "give", "cook" | Model plus validation |
| **Event** | A nameable cluster of persons, things and practices | Wedding, feast, transaction | **The project's domain expert only**, because the step is interpretative |

Practice annotation follows the BeNASch scheme. Aggregating practices into events is an interpretative act.

### Praxeological verb classes

The verbs are given in the source language, because the classification operates on the German terms the sources carry.

| Class | Verbs |
|-------|-------|
| Economic | kaufen, verkaufen, schenken, vererben, leihen, verpfänden, stehlen, zählen, wiegen, messen, verwalten |
| Aesthetic | genießen, bewundern, beschreiben, vergleichen, schätzen |
| Body-related | essen, trinken, schlafen, reinigen, pflegen, baden |
| Representational | jagen, tanzen, ausstellen, konsumieren, korrespondieren |
| Productive | reinigen, reparieren, kochen, herstellen |

**Open problem.** The verb classes follow a historical and substantive logic while BeNASch follows a linguistic and formal one. A mapping worked out on a handful of example entries is needed, ideally together with the Bern team.

## The BeNASch annotation scheme

**BeNASch** stands for Bernese Early New High German Annotation Scheme. It is ACE-based and compatible with CIDOC-CRM.

It models events formally as trigger verb, then agent, then patient. The annotation platform is INCEpTION; the named-entity models used are FLAIR, BERT and SpaCy.

**The link between practice and BeNASch is not yet operational.** The two systematics are differently motivated, and the concrete mapping is outstanding.

## Case studies

| Case study | Sources | State |
|------------|---------|-------|
| **The court kitchen** (recommended for the prototype) | Account books (payments), inventories (kitchen equipment) | A possible mention of a master of the kitchen in account book 2, fol. 2r; verification by the project lead outstanding |
| The ducal private chambers | Inventories, court ordinances | Not begun |
| Medical personnel | Account books, spatial analysis | Not begun |
| Luxury consumption | Account books, inventories | Not begun |

**The decision is open.** Three options stand. The first searches account book 2 for kitchen categories, the second treats the category "Provision und Sold" as a study in its own right, and the third chooses a different account book. For the funding strategy what counts is methodological persuasiveness rather than the specific case study.

## Mapping SiCProD onto SiCPAS

| SiCProD entity | SiCPAS entity | Note |
|----------------|---------------|------|
| Person | person | Direct |
| Place | place | The place/space distinction is absent in SiCProD |
| Institution | group or court | Most records untyped, assignment unclear |
| Function | practice (trigger) | Functions are distinct from practices, but a bridge exists |
| Salary | no counterpart | Links person to function, carries no monetary amounts |
| Event | event | Major events only, no everyday practices |
| Relation | relations | Relation types have to be mapped onto SiCPAS |

Current counts for the exported entities are in `data/stats.json`; see DATA.md for the quality of each entity type.

## Cooperation partners

| Partner | Contribution | Relevance to the prototype |
|---------|--------------|----------------------------|
| **SiCProD** (Innsbruck) | Prosopographic database with a public API | **Primary data source** |
| **BeNASch** (Bern) | Annotation scheme for Early New High German | Scheme compatibility |
| **The Flow Project** (Bern and Bielefeld) | Deep learning for event and relation extraction | Methodological alignment |
| **Inventaria** (Salzburg and Innsbruck) | Object thesaurus aligned with the Getty AAT, published inventory editions | Object classification, third priority |
| **DEPCHA** (Graz) | Semantics of account books | Structural models for the account books |
| **ZB Zurich** | A parallel coOCR/HTR application case | Sustainability argument |
| **VieCPro** (Vienna) | The early modern Viennese court | Comparative perspective |
| **ManMax** (Vienna) | Research consortium on Maximilian | Method transfer |

## Epistemic foundations

### Epistemic asymmetry

Language models give no reliable self-assessment of their own output. This is an **architectural property** rather than a temporary deficit. References: Zheng et al. 2023 on systematic biases, Wang et al. 2024 on position bias, Ye et al. 2024 on authority bias.

**Consequence for the pipeline.** Numerical self-assessments produced by a model (0.87, 0.93) are misleading. The categories secure, worth checking and problematic have to be bound to observable checking rules or to a human decision. A model statement about its own uncertainty serves triage and nothing else.

### Critical expert in the loop

The domain expert takes the decision about validity. The research tool supplies the facsimile, the competing readings, the provenance and the checking signals. Aggregating practices into events remains an interpretative act with documented scholarly responsibility.

### Hybrid checking, carried over from coOCR/HTR

| Status | Method | Validity |
|--------|--------|----------|
| Generated | HTR or a vision-language model | A model proposal with full provenance |
| Automatically checked | Rules, schemas, sums and model comparison | Marked consistency or divergence |
| Agentically reviewed | Palaeographic, linguistic, structural and domain-specific critique | A reasoned review signal |
| Facsimile-verified | Human comparison of image and text | Evidence for the named transcription scope |
| Editorially accepted | Decision by the project lead or a named domain expert | Accepted edition data |

A model acting as judge can prioritise contradictions and conspicuous passages. It confers no truth status and no release status on an output. For transcription the reference classes and metrics of `HTR-EVALUATION.md` apply.

### Methodological positioning

Language models serve as prototyping instruments whose outputs are reviewed against source evidence and accepted through accountable domain expertise. Promptotyping is the iterative method that keeps this under source-critical control. This position still has to be written out as a short text module for the planned resubmission.

## Resource URLs

| Resource | URL |
|----------|-----|
| DoCTA on GitHub | https://github.com/DigitalHumanitiesCraft/DoCTA |
| DoCTA live site | https://dhcraft.org/DoCTA/ |
| SiCProD API | https://sicprod.acdh-dev.oeaw.ac.at/apis/api |
| BeNASch | https://dhbern.github.io/BeNASch/ |
| Inventaria | https://www.inventaria.at |
| DEPCHA | https://gams.uni-graz.at/context:depcha |
| Promptotyping | https://dhcraft.org/Promptotyping/ |
| coOCR/HTR demo | https://dhcraft.org/co-ocr-htr |
| coOCR/HTR repository | https://github.com/DigitalHumanitiesCraft/co-ocr-htr |
