# JOURNAL — Entscheidungen, Exploration, offene Fragen

## Phasenstatus (17.02.2026)

| Phase | Status | Ergebnis |
|-------|--------|----------|
| 1. Preparation | ✓ | Quelldokumente gesammelt (Root-Verzeichnis) |
| 2. Exploration | ✓ | SiCProD API geprobt, CSV analysiert, Transkribus Collection kartiert (115 Dok, 12.236 S.), IIIF verifiziert |
| 3. Destillation | ✓ | 6 Knowledge-Dateien + IMPLEMENTATION.md |
| 4. Implementation | In Arbeit | Phase A (Daten-Pipeline) gestartet |

---

## Entscheidungen (17.02.2026)

### User-Entscheidungen (mit Christopher abgestimmt)

| Frage | Entscheidung | Begründung |
|-------|-------------|------------|
| Prototyp-Typ | Funktionales Tool (nicht nur Mockup) | Gutachter soll interagieren können |
| Prioritäten | 1. Pipeline-Demo, 2. Facettierte Suche, 3. Quellenexploration | Pipeline adressiert Gutachten-Kritik am direktesten |
| Tech Stack | Vanilla JS wie coOCR/HTR | Konsistenz, kein Build-Prozess |
| Deployment | GitHub Pages | Statisch, öffentlich |
| Auth | Keine | Prototyp muss für Gutachter zugänglich sein |
| Bilder | Transkribus IIIF-URLs + ggf. Dropbox-Fallback | IIIF in `<img>` vermutlich CORS-frei |

### Offene Entscheidungen

| Frage | Optionen | Wer entscheidet |
|-------|---------|----------------|
| Fallstudie für Prototyp | A: Küchenkategorien in RB2 suchen, B: "Provision und Sold", C: Anderes Raitbuch | Barbara (Küchenmeister-Fund verifizieren) |
| NER-Granularität | 5 Entitäten (Prototyp) vs. 9 (Vollprojekt) | Barbara + BeNASch-Team |
| Practice↔BeNASch-Mapping | Anhand von 5–10 Beispieleinträgen | Barbara + Berner Team |
| coOCR/HTR Open-Source-Positionierung | Mail 04.02.2026 an Barbara | Barbara (Rückmeldung ausstehend) |

---

## Explorationsergebnisse (17.02.2026)

### SiCProD API: Erwartung vs. Realität

| Was wir dachten | Was wir fanden | Konsequenz |
|----------------|---------------|------------|
| Events: "Anzahl unbekannt" | **Nur 28 Events.** Landtage, Reichstage, Hochzeiten. | Alltagspraktiken kommen aus Raitbüchern, nicht aus SiCProD. |
| Salaries: 2.906 Einträge | **Keine Geldbeträge.** Nur Person↔Funktion-Links. | Finanzielle Daten müssen aus Raitbüchern extrahiert werden. |
| Institutionen: 215 mit Typen | **207 ohne Typ.** | Institutionen-Filter im Prototyp wenig nützlich. |
| Funktionen: "99 distinkte" | 79+ Hofämter, gute Vielfalt | Exzellent für facettierte Suche und Hofstruktur-Analyse. |
| Orte: 736 mit Koordinaten | Viele ohne lat/lng | Karte wird Lücken haben. |
| Personen: 6.288 | Gut dokumentiert, aber `first_name` null, `status` leer | Namensvarianten (`alternative_label`) vorhanden und nützlich. |

### CSV-Quellenübersicht: Qualitätsprobleme

**Schwere Probleme:**
- 16 leere Geisterspalten (Excel-Artefakte)
- "Digitalisiert"-Spalte enthält Seitenanzahl, kein Boolean
- "Transkribiert" enthält nur "Inventaria" (55×) oder nichts
- 10+ verschiedene Datumsformate
- En-dash vs. Hyphen inkonsistent (Repertorium vs. Rest)

**Duplikate und Fehler:**
- Hs. 0041: echtes Duplikat
- A 002.1 / A 2.1: Quasi-Duplikat mit Tippfehler
- 7 Quellen außerhalb Sigmunds Lebenszeit
- Datumswert in Art-Spalte (Zeile 304)

**Strukturelle Erkenntnis:**
Nur 55 von 315 Quellen sind transkribiert (17.5%), ausschließlich Burgeninventare (Inventaria-Projekt). Kein Raitbuch transkribiert.

### Dateiinventar: Abdeckungslücken (geschlossen)

| Lücke | Quelldokument | Jetzt erfasst in |
|-------|---------------|-----------------|
| Epistemische Asymmetrie | `sources/coocr-htr-epistemologie.md` | CONTEXT.md |
| Phase-1-Sequenzierung | `sources/strategische-planung.md` | REQUIREMENTS.md |
| Barbaras Originalstimme | `sources/requirements-barbara.md` | knowledge/REQUIREMENTS.md |
| NER-Kategorie-Diskrepanz | `sources/fwf-proposal-2025.md` vs. SiCPAS | CONTEXT.md |
| Offene Quellenfragen RB2 | `sources/raitbuch-2-analyse.md` | DATA.md |

