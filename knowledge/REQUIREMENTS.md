# REQUIREMENTS — Ziele, Constraints, Erfolgskriterien

## Projektrahmen

| | |
|---|---|
| Projekt | DoCTA (Doing Court in the Tyrolean Alps) |
| Projektleitung | Dr. Barbara Denicolò, Universität Salzburg |
| DH-Komponente | Digital Humanities Craft OG (Christopher Pollin, Christian Steiner) |
| Budget DH | 100 Arbeitsstunden / 15.000 € brutto |
| Phasen | 1: Promptotyping (30h) → 2: Workflow (30h) → 3: Web-App (30h) → 4: Training (10h) |
| Phase-1-Sequenzierung | 8h Datenmodell → 12h LLM-Extraktion → 6h Validierungs-Wireframe → 4h Puffer |
| Deadline | ÖAW-Antrag März 2026, FWF-Wiedereinreichung ASAP |

## Barbaras Anforderungen (Originalstimme)

**Zielgruppe:** "Grundsätzlich erstmal ich zur Beantwortung meiner Forschungsfragen. Weitere Zielgruppen stehen im Projekt nicht drinnen."

**Design:** "Funktional bis irrelevant"

**Kernwunsch:** "sehen können wer mit welchen Objekten, wo was macht"

**Features:**
- Web-Applikation mit Netzwerk-, Zeit- und Raumvisualisierungen
- Netzwerk aus Personen und Objekten
- Facettierte Suche und Analysefunktionen
- Verknüpfung mit Normdaten (GND, Wikidata)

**Quellenprioritäten:**
1. Raitbücher (7.800 Seiten, 26 Bände)
2. Hofordnungen (inkl. Hs. 2466–2469: Hochzeitsdokumente 1484)
3. Inventare
4. Kopialbücher

**Wunschliste:**
- Beratung semantisches Modell und Ontologie (CIDOC-CRM, ACE Guidelines)
- Workflow-Pipeline: Quelle → HTR/TEI → Annotation → RDF/GraphDB → Visualisierung
- **"Schulung von mir"** (Barbara will selbst lernen)
- Prototyp-Bau
- Annotation Guidelines (Praxeologie, Verbfokus)
- Datenintegration (SiCProD, Inventaria, Wikidata, Getty AAT)
- "Kann man irgendwie ein Glossar erstellen, einbinden, um die Genauigkeit zu verbessern?"

## Technische Constraints

| Constraint | Begründung |
|-----------|------------|
| GitHub Pages (statisch) | Kein Backend, kein Server |
| Vanilla JS/ES6 Module | Kein Framework, kein Build-Prozess, kein npm zur Laufzeit |
| Vendored Dependencies | Externe Libs in `/lib/`, keine CDN-Abhängigkeit |
| Öffentlich, kein Auth | Prototyp für Gutachter zugänglich |

## Gutachten-Antworten (10 Kritikpunkte → Prototyp)

FWF APART-GSK: 26/40 Punkte. Empfehlung: Ablehnung in vorliegender Fassung.

| Kriterium | Punkte |
|-----------|--------|
| Wissenschaftliche Originalität | 6/10 |
| State of Research | 7/10 |
| Forschungsfragen und Methoden | 7/10 |
| Arbeitsschritte und Zeitplan | 6/10 |

Gutachter: "Ich kann nur den DH-Teil des Projektantrages angemessen beurteilen."

### Die 10 Kritikpunkte

| # | Kritik (Zitat) | Prototyp adressiert durch | Ebene |
|---|----------------|--------------------------|-------|
| 1 | "Die computationellen Methoden beschränken sich auf ein Repertoire, das inzwischen zum Standard gehört." | Zeigen, dass Standard-Methoden auf DIESEN Quellen funktionieren. Innovation = Anwendung, nicht Methode. | Code |
| 2 | "Ein 'Digital X' ist nicht wirklich originell und möglicherweise nicht relevant genug." | Framing entschärfen: DH-Methoden als Werkzeuge für Court Studies, nicht Feldgründung. Landing Page betont Forschungsfragen. | Text |
| 3 | "Aktuell im Fokus stehende Ansätze mittels LLM werden leider nicht diskutiert." | Pipeline-Demo zeigt LLM-Integration. coOCR/HTR als Referenz. Epistemische Asymmetrie als konzeptueller Rahmen. | Code |
| 4 | "Verpasst wurde die Chance, auf die sprachlichen Herausforderungen einzugehen." | Quellen-Explorer zeigt Frühneuhochdeutsch mit Kurrentschrift, Abkürzungen, regionalen Varianten. | Code |
| 5 | "Ich vermisse die Rezeption von Forschungsarbeiten der historischen Linguistik." | Nicht im Prototyp adressierbar. Verweis auf Frühneuhochdeutsch-Forschung im Antragstext. | Text |
| 6 | "Insgesamt sind die Quellen nicht ausreichend charakterisiert." | Quellenübersicht mit 316 Einträgen, kategorisiert, filterbar, sortierbar. | Code |
| 7 | "Dies wäre besser zu beurteilen gewesen, wenn Quellenauszüge beispielhaft dargestellt worden wären." | Prototyp IST das Quellenbeispiel. Echte Raitbuch-Seiten mit Transkription und Entitäten. | Code |
| 8 | "Der Projektplan ist sehr generisch aufgebaut, leider ohne wirkliche Adaption auf die konkreten Aufgabenstellungen." | Funktionierender Prototyp IST der spezifische Plan. Pipeline-Demo zeigt jeden Schritt an konkretem Material. | Code |
| 9 | "Evaluation der technischen Verfahren wird zu wenig thematisiert." | CER-Anzeige für HTR, Konfidenz-Kategorien (sicher/prüfenswert/problematisch), Extraktionsstatistiken. | Code |
| 10 | "Bei einem Hypothesen-geleiteten Ansatz sollte festgestellt werden, nach welchen Kriterien man die Hypothese als erfüllt ansieht." | Dashboard: # Personen, # Relationen, # Praktiken, Relationsabdeckung (%), Quellen-Coverage (%), Netzwerk-Metriken. | Code |

**8 von 10 durch Code adressierbar. Punkte 2 und 5 erfordern Antragstext.**

**Stärkstes Argument:** Gutachter sagt selbst: "Aus der Anwendung dieser Verfahren auf das Quellenkorpus können neue, höchst innovative fachliche Forschungsergebnisse und historische Erkenntnisse heraus erwachsen."

## Erfolgskriterien für den Prototyp

Der Prototyp ist erfolgreich, wenn:
1. Ein Gutachter die URL öffnet und in 5 Minuten versteht, was das Projekt methodisch leistet
2. Barbara ihre Forschungsfragen an echten Daten explorieren kann (Personen, Relationen, Quellen)
3. Die Pipeline-Demo zeigt: Quelle → HTR/VLM → Extraktion → Netzwerk (an echtem Material)
4. Qualitätsmetriken sichtbar sind (CER, Konfidenz, Coverage)
5. Die 8 Code-adressierbaren Gutachten-Kritikpunkte beantwortet sind

## Prototyp-Prioritäten (User-Entscheidung)

1. **Pipeline-Demo** — Schrittweise an echtem Quellenbeispiel
2. **Facettierte Suche** — SiCProD-Daten explorierbar
3. **Quellenexploration** — Bild + Transkription + Entitäten
