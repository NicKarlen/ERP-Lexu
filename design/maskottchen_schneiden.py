r"""Schneidet die Maskottchen aus den Bildbögen in docs/Maskottchen/ und legt sie als WebP in erpverzeichnis/static/maskottchen/ ab.

    .venv\Scripts\python design\maskottchen_schneiden.py      (braucht Pillow: pip install pillow)

Analyse-Bogen (weisser Grund): Hintergrund wird transparent.
Security-Bogen (schwarzer Grund mit Leuchten): bleibt schwarz und wird auf dunklen Flächen mit
`mix-blend-mode: screen` eingeblendet – dadurch verschwindet das Schwarz und nur das Leuchten bleibt.
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

PROJEKT = Path(__file__).resolve().parent.parent
QUELLE = PROJEKT / "docs" / "Maskottchen"
ZIEL = PROJEKT / "erpverzeichnis" / "static" / "maskottchen"

# Name -> Ausschnitt (links, oben, rechts, unten) im Bogen
ANALYSE = {
    "lupe": (40, 30, 560, 470),        # Marktforschung
    "laptop": (560, 50, 1060, 470),    # ERP-Recherche
    "checkliste": (1080, 10, 1500, 480),  # Anbietervergleich
    "tablet": (0, 500, 560, 960),      # Datenanalyse
    "wachstum": (560, 500, 1020, 960),  # Marktentwicklung
    "pokal": (1030, 510, 1500, 980),   # Erfolgreicher Abschluss
}
SECURITY = {
    "laptop": (110, 110, 500, 480),
    "schild": (590, 120, 960, 480),
    "dokument": (1080, 120, 1460, 480),
    "code": (300, 570, 700, 930),
    "zone": (820, 570, 1240, 930),
}


def transparent(bild: Image.Image) -> Image.Image:
    """Weissen Hintergrund (vom Rand her zusammenhängend) transparent machen, Kanten weich."""
    rgb = bild.convert("RGB")
    w, h = rgb.size
    hell = rgb.convert("L").point(lambda v: 255 if v > 232 else 0)
    # Fülle vom Rand aus: nur das zusammenhängende Weiss gilt als Hintergrund
    maske = Image.new("L", (w + 2, h + 2), 255)
    maske.paste(hell, (1, 1))
    ImageDraw.floodfill(maske, (0, 0), 128)
    hg = maske.crop((1, 1, w + 1, h + 1)).point(lambda v: 255 if v == 128 else 0)
    alpha = ImageChops.invert(hg).filter(ImageFilter.GaussianBlur(0.8))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(out.getbbox())


def main():
    ZIEL.mkdir(parents=True, exist_ok=True)
    analyse = Image.open(QUELLE / "Maskottchen Analyse.png")
    for name, box in ANALYSE.items():
        bild = transparent(analyse.crop(box))
        bild.thumbnail((440, 440), Image.LANCZOS)
        bild.save(ZIEL / f"analyse-{name}.webp", quality=88, method=6)
    security = Image.open(QUELLE / "Maskottchen Security.png").convert("RGB")
    for name, box in SECURITY.items():
        bild = security.crop(box)
        bild.thumbnail((400, 400), Image.LANCZOS)
        bild.save(ZIEL / f"security-{name}.webp", quality=88, method=6)
    # Kopf für Avatar und Favicon: runder Ausschnitt des fröhlichen Gesichts («pokal»)
    for name, (cx, cy, r) in {"kopf": (1300, 672, 168), "kopf-ruhig": (770, 205, 168)}.items():
        roh = analyse.crop((cx - r, cy - r, cx + r, cy + r)).convert("RGBA")
        kreis = Image.new("L", roh.size, 0)
        ImageDraw.Draw(kreis).ellipse((0, 0, roh.size[0] - 1, roh.size[1] - 1), fill=255)
        roh.putalpha(kreis)
        roh = roh.resize((192, 192), Image.LANCZOS)
        roh.save(ZIEL / f"{name}.webp", quality=90, method=6)
        roh.save(ZIEL / f"{name}.png")
    print("Maskottchen gespeichert in", ZIEL)


if __name__ == "__main__":
    main()
