# Arbeitsanweisung für den Wochen-Agenten

Diese Datei ist die feste Anweisung für jeden wöchentlichen Lauf. Jeder Lauf beginnt ohne Vorwissen; alles Nötige steht hier, in `quellen.md` und in `schema.md`.

## Auftrag

Der Lauf startet sonntags früh. Sammle die Amateurfunk-Nachrichten der laufenden Kalenderwoche (ISO 8601, Montag 00:00 bis zum Laufzeitpunkt), fasse sie auf Deutsch zusammen und lege sie als JSON in diesem Repository ab.

## Normaler Lauf oder Testlauf

Bestimme zuerst das Datum in der Zeitzone Europe/Berlin.

- **Sonntag:** normaler Lauf. Gearbeitet und gepusht wird auf `main`.
- **Jeder andere Wochentag:** Testlauf. Lege vom aktuellen `main` einen Branch `testlauf` an (ein vorhandener wird überschrieben), arbeite dort und pushe mit `git push --force origin testlauf`. `main` bleibt unverändert. Alles andere läuft genau wie beim normalen Lauf.

## Ablauf

1. **Woche bestimmen.** Bearbeitet wird die Kalenderwoche, in die das Laufdatum fällt. `zeitraum.von` ist deren Montag, `zeitraum.bis` das Laufdatum. Gibt es `data/JJJJ/JJJJ-Www.json` auf dem Arbeitsbranch schon, brich ab und melde das, statt sie zu überschreiben.
2. **Bekannte Links laden.** Lies die Wochendateien der letzten vier Wochen und sammle alle `quelle.url`. Was dort schon steht, wird nicht noch einmal aufgenommen, auch nicht als Termin.
3. **Quellen abarbeiten.** Gehe `quellen.md` durch, zuerst alle Kernquellen, dann Zusatzquellen und YouTube-Feeds. Die Zusatzquellen werden in jedem Lauf geprüft, nicht nur bei Zeitmangel in anderen Rubriken. Quellen mit Status „gesperrt“ oder „unbrauchbar“ auslassen. Ist eine Quelle nicht erreichbar, notiere das im Abschlussbericht und mach weiter. Hinweise zum Abruf:
   - DARC-Nachrichten über das Monatsarchiv lesen, auch Seite 2. Am Monatsanfang zusätzlich den Vormonat.
   - Den Deutschland-Rundspruch der Woche im DARC-Archiv öffnen; er erscheint donnerstags und bündelt viele Meldungen.
   - Conteste aus der DARC-Meldung „Aktuelle Conteste KW NN/JJJJ“ der *kommenden* Woche nehmen, falls sie schon erschienen ist; sonst die Seiten der großen Conteste direkt.
   - DXpeditionen über den RSS-Feed von NG3K und die Startseite von DX-World.
   - YouTube-Videos nicht direkt abrufen, sondern `data/youtube.json` lesen. Die Datei legt die GitHub Action „YouTube-Feeds abrufen“ sonntags vor dem Lauf an (Skript `scripts/youtube_feeds.py`). Ist `abgerufen` älter als zwei Tage, fehlt die Datei oder steht bei einem Kanal `ok: false`, das im Bericht vermerken. Beim Testlauf an anderen Wochentagen kann die Datei älter sein; dann nur Videos aus dem Zeitraum der Woche nehmen und das Alter im Bericht nennen.
4. **Auswählen.** Aufnehmen, was im Zeitraum veröffentlicht wurde und für Funkamateure in Deutschland von Belang ist. Weglassen: Werbung, Rabattaktionen, Produktankündigungen ohne Neuigkeitswert, Nachrufe auf unbekannte Personen außerhalb DL, reine Meinungsbeiträge.
5. **Doppelungen zusammenführen.** Berichten mehrere Quellen über dasselbe, wird es eine Meldung. Verlinkt wird die Originalquelle, also etwa die Behörde oder der Veranstalter, nicht der Sammeldienst. Jede `quelle.url` darf in einer Woche nur einmal vorkommen.
6. **Schreiben.** Titel und Zusammenfassung nach den Regeln unten.
7. **Termine.** Ereignisse der *kommenden* Woche als `typ: termin` aufnehmen. Nur die wichtigsten: große Conteste, DXpeditionen auf gesuchte Gebiete, ISS-Kontakte mit Schulen in DACH. Regionale Termine aus Sachsen und dem Vogtland werden immer aufgenommen, auch wenn die Ankündigung schon älter ist; dann als `typ: artikel` mit Rubrik `regional`.
8. **Kopf schreiben.** `ueberblick` mit drei bis fünf Sätzen zu den wichtigsten Themen; `ausbreitung` mit einer kurzen Notiz, wenn es Daten gibt (z. B. FunkWX des DARC-HF-Referats).
9. **Speichern.** Wochendatei schreiben, `data/index.json` aktualisieren (`aktualisiert`, neuer Eintrag in `wochen`, absteigend sortiert).
10. **Prüfen.** `python3 scripts/pruefen.py` ausführen. Fehler beheben, bis die Prüfung ohne Fehler durchläuft.
11. **Committen.** Autor `ohrenbeisser <ohrenbeisser@gmail.com>`. Commit-Nachricht: `KW 42/2026: 18 Meldungen`, beim Testlauf mit dem Zusatz `(Testlauf)`. Pushen wie oben beschrieben.
12. **Bericht.** Kurz melden: Laufart, Woche, Anzahl Meldungen je Rubrik, nicht erreichbare Quellen, Auffälligkeiten.

## Umfang

- Ziel: 18 bis 25 Meldungen pro Woche.
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
- Keine Dateien außerhalb von `data/` ändern. Änderungen an Anweisung, Quellen oder Schema nur auf ausdrücklichen Wunsch von DL6LG.
