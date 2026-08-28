# Tests

Zwei Playwright-Skripte, die die Site vor einem Push prüfen. Beide starten einen lokalen Server,
der das Repo bewusst unter dem Unterpfad `/DoCTA/` ausliefert, so wie GitHub Pages es tut. Pfadfehler,
die auf einer Domain-Wurzel unsichtbar blieben, fallen dadurch auf.

Beide Skripte lesen ihre Seitenliste aus den `*.html`-Dateien in `docs/`. Eine neue Seite ist damit
ohne Eingriff in die Tests abgedeckt, und eine gelöschte Seite hinterlässt keinen toten Eintrag.
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
zeigen, Bilder ohne `alt`-Attribut und die Ladezeit. Den Exit-Code kippen davon Konsolenfehler samt
Ausnahmen, tote interne Links und fehlgeschlagene Requests außerhalb der erwarteten Sonden. Fehlende
`alt`-Attribute und die Ladezeit stehen nur im Report.

**interaction-test.mjs** klickt auf jeder Seite durch Schaltflächen, Auswahlfelder, Suchfelder und
Kontrollkästchen und sammelt dabei dieselben Fehlerarten. Navigation wird ausgespart oder rückgängig
gemacht, damit der Test auf der jeweiligen Seite bleibt. Er meldet außerdem, wie sich die Textlänge
der Seite pro Aktion ändert. Bleibt sie bei einem Filter unverändert, wirkt der Filter womöglich
nicht.

## Grenzen

Beide messen sichtbaren Text und Netzwerkverkehr. Was im Canvas gerendert wird, erfassen sie nicht;
im Viewer zeichnet OpenSeadragon das Faksimile dorthin. Der Netzwerk-Explorer läuft seit dem
28.08.2026 auf D3 und zeichnet SVG, seine Marken stehen damit im DOM. Im Browser zählt
`document.querySelectorAll('.net-node')` die gezeichneten Knoten, `.net-node.is-labelled` die
dauerhaft beschrifteten und `.net-linkg` die Kanten; so fällt eine Abweichung zwischen angezeigter
und beschrifteter Knotenzahl auf.
