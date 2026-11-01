#!/usr/bin/env python3
"""Sammelt die Meldungen der Woche von den Quellen aus quellen.json und
schreibt sie nach data/rohdaten/JJJJ-Www.json.

Läuft als GitHub Action vor dem Wochen-Agenten (siehe
.github/workflows/quellen.yml). Der Agent ruft keine Webseiten mehr ab,
sondern liest nur diese Datei (und data/youtube.json).

Ablauf je Quelle: Feed oder Übersichtsseite lesen, bei Übersichtsseiten die
Detailseiten der Meldungen laden, Datum und Textauszug bestimmen, alles
vor Wochenbeginn und bereits bekannte Links aussortieren.

Aufruf:  python3 scripts/quellen_sammeln.py [--datum JJJJ-MM-TT] [--ziel DATEI]
Rückgabe 0 = mindestens eine Quelle geliefert, 1 = nichts erreichbar.
Nur Standardbibliothek, keine Abhängigkeiten.
"""
import argparse
import email.utils
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
KONFIG = ROOT / "quellen.json"
DATA = ROOT / "data"
ROHDATEN = DATA / "rohdaten"
UA = "afunews-sammler/1.0 (+https://github.com/ohrenbeisser/afunews)"
PAUSE = 1.0           # Sekunden zwischen Abrufen
MAX_BYTES = 3_000_000
BERLIN = ZoneInfo("Europe/Berlin")
MONATE_EN = ["january", "february", "march", "april", "may", "june", "july",
             "august", "september", "october", "november", "december"]
MONATE_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
            "September", "Oktober", "November", "Dezember"]
MONATE_EN_KURZ = {m[:3]: i + 1 for i, m in enumerate(MONATE_EN)}
ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"

GENERISCH = {"sitemap", "arrl", "cart", "home", "start", "startseite", "mehr", "weiterlesen",
             "weiterlesen …", "read more", "more", "menu", "menü", "details", "mehr erfahren",
             "link zu dieser meldung", "zurück", "zurück zur übersicht", "nachrichten detailansicht",
             "detailansicht", "news", "nachrichten", "aktuelles"}

_letzter_abruf = [0.0]
_robots = {}


# ---------------------------------------------------------------- Abruf

