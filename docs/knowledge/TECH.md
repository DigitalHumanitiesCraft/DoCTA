# TECH: Architektur, Libraries, Projektstruktur

## Constraint

GitHub Pages (statisch), Vanilla JS/ES6 Module, kein Build-Prozess, kein npm zur Laufzeit. Externe Dependencies vendored in `/lib/`.

### Gevendorte Versionen (aus den Dateiköpfen in `lib/`)

| Library | Gevendort | Aktuell | Datei |
|---------|-----------|---------|-------|
| Bootstrap | 5.3.3 | 5.3.8 | `lib/bootstrap.min.css`, `lib/bootstrap.bundle.min.js` |
| Cytoscape.js | 3.30.4 | 3.34.0 | `lib/cytoscape.esm.min.mjs` |
| OpenSeadragon | 4.1.1 | 6.0.2 | `lib/openseadragon.min.js` |
| marked | 15.0.12 | 18.0.9 | `lib/marked.min.js` |

Der Rückstand ist bekannt und für einen Prototyp unkritisch: die Versionen sind eingefroren, seit sie funktionieren, und ohne Paketmanager ist ein Update Handarbeit samt erneutem Durchtesten aller Seiten.

## Netzwerk-Visualisierung: Cytoscape.js

### Warum Cytoscape.js

| Bibliothek | Renderer | Max Knoten | ESM-Support | Graph-Algorithmen |
|-----------|----------|-----------|-------------|-------------------|
| **Cytoscape.js** | Canvas + WebGL (v3.31+) | ~10.000+ (WebGL) | Ja, ESM-Build | Ja (BFS, PageRank, Betweenness, Communities) |
| Sigma.js v3 | WebGL nativ | ~15.000+ | Problematisch ohne npm | Via graphology |
| vis.js | Canvas | ~3.000 | UMD Build | Nein |
| D3.js | SVG/Canvas | ~2.000 (SVG) | Ja | Nein |

### Einbindung

```html
<script type="module">
  import cytoscape from './lib/cytoscape.esm.min.mjs';
</script>
```

### Performance-Strategie (6.288 Personen + 42.893 Relationen)

Umgesetzt in `network.html`:

1. Progressive Disclosure: Start als Ego-Netzwerk um Sigmund, `EGO_MAX_NEIGHBORS = 50` Nachbarn, Concentric-Layout mit Sigmund im Zentrum
2. Klick auf einen Knoten zeigt dessen Ego-Netzwerk, Toggle schaltet auf das Gesamtnetzwerk (`FULL_MAX_NODES = 75`, nach Grad gefiltert, COSE-Layout)
3. Knotensuche und Filter nach Relationstyp, statt alles gleichzeitig zu zeigen

Geplant, aber nicht umgesetzt:

4. **Labels nur bei Hover und ab einer Zoomstufe.** Alle Knoten tragen dauerhaft ihr Label. Bei 50 bis 75 Knoten ist das lesbar; ein Zoom-abhängiges Einblenden wäre erst bei deutlich größeren Graphen nötig.
5. **Layout-Vorberechnung (Python/networkx).** `scripts/compute_layout.py` existiert und schreibt `data/network.json` (200 Knoten mit x/y). Die Datei wird von keiner Seite geladen: bei 50 bis 75 sichtbaren Knoten rechnet Cytoscape das Layout schnell genug im Browser, und ein Live-Layout erlaubt den Wechsel zwischen Concentric und COSE. `data/network.json` bleibt als Explorationsartefakt im Repo.
6. **WebGL-Renderer** (`{ renderer: { name: 'webgl' } }`). Nicht aktiviert: WebGL gibt es in Cytoscape erst ab 3.31, gevendort ist 3.30.4. Bei der aktuellen Knotenzahl reicht Canvas ohnehin.

## Dokumentenviewer: OpenSeadragon

Zero Dependencies, IIIF-Support, Deep Zoom.

```html
<script src="lib/openseadragon.min.js"></script>
```

Bild-Quellen: Transkribus-IIIF-URLs, geladen als einfache Bildquelle (`viewer.open({ type: 'image', url })`), nicht als gekachelter IIIF-Service. Das reicht für einzelne Inventarseiten und spart einen Request-Roundtrip pro Kachel.

Das Transkriptionspanel ist eigenes HTML neben dem Viewer. Eine Synchronisation über Viewport-Events (Zeile im Text ↔ Zeilenbox im Bild) war geplant und ist nicht umgesetzt: Bild und Text stehen nebeneinander, ohne aufeinander zu zeigen. Die Zeilenkoordinaten aus dem PAGE-XML liegen in `data/transcriptions/` bereit, das Overlay fehlt.

## Facettierte Suche: Custom Vanilla JS

Keine Bibliothek nötig. Für 6.288 Personen + 736 Orte reicht `Array.filter()` + `Map` + `Set`. Statt einer eigenen Klasse steht die Logik als Funktionen (`getFiltered`, `renderFacets`, `renderResults`) inline in `search.html`, gegen ein `activeFilters`-Objekt aus vier `Set`s.

Umgesetzte Facetten: **Entitätstyp, Geschlecht, Funktion (Top 15), Ortstyp.**

Geplant, nicht umgesetzt: Institution, Zeitraum als Slider, Ort. Institutionen sind als Ergebnistyp durchsuchbar, taugen aber als Facette nicht, weil 207 von 215 keinen Typ haben (siehe DATA.md). Ein Zeitraum-Slider scheitert an den uneinheitlichen und oft fehlenden Datumsangaben.

