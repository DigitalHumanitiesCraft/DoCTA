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
| 7 | Keine beispielhaften Quellenauszüge | Der Prototyp zeigt echte Inventarseiten mit Arbeitstranskription, Entitäten und Quelllink. Der Referenzstatus wird künftig explizit ausgewiesen. | Code |
| 8 | Projektplan zu generisch | Funktionierender Prototyp IST der spezifische Plan. Pipeline-Demo zeigt jeden Schritt an konkretem Material. | Code |
| 9 | Evaluation technischer Verfahren fehlt | Der HTR-Test liefert reale CER- und Divergenzdaten. `HTR-EVALUATION.md` definiert Referenzklassen, aufgabenspezifische Kennzahlen und fachliche Freigabe. Die Pipeline-Demo zeigt zusätzlich Prüfstatus und Extraktionsstatistik. | Code + Methode |
| 10 | Keine Erfüllungskriterien für Hypothesen | Die sechs Dashboard-Zählungen belegen Datenverfügbarkeit. Erfüllungskriterien für historische Hypothesen müssen im Antrag pro Forschungsfrage als beobachtbare Evidenz und Widerlegungskriterium formuliert werden. | Text + Methode |

**Sieben Punkte sind im Prototyp unmittelbar durch Code adressiert. Punkt 9 ist durch den aktuellen HTR-Test methodisch begonnen. Punkte 2, 5 und 10 benötigen eine explizite Ausarbeitung im Antrag.**

### Aktuelle Evaluationsgrenze

| Gegenstand | Aktueller Stand |
|------------|-----------------|
| CER auf Inventaren | Für eine Seite mit Referenzkandidat gemessen. Der formale Ground-Truth-Status und die Konventionszuordnung sind offen. Der Wert dient der Entwicklung. |
| CER/WER auf Raitbuch 2 | Vier Seiten wurden transkribiert. Eine akzeptierte Raitbuch-Referenz fehlt, daher sind nur Variantenstabilität, Strukturbeobachtung und fachliche Stichproben verfügbar. |
| Abgeleitete Quoten (Relationsabdeckung, Quellen-Coverage, Netzwerk-Metriken) | Das Dashboard zeigt Rohzählungen. Quoten setzen einen definierten Nenner voraus (was gilt als vollständig abgedeckt?), der methodisch noch nicht festgelegt ist. |

Der vollständige Prüfvertrag steht in `HTR-EVALUATION.md`.

## Erfolgskriterien für den Prototyp

Der Prototyp ist erfolgreich, wenn:
1. Ein Gutachter die URL öffnet und in 5 Minuten versteht, was das Projekt methodisch leistet
2. Barbara ihre Forschungsfragen an echten Daten explorieren kann (Personen, Relationen, Quellen)
3. Die Pipeline-Demo zeigt: Quelle → HTR/VLM → Extraktion → Netzwerk (an echtem Material)
4. Die Qualitätsangaben umfassen Prüfstatus pro Entität und Relation, Extraktionsstatistik, Verfügbarkeitspyramide der Quellen und klar gekennzeichnete experimentelle HTR-Metriken mit Referenzklasse.
5. Die sieben unmittelbar Code-adressierbaren Gutachten-Kritikpunkte beantwortet sind.

## Prototyp-Prioritäten (User-Entscheidung)

1. **Pipeline-Demo**: schrittweise an echtem Quellenbeispiel
2. **Facettierte Suche**: SiCProD-Daten explorierbar
3. **Quellenexploration**: Bild + Transkription + Entitäten
