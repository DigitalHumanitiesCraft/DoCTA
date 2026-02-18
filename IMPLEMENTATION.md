# DoCTA Prototyp — Implementierungsplan

## Ziel

Funktionaler Web-Prototyp auf GitHub Pages, der 8 von 10 Gutachten-Kritikpunkten durch laufenden Code beantwortet. Ein Gutachter öffnet die URL und versteht in 5 Minuten, was das Projekt methodisch leistet.

## Verfügbare Daten

| Quelle | Status | Umfang |
|--------|--------|--------|
| SiCProD API | Öffentlich, noch nicht gefetcht | 6.288 Personen, 42.893 Relationen, 736 Orte, 1.613 Funktionen |
| Transkribus Transkriptionen | **Fertig** in `data/transcriptions/` | 57 Inventare, 8.979 Zeilen, 35.724 Wörter |
| Transkribus Bilder | **Verifiziert**: IIIF ohne Auth | 12.236 Seiten, alle 123 RB2-Seiten mit Keys in `data/raitbuch2_pages.json` |
| CSV Quellenübersicht | Roh in `sources/quellen-katalog.csv` | 316 Einträge, noch nicht transformiert |
| Quellen-Mapping | **Fertig** in `data/source_mapping.json` | 64/64 Inventare gematcht |
| Collection-Metadaten | **Fertig** in `data/transkribus_collection.json` | 115 Dokumente |

## Constraints

- GitHub Pages (statisch, kein Backend)
- Vanilla JS/ES6 Module, kein Build-Prozess
- Vendored Dependencies in `/lib/`
- Konsistent mit coOCR/HTR (Farbschema, kategorielle Konfidenz)

## Prioritäten (mit Christopher abgestimmt)

1. **Pipeline-Demo** — Schrittweise an echtem Quellenbeispiel
2. **Facettierte Suche** — SiCProD-Daten explorierbar
3. **Quellenexploration** — Bild + Transkription + Entitäten

---

## Phase A: Daten-Pipeline (Python)

### A0. Repo-Setup

- `git init` im Projektverzeichnis
- `.gitignore`: `__pycache__/`, `*.pyc`, `.env` (falls Credentials ausgelagert)
- Remote: `DigitalHumanitiesCraft/docta-prototype`
- **Credentials nicht committen** — `scripts/` enthält Transkribus-Passwort. Entweder `.env`-Datei (gitignored) oder Credentials vor Commit entfernen.

### A1. SiCProD fetchen → statisches JSON

**Script:** `scripts/fetch_sicprod.py`

Paginiert alle Entitäten abrufen (`?format=json&limit=500&offset=0`):

| Endpunkt | Output | Felder |
|----------|--------|--------|
| `apis_ontology.person/` | `data/persons.json` | id, name, start_date, end_date, gender, alternative_label |
| `apis_ontology.place/` | `data/places.json` | id, label, lat, lng, type |
| `apis_ontology.institution/` | `data/institutions.json` | id, name, type |
| `apis_ontology.function/` | `data/functions.json` | id, name |
| `relations.relation/` | `data/relations.json` | subj_id, subj_type, obj_id, obj_type, relation_type |

**Relationstypen:** Zuerst alle distinkte Typen inventarisieren (aus den 42.893 Relationen), dann ein Mapping `camelCase → lesbar` erstellen. Nicht raten — aus den echten Daten ableiten.

### A2. Netzwerk-Layout vorberechnen

**Script:** `scripts/compute_layout.py`

- networkx Graph aus `relations.json`
- `spring_layout` (in networkx eingebaut, kein Extra-Paket)
- Zentralitätsmetriken: Degree, Betweenness für Top-200 Knoten
- Output: `data/network.json` — `{id, x, y, degree, betweenness}` pro Knoten

### A3. CSV transformieren

**Script:** `scripts/transform_sources.py`

- `sources/quellen-katalog.csv` → `data/sources.json`
- Geisterspalten entfernen (Spalte3–18)
- Datumsformate normalisieren (YYYY oder YYYY-YYYY)
- En-dash/Hyphen vereinheitlichen
- Transkribus-Link ergänzen (aus `data/source_mapping.json`)
- Verfügbarkeitstier berechnen (1–4)

