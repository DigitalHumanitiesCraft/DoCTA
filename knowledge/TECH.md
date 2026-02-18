# TECH -- Architektur, Libraries, Projektstruktur

## Constraint

GitHub Pages (statisch), Vanilla JS/ES6 Module, kein Build-Prozess, kein npm zur Laufzeit. Externe Dependencies vendored in `/lib/`.

## Netzwerk-Visualisierung: Cytoscape.js

### Warum Cytoscape.js

| Bibliothek | Renderer | Max Knoten | ESM-Support | Graph-Algorithmen |
|-----------|----------|-----------|-------------|-------------------|
| **Cytoscape.js** | Canvas + WebGL (v3.31+) | ~10.000+ (WebGL) | Ja, `.esm.min.js` | Ja (BFS, PageRank, Betweenness, Communities) |
| Sigma.js v3 | WebGL nativ | ~15.000+ | Problematisch ohne npm | Via graphology |
| vis.js | Canvas | ~3.000 | UMD Build | Nein |
| D3.js | SVG/Canvas | ~2.000 (SVG) | Ja | Nein |

### Einbindung

```html
<script type="module">
  import cytoscape from './lib/cytoscape.esm.min.js';
</script>
```

### Performance-Strategie (6.288 Personen + 42.893 Relationen)

1. Layout vorberechnen (Python/networkx) → x/y-Koordinaten in JSON
2. Progressive Disclosure: Start mit Top-200 nach Zentralität
3. "Nachbarschaft erweitern" bei Knoten-Click
4. WebGL-Renderer: `{ renderer: { name: 'webgl' } }`
5. Labels nur bei Hover/Zoom

## Dokumentenviewer: OpenSeadragon

Zero Dependencies, IIIF-Support, Deep Zoom.

```html
<script src="lib/openseadragon.min.js"></script>
```

Bild-Quellen: Transkribus IIIF-URLs als Legacy Tile Source. Transkriptions-Panel: eigenes HTML neben OpenSeadragon, synchronisiert via Viewport-Events.

## Facettierte Suche: Custom Vanilla JS

Keine Bibliothek nötig. Für 6.288 Personen + 736 Orte reicht `Array.filter()` + `Map` + `Set`.

```javascript
class FacetedSearch {
  constructor(data, facetConfig) { … }
  search(query, activeFilters) {
    return this.data
      .filter(item => this.matchesQuery(item, query))
      .filter(item => this.matchesFacets(item, activeFilters));
  }
  getFacetCounts(results, facetKey) { … }
}
```

Facetten: Entitätstyp, Geschlecht, Funktion/Rolle, Institution, Zeitraum (Slider), Ort.

## Daten-Loading

Alle JSON-Dateien beim Seitenstart laden, in IndexedDB cachen.

```javascript
async function loadData() {
  const cached = await idb.get('sicprod-data');
  if (cached && cached.version === DATA_VERSION) return cached;
  const [persons, relations, places] = await Promise.all([
    fetch('data/persons.json').then(r => r.json()),
    fetch('data/relations.json').then(r => r.json()),
    fetch('data/places.json').then(r => r.json())
  ]);
  const data = { persons, relations, places, version: DATA_VERSION };
  await idb.put('sicprod-data', data);
  return data;
}
```

Erwartete Ladezeit: ~1–3 Sekunden (1–1.5 MB gzipped über GitHub Pages CDN).

## Projektstruktur

```
DoCTA/
├── index.html          # Landing + Navigation + Dashboard
├── network.html        # Netzwerk-Explorer (Cytoscape.js)
├── search.html         # Facettierte Suche
├── sources.html        # Quellenübersicht (316 Einträge)
├── viewer.html         # Quellen-Explorer (OpenSeadragon + Transkription)
├── pipeline.html       # Pipeline-Demo (Schritt-für-Schritt)
├── css/styles.css      # Einheitliches Design
├── js/                 # ES6 Module
│   ├── app.js          # Shared: Navigation, State
│   ├── data-loader.js  # Fetch JSON, IndexedDB-Cache
│   ├── network-view.js # Cytoscape.js Netzwerk
│   ├── search-engine.js# Facettierte Suche
│   ├── source-table.js # Quellenübersicht
│   ├── document-viewer.js # OpenSeadragon + Transkription
│   ├── pipeline-demo.js   # Pipeline-Visualisierung
│   └── utils.js        # Shared Utilities
├── data/               # Pre-processed JSON (git-tracked)
├── images/             # Beispiel-Digitalisate
├── lib/                # Vendored: cytoscape.esm.min.js, openseadragon.min.js
├── scripts/            # Python Build-Time Scripts
└── knowledge/          # Promptotyping-Dokumentation
```

## Design-System

Konsistent mit coOCR/HTR (externes Referenzprojekt, entwickelt von DHCraft):

| Aspekt | Umsetzung |
|--------|-----------|
| Farbschema | Warm, hell |
| Konfidenz | Grün (sicher), Gelb (prüfenswert), Rot (problematisch) -- kategorisch, nicht numerisch |
| HTML | Semantisch, ARIA-Labels |
| Layout | Desktop-First, responsiv (kein Mobile-Fokus) |
| Typografie | Monospace für Quellentext, Sans-Serif für UI |

## Build-Time Scripts (Python)

| Script | Input | Output |
|--------|-------|--------|
| `fetch_sicprod.py` | SiCProD API | `data/persons.json`, `data/places.json`, `data/relations.json`, `data/network.json` |
| `transform_sources.py` | CSV | `data/sources.json` |
| `fetch_transkribus.py` | Transkribus API (OAuth2) | `data/transcriptions/{id}.json` |

## coOCR/HTR als Referenz

Browserbasierte VLM-Transkriptionsworkbench. **Externes Projekt**, nicht Teil des Prototyps.

| | |
|---|---|
| Demo | http://dhcraft.org/co-ocr-htr |
| Repo | https://github.com/DigitalHumanitiesCraft/co-ocr-htr |
| Stack | Vanilla JS/ES6, OpenSeadragon, kein Build-Prozess |

DoCTA übernimmt von coOCR/HTR: Farbschema, kategorielle Konfidenz, Design-Sprache. Nicht den Code.