## Daten-Loading

Jede Seite lädt nur die JSON-Dateien, die sie braucht. `js/data-loader.js` exportiert `loadJSON(path)` und `loadAll(pathMap)`; gecacht wird pro Datei in IndexedDB, versioniert über die Konstante `DATA_VERSION`.

```javascript
export async function loadJSON(path) {
  const cached = await getFromCache(path);
  if (cached) return cached;
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`Failed to load ${path}: ${resp.status}`);
  const data = await resp.json();
  putToCache(path, data);
  return data;
}
```

IndexedDB ist optional: Öffnet die Datenbank nicht innerhalb von 1,5 Sekunden oder schlägt sie fehl, fällt das Modul stillschweigend auf reines `fetch()` zurück.

Erwartete Ladezeit: ~1–3 Sekunden (1–1.5 MB gzipped über GitHub Pages CDN).

## Projektstruktur

```
DoCTA/docs/             # Published site (GitHub Pages serves docs/ on main)
├── index.html          # Start: Dashboard + Quellenübersicht mit Suche und Filtern
├── viewer.html         # Quellen-Explorer (OpenSeadragon + Transkription), Ort der Kuration
├── benchmark.html      # HTR-Benchmark: Ergebnisse der Prompt-Iterationen
├── knowledge.html      # Knowledge Vault (Promptotyping-Wissensbasis)
├── about.html          # About, Bedienung, Datenquellen, Impressum
├── css/styles.css      # Einheitliches Design
├── js/                 # ES6 Module, nur was mehrere Seiten teilen
│   ├── app.js          # Navigation, Beta-Banner, Footer
│   ├── benchmark.js    # Benchmark-Tabellen aus data/benchmark/summary.json
│   ├── data-loader.js  # Fetch JSON, IndexedDB-Cache
│   └── utils.js        # Formatierung, Sortierung, Escaping
├── data/               # Pre-processed JSON (git-tracked)
│   ├── benchmark/      # Export des HTR-Benchmarks (summary + runs)
│   └── demo/           # NER-Demo-Daten
├── lib/                # Vendored: bootstrap, cytoscape.esm.min.mjs,
│                       #   openseadragon.min.js, marked.min.js
DoCTA/
├── experiments/        # VLM-Transkriptionstest und Prompt-Benchmark (Labor)
├── scripts/            # Python Build-Time Scripts
└── knowledge/          # Promptotyping-Dokumentation
```

**Abweichung von der ursprünglichen Planung.** Geplant war ein Modul pro Seite (`network-view.js`, `search-engine.js`, `source-table.js`, `document-viewer.js`, `pipeline-demo.js`). Gebaut wurde anders: der seitenspezifische JavaScript-Code steht als `<script type="module">` direkt in der jeweiligen HTML-Datei, unter `js/` liegt nur, was mehrere Seiten gemeinsam nutzen. Grund: ohne Build-Prozess kostet jedes Modul einen zusätzlichen HTTP-Request, und der Code einer Seite wird von keiner anderen verwendet. Wer eine Seite verstehen will, liest eine Datei.

Auch der geplante Ordner `images/` (Beispiel-Digitalisate) existiert nicht. Die Digitalisate kommen zur Laufzeit über die Transkribus-IIIF-URLs, es liegt kein Bildmaterial im Repo.

## Design-System

Konsistent mit coOCR/HTR (externes Referenzprojekt, entwickelt von DHCraft):

| Aspekt | Umsetzung |
|--------|-----------|
| Farbschema | Warm, hell |
| Prüfstatus | Grün (sicher), Gelb (prüfenswert), Rot (problematisch), an Regeln oder fachliche Entscheidung gebunden |
| HTML | Semantisch, ARIA-Labels |
| Layout | Desktop-First, responsiv (kein Mobile-Fokus) |
| Typografie | Monospace für Quellentext, Sans-Serif für UI |

## Build-Time Scripts (Python)

| Script | Input | Output |
|--------|-------|--------|
| `fetch_sicprod.py` | SiCProD API | `data/persons.json`, `data/places.json`, `data/institutions.json`, `data/functions.json`, `data/relations.json` |
| `transform_sources.py` | CSV + `data/source_mapping.json` | `data/sources.json` |
| `fetch_transcriptions.py` | Transkribus API (OAuth2) | `data/transcriptions/{id}.json` |
| `map_sources.py` | Transkribus-Titel + CSV-Signaturen | `data/source_mapping.json` |

Explorations- und Hilfsskripte, deren Output der Prototyp nicht lädt: `compute_layout.py` (→ `data/network.json`), `explore_transkribus.py`, `explore_transkribus_deep.py`, `transkribus_status.py` (→ `data/transkribus_collection.json`, `data/transkribus_status.json`), `fetch_remaining.py`. Sie dokumentieren, wie die Datenlage ermittelt wurde, und bleiben deshalb im Repo.

## coOCR/HTR als Referenz

Browserbasierte VLM-Transkriptionsworkbench. **Externes Projekt**, nicht Teil des Prototyps.

| | |
|---|---|
| Demo | http://dhcraft.org/co-ocr-htr |
| Repo | https://github.com/DigitalHumanitiesCraft/co-ocr-htr |
| Stack | Vanilla JS/ES6, OpenSeadragon, kein Build-Prozess |

DoCTA übernimmt die visuelle Design-Sprache von coOCR/HTR. Die frühere kategorielle Konfidenz wird als regelgebundener Prüfstatus weitergeführt. Der Code wird nicht übernommen.
