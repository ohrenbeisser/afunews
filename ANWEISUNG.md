# Arbeitsanweisung für den Wochen-Agenten

Diese Datei ist die feste Anweisung für jeden wöchentlichen Lauf. Jeder Lauf beginnt ohne Vorwissen; alles Nötige steht hier, in `quellen.md` und in `schema.md`.

## Auftrag

Der Lauf startet sonntags früh. Sammle die Amateurfunk-Nachrichten der laufenden Kalenderwoche (ISO 8601, Montag 00:00 bis zum Laufzeitpunkt), fasse sie auf Deutsch zusammen und lege sie als JSON in diesem Repository ab.

## Normaler Lauf oder Testlauf

Bestimme zuerst das Datum in der Zeitzone Europe/Berlin.

- **Sonntag:** normaler Lauf. Gearbeitet und gepusht wird auf `main`.
- **Jeder andere Wochentag:** Testlauf. Lege vom aktuellen `main` einen Branch `testlauf` an (ein vorhandener wird überschrieben), arbeite dort und pushe mit `git push --force origin testlauf`. `main` bleibt unverändert. Alles andere läuft genau wie beim normalen Lauf.

## Ablauf

1. **Woche bestimmen.** Bearbeitet wird die Kalenderwoche, in die das Laufdatum fällt. `zeitraum.von` ist deren Montag, `zeitraum.bis` das Laufdatum. Gibt es `data/JJJJ/JJJJ-Www.json` auf dem Arbeitsbranch schon, brich ab und melde das, statt sie zu überschreiben; die Rohdaten bleiben dann unberührt.
2. **Bekannte Links laden.** Lies die Wochendateien der letzten vier Wochen und sammle alle `quelle.url`. Was dort schon steht, wird nicht noch einmal aufgenommen, auch nicht als Termin.
3. **Rohdaten lesen.** Rufe keine Quellenseiten selbst ab. Die GitHub Action „Quellen sammeln“ (Skript `scripts/quellen_sammeln.py`, Quellenliste `quellen.json`) legt sonntags früh (geplant 01:17 UTC, Ersatz 02:47 UTC) die Datei `data/rohdaten/JJJJ-Www.json` der Woche an. Lies sie vollständig. Sie enthält je Quelle `status` (`ok`, `leer`, `fehler`) und `eintraege` mit `titel`, `url`, `datum`, `datum_herkunft` und `auszug`. Dazu gilt:
   - Fehlt die Datei oder ist `abgerufen` älter als zwei Tage, ist der geplante Lauf der Action vermutlich ausgefallen oder verspätet (GitHub verzögert Zeitpläne). Starte dann beim normalen Lauf selbst den fehlenden Workflow auf `main` per `workflow_dispatch` (GitHub-MCP-Tool `actions_run_trigger`, Methode `run_workflow`): „Quellen sammeln“ (`quellen.yml`), wenn die Rohdatei fehlt oder alt ist, „YouTube-Feeds abrufen“ (`youtube.yml`), wenn `data/youtube.json` fehlt oder älter als zwei Tage ist. Den eigenen Lauf erkennst du über `actions_list` (`list_workflow_runs`, Filter `event: workflow_dispatch`) an der jüngsten Run-ID; fertig ist er bei `status: completed`. Warte höchstens 10 Minuten (Abfrage alle 60 Sekunden), hole `main` mit `git pull --rebase origin main` neu und lies die Datei. Schlägt ein Workflow fehl, lies sein Log. Ist `data/rohdaten/` auch danach nicht aktuell, brich ab und melde das per Benachrichtigung mit der Fehlerursache. Schlägt nur „YouTube-Feeds abrufen“ fehl, arbeite ohne neue Videos weiter und vermerke das im Bericht.
   - Beim Testlauf an anderen Wochentagen darf die Datei älter sein; dann nur das Alter im Bericht nennen.
   - Quellen mit Status `fehler` oder `leer` und die `hinweise` der Quellen kommen in den Abschlussbericht.
   - `datum_herkunft` `meta` und `feed` ist verlässlich, `text` eine Schätzung, `unbekannt` heißt: Datum nicht ermittelt. Im Zweifel `veroeffentlicht: null` setzen.
   - Quellen mit `nur_hinweis: true` (TWIAR) dienen nur als Hinweisgeber; verlinkt wird die Originalquelle, die der Auszug nennt. Findest du sie nicht, lass die Meldung weg.
   - Auszüge sind gekürzt. Reicht ein Auszug für eine Meldung nicht, darfst du einzelne Seiten mit WebFetch nachladen. Scheitert der Abruf, arbeite nur mit dem Auszug oder lass die Meldung weg.
   - Der Deutschland-Rundspruch der Woche (DARC, Titel enthält „Rundspruch“) steht mit langem Auszug in der Datei und bündelt viele Meldungen. Die Conteste der *kommenden* Woche stehen in der DARC-Meldung „Aktuelle Conteste KW NN/JJJJ“, falls sie schon erschienen ist. DXpeditionen liefern NG3K und DX-World.
   - Videos: nicht abrufen, sondern `data/youtube.json` lesen. Die Datei legt die GitHub Action „YouTube-Feeds abrufen“ sonntags vor dem Lauf an (geplant 01:07 UTC, Ersatz 02:37 UTC; Skript `scripts/youtube_feeds.py`). Ist `abgerufen` älter als zwei Tage, fehlt die Datei oder steht bei einem Kanal `ok: false`, das im Bericht vermerken. Beim Testlauf an anderen Wochentagen kann die Datei älter sein; dann nur Videos aus dem Zeitraum der Woche nehmen und das Alter im Bericht nennen. Auch beim normalen Lauf zählen nur Videos, die zwischen `zeitraum.von` und `zeitraum.bis` der Woche veröffentlicht wurden; die Datei enthält mehr, weil sie die letzten acht Tage abdeckt.
   - Quellen mit Status „gesperrt“ oder „unbrauchbar“ in `quellen.md` sind nicht in der Rohdatei und bleiben außen vor.
