"""Prüft daten/erp_verzeichnis.json auf Fehler und Unstimmigkeiten.

    python datencheck.py            # nur prüfen
    python datencheck.py --fix      # Zähler (meta.anzahl, anzahl_pruefpunkte) automatisch korrigieren
    python datencheck.py --offen    # zusätzlich alle «Prüfen»-Felder als Aufgabenliste ausgeben

Exit-Code 1 bei Fehlern (wird auch vom Build und von GitHub Actions verwendet).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from erpverzeichnis.data import (AUFWAND, BETRIEB_WERTE, BRANCHEN_WERTE, DATEN_DATEI, GROESSE_KEYS, KOSTEN, MODUL_FELDER,
                                 SCHWEIZ, SCHWEIZ_WERT, SEGMENTE, SKALA_WERT, datenort_key, ist_offen, liste)

DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")  # <anbieter>-<produkt>
PRUEFZYKLUS_TAGE = 90
JA_NEIN = re.compile(r"^(Ja|Nein|Prüfen)(\b|\s|$)")
# Felder mit festen Werten (optional mit Zusatz in Klammern)
STUFEN = {"kosten_stufe": set(KOSTEN) | {"Prüfen"}, "einfuehrung_aufwand": set(AUFWAND) | {"Prüfen"}}
PFLICHT_TEXT = ("name", "anbieter", "segment", "geeignet_fuer", "hinweise_fallstricke", "quellen")


def zaehle_pruefpunkte(e: dict) -> int:
    return sum(1 for v in e.values() if ist_offen(v))


def pruefen(path: Path, fix: bool = False, offen: bool = False, ausgabe=print) -> bool:
    """Gibt True zurück, wenn keine Fehler gefunden wurden."""
    try:
        with open(path, encoding="utf-8") as f:
            roh = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        ausgabe(f"FEHLER   Daten nicht lesbar: {exc}")
        return False

    fehler, warnungen = [], []
    meta = roh.get("meta") or {}
    eintraege = roh.get("eintraege")
    if not isinstance(eintraege, list):
        ausgabe("FEHLER   'eintraege' fehlt oder ist keine Liste.")
        return False
    felder = list((meta.get("felder") or {}).keys())
    if not felder:
        fehler.append("meta.felder fehlt – darin stehen die Feldnamen und Beschriftungen.")
    for f in MODUL_FELDER + [k for k, *_ in SCHWEIZ]:
        if felder and f not in felder:
            fehler.append(f"meta.felder: Feld '{f}' fehlt (wird im Code verwendet).")
    if not DATUM.match(str(meta.get("stand", ""))):
        fehler.append("meta.stand muss ein Datum im Format JJJJ-MM-TT sein.")

    for i, n in Counter(e.get("id") for e in eintraege).items():
        if n > 1:
            fehler.append(f"ID doppelt: {i} ({n}x)")

    heute = date.today()
    korrigiert = 0
    for idx, e in enumerate(eintraege):
        tid = e.get("id") or f"#{idx}"
        fehlend = [k for k in felder if k not in e]
        extra = [k for k in e if felder and k not in felder]
        if fehlend:
            fehler.append(f"{tid}: Felder fehlen: {', '.join(fehlend)}")
        if extra:
            warnungen.append(f"{tid}: unbekannte Felder (werden nicht angezeigt): {', '.join(extra)}")
        if not ID.match(str(e.get("id", ""))):
            fehler.append(f"{tid}: ID im Format <anbieter>-<produkt>, nur Kleinbuchstaben, Ziffern und Bindestriche")
        for k in PFLICHT_TEXT:
            if not str(e.get(k, "")).strip():
                fehler.append(f"{tid}: {k} ist leer")

        if e.get("segment") not in SEGMENTE:
            fehler.append(f"{tid}: segment '{e.get('segment')}' – erlaubt: {', '.join(SEGMENTE)}")
        for feld, erlaubt in (("zielgroesse_ma", GROESSE_KEYS), ("branchen_fokus", list(BRANCHEN_WERTE)),
                              ("betrieb", BETRIEB_WERTE)):
            wert = str(e.get(feld, ""))
            if ist_offen(wert):
                continue
            werte = liste(wert)
            falsch = [w for w in werte if w not in erlaubt]
            if not werte or falsch:
                fehler.append(f"{tid}: {feld} '{wert}' – kommagetrennt aus: {', '.join(erlaubt)} (oder «Prüfen – …»)")
        for feld in MODUL_FELDER:
            if feld in e and not SKALA_WERT.match(str(e[feld])):
                fehler.append(f"{tid}: {feld} '{e[feld]}' – erlaubt: Voll, Modul, Basis, Partner, Nein, Prüfen (optional mit Zusatz)")
        for feld, *_ in SCHWEIZ:
            if feld in e and not SCHWEIZ_WERT.match(str(e[feld])):
                fehler.append(f"{tid}: {feld} '{e[feld]}' – beginnt mit Ja, Nein, Teilweise, Modul, Partner oder Prüfen")
        if not JA_NEIN.match(str(e.get("us_cloud_act", ""))):
            fehler.append(f"{tid}: us_cloud_act '{e.get('us_cloud_act')}' – beginnt mit Ja, Nein oder Prüfen")
        for feld, erlaubt in STUFEN.items():
            kopf = re.split(r"\s+[–(]", str(e.get(feld, "")), maxsplit=1)[0].strip()
            if kopf not in erlaubt:
                fehler.append(f"{tid}: {feld} '{e.get(feld)}' – erlaubt: {', '.join(sorted(erlaubt))}")
        if datenort_key(e.get("datenort", "")) == "offen" and not ist_offen(e.get("datenort")):
            fehler.append(f"{tid}: datenort beginnt mit Schweiz, EU/EWR, Europa, Wählbar, Eigener Server, USA, Weltweit oder Prüfen")

        # Plausibilität
        if str(e.get("lohn", "")).startswith("Nein") and str(e.get("swissdec", "")).startswith("Ja"):
            warnungen.append(f"{tid}: lohn ist 'Nein', aber swissdec beginnt mit 'Ja'")
        if "On-Prem" in liste(str(e.get("betrieb", ""))) and str(e.get("datenort", "")).startswith("USA"):
            warnungen.append(f"{tid}: On-Prem möglich, aber datenort beginnt mit 'USA' – Wählbar?")

        stand = str(e.get("stand", ""))
        if not DATUM.match(stand):
            fehler.append(f"{tid}: stand '{stand}' muss JJJJ-MM-TT sein")
        else:
            alter = (heute - date.fromisoformat(stand)).days
            if alter > PRUEFZYKLUS_TAGE:
                warnungen.append(f"{tid}: zuletzt geprüft vor {alter} Tagen (Prüfzyklus {PRUEFZYKLUS_TAGE} Tage)")
        for q in [x.strip() for x in str(e.get("quellen", "")).split("|") if x.strip()]:
            if not q.startswith(("http://", "https://")):
                fehler.append(f"{tid}: Quelle ist keine URL: {q}")
        if e.get("website") and not str(e["website"]).startswith("https://") and not ist_offen(e["website"]):
            warnungen.append(f"{tid}: website sollte mit https:// beginnen")

        soll = zaehle_pruefpunkte(e)
        if e.get("anzahl_pruefpunkte") != soll:
            if fix:
                e["anzahl_pruefpunkte"] = soll
                korrigiert += 1
            else:
                warnungen.append(f"{tid}: anzahl_pruefpunkte={e.get('anzahl_pruefpunkte')}, gezählt {soll} (mit --fix korrigieren)")

    if meta.get("anzahl") != len(eintraege):
        if fix:
            meta["anzahl"] = len(eintraege)
            korrigiert += 1
        else:
            warnungen.append(f"meta.anzahl={meta.get('anzahl')}, tatsächlich {len(eintraege)} (mit --fix korrigieren)")

    if fix and korrigiert and not fehler:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(roh, f, ensure_ascii=False, indent=2)
            f.write("\n")
        ausgabe(f"{korrigiert} Zähler korrigiert und gespeichert.")

    for w in warnungen:
        ausgabe(f"WARNUNG  {w}")
    for x in fehler:
        ausgabe(f"FEHLER   {x}")

    if offen:
        ausgabe("\nOffene Prüfpunkte (Aufgabenliste):")
        for e in eintraege:
            punkte = [(k, v) for k, v in e.items() if ist_offen(v)]
            if punkte:
                ausgabe(f"\n  {e.get('id')} ({len(punkte)})")
                for k, v in punkte:
                    ausgabe(f"    - {k}: {v}")

    offen_total = sum(zaehle_pruefpunkte(e) for e in eintraege)
    seg = Counter(e.get("segment") for e in eintraege)
    ausgabe("")
    ausgabe(f"{len(eintraege)} Einträge · Stand {meta.get('stand')} · {offen_total} offene Prüfpunkte")
    ausgabe("Segmente: " + ", ".join(f"{k}: {v}" for k, v in seg.most_common()))
    if fehler:
        ausgabe(f"{len(fehler)} Fehler gefunden – bitte korrigieren.")
        return False
    ausgabe(f"OK – keine Fehler ({len(warnungen)} Warnungen).")
    return True


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Prüft die JSON-Daten des ERP-Verzeichnisses.")
    parser.add_argument("--fix", action="store_true", help="meta.anzahl und anzahl_pruefpunkte neu berechnen und speichern")
    parser.add_argument("--offen", action="store_true", help="alle «Prüfen»-Felder als Aufgabenliste ausgeben")
    parser.add_argument("--datei", default=str(DATEN_DATEI))
    args = parser.parse_args()
    return 0 if pruefen(Path(args.datei), fix=args.fix, offen=args.offen) else 1


if __name__ == "__main__":
    sys.exit(main())
