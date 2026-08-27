# HTR-EVALUATION

## Geltungsbereich

Dieses Dokument legt fest, wie DoCTA maschinelle Transkriptionen erzeugt, vergleicht und fachlich freigibt. Der Begriff HTR dient dabei als Oberbegriff. Gemini verarbeitet ganze Seiten als Vision-Language-Modell. Transkribus erkennt Text auf Basis einer Layout- und Zeilenstruktur.

Der dokumentierte Teststand stammt vom 26.08.2026. Beobachtet wurden vier Doppelseiten aus Raitbuch 2 und eine Inventarseite mit vorhandener Transkription. Alle sechs Varianten verwendeten `gemini-3.7-flash`. Die Rohdaten liegen unter `experiments/transcription-test/`.

## Status der Referenzen

Die Bezeichnung „Ground Truth“ im Test-Viewer ist vorläufig. Keines der 57 Inventardokumente besitzt im Projekt einen dokumentierten, formal abgenommenen Ground-Truth-Status. Drei Dokumente stehen in Transkribus auf `DONE`, 54 auf `IN_PROGRESS`. Dieser Workflow-Status belegt keine fachliche Abnahme.

Der Bestand enthält außerdem zwei Transkriptionskonventionen. Metriken dürfen deshalb erst nach einer Konventionspartitionierung oder nach einem dokumentierten Adapter gemeinsam ausgewertet werden. Bis zur fachlichen Adjudikation lautet die korrekte Bezeichnung **Inventar-Referenzkandidat**.

| Referenzklasse | Bedeutung | Zulässige Verwendung |
|----------------|-----------|----------------------|
| Formal abgenommene Ground Truth | Bild, Zeilenzuordnung und Transkription wurden fachlich geprüft und versioniert | Modellvergleich und belastbare CER/WER |
| Verifizierte Referenz | Stichprobe wurde gegen das Bild geprüft, besitzt aber noch keinen formalen Korpusstatus | Entwicklungsvergleich mit klarer Kennzeichnung |
| Arbeitstranskription | Text ist vorhanden, Konvention oder Freigabe ist ungeklärt | Fehlersuche und Auswahl von Adjudikationsstellen |
| Modelloutput | Automatisch erzeugter Vorschlag | Sichtung, Vergleich und manuelle Korrektur |

## Beobachtete Ergebnisse

### Inventar-Referenzkandidat

Der Test auf einer Inventarseite mit 39 Referenzzeilen ergibt folgendes Bild. Die faire CER verwendet die derzeitige projektspezifische Normalisierung. Sie entfernt unter anderem Diakritika, vereinheitlicht `u/v` und `i/j` und löst Abkürzungsmarkierungen auf. Diese Zahl beschreibt deshalb eine andere Fehlerklasse als die strikte CER.

| Variante | Strikte CER | Faire CER | Wortüberlappung |
|----------|-------------|-----------|------------------|
| V1 Baseline | 20,3 % | 10,7 % | 41,3 % |
| V2 Strukturiert | 20,6 % | 9,9 % | 41,5 % |
| **V3 Few-Shot** | **17,1 %** | **7,9 %** | 40,0 % |
| V4 Seitenteilung | 24,3 % | 14,6 % | 34,8 % |
| V5 Wiederholung | 19,6 % | 9,1 % | 39,4 % |
| V6 Bildverbesserung | 19,0 % | 8,9 % | **43,6 %** |

V3 ist innerhalb dieses Tests der beste Flash-Kandidat für Zeichenfolgen. V6 liefert die höchste Wortüberlappung und die zweitbeste faire CER. V4 verschlechtert das Ergebnis deutlich. Eine einzelne Inventarseite trägt keine Entscheidung für Raitbuch 2, weil Schrift, Layout und Textsorte abweichen.

### Raitbuch 2 ohne Ground Truth

Für die drei texttragenden Raitbuch-Seiten liegt die Wortüberlappung der Varianten mit V2 nur zwischen 30 und 52 Prozent. Wiederholte oder leicht veränderte Durchläufe unterscheiden sich damit materiell. Die Varianten erkennen häufig Überschriften, Seitenaufteilung und Eintragsstruktur. Personennamen, Jahreszahlen und Geldbeträge wechseln jedoch zwischen den Ausgaben. Gerade die Beträge sind für Rechnungsbuchforschung zentral und derzeit nicht belastbar.