4. **Auswählen.** Aufnehmen, was im Zeitraum veröffentlicht wurde und für Funkamateure in Deutschland von Belang ist. Weglassen: Werbung, Rabattaktionen, Produktankündigungen ohne Neuigkeitswert, Nachrufe auf unbekannte Personen außerhalb DL, reine Meinungsbeiträge.
5. **Doppelungen zusammenführen.** Berichten mehrere Quellen über dasselbe, wird es eine Meldung. Verlinkt wird die Originalquelle, also etwa die Behörde oder der Veranstalter, nicht der Sammeldienst. Jede `quelle.url` darf in einer Woche nur einmal vorkommen.
6. **Schreiben.** Titel und Zusammenfassung nach den Regeln unten.
7. **Termine.** Ereignisse der *kommenden* Woche als `typ: termin` aufnehmen. Nur die wichtigsten: große Conteste, DXpeditionen auf gesuchte Gebiete, ISS-Kontakte mit Schulen in DACH. Regionale Termine aus Sachsen und dem Vogtland werden immer aufgenommen, auch wenn die Ankündigung schon älter ist; dann als `typ: artikel` mit Rubrik `regional`.
8. **Kopf schreiben.** `ueberblick` mit drei bis fünf Sätzen zu den wichtigsten Themen; `ausbreitung` mit einer kurzen Notiz, wenn es Daten gibt (z. B. FunkWX des DARC-HF-Referats).
9. **Speichern.** Zeitstempel (`erstellt`, `aktualisiert`) nicht schätzen, sondern mit `TZ=Europe/Berlin date +%Y-%m-%dT%H:%M:%S%:z` bestimmen. Wochendatei schreiben, `data/index.json` aktualisieren (`aktualisiert`, neuer Eintrag in `wochen`, absteigend sortiert).
10. **Prüfen.** `python3 scripts/pruefen.py` ausführen. Fehler beheben, bis die Prüfung ohne Fehler durchläuft.
    Danach die Rohdaten der Woche entfernen: `git rm -r data/rohdaten`. Sie werden nur für diesen Lauf gebraucht und sollen das Repository nicht aufblähen. Die Löschung gehört in denselben Commit wie die Wochendatei.
