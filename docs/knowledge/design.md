---
title: Design
project:
  name: DoCTA
  repository: https://github.com/DigitalHumanitiesCraft/DoCTA
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: complete
language: en
version: "1.0"
created: 2026-08-05
updated: 2026-09-21
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Fable 5)
template:
  name: Vorlage Design
  version: 0.2
  url: https://dhcraft.org/Promptotyping/promptotyping-document/design
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-design
related: [INDEX, architecture, specification]
---

# Design

The working interface supports source inspection, correction and research annotation. Maintained design decisions guide the versioned implementation and its regression checks.

**Reference implementation:** [coOCR/HTR](https://github.com/DigitalHumanitiesCraft/co-ocr-htr). The opening question was which patterns of the sister project to adopt and which to leave.

## 1. Architecture: what was deliberately not adopted

| Pattern in coOCR/HTR | Decision | Reason |
|---|---|---|
| A stylesheet hierarchy | Shared tokens in `styles.css`, scoped viewer layout in `viewer.css` | The working editor changes independently of the public overview pages |
| Central state management (`AppState extends EventTarget`) | No | The pages are independent and there is no live interaction across pages |
| A service and component hierarchy | No, a flat `app.js`, `data-loader.js`, `utils.js` | Sufficient for a handful of static pages |
| A progressive web app with a service worker | No | The site has no offline use case |

The static interface needs no build process. A change to one of these choices is evaluated against its concrete requirement and does not require adopting the other patterns.

## 2. Architecture: what was adopted

| Pattern | Implemented in | Note |
|---|---|---|
| Knowledge vault as its own page | removed 28.08.2026 | Rendered the Markdown documents with marked.js and hash routing; withdrawn because the knowledge base addresses agents and repository readers, and site visitors were not its audience |
| Rule-bound review status instead of percentages | Extraction views, CSS tokens | See section 4 |
| CSS custom properties as design tokens | `css/styles.css` | Colours, spacing, typography, radii |
| IndexedDB caching | `js/data-loader.js` | With a timeout, `onblocked` handling and a fallback |
| Warm archival palette | `css/styles.css` | Background `#faf8f5` identical to coOCR/HTR, accent `#8b5e3c` in place of gold |

## 3. Network views

### The SiCProD court network, prototype phase

The hardest design question of the prototype phase was that the SiCProD court network, several thousand persons connected by tens of thousands of relations, cannot be drawn as one graph.

| Option | Decision | Reason |
|---|---|---|
| Render the full graph | Rejected | Unreadable and slow, whichever library is used |
| The most central two hundred nodes as the default view | Rejected, though it ran until February 2026 | A hairball without a statement. Looking at it teaches nothing about the court |
| **The ego network as the default view** | **Chosen** | It answers the question users actually ask, namely whom a given person stood in relation to |
| A switchable full view | Chosen, bounded | It shows the structure of the best-connected entities without making the hairball the entry point |

The limits in the prototype code were fifty neighbours in the ego view and seventy-five nodes in the full view, with a `concentric` layout for the ego view so that the central person sits visibly in the middle and `cose` for the full view. Two constraints followed and were named on the page. The full view showed fewer nodes than its own ceiling, because nodes without an index entry and without a visible edge dropped out, so the caption reported the actual number. And the relation types `salary` and `event` are in principle not representable in that display.

The dedicated network page and the faceted search over SiCProD were removed when the site was consolidated in August 2026. The exported SiCProD data stay in `data/` and are currently loaded by no page. The design decisions above hold for the day the court network returns as a view over edited text.

### The entity network of the extracted sources

`exploration.html` shows the aggregated entity layer of every document with an extraction, drawn with D3 from `data/graph.jsonld`. The single-source Cytoscape demo network over the Thaur inventory, with hand-made typed relations and always-on edge labels, was replaced on 2026-08-28: the displayed relations are now only what the data derivably holds, attestation of an entity in a document and co-occurrence of two entities in one transcription line, and edge labels are gone in favour of tooltips and a detail card. Typed relations return only when a relation extraction with full provenance exists. The graph is small enough for a live force layout over the whole set; node size follows the number of attestations, and every attestation keeps a route back to the facsimile through the viewer.

## 4. Rule-bound review status

The viewer displays the archival title in full and distinguishes the document's extent from the available transcription pages in its pager. Image focus offers the full image or either half of an opening. These controls address the silver-inventory example where a blank facing page occupied much of the panel.

The local review interface distinguishes a browser draft from a saved edition correction. Saving and rebuilding are separate buttons, errors retain the draft, and a changed base revision requires reconciliation. Annotation curation appears only where anchored extraction proposals exist. Neither a stored correction nor a successful build automatically approves a page.

The demo extraction of the prototype phase graded entities and relations as secure, worth checking and problematic. That grading came from the model output and held no epistemic validity, and the display no longer uses it. The pipeline extraction under `data/entities/` carries no such field, because the entity prompt `pipeline/prompts/entities_it01.md` forbids one, and `js/data-loader.js` drops the grading of the demo file on reading. An entity is shown with its machine provenance, the extracting model and the label "not verified".

The `--conf-*` tokens of section 6 therefore grade no entity. They colour documented states of the text layer, namely the provenance chips, the machine-output badge, the segments of the progress bar and the review bar.

An entity's presentation names its producer and any recorded editorial decision. A deterministic match confirms that a quoted string occurs at its line anchor. It does not validate the historical identification or normalization. Percentage self-assessments produced by a language model are never displayed. See [domain-knowledge.md](domain-knowledge.md#epistemic-foundations) and [htr-evaluation.md](htr-evaluation.md).

## 5. Rejected and open

| Idea | State | Reason |
|---|---|---|
| A map view of the places | Rejected for the prototype | A substantial share of the SiCProD places carry no coordinates. A map with systematic gaps suggests a completeness that is not there |
| A period filter as a slider | Not built | The datings in SiCProD are too heterogeneous for a continuous axis |
| Interface language | German working editor, English surrounding site | The editorial walkthrough uses German task labels; repository knowledge remains English |
| A line overlay in the viewer, coupling image and transcription | Built | Drawn from `regions[].lines[].coords` in `data/transcriptions/*.json`, see architecture.md. Documents the pipeline transcribed itself carry no coordinates and get no overlay |
| A separate edition page | Folded into the viewer, 2026-08-27 | The page duplicated the viewer while no accepted edition text exists. The viewer now carries a reading mode over the whole document text; a dedicated edition page returns once editorially accepted TEI text is available |

## 6. Colour system

All colours live in the token block at the top of `css/styles.css`; no raw hex value stands anywhere else in the stylesheet.

| Meaning | Token | Foreground | Background |
|---|---|---|---|
| Person | `--ent-person` | `#2b4c7e` | `#e6ecf4` |
| Place | `--ent-place` | `#2f6446` | `#e5efe8` |
| Object | `--ent-object` | `#a74320` | `#f8e9e3` |
| Time | `--ent-time` | `#6d3d78` | `#f0e8f2` |
| Review status secure | `--conf-high` | `#2d7d46` | `#e8f5e9` |
| Review status worth checking | `--conf-medium` | `#8a6100` | `#fff8e1` |
| Review status problematic | `--conf-low` | `#c62828` | `#ffebee` |

The entity hues are muted against the warm ground `#faf8f5`, and each foreground holds at least 4.5:1 on its own background pair, on the page background and on the white surface. Every type of the extraction vocabulary carries a hue of its own, so a shared value can no longer make two types indistinguishable. The prototype phase additionally held hues for institution and function, the two SiCProD types; they left the token block together with the page that rendered them.

The palette replaced a set of saturated Material hues. Three of those values survive as the XML syntax colours of the TEI display, `--tei-tag` `#6a1b9a`, `--tei-attr` `#1565c0` and `--tei-val` `#2e7d32`, where they carry no entity meaning at all.

The entity colours have to agree in three places, the badge classes in `css/styles.css`, the D3 node fills (read from the same CSS tokens at runtime) and the legend controls on the page carrying the graph. Since 28.08.2026 shape is a fourth axis of the same rule: object nodes are triangles rather than circles in another hue, and the D3 marks, the filter chips and the legend carry the same shape, because meaning must not rest on colour alone.

## Working editor hierarchy

The joint walkthrough on 2026-09-21 established that the operator could identify the source and navigate its pages. The requested revision addresses the crowded metadata and editing controls. A shared source header presents the full archival title, shelfmark and historical date. A source-details dialog holds archive, category, archival unit and original-edition reference. Text attribution stays visible beside the transcription, independently of the current page's local review state. Separator dots are omitted.

The default workspace is the facsimile beside the transcription. Each newly opened image fits fully into the panel, including a photographed opening. Zoom and page-half focus remain deliberate inspection actions. The whole-page action restores the full image. The former fixed initial zoom could crop the top and bottom of a tall image.

The German control Bearbeiten exposes reviewer initials, save and discard. The operator rejected page approval stages and all time tracking during the walkthrough. Corrections record the before and after reading, actor and save time. Text provenance and annotation controls share one row. The provenance label links directly to the original edition. Free research tags and automatic entity proposals open in separate dialogs, leaving the transcription unobstructed when closed. Narrow windows wrap the row without clipping controls. Reading text, TEI, draft export and the dated edition build are accessed through Weitere Funktionen. Native dialogs support Escape and restore focus. Save persists corrections; updating the edition derives and validates the output from saved text. The build refuses to proceed while transcription drafts remain unsaved.

The interface retains the existing palette and no-build modules. The page controller lives in `js/viewer.js`, with the workspace layout in `css/viewer.css`. Acceptance of the revised workflow belongs to the continuing [joint walkthrough](plan.md#joint-walkthrough).

Clicking a highlighted machine mention opens its own decision form. Personen und Begriffe opens the editor-owned register, and Auswahl annotieren attaches a selected passage within one saved line to a person or term. Local search considers preferred names and variants without merging equal names. Entry descriptions distinguish otherwise identical names. Manual annotations have their own edit and removal dialog with change history. Unsaved transcription changes block new assignments, and changed saved text marks existing assignments for rechecking. Dialogs retain unsaved edits until explicit save or discard. The research question and source evidence govern identity and vocabulary decisions.