| Seite | Beobachtung | Aussagekraft |
|-------|-------------|--------------|
| fol. 1v–2r | Namen, Datierungen und Beträge variieren stark | Struktur erkennbar, Einzelwerte ungeprüft |
| fol. 2v–3r | Hauptnamen erscheinen relativ stabil, Beträge und Formeln wechseln | Gute Adjudikationsgrundlage, keine Forschungsdaten |
| fol. 39v–40r | Niedrigste Variantenübereinstimmung mit 30 bis 40 Prozent Wortüberlappung | Schwierige Seite, gezielte Bildausschnitte erforderlich |
| fol. 89v–90r | Alle strukturierten Varianten erkennen die leere Seite | Leerseiten- und Layout-Triage funktioniert im Test |

Wortüberlappung misst Übereinstimmung zwischen Modellen. Sie misst keine historische Richtigkeit. Modellkonsens und arithmetische Plausibilität dienen als GT-freie Hinweise für die Priorisierung menschlicher Prüfung.

## Eignung nach Forschungszweck

| Zweck | Aktueller Status | Konsequenz |
|-------|------------------|------------|
| Leerseiten- und Layout-Triage | Beobachtet funktionsfähig | Flash kann Seiten vorsortieren und strukturierte JSON-Ausgaben erzeugen |
| Kategorienübersicht über einen Band | Plausibler Pilot | Flash-Ausgaben können Such- und Sichtungshypothesen erzeugen; Stichproben bleiben erforderlich |
| Personen- und Funktionskandidaten | Fachlich ungeprüft | NER darf nur auf Text mit Quelllink und Prüfstatus arbeiten |
| Diplomatische Edition | Unzureichend belegt | Freigabe verlangt zeilenbezogene Prüfung gegen das Faksimile |
| Geldbeträge und Abrechnungsrelationen | Im Test instabil | Exakte Beträge, Einheit und Zeilenzuordnung brauchen gesonderte Validierung |

## Empfohlenes Erzeugungsverfahren

1. Ein Manifest fixiert Dokument-ID, Folio, Bild-URL, Prüfsumme, Modellversion, Promptversion und Bildtransformation.
2. Die vorhandenen Transkribus-Baselines und Regionen werden als Layoutreferenz übernommen. Für ganze Doppelseiten bleibt zusätzlich ein seitenweiser VLM-Lauf erhalten.
3. Jede gesperrte Testseite wird mit einem spezialisierten HTR-Basismodell und mit der aktuellen VLM-Konfiguration verarbeitet. Text Titan I ter ist der naheliegende erste Transkribus-Baseline-Kandidat. Seine publizierten Herstellerwerte ersetzen den direkten DoCTA-Vergleich nicht.
4. V3 Few-Shot dient als aktuelle Flash-Entwicklungskonfiguration. V6 bleibt der zweite Kandidat. Regionale Ausschnitte werden gezielt für schwierige Namen, Randspalten und Beträge eingesetzt.
5. Abweichungen zwischen Systemen erzeugen eine Divergenzliste mit Bildausschnitt, Zeilenreferenz und konkurrierenden Lesarten. Die Fachwissenschaft entscheidet direkt am Faksimile.
6. Rohoutput, automatisch geprüfter Text und fachlich akzeptierter Text bleiben getrennte Datenstände. Jede Weiterverarbeitung übernimmt den Prüfstatus und die Provenienz.

Ein stärkeres Vision-Language-Modell wird auf demselben gesperrten Seitensatz verglichen. Modellfamilie und allgemeine Herstellerbeschreibung reichen als Auswahlgrund nicht aus. Ein eigenes HTR-Modell wird erst geprüft, wenn genügend korrigierte Raitbuch-Zeilen vorliegen und ein separater Testsatz erhalten bleibt.

### Umsetzung im Evaluator

`aep_eval` soll Transkribus PAGE XML und den abgeleiteten DoCTA-Datenvertrag direkt lesen. Der Reader übernimmt Seiten-ID, Regions- und Zeilenreihenfolge, Transkription, Konventionslabel und Referenzstatus. Das Normalisierungsprofil `docta-diplomatic-v1` wird als versionierte Konfiguration implementiert. Jeder Lauf erzeugt maschinenlesbare Seitenmetriken sowie eine Divergenzliste mit den zugehörigen Bildregionen.

## Evaluationsvertrag

### Testaufbau