### A4. Pipeline-Demo-Daten vorbereiten

**Quellenwahl:** Thaur A 49.1 (Doc-ID 11328300). Hat finale Transkription (DONE, 189 Zeilen, 753 Wörter), 4 Seiten, gut lesbares Inventar auf Frühneuhochdeutsch. Ideal für Demo.

**NER-Annotation erstellen** via LLM (Claude):
- Input: Transkriptionstext aus `data/transcriptions/11328300.json`
- Prompt: Extrahiere Entitäten (Person, Ort, Objekt, Zeit) und Relationen aus dem frühneuhochdeutschen Inventartext
- Output: `data/demo/thaur_entities.json` — Entitäten mit Offsets im Text
- Output: `data/demo/thaur_relations.json` — Subjekt→Relation→Objekt
- Output: `data/demo/thaur_network.json` — Mini-Graph für Schritt 5

**Wichtig:** Das ist ein vorberechnetes Demo-Beispiel, nicht ein live NER-System. Der Prototyp ZEIGT die Pipeline, er FÜHRT sie nicht aus. Das Ziel ist: der Gutachter sieht, was die Pipeline produzieren WIRD.

**Optional:** Zweites Beispiel mit RB2 fol. 1v-2r (Bild vorhanden, keine Transkription). Zeigt Schritt 1 (Quelle) und erklärt, dass HTR der nächste Projektschritt wäre. Demonstriert das Rohmaterial.

### A5. Vendored Libraries herunterladen

| Library | Version | Download |
|---------|---------|----------|
| Cytoscape.js | 3.30+ | `https://unpkg.com/cytoscape/dist/cytoscape.esm.min.js` → `lib/cytoscape.esm.min.js` |
| OpenSeadragon | 4.1+ | `https://github.com/openseadragon/openseadragon/releases` → `lib/openseadragon.min.js` + `lib/images/` |

### A6. Validierung

- Alle JSON-Dateien valide?
- `persons.json` enthält 6.288 Einträge?
- `relations.json` enthält 42.893 Einträge?
- `sources.json` enthält 316 Einträge?
- Demo-Entitäten plausibel? (Stichprobe: Personen im Inventar vs. SiCProD)
- Gesamtgröße `data/` < 10 MB?

---

## Phase B: Grundstruktur + Design

### B1. HTML-Gerüst

6 Seiten, gemeinsame Navigation:

| Seite | Zweck | Gutachten-Punkte |
|-------|-------|------------------|
| `index.html` | Landing, Dashboard, Pipeline-Übersicht | #8, #10 |
| `pipeline.html` | Pipeline-Demo Schritt für Schritt | #1, #3, #7, #8 |
| `search.html` | Facettierte Suche | #6 |
| `sources.html` | Quellenübersicht (316 Einträge) | #6 |
| `viewer.html` | Bild + Transkription + Entitäten | #4, #7, #9 |
| `network.html` | Netzwerk-Explorer | #10 |

### B2. CSS Design-System

`css/styles.css` — eine Datei, kein Framework:

- Warm, hell (konsistent mit coOCR/HTR)
- Konfidenz-Farben: `--conf-high: #2d7d46`, `--conf-medium: #c68a00`, `--conf-low: #c62828`
- Entitäts-Farben: `--ent-person: #1565c0`, `--ent-place: #2e7d32`, `--ent-object: #e65100`, `--ent-time: #6a1b9a`
- Semantisches HTML, ARIA-Labels
- Desktop-First, min-width 1024px
- Monospace für Quellentext, Sans-Serif für UI

### B3. Shared JS Module

- `js/app.js` — Navigation, globaler State
- `js/data-loader.js` — JSON laden, IndexedDB-Cache
- `js/utils.js` — Datumsformatierung, URL-Parameter

---

## Phase C: Features (nach Priorität)

### C1. Landing Page + Dashboard (`index.html`)

- Projekttitel, Kurzbeschreibung (2–3 Sätze)
- Visuelle Pipeline-Grafik: Quelle → HTR → Extraktion → Netzwerk (als statische SVG/HTML)
- Statistik-Kacheln: 6.288 Personen, 736 Orte, 42.893 Relationen, 316 Quellen, 57 Transkriptionen
- Navigation zu den 5 Bereichen
- Adressiert #8 (konkreter Plan), #10 (Kriterien)

