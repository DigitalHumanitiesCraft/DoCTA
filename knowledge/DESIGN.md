# DESIGN: Gestaltungs- und Interaktionsentscheidungen

Dieses Dokument hält fest, welche Gestaltungsoptionen erwogen und welche verworfen wurden, jeweils
mit Begründung. Nach dem Promptotyping-Prinzip ist die Entscheidungslogik das Reproduzierbare, nicht
der Code.

**Referenzimplementierung:** [coOCR/HTR](https://github.com/DigitalHumanitiesCraft/co-ocr-htr).
Die Ausgangsfrage lautete: welche Muster des Schwesterprojekts übernehmen wir, welche nicht?

---

## 1. Architektur: was bewusst NICHT übernommen wurde

| Muster in coOCR/HTR | Entscheidung | Begründung |
|---|---|---|
| 10 modulare CSS-Dateien | Nein, eine `styles.css` | Bei rund 350 Zeilen ist Modularisierung Aufwand ohne Ertrag |
| Zentrales State Management (`AppState extends EventTarget`) | Nein | Die Seiten sind unabhängig, es gibt keine seitenübergreifende Live-Interaktion |
| Service- und Component-Hierarchie | Nein, flach: `app.js`, `data-loader.js`, `utils.js` | Reicht für acht statische Seiten |
| PWA mit Service Worker | Nein | Ein Prototyp für Begutachtung braucht keinen Offline-Betrieb |

Diese vier Absagen sind der Grund, warum das Projekt ohne Build-Prozess auskommt. Wer eine davon
zurücknimmt, kippt die Konsequenz für alle anderen.

## 2. Architektur: was übernommen wurde

| Muster | Umgesetzt in | Anmerkung |
|---|---|---|
| Knowledge Vault als eigene Seite | `knowledge.html` | Sidebar plus Markdown-Rendering über marked.js, Hash-Routing |
| Kategorielle Konfidenz statt Prozentwerten | Pipeline-Demo, CSS-Tokens | Siehe Abschnitt 4 |
| CSS Custom Properties als Design Tokens | `css/styles.css` | Farben, Abstände, Typografie, Radien |
| IndexedDB-Caching | `js/data-loader.js` | Mit Timeout, `onblocked`-Behandlung und Fallback |
| Warme Archiv-Palette | `css/styles.css` | Hintergrund `#faf8f5` identisch zu coOCR/HTR, Akzent `#8b5e3c` statt Gold |

## 3. Netzwerk-Explorer

Die schwierigste Gestaltungsfrage des Projekts: 6.288 Personen und 42.893 Relationen sind in einem
Graphen nicht darstellbar.

| Option | Entscheidung | Begründung |
|---|---|---|
| Gesamtgraph rendern | Verworfen | Unlesbar und langsam, unabhängig von der Bibliothek |
| Top-200 nach Zentralität als Standard | Verworfen (war bis Februar in Betrieb) | Ein Hairball ohne Aussage. Wer ihn sieht, lernt nichts über den Hof |
| **Ego-Netzwerk als Standardansicht** | **Gewählt** | Beantwortet die Frage, die Nutzende tatsächlich stellen: mit wem stand diese Person in Beziehung |
| Gesamtansicht als umschaltbare Alternative | Gewählt, begrenzt | Zeigt die Struktur der bestvernetzten Entitäten, ohne den Hairball zum Einstieg zu machen |

Grenzwerte im Code: `EGO_MAX_NEIGHBORS = 50`, `FULL_MAX_NODES = 75`. Layout: `concentric` für die
Ego-Ansicht (die zentrale Person steht sichtbar im Mittelpunkt), `cose` für die Gesamtansicht.

Zwei Einschränkungen, die aus dieser Entscheidung folgen und benannt gehören: Die Gesamtansicht zeigt
weniger Knoten als die Obergrenze, weil Knoten ohne Index-Eintrag und ohne sichtbare Kante
herausfallen. Die Beschriftung nennt deshalb die tatsächliche Zahl. Und die Relationstypen `salary`
und `event` sind in dieser Darstellung prinzipiell nicht abbildbar.

## 4. Konfidenz: kategoriell statt numerisch

Extrahierte Entitäten und Relationen tragen `sicher`, `prüfenswert` oder `problematisch` statt
Prozentwerten.

Der Grund ist epistemologisch, nicht ästhetisch: Ein Sprachmodell, das seine eigene Ausgabe mit
"87 % Konfidenz" bewertet, erzeugt eine Scheingenauigkeit, die zu Automation Bias einlädt. Eine
dreistufige Skala macht sichtbar, dass es sich um eine Einschätzung handelt, die fachliche Prüfung
nicht ersetzt. Siehe CONTEXT.md zur epistemischen Asymmetrie.

Die Einschränkung bleibt bestehen und ist keine Gestaltungsfrage: auch die kategorielle Einstufung
stammt vom Modell selbst.

## 5. Verworfen und offen

| Idee | Stand | Grund |
|---|---|---|
| Kartenansicht der Orte | Verworfen für den Prototyp | Ein erheblicher Teil der 736 Orte hat keine Koordinaten. Eine Karte mit systematischen Lücken suggeriert Vollständigkeit, wo keine ist |
| Zeitraum-Filter als Slider | Nicht gebaut | Die Datierungen in SiCProD sind zu uneinheitlich für eine stufenlose Achse |
| Zweisprachigkeit Deutsch und Englisch | Offen | Begutachtung erfolgt oft auf Englisch. Aufwand mittel, bisher nicht priorisiert |
| Zeilen-Overlay im Viewer (Bild und Transkription verkoppelt) | Offen | Die Koordinaten liegen in `data/transcriptions/*.json` unter `regions[].lines[].coords` bereit |

## 6. Farbsystem

| Bedeutung | Wert |
|---|---|
| Person | `#1565c0` |
| Ort | `#2e7d32` |
| Funktion | `#6a1b9a` |
| Institution | `#e65100` |
| Objekt | `#e65100` |
| Konfidenz sicher | `#2d7d46` |
| Konfidenz prüfenswert | `#c68a00` |
| Konfidenz problematisch | `#c62828` |

Die Entitätsfarben müssen an drei Stellen übereinstimmen: den Badge-Klassen in `css/styles.css`, den
Cytoscape-Knotenfarben und der Legende in `network.html`. Objekt und Institution teilen sich derzeit
einen Wert; das fällt nicht auf, weil Objekte nur in der Pipeline-Demo und Institutionen nur in Suche
und Netzwerk vorkommen. Bei einer Zusammenführung der Ansichten müsste das aufgelöst werden.
