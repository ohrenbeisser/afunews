# Arbeitsanweisung für den Wochen-Agenten

Diese Datei ist die feste Anweisung für jeden wöchentlichen Lauf. Jeder Lauf beginnt ohne Vorwissen; alles Nötige steht hier, in `quellen.md` und in `schema.md`.

## Auftrag

Sammle die Amateurfunk-Nachrichten der vergangenen Kalenderwoche (Montag bis Sonntag, ISO 8601), fasse sie auf Deutsch zusammen und lege sie als JSON in diesem Repository ab.

## Ablauf

1. **Woche bestimmen.** Die zu bearbeitende Woche ist die Kalenderwoche vor dem Laufdatum. Gibt es `data/JJJJ/JJJJ-Www.json` schon, brich ab und melde das, statt sie zu überschreiben.
2. **Bekannte Links laden.** Lies die Wochendateien der letzten vier Wochen und sammle alle `quelle.url`. Was dort schon steht, wird nicht noch einmal aufgenommen.
3. **Quellen abarbeiten.** Gehe `quellen.md` durch, zuerst alle Kernquellen, dann Zusatzquellen und YouTube-Feeds. Ist eine Quelle nicht erreichbar, notiere das im Abschlussbericht und mach weiter.
4. **Auswählen.** Aufnehmen, was in den Zeitraum fällt und für Funkamateure in Deutschland von Belang ist. Weglassen: Werbung, Produktankündigungen ohne Neuigkeitswert, Nachrufe auf unbekannte Personen außerhalb DL, reine Meinungsbeiträge.
5. **Doppelungen zusammenführen.** Berichten mehrere Quellen über dasselbe, wird es eine Meldung. Verlinkt wird die Originalquelle, also etwa die Behörde oder der Veranstalter, nicht der Sammeldienst.
6. **Schreiben.** Titel und Zusammenfassung nach den Regeln unten.
7. **Termine.** Conteste und DX-Aktivitäten, die in der *kommenden* Woche stattfinden, als `typ: termin` aufnehmen. Nur die wichtigsten: große Conteste, DXpeditionen auf gesuchte Gebiete, ISS-Kontakte mit Schulen in DACH.
8. **Kopf schreiben.** `ueberblick` mit drei bis fünf Sätzen zu den wichtigsten Themen; `ausbreitung` mit einer kurzen Notiz, wenn es Daten gibt.
9. **Speichern.** Wochendatei schreiben, `data/index.json` aktualisieren.
10. **Prüfen.** `python3 scripts/pruefen.py` ausführen. Fehler beheben, bis die Prüfung ohne Fehler durchläuft.
11. **Committen.** Commit-Nachricht: `KW 42/2026: 18 Meldungen`. Auf den Branch `main` pushen.
12. **Bericht.** Kurz melden: Anzahl Meldungen je Rubrik, nicht erreichbare Quellen, Auffälligkeiten.

## Umfang

- Ziel: 10 bis 25 Meldungen pro Woche.
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
- Nichts erfinden. Ist ein Datum oder eine Zahl unklar, das Feld leer lassen oder `null` setzen.

## Grenzen

- Keine Inhalte hinter Login oder Bezahlschranke.
- Keine Seiten aus „Nicht verwenden“ in `quellen.md`.
- Keine Dateien außerhalb von `data/` ändern. Änderungen an Anweisung, Quellen oder Schema nur auf ausdrücklichen Wunsch von DL6LG.