### C2. Pipeline-Demo (`pipeline.html`)

**Höchste Priorität.** 5 Schritte am Inventar Thaur A 49.1 (Doc-ID 11328300, 4 Seiten, DONE):

| Schritt | Zeigt | Datenquelle |
|---------|-------|-------------|
| 1. Quelle | Originalbild via IIIF | IIIF-URL aus `data/transcriptions/11328300.json` |
| 2. HTR | Transkriptionstext zeilenweise | Text aus `data/transcriptions/11328300.json` |
| 3. NER | Entitäten farbcodiert im Text | `data/demo/thaur_entities.json` (LLM-vorberechnet) |
| 4. Relationen | Erkannte Beziehungen als Tabelle | `data/demo/thaur_relations.json` (LLM-vorberechnet) |
| 5. Netzwerk | Mini-Graph der extrahierten Entitäten | `data/demo/thaur_network.json` (aus Relationen abgeleitet) |

Jeder Schritt mit Erklärtext: was passiert hier, warum, welche Methode.
Vor/Zurück-Navigation zwischen Schritten.

**Kein Live-NER.** Die Demo zeigt vorberechnete Ergebnisse. Das ist transparent kommuniziert: "Diese Extraktion wurde mit Claude als LLM-Prototyping-Werkzeug erstellt und durch Fachwissenschaftlerin validiert."

**Optional (wenn Zeit):** Zweiter Tab "Raitbuch 2" zeigt RB2 fol. 1v-2r als Bild (Kurrentschrift) und erklärt: "Dieses Rohmaterial wird im Vollprojekt durch die Pipeline verarbeitet."

Adressiert #1, #3, #7, #8.

### C3. Quellenübersicht (`sources.html`)

- Tabelle: 316 Einträge aus `data/sources.json`
- Sortierbar: Kategorie, Signatur, Datierung, Seitenanzahl
- Filterbar: Kategorie-Dropdown, Verfügbarkeitstier, Projekt
- Verfügbarkeitstier visuell: Tier 1 (grün), 2 (gelb), 3 (orange), 4 (grau)
- Link zum Viewer für transkribierte Quellen (57 Inventare)

Adressiert #6.

### C4. Facettierte Suche (`search.html`)

- Freitext-Suche über alle SiCProD-Entitäten
- Facetten: Entitätstyp, Geschlecht, Funktion, Zeitraum (Slider), Ort
- Ergebnisliste mit Kurzinfo
- Click → Detail-Panel (Name, Daten, Relationen, Namensvarianten)
- URL-Parameter für teilbare Suchen

Adressiert #6.

### C5. Quellen-Explorer (`viewer.html`)

- Zwei-Panel: OpenSeadragon (Bild) links, Transkription rechts
- Transkription aus `data/transcriptions/{id}.json` (Rohtext, zeilenweise)
- Dropdown: Dokument wählen (57 verfügbare Inventare)
- Seiten-Navigation innerhalb eines Dokuments

**Entitäten-Highlighting:** Nur für das Demo-Dokument (Thaur A 49.1), wo NER-Annotationen existieren. Für die übrigen 56 Inventare: reiner Transkriptionstext ohne Highlighting. Das ist ehrlich — NER für alle Quellen ist Vollprojekt-Arbeit.

**Konfidenz:** Die Transkribus-Exporte enthalten keine wortweisen Konfidenzwerte. Stattdessen: Transkriptions-Metadaten anzeigen (Status, Zeilen, Wörter pro Seite). Das coOCR/HTR-Konfidenzkonzept (sicher/prüfenswert/problematisch) wird in der Pipeline-Demo erklärt, nicht auf alle Viewer-Dokumente angewendet.

Adressiert #4, #7.

### C6. Netzwerk-Explorer (`network.html`)

- Cytoscape.js mit vorberechnetem Layout
- Start: Top-200 Knoten nach Zentralität
- Knoten-Farben: Person (blau), Ort (grün), Institution (orange)
- Knoten-Größe: proportional zu Degree
- Click → Detail-Panel
- Filter: Zeitraum, Geschlecht, Funktion
- "Nachbarschaft erweitern" bei Click

