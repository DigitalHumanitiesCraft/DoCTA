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
updated: 2026-10-20
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

The viewer displays the archival title in full and distinguishes the document's extent from the transcribed pages in its pager, or from the available images of an image-only source. Image focus offers the full image or either half of an opening. These controls address the silver-inventory example where a blank facing page occupied much of the panel.

The local review interface distinguishes a browser draft from a saved edition correction. Saving and rebuilding are separate buttons, errors retain the draft, and a changed base revision requires reconciliation. Source-bound annotation starts from text selected by the editor and contains no automatic proposal. Neither a stored correction nor a successful build automatically approves a page.

The demo extraction of the prototype phase graded entities and relations as secure, worth checking and problematic. That grading came from the model output and held no epistemic validity. The working viewer no longer displays the extracted entities. The retained exploration view names their machine provenance and keeps them separate from the editor-owned register.

The `--conf-*` tokens of section 6 therefore grade no entity. They colour documented states of the text layer, namely the provenance chips, the machine-output badge, the review bar.

An entity's presentation names its producer and any recorded editorial decision. A deterministic match confirms that a quoted string occurs at its line anchor. It does not validate the historical identification or normalization. Percentage self-assessments produced by a language model are never displayed. See [domain-knowledge.md](domain-knowledge.md#epistemic-foundations) and [htr-evaluation.md](htr-evaluation.md).

## 5. Rejected and open

| Idea | State | Reason |
|---|---|---|
| A map view of the places | Rejected for the prototype | A substantial share of the SiCProD places carry no coordinates. A map with systematic gaps suggests a completeness that is not there |
| A period filter as a slider | Not built | The datings in SiCProD are too heterogeneous for a continuous axis |
| Interface language | English throughout, decided by the operator on 2026-10-20 | The working editor and the guide follow the surrounding site. The historical project lead asked for a fully English working edition for a proposal. German remains only in source text and in the stored data vocabulary, which `vocabLabel` (`docs/js/utils.js`) displays with English labels. The German task labels of the 2026-09-21 walkthrough are superseded |
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

The Edit control exposes reviewer initials, save and discard. The operator rejected page approval stages and all time tracking during the walkthrough. Corrections record the before and after reading, actor and save time. Controlled terms use the shared source-bound annotation field. The separate research-tag dialog is retired. Narrow windows wrap the row without clipping controls. Reading text, TEI, draft export and the dated edition build are accessed through More, which opens the More functions dialog. On static hosting a persistent read-only hint (`#readonly-hint`) states that annotating and saving require the local working edition and links to `guide.html#launch`, because the annotate controls are hidden there. The transcription header is one row, revised on 2026-10-20 after the operator found three stacked rows with mixed status and actions. The title is followed by one status pill, and the actions follow on the right: Edit, Annotate and Register (local editor only), text size and More. Status is a rounded pill with a state dot, actions are square controls with an icon and a short label. Narrower panels show the secondary actions and finally Edit as icons, keeping the label as accessible name and tooltip. The pill states the document's text attribution and qualifies it by the current page's state, so attribution and page state never contradict each other: Machine transcription, unrevised; Machine transcription, n lines corrected, otherwise unrevised; Transkribus HTR, correction not recorded; Inventaria, corrected; Transkribus, corrected. An unsaved draft switches the pill to Unsaved changes. The dot reinforces the wording and never carries the state alone. Amber marks machine text, blue text corrected in DoCTA, green a human-corrected source transcription and red an unsaved draft; the blue is a state token of its own (`--state-corrected`), apart from the brown accent of the controls and the person blue of the entity palette. During a draft the details keep every field below the draft note, so the attribution stays visible. A line in correction offers Mark as unclear and Delete line beside its input; focus may move between the three without ending the edit. Unclear marks stay as written with a dotted underline and their tooltip, so the line text and every annotation offset are unchanged. A deleted line stays in place, muted and struck through, and offers Restore only in correction mode; the reading text leaves it out. Work progress shows as one dot per held page under the facsimile toolbar, in the pill colours: blue for a page with a saved DoCTA correction, amber for unrevised machine text or a page whose correction is not recorded, green where every page of the document is marked done at its source, grey where only some are, because the served data carries the done status per document, and hollow for a page without text. A dot opens its page and takes no tab stop, since the pager remains the keyboard route; above 80 pages the dots are left out. The source header states n of m transcribed pages corrected in DoCTA, and the source overview names the pages corrected in DoCTA from the register summary. Progress is no approval and says so in no wording. An occurrence across a line break is selected in one drag from the first line into the next; the workspace title shows its segments with a slash at the break, every segment is marked, and only the first takes a tab stop. The line count is the `changedLines` field the served page carries, the number of lines whose saved reading differs from the Transkribus export or the machine transcription. Local payload and published projection carry the same count, so a corrected page of a DoCTA transcription states Machine transcription, n lines corrected, otherwise unrevised in both modes, and the details note keeps the remaining lines named as unrevised machine transcription. A locally corrected page without the count states that corrections are saved. Outside the synopsis, where no page is current, a corrected document in the published projection states Machine transcription, partly corrected, otherwise unrevised. An Inventaria document keeps an edition link beside the pill. The pill opens a nonmodal details surface with the description of the text layer, model and date of the transcription or its source, the corrected lines with corrector and date, and the document's page coverage; Escape closes it and returns focus to the pill. The former page provenance row, the separate coverage text and the separate draft badge are retired. That wording and the other provenance statements live in `docs/js/strings.js`, so the browser tests assert the shipped text. Remaining native dialogs support Escape and restore focus. Tooltips name the action of the next press, so a toggle such as the line regions switches between Show and Hide, and append a working shortcut in parentheses, letters uppercase and arrows as symbols, as in Rotate left (Shift+R) or Next page (→). A tooltip carries no final period and does not merely repeat a visible label. Save persists corrections; updating the edition derives and validates the output from saved text. The build refuses to proceed while transcription drafts remain unsaved.