- Entwicklungsmaterial und gesperrter Testsatz werden getrennt.
- Die Stichprobe deckt Schreiber, Seitentypen, Erhaltungszustände, Textdichte, Tabellen- oder Spaltenlayout und Leerseiten ab.
- Inventare und Raitbücher werden getrennt ausgewertet.
- Die beiden Inventar-Konventionen erhalten eigene Labels. Ein Adapter bildet beide Konventionen auf einen versionierten Datenvertrag ab.
- Jede Kennzahl nennt Referenzklasse, Normalisierungsprofil, Modellversion und Stichprobengröße.

### Kennzahlen

| Prüfgegenstand | Kennzahl oder Verfahren | Zweck |
|----------------|--------------------------|-------|
| Zeichenfolge | Strikte CER | Diplomatische Nähe ohne verdeckte Normalisierung |
| Konventionsunterschiede | CER mit versioniertem Profil `docta-diplomatic-v1` | Vergleich nach explizit dokumentierten Äquivalenzen |
| Worterkennung und Reihenfolge | WER und Bag-of-Words-WER | Trennung von Erkennungs- und Lesereihenfolgefehlern |
| Layout | Zeilenabdeckung, Regionszuordnung und Lesereihenfolge | Prüfung der Seitenstruktur |
| Kategorien | Precision und Recall auf fachlich markierten Kategorien | Eignung für die Bandübersicht |
| Entitäten | Precision, Recall und F1 pro Entitätstyp | Eignung als NER-Eingabe |
| Geldbeträge | Exakter Treffer von Wert, Einheit und Buchungszeile | Forschungsrelevante Rechnungsgenauigkeit |
| Stabilität | Wiederholungsläufe und systemübergreifende Divergenz | Auswahl von Prüfstellen |
| Korrekturaufwand | Zahl der fachlichen Eingriffe pro akzeptierter Seite | Praktische Vergleichbarkeit der Verfahren |

Die bisherige „faire CER“ wird beibehalten, bis `docta-diplomatic-v1` spezifiziert ist. Sie wird stets zusammen mit der strikten CER ausgegeben. Die aktuelle Jaccard-Wortüberlappung bleibt ein Stabilitätsindikator und wird durch WER sowie Bag-of-Words-WER ergänzt.

### Freigaberegel

Eine Konfiguration wird für genau den Forschungszweck freigegeben, für den sie den gesperrten Test erfüllt. Die Kategorienübersicht, die diplomatische Edition und die Betragserschließung erhalten getrennte Entscheidungen. V3 ist derzeit ein Entwicklungskandidat. Eine Produktionsentscheidung folgt nach dem Vergleich mit einem spezialisierten HTR-Modell und nach der fachlichen Prüfung einer repräsentativen Raitbuch-Stichprobe.

## Fachliche Prüfpunkte

- Die Projektleitung legt die diplomatische Zielkonvention und zulässige Normalisierungen fest.
- Eine repräsentative Raitbuch-Stichprobe erhält zeilenbezogene Referenztranskriptionen.
- Beträge werden zusammen mit Einheit, Zeile und möglicher Summenbeziehung adjudiziert.
- SiCProD-Namensvarianten werden ausschließlich im Post-Processing eingesetzt. Jeder Fuzzy Match bleibt als Vorschlag mit Ausgangslesart erhalten.

## Evidenz und Quellen

### Lokale Evidenz

- `experiments/transcription-test/results/summary.json`
- `experiments/transcription-test/results/*.json`
- `experiments/transcription-test/transcribe_test.py`
- `experiments/transcription-test/viewer.html`

### Methodische und technische Quellen

- Google, [Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash). Modellbeschreibung und Unterstützung strukturierter Ausgaben.
- READ-COOP, [The Text Titan I ter](https://www.transkribus.org/models/the-text-titan-i-ter). Offizielle Modellbeschreibung; Leistungsangaben sind Herstellerwerte.
- Ströbel et al. 2022, [Evaluation of HTR models without Ground Truth Material](https://aclanthology.org/2022.lrec-1.467/). GT-freie Metriken unterstützen die Modellauswahl im Anwendungskontext.
- Vidal et al. 2023, [End-to-End Page-Level Assessment of Handwritten Text Recognition](https://arxiv.org/abs/2301.05935). Seitenweite Evaluation soll Erkennungsqualität und Lesereihenfolge getrennt messen.