Adressiert #10.

---

## Phase D: Polish + Deploy

### D1. Cross-Linking

- Suche → Netzwerk: "Im Netzwerk zeigen"
- Quellen → Viewer: "Transkription öffnen"
- Pipeline → Viewer: "Vollständige Quelle anzeigen"
- Dashboard → alle Bereiche

### D2. Performance

- JSON-Dateien mit IndexedDB cachen
- Lazy Loading für Netzwerk (Progressive Disclosure)
- Bilder via IIIF nur bei Bedarf laden

### D3. GitHub Pages Deployment

- Repository: `DigitalHumanitiesCraft/docta-prototype`
- Alle `data/*.json` git-tracked (Transkribus-Exporte sind statisch)
- `lib/` mit vendored Cytoscape.js + OpenSeadragon
- `scripts/` committen OHNE Credentials (`.env` für Passwörter)
- Testen: `python -m http.server` lokal

---

## Dateistruktur (Ziel)

```
DoCTA/
├── index.html
├── pipeline.html
├── search.html
├── sources.html
├── viewer.html
├── network.html
├── css/
│   └── styles.css
├── js/
│   ├── app.js
│   ├── data-loader.js
│   ├── network-view.js
│   ├── search-engine.js
│   ├── source-table.js
│   ├── document-viewer.js
│   ├── pipeline-demo.js
│   └── utils.js
├── lib/
│   ├── cytoscape.esm.min.js
│   ├── openseadragon.min.js
│   └── images/             ← OpenSeadragon UI-Icons
├── data/                    ← bereits vorhanden + neu generiert
│   ├── persons.json         ← A1 (neu)
│   ├── places.json          ← A1 (neu)
│   ├── institutions.json    ← A1 (neu)
│   ├── functions.json       ← A1 (neu)
│   ├── relations.json       ← A1 (neu)
│   ├── network.json         ← A2 (neu)
│   ├── sources.json         ← A3 (neu)
│   ├── demo/                ← A4 (neu)
│   │   ├── thaur_entities.json
│   │   ├── thaur_relations.json
│   │   └── thaur_network.json
│   ├── source_mapping.json      ← existiert
│   ├── raitbuch2_pages.json     ← existiert
│   ├── transkribus_collection.json ← existiert
│   ├── transkribus_status.json    ← existiert
│   └── transcriptions/           ← existiert (57 JSON)
├── sources/                 ← Quelldokumente (8 Dateien)
├── knowledge/               ← Promptotyping-Dokumentation (6 Dateien)
├── scripts/                 ← Build-Time Scripts
└── .gitignore
```

---

## Reihenfolge

| Schritt | Was | Abhängigkeit | Status |
|---------|-----|-------------|--------|
| A0 | Repo-Setup, .gitignore | — | Offen |
| A1 | `fetch_sicprod.py` | — | Offen |
| A2 | `compute_layout.py` | A1 | Offen |
| A3 | `transform_sources.py` | — | Offen |
| A4 | Pipeline-Demo-Daten (LLM-Annotation) | Transkription existiert | Offen |
| A5 | Vendored Libraries herunterladen | — | Offen |
| A6 | Validierung | A1–A5 | Offen |
| B1 | HTML-Gerüst (6 Seiten) | — | Offen |
| B2 | `css/styles.css` | — | Offen |
| B3 | Shared JS Module | — | Offen |
| C1 | Landing Page | A1, B1–B3 | Offen |
| C2 | Pipeline-Demo | A4, A5, B1–B2 | Offen |
| C3 | Quellenübersicht | A3, B1–B3 | Offen |
| C4 | Facettierte Suche | A1, B1–B3 | Offen |
| C5 | Quellen-Explorer | A5, B1–B2 | Offen |
| C6 | Netzwerk-Explorer | A1, A2, A5, B1–B3 | Offen |
| D1 | Cross-Linking | C1–C6 | Offen |
| D2 | Performance | C1–C6 | Offen |
| D3 | Deploy | D1, D2 | Offen |

Parallelisierbar: A0+A1+A3+A4+A5+B1+B2 gleichzeitig. C2 kann direkt nach A4+A5+B1+B2 starten.
