# afunews

News aus dem Bereich des Amateurfunks, einmal pro Woche gesammelt, auf Deutsch zusammengefasst und als JSON abgelegt.

Ein Agent (Claude, als geplanter Task) läuft wöchentlich, arbeitet die Quellenliste ab und schreibt eine Datei pro Kalenderwoche nach `data/`. Eine Webseite liest diese Dateien und zeigt sie an.

## Inhalt

| Datei / Ordner | Zweck |
|---|---|
| `ANWEISUNG.md` | Feste Arbeitsanweisung für jeden Lauf des Agenten |
| `quellen.md` | Quellenliste: Kernquellen, Zusatzquellen, YouTube-Kanäle |
| `schema.md` | Datenformat aller JSON-Dateien |
| `data/index.json` | Übersicht aller Wochen |
| `data/JJJJ/JJJJ-Www.json` | eine Datei pro Kalenderwoche |
| `scripts/pruefen.py` | prüft alle Dateien gegen das Format |
| `beispiel/` | Beispieldatei mit erfundenen Inhalten, nur zur Ansicht |

## Prüfen

```sh
python3 scripts/pruefen.py                 # index.json und alle Wochen
python3 scripts/pruefen.py pfad/datei.json # einzelne Datei
```

Nur Python-Standardbibliothek, keine Installation nötig.

## Stand

- [x] Grundgerüst, Datenformat, Quellenliste, Prüfskript
- [x] Probelauf von Hand (KW 41), Quellen auf Erreichbarkeit geprüft
- [ ] Wöchentlicher geplanter Task
- [ ] GitHub Action für den Upload zum Webspace
- [ ] Anzeige auf der Webseite

## Hinweis

Die Zusammenfassungen sind eigene Kurztexte mit Link auf die jeweilige Originalquelle. Für den Inhalt der verlinkten Seiten sind deren Betreiber verantwortlich. Videos werden nur anhand von Titel und Beschreibung zusammengefasst.

Betreiber: DL6LG, [ohrenbeisser.de](https://www.ohrenbeisser.de/)