def erlaubt(url):
    """robots.txt des Hosts beachten; bei Fehlern gilt: erlaubt."""
    teile = urllib.parse.urlsplit(url)
    host = f"{teile.scheme}://{teile.netloc}"
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(host + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as r:
                rp.parse(r.read(200_000).decode("utf-8", "replace").splitlines())
        except Exception:  # noqa: BLE001 – ohne lesbare robots.txt gilt: erlaubt
            rp = None
        _robots[host] = rp
    rp = _robots[host]
    return True if rp is None else rp.can_fetch(UA, url)


def hole(url):
    """Liefert (Text, Endadresse). Wirft bei Fehlern."""
    if not erlaubt(url):
        raise PermissionError("robots.txt untersagt den Abruf")
    letzter = None
    for versuch in range(2):
        warte = PAUSE - (time.monotonic() - _letzter_abruf[0])
        if warte > 0:
            time.sleep(warte)
        _letzter_abruf[0] = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml,application/rss+xml;q=0.9,*/*;q=0.5",
                "Accept-Language": "de,en;q=0.7",
            })
            with urllib.request.urlopen(req, timeout=25) as r:
                roh = r.read(MAX_BYTES)
                cs = r.headers.get_content_charset() or "utf-8"
                return roh.decode(cs, "replace"), r.geturl()
        except urllib.error.HTTPError as e:
            letzter = e
            if e.code in (401, 403, 404, 410, 451):
                break
            time.sleep(3)
        except Exception as e:  # noqa: BLE001
            letzter = e
            time.sleep(3)
    raise letzter


# ---------------------------------------------------------------- Text und Datum

def bereinige(s):
    s = html.unescape(s or "")
    return re.sub(r"\s+", " ", s).strip()


def ohne_tags(s):
    return bereinige(re.sub(r"<[^>]+>", " ", s or ""))


def kuerze(s, n):
    s = s.strip()
    if len(s) <= n:
        return s
    stueck = s[:n].rsplit(" ", 1)[0]
    return stueck + " …"


class LinkParser(HTMLParser):
    """Sammelt alle Links (absolut) mit Linktext und dem Text davor/danach
    (dort steht auf Übersichtsseiten oft das Datum)."""

    def __init__(self, basis):
        super().__init__(convert_charrefs=True)
        self.basis = basis
        self.teile = []          # ("t", Text) oder ("a", Index in self.links)
        self.links = []          # Dicts: href, text, davor, danach
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "base":
            h = dict(attrs).get("href")
            if h:
                self.basis = urllib.parse.urljoin(self.basis, h)
        if tag == "a":
            h = dict(attrs).get("href")
            self._href = urllib.parse.urljoin(self.basis, h) if h else None
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)
        else:
            self.teile.append(("t", data))

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append({"href": self._href.split("#")[0],
                               "text": bereinige(" ".join(self._text))})
            self.teile.append(("a", len(self.links) - 1))
            self._href = None

    def ergebnis(self):
        """Links mit Kontext; je Adresse nur einmal, mit dem längsten Linktext."""
        for i, (art, wert) in enumerate(self.teile):
            if art != "a":
                continue
            davor, j = [], i - 1
            while j >= 0 and self.teile[j][0] == "t":
                davor.insert(0, self.teile[j][1])
                j -= 1
            danach, j = [], i + 1
            while j < len(self.teile) and self.teile[j][0] == "t":
                danach.append(self.teile[j][1])
                j += 1
            self.links[wert]["davor"] = bereinige(" ".join(davor))[-80:]
            self.links[wert]["danach"] = bereinige(" ".join(danach))[:80]
        beste = {}
        for l in self.links:
            alt = beste.get(l["href"])
            if alt is None:
                beste[l["href"]] = alt = dict(l)
                alt["texte"] = []
            alt["texte"].append(l["text"])
            if not alt.get("davor") and l.get("davor"):
                alt["davor"], alt["danach"] = l["davor"], l["danach"]
        for alt in beste.values():
            gut = [t for t in alt["texte"] if t.lower() not in GENERISCH]
            alt["text"] = max(gut or alt["texte"], key=len)
        return list(beste.values())


class TextParser(HTMLParser):
    """Reiner Text einer Seite. Bevorzugt <article>/<main>, lässt Navigation aus."""
    SKIP = {"head", "script", "style", "noscript", "nav", "header", "footer", "aside",
            "form", "svg", "template", "iframe"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr",
             "section", "article", "main", "table", "ul", "ol", "dd", "dt"}
    VOID = {"br", "img", "meta", "link", "input", "hr", "source", "wbr", "area", "col"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.art = 0
        self.alles = []
        self.artikel = []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            if tag == "br":
                self._add("\n")
            return
        if tag in self.SKIP:
            self.skip += 1
        if tag in ("article", "main") and not self.skip:
            self.art += 1
        if tag in self.BLOCK:
            self._add("\n")

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag in ("article", "main") and self.art:
            self.art -= 1
        if tag in self.BLOCK:
            self._add("\n")

    def handle_data(self, data):
        if not self.skip:
            self._add(data)

    def _add(self, s):
        self.alles.append(s)
        if self.art:
            self.artikel.append(s)

    def text(self):
        def zeilen(teile):
            roh = "".join(teile)
            return [z for z in (bereinige(x) for x in roh.split("\n")) if z]
        z = zeilen(self.artikel)
        if len(" ".join(z)) <= 200:
            z = zeilen(self.alles)
        return " ".join(entferne_menues(z))


JUNK = re.compile(r"cookie|navigation überspringen|direkt zum inhalt|datenschutzerkl|^zurück$| > ", re.I)


def entferne_menues(zeilen):
    """Wirft Menü- und Fußzeilen heraus: Folgen von mindestens vier kurzen
    Zeilen ohne Satzzeichen am Ende sowie Cookie-Hinweise und Brotkrumen."""
    def kurz(z):
        return len(z) < 30 and not z.endswith((".", "!", "?", ":", ";"))
    ergebnis, lauf = [], []
    for z in zeilen + [None]:
        if z is not None and kurz(z):
            lauf.append(z)
            continue
        if len(lauf) < 4:
            ergebnis.extend(lauf)
        lauf = []
        if z is not None and not JUNK.search(z):
            ergebnis.append(z)
    return ergebnis


def meta_datum(roh):
    muster = [
        r'<meta[^>]+(?:property|name|itemprop)=["\'](?:article:published_time|og:article:published_time|datePublished|date|dc\.date|dcterms\.created)["\'][^>]*content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name|itemprop)=["\'](?:article:published_time|og:article:published_time|datePublished|date|dc\.date|dcterms\.created)["\']',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'<time[^>]+datetime=["\']([^"\']+)',
    ]
    for m in muster:
        f = re.search(m, roh, re.I)
        if f:
            d = datum_aus_text(f.group(1))
            if d:
                return d
    return None


def datum_aus_text(s):
    """Erstes Datum in einem Text: ISO, TT.MM.JJJJ oder englische Schreibweisen."""
    m = re.search(r"(?<!\d)(20\d\d)-(\d\d)-(\d\d)(?!\d)", s)
    if m:
        return _d(m.group(1), m.group(2), m.group(3))
    m = re.search(r"\b(\d{1,2})\.\s?(\d{1,2})\.\s?(20\d\d)\b", s)
    if m:
        return _d(m.group(3), m.group(2), m.group(1))
    m = re.search(r"(?<![\d/])(\d{1,2})/(\d{1,2})/(20\d\d)(?!\d)", s)  # US: Monat/Tag/Jahr
    if m:
        return _d(m.group(3), m.group(1), m.group(2))
    m = re.search(r"\b(\d{1,2})\.?\s+(Januar|Februar|März|Maerz|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+(20\d\d)\b", s)
    if m:
        return _d(m.group(3), MONATE_DE.index(m.group(2).replace("Maerz", "März")) + 1, m.group(1))
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(20\d\d)\b", s)
    if m and m.group(2)[:3].lower() in MONATE_EN_KURZ:
        return _d(m.group(3), MONATE_EN_KURZ[m.group(2)[:3].lower()], m.group(1))
    m = re.search(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)\b", s)
    if m and m.group(1)[:3].lower() in MONATE_EN_KURZ:
        return _d(m.group(3), MONATE_EN_KURZ[m.group(1)[:3].lower()], m.group(2))
    return None


def _d(j, m, t):
    try:
        return date(int(j), int(m), int(t))
    except ValueError:
        return None


def seitentitel(roh):
    for m in (r'<meta[^>]+property=["\']og:title["\'][^>]*content=["\']([^"\']+)',
              r"<h1[^>]*>(.*?)</h1>",
              r"<title[^>]*>(.*?)</title>"):
        f = re.search(m, roh, re.I | re.S)
        if f:
            t = ohne_tags(f.group(1))
            t = re.sub(r"^News:\s*", "", t)
            t = re.sub(r"\s+[-–|]\s+DARC.*$", "", t)
            if t and t.lower() not in GENERISCH:
                return t
    return ""


# ---------------------------------------------------------------- Feeds

def lies_feed(xml_text):
    """RSS oder Atom -> Liste von Einträgen (Titel, URL, Datum, Text)."""
    try:
        wurzel = ET.fromstring(xml_text.encode("utf-8"))
    except ET.ParseError:
        return lies_feed_locker(xml_text)
    eintraege = []
    for e in wurzel.iter():
        tag = e.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        titel = bereinige(e.findtext("title") or e.findtext(ATOM + "title") or "")
        link = (e.findtext("link") or "").strip()
        if not link:
            for l in e.findall(ATOM + "link"):
                if l.get("rel", "alternate") == "alternate" and l.get("href"):
                    link = l.get("href")
                    break
        roh_datum = (e.findtext("pubDate") or e.findtext(ATOM + "published")
                     or e.findtext(ATOM + "updated") or e.findtext("{http://purl.org/dc/elements/1.1/}date") or "")
        d = None
        try:
            d = email.utils.parsedate_to_datetime(roh_datum).astimezone(BERLIN).date()
        except (TypeError, ValueError):
            d = datum_aus_text(roh_datum)
        text = (e.findtext(CONTENT + "encoded") or e.findtext("description")
                or e.findtext(ATOM + "content") or e.findtext(ATOM + "summary") or "")
        eintraege.append({"titel": titel, "url": link, "datum": d, "text": ohne_tags(text)})
    return eintraege


def lies_feed_locker(xml_text):
    """Notlösung für Feeds mit fehlerhaftem XML: Felder per Muster holen."""
    def feld(block, name):
        f = re.search(r"<%s[^>]*>(.*?)</%s>" % (name, name), block, re.S | re.I)
        if not f:
            return ""
        w = f.group(1).strip()
        c = re.match(r"<!\[CDATA\[(.*)\]\]>$", w, re.S)
        return c.group(1) if c else w
    eintraege = []
    for blk in re.findall(r"<item[ >].*?</item>", xml_text, re.S | re.I):
        roh_datum = feld(blk, "pubDate")
        try:
            d = email.utils.parsedate_to_datetime(roh_datum).astimezone(BERLIN).date()
        except (TypeError, ValueError):
            d = datum_aus_text(roh_datum)
        text = feld(blk, "content:encoded") or feld(blk, "description")
        eintraege.append({"titel": bereinige(feld(blk, "title")), "url": bereinige(feld(blk, "link")),
                          "datum": d, "text": ohne_tags(text)})
    if not eintraege:
        raise ET.ParseError("Feed nicht lesbar")
    return eintraege


# ---------------------------------------------------------------- Quellen

def montag_der_woche(tag):
    return tag - timedelta(days=tag.weekday())


def monate_fuer(tag, montag):
    """Monate, deren Archivseiten gelesen werden: Wochenanfang, heute und am
    Monatsanfang zusätzlich der Vormonat."""
    liste = {(montag.year, montag.month), (tag.year, tag.month)}
    if tag.day <= 7:
        vm = tag.replace(day=1) - timedelta(days=1)
        liste.add((vm.year, vm.month))
    return sorted(liste, reverse=True)


def ersetze(url, jahr, monat):
    return (url.replace("{JJJJ}", f"{jahr:04d}").replace("{MM}", f"{monat:02d}")
            .replace("{JJJJMM}", f"{jahr:04d}{monat:02d}")
            .replace("{MONAT_EN}", MONATE_EN[monat - 1]))


def auszug_laenge(quelle, titel):
    for s in quelle.get("auszug_sonder", []):
        if s["titel_enthaelt"].lower() in titel.lower():
            return s["zeichen"]
    return quelle.get("auszug", 500)


def sammle_quelle(q, tag, von, bekannt):
    """Eine Quelle abarbeiten. Liefert (eintraege, hinweise). Wirft nur, wenn
    keine einzige Abrufvariante etwas geliefert hat."""
    eintraege, hinweise, fehler = [], [], []
    for variante in q["abruf"]:
        try:
            gefunden = _variante(q, variante, tag, von, bekannt, hinweise)
        except Exception as e:  # noqa: BLE001
            fehler.append(f"{variante['url']}: {type(e).__name__}: {e}")
            continue
        eintraege.extend(gefunden)
        if gefunden or not q.get("weiter_bei_leer", True):
            break
    if not eintraege and fehler:
        raise RuntimeError("; ".join(fehler))
    hinweise.extend(f"Fehler bei Variante: {f}" for f in fehler)
    return eintraege, hinweise


def _urls_der_variante(v, tag, von):
    if not v.get("monatlich"):
        basen = [v["url"]]
    else:
        basen = [ersetze(v["url"], j, m) for j, m in monate_fuer(tag, von)]
    urls = []
    for b in basen:
        for suffix in v.get("seiten", [""]):
            urls.append(b + suffix)
    return urls


def _variante(q, v, tag, von, bekannt, hinweise):
    sonder = q.get("immer_titel", [])
    ergebnis = []
    if v["typ"] == "rss":
        text, _ = hole(v["url"])
        feed = lies_feed(text)
        imfenster = [e for e in feed if v.get("ohne_datumsfilter") or not e["datum"] or e["datum"] >= von]
        hinweise.append("%s: %d Einträge im Feed, %d im Zeitraum"
                        % (v["url"][:60], len(feed), len(imfenster)))
        for e in feed[: v.get("max", 40)]:
            if not e["url"] or e["url"] in bekannt:
                continue
            if not v.get("ohne_datumsfilter") and e["datum"] and e["datum"] < von:
                continue
            ergebnis.append(_eintrag(q, e["titel"], e["url"], e["datum"], "feed", e["text"]))
        return ergebnis

    # html: Übersichtsseiten -> Kandidaten -> Detailseiten
    muster = re.compile(v["link_muster"])
    kandidaten, gesehen, gelesen, probleme, links_gesamt = [], set(), 0, [], 0
    for u in _urls_der_variante(v, tag, von):
        try:
            seite, endadresse = hole(u)
        except Exception as e:  # noqa: BLE001
            probleme.append(f"Übersicht nicht lesbar: {u}: {type(e).__name__}: {e}")
            continue
        gelesen += 1
        p = LinkParser(endadresse)
        p.feed(seite)
        alle = p.ergebnis()
        links_gesamt += len(alle)
        for l in alle:
            if l["href"] in gesehen or not muster.search(l["href"]):
                continue
            gesehen.add(l["href"])
            kandidaten.append(l)
    hinweise.extend(probleme)
    if not gelesen:
        raise RuntimeError("; ".join(probleme))
    if not kandidaten:
        proben = [l for l in alle][:12] if gelesen else []
        hinweise.append("Übersicht gelesen (%d Links), aber kein Link passt zu link_muster; Beispiele: %s"
                        % (links_gesamt, ", ".join(l["href"] for l in proben)))
        return []
    neu_kand = [l for l in kandidaten if l["href"] not in bekannt]
    hinweise.append("%s: %d Kandidaten, %d davon schon bekannt"
                    % (v["url"][:60], len(kandidaten), len(kandidaten) - len(neu_kand)))
    alt_in_folge, geholt = 0, 0
    for l in neu_kand:
        href, listentitel = l["href"], l["text"]
        ist_sonder = any(x.lower() in listentitel.lower() for x in sonder)
        if geholt >= v.get("max_detail", 15) and not ist_sonder:
            continue
        lm = v.get("datum_aus_liste", "beide")
        d_liste = None if lm == "aus" else (datum_aus_text(l.get("davor", "")) or
                                           (datum_aus_text(l.get("danach", "")) if lm == "beide" else None))
        if (d_liste and d_liste < von and not ist_sonder and not v.get("ohne_datumsfilter")):
            alt_in_folge += 1
            if alt_in_folge >= v.get("stopp_nach_alt", 3):
                break
            continue
        if v.get("ohne_detail"):
            ergebnis.append(_eintrag(q, listentitel, href, d_liste, "liste" if d_liste else "keins", ""))
            geholt += 1
            continue
        try:
            seite, _ = hole(href)
        except Exception as e:  # noqa: BLE001
            hinweise.append(f"Detailseite nicht lesbar: {href}: {type(e).__name__}: {e}")
            continue
        geholt += 1
        tp = TextParser()
        tp.feed(seite)
        text = tp.text()
        titel = waehle_titel(listentitel, seite)
        titel = re.sub(r"^Weiterlesen\s*…?\s*", "", titel)
        i = text.find(titel) if len(titel) >= 8 else -1
        if i >= 0:                                # Menüreste vor der Überschrift abschneiden
            text = text[i + len(titel):].lstrip(" -–|:")
        d, herkunft = meta_datum(seite), "meta"
        if d is None and d_liste:
            d, herkunft = d_liste, "liste"
        if d is None:
            d, herkunft = datum_aus_text(text[:600]), "text"
        ist_sonder = ist_sonder or any(x.lower() in titel.lower() for x in sonder)
        if d is not None and d < von and not ist_sonder and not v.get("ohne_datumsfilter"):
            alt_in_folge += 1
            if alt_in_folge >= v.get("stopp_nach_alt", 3):
                break
            continue
        alt_in_folge = 0
        ergebnis.append(_eintrag(q, titel, href, d, herkunft if d else "unbekannt", text))
    return ergebnis


def waehle_titel(listentitel, seite):
    """Linktext der Übersicht, sonst Überschrift der Detailseite."""
    if len(listentitel) >= 12 and listentitel.lower() not in GENERISCH:
        return re.sub(r"^Weiterlesen\s*…?\s*", "", listentitel)
    for t in (seitentitel(seite), re.sub(r"^Weiterlesen\s*…?\s*", "", listentitel), listentitel):
        if t and t.lower() not in GENERISCH:
            return t
    return listentitel


def _eintrag(q, titel, url, d, datum_herkunft, text):
    n = auszug_laenge(q, titel)
    return {
        "titel": titel,
        "url": url,
        "datum": d.isoformat() if d else None,
        "datum_herkunft": datum_herkunft,
        "auszug": kuerze(text, n),
    }


def bekannte_links(kw, wochen=4):
    """Alle quelle.url der letzten Wochendateien (nicht noch einmal aufnehmen).
    Die Datei der laufenden Woche zählt nicht mit, sonst bliebe bei einem
    zweiten Lauf nichts übrig."""
    urls = set()
    dateien = [d for d in sorted(DATA.glob("20*/20*-W*.json"), reverse=True) if d.stem != kw]
    for datei in dateien[:wochen]:
        try:
            w = json.loads(datei.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for m in w.get("meldungen", []):
            u = (m.get("quelle") or {}).get("url")
            if u:
                urls.add(u)
    return urls


# ---------------------------------------------------------------- Hauptprogramm

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datum", help="Laufdatum JJJJ-MM-TT (Standard: heute in Europe/Berlin)")
    ap.add_argument("--ziel", help="Ausgabedatei (Standard: data/rohdaten/JJJJ-Www.json)")
    ap.add_argument("--nur", help="nur diese Quellen-ID (zum Testen)")
    args = ap.parse_args()

    jetzt = datetime.now(timezone.utc).replace(microsecond=0)
    tag = date.fromisoformat(args.datum) if args.datum else jetzt.astimezone(BERLIN).date()
    von = montag_der_woche(tag)
    iso = tag.isocalendar()
    kw = f"{iso[0]}-W{iso[1]:02d}"
    ziel = Path(args.ziel) if args.ziel else ROHDATEN / f"{kw}.json"

    konfig = json.loads(KONFIG.read_text(encoding="utf-8"))
    bekannt = bekannte_links(kw)

    ergebnisse, ok = [], 0
    for q in konfig["quellen"]:
        if args.nur and q["id"] != args.nur:
            continue
        eintrag = {"id": q["id"], "name": q["name"], "sprache": q["sprache"],
                   "rubriken": q.get("rubriken", []), "kern": q.get("kern", False),
                   "nur_hinweis": q.get("nur_hinweis", False)}
        try:
            eintraege, hinweise = sammle_quelle(q, tag, von, bekannt)
            eintrag.update(status="ok" if eintraege else "leer",
                           anzahl=len(eintraege), hinweise=hinweise, eintraege=eintraege)
            ok += 1 if eintraege else 0
        except Exception as e:  # noqa: BLE001
            eintrag.update(status="fehler", anzahl=0, fehler=f"{type(e).__name__}: {e}",
                           hinweise=[], eintraege=[])
        ergebnisse.append(eintrag)
        print(f"{q['id']:<22} {eintrag['status']:<7} {eintrag['anzahl']:>3}")

    # Rohdaten früherer Wochen entfernen, damit das Repository nicht anwächst.
    ROHDATEN.mkdir(parents=True, exist_ok=True)
    if not args.ziel:
        for alt in ROHDATEN.glob("*.json"):
            if alt != ziel:
                alt.unlink()

    ausgabe = {
        "kw": kw,
        "zeitraum": {"von": von.isoformat(), "bis": tag.isoformat()},
        "abgerufen": jetzt.isoformat().replace("+00:00", "Z"),
        "hinweis": "Rohdaten für den Wochen-Agenten. Datum aus 'meta' ist verlässlich, aus 'text' eine Schätzung. Der Agent löscht die Datei nach dem Erstellen der Wochendatei.",
        "bekannte_links_uebersprungen": len(bekannt),
        "quellen": ergebnisse,
    }
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    gesamt = sum(e["anzahl"] for e in ergebnisse)
    print(f"{ok}/{len(ergebnisse)} Quellen mit Einträgen, {gesamt} Einträge gesamt -> {ziel}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
