"""Erzeugt die statische Website (für GitHub Pages) aus daten/.

Alle Links sind relativ – die Seite funktioniert darum unter
https://<name>.github.io/<repo>/ genauso wie lokal oder mit eigener Domain.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, StrictUndefined, pass_context, select_autoescape
from markupsafe import Markup, escape

from .data import (ANALYSE_GLOB, AUFWAND, BEDARF, BEREICHE, BETRIEB_TEXT, BRANCHE_INFO, BRANCHEN, DATENORT, DOCS_DIR,
                   GROESSE_INFO, GROESSEN, KOSTEN, MODUL_FELDER, SCHWEIZ, SEGMENTE, SKALA, Verzeichnis, empfehlen,
                   filtern, get_verzeichnis, gruende, treffer_liste)
from .ui import ZEICHEN, icon, maskottchen, waechter, zeichen

HIER = Path(__file__).resolve().parent
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
          "Dezember"]
# Name des Maskottchens – erscheint im Berater («Lexu fragt …») und in den Texten.
MASKOTTCHEN_NAME = "Lexu"


class BuildFehler(Exception):
    pass


# ---------------------------------------------------------------------------
# Berater: Grösse und Branche als eigene Seiten (teilbar, mit eigener Vorschau),
# Module und Betrieb wählt man auf der Ergebnisseite – gerechnet wird im Browser.
#   /                                  Frage 1 (Grösse)
#   /berater/10-50/                    Frage 2 (Branche)
#   /berater/10-50/handel/?modul=lohn,lager&betrieb=cloud    Fragen 3 + 4 und Ergebnis
# Achtung: Pfade und Parameter stehen in geteilten Links – nach der Veröffentlichung nicht mehr ändern.
# ---------------------------------------------------------------------------

BETRIEB_OPTIONEN = [
    ("", "globe", "Ist mir egal", "Alle Betriebsarten berücksichtigen"),
    ("cloud", "cloud", "In der Cloud", "Keine eigene Hardware, Zugriff über den Browser"),
    ("server", "server", "Auf eigenem Server", "Software im eigenen Haus oder beim IT-Partner"),
]


def berater_pfad(groesse: str = "", branche: str = "") -> str:
    if not groesse:
        return ""
    teile = [GROESSE_INFO[groesse]["pfad"]] + ([branche] if branche else [])
    return "berater/" + "".join(f"{t}/" for t in teile)


def berater_kontext(v: Verzeichnis, groesse: str = "", branche: str = "") -> dict:
    schritt = 0 if not groesse else 1 if not branche else 2
    ctx = {"schritt": schritt, "groesse": groesse, "branche": branche,
           "g_info": GROESSE_INFO.get(groesse), "b_info": BRANCHE_INFO.get(branche)}
    if schritt == 0:
        ctx["optionen"] = [{"icon": "user" if i == 0 else "users" if i == 1 else "team" if i == 2 else "building",
                            "label": g["titel"], "hilfe": g["hilfe"], "pfad": berater_pfad(g["key"]),
                            "anzahl": len(treffer_liste(v.loesungen, g["key"]))} for i, g in enumerate(GROESSEN)]
    elif schritt == 1:
        ctx["optionen"] = [{"icon": b["icon"], "label": b["label"], "hilfe": b["hilfe"], "pfad": berater_pfad(groesse, b["key"]),
                            "anzahl": len(treffer_liste(v.loesungen, groesse, b["key"]))} for b in BRANCHEN]
    else:
        rollen, rest = empfehlen(v.loesungen, groesse, branche)
        alle = treffer_liste(v.loesungen, groesse, branche)
        for r in rollen:
            r["gruende"] = gruende(r["t"], groesse, branche)
        ctx.update({
            "rollen": rollen, "rest": rest, "pool": [t.l for t in alle],
            "bedarf": BEDARF, "betrieb_optionen": BETRIEB_OPTIONEN,
            "js": {"groesse": groesse, "branche": branche, "loesungen": [t.l.js_daten() for t in alle],
                   "bedarf": {b["key"]: b["label"] for b in BEDARF},
                   "skala": {k: {"ton": s["ton"], "satz": s["satz"], "punkte": s["punkte"], "rang": s["rang"]} for k, s in SKALA.items()},
                   "groessen": [g["key"] for g in GROESSEN], "branche_label": BRANCHE_INFO[branche]["label"],
                   "modul_total": len(MODUL_FELDER), "zeichen": {k: ZEICHEN[k] for k in ("gut", "mittel", "schlecht", "offen")}},
        })
        namen = ", ".join(r["t"].l.name for r in rollen)
        g_titel = GROESSE_INFO[groesse]["titel"]
        ctx["seiten_titel"] = f"ERP für {BRANCHE_INFO[branche]['label']} · {g_titel}"
        ctx["seiten_text"] = (f"{len(alle)} passende ERP- und Buchhaltungslösungen für {BRANCHE_INFO[branche]['label']} mit "
                              f"{GROESSE_INFO[groesse]['mit']}. Empfehlungen: {namen}. Unabhängig, mit Modul-Matrix und Preisen."
                              if alle else "Für diese Kombination gibt es noch keine passende Lösung im Verzeichnis.")
    return ctx


def alle_berater_zustaende():
    yield "", ""
    for g in GROESSEN:
        yield g["key"], ""
        for b in BRANCHEN:
            yield g["key"], b["key"]


# ---------------------------------------------------------------------------
# Verzeichnis und Vergleich: alle Lösungen werden ausgeliefert, gefiltert wird im Browser (app.js)
# ---------------------------------------------------------------------------


def verzeichnis_kontext(v: Verzeichnis) -> dict:
    seg_n = {}
    for l in v.loesungen:
        seg_n[l.seg["id"]] = seg_n.get(l.seg["id"], 0) + 1
    return {
        "loesungen": filtern(v.loesungen), "total": len(v.loesungen),
        "segmente": [{"id": s["id"], "label": s["label"], "icon": s["icon"], "anzahl": seg_n.get(s["id"], 0)} for s in SEGMENTE.values()],
        "groessen": GROESSEN, "bedarf": BEDARF, "betrieb_optionen": BETRIEB_OPTIONEN, "skala": SKALA,
    }


def vergleich_kontext(v: Verzeichnis) -> dict:
    zeilen = []
    for b in BEREICHE:
        zeilen.append({"art": "kopf", "titel": b["titel"], "icon": b["icon"]})
        for f, hilfe in b["felder"]:
            zeilen.append({"art": "modul", "key": f, "label": v.labels.get(f, f), "hilfe": hilfe})
    zeilen.append({"art": "kopf", "titel": "Schweiz-Tauglichkeit", "icon": "ch"})
    for f, label, hilfe in SCHWEIZ:
        zeilen.append({"art": "text", "key": f, "label": label, "hilfe": hilfe})
    zeilen.append({"art": "kopf", "titel": "Betrieb & Kosten", "icon": "cloud"})
    for f in ("betrieb", "preis_einstieg", "kosten_stufe", "einfuehrung_aufwand", "testversion"):
        zeilen.append({"art": "text", "key": f, "label": v.labels.get(f, f), "hilfe": ""})
    zeilen.append({"art": "kopf", "titel": "Datenschutz", "icon": "shield"})
    for f in ("datenort", "us_cloud_act", "datenexport"):
        zeilen.append({"art": "text", "key": f, "label": v.labels.get(f, f), "hilfe": ""})
    return {"loesungen": filtern(v.loesungen), "zeilen": zeilen, "skala": SKALA}


# ---------------------------------------------------------------------------
# Marktanalyse (Markdown aus daten/)
# ---------------------------------------------------------------------------


def _slug(value, separator="-"):
    value = value.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        value = value.replace(a, b)
    return re.sub(r"[^a-z0-9]+", separator, value).strip(separator)


def analyse_platzhalter(v: Verzeichnis) -> dict:
    """Zahlen, die in der Marktanalyse als {{ name }} verwendet werden können."""
    ls = v.loesungen
    werte = {
        "anzahl": len(ls),
        "anzahl_swissdec": sum(l.swissdec == "ja" for l in ls),
        "anzahl_cloud": sum("Cloud" in l.betrieb for l in ls),
        "anzahl_onprem": sum("On-Prem" in l.betrieb for l in ls),
        "anzahl_daten_ch": sum(l.dort["key"] == "ch" for l in ls),
        "anzahl_cloud_act": sum(l.cloud_act == "ja" for l in ls),
        "anzahl_pruefpunkte": sum(l.pruefpunkte for l in ls),
        "stand": datum_lang(v.stand),
    }
    for s in SEGMENTE.values():
        werte[f"anzahl_{s['id']}"] = sum(l.seg["id"] == s["id"] for l in ls)
    return werte


SEITEN = {"verzeichnis": "verzeichnis/", "grundlagen": "grundlagen/", "berater": "", "vergleich": "vergleich/", "ueber": "ueber/"}


def analyse_html(v: Verzeichnis, root: str):
    files = sorted(DOCS_DIR.glob(ANALYSE_GLOB))
    if not files:
        return None, "", []
    text = files[-1].read_text(encoding="utf-8")
    werte = analyse_platzhalter(v)

    def ersetzen(m):
        name = m.group(1)
        if name not in werte:
            raise BuildFehler(f"Marktanalyse: unbekannter Platzhalter {{{{ {name} }}}} – erlaubt: {', '.join(werte)}")
        return str(werte[name])

    text = re.sub(r"\{\{\s*(\w+)\s*\}\}", ersetzen, text)
    lines = text.splitlines()
    titel = lines.pop(0)[2:].strip() if lines and lines[0].startswith("# ") else ""
    html = markdown.markdown("\n".join(lines), extensions=["tables", "sane_lists", "toc"],
                             extension_configs={"toc": {"slugify": _slug}})
    html = html.replace("<li>[ ] ", '<li class="todo">').replace("<li>[x] ", '<li class="todo erledigt">')

    # Interne Links: [Name](tool:<id>) und [Text](seite:verzeichnis|grundlagen|berater|vergleich)
    def intern(m):
        art, ziel = m.group(1), m.group(2)
        if art == "tool":
            if ziel not in v.by_id:
                raise BuildFehler(f"Marktanalyse verlinkt unbekannte Lösung: tool:{ziel}")
            return f'href="{root}erp/{ziel}/" data-drawer'
        basis, _, query = ziel.partition("?")
        if basis not in SEITEN:
            raise BuildFehler(f"Marktanalyse verlinkt unbekannte Seite: seite:{ziel}")
        return f'href="{root}{SEITEN[basis] or "./"}{"?" + query if query else ""}"'

    html = re.sub(r'href="(tool|seite):([^"]+)"', intern, html)
    html = html.replace('<a href="http', '<a target="_blank" rel="noopener" href="http')
    toc = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', html)
    return titel, html, toc


# ---------------------------------------------------------------------------
# Template-Umgebung
# ---------------------------------------------------------------------------


def datum_lang(d) -> str:
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except ValueError:
            return d
    if not d:
        return ""
    return f"{d.day}. {MONATE[d.month - 1]} {d.year}"


def domain(url: str) -> str:
    try:
        return url.split("//", 1)[1].split("/", 1)[0].removeprefix("www.")
    except IndexError:
        return url


def ton_icon(ton: str) -> str:
    return {"gut": "✓", "schlecht": "✕", "mittel": "!"}.get(ton, "?")


def json_script(wert, element_id: str) -> Markup:
    daten = json.dumps(wert, ensure_ascii=False).replace("<", "\\u003C").replace(">", "\\u003E").replace("&", "\\u0026")
    return Markup(f'<script id="{escape(element_id)}" type="application/json">{daten}</script>')


@pass_context
def url(ctx, ziel: str = "") -> str:
    """Relativer Link von der aktuellen Seite zu `ziel` (z.B. 'verzeichnis/', 'erp/x/')."""
    return (ctx["root"] + ziel) or "./"


@pass_context
def mk(ctx, pose: str, klasse: str = "", schmuck: bool = False) -> Markup:
    return maskottchen(ctx["root"], pose, klasse, schmuck)


@pass_context
def mk_sec(ctx, pose: str, klasse: str = "") -> Markup:
    return waechter(ctx["root"], pose, klasse)


def umgebung() -> Environment:
    env = Environment(loader=FileSystemLoader(HIER / "templates"), autoescape=select_autoescape(["html"]),
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    env.globals.update(icon=icon, zeichen=zeichen, url=url, mk=mk, mk_sec=mk_sec, MASKOTTCHEN=MASKOTTCHEN_NAME, BEDARF_LISTE=BEDARF)
    env.filters.update(datum=datum_lang, domain=domain, ton_icon=ton_icon, json_script=json_script)
    return env


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def adressen() -> tuple[str, str]:
    """Öffentliche Adresse der Website und des GitHub-Repositorys.

    Beide setzt der GitHub-Workflow automatisch (.github/workflows/pages.yml). Bei eigener Domain
    ERP_SITE_URL dort überschreiben.
    """
    site = os.environ.get("ERP_SITE_URL", "").strip()
    repo = os.environ.get("ERP_REPO_URL", "").strip().rstrip("/") or _repo_aus_git()
    return (site.rstrip("/") + "/" if site else ""), repo


def _repo_aus_git() -> str:
    """Lokal: Repo-Adresse aus `git remote` lesen, damit «Fehler melden» auch in der Vorschau verlinkt ist."""
    try:
        erg = subprocess.run(["git", "remote", "get-url", "origin"], cwd=HIER.parent, capture_output=True,
                             text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    adresse = erg.stdout.strip() if erg.returncode == 0 else ""
    m = re.match(r"(?:git@github\.com:|https://github\.com/)([^/]+/[^/]+?)(?:\.git)?/?$", adresse)
    return f"https://github.com/{m.group(1)}" if m else ""


def bauen(ziel: Path, log=print) -> int:
    # Nicht den ganzen Ordner löschen (unter Windows sperrt z.B. die laufende Vorschau einzelne Dateien),
    # sondern alles überschreiben und am Schluss nur veraltete Dateien entfernen.
    v = get_verzeichnis()
    ziel.mkdir(parents=True, exist_ok=True)
    env = umgebung()
    site_url, repo_url = adressen()
    if not site_url:
        log("Hinweis: ERP_SITE_URL ist nicht gesetzt – die LinkedIn-Vorschau braucht die öffentliche Adresse "
            "(auf GitHub wird sie automatisch gesetzt).")
    basis = {"daten_stand": v.stand, "daten_anzahl": len(v.loesungen), "daten_hinweis": v.meta.get("hinweis", ""),
             "daten_status": v.meta.get("status", ""), "site_url": site_url, "repo_url": repo_url,
             "daten_geprueft": sum(1 for l in v.loesungen if l.pruefpunkte == 0),
             "daten_offen": sum(l.pruefpunkte for l in v.loesungen)}
    seiten = 0
    geschrieben: set[Path] = set()

    def datei_schreiben(out: Path, text: str):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        geschrieben.add(out.resolve())

    def schreiben(pfad: str, template: str, datei: str = "index.html", **ctx):
        nonlocal seiten
        tiefe = pfad.count("/")
        html = env.get_template(template).render(**basis, root="../" * tiefe, pfad=pfad, **ctx)
        datei_schreiben(ziel / pfad / datei, html)
        seiten += 1

    # Berater (Startseite + Grösse + Grösse × Branche)
    for groesse, branche in alle_berater_zustaende():
        schreiben(berater_pfad(groesse, branche), "berater.html", seite="berater", **berater_kontext(v, groesse, branche))

    schreiben("verzeichnis/", "verzeichnis.html", seite="verzeichnis", **verzeichnis_kontext(v))
    schreiben("vergleich/", "vergleich.html", seite="vergleich", **vergleich_kontext(v))

    # Steckbriefe: ganze Seite + Fragment für die Schublade
    for l in v.loesungen:
        ctx = {"l": l, "bereiche": l.bereiche(v.labels), "gruppen": l.detail_gruppen(v.labels), "skala": SKALA}
        aehnlich = [x for x in v.loesungen if x.id != l.id and (x.segment == l.segment or set(x.groessen) & set(l.groessen))]
        aehnlich.sort(key=lambda x: (x.segment != l.segment, -len(set(x.groessen) & set(l.groessen)), x.pruefpunkte))
        schreiben(f"erp/{l.id}/", "detail.html", seite="detail", aehnlich=aehnlich[:4], **ctx)
        schreiben(f"erp/{l.id}/", "_steckbrief.html", datei="steckbrief.html", **ctx)

    schreiben("grundlagen/", "grundlagen.html", seite="grundlagen", skala=SKALA, kosten=KOSTEN, aufwand=AUFWAND,
              schweiz=SCHWEIZ, segmente=SEGMENTE, betrieb_text=BETRIEB_TEXT, datenort=DATENORT)
    schreiben("ueber/", "ueber.html", seite="ueber")
    titel, inhalt, toc = analyse_html(v, "../")
    if titel is not None:
        schreiben("marktanalyse/", "marktanalyse.html", seite="marktanalyse", titel=titel, inhalt=Markup(inhalt), toc=toc)

    # 404 (GitHub Pages liefert sie für jede unbekannte Adresse aus – Basis wird per Skript gesetzt)
    schreiben("", "404.html", datei="404.html", seite="404")

    # Für Suchmaschinen: robots.txt immer, sitemap.xml nur mit bekannter öffentlicher Adresse.
    if site_url:
        stand = v.stand.isoformat() if v.stand else ""
        seiten_liste = ["", "verzeichnis/", "vergleich/", "grundlagen/", "marktanalyse/", "ueber/"]
        seiten_liste += [berater_pfad(g, b) for g, b in alle_berater_zustaende() if b]
        seiten_liste += [f"erp/{l.id}/" for l in v.loesungen]
        eintraege = "".join(f"  <url><loc>{escape(site_url + p)}</loc>{f'<lastmod>{stand}</lastmod>' if stand else ''}</url>\n"
                            for p in seiten_liste)
        datei_schreiben(ziel / "sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + eintraege + "</urlset>\n")
    datei_schreiben(ziel / "robots.txt", "User-agent: *\nAllow: /\n" + (f"Sitemap: {site_url}sitemap.xml\n" if site_url else ""))

    # Suchdaten für die Vorschläge im Berater (einmal statt in jeder Seite)
    datei_schreiben(ziel / "suche.json", json.dumps(
        [{"id": l.id, "name": l.name, "seg": l.seg["label"], "an": l.anbieter, "such": l.suchtext, "n": l.name.lower()}
         for l in v.loesungen], ensure_ascii=False))

    # Statische Dateien
    for quelle in (HIER / "static").rglob("*"):
        if quelle.is_file():
            out = ziel / "static" / quelle.relative_to(HIER / "static")
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(quelle, out)
            geschrieben.add(out.resolve())
    datei_schreiben(ziel / ".nojekyll", "")

    # Veraltete Dateien entfernen (z.B. Steckbrief einer gelöschten Lösung)
    for alt in sorted(ziel.rglob("*"), reverse=True):
        try:
            if alt.is_file() and alt.resolve() not in geschrieben:
                alt.unlink()
            elif alt.is_dir() and not any(alt.iterdir()):
                alt.rmdir()
        except OSError as exc:
            log(f"Hinweis: konnte {alt} nicht entfernen ({exc})")
    log(f"{seiten} Seiten erzeugt in {ziel}")
    return seiten
