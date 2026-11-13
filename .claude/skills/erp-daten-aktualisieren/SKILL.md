---
name: erp-daten-aktualisieren
description: Aktualisiert die Daten des ERP-Verzeichnisses (daten/erp_verzeichnis.json) – neue ERP- oder Buchhaltungslösungen erfassen, Modul-Matrix, Schweiz-Funktionen, Preise und Datenschutz nachführen, offene Prüfpunkte klären, Stand-Datum setzen und die Daten anschliessend validieren. Verwenden, wenn der Nutzer Lösungen, Anbieter, Module, Preise oder die Marktanalyse im Verzeichnis aktualisieren will.
---

# ERP-Verzeichnis-Daten aktualisieren

Die Website ist statisch (GitHub Pages). `build.py` erzeugt sie aus **nur** zwei Quellen:
`daten/erp_verzeichnis.json` und `daten/Marktanalyse*.md`. Es gibt keine Datenbank und keinen Server.
Lokale Vorschau mit automatischem Neubau: `.venv\Scripts\python build.py --serve`.
Online wird die Seite nach einem Push auf `main` per GitHub Actions neu gebaut – Datenfehler brechen den Build ab.

## Ablauf

1. **Verstehen, was sich ändert.** Nach der Quelle fragen, falls keine genannt ist.
   Quellenhierarchie: *Zertifizierungslisten (Swissdec, eBill, bLink) > Produktdoku / Funktionsliste / Preisseite
   des Anbieters > Partner-Unterlagen > Fachartikel > Bewertungsportale* (Portale nur zum Finden, nie als Beleg).
2. **Recherche in Paketen** von 8–10 Lösungen pro Segment; gerne parallel mit Subagenten. Nach jedem Paket validieren.
3. **Datei bearbeiten.** Einzelne Einträge mit dem Edit-Tool ändern. Für viele Änderungen ein kurzes Python-Skript
   im Scratchpad schreiben, das die JSON lädt, ändert und mit `json.dump(..., ensure_ascii=False, indent=2)` zurückschreibt.
4. **Stand setzen.** Bei jedem geänderten oder geprüften Eintrag `stand` = heutiges Datum (JJJJ-MM-TT); bei grösseren
   Updates auch `meta.stand`. Sobald die Recherche abgeschlossen ist, `meta.status` leeren.
5. **Validieren:**
   ```
   .venv\Scripts\python datencheck.py --fix
   .venv\Scripts\python datencheck.py --offen     # Aufgabenliste aller «Prüfen»-Felder
   .venv\Scripts\python build.py
   ```
   FEHLER beheben, WARNUNGEN melden (z.B. Einträge älter als 90 Tage).
6. **Kurz zusammenfassen**, was geändert wurde (IDs, Felder, alt → neu).

## Regeln

- **IDs nie ändern** – sie sind URLs (`/erp/<id>/`). Format `<anbieter>-<produkt>`, nur `a-z0-9-`.
- **Nie raten.** Unbekanntes als `Prüfen – <was genau>` erfassen; erscheint als «noch offen».
- **Nie aufwerten.** «Lager» kann vollwertig oder nur eine Artikelliste sein → im Zweifel `Basis` oder `Prüfen`.
  «Integriert» heisst oft «über Partner» → `Partner`.
- Preise «auf Anfrage» als solche erfassen; Richtwerte nur mit Quelle.
- Keine Texte von Anbietern kopieren – Funktionen in eigenen Worten. Deutsch (Schweiz), «ss» statt «ß».
- Keine Rangliste «bestes ERP».

## Datenformat

Jeder Eintrag hat **genau** die Felder aus `meta.felder` (Strings, ausser `anzahl_pruefpunkte`).
Neue Felder nur zusammen mit `meta.felder` und einer Zuordnung in `erpverzeichnis/data.py` einführen.

| Feld | Regeln |
| --- | --- |
| `segment` | `Buchhaltung`, `KMU-ERP`, `Mittelstand-ERP`, `Gross-ERP`, `Branchenlösung` |
| `zielgroesse_ma` | kommagetrennt aus `1-10`, `10-50`, `50-250`, `250+` |
| `branchen_fokus` | kommagetrennt aus `Branchenneutral`, `Dienstleistung`, `Handel`, `Produktion`, `Bau/Handwerk`, `Non-Profit/Verwaltung` |
| Module (`fibu` … `ki_funktionen`, 28 Felder) | `Voll`, `Modul`, `Basis`, `Partner`, `Nein`, `Prüfen`, optional mit Zusatz: `Voll (ab Paket Optima)` |
| Schweiz (`swissdec`, `mwst_ch`, `qr_rechnung`, `ebill`, `bank_iso20022`, `bankanbindung`, `gebuev_archiv`, `rechnungslegung`, `treuhaender_zugang`) | beginnt mit `Ja`, `Nein`, `Teilweise`, `Modul`, `Partner` oder `Prüfen` |
| `betrieb` | kommagetrennt aus `Cloud`, `Hosted`, `Hybrid`, `On-Prem` |
| `kosten_stufe` | `Tief`, `Mittel`, `Hoch`, `Sehr hoch`, `Prüfen` (Definition in den Grundlagen) |
| `einfuehrung_aufwand` | `Gering`, `Mittel`, `Hoch`, `Prüfen` |
| `preis_einstieg` | mit Bezugsgrösse: «ab CHF 45/Monat für 1 Nutzer»; sonst «Auf Anfrage» |
| `datenort` | beginnt mit `Schweiz`, `EU/EWR`, `Europa`, `Wählbar`, `Eigener Server`, `USA`, `Weltweit` oder `Prüfen` |
| `us_cloud_act` | beginnt mit `Ja`, `Nein` oder `Prüfen` |
| `hinweise_fallstricke` | wichtigster Text («Darauf sollten Sie achten»): kurz, konkret, verständlich |
| `geeignet_fuer` | ein Satz |
| `quellen` | URLs, getrennt mit ` | ` |
| `anzahl_pruefpunkte` | nicht von Hand – `datencheck --fix` |

## Marktanalyse

`daten/Marktanalyse ERP Schweiz 2026.md`: Links `[Name](tool:<id>)` und `[Text](seite:verzeichnis|grundlagen|berater|vergleich)`.
Platzhalter: `{{ anzahl }}`, `{{ anzahl_swissdec }}`, `{{ anzahl_cloud }}`, `{{ anzahl_onprem }}`, `{{ anzahl_daten_ch }}`,
`{{ anzahl_cloud_act }}`, `{{ anzahl_buchhaltung }}`, `{{ anzahl_kmu }}`, `{{ anzahl_mittelstand }}`, `{{ anzahl_gross }}`,
`{{ anzahl_branche }}`, `{{ anzahl_pruefpunkte }}`, `{{ stand }}`. Unbekannte Platzhalter oder IDs brechen den Build ab.
