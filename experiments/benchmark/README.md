# HTR-Prompt-Benchmark

Kleines, versioniertes Benchmark für die VLM-Transkription des DoCTA-Bestands (Raitbuch 2 und Burgeninventare, Tiroler Landesarchiv). Zweck: Prompt-Iterationen dokumentiert weiterentwickeln, ohne je eine frühere Iteration oder ihre Ergebnisse zu verlieren, und die Qualität jeder Iteration vergleichbar messen. Das Benchmark ist zugleich das Evaluations-Demonstrat für die Fallstudie und die Antragswiedereinreichung.

## Protokoll

1. **Seiten** stehen fest in `pages.json` (12 Seiten aus der visuellen Bestandssichtung aller 123 Raitbuch-Doppelseiten plus Inventar-Stichprobe; jede Seite vertritt ein Phänomen). Drei Inventarseiten tragen formalen Transkribus-DONE-Status und dienen als CER-Anker. Änderungen am Set nur dokumentiert und nur additiv.
2. **Prompts** liegen versioniert unter `prompts/` (`it01_*`, `it02_*`, ...). Eine Iteration ist nach ihrem ersten Lauf eingefroren; jede Änderung ist eine neue Iteration mit Änderungsbegründung im Prompt-Dokument. Iteration 02 trennt einen gemeinsamen Kern von Textsorten-Bausteinen (Raitbuch, Inventar).
3. **Läufe** landen unter `runs/` als je eine Datei pro (Seite × Bedingung × Wiederholung), mit vollständiger Provenienz: Prompt-Version und -Hash, Modell, Temperatur, Bildparameter, Zeitstempel. Es wird nie überschrieben oder gelöscht.
4. **Wiederholungen**: k >= 3 pro Bedingung, auf GT-Seiten k = 5. Befund aus Iteration 01: identische Requests streuen bei Temperatur 0 um bis zu 5,5 CER-Punkte; eine Rangfolge aus Einzelläufen ist Rauschen.
5. **Messgrößen**, stratifiziert nach Seite und Zone (Rubrik, Fließtext, Beträge), nie nur als Aggregat:
   - CER fair/strict gegen die DONE-GT-Seiten (Normalisierungsprofil dokumentiert im Runner)
   - positionsweise Token-Übereinstimmung zwischen Wiederholungen, getrennt für Worttokens und Zahl-/Währungstokens (Selbstkonsistenz; Jaccard-Overlap hat sich als irreführend erwiesen)
   - Ausbeute und Präzision der uncertain-Marker
   - Zeilenausfall gegen GT bzw. zwischen Wiederholungen
   - arithmetische Konsistenz der Beträge als Ausschlussfilter (nicht als Korrektheitsnachweis; das Modell glättet Bilanzen)
6. **Herkunft der Iterationen**: it01 ist der Testlauf vom 2026-08-26 (`../transcription-test/`, Ergebnisse bleiben dort erhalten); it02 synthetisiert die drei Analyseberichte desselben Tages (GT-Fehleranalyse, Raitbuch-Divergenz-Adjudikation, Bestandssichtung); it03 ist nach der Mini-GT-Adjudikation mit der Projektleitung geplant (echtes Raitbuch-Few-Shot, Pro-Modell-Vergleich).

## Stand (2026-08-26, Sessionende)

- pages.json: 18 Seiten (8 Raitbuch-Phänomenseiten, 9 DONE-GT-Inventarseiten, 1 dichte Inventarseite) + 5 Reserve
- it01: eingefroren; Ursprungslauf in `../transcription-test/results/`
- it02: erster Volllauf am 2026-08-26 gestartet (144 Läufe, k=5 auf GT-Seiten, 4 Worker)
- Runner: `run_benchmark.py`; ein Download-Race der ersten Version ist behoben, von der Kollision betroffene Läufe stehen in `errors.json`

## Wiedereinstieg

1. `python run_benchmark.py` füllt fehlende und fehlgeschlagene Läufe nach (skip-if-exists) und schreibt `summary.json`
2. `python run_benchmark.py --eval` rechnet nur die Auswertung neu
3. Auswertung lesen: `summary.json` je Seite × Iteration (CER fair/strict auf GT-Seiten mit Spannweite, positionsweise Konsistenz getrennt nach Wort- und Zahl-Tokens, uncertain-Ausbeute, Zeilenzahlen)
4. Danach offen: Viewer auf das runs-Format umstellen; it03 nach Mini-GT-Adjudikation mit der Projektleitung (echtes Raitbuch-Few-Shot, Pro-Modell-Vergleich)
5. API-Key: `GEMINI_API_KEY` in der Repo-Root-`.env` (gitignored), pro Session vom Operator

Lizenz wie Repo: Code MIT, Dokumente und Daten CC BY 4.0.
