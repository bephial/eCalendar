# E-Ink Tageskalender (PDF)

Python-Skript, das für ein beliebiges Jahr einen **Tageskalender als PDF** erzeugt: eine Seite pro Tag (365 bzw. 366 Seiten), rein **schwarz-weiß** und damit für monochrome E-Ink-Reader und -Notizgeräte geeignet.

## Aufbau einer Seite

- **Kopfzeile:** große Tageszahl, Wochentag, Monat und Jahr, rechts Kalenderwoche und Tag im Jahr
- **Timeline links:** Stundenlinien mit gestrichelten Halbstundenlinien
- **To-Do-Liste rechts oben:** 9 Zeilen mit Kästchen zum Abhaken
- **Notizfeld rechts unten:** Punktraster
- **Feiertage und Schulferien** (optional): in der Kopfzeile, Feiertag als schwarzes Feld mit weißer Schrift, Ferien als Rahmen
- **Lesezeichen im PDF:** je Monat und je Tag, damit man auf dem Reader direkt zu einem Datum springen kann

## Installation

```bash
pip install reportlab holidays
```

`holidays` wird nur benötigt, wenn Feiertage angezeigt werden sollen (`--bundesland`).

## Verwendung

```bash
python3 kalender.py                  # fragt nach dem Jahr
python3 kalender.py 2027             # erzeugt kalender_2027.pdf
python3 kalender.py 2027 --bundesland BW           # mit Feiertagen
python3 kalender.py 2027 --bundesland BW --ferien  # mit Feiertagen und Schulferien
python3 kalender.py 2027 --format 6zoll --start 7 --ende 21 --out mein_kalender.pdf
```

## Optionen

| Option | Beschreibung | Standard |
|---|---|---|
| `jahr` | Jahr, für das der Kalender erzeugt wird. Ohne Angabe fragt das Skript danach. | Abfrage |
| `--format` | Seitengröße, siehe unten | `remarkable` |
| `--start` | Erste Stunde der Timeline (0–23) | `6` |
| `--ende` | Ende der Timeline (bis 24); es muss `start < ende` gelten | `22` |
| `--bundesland KÜRZEL` | Bundesland für gesetzliche Feiertage, siehe unten | keins |
| `--ferien` | Zeigt zusätzlich die Schulferien des Bundeslands an. Benötigt `--bundesland`. | aus |
| `--out DATEI` | Name der Ausgabedatei | `kalender_<jahr>.pdf` |
| `-h`, `--help` | Hilfe anzeigen | |

### Seitenformate (`--format`)

| Wert | Größe (mm) | Gedacht für |
|---|---|---|
| `remarkable` | 157 × 210 | reMarkable 2 (10,3") |
| `boox` | 158 × 210 | Boox Note/Tab (10,3") |
| `a5` | 148 × 210 | A5 |
| `a4` | 210 × 297 | A4 |
| `7zoll` | 95 × 127 | Kobo Libra, Boox Page u. ä. |
| `6zoll` | 90 × 120 | Kindle, Kobo Clara u. ä. |
| `scribe3` | 168 × 224 | Kindle Scribe 3 |

Weicht die Darstellung auf deinem Gerät ab (zu klein oder mit Rand), passe die Größen im Dictionary `FORMATE` in `kalender.py` an.

### Bundesländer (`--bundesland`)

`BW` Baden-Württemberg · `BY` Bayern · `BE` Berlin · `BB` Brandenburg · `HB` Bremen · `HH` Hamburg · `HE` Hessen · `MV` Mecklenburg-Vorpommern · `NI` Niedersachsen · `NW` Nordrhein-Westfalen · `RP` Rheinland-Pfalz · `SL` Saarland · `SN` Sachsen · `ST` Sachsen-Anhalt · `SH` Schleswig-Holstein · `TH` Thüringen

Groß- und Kleinschreibung spielen keine Rolle.

## Hinweise zu Feiertagen und Schulferien

- **Feiertage** werden mit dem Python-Paket [`holidays`](https://pypi.org/project/holidays/) berechnet und funktionieren offline.
- **Schulferien** lädt das Skript beim ersten Lauf von der [OpenHolidays API](https://www.openholidaysapi.org) und speichert sie im Ordner `~/.cache/kalender_ferien`. Danach funktioniert es auch offline. Ist die Schnittstelle nicht erreichbar, gibt das Skript eine Warnung aus und erstellt den Kalender ohne Ferien.
- Ferien erscheinen nur für Tage innerhalb des gewählten Jahres. Weihnachtsferien, die im Dezember des Vorjahres beginnen, sind also ab dem 1. Januar eingetragen.
- Ändern sich Ferientermine nachträglich, lösche die zugehörige Datei im Cache-Ordner, damit sie neu geladen wird.
- Die Ferientermine stammen aus einer Community-Datenbank (Lizenz ODbL). Prüfe sie bei wichtigen Terminen gegen die Angaben des zuständigen Kultusministeriums.

## Beispiele

```bash
# reMarkable-Kalender 2027 für Baden-Württemberg mit Ferien
python3 kalender.py 2027 --bundesland BW --ferien

# Kindle, Tagesplan nur von 8 bis 20 Uhr
python3 kalender.py 2027 --format 6zoll --start 8 --ende 20

# Nur Wochenplanung am Vormittag, ohne Feiertage
python3 kalender.py 2028 --start 6 --ende 13 --out vormittag_2028.pdf
```
----
Unter GPL-3.0-Lizenz
