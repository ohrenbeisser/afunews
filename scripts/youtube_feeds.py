#!/usr/bin/env python3
"""Holt die RSS-Feeds der YouTube-Kanäle aus quellen.md und schreibt
die neuen Videos nach data/youtube.json.

Läuft als GitHub Action vor dem Wochen-Agenten (siehe
.github/workflows/youtube.yml). Der Agent liest nur die Ergebnisdatei.

Aufruf:  python3 scripts/youtube_feeds.py [--tage 8]
Rückgabe 0 = mindestens ein Feed gelesen, 1 = kein Feed erreichbar.
Nur Standardbibliothek, keine Abhängigkeiten.
"""
import argparse
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUELLEN = ROOT / "quellen.md"
ZIEL = ROOT / "data" / "youtube.json"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
ID_RE = re.compile(r"^UC[\w-]{22}$")
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
MAX_BESCHREIBUNG = 1500


def kanaele_aus_quellen(text):
    """Liest die Tabelle unter '## YouTube-Kanäle'.
    Spalten: Kanal | Adresse | Kanal-ID | Sprache | Status"""
    teil = text.split("## YouTube-Kanäle", 1)
    if len(teil) < 2:
        return []
    abschnitt = teil[1].split("\n## ", 1)[0]
    kanaele = []
    for zeile in abschnitt.splitlines():
        zellen = [z.strip() for z in zeile.strip().strip("|").split("|")]
        if len(zellen) < 4 or not ID_RE.match(zellen[2]):
            continue
        kanaele.append({"name": zellen[0], "adresse": zellen[1],
                        "channel_id": zellen[2], "sprache": zellen[3]})
    return kanaele


def lies_feed(xml_bytes, kanal):
    wurzel = ET.fromstring(xml_bytes)
    videos = []
    for e in wurzel.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", default="", namespaces=NS)
        if not vid:
            continue
        link = e.find("a:link", NS)
        url = link.get("href") if link is not None else f"https://www.youtube.com/watch?v={vid}"
        beschreibung = e.findtext("media:group/media:description", default="", namespaces=NS) or ""
        videos.append({
            "kanal": kanal["name"],
            "channel_id": kanal["channel_id"],
            "sprache": kanal["sprache"],
            "video_id": vid,
            "titel": (e.findtext("a:title", default="", namespaces=NS) or "").strip(),
            "veroeffentlicht": e.findtext("a:published", default=None, namespaces=NS),
            "url": url,
            "ist_short": "/shorts/" in url,
            "beschreibung": beschreibung.strip()[:MAX_BESCHREIBUNG],
        })
    return videos


def hole(url):
    anfrage = urllib.request.Request(url, headers={"User-Agent": "afunews-feedreader/1.0"})
    letzter_fehler = None
    for versuch in range(2):
        try:
            with urllib.request.urlopen(anfrage, timeout=20) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 – Fehlertext landet in der Ergebnisdatei
            letzter_fehler = e
            time.sleep(3)
    raise letzter_fehler


def zeitpunkt(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tage", type=int, default=8, help="Zeitfenster rückwärts ab jetzt")
    args = ap.parse_args()

    jetzt = datetime.now(timezone.utc).replace(microsecond=0)
    von = jetzt - timedelta(days=args.tage)
    kanaele = kanaele_aus_quellen(QUELLEN.read_text(encoding="utf-8"))
    status, videos = [], []
    for k in kanaele:
        eintrag = {"name": k["name"], "channel_id": k["channel_id"]}
        try:
            alle = lies_feed(hole(FEED.format(k["channel_id"])), k)
            neu = [v for v in alle if (zeitpunkt(v["veroeffentlicht"]) or von) > von]
            videos.extend(neu)
            eintrag.update(ok=True, videos_im_feed=len(alle), videos_im_zeitraum=len(neu))
        except Exception as e:  # noqa: BLE001
            eintrag.update(ok=False, fehler=f"{type(e).__name__}: {e}")
        status.append(eintrag)

    videos.sort(key=lambda v: v["veroeffentlicht"] or "", reverse=True)
    ergebnis = {
        "abgerufen": jetzt.isoformat().replace("+00:00", "Z"),
        "zeitraum": {"von": von.isoformat().replace("+00:00", "Z"),
                     "bis": jetzt.isoformat().replace("+00:00", "Z")},
        "kanaele": status,
        "videos": videos,
    }
    ZIEL.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = sum(1 for s in status if s["ok"])
    print(f"{ok}/{len(status)} Feeds gelesen, {len(videos)} Videos im Zeitraum.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
