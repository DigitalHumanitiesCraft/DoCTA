# Tests

Zwei Playwright-Skripte, die die Site vor einem Push prüfen. Beide starten einen lokalen Server,
der das Repo bewusst unter dem Unterpfad `/DoCTA/` ausliefert, so wie GitHub Pages es tut. Pfadfehler,
die auf einer Domain-Wurzel unsichtbar blieben, fallen dadurch auf.

Beide Skripte lesen ihre Seitenliste aus den `*.html`-Dateien in `docs/`. Eine neue Seite ist damit
ohne Eingriff in die Tests abgedeckt, und eine gelöschte Seite hinterlässt keinen toten Eintrag.
Wo ein Dokument gebraucht wird, für die Deep Links und für den Review-Durchlauf, wählen die Skripte
es aus den Daten auf der Platte statt aus einer festen ID, sodass ein verändertes Korpus keine tote
Adresse hinterlässt.
Beide beenden sich mit Exit-Code 0 nur, wenn kein Befund vorliegt, sonst mit einem Wert ungleich
null. Damit taugen sie als Gate vor einem Push. Früher gaben sie ihre Befunde aus und endeten in
jedem Fall mit Erfolg, sodass jemand die Ausgabe lesen musste, um den Zustand der Site zu kennen.
Eine Ausnahme kippt den Exit-Code nicht: 404-Antworten unter `data/entities/` und `data/tei/`
gelten als erwartete Sonden, weil die meisten Dokumente keine Extraktion und nicht jedes eine
TEI-Datei haben; der Client fängt diese Fälle ab, und die Skripte melden sie nur im Report.

## Voraussetzung

Playwright ist nicht Teil des Projekts, die Site selbst kommt ohne Node-Abhängigkeiten aus.
Einmalig im Repo-Wurzelverzeichnis:

```
npm install playwright
npx playwright install chromium
```

`package.json` und `node_modules/` sind absichtlich gitignoriert. Sie gehören zur Prüfumgebung; das
ausgelieferte Artefakt bleibt davon frei.

## Ausführen

```
node tests/smoketest.mjs
node tests/interaction-test.mjs
```

## Was sie prüfen

**smoketest.mjs** lädt jede Seite der Site und meldet pro Seite Konsolenfehler, nicht abgefangene
Ausnahmen, fehlgeschlagene Netzwerk-Requests, HTTP-Status ab 400, interne Links, die auf keine Datei
zeigen, Bilder ohne `alt`-Attribut und die Ladezeit. Über die Seitenliste hinaus lädt er die Deep
Links, die eine Zitation adressiert, den Viewer mit `?view=tei` und mit `?page=<Nr>` sowie die
Exploration mit `?view=register`, `?view=network` und `?view=entities`. Zu jedem Deep Link ist
hinterlegt, was auf der Seite stehen muss, das TEI-Listing, eine Transkriptionszeile, der Tab samt
gefülltem Panel; beim Seiten-Deep-Link wird zusätzlich geprüft, dass der Pager auf der verlinkten
Seite steht. Den Exit-Code kippen Konsolenfehler samt Ausnahmen, tote interne Links, fehlgeschlagene
Requests außerhalb der erwarteten Sonden, ein nicht eingelöstes Deep-Link-Versprechen und eine Seite
ohne gerenderten Text. Fehlende `alt`-Attribute und die Ladezeit stehen nur im Report.

**interaction-test.mjs** klickt auf jeder Seite durch Schaltflächen, Auswahlfelder, Suchfelder und
Kontrollkästchen und sammelt dabei dieselben Fehlerarten. Navigation wird ausgespart oder rückgängig
gemacht, damit der Test auf der jeweiligen Seite bleibt; nur ein geänderter Pfad zählt dabei als
Navigation, weil der Viewer Dokument und Seite selbst in die URL schreibt. Er meldet außerdem, wie
sich die Textlänge der Seite pro Aktion ändert. Bleibt sie bei einem Filter unverändert, wirkt der
Filter womöglich nicht.

Die Bedienelemente werden vor jeder Aktion neu ermittelt statt einmal vorab eingesammelt, und der
Durchlauf geht in mehreren Runden über die Seite. Ein Klick kann seinen Container neu rendern, und
ein vorher genommener Handle zeigt danach in einen abgehängten Teilbaum; das stand früher als
übersprungene Aktion im Report und verdeckte, dass fast nichts geprüft wurde. Die Runden erreichen
zudem Elemente, die erst durch einen Klick entstehen. Wartezeiten hängen an einer Bedingung; der
Text der Seite gilt als fertig, sobald er sich nicht mehr ändert. Als Befund zählen neben Fehlern
auch eine Seite ohne gerenderten Text und ein Durchlauf, der mehr Elemente übersprungen als
geklickt hat.

Zwei benannte Abläufe kommen hinzu, die der allgemeine Durchlauf nicht prüfen kann:

- **Quellensuche der Startseite.** Ein echtes Signaturfragment des Korpus muss die Liste verengen,
  die Trefferzahl muss das melden, ein Begriff ohne Treffer muss den leeren Zustand zeigen, und das
  Leeren des Feldes muss die vollständige Liste wiederherstellen.
- **Review-Schleife des Viewers.** Review-Modus einschalten, Initialen setzen, eine Zeile zur
  Korrektur öffnen, durch den Klick auf die nächste Zeile committen, wobei derselbe Klick deren
  Editor öffnen muss (die Regressionssicherung gegen den nötigen Doppelklick), die beiden
  Entscheidungsschalter gegen den `aria-pressed`-Vertrag prüfen, insbesondere dass ein Klick auf
  Reviewed eine abgenommene Seite nicht zurückstuft, und den Export lesen. Der Export wird aus dem
  Blob gelesen, den die Seite ihrem Anker übergibt; es wird keine Datei geschrieben. Geprüft wird,
  dass das JSON parst und Version, Seiten, Status und die korrigierte Zeile trägt.

## Grenzen

Beide messen sichtbaren Text und Netzwerkverkehr. Was im Canvas gerendert wird, erfassen sie nicht;
im Viewer zeichnet OpenSeadragon das Faksimile dorthin. Der Netzwerk-Explorer läuft seit dem
28.08.2026 auf D3 und zeichnet SVG, seine Marken stehen damit im DOM. Im Browser zählt
`document.querySelectorAll('.net-node')` die gezeichneten Knoten, `.net-node.is-labelled` die
dauerhaft beschrifteten und `.net-linkg` die Kanten; so fällt eine Abweichung zwischen angezeigter
und beschrifteter Knotenzahl auf.
