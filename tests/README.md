# Tests

Der Anleitungsdurchlauf `guide-walkthrough-test.mjs` kann über die Umgebungsvariable `DOCTA_TEST_PYTHON` den absoluten Pfad einer gesondert eingerichteten Python-Umgebung verwenden. Damit lässt sich der dokumentierte Installationsweg mit `venv` und `pip install -r editor-requirements.txt` gegen dieselben isolierten Bearbeitungsprüfungen testen. Ohne diese Variable nutzt er wie bisher die Projektumgebung.

Die allgemeinen Playwright-Prüfungen `smoketest.mjs` und `interaction-test.mjs` starten einen lokalen Server,
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
node tests/viewer-ui-test.mjs
node tests/registry-editor-test.mjs
node tests/sources-ui-test.mjs
node tests/guide-walkthrough-test.mjs
```

## Was sie prüfen


Die Registerprüfung umfasst die Kategorien Person, Begriff, Ort und Datumsangabe, Rechtsklick und Tastaturzugang sowie die Register-Seitenleiste. Auswahl, Fundstellenbearbeitung und neue Registereinträge müssen in demselben geöffneten Feld bleiben. KI-Vorschläge werden weder geladen noch angezeigt. Die Indexansicht zeigt ausschließlich gespeicherte editorische Einträge mit ihren Fundstellen. Eine reine Einsicht erzeugt keinen Entwurf. Datumsprüfungen unterscheiden exakte Angaben und unsichere Zeiträume. Die schmale Ansicht bei vergrößerter Darstellung muss tatsächliche Eingaben und Speichern ermöglichen.

`registry-editor-test.mjs` startet den echten Python-Speicherdienst über einer isolierten Kopie vorhandener Quelldaten. Geprüft werden Personen und Begriffe, Namensvarianten, gleichnamige getrennte Identitäten, Auswahl und Änderung von Fundstellen, Änderungshistorie, veraltete Textanker sowie Tastaturbedienung und schmale Ansichten. Die Forschungsdaten im Repository werden nicht bearbeitet. Benötigt wird die mit `uv sync --locked` eingerichtete Projektumgebung.

`sources-ui-test.mjs` prüft die Quellenübersicht mit den vorhandenen Katalogdaten, Verfügbarkeit und Herkunft der Transkriptionen sowie den Einstieg in bekannte erste Bilder ohne Transkription. Responsive Darstellung und Navigation gehören zum selben Test.

Die Python-Prüfungen zur TEI-Baseline erzeugen ihren Ausgangsstand aus den vorhandenen Quellen in einem temporären Verzeichnis. Persönliche Korrekturen im Arbeitsverzeichnis dürfen die erwartete ursprüngliche Provenienz nicht verändern.

`viewer-ui-test.mjs` prüft Quellenkopf, Dialogbedienung, Bildpassung und den vereinfachten Bearbeitungsablauf mit einer vorhandenen Transkription. Sein Speicherdienst läuft ausschließlich im Arbeitsspeicher. Die Prüfung verändert keine Forschungsdaten.

Die frühere Schlagwortoberfläche ist entfernt. Die Viewer-Prüfung sichert ihre Abwesenheit. Die Python-Tests decken weiterhin den kompatiblen Speicher und die HTTP-Endpunkte für erhaltene Altdaten ab.

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
- Der Korrekturdurchgang öffnet Bearbeiten, setzt Initialen und korrigiert eine Zeile. Der Klick auf die nächste Zeile muss die Änderung übernehmen und deren Eingabefeld öffnen. Der Test prüft den sichtbaren Entwurfszustand, das Fehlen von Freigabe- und Zeitmessungsfunktionen sowie den JSON-Export mit der korrigierten Zeile, einer leeren Seitenentscheidung und ohne Aufwandserfassung. Der Export wird im Arbeitsspeicher gelesen und schreibt keine Forschungsdatei.

`guide-walkthrough-test.mjs` folgt dem Personenbeispiel der Anleitung im echten Python-Editor mit isolierten Datenkopien. Er prüft Speichern, Index und Rücksprung, Änderung und Entfernung der Fundstelle sowie Textkorrektur und Wiederherstellung. Die Textauswahl wird im Browser per DOM gesetzt. Die Prüfung ersetzt keinen manuellen Nutzertest oder eine Betriebssysteminstallation. Screenshots liegen unter `output/guide-check/`.

## Grenzen

Beide messen sichtbaren Text und Netzwerkverkehr. Was im Canvas gerendert wird, erfassen sie nicht;
im Viewer zeichnet OpenSeadragon das Faksimile dorthin. Der Netzwerk-Explorer läuft seit dem
28.08.2026 auf D3 und zeichnet SVG, seine Marken stehen damit im DOM. Im Browser zählt
`document.querySelectorAll('.net-node')` die gezeichneten Knoten, `.net-node.is-labelled` die
dauerhaft beschrifteten und `.net-linkg` die Kanten; so fällt eine Abweichung zwischen angezeigter
und beschrifteter Knotenzahl auf.
