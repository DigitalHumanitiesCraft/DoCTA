# Tests

Zwei Playwright-Skripte, die den Prototyp vor einem Push prüfen. Beide starten einen lokalen Server,
der das Repo bewusst unter dem Unterpfad `/DoCTA/` ausliefert, so wie GitHub Pages es tut. Pfadfehler,
die auf einer Domain-Wurzel unsichtbar blieben, fallen dadurch auf.

## Voraussetzung

Playwright ist nicht Teil des Projekts, der Prototyp selbst kommt ohne Node-Abhängigkeiten aus.
Einmalig im Repo-Wurzelverzeichnis:

```
npm install playwright
npx playwright install chromium
```

`package.json` und `node_modules/` sind absichtlich gitignoriert: sie gehören zum Testen, nicht zum
Artefakt.

## Ausführen

```
node tests/smoketest.mjs
node tests/interaction-test.mjs
```

## Was sie prüfen

**smoketest.mjs** lädt alle acht Seiten und meldet pro Seite: Konsolenfehler, nicht abgefangene
Ausnahmen, fehlgeschlagene Netzwerk-Requests, HTTP-Status ab 400, interne Links, die auf keine Datei
zeigen, Bilder ohne `alt`-Attribut und die Ladezeit. Erwartetes Ergebnis: überall null.

**interaction-test.mjs** klickt auf jeder Seite durch Schaltflächen, Auswahlfelder, Suchfelder und
Kontrollkästchen und sammelt dabei dieselben Fehlerarten. Navigation wird ausgespart oder rückgängig
gemacht, damit der Test auf der jeweiligen Seite bleibt. Er meldet außerdem, wie sich die Textlänge
der Seite pro Aktion ändert: bleibt sie bei einem Filter unverändert, wirkt der Filter womöglich
nicht.

## Grenzen

Beide messen sichtbaren Text und Netzwerkverkehr. Was im Canvas gerendert wird (Cytoscape im
Netzwerk-Explorer, OpenSeadragon im Viewer), erfassen sie nicht. Für den Graphen lässt sich die
Cytoscape-Instanz im Browser über die Container-Eigenschaft `_cyreg.cy` auslesen und dann `nodes()`
und `edges()` zählen; so wurde die Abweichung zwischen angezeigter und beschrifteter Knotenzahl
gefunden.
