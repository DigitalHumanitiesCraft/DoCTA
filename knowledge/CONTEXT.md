# CONTEXT -- Domänenwissen, Methoden, Epistemologie

## Hypothese

Durch semantische Annotation und Ereignismodellierung lassen sich Handlungsmuster rekonstruieren, die in konventioneller Quellenanalyse unsichtbar bleiben.

## Drei analytische Dimensionen

| Dimension | Frage | Methoden |
|-----------|-------|----------|
| Höfische Praktiken | Wie funktionierten Praktiken im höfischen Umfeld? | Netzwerkanalyse, Event Extraction |
| Besitz und Objektbewegungen | Wie trugen Besitz und Transfer von Objekten zu Praktiken bei? | Zirkulationsmuster (Kauf, Geschenk, Pfand) |
| Räumliche Strukturen | Welche Hierarchien existierten und wie beeinflussten sie Interaktionen? | Bewegungsmuster, Zugang, Raumnutzung |

## SiCPAS-Datenmodell

**SiCPAS** = Sigmund's Court Practices and Structures.

### Entitäten

| Entität | Erfasste Information | Prototyp |
|---------|---------------------|----------|
| **person** | Namen, Titel, Rollen. Agent oder Patient in Events. | ✓ |
| **place** | Geographische Orte (Innsbruck, Sigmundsberg) | ✓ |
| **space** | Funktionale Räume (Kammer, Küche, Stall, Frauenzimmer) | Zusammen mit place |
| **thing** | Gegenstände: Alltag (Brot, Wein, Holz) + Wert (Gold, Seide, Schmuck). Attribute: size, number, material, category, quality, color, function. | ✓ |
| **time** | Datierungen und Zeitperioden | ✓ |
| **practice** | Handlungen als Trigger-Verben (Prädikate/Verbformen) | ✓ |
| **group** | Institutionen (Rat, Kanzlei, Küchenteam) | Post-Prototyp |
| **court** | Hofzugehörigkeit (social group, profession) | Post-Prototyp |
| **source** | Quellengattung und Metadaten | Post-Prototyp |

**Prototyp-Set:** 5 Entitäten (person, place, thing, time, practice). Die Feinunterscheidungen place/space und group/court werden im Antrag als geplante Erweiterung dargestellt.

**NER-Diskrepanz:** FWF-Proposal Table 2 definierte 6 Kategorien ("object", "organization"). SiCPAS differenziert feiner (9 Entitäten, "thing" statt "object", "group"/"court" statt "organization"). Das Prototyp-Set (5) ist ein pragmatischer Kompromiss.

### Relationen

| Typ | Bedeutung |
|-----|-----------|
| belongs_to | Besitzverhältnisse |
| located_in | Räumliche Zuordnung |
| related_to | Allgemein (Verwandtschaft, Hierarchie) |
| part_of | Teil-Ganzes |
| used_by | Nutzungsbeziehung |

### Ereignismodellierung

Zwei Konzeptebenen:

| Ebene | Definition | Beispiel | Wer annotiert |
|-------|-----------|---------|---------------|
| **Practice** | Einzelne Handlung, Trigger-Verb, Agent↔Patient | "kaufen", "schenken", "kochen" | LLM + Validierung |
| **Event** | Cluster von Personen, Dingen, Praktiken -- benennbar | Hochzeit, Fest, Transaktion | **Nur Fachwissenschaftlerin** (interpretatorisch) |

Practice-Annotation folgt BeNASch-Schema. Event-Aggregation ist interpretatorische Leistung.

### Praxeologische Verbklassen

| Klasse | Verben |
|--------|--------|
| Ökonomisch | kaufen, verkaufen, schenken, vererben, leihen, verpfänden, stehlen, zählen, wiegen, messen, verwalten |
| Ästhetisch | genießen, bewundern, beschreiben, vergleichen, schätzen |
| Körperbezogen | essen, trinken, schlafen, reinigen, pflegen, baden |
| Repräsentativ | jagen, tanzen, ausstellen, konsumieren, korrespondieren |
| Produktiv | reinigen, reparieren, kochen, herstellen |

**Offenes Problem:** Verbklassen folgen historisch-inhaltlicher Logik, BeNASch folgt linguistisch-formaler Logik. Mapping anhand von 5–10 Beispieleinträgen nötig, idealerweise mit Berner Team.

## BeNASch-Annotationsschema

**BeNASch** = Bernese Early New High German Annotation Scheme. ACE-basiert, CIDOC-CRM-kompatibel.

Modelliert Ereignisse formal: Trigger-Verb → Agent → Patient. Annotationsplattform: INCEpTION. NER-Modelle: FLAIR, BERT, SpaCy.

**Verbindung Practice↔BeNASch noch nicht operationalisiert.** Beide Systematiken unterschiedlich motiviert. Konkretes Mapping ausstehend.

## Fallstudien

