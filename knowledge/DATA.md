# DATA -- Datenquellen, Struktur, Qualität

## 1. SiCProD API

**Base:** `https://sicprod.acdh-dev.oeaw.ac.at/apis/api/`
Öffentlich, kein Auth, JSON via `?format=json`. Paginiert: `?limit=500&offset=0`.

### Entitäten

| Typ | Endpunkt | Anzahl | Qualität |
|-----|----------|--------|----------|
| Person | `apis_ontology.person/` | 6.288 | Gut. Name, Daten, Geschlecht, Namensvarianten, Referenzen. `first_name` immer null, `status` immer leer. |
| Ort | `apis_ontology.place/` | 736 | Mittel. Typ vorhanden (Stadt, Burg, Dorf). **Viele ohne lat/lng** -- Karte wird Lücken haben. |
| Institution | `apis_ontology.institution/` | 215 | **Schlecht. 207 von 215 ohne Typ.** Nur 5 Universität, 1 Kanzlei, 1 Küche, 1 Pfarrei typifiziert. |
| Funktion | `apis_ontology.function/` | 1.613 | Gut. 79+ distinkte Hofämter. Mischung aus Hofpositionen und regionalen Ämtern. |
| Gehalt | `apis_ontology.salary/` | 2.906 | **Keine Geldbeträge.** Nur Verknüpfungen Person↔Funktion. |
| Event | `apis_ontology.event/` | **28** | **Nur Großereignisse:** Landtage (11), Reichstage (6), Hochzeiten (3), Schlachten (3). Keine Alltagspraktiken. |
| Relation | `relations.relation/` | 42.893 | Gut. Subj→Obj mit Typ. Hauptwert der API. |

### Beispiel: Person (Sigmund, ID 18)

```json
{
  "id": 18,
  "name": "Sigmund von Tirol",
  "start_date_written": "1427-10-26",
  "end_date_written": "1496-03-04",
  "gender": "männlich",
  "first_name": null,
  "status": "",
  "alternative_label": [
    "Sigismund", "Siegmund", "Sigmund der Münzreiche",
    "Erzherzog zu Österreich, Steiermark, Kärnten und Krain, Graf zu Tirol"
  ],
  "relation_types": ["event", "person", "salary", "place"],
  "references": [
    {
      "notes": "Nr. 5840 (8.2.1459 Feldkirch)",
      "bibtex": { "title": "Acta Cusana...", "volume": "III/1", "issued": {"date-parts": [[2022]]} }
    }
  ]
}
```

### Beispiel: Relation

```json
{
  "subj": {
    "label": "Sigmund von Tirol (ID: 18)",
    "content_type_key": "apis_ontology.person"
  },
  "obj": {
    "label": "Hochzeit Sigmund-Eleonore (ID: 17)",
    "content_type_key": "apis_ontology.event"
  },
  "relation_type": "nimmtteilan"
}
```

Relationstypen (Auswahl): `nimmtteilan`, `wirdausgeuebtvon`, `istan`, `wirdausbezahltanperson`, `hatfamilienbeziehungzu`, `istmitgliedvon`

### Ausgewählte Hofämter (von 79+)

| Funktion | Personen | Fallstudien-Relevanz |
|----------|----------|---------------------|
| Hofmeister | 12 | Hofstruktur |
| Küchenmeister | 10 | Hofküche |
| Stallmeister | 10 | Hofstruktur |
| Marschall | 8 | Hofstruktur |
| Salzmair zu Hall | 9 | Ökonomie |
| Hauskämmerer | 5 | Privatgemächer |
| Hofarzt | 1 | Medizinalpersonen |
| Leibarzt Sigmunds | 1 | Medizinalpersonen |
| Koch des Herzogs | 1 | Hofküche |
| Türhüter der Küche | 1 | Hofküche |
| Goldschmied | 1 | Luxuskonsum |
| Hofmaler | 1 | Luxuskonsum |
| Schleierwäscherin | 1 | Hofstruktur (Frauen) |
| Trompeterin | 1 | Hofstruktur (Frauen) |

### Geschlechterverteilung

| Geschlecht | Anzahl |
|-----------|--------|
| Männlich | 5.777 |
| Weiblich | 481 |
| Unbekannt | 30 |

### Kernwert und Grenzen

**Hauptwert:** Personennetzwerk -- 6.288 Personen mit 42.893 Relationen.
**Grenzen:** Events fast leer (28), Salaries ohne Beträge, Institutionen untypisiert. Finanzielle und praxeologische Daten müssen aus den Raitbüchern kommen, nicht aus SiCProD.

