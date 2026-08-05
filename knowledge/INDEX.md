# DoCTA Knowledge: Map of Content

## Promptotyping Phase

**Aktuell: Phase 4 abgeschlossen. Der Prototyp ist seit 19.02.2026 vollständig implementiert und unter https://dhcraft.org/DoCTA/ öffentlich erreichbar.**

| Phase | Status |
|-------|--------|
| 1. Preparation | ✓ Quelldokumente in `sources/` (projektintern) |
| 2. Exploration | ✓ SiCProD API, CSV, Transkribus Collection kartiert |
| 3. Destillation | ✓ 7 Knowledge-Dateien, alle Daten exportiert |
| 4. Implementation | ✓ Acht Seiten gebaut, Daten eingebunden, deployed |

## Dateien nach Zweck

| Datei | Zweck | Inhalt |
|-------|-------|--------|
| **DATA.md** | Datenquellen und -qualität | SiCProD API (Struktur, echte Beispiele, Lücken), CSV-Quellenübersicht (Qualitätsprobleme, Verfügbarkeitspyramide), Transkribus (Auth, Collection, IIIF, Pre-Fetch), Raitbuch 2 (Struktur, offene Fragen) |
| **REQUIREMENTS.md** | Ziele und Constraints | Barbaras Wünsche (Originalstimme), Gutachten 10 Kritikpunkte → Prototyp-Antworten, technische Constraints, Budget/Timeline, Erfolgskriterien, Prioritäten |
| **CONTEXT.md** | Domänenwissen und Methoden | SiCPAS-Datenmodell, Praxeologie/Verbklassen, BeNASch-Schema, Forschungsfragen, Fallstudien, Kooperationspartner, epistemische Asymmetrie, coOCR/HTR-Konzepte |
| **TECH.md** | Architektur und Implementierung | Libraries (Cytoscape.js, OpenSeadragon), Performance-Strategien, Projektstruktur, Design-System, Build-Time Scripts, coOCR/HTR als Referenz |
| **DESIGN.md** | Gestaltung und Interaktion | Verworfene Architekturmuster mit Begründung, Netzwerk-Explorer (warum Ego-Netzwerk als Standard), kategorielle Konfidenz, verworfene Ansichten (Karte, Zeit-Slider), Farbsystem |
| **JOURNAL.md** | Entscheidungen und Erkenntnisse | Chronologische Entscheidungen mit Begründung, Explorationsergebnisse, Sackgassen, offene Fragen, Phasentracking |

## Leseordnung für LLM-Context

1. **INDEX.md** (dieses Dokument): Orientierung
2. **REQUIREMENTS.md**: Was der Prototyp leisten muss
3. **DATA.md**: Welche Daten verfügbar sind und wo sie brechen
4. **CONTEXT.md**: Domänenwissen für korrekte Interpretation
5. **TECH.md**: Wie der Prototyp gebaut wurde
6. **DESIGN.md**: Warum er so aussieht und sich so verhält, und was verworfen wurde
7. **JOURNAL.md**: Entscheidungshistorie (optional, bei Bedarf)

## Quelldokumente (`sources/`)

Die Knowledge-Dateien destillieren die folgenden Quelldokumente. **Diese Dateien sind projektintern und im öffentlichen Repository nicht enthalten**, weil sie unveröffentlichte Antragstexte und personenbezogene Korrespondenz enthalten. Die Tabelle steht hier, damit nachvollziehbar bleibt, woher der Inhalt der Knowledge-Dateien stammt; die Links führen ins Leere.

| Datei (projektintern) | Funktion | In Knowledge erfasst? |
|-------|----------|----------------------|
| `sources/strategische-planung.md` | Master-Planungsdokument (378 Zeilen) | Ja, verteilt über alle Dateien |
| `sources/requirements-barbara.md` | Barbaras Anforderungen (94 Zeilen) | Ja, in knowledge/REQUIREMENTS.md integriert |
| `sources/raitbuch-2-analyse.md` | Quellenanalyse (186 Zeilen) | Ja, in DATA.md |
| `sources/coocr-htr-epistemologie.md` | Epistemologie-Argumentation (133 Zeilen) | Ja, Kernkonzepte in CONTEXT.md |
| `sources/fwf-proposal-2025.md` | Abgelehnter ÖAW-Antrag APART-GSK (~900 Zeilen). Der Dateiname stammt aus einer früheren Ablage und ist irreführend. | Teilweise. Bibliografie und WP-Details sind nicht erfasst. |
| `sources/gutachten-denicolo.pdf` | ÖAW-Gutachten zur Ersteinreichung | Ja, in REQUIREMENTS.md |
| `sources/quellen-katalog.csv` | Quellenübersicht (312 Einträge) | Ja, Analyse in DATA.md |
| `sources/sicpas-modell.svg` | SiCPAS-Diagramm (742 KB SVG) | Textuell in CONTEXT.md |

## Exportierte Daten (`data/`)

Anders als `sources/` ist dieser Ordner vollständig im öffentlichen Repository enthalten.

### Vom Prototyp verwendet

| Datei | Inhalt |
|-------|--------|
| `data/persons.json` | 6.288 Personen (SiCProD) |
| `data/relations.json` | 42.893 Relationen |
| `data/places.json`, `data/institutions.json`, `data/functions.json` | 736 Orte, 215 Institutionen, 1.613 Funktionen |
| `data/sources.json` | 312 Quellen, aus der CSV bereinigt |
| `data/source_mapping.json` | Mapping Transkribus-Titel → CSV-Signaturen (64/64) |
| `data/transcriptions/*.json` | 57 Inventar-Transkriptionen (8.979 Zeilen, 35.724 Wörter) |
| `data/demo/*.json` | NER-Demo zum Inventar Thaur A 49.1 (Entitäten, Relationen, Netzwerk) |

### Explorationsartefakte, von keiner Seite geladen

Sie bleiben im Repo, weil sie belegen, wie die Datenlage ermittelt wurde.

| Datei | Inhalt |
|-------|--------|
| `data/transkribus_collection.json` | 115 Dokumente mit Metadaten |
| `data/transkribus_status.json` | Transkriptionsstatus aller 115 Dokumente |
| `data/raitbuch2_pages.json` | 123 Seiten mit IIIF-Keys |
| `data/network.json` | Vorberechnetes Layout, 200 Knoten mit x/y (siehe TECH.md) |