| Fallstudie | Quellen | Status |
|-----------|---------|--------|
| **Hofküche** (empfohlen für Prototyp) | Raitbücher (Zahlungen), Inventare (Küchenausstattung) | Küchenmeister-Fund in Raitbuch 2 fol. 2r -- Verifizierung durch Barbara ausstehend |
| Herzogliche Privatgemächer | Inventare, Hofordnungen | Nicht begonnen |
| Medizinalpersonen | Raitbücher, Raumanalyse | Nicht begonnen |
| Luxuskonsum | Raitbücher, Inventare | Nicht begonnen |

**Entscheidung offen.** Drei Optionen: A) Im Raitbuch 2 nach Küchenkategorien suchen, B) "Provision und Sold" als eigenständige Studie, C) Anderes Raitbuch wählen. Für Drittmittelstrategie zählt methodische Überzeugungskraft, nicht spezifische Fallstudie.

## SiCProD → SiCPAS Mapping

| SiCProD-Entität | SiCPAS-Entität | Anmerkung |
|----------------|----------------|-----------|
| Person (6.288) | person | Direkt |
| Place (736) | place | place/space-Unterscheidung fehlt in SiCProD |
| Institution (215) | group / court | 207 ohne Typ -- Zuordnung unklar |
| Function (1.613) | practice (Trigger) | Funktionen ≠ Praktiken, aber Brücke vorhanden |
| Salary (2.906) | -- | Verknüpfung Person↔Funktion, keine Geldbeträge |
| Event (28) | event | Nur Großereignisse, keine Alltagspraktiken |
| Relation (42.893) | Relationen | Relationstypen müssen auf SiCPAS gemappt werden |

## Kooperationspartner

| Partner | Beitrag | Prototyp-Relevanz |
|---------|---------|-------------------|
| **SiCProD** (Innsbruck/ACDH) | Prosopographische DB, API (6.288 Personen) | **Primäre Datenquelle** |
| **BeNASch** (Bern) | Annotationsschema für Frühneuhochdeutsch | Schema-Kompatibilität |
| **The Flow Project** (Bern/Bielefeld) | Deep Learning für Event/Relation Extraction | Methodische Abstimmung |
| **Inventaria** (Salzburg/Innsbruck) | Objektthesaurus (5.300 Einträge, Getty AAT) | Objektklassifikation (Prio 3) |
| **DEPCHA** (Graz) | Rechnungsbuch-Semantik | Strukturmodelle für Raitbücher |
| **ZB Zürich** | Paralleler coOCR/HTR-Anwendungsfall | Nachhaltigkeitsargument |
| **VieCPro** (Wien) | Frühneuzeitlicher Wiener Hof | Vergleichsperspektive |
| **ManMax** (Wien) | Maximilian-SFB | Methodentransfer |

## Epistemische Grundlagen

### Epistemische Asymmetrie

LLMs liefern keine verlässliche Selbsteinschätzung ihrer Outputs. Das ist eine **architektonische Eigenschaft**, kein temporäres Defizit. Referenzen: Zheng et al. 2023 (systematische Biases), Wang et al. 2024 (Position Bias), Ye et al. 2024 (Authority Bias).

**Konsequenz für den Prototyp:** Numerische Konfidenzwerte (0.87, 0.93) sind irreführend. Stattdessen **kategorielle Konfidenz**: sicher / prüfenswert / problematisch.

### Critical Expert in the Loop

Fachwissenschaftlerin validiert, nicht nur kontrolliert. Das Forschungstool unterstützt menschliche Expertise, ersetzt sie nicht. Die Aggregation von Practices zu Events ist eine interpretatorische Leistung, die nicht automatisiert werden kann.

### Hybride Validierung (aus coOCR/HTR)

| Schicht | Methode | Beispiel |
|---------|---------|---------|
| 1: Deterministisch | Regelbasiert | Datumsformate, Währungsangaben, Tabellenstruktur |
| 2: Optional | LLM-as-Judge (4 Perspektiven) | Paläographisch, linguistisch, strukturell, domänenspezifisch |

### Methodologische Positionierung

LLMs als Prototyping-Instrumente, deren Outputs systematisch durch Fachexpertise validiert werden. Promptotyping als iterative, quellenkritisch kontrollierte Methode. Dieser Absatz muss als ~1–2 Seiten Textbaustein für die FWF-Wiedereinreichung ausformuliert werden.

## Ressourcen-URLs

| Ressource | URL |
|-----------|-----|
| GitHub DoCTA | https://github.com/DigitalHumanitiesCraft/DoCTA |
| SiCProD API | https://sicprod.acdh-dev.oeaw.ac.at/apis/api |
| BeNASch | https://dhbern.github.io/BeNASch/ |
| Inventaria | https://www.inventaria.at |
| DEPCHA | https://gams.uni-graz.at/context:depcha |
| coOCR/HTR Demo | http://dhcraft.org/co-ocr-htr |
| coOCR/HTR Repo | https://github.com/DigitalHumanitiesCraft/co-ocr-htr |
