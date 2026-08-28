# Iteration 02 — Baustein Rechnungsbuch (eingefroren)

Wird an it02_kern.md angehängt, wenn die Seite aus einem Raitbuch stammt.

Seit dem ersten Lauf eingefroren und in Benchmark, Pilot und Editionsstrecke produktiv. Änderungen nur als neue Iteration.

```
TEXTSORTE: RAITBUCH (RECHNUNGSBUCH)

Die Einträge sind hochgradig uniform aufgebaut:
- Namensrubrik in größerer Auszeichnungsschrift (ein Personenname je Eintrag)
- Abrechnungsabsatz in Fließtext ("Nota an ... in gegenwurtikait ...")
- Postenliste mit "It(em)"-Markern; die Marker stehen in einer eigenen
  Marginalspalte links und werden als kind "marginal" der jeweiligen Zeile
  zugeordnet
- Summenzeile ("Summa ...") und ggf. Restbetrag

BETRÄGE

Beträge sind der fehleranfälligste Teil. Für jede Zeile mit einem Betrag wird
zusätzlich zum Zeilentext das Feld "amount" gefüllt, mit getrennten Angaben:
- "multiplier": Hochstellung, falls vorhanden (z.B. "C" für Hundert, "m" für
  Tausend), sonst leer. Prüfe die Minim-Zahl vor der Hochstellung einzeln.
- "numeral": das Zahlzeichen exakt wie geschrieben (römisch, ggf.
  durchstrichenes L = 50)
- "unit": das Währungskürzel exakt wie geschrieben

Zulässige Einheiten in diesem Bestand: gld, Rhgld, lb (Pfund), ß (Schilling),
d (Pfennig), kr (Kreuzer), m mit Makron (Mark), hl (Heller). Ein Kürzel, das
nicht in dieser Liste steht, wird unaufgelöst übernommen und als unsicher
gemeldet; erfinde keine Einheit.

VERBOT DER BILANZGLÄTTUNG: Beträge werden niemals so angepasst, dass eine
Summe aufgeht. Eine nicht aufgehende Rechnung bleibt stehen, wie sie gelesen
wurde. Jeder Betrag wird unabhängig von Summen- und Restzeilen gelesen.

Füllstriche vor Beträgen als "——" wiedergeben, aber nur wo die Vorlage
tatsächlich einen zeigt.
```

Begründungen: Struktur-Template nutzt die belegte Uniformität des Bandes (Bestandssichtung); amount-Objekt erzwingt die getrennte Entscheidung über Multiplikator/Zahl/Einheit statt Mitlaufen im Textstrom (Betragszone hatte 9-17% positionsweise Übereinstimmung); geschlossenes Einheitenvokabular inkl. Mark (drei Läufe erfanden an der Mark-Stelle eine Einheit); Bilanzglättungsverbot gegen den nachgewiesenen Anpassungsmechanismus (drei einander ausschließende, intern stimmige Bilanzen auf fol. 3r); Füllstrich-Regel konditionalisiert (halluzinierter Füllstrich auf der Inventarseite in it01).

Betriebsregeln außerhalb des Prompts (Runner): ein Folio pro Request (Split als Default, Gewinn durch kleineres Sichtfeld); Few-Shot nur mit Raitbuch-Beispiel und nur, sobald die Mini-GT existiert, mit vorbildlich gefüllten uncertain/kind-Feldern; Kontrastverstärkung nur lokal auf messbar tintenarme Regionen, nie global.
