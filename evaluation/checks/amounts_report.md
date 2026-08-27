# Arithmetische Probe der Raitbuch-Transkriptionen

Posten eines Blocks gegen dessen Summenzeile, je Denomination und ohne angenommene Umrechnung. Erzeugt von `check_amounts.py`.

## Kohorten

| Kohorte | Läufe | Blöcke | exact-match | mismatch | unverifiable | davon Teilmengen-Treffer | Betragsläufe ohne Summenzeile |
|---|---|---|---|---|---|---|---|
| pilot | 40 | 29 | 6 | 4 | 19 | 0 | 29 |
| pilot2 | 40 | 41 | 3 | 4 | 34 | 1 | 25 |

## Warum ein Block nicht entscheidet

| Grund | Blöcke |
|---|---|
| Summa without preceding item amounts | 13 |
| denominations differ, an unknown conversion could explain it | 13 |
| unparsed token in the block | 9 |
| single item, arithmetic is trivial | 7 |
| no named denomination on one side | 6 |
| Summa line carries no readable amount | 5 |

## Seiten, auf denen genau eine Wiederholung aufgeht

Kandidaten für eine gezielte Bildlektüre; die Probe weist dort einen Lauf aus.

| Seite | r1 | r2 |
|---|---|---|
| pilot2_rb2_p025 | unverifiable | clean |
| pilot2_rb2_p030 | clean | unverifiable |
| pilot2_rb2_p039 | clean | mismatch |

## Seiten, auf denen beide Wiederholungen scheitern

pilot_rb2_p015

## Nicht geparste Tokens

Tokens, die der Parser nicht liest und deshalb auch nicht rät.

| Token | Läufe |
|---|---|
| `...` | 4 |
| `dreizehn` | 2 |
| `f` | 1 |
| `funfzehn` | 1 |
| `iiij̄` | 1 |
| `t` | 1 |
| `tt` | 1 |
| `vje` | 1 |
| `w` | 1 |
| `ÿ` | 1 |

## Blöcke mit Befund

### pilot_rb2_p003__it02__r2.json

- mismatch: Posten 81 gld gegen Summe 200 gld [fol. 3r, „Suma seins emphabens“]

### pilot_rb2_p005__it02__r1.json

- exact-match: Posten 342 gld gegen Summe 342 gld [5r, „Sm̃a der bemelten schuld“]
- exact-match: Posten 127 gld gegen Summe 127 gld [5r, „Sm̃a des Innemens hat“]

### pilot_rb2_p005__it02__r2.json

- exact-match: Posten 342 gld gegen Summe 342 gld [5r, „Suma der bemelten Schuld“]
- exact-match: Posten 127 gld gegen Summe 127 gld [5r, „Suma des Innemens hat“]

### pilot_rb2_p014__it02__r1.json

- exact-match: Posten 384 gld gegen Summe 384 gld [14r, „Summa his so man Im schuldig“]

### pilot_rb2_p014__it02__r2.json

- exact-match: Posten 384 gld gegen Summe 384 gld [14r, „Sm̄a des so man jm schuldig“]

### pilot_rb2_p015__it02__r1.json

- mismatch: Posten 390 gld gegen Summe 90 gld [verso, „Summa sein emphabens“]

### pilot_rb2_p015__it02__r2.json

- mismatch: Posten 386 gld gegen Summe 86 gld [verso, „Summa sein emphabens“]

### pilot_rb2_p020__it02__r1.json

- mismatch: Posten 277 m gegen Summe 229 m [verso, „Suma seins vorgeschriben emphangenn“]

### pilot2_rb2_p023__it02__r1.json

- mismatch: Posten 22 gld gegen Summe 18 gld [23r, „Sum(m)a des Innemens facit ——“]

### pilot2_rb2_p025__it02__r2.json

- exact-match: Posten 1694 gld gegen Summe 1694 gld [verso, „Summa des Innemen fant“]

### pilot2_rb2_p030__it02__r1.json

- mismatch (Teilmenge der Zeilen [18, 21] geht auf): Posten 1441 duc gegen Summe 1287 duc [30r, „xij C lxxxvij duc j ß x d j hl“]

### pilot2_rb2_p039__it02__r1.json

- exact-match: Posten 172 lb gegen Summe 172 lb [fol. [1]v, „Sum̃a des was man dem yphöſer ſchuldig“]

### pilot2_rb2_p039__it02__r2.json

- mismatch: Posten 171 lb gegen Summe 122 lb [verso, „Suma zu was man dem yphofer ſchuldig“]
- exact-match: Posten 133 m gegen Summe 133 m [39r, „Sm̅a hie seins emphachens“]

### pilot2_rb2_p040__it02__r2.json

- mismatch: Posten 228 m gegen Summe 200 m [fol. verso, „Suma Irz Jnnemens ſtat“]
