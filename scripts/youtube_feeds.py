#!/usr/bin/env python3
"""Holt die vom Betreiber aufbereitete YouTube-Datei und legt sie als
data/youtube.json ab. Es gibt keinen Abruf bei YouTube selbst.

Quelle: https://ohrenbeisser.de/tools/afu/afu-youtube.json
Ist die Datei nicht erreichbar, wird sie über
https://ohrenbeisser.de/tools/afu/afu-youtube.php neu erzeugt und noch
einmal geholt. Zusätzlich wird, falls vorhanden, die Kanal-Infodatei nach
data/youtube-kanaele.json kopiert (Fehler dabei sind unkritisch).

Läuft als GitHub Action vor dem Wochen-Agenten (siehe
.github/workflows/youtube.yml). Der Agent liest nur die Ergebnisdatei.
Hat die Quelldatei kein Feld "abgerufen", wird es ergänzt; eine reine
Liste wird als {"videos": [...]} eingepackt.

Aufruf:  python3 scripts/youtube_feeds.py
Rückgabe 0 = Datei geholt und gültiges JSON, 1 = nicht erreichbar.
Nur Standardbibliothek, keine Abhängigkeiten.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIEL = ROOT / "data" / "youtube.json"
ZIEL_KANAELE = ROOT / "data" / "youtube-kanaele.json"
BASIS = "https://ohrenbeisser.de/tools/afu/"
VIDEOS = BASIS + "afu-youtube.json"
ERZEUGEN = BASIS + "afu-youtube.php"
KANAELE = [BASIS + urllib.parse.quote("afuyoutube-caneö.json"),
           BASIS + "afuyoutube-canel.json"]


def hole(url, versuche=3):
    anfrage = urllib.request.Request(url, headers={"User-Agent": "afunews-feedreader/1.0"})
    letzter_fehler = None
    for versuch in range(versuche):
        try:
            with urllib.request.urlopen(anfrage, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 – Fehlertext kommt ins Log
            letzter_fehler = e
            print(f"  {url}: Versuch {versuch + 1}/{versuche} fehlgeschlagen: {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(5 * (versuch + 1))
    raise letzter_fehler


def hole_json(url, versuche=3):
    return json.loads(hole(url, versuche).decode("utf-8"))


def main():
    jetzt = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    try:
        daten = hole_json(VIDEOS)
    except Exception as e:  # noqa: BLE001
        print(f"Datei nicht lesbar ({type(e).__name__}: {e}); erzeuge sie über {ERZEUGEN}", file=sys.stderr)
        try:
            hole(ERZEUGEN, 2)
            daten = hole_json(VIDEOS, 2)
        except Exception as e2:  # noqa: BLE001
            print(f"Abruf gescheitert: {type(e2).__name__}: {e2}", file=sys.stderr)
            return 1

    if isinstance(daten, list):
        daten = {"videos": daten}
    daten.setdefault("abgerufen", jetzt)
    ZIEL.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    anzahl = len(daten.get("videos", [])) if isinstance(daten.get("videos"), list) else "?"
    print(f"{ZIEL.name} geschrieben, Videos: {anzahl}")

    for url in KANAELE:
        try:
            info = hole_json(url, 1)
            ZIEL_KANAELE.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Kanalinfos aus {url} gespeichert")
            break
        except Exception as e:  # noqa: BLE001
            print(f"Kanalinfos nicht lesbar ({url}): {type(e).__name__}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
