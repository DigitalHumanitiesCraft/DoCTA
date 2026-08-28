# HTR-Prompt-Benchmark

Kleines, versioniertes Benchmark für die VLM-Transkription des DoCTA-Bestands (Raitbuch 2 und Burgeninventare, Tiroler Landesarchiv). Zweck: Prompt-Iterationen dokumentiert weiterentwickeln, ohne je eine frühere Iteration oder ihre Ergebnisse zu verlieren, und die Qualität jeder Iteration vergleichbar messen. Das Benchmark ist zugleich das Evaluations-Demonstrat für die Fallstudie und die Antragswiedereinreichung.

## Protokoll

1. **Seiten** stehen fest in `pages.json` (12 Seiten aus der visuellen Bestandssichtung aller 123 Raitbuch-Doppelseiten plus Inventar-Stichprobe; jede Seite vertritt ein Phänomen). Drei Inventarseiten tragen formalen Transkribus-DONE-Status und dienen als CER-Anker. Änderungen am Set nur dokumentiert und nur additiv.
2. **Prompts** liegen versioniert unter `prompts/` (`it01_*`, `it02_*`, ...). Eine Iteration ist nach ihrem ersten Lauf eingefroren; jede Änderung ist eine neue Iteration mit Änderungsbegründung im Prompt-Dokument. Iteration 02 trennt einen gemeinsamen Kern von Textsorten-Bausteinen (Raitbuch, Inventar).
3. **Läufe** landen unter `runs/` als je eine Datei pro (Seite × Bedingung × Wiederholung), mit vollständiger Provenienz: Prompt-Version und -Hash, Modell, Temperatur, Bildparameter, Zeitstempel. Es wird nie überschrieben oder gelöscht.
4. **Wiederholungen**: k >= 3 pro Bedingung, auf GT-Seiten k = 5. Befund aus Iteration 01: identische Requests streuen bei Temperatur 0 um bis zu 5,5 CER-Punkte; eine Rangfolge aus Einzelläufen ist Rauschen.
5. **Messgrößen**, stratifiziert nach Seite und Zone (Rubrik, Fließtext, Beträge), nie nur als Aggregat:
   - CER fair/strict gegen die DONE-GT-Seiten, mit Editierdistanz und Referenzlänge je Lauf, damit eine Rate ohne Nachrechnen lesbar bleibt (Normalisierungsprofil samt Versions-id im Runner und in `summary.json`)
   - positionsweise Token-Übereinstimmung zwischen Wiederholungen, getrennt für Worttokens und Zahl-/Währungstokens (Selbstkonsistenz; Jaccard-Overlap hat sich als irreführend erwiesen). Der Wert ist symmetrisch gerechnet, `2 × Treffer / (|a| + |b|)` je Tokenklasse, damit die Übereinstimmung zweier Wiederholungen nicht davon abhängt, welche von beiden zuerst steht. Ob ein Token eine Zahl ist, entscheidet seine Form vor der v/u- und j/i-Angleichung des fair-Profils, sonst fällt jedes Zahlzeichen mit `v` oder `j` aus der Zahlmetrik; ein Treffer zählt für eine Klasse nur, wenn beide Seiten sie tragen. Eine Klasse ohne Tokens auf beiden Seiten meldet keinen Wert statt einer Null, zwei leere Wiederholungen gelten als übereinstimmend
   - Ausbeute und Präzision der uncertain-Marker
   - Zeilenausfall gegen GT bzw. zwischen Wiederholungen
   - arithmetische Konsistenz der Beträge als Ausschlussfilter (nicht als Korrektheitsnachweis; das Modell glättet Bilanzen)
6. **Herkunft der Iterationen**: it01 ist der Testlauf vom 2026-08-26 (`../../experiments/transcription-test/`, Ergebnisse bleiben dort erhalten); it02 synthetisiert die drei Analyseberichte desselben Tages (GT-Fehleranalyse, Raitbuch-Divergenz-Adjudikation, Bestandssichtung); it03 ist nach der Mini-GT-Adjudikation mit der Projektleitung geplant (echtes Raitbuch-Few-Shot, Pro-Modell-Vergleich).

## Normalisierungsprofil und seine Version

`summary.json` trägt unter `normalisation_profile` je eine Versions-id für das fair- und das strict-Profil, dazu die Temperatur und je Seite die Referenzklasse (`transkribus-done` oder `self-consistency`). Die Versionsregel lautet, jede Änderung an `normalize()`, an der Tokenklassifikation oder an der Übereinstimmungsformel hebt die Version jedes Profils, das sie berührt, weil Summaries verschiedener Versionen nicht vergleichbar sind. Prompts und Läufe bleiben davon unberührt, eine Metrikänderung ist keine neue Iteration.

