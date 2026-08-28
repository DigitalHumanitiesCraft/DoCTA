---
title: Data
project:
  name: DoCTA
  repository: https://github.com/DigitalHumanitiesCraft/DoCTA
method:
  name: Promptotyping
  url: https://dhcraft.org/Promptotyping/
status: complete
language: en
version: "1.0"
created: 2026-02-18
updated: 2026-08-28
authors: [Christopher Pollin]
generated-with: Claude Code (Claude Fable 5)
template:
  name: Vorlage Datengrundlage
  version: 0.1
  url: https://dhcraft.org/Promptotyping/promptotyping-document/data
  alias: https://dhcraft.org/Promptotyping/#promptotyping-document-data
knowledge-sources:
  institutions:
    Digital Humanities Craft OG: https://dhcraft.org
  datasets:
    SiCProD: https://sicprod.acdh-dev.oeaw.ac.at/
    Transkribus collection 2197991: https://app.transkribus.org/collection/2197991
    Inventaria edition: https://www.inventaria.at/
related: [INDEX, specification, htr-evaluation, domain-knowledge]
---

# Data

This document describes the data DoCTA works with, what each source can carry and where it breaks. The site computes the figures it shows in the browser from `data/sources.json` and the register projection; figures given here characterise the collections at the stated verification date and are snapshots rather than live values.

## 1. SiCProD API

**Base:** `https://sicprod.acdh-dev.oeaw.ac.at/apis/api/`
Public, no authentication, JSON via `?format=json`. Paginated with `?limit=500&offset=0`.

SiCProD is the prosopographical database of Sigismund's court, built at the University of Innsbruck together with the Tyrolean State Archives and a partner research infrastructure. It supplies the persons, places, offices and relations the edition can link against.

### Entity API state checked 17.02.2026

| Type | Endpoint | Quality |
|------|----------|---------|
| Person | `apis_ontology.person/` | Good. Name, dates, gender, name variants, references. `first_name` is filled for all but seven records; `status` is empty throughout and therefore not exported. |
| Place | `apis_ontology.place/` | Medium. Type is present (town, castle, village). **Many records without lat/lng**, so any map will have systematic gaps. |
| Institution | `apis_ontology.institution/` | **Poor. The great majority carry no type.** Only a handful are typed as university, chancery, kitchen or parish. |
| Function | `apis_ontology.function/` | Good. Some eighty distinct court offices, mixing court positions and regional offices. |
| Salary | `apis_ontology.salary/` | **No monetary amounts.** Only links between person and function. |
| Event | `apis_ontology.event/` | **Major events only:** diets, imperial diets, weddings, battles. No everyday practices. |
| Relation | `relations.relation/` | Good. Subject to object with a type. The main value of the API. |

### Example: person (Sigismund, ID 18)

```json
{
  "id": 18,
  "name": "Sigmund von Tirol",
  "start_date_written": "1427-10-26",
  "end_date_written": "1496-03-04",
  "gender": "männlich",
  "first_name": "",
  "status": "",
  "alternative_label": [
    "Sigismund", "Siegmund", "Sigmund der Münzreiche",
    "Erzherzog zu Österreich, Steiermark, Kärnten und Krain, Graf zu Tirol"
  ],
  "relation_types": ["event", "person", "salary", "place"],
  "references": [
    {
      "notes": "Nr. 5840 (8.2.1459 Feldkirch)",
      "bibtex": { "title": "Acta Cusana...", "volume": "III/1", "issued": {"date-parts": [[2022]]} }
    }
  ]
}
```

Sigismund is one of the few records without a given name: `first_name` here is an empty string rather than null. For the remaining persons a given name is present and is shown in search and network views. The export `data/persons.json` reduces each record to `id`, `name`, `first_name`, `gender`, `start_date`, `end_date` and `alternative_label`. `status` is dropped because the field is empty in every record.

### Example: relation

```json
{
  "subj": {
    "label": "Sigmund von Tirol (ID: 18)",
    "content_type_key": "apis_ontology.person"
  },
  "obj": {
    "label": "Hochzeit Sigmund-Eleonore (ID: 17)",
    "content_type_key": "apis_ontology.event"
  },
  "relation_type": "nimmtteilan"
}
```

