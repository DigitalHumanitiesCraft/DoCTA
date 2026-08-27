# REQUIREMENTS: Ziele, Constraints, Erfolgskriterien

## Projektrahmen

| | |
|---|---|
| Projekt | DoCTA (Doing Court in the Tyrolean Alps) |
| Projektleitung | Dr. Barbara Denicolò, Universität Salzburg |
| DH-Komponente | Digital Humanities Craft OG (Christopher Pollin, Christian Steiner) |
| Phasen | 1: Promptotyping → 2: Workflow → 3: Web-App → 4: Training |
| Zeitrahmen | Geplante Wiedereinreichung bei der ÖAW (APART-GSK) |

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
1. Raitbücher (8.561 Seiten, 26 Bände)
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

Ersteinreichung ÖAW APART-GSK: Ablehnung in vorliegender Fassung. Das ÖAW-Gutachten bezog sich primär auf den DH-Teil.

### Die 10 Kritikpunkte (paraphrasiert)

| # | Kritik | Prototyp adressiert durch | Ebene |
|---|--------|--------------------------|-------|
| 1 | Computationelle Methoden als Standard, kein Innovationsnachweis | Zeigen, dass Standard-Methoden auf DIESEN Quellen funktionieren. Innovation = Anwendung auf frühneuhochdeutsche Quellen. | Code |
| 2 | "Digital X" nicht originell genug, Relevanzfrage | Framing: DH-Methoden als Werkzeuge für Court Studies, nicht Feldgründung. Landing Page betont Forschungsfragen. | Text |
| 3 | LLM-Ansätze nicht diskutiert | Pipeline-Demo zeigt LLM-Integration. coOCR/HTR als Referenz. Epistemische Asymmetrie als konzeptueller Rahmen. | Code |
| 4 | Sprachliche Herausforderungen nicht adressiert | Quellen-Explorer zeigt Frühneuhochdeutsch mit Kurrentschrift, Abkürzungen, regionalen Varianten. | Code |
| 5 | Historische Linguistik fehlt | Nicht im Prototyp adressierbar. Verweis auf Frühneuhochdeutsch-Forschung im Antragstext. | Text |
| 6 | Quellen nicht ausreichend charakterisiert | Quellenübersicht mit 312 Einträgen, kategorisiert, filterbar, sortierbar. | Code |
| 7 | Keine beispielhaften Quellenauszüge | Prototyp IST das Quellenbeispiel. Echte Inventarseiten mit Transkription und Entitäten. | Code |
| 8 | Projektplan zu generisch | Funktionierender Prototyp IST der spezifische Plan. Pipeline-Demo zeigt jeden Schritt an konkretem Material. | Code |
| 9 | Evaluation technischer Verfahren fehlt | Kategorielle Konfidenzstufen (sicher/prüfenswert/problematisch) an jeder extrahierten Entität und Relation, plus Extraktionsstatistik in der Pipeline-Demo (Verteilung nach Typ und nach Konfidenz). | Code |
| 10 | Keine Erfüllungskriterien für Hypothesen | Dashboard auf der Startseite mit sechs Kennzahlen: Personen, Relationen, Orte, Quellen, Transkriptionen, Funktionen. | Code |

**8 von 10 durch Code adressierbar. Punkte 2 und 5 erfordern Antragstext.**

### Was der Prototyp bewusst NICHT zeigt

Zwei naheliegende Evaluationsmaße fehlen, weil die Datengrundlage dafür fehlt:

| Geplant, nicht im Prototyp | Grund |
|---------------------------|-------|
| CER/WER für HTR | Es existiert keine Ground Truth zu den Raitbüchern und kein HTR-Durchlauf, gegen den gemessen werden könnte. Eine CER-Zahl wäre erfunden. Vorgesehen für das Vollprojekt, sobald HTR auf Raitbuch 2 gelaufen ist. |
| Abgeleitete Quoten (Relationsabdeckung, Quellen-Coverage, Netzwerk-Metriken) | Das Dashboard zeigt Rohzählungen. Quoten setzen einen definierten Nenner voraus (was gilt als vollständig abgedeckt?), der methodisch noch nicht festgelegt ist. |

## Erfolgskriterien für den Prototyp

Der Prototyp ist erfolgreich, wenn:
1. Ein Gutachter die URL öffnet und in 5 Minuten versteht, was das Projekt methodisch leistet
2. Barbara ihre Forschungsfragen an echten Daten explorieren kann (Personen, Relationen, Quellen)
3. Die Pipeline-Demo zeigt: Quelle → HTR/VLM → Extraktion → Netzwerk (an echtem Material)
4. Qualitätsangaben sichtbar sind: kategorielle Konfidenz pro Entität und Relation, Extraktionsstatistik, Verfügbarkeitspyramide der Quellen. Numerische HTR-Metriken (CER) bleiben dem Vollprojekt vorbehalten, siehe oben.
5. Die 8 Code-adressierbaren Gutachten-Kritikpunkte beantwortet sind

## Prototyp-Prioritäten (User-Entscheidung)

1. **Pipeline-Demo**: schrittweise an echtem Quellenbeispiel
2. **Facettierte Suche**: SiCProD-Daten explorierbar
3. **Quellenexploration**: Bild + Transkription + Entitäten
