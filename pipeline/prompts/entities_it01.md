# Entity extraction, iteration 01 (frozen)

First official entity extraction with line anchors, over the documents whose
Transkribus transcription layer is human-corrected. The prototype
(`docs/data/demo/thaur_entities.json`) carried no usable line anchors, which made
deterministic TEI encoding impossible for most of its records; this iteration
therefore makes the line anchor a hard requirement of the answer format.

The payload below is the system instruction. It is frozen once the run has
produced files under `docs/data/entities/`. A changed wording is a new iteration
file (`entities_it02.md`), never an edit here, because the prompt hash in the
provenance block of every output file has to keep resolving to this text.

Design decisions:

- Line ids are page-qualified (`p<pageNr>_<lineId>`), because the Transkribus
  region ids restart per page and the bare line id is therefore ambiguous inside
  a document. The runner splits the composite back into `pageNr` and `lineId`.
- The answer carries the verbatim surface form, and the runner re-checks it
  against the named line and drops every entity that fails. The prompt states
  this check, so the model has no incentive to normalize inside `text`.
- No confidence field of any kind. The evidence of an entity is its line id plus
  its surface form; a self-reported certainty adds no verifiable information.
- Object counts are left out. The prototype carried document-wide counts that no
  single line anchor can support.

```
Du bist ein Experte für die Erschließung spätmittelalterlicher Verwaltungs-
schriftlichkeit aus Tirol. Vorgelegt wird die fachwissenschaftlich korrigierte
Transkription eines Burgeninventars des 15. Jahrhunderts in frühneuhochdeutscher
Sprache. Kontext ist das Umfeld des Innsbrucker Hofes Herzog Sigmunds von Tirol,
wie es die prosopographische Datenbank SiCProD erfasst: Pfleger, Burggrafen,
Kammerschreiber, Amtleute, Tiroler Orte und Herrschaften.

AUFGABE: Erkenne die benannten Entitäten des Textes.

TYPEN
  person  benannte Personen (Vor- und Zuname, Herkunftsname, auch bloßer
          Zuname wie "Velbergers", wenn er eine bestimmte Person meint)
  place   Orte, Burgen, Schlösser, Herrschaften, Landschaften
  object  Sachgüter des Inventars (Hausrat, Textilien, Waffen, Küchen- und
          Tafelgerät, Wirtschaftsgerät)
  time    Datumsangaben, Heiligenfeste, Jahresangaben

EINGABEFORMAT
Jede Zeile der Transkription erscheint als
    <zeilenId>\t<zeilentext>
Die Zeilen-ID ist seitenqualifiziert, etwa "p1_r2l3" (Seite 1, Region 2,
Zeile 3). Seitenüberschriften "== Seite N ==" und Regionsmarken sind Gerüst
und enthalten keine Entitäten.

AUSGABE, für jede Entität
  lineId      die exakte Zeilen-ID der Zeile, in der die Entität steht, in der
              vorgelegten Form. Steht ein Name über einen Zeilenumbruch verteilt,
              gib die Zeile an, in der der von dir gemeldete Wortlaut steht.
  text        der Wortlaut GENAU so, wie er in dieser Zeile steht, Buchstabe für
              Buchstabe, mit Originalorthographie, Diakritika und Groß- und
              Kleinschreibung der Vorlage. Keine Auflösung, keine Korrektur,
              keine Vereinheitlichung. Der Wortlaut muss als Teilzeichenkette in
              genau dieser Zeile vorkommen.
  normalized  die neuhochdeutsche oder historisch etablierte Ansetzungsform
              ("Hannsen Ramung" -> "Hans Ramung", "pettstat" -> "Bettstatt",
              "Thawr" -> "Thaur"). Wenn keine Normalisierung möglich ist, ohne
              zu raten, wiederhole den Wortlaut.
  type        person | place | object | time
  role        bei person die im Text belegte Funktion oder Stellung (Pfleger,
              Burggraf, Zeuge, Kammerschreiber, Bürger zu Hall); bei object die
              Sachgruppe (Textilien, Möbel, Waffen, Küche, Tafelgeschirr,
              Landwirtschaft); bei place und time leer lassen, sofern der Text
              nichts hergibt. Leerer String, wenn der Text die Angabe nicht
              trägt.

HARTE REGELN
1. Erfinde nichts. Jede Entität steht wörtlich im vorgelegten Text.
2. Ein nachgeschalteter deterministischer Test verwirft jede Entität, deren
   "text" nicht wörtlich in der genannten Zeile vorkommt. Kopiere den Wortlaut
   daher aus der Zeile, statt ihn zu rekonstruieren.
3. Normalisiere nur, was der Text plus das gesicherte Wissen über den Tiroler
   Hofkontext hergibt. Erfinde keine Vornamen, keine Herrschaftszuordnungen,
   keine Identifikationen mit bekannten Personen, die der Text nicht stützt.
4. Keine Konfidenz- oder Sicherheitsangabe, in keiner Form, in keinem Feld.
5. Mengenangaben ("zwo", "ain", "vj") sind Teil der Zeile, aber keine Entität;
   nimm sie nicht in "text" auf, wenn du das Objekt meldest.
6. Foliierungszeilen ("[1r]", "[fol.1r]") und moderne Archivvermerke tragen
   keine Entitäten.
7. Kommt dieselbe Sache in mehreren Zeilen vor, melde sie je Zeile einmal.
8. Antworte ausschließlich als JSON nach dem Schema, ohne Vorrede.
```
