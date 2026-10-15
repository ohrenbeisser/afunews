# Datenformat

Alle Daten liegen als JSON (UTF-8, 2 Leerzeichen Einrückung) im Ordner `data/`.

```
data/
├── index.json            Übersicht aller Wochen
└── 2026/
    └── 2026-W42.json     eine Datei pro Kalenderwoche (ISO 8601)
```

## index.json

```json
{
  "aktualisiert": "2026-10-19T07:12:00+02:00",
  "wochen": [
    {
      "kw": "2026-W42",
      "datei": "2026/2026-W42.json",
      "erstellt": "2026-10-19T07:12:00+02:00",
      "anzahl_meldungen": 18
    }
  ]
}
```

`wochen` ist absteigend sortiert, die neueste Woche steht oben.

## Wochendatei

```json
{
  "kw": "2026-W42",
  "zeitraum": { "von": "2026-10-12", "bis": "2026-10-18" },
  "erstellt": "2026-10-19T07:12:00+02:00",
  "ueberblick": "Drei bis fünf Sätze zu den wichtigsten Themen der Woche.",
  "ausbreitung": "Kurze Notiz zur Sonnenaktivität und den Bedingungen, oder null.",
  "meldungen": [ ... ]
}
```

## Meldung

| Feld | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `id` | Text | ja | `2026-W42-001`, fortlaufend pro Woche |
| `typ` | Text | ja | `artikel`, `video` oder `termin` |
| `rubrik` | Text | ja | eine der Rubriken unten |
| `titel` | Text | ja | eigene Überschrift auf Deutsch, höchstens 100 Zeichen |
| `zusammenfassung` | Text | ja | 2 bis 3 Sätze in eigenen Worten, auf Deutsch |
| `quelle.name` | Text | ja | z. B. `DARC`, `Southgate ARC` |
| `quelle.url` | Text | ja | Link zum Original, dient als Schlüssel gegen Doppelungen |
| `quelle.sprache` | Text | ja | `de`, `en`, … |
| `veroeffentlicht` | Datum | nein | Datum der Originalmeldung (`JJJJ-MM-TT`), `null` wenn unbekannt |
| `wichtigkeit` | Zahl | ja | 1 = Top-Meldung, 2 = normal, 3 = Randnotiz |
| `region` | Text | ja | `DL`, `DACH`, `EU`, `INT` oder `S` (Distrikt Sachsen) |
| `tags` | Liste | ja | einige Schlagwörter, darf leer sein |
| `termin` | Objekt | nein | nur bei `typ: termin`, sonst `null` |
| `video` | Objekt | nein | nur bei `typ: video`, sonst `null` |

### termin

```json
{
  "beginn": "2026-10-24T00:00:00Z",
  "ende": "2026-10-25T23:59:00Z",
  "rufzeichen": ["3Y0K"],
  "baender": ["160m", "80m", "40m"],
  "betriebsarten": ["CW", "SSB", "FT8"]
}
```

Zeiten in UTC. Felder, die nicht bekannt sind, bleiben leere Listen.

### video

```json
{
  "kanal": "Name des Kanals",
  "video_id": "dQw4w9WgXcQ",
  "dauer": "PT18M30S",
  "nur_beschreibung": true
}
```

`nur_beschreibung: true` heißt: Die Zusammenfassung beruht nur auf Titel und Videobeschreibung, das Video selbst wurde nicht gesehen. Das ist bei diesem Agenten immer der Fall.

## Rubriken

| Schlüssel | Anzeige |
|---|---|
| `regulatorik` | Regulatorik und Behörden |
| `verband` | Verbände und Vereine |
| `dx` | DX und DXpeditionen |
| `contest` | Contest |
| `satellit` | Satelliten und Raumfahrt |
| `technik` | Technik und Selbstbau |
| `ausbreitung` | Ausbreitung |
| `regional` | Sachsen und Vogtland |
| `veranstaltung` | Treffen, Messen, Fieldday |
