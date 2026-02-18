# Promptotyping Frontend — Best Practices Matrix

**Referenzimplementierung:** [co-ocr-htr](https://github.com/DigitalHumanitiesCraft/co-ocr-htr) (dhcraft.org/co-ocr-htr)
**Ziel:** DoCTA-Prototyp für FWF-Wiedereinreichung
**Datum:** 2026-02-18

---

## Vollständige Matrix

### A. Knowledge & Dokumentation

| # | Pattern / Feature | co-ocr-htr | DoCTA aktuell | Relevanz | Aufwand | Empfehlung |
|---|---|---|---|---|---|---|
| A1 | **Knowledge Vault Page** | Eigene `knowledge.html` mit Sidebar + Markdown-Rendering (marked.js), 9 Dokumente, Hash-Routing | Fehlt komplett — `knowledge/` existiert als Ordner, aber kein Frontend | **Hoch** — Gutachter brauchen Methodik-Zugang | Klein | **JA** |
| A2 | **Design Principles Display** | 5 Prinzipien-Cards als Welcome-State im Knowledge Vault | Fehlt | **Hoch** — zeigt methodisches Bewusstsein | Klein | **JA** |
| A3 | **JOURNAL.md Integration** | Letztes Dokument im Vault, zeigt Entwicklungsprozess | JOURNAL.md existiert, nur nicht im Frontend | **Mittel** — Transparenz für Gutachter | Klein | **JA** |
| A4 | **Dokument-Matrix** (INDEX.md) | Zeigt Abhängigkeiten zwischen Dokumenten, Lesereihenfolge "Why→How→What→Reference" | INDEX.md existiert | **Mittel** | Klein | **JA** |

### B. CSS-Architektur

| # | Pattern / Feature | co-ocr-htr | DoCTA aktuell | Relevanz | Aufwand | Empfehlung |
|---|---|---|---|---|---|---|
| B1 | **Modulare CSS-Dateien** (10 Stück) | `variables.css`, `base.css`, `layout.css`, `components.css`, etc. | 1 Datei `styles.css` (350 Zeilen) | **Niedrig** — DoCTA ist kleiner, 1 File reicht | – | **NEIN** |
| B2 | **CSS Custom Properties** als Design Tokens | Vollständig: Farben, Spacing, Typo, Schatten, Radii | Vorhanden, gut umgesetzt | – | – | Bereits OK |
| B3 | **Warme Archiv-Palette** | `#faf8f5`, `#b89850`, `#4a7c9b` | `#faf8f5`, `#8b5e3c` — gleiche Familie | – | – | Bereits OK |

### C. JS-Architektur

| # | Pattern / Feature | co-ocr-htr | DoCTA aktuell | Relevanz | Aufwand | Empfehlung |
|---|---|---|---|---|---|---|
| C1 | **State Management** (EventTarget pub/sub) | Zentraler `AppState extends EventTarget`, Events für alles | Kein zentraler State, jede Seite eigenständig | **Niedrig** — DoCTA hat keine Live-Interaktion | – | **NEIN** |
| C2 | **Service/Component Pattern** | `services/`, `components/`, `utils/`, `config/` | Flach: `app.js`, `data-loader.js`, `utils.js` | **Niedrig** — reicht für 6 statische Seiten | – | **NEIN** |
| C3 | **IndexedDB Caching** | Vollständig mit Projektmanagement | Vorhanden in `data-loader.js` | – | – | Bereits OK |

### D. Inhalt & UX

| # | Pattern / Feature | co-ocr-htr | DoCTA aktuell | Relevanz | Aufwand | Empfehlung |
|---|---|---|---|---|---|---|
| D1 | **Kategoriale Konfidenz** (nicht Prozente) | `confident/uncertain/problematic` mit Farben + Badges | Konzeptionell vorhanden (Pipeline-Demo NER), aber nicht durchgängig | **Mittel** — stärkt methodisches Argument | Klein | **Ja, ausbauen** |
| D2 | **Cross-Referencing** zwischen Views | Triple-Sync: Viewer↔Editor↔Validation | Links zwischen Seiten (search→network, sources→viewer) | **Mittel** — ausbaubar | Mittel | **Optional** |
| D3 | **i18n** (EN/DE) | ~800 Keys, runtime switching, JSON dictionaries | Nur DE | **Hoch** — FWF-Gutachter sind international! | Mittel | **JA** (zumindest EN für Gutachter-Kontext) |
| D4 | **Loading States** | 4 States: welcome/loading/error/content | Einfacher Spinner vorhanden | **Niedrig** | – | Bereits OK |
| D5 | **Help/About Pages** | Eigene `help.html` + `about.html` | Fehlt — "Für Gutachter"-Section auf Dashboard | **Mittel** | Klein | **Optional** |

### E. Deployment & Infrastruktur

| # | Pattern / Feature | co-ocr-htr | DoCTA aktuell | Relevanz | Aufwand | Empfehlung |
|---|---|---|---|---|---|---|
| E1 | **PWA / Service Worker** | Ja, offline-fähig | Nein | **Niedrig** — Prototyp braucht kein Offline | – | **NEIN** |
| E2 | **GitHub Pages** | `docs/` Ordner als Deploy-Root | Noch nicht konfiguriert | **Hoch** — muss vor Einreichung passieren | Klein | **JA** |
| E3 | **CLAUDE.md** | Vorhanden, definiert AI-Kontext | Fehlt (wir nutzen MEMORY.md + IMPLEMENTATION.md) | **Niedrig** — internes Tool | – | **Optional** |

### F. Vendored Dependencies

| # | Pattern / Feature | co-ocr-htr | DoCTA aktuell | Relevanz | Aufwand | Empfehlung |
|---|---|---|---|---|---|---|
| F1 | **Marked.js** (Markdown-Rendering) | CDN-geladen für Knowledge Vault | Fehlt — wird für Knowledge Vault gebraucht | **Hoch** (wenn A1=JA) | Klein | **JA** |
| F2 | **Bootstrap** | Nicht verwendet (custom CSS) | Gerade integriert (v5.3.3) | – | – | Bereits OK |

---

## Entscheidung: Was einbauen?

### Must-have

| # | Was | Warum |
|---|---|---|
| A1 | Knowledge Vault Page | Gutachter-Zugang zu Methodik, zeigt Promptotyping-Prozess |
| A2 | Design Principles (Welcome State) | Methodisches Bewusstsein demonstrieren |
| A3 | JOURNAL.md im Vault | Entwicklungstransparenz |
| A4 | Dokument-Navigation (Sidebar) | Strukturierter Zugang zum Knowledge-Ordner |
| F1 | marked.js vendoren | Technische Voraussetzung für A1 |

### Should-have

| # | Was | Warum |
|---|---|---|
| D1 | Kategoriale Konfidenz durchgängig | Stärkt methodisches Argument gegen "automation bias" |
| D3 | Englische Gutachter-Texte | FWF-Reviews sind oft auf Englisch |

### Nice-to-have

| # | Was | Warum |
|---|---|---|
| D5 | About-Page | Projektkontext, Team, Förderung |
| E2 | GitHub Pages Deploy | Muss sowieso passieren |

### Explizit NEIN

| # | Was | Warum nicht |
|---|---|---|
| B1 | 10 modulare CSS-Files | Overkill für 350 Zeilen |
| C1 | EventTarget State Management | Keine Live-Interaktion, Seiten sind unabhängig |
| C2 | Service/Component-Hierarchie | 3 JS-Dateien reichen für statische Seiten |
| E1 | PWA/Service Worker | Prototyp, nicht Produktionsapp |

---

## co-ocr-htr Architektur-Notizen (Referenz)

### Knowledge Vault Implementierung (knowledge.html)

- **Layout:** CSS Grid mit Sidebar (320px) + Content-Area
- **Sidebar:** 9 Dokument-Links mit SVG-Icons und Beschreibungen
- **Content:** 4 States — welcome (Übersicht), loading (Spinner), error, content (gerendertes Markdown)
- **Markdown:** `marked.js` (CDN) konvertiert `.md` → HTML
- **Routing:** Hash-basiert (`#VISION`, `#METHODOLOGY`, etc.) mit `history.replaceState`
- **Frontmatter:** YAML wird vor dem Rendern gestrippt: `markdown.replace(/^---[\s\S]*?---\n*/m, '')`
- **Welcome State:** 5 Design-Prinzipien-Cards (3+2 Grid), Methodologie-Abschnitt, klickbarer Dokumentindex

### Farb-Palette (Vergleich)

| Token | co-ocr-htr | DoCTA |
|---|---|---|
| Background | `#faf8f5` | `#faf8f5` (identisch) |
| Brand/Accent | `#b89850` (Gold) | `#8b5e3c` (Braun) |
| Accent Secondary | `#4a7c9b` (Stahlblau) | – |
| Text Primary | `#3d3229` | `#2c2416` |
| Confident | `#5a8a5a` (Waldgrün) | `#2d7d46` |
| Uncertain | `#c4973a` (Bernstein) | `#c68a00` |
| Problematic | `#b85c4a` (Terrakotta) | `#c62828` |