The interface retains the existing palette and no-build modules. Decorative horizontal separators are excluded, and the operator excluded middle-dot separators from every page on 2026-10-20; commas, sentence boundaries or spacing take their place. Spacing and alignment separate groups, while control borders retain their interaction function. The page controller lives in `js/viewer.js`, with the workspace layout in `css/viewer.css`. Acceptance of the revised workflow belongs to the continuing [joint walkthrough](plan.md#joint-walkthrough).

Selecting a saved source passage opens one anchored nonmodal annotation field. Person, Term, Place and Date select its category. The same field holds the quotation, register assignment, entry creation and editing, date interpretation, notes and occurrence history. Machine proposals are excluded from this interface, so the historical editor constructs the index and vocabulary through her own assignments. Right-click is optional, and the explicit Annotate button and Alt+A offer equivalent entry points. Clicking a saved editorial mark opens this field. Inspection alone creates no unsaved assignment.

The annotation field uses lateral space when its controls cannot fit above or below the quotation. Narrow layouts retain an internal scroll area while preserving the source anchor. Register opens a collapsible sidebar for persons, places and terms. Local search considers preferred names and variants without merging equal names. Entry descriptions distinguish otherwise identical names. Occurrences return to the source, while unresolved occurrences remain findable. Unsaved text changes block new assignments, and changed saved text marks existing assignments for rechecking. Closing the inline editor retains its draft behind Continue annotation. Navigation to another source requires saving or explicit discard. The research question and source evidence govern identity and vocabulary decisions.

The joint acceptance exercise checks whether the editor can select a passage, choose its category, find an existing entry or create one, save, return to the reading and reopen the same occurrence without losing source context. It also checks whether an assigned identity and an unresolved identification remain distinguishable and whether the Index view leads back to the right source occurrence. Technical checks establish persistence and keyboard access, while the historical editor assesses whether the interaction serves the research task.

Index beside Viewer opens a dedicated page for the saved persons, places and controlled vocabulary. Search and category filters expose the entries already built by the editor, with aliases, notes, broader terms and exact source links. The page reads the editorial register only. It shows an explicit unavailable state outside the local editor and does not substitute generated extraction data.

## Source selection

The source overview supports finding material and opening it. Search, category and availability filters precede the source list. Each row shows title, shelfmark, historical date, documented extent, availability and transcription attribution. A stored first image remains distinguishable from a complete image set. Pipeline progress, stage initials and introductory method prose are excluded from this working entry point. Research preview beside the brand links to the project explanation. Spacing separates rows and metadata without decorative horizontal rules or separator dots.
