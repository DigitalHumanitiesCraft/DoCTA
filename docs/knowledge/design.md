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
updated: 2026-08-28
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

### The entity network of the extracted sources

`exploration.html` shows the aggregated entity layer of every document with an extraction, drawn with D3 from `data/graph.jsonld`. The single-source Cytoscape demo network over the Thaur inventory, with hand-made typed relations and always-on edge labels, was replaced on 2026-08-28: the displayed relations are now only what the data derivably holds, attestation of an entity in a document and co-occurrence of two entities in one transcription line, and edge labels are gone in favour of tooltips and a detail card. Typed relations return only when a relation extraction with full provenance exists. The graph is small enough for a live force layout over the whole set; node size follows the number of attestations, and every attestation keeps a route back to the facsimile through the viewer.

## 4. Rule-bound review status

Extracted entities and relations carry the values secure, worth checking and problematic. The current implementation still takes that grading from the model output and therefore holds no epistemic validity of its own.

The next iteration binds the display to documented workflow states. Secure presupposes a deterministic check or a scholarly verification. Worth checking marks an open comparison against image or source. Problematic marks a recognised contradiction, a strong divergence between models or a violated rule. Percentage self-assessments produced by a language model are never displayed. See domain-knowledge.md on epistemic asymmetry and htr-evaluation.md on the review contract.

## 5. Rejected and open

| Idea | State | Reason |
|---|---|---|
| A map view of the places | Rejected for the prototype | A substantial share of the SiCProD places carry no coordinates. A map with systematic gaps suggests a completeness that is not there |
| A period filter as a slider | Not built | The datings in SiCProD are too heterogeneous for a continuous axis |
| A German and English bilingual site | Resolved by the August 2026 refactor | The site and the knowledge base are English throughout; German remains for shelfmarks, source titles and quoted source text |
| A line overlay in the viewer, coupling image and transcription | Open | The coordinates are ready in `data/transcriptions/*.json` under `regions[].lines[].coords` |
| A separate edition page | Folded into the viewer, 2026-08-27 | The page duplicated the viewer while no accepted edition text exists. The viewer now carries a reading mode over the whole document text; a dedicated edition page returns once editorially accepted TEI text is available |

## 6. Colour system

All colours live in the token block at the top of `css/styles.css`; no raw hex value stands anywhere else in the stylesheet.

| Meaning | Token | Foreground | Background |
|---|---|---|---|
| Person | `--ent-person` | `#2b4c7e` | `#e6ecf4` |
| Place | `--ent-place` | `#2f6446` | `#e5efe8` |
| Object | `--ent-object` | `#a74320` | `#f8e9e3` |
| Time | `--ent-time` | `#6d3d78` | `#f0e8f2` |
| Institution | `--ent-institution` | `#175c6d` | `#e2eef1` |
| Function | `--ent-function` | `#5d5a1c` | `#efedda` |
| Review status secure | `--conf-high` | `#2d7d46` | `#e8f5e9` |
| Review status worth checking | `--conf-medium` | `#8a6100` | `#fff8e1` |
| Review status problematic | `--conf-low` | `#c62828` | `#ffebee` |

The six entity hues are muted against the warm ground `#faf8f5`, and each foreground holds at least 4.5:1 on its own background pair, on the page background and on the white surface. Every entity type carries a distinct hue, so a shared value can no longer make two types indistinguishable where the extraction views and the SiCProD data meet.

The palette replaced a set of saturated Material hues. Three of those values survive as the XML syntax colours of the TEI display, `--tei-tag` `#6a1b9a`, `--tei-attr` `#1565c0` and `--tei-val` `#2e7d32`, where they carry no entity meaning at all.

The entity colours have to agree in three places, the badge classes in `css/styles.css`, the D3 node fills (read from the same CSS tokens at runtime) and the legend controls on the page carrying the graph.
