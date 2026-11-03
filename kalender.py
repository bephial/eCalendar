#!/usr/bin/env python3
"""Tageskalender-PDF für E-Ink-Reader (rein schwarz-weiß, eine Seite pro Tag).

Aufruf:
    python3 kalender.py            -> fragt nach dem Jahr
    python3 kalender.py 2027       -> erzeugt kalender_2027.pdf
    python3 kalender.py 2027 --format remarkable --start 7 --ende 21
    python3 kalender.py 2027 --bundesland BW            # + gesetzliche Feiertage
    python3 kalender.py 2027 --bundesland BW --ferien   # + Schulferien

Benötigt: pip install reportlab holidays
Schulferien werden einmalig von openholidaysapi.org geladen und danach lokal
zwischengespeichert (Ordner ~/.cache/kalender_ferien).
"""
import argparse
import calendar
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

from reportlab.lib.colors import black, white
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag",
              "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

# Seitengrößen (Breite, Höhe) – auf gängige Reader abgestimmt
FORMATE = {
    "a5": (148 * mm, 210 * mm),
    "a4": (210 * mm, 297 * mm),
    "remarkable": (157 * mm, 210 * mm),   # reMarkable 2 (10,3")
    "boox": (158 * mm, 210 * mm),         # Boox Note/Tab (10,3")
    "7zoll": (95 * mm, 127 * mm),         # Kobo Libra, Boox Page, ...
    "6zoll": (90 * mm, 120 * mm),         # Kindle, Kobo Clara, ...
    "scribe3": (168 * mm, 224 * mm),      # Kindle Scribe 3
}

BUNDESLAENDER = {
    "BW": "Baden-Württemberg", "BY": "Bayern", "BE": "Berlin",
    "BB": "Brandenburg", "HB": "Bremen", "HH": "Hamburg", "HE": "Hessen",
    "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz", "SL": "Saarland",
    "SN": "Sachsen", "ST": "Sachsen-Anhalt", "SH": "Schleswig-Holstein",
    "TH": "Thüringen",
}


def feiertage_laden(jahr, land):
    """Gesetzliche Feiertage {date: name} für das Bundesland."""
    try:
        import holidays
    except ImportError:
        sys.exit("Für Feiertage wird das Paket 'holidays' benötigt: "
                 "pip install holidays")
    return dict(holidays.Germany(subdiv=land, years=jahr, language="de"))


