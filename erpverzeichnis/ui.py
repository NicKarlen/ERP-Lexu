"""Icons, Maskottchen und kleine HTML-Bausteine für die Templates."""
from markupsafe import Markup, escape

ICONS = {
    "doc": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
    "users": '<circle cx="9" cy="8" r="3.2"/><path d="M3.5 19c.6-3 3-4.8 5.5-4.8s4.9 1.8 5.5 4.8"/><path d="M16 5.2a3 3 0 0 1 0 5.6M17.5 14.4c1.6.6 2.7 2.2 3 4.6"/>',
    "user": '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c.8-3.6 3.6-5.6 7-5.6s6.2 2 7 5.6"/>',
    "team": '<circle cx="12" cy="7.5" r="2.6"/><circle cx="5.5" cy="10" r="2.1"/><circle cx="18.5" cy="10" r="2.1"/><path d="M7.5 19.5c.4-3 2.3-4.8 4.5-4.8s4.1 1.8 4.5 4.8M2.5 18c.3-2 1.5-3.3 3-3.5M21.5 18c-.3-2-1.5-3.3-3-3.5"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>',
    "shield": '<path d="M12 3.5 19 6v5.5c0 4.4-3 7.8-7 9-4-1.2-7-4.6-7-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "globe": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.5 2.6 3.6 5.4 3.6 8.5s-1.1 5.9-3.6 8.5c-2.5-2.6-3.6-5.4-3.6-8.5S9.5 6.1 12 3.5z"/>',
    "layers": '<path d="M12 3.5 3.5 8 12 12.5 20.5 8z"/><path d="M3.5 12 12 16.5 20.5 12M3.5 16 12 20.5 20.5 16"/>',
    "coins": '<ellipse cx="9" cy="7" rx="5.5" ry="2.5"/><path d="M3.5 7v4c0 1.4 2.5 2.5 5.5 2.5M3.5 11v4c0 1.4 2.5 2.5 5.5 2.5"/><ellipse cx="15" cy="13" rx="5.5" ry="2.5"/><path d="M9.5 13v4c0 1.4 2.5 2.5 5.5 2.5s5.5-1.1 5.5-2.5v-4"/>',
    "box": '<path d="M12 3.5 20 7.5v9L12 20.5 4 16.5v-9z"/><path d="m4 7.5 8 4 8-4M12 11.5v9"/>',
    "factory": '<path d="M3.5 20V10l5 3V10l5 3V6.5h4l1 13.5z"/><path d="M3.5 20h17M7.5 16.5h2M12.5 16.5h2"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "handshake": '<path d="m3 11 3.5-3.5L10 9l3-2 4.5 4.5L21 8"/><path d="m6.5 7.5-3.5 3.5 6.5 6.5c.8.8 2 .8 2.8 0l5.7-5.7"/><path d="m10 14 1.5 1.5M12.5 11.5 14 13"/>',
    "cart": '<path d="M3.5 4.5h2.2l2 10.5h10.3l1.9-7.5H6.8"/><circle cx="9" cy="19" r="1.4"/><circle cx="17" cy="19" r="1.4"/>',
    "building": '<rect x="4.5" y="3.5" width="10" height="17" rx="1.5"/><path d="M14.5 9.5h4a1 1 0 0 1 1 1v10h-15M8 7.5h3M8 11h3M8 14.5h3"/>',
    "brief": '<rect x="3.5" y="7" width="17" height="12.5" rx="2"/><path d="M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7M3.5 12.5h17"/>',
    "hammer": '<path d="m13.5 6.5 4 4M10 5l5.5-1.5 3 3L17 12l-7-7z"/><path d="m12.5 9.5-8 8a1.8 1.8 0 0 0 2.5 2.5l8-8"/>',
    "heart": '<path d="M12 20s-7.5-4.4-7.5-10A4.2 4.2 0 0 1 12 7.6 4.2 4.2 0 0 1 19.5 10c0 5.6-7.5 10-7.5 10z"/>',
    "cloud": '<path d="M7 18.5a4.5 4.5 0 0 1-.6-9 6 6 0 0 1 11.5 1.7A3.7 3.7 0 0 1 17.5 18.5z"/>',
    "server": '<rect x="4" y="4" width="16" height="7" rx="1.5"/><rect x="4" y="13" width="16" height="7" rx="1.5"/><path d="M8 7.5h.01M8 16.5h.01" stroke-width="2.6"/>',
    "spark": '<path d="M12 3.5v4M12 16.5v4M3.5 12h4M16.5 12h4M6 6l2.6 2.6M15.4 15.4 18 18M6 18l2.6-2.6M15.4 8.6 18 6"/>',
    "ch": '<rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="M12 7.5v9M7.5 12h9" stroke-width="2.6"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "filter": '<path d="M4 6h16M7 12h10M10 18h4"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "compare": '<rect x="3.5" y="4.5" width="7" height="15" rx="1.5"/><rect x="13.5" y="4.5" width="7" height="15" rx="1.5"/><path d="M6 9h2M6 12.5h2M16 9h2M16 12.5h2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "share": '<circle cx="6" cy="12" r="2.3"/><circle cx="17.5" cy="6" r="2.3"/><circle cx="17.5" cy="18" r="2.3"/><path d="m8 11 7.5-4M8 13l7.5 4"/>',
    "github": '<path d="M9 19c-4 1.3-4-2-5.5-2.5M14.5 21v-3.2c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.4 1.3a11.6 11.6 0 0 0-6.2 0C6.1 3.1 5.1 3.4 5.1 3.4a4.3 4.3 0 0 0-.1 3.2A4.6 4.6 0 0 0 3.7 9.8c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/>',
    "external": '<path d="M14 4h6v6M20 4l-9 9M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
}


