# Sekundäranalyse des Benchmark-Summary

Datenstand `summary.json` 2026-08-28, Profile docta-fair-v2 und docta-strict-v2. Grundlage sind die 7 Referenzseiten mit tragfähiger Referenz (inv_11328300_p1, inv_11328300_p2, inv_11328300_p3, inv_11330019_p1, inv_11330019_p2, inv_11330020_p1, inv_11330020_p2); ausgeschlossen sind inv_11328300_p4, inv_11330019_p3 über das Datenfeld `reference_degenerate`.

## Sagt die Selbstkonsistenz die Fehlerrate vorher?

Spearman-Rangkorrelation der Übereinstimmung gegen die faire CER, je Iteration über n = 7 Seiten, mit exaktem Permutations-p über alle 5040 Umordnungen.

| Iteration | Wortkonsistenz vs. CER fair | p | Zahlkonsistenz vs. CER fair | p |
|-----------|-----------------------------|---|-----------------------------|---|
| it01 | -0.9286 | 0.00675 | -0.7143 | 0.0881 |
| it02 | -0.7857 | 0.04802 | -0.5714 | 0.2 |

Ein negatives Vorzeichen heißt, dass die Seiten mit geringer Übereinstimmung die Seiten mit hoher Fehlerrate sind. Damit ist die Voraussetzung erfüllt, referenzlose Seiten nach Übereinstimmung zu priorisieren. Die Effektstärke bleibt bei sieben Seiten unbestimmt. Ablesbar ist die Richtung.

## it01 gegen it02, seitenweise gepaart

Jede Seite wird mit sich selbst verglichen, also it02 gegen it01 auf derselben Referenz. Das Vorzeichen ist unabhängig davon, wie lang die Seiten sind, und der exakte Binomialtest über die entschiedenen Seiten prüft, ob die Richtung Zufall sein kann.

| Maß | besser | schlechter | p einseitig | p zweiseitig | Mikro-CER it01 → it02 | Seitenmittel it01 → it02 |
|-----|--------|------------|-------------|--------------|--------------------|--------------------|
| cer_strict | 7 von 7 | 0 | 0.00781 | 0.01562 | 37.3 % → 34.1 % | 37.3 % → 34.3 % |
| cer_fair | 4 von 7 | 3 | 0.5 | 1.0 | 23.6 % → 23.5 % | 23.4 % → 23.7 % |

Das Mikro-Mittel gewichtet jede Seite mit ihrer Referenzlänge, das Seitenmittel gewichtet jede Seite gleich. Wo beide auseinanderlaufen, stammt der Unterschied aus der Längenverteilung des Sets.

## Treffen die uncertain-Marker die Fehler?

Die Tokens eines Laufs werden gegen die Referenz aligniert; ein Token ohne Alignment gilt als falsch. Das ist eine Näherung. Ein an falscher Stelle aligniertes Token und ein korrektes Token, das sein Alignment an eine benachbarte Einfügung verliert, fallen beide auf die falsche Seite dieser Grenze. Die Basisrate ist der Anteil nicht alignierter Tokens insgesamt und damit die Präzision, die ein zufällig gesetzter Marker erreichen würde.

| Iteration | Marker | falsche Tokens | Tokens | Präzision | Recall | Basisrate |
|-----------|--------|----------------|--------|-----------|--------|-----------|
| it01 | 1161 | 4364 | 8889 | 95.4 % | 25.4 % | 49.1 % |
| it02 | 1988 | 4475 | 8877 | 88.4 % | 39.3 % | 50.4 % |

Die Präzision liegt in beiden Iterationen weit über der Basisrate, ein Marker steht also überzufällig oft auf einem Token, das dem Alignment entgeht. Der Übergang zu it02 kauft Recall mit Präzision, was der Absicht der Iteration entspricht.

## Ein abgeleiteter Arbeitspunkt für die Triage

Das schlechteste Drittel des Materials sind die 3 Seiten mit der höchsten fairen CER. Gesucht ist der Schnitt auf der Wortkonsistenz, der genau diese Seiten einsammelt.

| Iteration | Schwelle Wortkonsistenz | trennt | erfasst | Fehlalarme |
|-----------|-------------------------|--------|---------|------------|
| it01 | ≤ 0.552 | ja | 3 von 3 | 0 |
| it02 | ≤ 0.586 | nein | 3 von 3 | 1 |

Die Schwelle ist ein Vorschlag. Sie stammt aus sieben Seiten dreier Dokumente und ist an denselben Seiten abgelesen, an denen sie bewertet wird; ein Holdout fehlt. Auf unbekanntem Material taugt sie als Startwert für eine Reihenfolge der Prüfung. Für die Beurteilung einer einzelnen Seite bleibt der Blick ins Faksimile maßgeblich.

## Reproduktion

```
python evaluation/benchmark/analyze_summary.py
```