def ferien_laden(jahr, land):
    """Schulferien {date: [namen]} über die OpenHolidays-API (mit Cache).

    Gibt bei Netzwerkproblemen eine Warnung aus und liefert {} zurück.
    """
    cache_dir = os.path.expanduser("~/.cache/kalender_ferien")
    cache = os.path.join(cache_dir, f"{land}_{jahr}.json")
    daten = None
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            daten = json.load(f)
    else:
        # ab Dezember des Vorjahres, damit Weihnachtsferien erfasst werden
        query = urllib.parse.urlencode({
            "countryIsoCode": "DE", "subdivisionCode": f"DE-{land}",
            "languageIsoCode": "DE",
            "validFrom": f"{jahr - 1}-12-01", "validTo": f"{jahr}-12-31"})
        url = f"https://openholidaysapi.org/SchoolHolidays?{query}"
        try:
            req = urllib.request.Request(url, headers={"accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                daten = json.load(r)
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(daten, f, ensure_ascii=False)
        except Exception as e:  # Netzwerk, JSON, ...
            print(f"WARNUNG: Schulferien konnten nicht geladen werden ({e}). "
                  "Kalender wird ohne Ferien erstellt.", file=sys.stderr)
            return {}
    return ferien_aus_api(daten, jahr)


def ferien_aus_api(daten, jahr):
    ergebnis = {}
    for eintrag in daten:
        namen = eintrag.get("name", [])
        name = next((n["text"] for n in namen if n.get("language") == "DE"),
                    namen[0]["text"] if namen else "Ferien")
        d = datetime.date.fromisoformat(eintrag["startDate"])
        ende = datetime.date.fromisoformat(eintrag["endDate"])
        while d <= ende:
            if d.year == jahr:
                ergebnis.setdefault(d, []).append(name)
            d += datetime.timedelta(days=1)
    return ergebnis


def passende_schrift(c, text, schrift, groesse, max_breite):
    while groesse > 5 and c.stringWidth(text, schrift, groesse) > max_breite:
        groesse -= 0.5
    return groesse


SCHWARZ = black  # nur reines Schwarz auf Weiß


def zeichne_tag(c, tag, W, H, start, ende, feiertag=None, ferien=None):
    m = W * 0.06                      # Seitenrand
    inhalt_b = W - 2 * m

    # ---------- Kopfzeile ----------
    kopf_h = H * 0.10
    y_kopf_unten = H - m - kopf_h

    c.setFillColor(SCHWARZ)
    c.setStrokeColor(SCHWARZ)

    # Große Tageszahl
    gross = kopf_h * 0.95
    c.setFont("Helvetica-Bold", gross)
    c.drawString(m, y_kopf_unten + kopf_h * 0.08, f"{tag.day}")
    zahl_b = c.stringWidth(f"{tag.day}", "Helvetica-Bold", gross)

    # Wochentag + Monat/Jahr neben der Zahl
    x_text = m + zahl_b + W * 0.03
    c.setFont("Helvetica-Bold", kopf_h * 0.38)
    c.drawString(x_text, y_kopf_unten + kopf_h * 0.52, WOCHENTAGE[tag.weekday()])
    c.setFont("Helvetica", kopf_h * 0.27)
    c.drawString(x_text, y_kopf_unten + kopf_h * 0.14,
                 f"{MONATE[tag.month - 1]} {tag.year}")

    # Kalenderwoche + Tag im Jahr rechts oben
    kw = tag.isocalendar()[1]
    c.setFont("Helvetica", kopf_h * 0.16)
    c.drawRightString(W - m, y_kopf_unten + kopf_h * 0.84,
                      f"KW {kw}  ·  Tag {tag.timetuple().tm_yday}")

    # Feiertag: schwarzes Feld mit weißer Schrift; Ferien: Rahmen
    max_b = W - m - (x_text + c.stringWidth(WOCHENTAGE[tag.weekday()],
                     "Helvetica-Bold", kopf_h * 0.38)) - W * 0.03
    lab_h = kopf_h * 0.21
    pad = lab_h * 0.28
    y_lab = y_kopf_unten + kopf_h * 0.50
    for text, gefuellt in ((feiertag, True), (ferien, False)):
        if not text:
            continue
        gr = passende_schrift(c, text, "Helvetica-Bold", lab_h * 0.72, max_b - 2 * pad)
        tb = c.stringWidth(text, "Helvetica-Bold", gr)
        x0 = W - m - tb - 2 * pad
        c.setLineWidth(0.9)
        c.rect(x0, y_lab, tb + 2 * pad, lab_h, stroke=1, fill=1 if gefuellt else 0)
        c.setFillColor(white if gefuellt else SCHWARZ)
        c.setFont("Helvetica-Bold", gr)
        c.drawString(x0 + pad, y_lab + (lab_h - gr) / 2 + gr * 0.15, text)
        c.setFillColor(SCHWARZ)
        y_lab -= lab_h + pad

    c.setLineWidth(1.6)
    c.line(m, y_kopf_unten, W - m, y_kopf_unten)

    # ---------- Spalten ----------
    gap = W * 0.04
    zeit_b = inhalt_b * 0.60
    x_zeit = m
    x_rechts = m + zeit_b + gap
    rechts_b = W - m - x_rechts

    y_oben = y_kopf_unten - H * 0.015
    y_unten = m

    # ---------- Timeline links ----------
    stunden = ende - start
    zeile_h = (y_oben - y_unten) / stunden
    label_b = W * 0.075
    c.setFont("Helvetica-Bold", min(zeile_h * 0.4, 11))
    for i in range(stunden + 1):
        y = y_oben - i * zeile_h
        c.setLineWidth(0.8)
        c.setDash()
        c.line(x_zeit, y, x_zeit + zeit_b, y)
        if i < stunden:
            c.drawString(x_zeit, y - zeile_h * 0.38, f"{start + i:02d}")
            # halbe Stunde: fein gestrichelt
            c.setLineWidth(0.35)
            c.setDash(1.5, 2.5)
            c.line(x_zeit + label_b, y - zeile_h / 2,
                   x_zeit + zeit_b, y - zeile_h / 2)
            c.setDash()
    # senkrechte Trennlinie zwischen Stunden-Label und Terminfläche
    c.setLineWidth(0.8)
    c.line(x_zeit + label_b, y_oben, x_zeit + label_b, y_oben - stunden * zeile_h)

    # ---------- To-Do rechts oben ----------
    titel_h = H * 0.03
    c.setFont("Helvetica-Bold", titel_h * 0.8)
    c.drawString(x_rechts, y_oben - titel_h * 0.8, "To-Do")
    c.setLineWidth(1.2)
    c.line(x_rechts, y_oben - titel_h, x_rechts + rechts_b, y_oben - titel_h)

    todo_zeilen = 9
    todo_h = (y_oben - y_unten) * 0.52
    z_h = (todo_h - titel_h) / todo_zeilen
    box = min(z_h * 0.55, 4.2 * mm)
    for i in range(todo_zeilen):
        y = y_oben - titel_h - (i + 1) * z_h
        c.setLineWidth(0.4)
        c.line(x_rechts, y, x_rechts + rechts_b, y)
        c.setLineWidth(0.9)
        c.rect(x_rechts, y + (z_h - box) / 2 - 0.5, box, box, stroke=1, fill=0)
        # Linie zum Schreiben beginnt rechts der Box
    y_todo_unten = y_oben - todo_h

    # ---------- Notizen rechts unten (Punktraster) ----------
    y_notiz_oben = y_todo_unten - H * 0.025
    c.setFont("Helvetica-Bold", titel_h * 0.8)
    c.drawString(x_rechts, y_notiz_oben - titel_h * 0.8, "Notizen")
    c.setLineWidth(1.2)
    c.line(x_rechts, y_notiz_oben - titel_h, x_rechts + rechts_b,
           y_notiz_oben - titel_h)

    raster = 6 * mm
    c.setLineWidth(0.9)
    c.setLineCap(1)  # runde Punkte
    y = y_notiz_oben - titel_h - raster
    while y >= y_unten:
        x = x_rechts + raster / 2
        while x <= x_rechts + rechts_b:
            c.line(x, y, x, y)
            x += raster
        y -= raster
    c.setLineCap(0)


def erzeuge_kalender(jahr, dateiname, format_name, start, ende,
                     feiertage=None, ferien=None):
    feiertage = feiertage or {}
    ferien = ferien or {}
    W, H = FORMATE[format_name]
    c = canvas.Canvas(dateiname, pagesize=(W, H))
    c.setTitle(f"Tageskalender {jahr}")
    c.setAuthor("kalender.py")

    tag = datetime.date(jahr, 1, 1)
    letzter = datetime.date(jahr, 12, 31)
    aktueller_monat = 0
    seiten = 0
    while tag <= letzter:
        key = tag.isoformat()
        c.bookmarkPage(key)
        # Lesezeichen: Monate als Ebene 0, Tage als Ebene 1
        if tag.month != aktueller_monat:
            c.addOutlineEntry(f"{MONATE[tag.month - 1]} {jahr}", key,
                              level=0, closed=True)
            aktueller_monat = tag.month
        c.addOutlineEntry(
            f"{WOCHENTAGE[tag.weekday()][:2]}, {tag.day}. {MONATE[tag.month - 1]}",
            key, level=1)
        ft = feiertage.get(tag)
        fe = ", ".join(ferien[tag]) if tag in ferien else None
        zeichne_tag(c, tag, W, H, start, ende, ft, fe)
        c.showPage()
        seiten += 1
        tag += datetime.timedelta(days=1)

    c.save()
    return seiten


def main():
    p = argparse.ArgumentParser(description="Tageskalender-PDF für E-Ink-Reader")
    p.add_argument("jahr", nargs="?", type=int, help="Jahr, z. B. 2027")
    p.add_argument("--format", choices=sorted(FORMATE), default="remarkable",
                   help="Seitengröße (Standard: remarkable)")
    p.add_argument("--start", type=int, default=6, help="erste Stunde (Standard 6)")
    p.add_argument("--ende", type=int, default=22, help="letzte Stunde (Standard 22)")
    p.add_argument("--bundesland", metavar="KÜRZEL",
                   help="Bundesland für Feiertage: " + ", ".join(BUNDESLAENDER))
    p.add_argument("--ferien", action="store_true",
                   help="Schulferien des Bundeslands anzeigen (braucht --bundesland)")
    p.add_argument("--out", help="Dateiname (Standard: kalender_<jahr>.pdf)")
    a = p.parse_args()

    jahr = a.jahr
    if jahr is None:
        jahr = int(input("Für welches Jahr soll der Kalender erstellt werden? "))
    if not 0 <= a.start < a.ende <= 24:
        p.error("Es muss gelten: 0 <= start < ende <= 24")

    land = a.bundesland.upper() if a.bundesland else None
    if land and land not in BUNDESLAENDER:
        p.error(f"Unbekanntes Bundesland '{a.bundesland}'. Erlaubt: "
                + ", ".join(BUNDESLAENDER))
    if a.ferien and not land:
        p.error("--ferien braucht --bundesland, z. B. --bundesland BW")

    feiertage = feiertage_laden(jahr, land) if land else {}
    ferien = ferien_laden(jahr, land) if (land and a.ferien) else {}
    if land:
        print(f"{BUNDESLAENDER[land]}: {len(feiertage)} Feiertage"
              + (f", {len(ferien)} Ferientage" if a.ferien else ""))

    out = a.out or f"kalender_{jahr}.pdf"
    n = erzeuge_kalender(jahr, out, a.format, a.start, a.ende, feiertage, ferien)
    print(f"{out} erstellt: {n} Seiten ({'Schaltjahr' if calendar.isleap(jahr) else 'kein Schaltjahr'}).")


if __name__ == "__main__":
    main()