### Bewusst nicht erfasst (Antragsebene, nicht Code)

- FWF-Bibliografie (~100 Referenzen)
- WP-Details + GANTT (36 Monate)
- Finanzielle Details (~370K Budget)

---

## Sackgassen

| Was | Warum Sackgasse | Erkenntnis |
|-----|----------------|------------|
| Transkribus API im Browser | CORS blockiert, OAuth2 im Client unsicher | Pre-Fetch mit Python |
| SiCProD Events für Praxis-Daten | Nur 28 Großereignisse | Alltagspraktiken aus Raitbüchern |
| SiCProD Salaries für Finanzen | Keine Beträge, nur Links | Finanzielle Daten aus Raitbüchern |
| SVG-Modelldiagramm lesen | 742 KB einzeilig | Inhalt textuell in CONTEXT.md |
| PDF auf Windows lesen | pdftoppm nicht verfügbar | Agent-basierte Extraktion |
| Transkribus Auth — falsches PW | Erstes PW falsch → 401. Korrektes PW vom User erhalten | Immer PW direkt vom User übernehmen, nicht aus Gedächtnis |

---

## Explorationsergebnisse: Transkribus (17.02.2026)

### Collection 2197991 — Erwartung vs. Realität

| Was wir dachten | Was wir fanden | Konsequenz |
|----------------|---------------|------------|
| ~55 Inventare transkribiert | **57 mit Text** (8.979 Zeilen, 35.730 Wörter). 3× DONE, 54× IN_PROGRESS. | Status-Feld unzuverlässig — nach Zeilenanzahl filtern |
| Raitbücher „nicht transkribiert" | **Bestätigt.** 26 Raitbücher, 8.561 Seiten, 0 Zeilen Text. Nr. 1–6 haben Layout-Analyse. | HTR muss vor Prototyp laufen (mindestens für RB2) |
| Collection-Umfang unklar | **115 Dokumente, 12.236 Seiten.** 64 Inventare + 26 Raitbücher + 12 Kopialbücher + 13 Andere | Deutlich mehr Material als erwartet |
| IIIF-URLs evtl. CORS-Problem | **Kein Problem.** IIIF UND Direkt-URLs laden ohne Auth. | OpenSeadragon kann direkt IIIF nutzen — kein Pre-Fetch für Bilder nötig |
| PAGE-XML Format unbekannt | Strukturiert: Page → TextRegion (Coords) → TextLine (Coords, Baseline, Unicode) | Parser-Logik klar, Pre-Fetch-Script kann geschrieben werden |

### Zusätzliche Dokumente (nicht in CSV)

Die Collection enthält Dokumente, die in der CSV-Quellenübersicht nicht explizit als „transkribiert" markiert sind:
- 12 Kopialbücher (2.224 Seiten, nur Bilder)
- Hof- und Regimentordnungen (TLA_HS_208.1 + 208.2, 149 Seiten)
- Hochzeitscluster: Hs. 2466 (33p), 2467 (58p), 2468 (19p), 2469 (54p)
- Weitere Handschriften: Hs. 113 (133p), Hs. 324 (86p), Hs. 514 (16p), Hs. 792 (7p), Hs. 5087.1+2 (218p)

---

## Offene Punkte (konsolidiert)

### Blockierend für Prototyp

- [x] ~~Transkribus-Credentials~~ → verifiziert (via env vars TRANSKRIBUS_USER/TRANSKRIBUS_PASS)
- [x] ~~Collection-ID~~ → **2197991** (https://app.transkribus.org/collection/2197991)
- [x] ~~Document-IDs auflisten~~ → 115 Dokumente kartiert, in `data/transkribus_collection.json`
- [x] ~~IIIF-URLs ohne Auth testen~~ → **Funktioniert** (bestätigt)
- [x] ~~Beispiel-Digitalisate zugänglich machen~~ → IIIF-URLs für alle 123 Seiten in `data/raitbuch2_pages.json`
- [x] ~~PAGE-XML der 57 Inventare als JSON exportieren~~ → 57 Dateien in `data/transcriptions/`, 522 Seiten, 8.979 Zeilen, 35.724 Wörter
- [x] ~~Mapping Transkribus-Titel → CSV-Signaturen~~ → 64/64 Inventare gematcht, in `data/source_mapping.json`

### Wichtig für Antrag

- [ ] Methodologischer Textbaustein (~1–2 Seiten) für ÖAW
- [ ] Fallstudie finalisieren (A/B/C) — inkl. Küchenmeister-Fund verifizieren (Barbara)
- [ ] Practice↔BeNASch-Mapping (mit Bern)
- [ ] Historische Linguistik-Literatur (Gutachten-Punkt 5)

### Nice-to-have

- [ ] Google Spreadsheet-URL für zusätzliche Metadaten
- [ ] Glossar-Idee von Barbara evaluieren
