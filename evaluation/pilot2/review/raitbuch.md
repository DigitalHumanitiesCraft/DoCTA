# Fachliche Durchsicht der Raitbuch-2-Transkriptionen aus Pilot 2

Gegenstand sind fünf Doppelseiten des Raitbuchs 2 (docId 12514730) in der Konfiguration it02, jeweils in zwei Wiederholungen. Vier Aufnahmen sind Ausreißer der Pilot-2-Auswertung (p025, p029, p030, p041), die fünfte (p038) ist als Kontrolle gewählt, weil sie mit einer Wortkonsistenz von 0.722 den besten Wert der Raitbuch-Kohorte hält. Alle zehn Bildhälften wurden am zwischengespeicherten IIIF-Digitalisat gelesen, jede Doppelseite misst 3780 × 2644 Pixel, jede Hälfte nach dem Schnitt des Runners 1890 × 2644 Pixel. Kein Bild musste nachgeladen werden.

Eine Korrektur zur Aufgabenstellung vorweg. Die dort genannten Werte 0.107 für p030 und 0.235 für p041 sind nicht die Wort-, sondern die Zahlenkonsistenzen; die Wortkonsistenzen liegen bei 0.5 und 0.713. Der Befund bleibt bestehen und wird durch die Korrektur sogar schärfer, denn die Divergenz sitzt auf beiden Seiten fast ausschließlich in den Beträgen.

## Was auf p029 wirklich geschehen ist

Die Vermutung, r2 sei auf dem recto von p029 früh abgebrochen (19 gegen 1 Zeile), trifft nicht zu. Das Bild zeigt ein Blatt, das außer der Foliierung „29“ in der oberen rechten Ecke keine Tinte trägt. Was auf der Aufnahme wie ein voller Text aussieht, ist Durchscheinen des dahinterliegenden Blattes fol. 30r. Der Nachweis ist eindeutig, denn die durchscheinende Rubrik lautet „Hanns Elsspambm zu Botzn“ und ist wortgleich die Rubrik des recto von p030, ebenso die zweite Rubrik „Ausgeben“.

Damit kehrt sich die Bewertung um. r2 gibt mit der einen Zeile „29“ genau das wieder, was auf dem Blatt steht. r1 erzeugt eine Phantomseite: neunzehn Zeilen, zwei aus dem Durchscheinen abgeschriebene Rubriken, dabei der erfundene Name „Hannss Apponntner zu Bozen“, und siebzehn Zeilen, die als Text das Literal „[...]“ tragen. Die Zeilendivergenz 26 gegen 9 ist eine Halluzination in r1. Beide Wiederholungen versäumen es außerdem, `empty` zu setzen.

Auf dem verso derselben Aufnahme steht der umgekehrte Fall. Der Textspiegel ist durch einen langen diagonalen Strich getilgt, wie es in Rechnungsbüchern die abgeschlossene Post kennzeichnet. r2 erkennt die Tilgung und markiert alle acht Zeilen mit `~~...~~`. r1 übergeht sie. Die Markierung von r2 ist inhaltlich richtig und formal ein Fremdkörper, weil das Schema kein Feld für Tilgung kennt und die Markdown-Zeichen deshalb in den Transkriptionstext geraten und die Wortkonsistenz drücken.

## Die Leermeldungen halten stand

Die beiden gemeldeten leeren verso, p030 und p041, sind am Bild tatsächlich tintenfrei. Beide zeigen kräftiges, seitenverkehrtes Durchscheinen, das beide Wiederholungen korrekt ignorieren. Der gefährliche Fall ist der umgekehrte, die nicht gemeldete Leere von p029 recto. Das Modell erkennt eine leere Seite dann zuverlässig, wenn das Durchscheinen spiegelverkehrt ist, und scheitert dann, wenn es rechtsläufig lesbar erscheint, weil das durchscheinende Blatt zwei Lagen tiefer liegt.

## Beträge

Geprüft wurde jeder auf der jeweiligen Hälfte sichtbare Betrag, insgesamt 27 auf acht nicht leeren Hälften. Die geforderte Zahl von zehn Beträgen je Hälfte ist auf diesen Seiten nicht erreichbar, weil keine Hälfte mehr als sechs Beträge trägt; die Buchführung arbeitet hier mit wenigen großen Posten und einer Blocksumme statt mit langen Postenlisten.

