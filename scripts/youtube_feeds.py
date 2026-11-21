#!/usr/bin/env python3
"""Erzeugt die YouTube-Videoliste der Woche und legt sie als
data/youtube.json ab.

Ablauf:
1. Bevorzugt wird scripts/afu-youtube.php (Kopie des Betreiber-Skripts)
   auf dem GitHub-Runner mit der PHP-CLI ausgeführt. Es holt dann immer neu
   (kein Cache). Die Kanalliste afu-youtube-canel.json wird dafür von
   https://ohrenbeisser.de/tools/afu/ geladen. Das Skript schreibt nur,
   wenn alle Kanäle erreichbar waren.
2. Scheitert das (kein PHP, Kanal nicht erreichbar), wird
   https://ohrenbeisser.de/tools/afu/afu-youtube.php auf dem Server
   aufgerufen (bis 300 Sekunden Wartezeit, dort gilt ein Stunden-Cache) und
   danach https://ohrenbeisser.de/tools/afu/afu-youtube.json geholt.
Die Kanal-Infodatei wird zusätzlich nach data/youtube-kanaele.json kopiert.

Läuft als GitHub Action vor dem Wochen-Agenten (siehe
.github/workflows/youtube.yml). Der Agent liest nur die Ergebnisdatei.
Hat die Quelldatei kein Feld "abgerufen", wird es ergänzt; eine reine
Liste wird als {"videos": [...]} eingepackt.

Aufruf:  python3 scripts/youtube_feeds.py
Rückgabe 0 = Datei geholt und gültiges JSON, 1 = nicht erreichbar.
Nur Standardbibliothek, keine Abhängigkeiten.
"""
import json
import shutil
import subprocess
import sys
import tempfile
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
KANAL_URL = BASIS + "afu-youtube-canel.json"
PHP_SKRIPT = ROOT / "scripts" / "afu-youtube.php"


def hole(url, versuche=3, timeout=30):
    anfrage = urllib.request.Request(url, headers={"User-Agent": "afunews-feedreader/1.0"})
    letzter_fehler = None
    for versuch in range(versuche):
        try:
            with urllib.request.urlopen(anfrage, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 – Fehlertext kommt ins Log
            letzter_fehler = e
            print(f"  {url}: Versuch {versuch + 1}/{versuche} fehlgeschlagen: {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(5 * (versuch + 1))
    raise letzter_fehler


def hole_json(url, versuche=3):
    return json.loads(hole(url, versuche).decode("utf-8"))


def lokal_erzeugen():
    """Führt das PHP-Skript auf dem Runner aus. Gibt die Daten zurück oder None."""
    php = shutil.which("php")
    if not php:
        print("PHP-CLI nicht gefunden, überspringe lokale Erzeugung.", file=sys.stderr)
        return None
    with tempfile.TemporaryDirectory() as tmp:
        arbeit = Path(tmp)
        shutil.copy(PHP_SKRIPT, arbeit / "afu-youtube.php")
        try:
            (arbeit / "afu-youtube-canel.json").write_bytes(hole(KANAL_URL, 2))
        except Exception as e:  # noqa: BLE001
            print(f"Kanalliste nicht ladbar: {type(e).__name__}: {e}", file=sys.stderr)
            return None
        ZIEL_KANAELE.write_bytes((arbeit / "afu-youtube-canel.json").read_bytes())
        try:
            r = subprocess.run([php, str(arbeit / "afu-youtube.php")], cwd=arbeit,
                               capture_output=True, text=True, timeout=280)
        except Exception as e:  # noqa: BLE001
            print(f"PHP-Lauf gescheitert: {type(e).__name__}: {e}", file=sys.stderr)
            return None
        print(r.stdout[-1500:], flush=True)
        if r.stderr.strip():
            print(r.stderr.strip(), file=sys.stderr)
        ergebnis = arbeit / "afu-youtube.json"
        if r.returncode != 0 or not ergebnis.exists():
            print(f"PHP-Lauf ohne gültiges Ergebnis (Rückgabe {r.returncode}).", file=sys.stderr)
            return None
        return json.loads(ergebnis.read_text(encoding="utf-8"))


def main():
    jetzt = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    daten = lokal_erzeugen()
    if daten is not None:
        print("Videoliste lokal auf dem Runner erzeugt.")
    else:
        try:
            print(f"Fallback: erzeuge Datei auf dem Server über {ERZEUGEN} ...")
            t0 = time.time()
            antwort = hole(ERZEUGEN, 2, timeout=300)
            text = antwort.decode("utf-8", errors="replace").strip().replace("\n", " ")
            print(f"Serveraufruf nach {time.time() - t0:.1f} s, Antwort {len(antwort)} Bytes: {text[:150]}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"Warnung: Serveraufruf nicht bestätigt ({type(e).__name__}: {e})", file=sys.stderr)
        try:
            daten = hole_json(VIDEOS)
        except Exception as e:  # noqa: BLE001
            print(f"Abruf gescheitert: {type(e).__name__}: {e}", file=sys.stderr)
            return 1

    if isinstance(daten, list):
        daten = {"videos": daten}
    daten.setdefault("abgerufen", jetzt)
    ZIEL.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    liste = daten.get("Eintraege", daten.get("videos"))
    anzahl = len(liste) if isinstance(liste, list) else "?"
    print(f"{ZIEL.name} geschrieben, Videos: {anzahl}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