Relation types, a selection: `nimmtteilan` (takes part in), `wirdausgeuebtvon` (is exercised by), `istan` (is at), `wirdausbezahltanperson` (is paid to person), `hatfamilienbeziehungzu` (has family relation to), `istmitgliedvon` (is member of).

### Selected court offices

The office names below are given in the source language with a gloss, because the exact German term is what the data carry.

| Office | Relevance to case studies |
|--------|---------------------------|
| Hofmeister (court steward) | Court structure |
| Küchenmeister (master of the kitchen) | Court kitchen |
| Stallmeister (master of the horse) | Court structure |
| Marschall (marshal) | Court structure |
| Salzmair zu Hall (salt official at Hall) | Economy |
| Hauskämmerer (household chamberlain) | Private chambers |
| Hofarzt, Leibarzt Sigmunds (court physician, personal physician) | Medical personnel |
| Koch des Herzogs, Türhüter der Küche (the duke's cook, doorkeeper of the kitchen) | Court kitchen |
| Goldschmied, Hofmaler (goldsmith, court painter) | Luxury consumption |
| Schleierwäscherin, Trompeterin (veil washer, trumpeter) | Court structure, women |

The gender distribution is heavily male, with a small female group and a residue of unknown; the exact split is in the exported data.

### Core value and limits

**Core value:** a person network of several thousand persons connected by tens of thousands of relations.
**Limits:** events are nearly empty, salaries carry no amounts, institutions are untyped. Financial and praxeological data have to come from the account books, and SiCProD cannot supply them.

### Pre-fetch strategy

A Python script (`scripts/fetch_sicprod.py`) retrieves all entities page by page and the relations as an edge list. Output: `data/persons.json`, `data/places.json`, `data/institutions.json`, `data/functions.json`, `data/relations.json`, on the order of a few megabytes raw and roughly a megabyte gzipped.

A second script (`scripts/compute_layout.py`) pre-computes a network layout with networkx and writes `data/network.json`. That file is an exploration artifact from the prototype phase and is loaded by no current page.

## 2. Source catalogue (CSV)

**File:** `sources/quellen-katalog.csv`, cleaned into `data/sources.json` by `scripts/transform_sources.py`.

### Column structure

Of twenty-four columns only eight carry content.

| Column | Actual content | Problem |
|--------|----------------|---------|
| Kategorie | Source category | Fine |
| Signatur | Archival shelfmark | Fine |
| Titel | Description | Fine |
| Datierung | Date or period | **More than ten formats, en dash and hyphen used inconsistently** |
| Art | Mostly "Einzelstück" (single item) | The Repertorium rows misuse the field for extent |
| Projekt | SiCProD, Inventaria, DoCTA or empty | Fine |
| Digitalisiert | **An extent figure in free text** | Column name suggests a boolean, and the unit of the figure is nowhere stated |
| Transkribiert | Only "Inventaria" or empty | Column name misleading |
| Spalte3 to Spalte18 | **Entirely empty** | Excel export artifacts |

### Cleaned schema (`data/sources.json`)

One entry per catalogue row. Shelfmark, category, title, normalised dating, form, project and the Transkribiert flag pass through unchanged from the CSV. Two fields carry the extent, and they are in different units, which is why they are separate.

| Field | Meaning |
|-------|---------|
| `catalogue_extent` | The archival statement of the finding aid, or `null` where the catalogue gives none. `value` is the integer parsed from the Digitalisiert cell, `raw` is that cell verbatim so the parse stays checkable, `unit` is one of `seiten` (written sides), `bilder` (images or openings) and `unbekannt`. |
| `transkribus_docs` | Every Transkribus document of the shelfmark, with `doc_id`, `title`, `pages`, `lines`, `words` and `has_text`. Two rows carry two documents each (A 125.3-4, A 142.1-2); an earlier version indexed by shelfmark and silently dropped the second. The first entry is the document a deep link opens. |
| `digital_images` | Sum of the scans of those documents, from `nrOfPages` of the collection metadata. Zero where Transkribus holds nothing under the shelfmark. |

The unit of `catalogue_extent` is derived rather than recorded, because the CSV never states it. Account-book volumes get `bilder`, the A 006 and A 024 personal inventories get `seiten` where the figure is even and near twice the image count, and everything else stays `unbekannt`. A parse artifact stays visible instead of being smoothed over. A 194.1 carries `value` 1 against 40 scans, because the first integer of its Digitalisiert cell means something other than an extent.

The site shows the scan count as the primary figure per source and the catalogue extent beside it where the two diverge. The editorial progress bar counts digital images end to end and leaves the catalogue extent out of its denominator; an earlier version summed catalogue figures into the denominator while the numerator came from the register, which divided written sides by openings wherever the units differed.

### Availability pyramid

| Tier | State | Content |
|------|-------|---------|
| **1** | Digitized and transcribed | Castle inventories, full text in Transkribus. Several inventories were edited and published by the Inventaria project (see below). Two shelfmarks (A 125.3-4, A 142.1-2) each cover two Transkribus documents. |
| **2** | Digitized, not transcribed | Account books, copybooks, court ordinances, personal inventories |
| **3** | Identified, not digitized | The remainder, roughly two thirds of the catalogue |

### Category distribution

Measured against `data/sources.json`, that is, after cleaning. This is the state the source table on the home page shows.

| Category | Cleaned | Raw in CSV |
|----------|---------|------------|
| Castle inventory | 84 | 84 |
| Accounts | 56 | 56 |
| Other | 42 | 43 |
| Repertorium | 41 | 42 |
| Copybook | 37 | 37 |
| Personal inventory | 18 | 18 |
| Court and table ordinances | 16 | 16 |
| Literature | 9 | 9 |
| Church inventory | 6 | 6 |
| Records of the diets | 3 | 4 |
| **Total** | **312** | 315 |

The three differences come from the duplicates and cross-listings noted below.

### Known quality problems

1. Sixteen ghost columns (Spalte3 to Spalte18), Excel export artifacts
2. Date formats: `YYYY`, `YYYY-YYYY`, `YYYY.MM.DD`, `ca.`, `15. Jh.`, open ranges (`-1564`, `1229-`)
3. The Repertorium section uses a Unicode en dash while the rest uses an ASCII hyphen, which is a parser trap
4. A true duplicate: Hs. 0041 appears as two identical rows
5. A near duplicate: A 002.1 and A 2.1 are the same source, with a typo in one row
6. Cross-listed: Hs. 0048 and Hs. 0057 each appear in two categories
7. Temporal outliers: a handful of sources fall outside Sigismund's lifetime (1411 to 1645)
8. A date value in the Art column (row 304: "1361-1848")

### Account books (Raitbücher)

**Canonical count: 26 volumes, 8,561 pages.** This figure comes from the Transkribus collection, that is, from the digitized material actually present, and is used throughout the project.

The catalogue CSV gives different values.

| Count | Volumes | Pages | Origin |
|-------|---------|-------|--------|
| **Transkribus (canonical)** | **26** | **8,561** | Collection 2197991, counted scans |
| CSV and `data/sources.json` | 25 | 8,750 | Catalogue entries with an extent figure in the Digitalisiert column |

The CSV lists 25 entries (numbered 00 to 26, omitting 23 and 25, which the catalogue records as identical with 22 and 26). Transkribus counts the volumes individually and therefore arrives at 26.

The two page figures count the same thing. Compared volume by volume, 22 of the 25 catalogue entries equal the counted scans exactly, including the two volumes Transkribus splits across two documents (15 as 24 + 328, 20 as 43 + 396, both summing to the catalogue figure). The gap of 189 comes from coverage and grouping.

- Volume 00, 241 catalogue images, has no Transkribus document at all
- Volumes 22, 24 and 26 hold more scans than the catalogue records (517 against 494, 371 against 355, 308 against 294)
- Volume 17 differs by a single image (468 against 469)

An account-book image is one opening, meaning two written sides photographed together. The same holds for the A 006 booklets, where the catalogue counts the written sides and therefore reaches roughly twice the number of images. A figure that mixes the two units means nothing, and `data/sources.json` mixed them until the extent was split into `catalogue_extent` and `digital_images`. Where a defensible figure is needed, Transkribus governs.

| No. | Date | Images (CSV) | Note |
|-----|------|--------------|------|
| 00 | 1454–1457 | 241 | "Raitbuch von Konrad Vintler" |
| 01 | 1460–1461 | 331 | |
| **02** | **1462–1463** | **123** | **The volume the project works on** |
| 03 | 1463–1465 | 815 | Largest volume |
| 04–26 | 1466–1490 | 7,240 | 21 entries. Gaps at 1476 and 1481. 1485 appears twice (nos. 18 and 19). Nos. 23 and 25 are recorded as identical with 22 and 26 and are not listed separately. |
| **CSV total** | 1454–1490 | **8,750** | |

### Court ordinances (11 catalogue entries)

Among them a coherent cluster on Sigismund's wedding of 1484. The page figures are catalogue statements from the CSV; in brackets stands the counted number of scans in the Transkribus collection, which is consistently lower (see journal.md). Which of the two counts represents the complete volume is unresolved.

- Hs. 2466: "Notl der hochzeit", register of invitations, 60 pp. per CSV (33 scans)
- Hs. 2467: "Rescribent der hochzeit", instructions to the court offices, 100 pp. per CSV (58 scans)
- Hs. 2468: "Fueterzetl", guests and horses, 35 pp. per CSV (19 scans)
- Hs. 2469: register of Sigismund's wedding with Katharina of Saxony, 140 pp. per CSV (54 scans)

### Directly usable material

**Castle inventories with working transcriptions** are immediately available. A subset was edited and published by the Inventaria project on Transkribus Sites (see section 3); only published material is used, and it is used with attribution. The remaining transcriptions in the collection carry no documented formal ground-truth status and follow two different transcription conventions.

**Account book 2** is available as an image and layout source. Transkribus holds no text for it. Machine transcriptions from the benchmark and the pilot exist and are marked as unrevised model output.

Script output: `data/sources.json`, the cleaned catalogue as JSON for the source table on the home page, in the schema described above. `scripts/transform_sources.py --migrate` rewrites that file into the current schema without the CSV, which is project-internal and missing from the public clone; a `catalogue_extent.raw` of `null` marks a value that reached the file that way.

## 3. Transkribus collection 2197991

### API overview checked 17.02.2026

**Collection ID:** 2197991
**URL:** https://app.transkribus.org/collection/2197991
**Extent:** 115 documents, 12,236 pages

| Category | Documents | Pages | With transcription |
|----------|-----------|-------|--------------------|
| Castle inventories | 64 | 569 | 57 |
| Account books | 26 | 8,561 | 0 (layout analysis only, or empty) |
| Copybooks | 12 | 2,224 | 0 |
| Other (court ordinances, manuscripts) | 13 | 882 | 0 |

### Inventaria and the status of the inventory transcriptions

Several of the castle inventories were edited and published by the **Inventaria** project (led from the University of Salzburg with the University of Innsbruck) and are available as an edition on Transkribus Sites at https://www.inventaria.at/. DoCTA uses only material that Inventaria has published, and cites it with attribution to the Inventaria project wherever a transcription is displayed or evaluated.

The wider inventory stock in the collection is a different matter. The catalogue marks 55 inventories as transcribed; 57 documents actually carry text, two of them missing from the CSV marking (A 125.3-4 and A 142.1-2, each with two Transkribus document IDs). Three documents carry the Transkribus workflow status `DONE`, the rest `IN_PROGRESS`. The workflow status is not a scholarly approval and must never be used as a substitute for one. The canonical description of the stock is therefore **inventories with working transcriptions**, with a small `DONE` subset used as a reference anchor in the benchmark.

Two transcription conventions are present in the stock. Any comparison across documents needs a convention partition and a versioned adapter onto the DoCTA data contract. Reference classes and evaluation rules are in `htr-evaluation.md`.

**Account books.** All 26 volumes are digitized. Six volumes (nos. 1 to 6) have a layout analysis with baselines and regions; the remaining twenty carry the status `NEW`. No volume holds transcription text in Transkribus. Machine transcriptions live outside Transkribus under `evaluation/`, and they are unrevised model output.

### Rights and reuse of third-party material

Publication is not a licence. Material that is freely accessible on the web but carries no open licence is used in three tiers, and the rule is the same for every third-party source.

1. **Reference**, always permitted and the default. A direct link to the official publication plus a full citation in DoCTA, while the data itself stays where it is published.
2. **Quotation**, narrowly permitted. Small excerpts or screenshots where a concrete scholarly explanation requires them, always with full attribution; § 42f UrhG (AT) permits quotation only to the extent that this purpose justifies.
3. **Copying and republishing**, only with an open licence on the material or written permission from the rights holders. Until granted, a full copy stays local, unversioned and secured against public access, and only aggregate figures derived from it (error rates, error classes) are published.

Three precisions govern the Inventaria case. The Inventaria annotation collection is treated as a potentially protected database (§§ 76c–76d UrhG); sui generis protection presupposes a substantial investment in obtaining, verifying or presenting the contents, which is plausible for a scholarly annotation collection but has not been legally determined, so the cautious reading governs. The repository's CC BY 4.0 licence does not automatically capture third-party material that is clearly marked as excluded, but inclusion would still require its own authorization and create licence ambiguity; third-party material is therefore marked as such wherever it appears (attribution chips, citation lines, this document). A local research copy rests on § 42h UrhG, automated scholarly analysis under lawful access with storage secured for the research purpose; that is no general permission for arbitrary internal reuse, and such a copy never enters the repository or the website.

The base transcriptions of the Inventaria-transcribed inventories came into the repository through the shared Transkribus collection and are attributed wherever they are displayed or evaluated. The written permission sought from the Inventaria project covers this existing use and the planned use of the published annotations as evaluation ground truth; once granted, the permission and its licence terms are recorded in `journal.md`.

### Account books in the collection

| No. | Doc ID | Pages | Status |
|-----|--------|-------|--------|
| 1 | 12514207 | 331 | IN_PROGRESS (layout) |
| **2** | **12514730** | **123** | **IN_PROGRESS (layout, no text)** |
| 3 | 12515152 | 815 | IN_PROGRESS (layout) |
| 4 | 12515414 | 347 | IN_PROGRESS (layout) |
| 5 | 12515448 | 146 | IN_PROGRESS (layout) |
| 6 | 12515416 | 170 | IN_PROGRESS (layout) |
| 7–26 | various | 6,629 | NEW (images only) |

### API and authentication

**Endpoint:** `https://transkribus.eu/TrpServer/rest` (legacy REST API)
**Auth:** OpenID Connect via Keycloak (`account.readcoop.eu`), `client_id=transkribus-api-client`, `grant_type=password`.
**Credentials:** through the environment variables TRANSKRIBUS_USER and TRANSKRIBUS_PASS.

Relevant endpoints:

- `GET /collections/{colId}/list` returns the document list
- `GET /collections/{colId}/{docId}/fulldoc` returns all pages with metadata and PAGE XML URLs
- PAGE XML: `https://files.transkribus.eu/Get?id={KEY}` (auth header required)

### IIIF image access checked

```
https://files.transkribus.eu/iiif/2/{KEY}/full/{width},{height}/0/default.jpg
```

**Tested and confirmed:** IIIF URLs work **without authentication** in `<img>` and in `fetch()`. Example, account book 2, fol. 0v-1r:

- Thumbnail: `https://files.transkribus.eu/iiif/2/ISMVDKARQUBRQTZVDEQSWVHR/full/200,/0/default.jpg`
- Full: `https://files.transkribus.eu/iiif/2/ISMVDKARQUBRQTZVDEQSWVHR/full/max/0/default.jpg`

Direct URLs also work without authentication: `https://files.transkribus.eu/Get?fileType=view&id={KEY}`.

### PAGE XML format (example Thaur A 49.1)

```xml
<TextRegion type="page-number" id="r1">
  <Coords points="912,148 839,148 839,85 912,85"/>
  <TextLine id="r1l1">
    <Coords points="856,90 906,94 902,144 852,140"/>
    <Baseline points="852,135 902,139"/>
    <TextEquiv><Unicode>[1r]</Unicode></TextEquiv>
  </TextLine>
</TextRegion>
```

The structure is Page, then TextRegion (with type and coordinates), then TextLine (with coordinates, baseline and Unicode text). A ReadingOrder element defines the sequence of regions.

### CORS

The APIs were designed for a desktop client. A `fetch()` on PAGE XML is blocked in the browser by CORS. **Images are CORS-free.** Hence the pre-fetch strategy for transcriptions, while images load directly.

### Pre-fetch strategy

`scripts/fetch_transcriptions.py` authenticates via OAuth2, requests `fulldoc` per document, parses the PAGE XML and writes JSON with lines, coordinates and text. Output: `data/transcriptions/{doc_id}.json` and `data/raitbuch2_pages.json`. The page list is an exploration artifact that no page loads; the viewer takes its IIIF URLs from the transcription files themselves.

### Exploration checklist (closed)

- [x] Collection ID: 2197991
- [x] Transkribus credentials verified via environment variables
- [x] Document IDs enumerated, in `data/transkribus_collection.json`
- [x] IIIF URLs tested without authentication, they work
- [x] PAGE XML export of the transcribed inventories converted to JSON, in `data/transcriptions/`
- [x] Mapping from Transkribus titles to catalogue shelfmarks established, all matched, in `data/source_mapping.json`

The collection metadata `data/transkribus_collection.json` and `data/transkribus_status.json` are results of this exploration and are loaded by no page.

## 4. Account book 2, the working volume

| Field | Value |
|-------|-------|
| Holding | OÖKAM, Tyrolean State Archives |
| Transkribus doc ID | **12514730** |
| Extent | 123 openings (fol. 0v-1r to fol. 122v-123r) |
| File names | `OÖKAM Raitbuch 2, fol. {Xv-Yr}.jpg` |
| Digitized images | JPG via IIIF, loadable without authentication |
| Layout analysis | Yes (baselines, regions), no text |
| Transcription status in Transkribus | **Not transcribed** |
| Date | 1462–1463 (exact boundaries to be clarified) |
| IIIF example (fol. 0v-1r) | `https://files.transkribus.eu/iiif/2/ISMVDKARQUBRQTZVDEQSWVHR/full/max/0/default.jpg` |

### Structural elements checked against facsimiles

| Element | Description |
|---------|-------------|
| Rubricated headings | Personal names in a larger chancery hand |
| "Nota" | Opening formula of an entry |
| "Item" | Marker of an individual item |
| Column of figures | Monetary amounts at the right margin (fl., kr., lb.) |
| "daran sein Innemen" | Sub-heading (fol. 3r) |

### Confirmed persons

| Person | Folio | Certainty |
|--------|-------|-----------|
| Sigmund von Brandis | fol. 2r | Legible |
| Graf Heinrich von Lupfen | fol. 3r | Legible |
| [name] | fol. 2v | Uncertain |

### Machine transcription of the volume

Openings from account book 2 form the core of the versioned prompt benchmark under `evaluation/benchmark/`; the page set was chosen from a visual survey of all 123 openings so that each selected page represents a distinct phenomenon (rule structure, name rubrics, columns of figures, cancellation crosses, faded rubrics, blank and transitional pages). The pilot under `evaluation/pilot/` runs the same prompts over a stretch of consecutive openings from the start of the volume.

The models reliably recognise blank pages, the division of an opening into its two halves and the coarse entry structure. Personal names, dates and monetary amounts vary between repeated runs of the same prompt, and the amounts are precisely what account-book research depends on. All model output is therefore treated as an unrevised proposal. Edition use requires facsimile verification and an explicit editorial decision. The full argument and the current measurements are in `htr-evaluation.md` and in `data/benchmark/summary.json`.

### First category identified

**"prussian vnd Solde aussserhalb Lanndes"** (provision and pay outside the country): payments to personnel beyond Tyrol. A possible mention of a master of the kitchen in line 9, fol. 2r ("[?]kuncmeister", perhaps "kuechenmeister"). **Verification by the project lead is outstanding.**

### Linguistic challenges

- Kurrentschrift, not readable without transcription support
- Early New High German with regional variants
- Abbreviations: fl. (Gulden), kr. (Kreuzer), lb. (Pfund)
- Latin formulae inside otherwise German text

### Open questions about the source

- [ ] Which years exactly does account book 2 cover?
- [ ] Which further accounting categories does the volume contain?
- [ ] Is there an index or table of contents?
- [ ] How does account book 2 relate to the other 25 volumes?
- [x] Do partial transcriptions already exist? **No.** A layout analysis with baselines is present, but no text.
- [ ] Does the volume contain kitchen-related categories?