def icon(name, size=20):
    pfad = ICONS.get(name, ICONS["spark"])
    return Markup(
        f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" aria-hidden="true" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{pfad}</svg>'
    )


# Maskottchen: Datei in static/maskottchen/ -> Beschreibung (Alt-Text) und Seitenverhältnis
MASKOTTCHEN = {
    "lupe": ("Der Waschbär untersucht den ERP-Markt mit einer Lupe", 440, 364),
    "laptop": ("Der Waschbär recherchiert am Laptop ERP-Systeme", 440, 366),
    "checkliste": ("Der Waschbär präsentiert eine Auswertung", 364, 440),
    "tablet": ("Der Waschbär mit Brille wertet Daten auf dem Tablet aus", 440, 362),
    "wachstum": ("Der Waschbär sitzt auf einem wachsenden Balkendiagramm", 416, 440),
    "pokal": ("Der Waschbär freut sich über das Ergebnis", 440, 419),
}
SECURITY = {
    "laptop": "Der Waschbär schützt Daten auf dem Laptop",
    "schild": "Der Waschbär hält einen Schutzschild",
    "dokument": "Der Waschbär hält ein geschütztes Dokument",
    "code": "Der Waschbär verschlüsselt Daten",
    "zone": "Der Waschbär in einem geschützten Bereich",
}


def maskottchen(root: str, pose: str, klasse: str = "", schmuck: bool = False) -> Markup:
    """Bild des Maskottchens. schmuck=True: rein dekorativ (leerer Alt-Text)."""
    alt, w, h = MASKOTTCHEN[pose]
    return Markup(f'<img class="mk {escape(klasse)}" src="{root}static/maskottchen/analyse-{pose}.webp" width="{w}" height="{h}" '
                  f'alt="{"" if schmuck else escape(alt)}" loading="lazy" decoding="async">')


def waechter(root: str, pose: str, klasse: str = "") -> Markup:
    """Security-Maskottchen (schwarzer Grund, wird per mix-blend-mode eingeblendet)."""
    return Markup(f'<img class="mk-sec {escape(klasse)}" src="{root}static/maskottchen/security-{pose}.webp" width="400" height="360" '
                  f'alt="{escape(SECURITY[pose])}" loading="lazy" decoding="async">')


# Zeichen in den runden Status-Punkten als SVG (Schrift-Glyphen wie ✓ oder ? sitzen je nach Schrift
# nicht mittig). viewBox 16 × 16, Mitte (8, 8).
ZEICHEN = {
    "voll": '<path d="M4.6 8.4l2.3 2.3 4.6-4.9"/>',
    "modul": '<path d="M8 4.6v6.8M4.6 8h6.8"/>',
    "partner": '<path d="M5.4 10.6l5.2-5.2M6.6 5.4h4v4"/>',
    "basis": '<circle cx="8" cy="8" r="3.6"/><path d="M8 4.4a3.6 3.6 0 0 1 0 7.2z" fill="currentColor" stroke="none"/>',
    "nein": '<path d="M4.8 8h6.4"/>',
    "pruefen": '<path d="M6.2 6.3a1.9 1.9 0 1 1 2.7 1.7c-.6.3-.9.7-.9 1.3v.2"/><path d="M8 11.5v.01" stroke-width="2.4"/>',
    "gut": '<path d="M4.6 8.4l2.3 2.3 4.6-4.9"/>',
    "mittel": '<path d="M8 4.6v4.2"/><path d="M8 11.4v.01" stroke-width="2.4"/>',
    "schlecht": '<path d="M5.4 5.4l5.2 5.2M10.6 5.4l-5.2 5.2"/>',
    "offen": '<path d="M6.2 6.3a1.9 1.9 0 1 1 2.7 1.7c-.6.3-.9.7-.9 1.3v.2"/><path d="M8 11.5v.01" stroke-width="2.4"/>',
    "ja": '<path d="M4.6 8.4l2.3 2.3 4.6-4.9"/>',
    "teils": '<circle cx="8" cy="8" r="3.6"/><path d="M8 4.4a3.6 3.6 0 0 1 0 7.2z" fill="currentColor" stroke="none"/>',
}


def zeichen(key: str) -> Markup:
    pfad = ZEICHEN.get(key, ZEICHEN["offen"])
    return Markup(f'<svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" '
                  f'stroke-linecap="round" stroke-linejoin="round">{pfad}</svg>')
