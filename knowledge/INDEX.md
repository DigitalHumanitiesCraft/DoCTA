# DoCTA Knowledge — Map of Content

## Promptotyping Phase

**Aktuell: Phase 3→4 (Destillation abgeschlossen, Implementation bereit)**

| Phase | Status |
|-------|--------|
| 1. Preparation | ✓ Quelldokumente in `sources/` |
| 2. Exploration | ✓ SiCProD API, CSV, Transkribus Collection kartiert |
| 3. Destillation | ✓ 6 Knowledge-Dateien, alle Daten exportiert |
| 4. Implementation | Bereit — keine blockierenden Punkte |

## Dateien nach Zweck

| Datei | Zweck | Inhalt |
|-------|-------|--------|
| **DATA.md** | Datenquellen und -qualität | SiCProD API (Struktur, echte Beispiele, Lücken), CSV-Quellenübersicht (Qualitätsprobleme, Verfügbarkeitspyramide), Transkribus (Auth, Collection, IIIF, Pre-Fetch), Raitbuch 2 (Struktur, offene Fragen) |
| **REQUIREMENTS.md** | Ziele und Constraints | Barbaras Wünsche (Originalstimme), Gutachten 10 Kritikpunkte → Prototyp-Antworten, technische Constraints, Budget/Timeline, Erfolgskriterien, Prioritäten |
| **CONTEXT.md** | Domänenwissen und Methoden | SiCPAS-Datenmodell, Praxeologie/Verbklassen, BeNASch-Schema, Forschungsfragen, Fallstudien, Kooperationspartner, epistemische Asymmetrie, coOCR/HTR-Konzepte |
| **TECH.md** | Architektur und Implementierung | Libraries (Cytoscape.js, OpenSeadragon), Performance-Strategien, Projektstruktur, Design-System, Build-Time Scripts, coOCR/HTR als Referenz |
| **JOURNAL.md** | Entscheidungen und Erkenntnisse | Chronologische Entscheidungen mit Begründung, Explorationsergebnisse, Sackgassen, offene Fragen, Phasentracking |

## Leseordnung für LLM-Context

1. **INDEX.md** (dieses Dokument) — Orientierung
2. **REQUIREMENTS.md** — Was der Prototyp leisten muss
3. **DATA.md** — Welche Daten verfügbar sind und wo sie brechen
4. **CONTEXT.md** — Domänenwissen für korrekte Interpretation
5. **TECH.md** — Wie der Prototyp gebaut wird
6. **JOURNAL.md** — Entscheidungshistorie (optional, bei Bedarf)

## Quelldokumente (`sources/`)

Die Knowledge-Dateien destillieren diese Quelldokumente:

| Datei | Funktion | In Knowledge erfasst? |
|-------|----------|----------------------|
| `sources/strategische-planung.md` | Master-Planungsdokument (378 Zeilen) | Ja, verteilt über alle Dateien |
| `sources/requirements-barbara.md` | Barbaras Anforderungen (94 Zeilen) | Ja, in knowledge/REQUIREMENTS.md integriert |
| `sources/raitbuch-2-analyse.md` | Quellenanalyse (186 Zeilen) | Ja, in DATA.md |
| `sources/coocr-htr-epistemologie.md` | Epistemologie-Argumentation (133 Zeilen) | Ja, Kernkonzepte in CONTEXT.md |
| `sources/fwf-proposal-2025.md` | Abgelehnter FWF-Antrag (~900 Zeilen) | Teilweise — Bibliografie und WP-Details nicht erfasst |
| `sources/gutachten-denicolo.pdf` | Gutachten (26/40 Punkte) | Ja, in REQUIREMENTS.md |
| `sources/quellen-katalog.csv` | Quellenübersicht (316 Einträge) | Ja, Analyse in DATA.md |
| `sources/sicpas-modell.svg` | SiCPAS-Diagramm (742 KB SVG) | Textuell in CONTEXT.md |

## Exportierte Daten (`data/`)

| Datei | Inhalt |
|-------|--------|
| `data/transkribus_collection.json` | 115 Dokumente mit Metadaten |
| `data/transkribus_status.json` | Transkriptionsstatus aller 115 Dokumente |
| `data/raitbuch2_pages.json` | 123 Seiten mit IIIF-Keys |
| `data/source_mapping.json` | Mapping Transkribus-Titel → CSV-Signaturen (64/64) |
| `data/transcriptions/*.json` | 57 Inventar-Transkriptionen (8.979 Zeilen, 35.724 Wörter) |
