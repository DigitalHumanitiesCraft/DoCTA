# Pilot: it02 unter Betriebsbedingungen

Der Benchmark misst auf handverlesenen Phänomenseiten; der Pilot beantwortet die Anschlussfrage, wie gut die Iteration-02-Prompts auf zusammenhängendem, nicht kuratiertem Material arbeiten. Er ist bewusst klein und läuft mit dem unveränderten Benchmark-Runner (`../benchmark/run_benchmark.py`, per Import wiederverwendet).

## Design

Zwei Kohorten, zwei Bewertungsmodi, je 2 Wiederholungen pro Seite:

1. **Inventar-Volldokument**: Naudersberg A 152.1 (docId 11330060, 8 Seiten), eine im Benchmark nicht vorkommende Burg. Bewertung je Seite als CER fair gegen die Transkribus-Arbeitstranskription. Das ist ein Vergleichssignal gegen eine ungeprüfte Referenz und kein Ground-Truth-Maß; systematische Abweichungen können auch auf Seiten der Arbeitstranskription liegen (zwei Konventionen im Bestand).
2. **Raitbuch-Abschnitt**: zwanzig aufeinanderfolgende Doppelseiten vom Buchbeginn (pageNr 2–21), inklusive Leer- und Übergangsseiten. Bewertung über Selbstkonsistenz der beiden Wiederholungen (positionsweise Token-Übereinstimmung, getrennt nach Wort- und Zahltokens); Seiten mit niedriger Zahlen-Konsistenz sind Sichtungskandidaten.

## Nutzung

1. `python run_pilot.py` fährt fehlende Läufe nach (skip-if-exists über den Benchmark-Runner) und schreibt `pilot_summary.json`
2. `python run_pilot.py --eval` rechnet nur die Auswertung neu
3. Läufe unter `runs/`, Fehler unter `errors.json`; Bilder im geteilten Cache `../benchmark/images/` (gitignored)
4. API-Key: `GEMINI_API_KEY` in der Repo-Root-`.env`, pro Session vom Operator

Lizenz wie Repo: Code MIT, Dokumente und Daten CC BY 4.0.