### Pre-Fetch-Strategie

Python-Script (`scripts/fetch_sicprod.py`): Alle Entitäten paginiert abrufen, Relationen als Edge-Liste, Netzwerk-Layout vorberechnen (networkx). Output: `data/persons.json`, `data/places.json`, `data/relations.json`, `data/network.json`. Geschätzt: ~4–5 MB roh, ~1–1.5 MB gzipped.

---

## 2. CSV-Quellenübersicht (312 Einträge)

**Datei:** `sources/quellen-katalog.csv`

### Spaltenstruktur (nur 8 von 24 befüllt)

| Spalte | Tatsächlicher Inhalt | Problem |
|--------|---------------------|---------|
| Kategorie | Quellenkategorie | OK |
| Signatur | Archivsignatur | OK |
| Titel | Beschreibung | OK |
| Datierung | Datum/Zeitraum | **10+ Formate, en-dash vs. hyphen inkonsistent** |
| Art | Meist "Einzelstück" | Repertorium missbraucht für Umfang ("390 Bände") |
| Projekt | SiCProD / Inventaria / DoCTA / leer | OK |
| Digitalisiert | **Seitenanzahl** (NICHT Boolean) | Spaltenname irreführend |
| Transkribiert | Nur "Inventaria" (55×) oder leer | Spaltenname irreführend |
| Spalte3–Spalte18 | **Komplett leer** | Excel-Artefakte |

### Verfügbarkeitspyramide

| Tier | Status | Anzahl | Seiten | Inhalt |
|------|--------|--------|--------|--------|
| **1** | Digitalisiert + Transkribiert | 55 | ~450 | NUR Burgeninventare (Inventaria-Projekt) |
| **2** | Digitalisiert, DoCTA-Prio | 19 | ~1.865 | 11 Hofordnungen, 7 Personeninventare, 1 Rechnung |
| **3** | Digitalisiert, SiCProD | 37 | ~10.888 | 25 Raitbücher + 12 Kopialbücher |
| **4** | Nicht digitalisiert | 204 | unbekannt | Rest (65% des Katalogs) |

### Kategorieverteilung

| Kategorie | Anzahl | % |
|-----------|--------|---|
| Burgeninventar | 84 | 26.7 |
| Rechnungen | 56 | 17.8 |
| Anderes | 43 | 13.7 |
| Repertorium | 42 | 13.3 |
| Kopialbuch | 37 | 11.7 |
| Personeninventar | 18 | 5.7 |
| Hof- und Speiseordnungen | 16 | 5.1 |
| Literatur | 9 | 2.9 |
| Kircheninventar | 6 | 1.9 |
| Landtagsakten | 4 | 1.3 |

### Bekannte Qualitätsprobleme

1. 16 Geisterspalten (Spalte3–18) -- Excel-Export-Artefakte
2. Datumsformate: `YYYY`, `YYYY-YYYY`, `YYYY.MM.DD`, `ca.`, `15. Jh.`, offene Ranges (`-1564`, `1229-`)
3. Repertorium-Sektion nutzt Unicode en-dash (–), Rest nutzt ASCII-Hyphen (-) → Parser-Falle
4. Echtes Duplikat: Hs. 0041 (zwei identische Zeilen)
5. Quasi-Duplikat: A 002.1 / A 2.1 (gleiche Quelle, Tippfehler "ubernmmen")
6. Cross-Listed: Hs. 0048 und Hs. 0057 je in zwei Kategorien
7. Zeitliche Ausreißer: 7 Quellen außerhalb Sigmunds Lebenszeit (1411–1645)
8. Datumswert in Art-Spalte (Zeile 304: "1361-1848")

### Raitbücher (25 Bände, SiCProD)

| Nr. | Datierung | Seiten | Anmerkung |
|-----|-----------|--------|-----------|
| 00 | 1454–1457 | 241 | "Raitbuch von Konrad Vintler" |
| 01 | 1460–1461 | 331 | |
| **02** | **1462–1463** | **123** | **Prototyp-Quelle** |
| 03 | 1463–1465 | 815 | Größter Band |
| 04–26 | 1466–1490 | ~7.150 | Lücken: 1476, 1481. Doppelt: 1485. Identisch: 22=23, 26=25. |
| **Gesamt** | 1454–1490 | **~8.660** | |

### Hofordnungen (DoCTA-Projekt, 11 Einträge)