Stand ist `docta-fair-v2` und `docta-strict-v2` (2026-08-28). v2 fasst drei Änderungen zusammen, die Zahlklassifikation vor der v/u-Angleichung, das Entfernen aller Blattmarken-Schreibweisen und die symmetrische Übereinstimmung. Die Blattmarke betrifft beide Profile, deshalb steigt strict mit auf v2, obwohl die beiden anderen Änderungen nur das fair-Profil berühren.

Blattmarken kommen im Bestand in drei Schreibweisen vor, lang `[fol.1r]`, kurz `[1r]` und einmal fehlerhaft als `2[r]` mit der Blattzahl außerhalb der Klammer. Alle drei werden in Referenz und Hypothese entfernt, sonst zählt eine Marke, die nur eine Seite trägt, als Transkriptionsfehler. Eine eckige Klammer innerhalb eines Wortes (`It[em]`, `sup[r]a`) und die Verlustmarke `[...]` bleiben stehen, sie sind Aussagen über den Text.

## Entartete Referenz

Zwei Referenzseiten sind Deckblattetiketten, deren Transkribus-Export drei beziehungsweise vier Zeilen führt, während das Bild eine volle Seite trägt. Ihre CER liegt über 100 % und misst damit die Referenz statt des Laufs. `summary.json` markiert sie je Seite als `reference_degenerate`, berechnet aus `reference_chars`, der Länge der fair-normalisierten Referenz; unter 100 Zeichen gilt eine Referenz als entartet. Die Schwelle liegt in einer Lücke von einer Größenordnung, die beiden markierten Seiten normalisieren auf 30 und 38 Zeichen, die kürzeste tragfähige Referenz des Sets auf 1006. Ein Konsument schließt so über eine Dateneigenschaft aus und nie über den gemessenen Wert.

## Sekundäranalyse

`analyze_summary.py` rechnet aus `summary.json` und den Läufen die Aussagen, die eine Ratentabelle allein nicht trägt, und schreibt sie nach `analysis.json` und `analysis.md` (deutscher Bericht). Es liest ausschließlich von Platte, macht keinen Netzaufruf und liest keine Uhr; der Zeitstempel im Ergebnis ist der `generated`-Stand des ausgewerteten Summary, zwei Läufe über dasselbe Summary sind also byte-identisch. Grundlage sind die Referenzseiten ohne `reference_degenerate`.

Vier Auswertungen:

- Spearman-Rangkorrelation von Wort- und Zahlkonsistenz gegen die faire CER je Iteration, mit exaktem Permutations-p über alle 5040 Umordnungen der sieben Seiten
- der gepaarte Seitenvergleich it01 gegen it02 mit Vorzeichenzählung und exaktem Binomialtest, dazu die längengewichtete Mikro-CER neben dem ungewichteten Seitenmittel
- Präzision und Recall der uncertain-Marker gegen ein Token-Alignment auf die Referenz, mit der Basisrate nicht alignierter Tokens als Vergleichsmaßstab. Das Alignment ist eine Näherung, der Bericht sagt das an Ort und Stelle
- ein abgeleiteter Triage-Arbeitspunkt, die Wortkonsistenz-Schwelle, die das schlechteste CER-Drittel einsammelt

Die Statistik-Helfer sind in `../checks/test_analyze_summary.py` gegen von Hand nachrechenbare Werte geprüft, und derselbe Test hält `analysis.json` und `analysis.md` gegen einen Neubau aus dem danebenliegenden Summary.

## Few-Shot

Das Few-Shot-Beispiel (`FEWSHOT_DOC` 11327964, A 49.5, Seite 2) steht in keiner der drei Seitenmengen von Benchmark, Pilot und Pilot 2. Keine gemessene Seite hat also ihre eigene Referenztranskription im Prompt gesehen. Das Beispiel wird zur Laufzeit aus dem Export gebaut statt als Prompt-Datei eingefroren, deshalb deckt `prompt_hash` es nicht ab; jeder neue Lauf trägt zusätzlich `fewshot_hash`, den Hash des tatsächlich gesendeten Blocks. Bestehende Läufe bleiben unverändert.

## Stand (2026-08-28)

