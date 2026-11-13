"""Lädt das ERP-Verzeichnis aus der JSON-Datei und übersetzt die Rohwerte in Alltagssprache.

Enthält ausserdem die Filter (Verzeichnis) und die Empfehlungslogik (Berater). Die Empfehlungslogik gibt es
zweimal: hier (für die Seite ohne JavaScript und die LinkedIn-Vorschau) und in static/app.js (für die
Modulauswahl im Browser). Wer die Punkte ändert, ändert beide Stellen – siehe Kommentar «PUNKTELOGIK».

Wird von build.py (statische Website) und datencheck.py verwendet.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROJEKT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJEKT / "daten"  # was die Website braucht; docs/ bleibt privat (nicht im Repo)
DATEN_DATEI = DOCS_DIR / "erp_verzeichnis.json"
ANALYSE_GLOB = "Marktanalyse*.md"

# ---------------------------------------------------------------------------
# Skala der Modul-Matrix
# ---------------------------------------------------------------------------

# Reihenfolge = Reihenfolge in der Legende
SKALA = {
    "voll": {"label": "Im Standard", "kurz": "Voll", "zeichen": "✓", "rang": 0, "punkte": 3, "ton": "gut",
             "satz": "im Standard enthalten", "erklaerung": "Im Grundpaket enthalten, ohne Aufpreis."},
    "modul": {"label": "Gegen Aufpreis", "kurz": "Modul", "zeichen": "+", "rang": 1, "punkte": 2, "ton": "mittel",
              "satz": "als Zusatzmodul gegen Aufpreis", "erklaerung": "Vom Anbieter selbst, aber als Zusatzmodul oder in einem teureren Paket."},
    "partner": {"label": "Über Partner", "kurz": "Partner", "zeichen": "↗", "rang": 2, "punkte": 1.5, "ton": "mittel",
                "satz": "nur über eine Partnerlösung", "erklaerung": "Nur mit einer Drittlösung, die angebunden wird – eigener Vertrag, eigene Kosten."},
    "basis": {"label": "Rudimentär", "kurz": "Basis", "zeichen": "◐", "rang": 3, "punkte": 1, "ton": "mittel",
              "satz": "nur in Grundzügen vorhanden", "erklaerung": "Vorhanden, aber nur in Grundzügen – z.B. eine Artikelliste statt einer Lagerverwaltung."},
    "nein": {"label": "Nicht vorhanden", "kurz": "Nein", "zeichen": "–", "rang": 5, "punkte": None, "ton": "schlecht",
             "satz": "nicht vorhanden", "erklaerung": "Gibt es nicht, auch nicht über Partner."},
    "pruefen": {"label": "Noch offen", "kurz": "Prüfen", "zeichen": "?", "rang": 4, "punkte": 0.5, "ton": "offen",
                "satz": "noch nicht belegt", "erklaerung": "Öffentlich nicht eindeutig dokumentiert – beim Anbieter nachfragen."},
}
for _k, _s in SKALA.items():
    _s.update(key=_k, zusatz="")
SKALA_WERT = re.compile(r"^(Voll|Modul|Basis|Partner|Nein|Prüfen)(\s|$)")


def skala(raw: str) -> dict:
    v = (raw or "").strip()
    m = SKALA_WERT.match(v)
    key = {"Voll": "voll", "Modul": "modul", "Basis": "basis", "Partner": "partner", "Nein": "nein"}.get(
        m.group(1) if m else "", "pruefen")
    zusatz = v[len(m.group(1)):].strip() if m else v
    zusatz = re.sub(r"^[–—-]\s*", "", zusatz)
    if zusatz.startswith("(") and zusatz.endswith(")"):
        zusatz = zusatz[1:-1]
    return {"key": key, **SKALA[key], "zusatz": zusatz, "raw": v}


# ---------------------------------------------------------------------------
# Modul-Matrix: Bereiche und Felder (Feld, kurze Erklärung für Laien)
# ---------------------------------------------------------------------------

BEREICHE = [
    {"id": "finanzen", "titel": "Finanzen", "icon": "coins", "felder": [
        ("fibu", "Hauptbuch, Bilanz und Erfolgsrechnung."),
        ("debitoren_kreditoren", "Offene Rechnungen von Kunden und an Lieferanten, Mahnwesen, Zahlungen."),
        ("anlagen", "Maschinen, Fahrzeuge, Mobiliar – mit Abschreibungen."),
        ("kostenrechnung", "Kostenstellen und Kostenträger: Was kostet welche Abteilung, welches Produkt?"),
        ("budget_planung", "Budget erstellen und mit den Ist-Zahlen vergleichen."),
        ("fremdwaehrung", "Buchungen in EUR, USD usw. mit Kursdifferenzen."),
        ("mehrmandanten_konsolidierung", "Mehrere Firmen im selben System, auf Wunsch zusammengefasst (Konzernabschluss)."),
    ]},
    {"id": "personal", "titel": "Personal", "icon": "users", "felder": [
        ("lohn", "Lohnabrechnung mit Sozialversicherungen und Quellensteuer."),
        ("zeiterfassung", "Arbeits- und Präsenzzeit erfassen."),
        ("spesen", "Spesen erfassen, Belege fotografieren, zurückzahlen."),
        ("hr_personaldossier", "Personalakte, Verträge, Absenzen, Ferien."),
    ]},
    {"id": "verkauf", "titel": "Verkauf & Kunden", "icon": "handshake", "felder": [
        ("offerten_auftraege", "Offerten, Auftragsbestätigungen, Lieferscheine, Rechnungen."),
        ("crm", "Kontakte, Verkaufschancen, Aktivitäten."),
        ("webshop_anbindung", "Bestellungen aus dem Onlineshop automatisch übernehmen."),
        ("service_wartung", "Serviceaufträge, Wartungsverträge, Einsatzplanung."),
        ("abo_wiederkehrend", "Abonnemente und wiederkehrende Rechnungen."),
    ]},
    {"id": "logistik", "titel": "Einkauf & Logistik", "icon": "box", "felder": [
        ("einkauf", "Bestellungen bei Lieferanten, Wareneingang."),
        ("lager", "Lagerbestände, Inventur, Mindestmengen."),
        ("seriennummern_chargen", "Einzelne Geräte oder Chargen rückverfolgen."),
        ("mehrlager_logistik", "Mehrere Lager oder Standorte, Lagerplätze, Kommissionierung."),
    ]},
    {"id": "produktion", "titel": "Produktion & Projekte", "icon": "factory", "felder": [
        ("produktion_pps", "Fertigungsaufträge planen und steuern (PPS)."),
        ("stuecklisten", "Aus welchen Teilen ein Produkt besteht."),
        ("projekte_leistungen", "Projekte führen, Stunden und Material darauf buchen und abrechnen."),
        ("ressourcenplanung", "Personal und Maschinen einplanen."),
    ]},
    {"id": "weiteres", "titel": "Weiteres", "icon": "spark", "felder": [
        ("dms_archiv", "Belege und Dokumente ablegen und wiederfinden."),
        ("reporting_bi", "Auswertungen, Dashboards, Kennzahlen."),
        ("mobile_app", "App für Handy oder Tablet."),
        ("ki_funktionen", "KI-Funktionen, z.B. Belege automatisch erkennen oder Texte vorschlagen."),
    ]},
]
MODUL_FELDER = [f for b in BEREICHE for f, _ in b["felder"]]
MODUL_HILFE = {f: h for b in BEREICHE for f, h in b["felder"]}

# Bedarf: Auswahl im Berater (Frage 3) und Filter «modul=» im Verzeichnis.
# Achtung: Die Schlüssel stehen in geteilten Links – nach der Veröffentlichung nicht mehr ändern.
BEDARF = [
    {"key": "lohn", "label": "Lohn", "hilfe": "Löhne abrechnen", "icon": "users", "felder": ["lohn"]},
    {"key": "lager", "label": "Lager", "hilfe": "Artikel und Bestände", "icon": "box", "felder": ["lager"]},
    {"key": "produktion", "label": "Produktion", "hilfe": "Stücklisten, Fertigung", "icon": "factory",
     "felder": ["produktion_pps", "stuecklisten"]},
    {"key": "projekte", "label": "Projekte & Zeit", "hilfe": "Stunden erfassen und abrechnen", "icon": "clock",
     "felder": ["projekte_leistungen", "zeiterfassung"]},
    {"key": "crm", "label": "CRM", "hilfe": "Kontakte und Verkaufschancen", "icon": "handshake", "felder": ["crm"]},
    {"key": "webshop", "label": "Webshop", "hilfe": "Onlineshop anbinden", "icon": "cart", "felder": ["webshop_anbindung"]},
    {"key": "mandanten", "label": "Mehrere Firmen", "hilfe": "Mehrere Mandanten, Konsolidierung", "icon": "layers",
     "felder": ["mehrmandanten_konsolidierung"]},
]
BEDARF_INFO = {b["key"]: b for b in BEDARF}

# ---------------------------------------------------------------------------
# Stammdaten: Segment, Grösse, Branche, Betrieb, Kosten
# ---------------------------------------------------------------------------

SEGMENTE = {
    "Buchhaltung": {"id": "buchhaltung", "label": "Buchhaltung", "icon": "coins",
                    "text": "Buchhaltung und Rechnungen, oft mit Lohn – für Kleinst- und Kleinbetriebe."},
    "KMU-ERP": {"id": "kmu", "label": "KMU-ERP", "icon": "layers",
                "text": "Ein System für Finanzen, Verkauf, Einkauf und Personal – für KMU mit etwa 10 bis 250 Mitarbeitenden."},
    "Mittelstand-ERP": {"id": "mittelstand", "label": "Mittelstand-ERP", "icon": "building",
                        "text": "Umfangreiches ERP für grössere KMU, oft mit Produktion und mehreren Standorten."},
    "Gross-ERP": {"id": "gross", "label": "Gross-ERP", "icon": "building",
                  "text": "ERP für Konzerne und grosse Unternehmen, international und mit vielen Gesellschaften."},
    "Branchenlösung": {"id": "branche", "label": "Branchenlösung", "icon": "brief",
                       "text": "Auf eine Branche zugeschnitten, z.B. Bau, Immobilien oder Dienstleister."},
}
SEGMENT_RANG = {k: i for i, k in enumerate(SEGMENTE)}

GROESSEN = [
    {"key": "1-10", "pfad": "1-10", "label": "1–10", "titel": "1–10 Mitarbeitende", "mit": "1–10 Mitarbeitenden", "hilfe": "Kleinstbetrieb, Start-up"},
    {"key": "10-50", "pfad": "10-50", "label": "10–50", "titel": "10–50 Mitarbeitende", "mit": "10–50 Mitarbeitenden", "hilfe": "Kleines KMU"},
    {"key": "50-250", "pfad": "50-250", "label": "50–250", "titel": "50–250 Mitarbeitende", "mit": "50–250 Mitarbeitenden", "hilfe": "Mittleres KMU"},
    {"key": "250+", "pfad": "250-plus", "label": "250+", "titel": "Über 250 Mitarbeitende", "mit": "über 250 Mitarbeitenden", "hilfe": "Grösseres Unternehmen"},
]
GROESSE_KEYS = [g["key"] for g in GROESSEN]
GROESSE_INFO = {g["key"]: g for g in GROESSEN}

# Werte im Feld branchen_fokus (kommagetrennt) -> Schlüssel im Berater
BRANCHEN = [
    {"key": "dienstleistung", "wert": "Dienstleistung", "label": "Dienstleistung", "hilfe": "Beratung, Agentur, Treuhand, IT", "icon": "brief"},
    {"key": "handel", "wert": "Handel", "label": "Handel", "hilfe": "Gross- und Detailhandel, Import", "icon": "cart"},
    {"key": "produktion", "wert": "Produktion", "label": "Produktion", "hilfe": "Fertigung, Maschinenbau, Lebensmittel", "icon": "factory"},
    {"key": "bau", "wert": "Bau/Handwerk", "label": "Bau & Handwerk", "hilfe": "Bau, Schreinerei, Haustechnik", "icon": "hammer"},
    {"key": "nonprofit", "wert": "Non-Profit/Verwaltung", "label": "Non-Profit & Verwaltung", "hilfe": "Verein, Stiftung, Gemeinde", "icon": "heart"},
    {"key": "andere", "wert": "", "label": "Andere Branche", "hilfe": "Keine der genannten", "icon": "spark"},
]
BRANCHE_INFO = {b["key"]: b for b in BRANCHEN}
BRANCHEN_WERTE = {b["wert"]: b["key"] for b in BRANCHEN if b["wert"]} | {"Branchenneutral": "neutral"}

BETRIEB_WERTE = ["Cloud", "Hosted", "Hybrid", "On-Prem"]
BETRIEB_TEXT = {"Cloud": "Cloud (Software als Dienst)", "Hosted": "Beim Partner gehostet", "Hybrid": "Cloud oder eigener Server",
                "On-Prem": "Eigener Server"}
# Berater Frage 4 / Filter «betrieb=»: welche Betriebsarten passen
BETRIEB_WAHL = {"cloud": {"Cloud", "Hosted", "Hybrid"}, "server": {"On-Prem", "Hybrid"}}

KOSTEN = {
    "Tief": {"rang": 0, "label": "Tief", "text": "Unter etwa CHF 100 pro Monat für einen kleinen Betrieb."},
    "Mittel": {"rang": 1, "label": "Mittel", "text": "Einige hundert Franken pro Monat oder eine Lizenz im tiefen fünfstelligen Bereich."},
    "Hoch": {"rang": 2, "label": "Hoch", "text": "Ab etwa CHF 1000 pro Monat oder Lizenzen und Einführung im fünf- bis sechsstelligen Bereich."},
    "Sehr hoch": {"rang": 3, "label": "Sehr hoch", "text": "Grossprojekt: Lizenzen und Einführung meist deutlich im sechsstelligen Bereich."},
}
AUFWAND = {
    "Gering": {"rang": 0, "label": "Gering", "text": "Selbst einrichten, in Tagen startklar."},
    "Mittel": {"rang": 1, "label": "Mittel", "text": "Einige Wochen, meist mit Unterstützung eines Partners."},
    "Hoch": {"rang": 2, "label": "Hoch", "text": "Einführungsprojekt über Monate, mit Partner."},
}

# Schweiz-Funktionen: Feld, Kurzname, Erklärung
SCHWEIZ = [
    ("swissdec", "Swissdec", "Zertifizierte Lohnmeldung an AHV, Unfallversicherung, Steuerämter und BFS."),
    ("mwst_ch", "MWST Schweiz", "Schweizer Mehrwertsteuer inkl. Saldosteuersatz und Abrechnung an die ESTV."),
    ("qr_rechnung", "QR-Rechnung", "Rechnungen mit Swiss QR Code erstellen und einlesen."),
    ("ebill", "eBill", "Rechnungen direkt ins E-Banking der Kunden senden."),
    ("bank_iso20022", "Zahlungen ISO 20022", "Zahlungsdateien (pain.001) und Kontoauszüge (camt.053/054)."),
    ("bankanbindung", "Bankanbindung", "Direkte Verbindung zur Bank (EBICS, bLink oder Schnittstelle der Bank)."),
    ("gebuev_archiv", "Archiv nach GeBüV", "Revisionssichere Aufbewahrung der Geschäftsbücher (10 Jahre)."),
    ("rechnungslegung", "Rechnungslegung", "Welche Standards unterstützt werden (OR, Swiss GAAP FER, IFRS)."),
    ("treuhaender_zugang", "Zugang für Treuhand", "Die Treuhänderin kann direkt im System arbeiten."),
]
SCHWEIZ_WERT = re.compile(r"^(Ja|Nein|Teilweise|Modul|Partner|Prüfen)(\b|\s|$)")

# Detailbereiche im Steckbrief (ausser Modul-Matrix und Schweiz): Feld -> kurze Erklärung
DETAIL_GRUPPEN = [
    {"id": "betrieb", "titel": "Betrieb & Kosten", "felder": [
        ("betrieb", "Wo die Software läuft."),
        ("preis_modell", "Wie abgerechnet wird."),
        ("preis_einstieg", "Öffentlich bekannter Einstiegspreis mit Bezugsgrösse."),
        ("kosten_stufe", "Unsere grobe Einordnung der laufenden Kosten."),
        ("einfuehrung", "Wer die Software einführt und wie lange es typischerweise dauert."),
        ("einfuehrung_aufwand", "Unsere grobe Einordnung des Einführungsaufwands."),
        ("vertragslaufzeit", "Mindestlaufzeit und Kündigungsfrist."),
        ("testversion", "Kann man die Software vorher ausprobieren?"),
        ("api", "Schnittstelle für eigene Erweiterungen und andere Programme."),
        ("integrationen", "Fertige Anbindungen an andere Software."),
    ]},
    {"id": "datenschutz", "titel": "Datenschutz & Datenhoheit", "felder": [
        ("datenort", "Wo Ihre Buchhaltungs- und Personaldaten gespeichert werden."),
        ("us_cloud_act", "Können US-Behörden Zugriff verlangen – auch auf Daten in Europa?"),
        ("dpa_avv", "Auftragsverarbeitungsvertrag – Pflicht, sobald Personendaten verarbeitet werden."),
        ("datenexport", "Kommen Sie mit allen Daten wieder heraus, und was kostet das?"),
        ("ki_datennutzung", "Welche Daten an welches KI-Modell gehen."),
    ]},
    {"id": "anbieter", "titel": "Anbieter", "felder": [
        ("anbieter", "Vollständiger Firmenname."),
        ("hq_land", "Hauptsitz des Anbieters."),
        ("mutter_konzern", "Wem der Anbieter gehört."),
        ("marktpraesenz_ch", "Kunden und Partner in der Schweiz, soweit bekannt."),
        ("sprachen", "Sprachen der Software."),
        ("website", "Offizielle Website."),
    ]},
]


def ist_offen(value) -> bool:
    """Wert, der noch beim Anbieter geprüft werden muss («Prüfen – …»)."""
    return isinstance(value, str) and bool(re.match(r"(prüfen|offen|unklar)\b", value.strip().lower()))


def ja_nein(value: str) -> str:
    v = (value or "").strip().lower()
    if v.startswith("ja"):
        return "ja"
    if v.startswith("nein"):
        return "nein"
    if ist_offen(value):
        return "offen"
    return "teils"


def liste(raw: str) -> list[str]:
    """Kommagetrennte Werte vor einem allfälligen Kommentar in Klammern: «Cloud, On-Prem (nur Version 8)»."""
    kopf = re.split(r"\s+[–(]", raw or "", maxsplit=1)[0]
    return [x.strip() for x in kopf.split(",") if x.strip()]


def datenort_key(raw: str) -> str:
    v = (raw or "").strip().lower()
    if v.startswith("schweiz"):
        return "ch"
    if v.startswith(("eu", "europa")):
        return "eu"
    if v.startswith("wählbar"):
        return "wahl"
    if v.startswith("eigener server"):
        return "eigen"
    if v.startswith(("usa", "weltweit")):
        return "us"
    return "offen"


DATENORT = {
    "ch": {"label": "Schweiz", "ton": "gut", "satz": "Ihre Daten liegen in der Schweiz."},
    "eu": {"label": "Europa", "ton": "gut", "satz": "Ihre Daten liegen in Europa."},
    "wahl": {"label": "Wählbar", "ton": "gut", "satz": "Der Speicherort lässt sich wählen (z.B. Schweiz oder Europa)."},
    "eigen": {"label": "Eigener Server", "ton": "gut", "satz": "Die Daten liegen auf Ihrem eigenen Server oder bei Ihrem Hoster."},
    "us": {"label": "USA / weltweit", "ton": "schlecht", "satz": "Ihre Daten können ausserhalb Europas gespeichert werden."},
    "offen": {"label": "Noch offen", "ton": "offen", "satz": "Wo die Daten liegen, ist noch nicht belegt."},
}


# ---------------------------------------------------------------------------
# Datenobjekt
# ---------------------------------------------------------------------------


@dataclass
class Loesung:
    raw: dict
    id: str = ""
    name: str = ""
    anbieter: str = ""
    segment: str = ""
    groessen: list = field(default_factory=list)
    branchen: set = field(default_factory=set)
    betrieb: list = field(default_factory=list)
    module: dict = field(default_factory=dict)
    quellen: list = field(default_factory=list)
    suchtext: str = ""

    def __post_init__(self):
        r = self.raw
        self.id = r.get("id", "")
        self.name = r.get("name", "")
        self.anbieter = r.get("anbieter", "")
        self.segment = r.get("segment", "")
        self.groessen = [g for g in liste(r.get("zielgroesse_ma", "")) if g in GROESSE_KEYS]
        self.branchen = {BRANCHEN_WERTE[b] for b in liste(r.get("branchen_fokus", "")) if b in BRANCHEN_WERTE}
        self.betrieb = [b for b in liste(r.get("betrieb", "")) if b in BETRIEB_WERTE]
        self.module = {f: skala(r.get(f, "")) for f in MODUL_FELDER}
        self.quellen = [q.strip() for q in (r.get("quellen") or "").split("|") if q.strip()]
        self.suchtext = " ".join(str(r.get(k, "")) for k in ("name", "anbieter", "segment", "branchen_fokus", "hq_land",
                                                             "mutter_konzern", "geeignet_fuer")).lower()

    def __getattr__(self, item):
        # Erlaubt im Template z.B. {{ l.preis_einstieg }}
        raw = self.__dict__.get("raw")
        if raw is not None and item in raw:
            return raw[item]
        raise AttributeError(item)

    # --- Einfache Aussagen -------------------------------------------------
    @property
    def seg(self) -> dict:
        return SEGMENTE.get(self.segment, {"id": "weitere", "label": self.segment or "Weitere", "icon": "spark", "text": ""})

    @property
    def groessen_text(self) -> str:
        if not self.groessen:
            return "noch offen"
        erste, letzte = GROESSE_INFO[self.groessen[0]], GROESSE_INFO[self.groessen[-1]]
        if erste is letzte:
            return "über 250 Mitarbeitende" if erste["key"] == "250+" else erste["titel"]
        if letzte["key"] == "250+":
            return f"{erste['label'].split('–')[0]} und mehr Mitarbeitende"
        return f"{erste['label'].split('–')[0]}–{letzte['label'].split('–')[-1]} Mitarbeitende"

    @property
    def betrieb_text(self) -> str:
        return " · ".join(BETRIEB_TEXT[b].split(" (")[0] for b in self.betrieb) or "noch offen"

    @property
    def kosten(self) -> dict | None:
        x = KOSTEN.get((self.raw.get("kosten_stufe") or "").strip())
        return x

    @property
    def aufwand(self) -> dict | None:
        return AUFWAND.get((self.raw.get("einfuehrung_aufwand") or "").strip())

    @property
    def kosten_achse(self) -> float:
        # PUNKTELOGIK (gleich in app.js): unbekannt zählt wie «Mittel»
        return (self.kosten["rang"] if self.kosten else 1.5) + (self.aufwand["rang"] if self.aufwand else 1)

    @property
    def dort(self) -> dict:
        key = datenort_key(self.raw.get("datenort", ""))
        return {"key": key, **DATENORT[key]}

    @property
    def cloud_act(self) -> str:
        return ja_nein(self.raw.get("us_cloud_act", ""))

    @property
    def swissdec(self) -> str:
        return ja_nein(self.raw.get("swissdec", ""))

    @property
    def pruefpunkte(self) -> int:
        try:
            return int(self.raw.get("anzahl_pruefpunkte") or 0)
        except (TypeError, ValueError):
            return 0

    def bedarf(self, key: str) -> dict:
        """Schlechtester Wert der Felder, die zu einem Bedarf gehören (z.B. Projekte & Zeit)."""
        werte = [self.module[f] for f in BEDARF_INFO[key]["felder"]]
        return max(werte, key=lambda w: w["rang"])

    @property
    def bedarf_werte(self) -> dict:
        return {b["key"]: self.bedarf(b["key"])["key"] for b in BEDARF}

    @property
    def breite(self) -> float:
        """Durchschnittliche Punkte über alle Module (0–3)."""
        p = [(w["punkte"] or 0) for w in self.module.values()]
        return round(sum(p) / len(p), 3) if p else 0

    @property
    def anzahl_voll(self) -> int:
        return sum(1 for w in self.module.values() if w["key"] == "voll")

    @property
    def abdeckung_prozent(self) -> int:
        return round(self.breite / 3 * 100)

    def bereiche(self, labels: dict) -> list[dict]:
        out = []
        for b in BEREICHE:
            zeilen = [{"key": f, "label": labels.get(f, f), "hilfe": h, "wert": self.module[f]} for f, h in b["felder"]]
            out.append({**b, "zeilen": zeilen, "voll": sum(z["wert"]["key"] == "voll" for z in zeilen)})
        return out

    @property
    def schweiz(self) -> list[dict]:
        out = []
        for key, label, hilfe in SCHWEIZ:
            wert = self.raw.get(key, "")
            jn = ja_nein(wert)
            if (wert or "").startswith(("Modul", "Partner", "Teilweise")):
                jn = "teils"
            out.append({"key": key, "label": label, "hilfe": hilfe, "wert": wert, "jn": jn, "offen": ist_offen(wert)})
        return out

    @property
    def kurz_gesagt(self) -> list[dict]:
        """Die wichtigsten Aussagen in einfacher Sprache, mit Tonalität (gut/mittel/schlecht/offen)."""
        punkte = [{"ton": "gut", "text": f"Gedacht für {self.groessen_text}."
                   if self.groessen else "Für welche Betriebsgrösse, ist noch offen."}]
        n = self.anzahl_voll
        punkte.append({"ton": "gut" if n >= 18 else "mittel" if n >= 10 else "offen" if n == 0 else "mittel",
                       "text": f"{n} von {len(MODUL_FELDER)} Bereichen sind im Standard enthalten."})
        s = self.swissdec
        if s == "ja":
            punkte.append({"ton": "gut", "text": "Die Lohnbuchhaltung ist Swissdec-zertifiziert."})
        elif s == "nein":
            punkte.append({"ton": "mittel", "text": "Keine Swissdec-zertifizierte Lohnbuchhaltung."})
        elif s == "offen":
            punkte.append({"ton": "offen", "text": "Ob der Lohn Swissdec-zertifiziert ist, ist noch offen."})
        d = self.dort
        punkte.append({"ton": d["ton"], "text": d["satz"]})
        c = self.cloud_act
        if c == "ja":
            punkte.append({"ton": "mittel", "text": "Der Anbieter untersteht US-Recht (CLOUD Act): US-Behörden könnten Zugriff verlangen."})
        elif c == "nein":
            punkte.append({"ton": "gut", "text": "Kein US-Konzern im Hintergrund – kein Zugriff über den US CLOUD Act."})
        return punkte

    @property
    def fakten(self) -> list[dict]:
        r = self.raw
        return [
            {"titel": "Preis", "wert": r.get("preis_einstieg", ""), "offen": ist_offen(r.get("preis_einstieg"))},
            {"titel": "Betrieb", "wert": self.betrieb_text, "offen": not self.betrieb},
            {"titel": "Einführung", "wert": r.get("einfuehrung", ""), "offen": ist_offen(r.get("einfuehrung"))},
            {"titel": "Testversion", "wert": r.get("testversion", ""), "offen": ist_offen(r.get("testversion"))},
        ]

    def detail_gruppen(self, labels: dict) -> list[dict]:
        out = []
        for g in DETAIL_GRUPPEN:
            zeilen = []
            for key, hilfe in g["felder"]:
                wert = self.raw.get(key, "")
                if wert in ("", None):
                    continue
                zeilen.append({"key": key, "label": labels.get(key, key), "hilfe": hilfe, "wert": wert, "offen": ist_offen(wert)})
            out.append({**g, "zeilen": zeilen, "offen_anzahl": sum(z["offen"] for z in zeilen)})
        return out

    # --- Berater -------------------------------------------------------------
    def fit(self, groesse: str = "", branche: str = "") -> float | None:
        """PUNKTELOGIK (gleich in app.js): Passung zu Grösse und Branche. None = passt nicht."""
        punkte = 0.0
        if groesse and self.groessen:
            if groesse in self.groessen:
                punkte += 2
            elif any(abs(GROESSE_KEYS.index(g) - GROESSE_KEYS.index(groesse)) == 1 for g in self.groessen):
                punkte += 0.5
            else:
                return None
        else:
            punkte += 1  # keine Grösse gewählt oder Zielgrösse noch offen
        if branche and branche != "andere" and branche in self.branchen:
            # Branchenlösungen nennen ihre Zielgrösse selten: offene Grösse nicht bestrafen (+0.5)
            punkte += (2.5 + (0.5 if groesse and not self.groessen else 0)) if self.segment == "Branchenlösung" else 1.5
        elif self.segment == "Branchenlösung":
            return None  # Branchenlösung einer anderen Branche
        elif "neutral" in self.branchen or not self.branchen:
            punkte += 1
        else:
            punkte += 0.5
        return punkte

    def passt_betrieb(self, betrieb: str) -> bool:
        return not betrieb or bool(BETRIEB_WAHL.get(betrieb, set()) & set(self.betrieb))

    def js_daten(self) -> dict:
        """Kompakte Daten für die Berechnung im Browser (app.js)."""
        return {"id": self.id, "g": self.groessen, "b": sorted(self.branchen), "seg": self.segment, "bt": self.betrieb,
                "m": self.bedarf_werte, "br": self.breite, "k": self.kosten["rang"] if self.kosten else None,
                "a": self.aufwand["rang"] if self.aufwand else None, "pp": self.pruefpunkte, "n": self.name.lower(),
                "v": self.anzahl_voll, "gt": self.groessen_text}


@dataclass
class Verzeichnis:
    meta: dict
    loesungen: list[Loesung]
    by_id: dict

    @property
    def stand(self) -> date | None:
        try:
            return date.fromisoformat(self.meta.get("stand", ""))
        except ValueError:
            return None

    @property
    def labels(self) -> dict:
        return self.meta.get("felder", {})


# ---------------------------------------------------------------------------
# Filtern (Verzeichnis, gleiche Logik in app.js)
# ---------------------------------------------------------------------------


def filtern(loesungen, *, groesse="", segment="", module=(), betrieb="", q=""):
    woerter = q.strip().lower().split()
    out = []
    for l in loesungen:
        if groesse and groesse not in l.groessen:
            continue
        if segment and l.seg["id"] != segment:
            continue
        if any(l.bedarf(m)["key"] == "nein" for m in module):
            continue
        if not l.passt_betrieb(betrieb):
            continue
        if woerter and not all(w in l.suchtext for w in woerter):
            continue
        out.append(l)
    out.sort(key=lambda l: (SEGMENT_RANG.get(l.segment, 99), l.name.lower()))
    return out


# ---------------------------------------------------------------------------
# Empfehlungen im Berater – PUNKTELOGIK (gleich in app.js, Funktion «empfehlen»)
#
# 1. Ausschluss: falsche Grösse (nicht einmal angrenzend), Branchenlösung einer anderen Branche,
#    falscher Betrieb oder ein Pflichtmodul «Nein».
# 2. Abdeckung: Durchschnitt der Punkte der gewählten Module (Voll 3, Modul 2, Partner 1.5, Basis 1,
#    Prüfen 0.5). Ohne Auswahl: Breite über alle Module.
# 3. Passung: Grösse (2 / angrenzend 0.5 / Zielgrösse offen 1) + Branche (
#    Branchenlösung der Branche 2.5 / spezialisiert 1.5 / branchenneutral 1 / sonst 0.5). «Beste Abdeckung» = höchste Abdeckung + Passung.
# 4. Kostenachse: Kostenstufe (0–3) + Einführungsaufwand (0–2), unbekannt 1.5 bzw. 1.
# Rollen: «Beste Abdeckung», «Günstigste Lösung», «Guter Kompromiss» (Abdeckung + Passung − 0.6 × Kosten).
# ---------------------------------------------------------------------------

ROLLEN = {
    "beide": {"label": "Beste Wahl", "hilfe": "Beste Abdeckung und zugleich die günstigste Lösung"},
    "abdeckung": {"label": "Beste Abdeckung", "hilfe": "Deckt Ihre Bereiche am vollständigsten ab"},
    "guenstig": {"label": "Günstigste Lösung", "hilfe": "Tiefste Kosten und Einführungsaufwand"},
    "kompromiss": {"label": "Guter Kompromiss", "hilfe": "Gute Abdeckung zu vernünftigen Kosten"},
    "weitere": {"label": "Ebenfalls passend", "hilfe": "Eine weitere gute Wahl"},
}


@dataclass
class Treffer:
    l: Loesung
    fit: float
    abdeckung: float
    werte: list

    @property
    def gesamt(self) -> float:
        return self.abdeckung + self.fit - 0.6 * self.l.kosten_achse


def treffer_liste(loesungen, groesse="", branche="", module=(), betrieb="") -> list[Treffer]:
    out = []
    for l in loesungen:
        f = l.fit(groesse, branche)
        if f is None or not l.passt_betrieb(betrieb):
            continue
        werte = [(m, l.bedarf(m)) for m in module]
        if any(w["key"] == "nein" for _, w in werte):
            continue
        abdeckung = sum(w["punkte"] for _, w in werte) / len(werte) if werte else l.breite
        out.append(Treffer(l, f, abdeckung, werte))
    return out


def empfehlen(loesungen, groesse="", branche="", module=(), betrieb="") -> tuple[list[dict], list[Treffer]]:
    alle = treffer_liste(loesungen, groesse, branche, module, betrieb)
    if not alle:
        return [], []

    def name(t):
        return t.l.name.lower()

    beste = min(alle, key=lambda t: (-(t.abdeckung + t.fit), -t.abdeckung, -t.l.breite, t.l.kosten_achse, t.l.pruefpunkte, name(t)))
    mit_preis = [t for t in alle if t.l.kosten]
    guenstig = min(mit_preis, key=lambda t: (t.l.kosten_achse, -t.abdeckung, -t.fit, t.l.pruefpunkte, name(t))) if mit_preis else None
    gewaehlt: list[tuple[str, Treffer]] = []
    if guenstig is beste:
        gewaehlt.append(("beide", beste))
    else:
        gewaehlt.append(("abdeckung", beste))
        if guenstig:
            gewaehlt.append(("guenstig", guenstig))
    uebrig = sorted((t for t in alle if not any(t is x for _, x in gewaehlt)),
                    key=lambda t: (-t.gesamt, -t.abdeckung, t.l.pruefpunkte, name(t)))
    for t in uebrig:
        if len(gewaehlt) >= 3:
            break
        rolle = "kompromiss" if not any(r == "kompromiss" for r, _ in gewaehlt) and gewaehlt[0][0] != "beide" else "weitere"
        gewaehlt.append((rolle, t))
    rollen = [{"rolle": r, **ROLLEN[r], "t": t} for r, t in gewaehlt]
    rest = [t for t in uebrig if not any(t is x for _, x in gewaehlt)]
    return rollen, rest


def gruende(t: Treffer, groesse: str = "", branche: str = "") -> list[dict]:
    """Begründung einer Empfehlung – gleiche Sätze wie in app.js («gruende»)."""
    out = []
    for m, w in t.werte:
        out.append({"ton": w["ton"], "text": f"{BEDARF_INFO[m]['label']}: {w['satz']}"})
    if not t.werte:
        out.append({"ton": "gut" if t.l.anzahl_voll >= 18 else "mittel",
                    "text": f"{t.l.anzahl_voll} von {len(MODUL_FELDER)} Bereichen im Standard enthalten"})
    if groesse and not t.l.groessen:
        out.append({"ton": "offen", "text": "Für welche Betriebsgrösse, ist noch offen"})
    elif groesse:
        if groesse in t.l.groessen:
            out.append({"ton": "gut", "text": "Passt zu Ihrer Betriebsgrösse"})
        else:
            out.append({"ton": "mittel", "text": f"Grösse grenzwertig: gedacht für {t.l.groessen_text}"})
    if branche and branche in t.l.branchen:
        out.append({"ton": "gut", "text": f"Auf {BRANCHE_INFO[branche]['label']} ausgerichtet"})
    return out


# ---------------------------------------------------------------------------
# Laden
# ---------------------------------------------------------------------------


def lade_rohdaten(path: Path | None = None) -> dict:
    with open(path or DATEN_DATEI, encoding="utf-8") as f:
        return json.load(f)


def get_verzeichnis(path: Path | None = None) -> Verzeichnis:
    roh = lade_rohdaten(path)
    loesungen = [Loesung(e) for e in roh.get("eintraege", [])]
    return Verzeichnis(meta=roh.get("meta", {}), loesungen=loesungen, by_id={l.id: l for l in loesungen})