11. **Committen.** Autor `ohrenbeisser <ohrenbeisser@gmail.com>`. Commit-Nachricht: `KW 42/2026: 18 Meldungen`, beim Testlauf mit dem Zusatz `(Testlauf)`. Pushen wie oben beschrieben. Der Commit enthält die Wochendatei, `data/index.json` und die Löschung von `data/rohdaten/`.
12. **Bericht.** Kurz melden: Laufart, Woche, Anzahl Meldungen je Rubrik, nicht erreichbare Quellen, Auffälligkeiten.

## Umfang

- Ziel: 30 bis 35 Meldungen pro Woche. FUNKAMATEUR ist nach dem DARC die wichtigste Quelle: Alle Einträge der Rohdaten mit Bezug zum Amateurfunk prüfen und gut verwertbare aufnehmen.
- Quellenmischung: Höchstens ein Drittel der Meldungen aus derselben Quelle. DARC-Nachrichten, Deutschland-Rundspruch, FunkWX und DARC-Distrikte zählen dabei zusammen als DARC; die Pflichtmeldungen aus Sachsen und dem Vogtland dürfen die Grenze überschreiten. Wird die Grenze sonst überschritten, zuerst weitere Zusatzquellen abarbeiten und Randmeldungen der stärksten Quelle weglassen.
- Höchstens 3 Meldungen mit `wichtigkeit: 1`.
- Höchstens 5 Videos.
- Lieber weniger und gesichert als viele und fragwürdig.

## Schreibregeln

- Alles auf Deutsch, auch wenn die Quelle englisch ist.
- Titel: sachlich, eigene Worte, keine Übernahme der Originalüberschrift, kein Ausrufezeichen, keine Clickbait-Fragen.
- Zusammenfassung: 2 bis 3 Sätze in eigenen Worten. Keine wörtlichen Zitate über 15 Wörter, keine Absätze aus dem Original. Was passiert ist, wer betroffen ist, ab wann es gilt.
- Keine Wertungen, keine Werbesprache, keine Floskeln wie „spannend“ oder „ein Meilenstein“.
- Rufzeichen in Großbuchstaben, Frequenzen mit Einheit (`7,074 MHz`), Bänder als `40m`, Zeiten in UTC.
- Bei Videos steht am Anfang der Zusammenfassung „Laut Videobeschreibung …“.
- Videos: Aufnehmen nur, was laut Titel und Beschreibung einen Nachrichten- oder Sachwert hat (Berichte, Anleitungen, Tests, Veranstaltungen). Keine Shorts (`ist_short: true`), keine Livestream-Ankündigungen ohne Inhalt, keine reinen Werbe- oder Unboxing-Videos. `quelle.url` ist die Video-URL, `quelle.name` der Kanalname, `video.video_id` aus der Datei, `video.dauer` ist `null`, weil der Feed keine Länge liefert, `video.nur_beschreibung` ist `true`. Ein Video gilt bei der Quellenmischung als eigene Quelle je Kanal.
- Nichts erfinden. Ist ein Datum, ein Band oder eine Zahl unklar, das Feld leer lassen oder `null` setzen. Bandlisten nur mit ausdrücklich genannten Bändern füllen, keine Bereiche auffüllen.

## Grenzen

- Keine Inhalte hinter Login oder Bezahlschranke.
- Keine Seiten aus „Nicht verwenden“ in `quellen.md`.
- Quellenseiten nicht selbst durchsuchen oder abrufen, außer zum gezielten Nachladen nach Schritt 3.
- Keine Dateien außerhalb von `data/` ändern. Änderungen an Anweisung, Quellen oder Schema nur auf ausdrücklichen Wunsch von DL6LG.