Darunter ein zusammenhängendes Cluster zur Hochzeit Sigmunds 1484:
- Hs. 2466: "Notl der hochzeit" -- Einladungsregister (60 S.)
- Hs. 2467: "Rescribent der hochzeit" -- Verordnungen an Hofämter (100 S.)
- Hs. 2468: "Fueterzetl" -- Festteilnehmer und Pferde (35 S.)
- Hs. 2469: Register Hochzeit Sigmunds mit Katharina von Sachsen (140 S.)

### Für Prototyp nutzbar

Sofort: **55 Burgeninventare** (Tier 1, finale Transkriptionen in Transkribus Collection 2197991).
Mit Transkription: **Raitbuch 2** (123 Doppelseiten, Prototyp-Quelle, nicht transkribiert).
Script-Output: `data/sources.json` -- CSV bereinigt und als JSON für `sources.html`.

---

## 3. Transkribus Collection 2197991

### Übersicht (verifiziert 17.02.2026)

**Collection-ID:** 2197991
**URL:** https://app.transkribus.org/collection/2197991
**Gesamt:** 115 Dokumente, 12.236 Seiten

| Kategorie | Dokumente | Seiten | Mit Transkription |
|-----------|-----------|--------|-------------------|
| Burgeninventare | 64 | 569 | **57 ja** (8.979 Zeilen, 35.730 Wörter) |
| Raitbücher | 26 | 8.561 | **0** (nur Layout-Analyse oder leer) |
| Kopialbücher | 12 | 2.224 | 0 |
| Andere (Hofordnungen, Hss.) | 13 | 882 | 0 |

### Transkriptionsstatus-Realität

**Erwartung (aus CSV):** 55 Burgeninventare mit "Inventaria" = finale Transkriptionen.
**Realität:** 57 Burgeninventare haben Text (8.979 Zeilen). Nur 3 davon Status "DONE", 54 zeigen "IN_PROGRESS" -- aber **enthalten trotzdem vollständigen Transkriptionstext**. Status-Feld ist unzuverlässig als Qualitätsindikator.

**Raitbücher:** 26 Bände digitalisiert, 6 (Nr. 1–6) haben Layout-Analyse (Baselines, Regionen), 20 (Nr. 7–26) Status "NEW". **Keines hat Transkriptionstext.**

### Raitbücher in der Collection

| Nr. | Doc-ID | Seiten | Status |
|-----|--------|--------|--------|
| 1 | 12514207 | 331 | IN_PROGRESS (Layout) |
| **2** | **12514730** | **123** | **IN_PROGRESS (Layout, kein Text)** |
| 3 | 12515152 | 815 | IN_PROGRESS (Layout) |
| 4 | 12515414 | 347 | IN_PROGRESS (Layout) |
| 5 | 12515448 | 146 | IN_PROGRESS (Layout) |
| 6 | 12515416 | 170 | IN_PROGRESS (Layout) |
| 7–26 | diverse | 6.629 | NEW (nur Bilder) |

### API und Auth

**Endpunkt:** `https://transkribus.eu/TrpServer/rest` (Legacy REST API)
**Auth:** OpenID Connect via Keycloak (`account.readcoop.eu`), `client_id=transkribus-api-client`, `grant_type=password`.
**Credentials:** Via env vars TRANSKRIBUS_USER / TRANSKRIBUS_PASS

Wichtige Endpunkte:
- `GET /collections/{colId}/list` → Dokumentliste
- `GET /collections/{colId}/{docId}/fulldoc` → Alle Seiten mit Metadaten und PAGE-XML-URLs
- PAGE-XML: `https://files.transkribus.eu/Get?id={KEY}` (Auth-Header nötig)

### Bilder via IIIF (verifiziert)

```
https://files.transkribus.eu/iiif/2/{KEY}/full/{width},{height}/0/default.jpg
```

**Getestet und bestätigt:** IIIF-URLs funktionieren **ohne Auth** in `<img>` und `fetch()`. Beispiel Raitbuch 2, fol. 0v-1r:
- Thumb: `https://files.transkribus.eu/iiif/2/ISMVDKARQUBRQTZVDEQSWVHR/full/200,/0/default.jpg`
- Full: `https://files.transkribus.eu/iiif/2/ISMVDKARQUBRQTZVDEQSWVHR/full/max/0/default.jpg`

Auch Direkt-URLs funktionieren ohne Auth:
- `https://files.transkribus.eu/Get?fileType=view&id={KEY}` (1.2 MB JPG)

### PAGE-XML Format (Beispiel Thaur A 49.1)

```xml
<TextRegion type="page-number" id="r1">
  <Coords points="912,148 839,148 839,85 912,85"/>
  <TextLine id="r1l1">
    <Coords points="856,90 906,94 902,144 852,140"/>
    <Baseline points="852,135 902,139"/>
    <TextEquiv><Unicode>[1r]</Unicode></TextEquiv>
  </TextLine>
</TextRegion>
```