Der schwerwiegendste Fehler betrifft das hochgestellte Hundertzeichen. Auf p025 recto steht „viij^C lx Rh gld“, also 860 rheinische Gulden. r1 liest „viij lb x ß gld“, r2 liest „viij tt Rh gld“. Der Betrag verliert damit zwei Größenordnungen, und zwar in beiden Wiederholungen, sodass die Selbstkonsistenz den Fehler nicht anzeigt. Steht dasselbe Zeichen auf der Grundlinie statt hochgestellt, wie auf dem verso derselben Aufnahme, wird es zuverlässig als „C“ erkannt.

Der zweite systematische Fehler ist die Mark-Kürzung, ein m mit Kürzungsstrich. Auf p041 recto steht zweimal „lxxx m“ und „lxx m“; r2 macht daraus „lxxx iiij“ und „lxx iiij“, r1 zusätzlich „lxxxiiij lb“. Die Einheit verschwindet und wandert als römische Ziffer in die Zahl. Auf p038 recto trifft es die Kopfsumme der Seite, „xxxviij m viij lb ij d“ wird in r1 zu „xxviij lb viij ß vj d“ und in r2 zu „xxviij lb iiij ß vj d“. Gerade die Kontrollseite mit der höchsten Selbstkonsistenz zeigt damit, dass Übereinstimmung zwischen zwei Läufen keine Richtigkeit verbürgt; beide Läufe irren gleichsinnig.

Ein brauchbarer unabhängiger Prüfgriff liegt in der Arithmetik der Blöcke. Auf p025 verso addieren sich die drei Posten von r2 (300, 700, 694) exakt zu dessen Summenzeile (1694), während sich die Zahlen von r1 zu nichts addieren; auf p030 recto geht die Rechnung von r1 auf (1220 + 67 = 1287), die von r2 nicht. In beiden Fällen weist die Probe genau den Lauf als richtig aus, den auch die Bildlektüre bestätigt.

## Erscheinungen des Rechnungsbuchs

Spalten führen diese Seiten nicht. Die Beträge stehen rechts eingerückt in eigener Zeile oder am Zeilenende, in der Regel hinter einem langen Leerlaufstrich. Dieser Strich gerät uneinheitlich als „——“ in den Transkriptionstext, mal gesetzt, mal weggelassen, und kostet Konsistenz ohne inhaltlichen Gewinn.

Dittographie über Postengrenzen hinweg wurde nicht beobachtet. An ihre Stelle tritt eine andere Art von Wiederholung, die Platzhalterkette in r1 auf p029 recto.

Marginale Summen kommen in der Kohorte nicht vor. Das einzige marginale Element ist die Item-Initiale am linken Rand, und genau sie erzeugt die Zeilenzahldivergenz zwischen den Wiederholungen. Auf p025 verso setzt r2 drei eigene Zeilen vom Typ `marginal` und r1 keine, was die im Summary sichtbare Dreizeilendivergenz vollständig erklärt; auf p038 recto verhält es sich spiegelbildlich, dort setzt r1 sie und r2 nicht. Substanz geht dabei nicht verloren, die Metrik straft eine unentschiedene Konvention.

Die Tilgungsstriche schließlich werden zufällig erkannt. Auf p029 verso markiert r2 sie, auf p038 verso und p041 recto liegen formgleiche Striche, die keine der vier Wiederholungen erwähnt.

## Warum p030 und p041 einbrechen

Auf p030 recto ist die Abdeckung tadellos, beide Wiederholungen liefern 24 Zeilen mit identischen Zeilengrenzen, und die Wortkonsistenz von 0.5 stammt aus dem unteren Drittel. Dort wechselt der Duktus in eine schnellere, stärker gekürzte Kursive mit dichten Ziffernclustern. Die Seite verbucht einen Venedig-Einkauf in Dukaten. r1 hält das Währungssystem durch und rechnet richtig, r2 gibt es auf und setzt „dut“ statt „duc“, lb statt ß und d, und erfindet Buchstabenfolgen wie „Zendel Diminuter Balter kanss vergy weltmasir“. Sichtbare Ursache ist der Duktus des Blocks; der Ausfall geht darüber hinaus, weil ein einzelner Lauf die Währung des gesamten Geschäfts aufgibt.

Auf p041 recto ist der Duktus ruhig und die Wortkonsistenz mit 0.713 gut. Die Zahlenkonsistenz von 0.235 hängt an einem einzigen Zeichen, der Mark-Kürzung in Endstellung, und an dem Zeichencluster ß/d/hl dahinter. Weder Anlage noch Hand sind hier die Ursache.

## Urteil je Aufnahme

