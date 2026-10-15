#!/usr/bin/env python3
"""Prüft data/index.json und alle Wochendateien gegen schema.md.

Aufruf:  python3 scripts/pruefen.py [datei.json ...]
Ohne Argumente werden index.json und alle Wochendateien geprüft.
Rückgabe 0 = alles in Ordnung, 1 = Fehler gefunden.
Nur Standardbibliothek, keine Abhängigkeiten.
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

TYPEN = {"artikel", "video", "termin"}
RUBRIKEN = {"regulatorik", "verband", "dx", "contest", "satellit",
            "technik", "ausbreitung", "regional", "veranstaltung"}
REGIONEN = {"DL", "DACH", "EU", "INT", "S"}
KW_RE = re.compile(r"^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$")
ID_RE = re.compile(r"^\d{4}-W\d{2}-\d{3}$")

fehler = []


def f(ort, text):
    fehler.append(f"{ort}: {text}")


def ist_datum(s):
    try:
        date.fromisoformat(s)
        return True
    except (TypeError, ValueError):
        return False


def ist_zeit(s):
    try:
        datetime.fromisoformat(s)
        return True
    except (TypeError, ValueError):
        return False


def text(obj, feld, ort, maxlen=None):
    v = obj.get(feld)
    if not isinstance(v, str) or not v.strip():
        f(ort, f"'{feld}' fehlt oder ist leer")
        return None
    if maxlen and len(v) > maxlen:
        f(ort, f"'{feld}' ist länger als {maxlen} Zeichen")
    return v


def pruefe_meldung(m, kw, ort, urls):
    if not isinstance(m, dict):
        f(ort, "keine Meldung (kein Objekt)")
        return
    mid = text(m, "id", ort)
    if mid:
        ort = f"{ort} [{mid}]"
        if not ID_RE.match(mid) or not mid.startswith(kw):
            f(ort, f"'id' passt nicht zu {kw}-NNN")
    typ = m.get("typ")
    if typ not in TYPEN:
        f(ort, f"'typ' ungültig: {typ!r}")
    if m.get("rubrik") not in RUBRIKEN:
        f(ort, f"'rubrik' ungültig: {m.get('rubrik')!r}")
    text(m, "titel", ort, maxlen=100)
    zf = text(m, "zusammenfassung", ort)
    if zf and len(zf) > 600:
        f(ort, "'zusammenfassung' ist länger als 600 Zeichen")
    q = m.get("quelle")
    if not isinstance(q, dict):
        f(ort, "'quelle' fehlt")
    else:
        text(q, "name", ort + " quelle")
        url = text(q, "url", ort + " quelle")
        if url:
            if not url.startswith(("https://", "http://")):
                f(ort, "'quelle.url' ist kein Link")
            if url in urls:
                f(ort, f"Link doppelt: {url}")
            urls.add(url)
        text(q, "sprache", ort + " quelle")
    v = m.get("veroeffentlicht")
    if v is not None and not ist_datum(v):
        f(ort, f"'veroeffentlicht' kein Datum: {v!r}")
    if m.get("wichtigkeit") not in (1, 2, 3):
        f(ort, f"'wichtigkeit' muss 1, 2 oder 3 sein")
    if m.get("region") not in REGIONEN:
        f(ort, f"'region' ungültig: {m.get('region')!r}")
    if not isinstance(m.get("tags"), list):
        f(ort, "'tags' muss eine Liste sein")

    t = m.get("termin")
    if typ == "termin":
        if not isinstance(t, dict):
            f(ort, "'termin' fehlt bei typ termin")
        else:
            for feld in ("beginn", "ende"):
                if not ist_zeit(t.get(feld)):
                    f(ort, f"'termin.{feld}' keine Zeitangabe")
            for feld in ("rufzeichen", "baender", "betriebsarten"):
                if not isinstance(t.get(feld), list):
                    f(ort, f"'termin.{feld}' muss eine Liste sein")
    elif t is not None:
        f(ort, "'termin' muss null sein, wenn typ nicht termin ist")

    vd = m.get("video")
    if typ == "video":
        if not isinstance(vd, dict):
            f(ort, "'video' fehlt bei typ video")
        else:
            text(vd, "kanal", ort + " video")
            text(vd, "video_id", ort + " video")
            if vd.get("nur_beschreibung") is not True:
                f(ort, "'video.nur_beschreibung' muss true sein")
            if zf and not zf.startswith("Laut Videobeschreibung"):
                f(ort, "Video-Zusammenfassung muss mit 'Laut Videobeschreibung' beginnen")
    elif vd is not None:
        f(ort, "'video' muss null sein, wenn typ nicht video ist")


def pruefe_woche(pfad):
    ort = str(pfad.relative_to(ROOT)) if pfad.is_relative_to(ROOT) else str(pfad)
    try:
        w = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        f(ort, f"nicht lesbar: {e}")
        return None
    kw = w.get("kw")
    if not isinstance(kw, str) or not KW_RE.match(kw):
        f(ort, f"'kw' ungültig: {kw!r}")
        return None
    if pfad.name != f"{kw}.json" or pfad.parent.name != kw[:4]:
        f(ort, f"Dateiname oder Ordner passt nicht zu {kw}")
    z = w.get("zeitraum") or {}
    if not (ist_datum(z.get("von")) and ist_datum(z.get("bis"))):
        f(ort, "'zeitraum.von/bis' fehlt oder ist kein Datum")
    if not ist_zeit(w.get("erstellt")):
        f(ort, "'erstellt' keine Zeitangabe")
    text(w, "ueberblick", ort)
    a = w.get("ausbreitung")
    if a is not None and not isinstance(a, str):
        f(ort, "'ausbreitung' muss Text oder null sein")
    meldungen = w.get("meldungen")
    if not isinstance(meldungen, list):
        f(ort, "'meldungen' fehlt")
        return w
    urls = set()
    ids = set()
    for i, m in enumerate(meldungen):
        pruefe_meldung(m, kw, f"{ort} Meldung {i + 1}", urls)
        if isinstance(m, dict):
            if m.get("id") in ids:
                f(ort, f"id doppelt: {m.get('id')}")
            ids.add(m.get("id"))
    top = sum(1 for m in meldungen if isinstance(m, dict) and m.get("wichtigkeit") == 1)
    if top > 3:
        f(ort, f"{top} Top-Meldungen, erlaubt sind höchstens 3")
    vids = sum(1 for m in meldungen if isinstance(m, dict) and m.get("typ") == "video")
    if vids > 5:
        f(ort, f"{vids} Videos, erlaubt sind höchstens 5")
    return w


def pruefe_index():
    pfad = DATA / "index.json"
    ort = "data/index.json"
    try:
        idx = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        f(ort, f"nicht lesbar: {e}")
        return
    if idx.get("aktualisiert") is not None and not ist_zeit(idx.get("aktualisiert")):
        f(ort, "'aktualisiert' keine Zeitangabe")
    wochen = idx.get("wochen")
    if not isinstance(wochen, list):
        f(ort, "'wochen' fehlt")
        return
    kws = [w.get("kw") for w in wochen if isinstance(w, dict)]
    if kws != sorted(kws, reverse=True):
        f(ort, "'wochen' ist nicht absteigend sortiert")
    gelistet = set()
    for w in wochen:
        datei = DATA / w.get("datei", "")
        gelistet.add(datei.resolve())
        if not datei.is_file():
            f(ort, f"Datei fehlt: {w.get('datei')}")
            continue
        inhalt = pruefe_woche(datei)
        if inhalt and w.get("anzahl_meldungen") != len(inhalt.get("meldungen", [])):
            f(ort, f"{w.get('kw')}: 'anzahl_meldungen' stimmt nicht")
    for datei in sorted(DATA.glob("*/*.json")):
        if datei.resolve() not in gelistet:
            f(ort, f"nicht im Index: {datei.relative_to(DATA)}")


def main(argv):
    if argv:
        for a in argv:
            pruefe_woche(Path(a).resolve())
    else:
        pruefe_index()
    if fehler:
        print(f"{len(fehler)} Fehler:")
        for e in fehler:
            print("  - " + e)
        return 1
    print("Prüfung bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