Struktur: Page → TextRegion (mit Typ und Coords) → TextLine (mit Coords, Baseline, Unicode-Text). ReadingOrder definiert Reihenfolge der Regionen.

### CORS-Problem

APIs für Desktop-Client konzipiert. `fetch()` auf PAGE-XML wird im Browser durch CORS blockiert. **Bilder sind CORS-frei.** → Pre-Fetch-Strategie für Transkriptionen, Bilder direkt ladbar.

### Pre-Fetch-Strategie

Script (`scripts/fetch_transkribus.py`): OAuth2-Auth → `fulldoc` pro Dokument → PAGE-XML parsen → JSON mit Zeilen, Koordinaten, Text.
Output: `data/transcriptions/{doc_id}.json`, `data/raitbuch2_pages.json` (123 Seiten mit IIIF-Keys)

### Offene Punkte

- [x] ~~Collection-ID~~ → **2197991**
- [x] ~~Transkribus-Credentials~~ → verifiziert (via env vars)
- [x] ~~Document-IDs auflisten~~ → 115 Dokumente kartiert, `data/transkribus_collection.json`
- [x] ~~IIIF-URLs ohne Auth testen~~ → **Funktioniert** (bestätigt)
- [ ] Vollständigen PAGE-XML-Export der 57 transkribierten Inventare als JSON konvertieren
- [ ] Mapping Transkribus-Titel → CSV-Signaturen herstellen

---

## 4. Raitbuch 2 (Prototyp-Quelle)

| Feld | Wert |
|------|------|
| Bestand | OÖKAM, Tiroler Landesarchiv |
| Transkribus Doc-ID | **12514730** |
| Umfang | 123 Doppelseiten (fol. 0v-1r bis fol. 122v-123r) |
| Dateinamen | `OÖKAM Raitbuch 2, fol. {Xv-Yr}.jpg` |
| Digitalisate | JPG via IIIF, ohne Auth ladbar |
| Layout-Analyse | Ja (Baselines, Regionen) -- kein Text |
| Transkriptionsstatus | **Nicht transkribiert** (0 Zeilen, 0 Wörter) |
| Datierung | 1462–1463 (Abgrenzung zu klären) |
| IIIF-Beispiel (fol. 0v-1r) | `https://files.transkribus.eu/iiif/2/ISMVDKARQUBRQTZVDEQSWVHR/full/max/0/default.jpg` |

### Gesicherte Strukturelemente (visuell bestätigt)

| Element | Beschreibung |
|---------|-------------|
| Rubrizierte Überschriften | Personennamen in größerer Kanzleischrift |
| "Nota" | Einleitungsformel für Einträge |
| "Item" | Markierung von Einzelposten |
| Zahlenkolonne | Geldbeträge am rechten Rand (fl., kr., lb.) |
| "daran sein Innemen" | Unterüberschrift (fol. 3r) |

### Gesicherte Personen

| Person | Folio | Sicherheit |
|--------|-------|------------|
| Sigmund von Brandis | fol. 2r | Lesbar |
| Graf Heinrich von Lupfen | fol. 3r | Lesbar |
| [Name] | fol. 2v | Unsicher |

### Erste Kategorie

**"prussian vnd Solde aussserhalb Lanndes"** (Provision und Sold außerhalb Landes) -- Personalzahlungen jenseits Tirols. Möglicher Küchenmeister-Fund in Zeile 9, fol. 2r ("[?]kuncmeister" → "kuechenmeister"?). **Verifizierung durch Barbara ausstehend.**

### Sprachliche Herausforderungen

- Kurrentschrift (ohne HTR nicht lesbar)
- Frühneuhochdeutsch mit regionalen Varianten
- Abkürzungen: fl. (Gulden), kr. (Kreuzer), lb. (Pfund)
- Lateinische Formeln in sonst deutschem Text

### Offene Fragen zur Quelle

- [ ] Welche Jahre deckt Raitbuch 2 genau ab?
- [ ] Welche weiteren Abrechnungskategorien enthält der Band?
- [ ] Gibt es einen Index oder eine Inhaltsübersicht?
- [ ] Wie verhält sich Raitbuch 2 zu den anderen 25 Raitbüchern?
- [x] ~~Existieren bereits Teiltranskriptionen?~~ → **Nein.** Layout-Analyse (Baselines) vorhanden, aber 0 Zeilen Text.
- [ ] Enthält der Band küchenbezogene Kategorien?
