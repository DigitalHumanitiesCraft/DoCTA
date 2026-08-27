# DESIGN: Design and Interaction Decisions

This document records which design options were considered and which were rejected, each with its reason. Under the Promptotyping principle the decision logic is the reproducible part; the code is disposable.

**Reference implementation:** [coOCR/HTR](https://github.com/DigitalHumanitiesCraft/co-ocr-htr). The opening question was which patterns of the sister project to adopt and which to leave.

## 1. Architecture: what was deliberately not adopted

| Pattern in coOCR/HTR | Decision | Reason |
|---|---|---|
| Ten modular CSS files | No, a single `styles.css` | At this size modularisation is effort without return |
| Central state management (`AppState extends EventTarget`) | No | The pages are independent and there is no live interaction across pages |
| A service and component hierarchy | No, a flat `app.js`, `data-loader.js`, `utils.js` | Sufficient for a handful of static pages |
| A progressive web app with a service worker | No | The site has no offline use case |

These four refusals are the reason the project works without a build process. Reversing any one of them undoes the consequence for the others.

## 2. Architecture: what was adopted

| Pattern | Implemented in | Note |
|---|---|---|
| Knowledge vault as its own page | `knowledge.html` | Sidebar plus Markdown rendering through marked.js, hash routing |
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

### The relation network of an edited source

`exploration.html` shows what the pipeline itself produces, the entities and relations extracted from one validated transcription, currently the Thaur inventory A 49.1. The graph is small enough that a `cose` layout over the whole set is the right answer and progressive disclosure would only add friction. Node size follows the number of attested relations, edge labels carry the relation type as the source gives it, and selecting a node names its role in that source. Every node keeps a route back to the facsimile through the viewer.

## 4. Rule-bound review status

Extracted entities and relations carry the values secure, worth checking and problematic. The current implementation still takes that grading from the model output and therefore holds no epistemic validity of its own.

The next iteration binds the display to documented workflow states. Secure presupposes a deterministic check or a scholarly verification. Worth checking marks an open comparison against image or source. Problematic marks a recognised contradiction, a strong divergence between models or a violated rule. Percentage self-assessments produced by a language model are never displayed. See CONTEXT.md on epistemic asymmetry and HTR-EVALUATION.md on the review contract.

## 5. Rejected and open

| Idea | State | Reason |
|---|---|---|
| A map view of the places | Rejected for the prototype | A substantial share of the SiCProD places carry no coordinates. A map with systematic gaps suggests a completeness that is not there |
| A period filter as a slider | Not built | The datings in SiCProD are too heterogeneous for a continuous axis |
| A German and English bilingual site | Resolved by the August 2026 refactor | The site and the knowledge base are English throughout; German remains for shelfmarks, source titles and quoted source text |
| A line overlay in the viewer, coupling image and transcription | Open | The coordinates are ready in `data/transcriptions/*.json` under `regions[].lines[].coords` |
| A separate edition page | Folded into the viewer, 2026-08-27 | The page duplicated the viewer while no approved edition text exists. The viewer now carries a reading mode over the whole document text; a dedicated edition page returns once approved TEI text is available |

## 6. Colour system

| Meaning | Value |
|---|---|
| Person | `#1565c0` |
| Place | `#2e7d32` |
| Function | `#6a1b9a` |
| Institution | `#e65100` |
| Object | `#e65100` |
| Review status secure | `#2d7d46` |
| Review status worth checking | `#c68a00` |
| Review status problematic | `#c62828` |

The entity colours have to agree in three places: the badge classes in `css/styles.css`, the Cytoscape node styles and the legend on the page carrying the graph. Object and institution currently share a value. That goes unnoticed because objects appear only in the extraction views and institutions only in the SiCProD data, which no page currently renders. Merging those views would force the conflict to be resolved.