| Aufnahme | Urteil | besserer Lauf | wichtigster Korrekturbedarf |
|---|---|---|---|
| p025 | needs-targeted-correction | r2 | alle Betragszeilen des recto, hochgestelltes Hundertzeichen durchgängig verloren |
| p029 | needs-targeted-correction | r2 | r1 für das recto verwerfen, Seite als leer mit Foliierung führen |
| p030 | needs-targeted-correction | r1 | Ausgabenblock ab der Registerzeile aus r1 übernehmen, r2 dort unbrauchbar |
| p038 (Kontrolle) | needs-targeted-correction | r2 | Kopf- und Empfangssumme des recto neu lesen, Mark-Kürzung als Pfund gelesen |
| p041 | needs-targeted-correction | r2 | die vier Beträge neu lesen, Mark-Kürzung am Zeilenende als Zahl verarbeitet |

Keine Aufnahme erreicht „usable-as-draft“, obwohl die Textschicht auf p025, p030, p038 und p041 durchweg brauchbar ist. Für ein Rechnungsbuch ist der Betrag die Aussage, und auf jeder der fünf Aufnahmen ist mindestens eine tragende Summe in beiden Wiederholungen falsch. Als Vorlage für eine fachliche Korrektur taugen die Transkripte; als Datengrundlage für eine Auswertung der Beträge taugen sie ohne Nachlese nicht. Unbrauchbar im engeren Sinn ist genau eine Hälfte, das recto von p029 in r1.

## Drei Lehren für Prompt und Pipeline

**Durchscheinen und leere Seiten als eigenen Fall führen.** Der Prompt muss verbieten, durchscheinende Schrift zu transkribieren, und den Leerfall positiv definieren, also `empty: true` bei einer Seite, die außer Foliierung und Randvermerk keine Tinte trägt. Im Schema ist `empty` derzeit nicht in `required`, und tatsächlich lassen sieben der zehn geprüften Seitenobjekte das Feld auf null; es gehört in die Pflichtfelder, damit die Leerentscheidung erzwungen und auswertbar wird. Ein zweiter Griff kommt aus der Bildvorbereitung: der Schnitt bei `width//2` legt die Zeilenenden des verso, wo alle Beträge stehen, bis auf wenige Pixel an die Schnittkante und in den dunkelsten Teil des Bundschattens; auf p038 verso endet die Summenzeile etwa sieben Pixel vor der Kante. Der Schnitt sollte am erkannten Bund mit kleinem Überlappungsrand erfolgen.

**Platzhalter verbieten und die Abdeckung prüfbar machen.** Der Lauf r1 hat auf p029 recto siebzehn Zeilen mit dem Literal „[...]“ gefüllt und auf p038 verso zweimal mitten in der Betragszeile abgebrochen. Die Auswertung zählt diese Zeilen als transkribiert, sodass Zeilenzahl und Konsistenzwerte durch Nichtinhalt aufgebläht werden. Der Prompt sollte jeden Platzhalter im Feld `text` untersagen und dafür ein Feld `illegible` je Zeile anbieten; der Evaluationsschritt sollte solche Zeilen aus Zeilenzahl und Konsistenz herausrechnen. Dazu gehört ein Feld für die Tilgung, damit die inhaltlich richtige Beobachtung von r2 auf p029 nicht als Markdown im Transkriptionstext landet.

**Die Notation des Rechnungsbuchs ins Amount-Objekt holen und arithmetisch prüfen.** Die drei Zeichen, an denen die Kohorte scheitert, sind das hochgestellte Hundertzeichen, die Mark-Kürzung und die Kette ß/d/hl am Zeilenende. Der Prompt sollte das Vokabular als geschlossene Liste führen (Multiplikator C und m, Einheiten Rh gld, duc, m, lb, ß, d, hl) und lateinische Ziffern sowie Einzelbuchstaben im Feld `numeral` ausschließen; heute erscheinen dort „4“, „t“, „w“ und „tt“. Darauf setzt eine Nachprüfung auf, die die Posten eines Blocks gegen dessen Summenzeile rechnet. Diese Probe trennt in der Kohorte sauber: Auf p025 verso addieren sich die Posten von r2 exakt zu dessen Summe und die von r1 zu nichts, auf p030 recto geht die Rechnung von r1 auf und die von r2 nicht, und in beiden Fällen deckt sich das Ergebnis mit der Bildlektüre. Sie ist zugleich das einzige Instrument im bisherigen Aufbau, das den gefährlichsten Fall erfasst, den gleichsinnigen Irrtum beider Wiederholungen, wie ihn die Kontrollseite p038 zeigt.