- pages.json: 18 Seiten (8 Raitbuch-Phänomenseiten, 9 DONE-GT-Inventarseiten, 1 dichte Inventarseite) + 5 Reserve
- it01: eingefroren; Ursprungslauf in `../../experiments/transcription-test/results/`
- it02: eingefroren und produktiv (Benchmark, Pilot, Pilot 2, Editionsstrecke); die drei Prompt-Dokumente tragen das seit 2026-08-28 im Kopf, der zusammengebaute Prompt bleibt davon unberührt, weil `extract_prompt` nur den ersten Codeblock liest. Volllauf abgeschlossen; zwei Läufe der dichten Inventarseite `inv_11348659_p1` bleiben offen, die API liefert dort wiederholt keinen Kandidaten (blockReason OTHER), dokumentiert in `errors.json`
- Runner: `run_benchmark.py` (Download-Race und Kandidaten-Fehlerbehandlung behoben); `summary.json` trägt jetzt IIIF-URL, Quelle, Referenzzeilen und die Run-Dateinamen je Iteration
- Metrik-Korrektur 2026-08-28, erster Schritt: die Zahlmetrik erfasst jetzt auch Zahlzeichen mit `v` und `j` (`vij`, `xxv`), die vorher in die Wortmetrik fielen. Die Zahlkonsistenz sinkt dadurch auf den meisten Seiten und die Wortkonsistenz steigt leicht, weil die verschobenen Tokens die instabilsten der Seite sind
- Methodenrevision 2026-08-28, zweiter Schritt: symmetrische Übereinstimmung, alle Blattmarken-Schreibweisen entfernt, Profil-Versionierung, `reference_degenerate` als Dateneigenschaft, Editierdistanz und Referenzlänge je Lauf, `empty` je Lauf. Prompts und Läufe sind unverändert, `summary.json` ist neu gerechnet. Die CER bewegt sich allein auf `inv_11328300_p1` und `inv_11328300_p2`, den beiden Seiten mit kurzer Blattmarke in der Referenz. Auch die Pilot-Summaries sind auf die korrigierte Metrik neu gerechnet; die ursprünglich publizierten Zahlen stehen als `pilot_summary_oldmetric.json` und `pilot2_summary_oldmetric.json` daneben
- `summary.json` und die Site-Kopie `docs/data/benchmark/summary.json` müssen byte-identisch sein, `pipeline/check_pipeline.py` prüft das als FAIL. `evaluate()` schreibt seit 2026-08-28 mit `newline="\n"`, sonst trägt eine Windows-Arbeitskopie CRLF in die Datei und die Kopie hängt vom Rechner ab, der sie geschrieben hat. Die Pilot-Summaries tragen die alten CRLF-Enden weiter; ihr Inhalt ist eingecheckt und richtig, und ihre Kohorten laufen nicht mehr
- Sekundäranalyse: `analyze_summary.py` schreibt `analysis.json` und `analysis.md` (Korrelation Konsistenz gegen CER, gepaarter Iterationsvergleich, uncertain-Präzision, Triage-Schwelle)
- `errors.json` wird bei jedem Füllauf geschrieben, auch wenn nichts fehlschlug, und trägt den Zeitstempel des neuesten Laufs auf Platte; ein behobener Blocker bleibt so nicht als Altlast stehen. Der `--eval`-Pfad schreibt die Datei nicht, die eingecheckte Fassung trägt deshalb noch die ältere reine Listenform und bekommt die Zeitstempel-Form beim nächsten Füllauf
- `--only` prüft den Iterationsnamen; die Auswertung deckt danach weiterhin alle Iterationen ab, damit ein Teil-Füllauf `summary.json` nicht beschneidet
- Viewer: `viewer.html` in diesem Ordner, Bild-Text-Synopse über alle Benchmark-Seiten mit Iterations-Tabs, Wiederholungs-Auswahl, Referenz-Vergleich und Metrik-Tabelle; Start mit `python -m http.server 8742` aus dem Repo-Root, dann `http://127.0.0.1:8742/evaluation/benchmark/viewer.html`

## Wiedereinstieg

1. `python run_benchmark.py` füllt fehlende und fehlgeschlagene Läufe nach (skip-if-exists) und schreibt `summary.json`
2. `python run_benchmark.py --eval` rechnet nur die Auswertung neu
3. `python analyze_summary.py` rechnet die Sekundäranalyse neu (`analysis.json`, `analysis.md`)
4. Auswertung lesen: `summary.json` je Seite × Iteration, oder im Viewer (siehe Stand)
5. Danach offen: Adjudikation der Thaur-Regression und der zwei entarteten Referenzseiten am Viewer; ein it01-Lauf über die Pilot-Seitenmengen als fehlender Out-of-Sample-Vergleich; it03 nach Mini-GT-Adjudikation mit der Projektleitung (echtes Raitbuch-Few-Shot, Pro-Modell-Vergleich)
6. API-Key: `GEMINI_API_KEY` in der Repo-Root-`.env` (gitignored), pro Session vom Operator

Lizenz wie Repo: Code MIT, Dokumente und Daten CC BY 4.0.
