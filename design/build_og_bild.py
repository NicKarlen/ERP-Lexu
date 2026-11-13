"""Erzeugt das Vorschaubild für LinkedIn & Co. (erpverzeichnis/static/og-bild.png, 1200 × 627).

    .venv\\Scripts\\python design\\build_og_bild.py      (braucht Pillow: pip install -r design/requirements.txt)

Schriften: Segoe UI (Windows). Auf anderen Systemen wird auf eine Standardschrift ausgewichen.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJEKT = Path(__file__).resolve().parent.parent
STATIC = PROJEKT / "erpverzeichnis" / "static"
B, H = 1200, 627
TINTE, INDIGO, LAVENDEL, GRAU = (28, 26, 62), (91, 91, 214), (233, 233, 253), (74, 71, 112)


def schrift(namen, groesse):
    for n in namen:
        for ordner in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu")):
            if (ordner / n).exists():
                return ImageFont.truetype(str(ordner / n), groesse)
    return ImageFont.load_default(groesse)


def main():
    bild = Image.new("RGB", (B, H), (247, 246, 253))
    d = ImageDraw.Draw(bild)
    # Weicher Lavendel-Kreis hinter dem Maskottchen
    d.ellipse((770, 90, 1250, 620), fill=LAVENDEL)
    mk = Image.open(STATIC / "maskottchen" / "analyse-lupe.webp").convert("RGBA")
    mk.thumbnail((420, 420), Image.LANCZOS)
    bild.paste(mk, (790, 170), mk)

    titel = schrift(["seguibl.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"], 66)
    text = schrift(["segoeui.ttf", "DejaVuSans.ttf"], 30)
    klein = schrift(["segoeuib.ttf", "DejaVuSans-Bold.ttf"], 24)

    kopf = Image.open(STATIC / "maskottchen" / "kopf.png").convert("RGBA").resize((64, 64), Image.LANCZOS)
    d.ellipse((68, 66, 136, 134), fill=TINTE)
    bild.paste(kopf, (70, 68), kopf)
    d.text((152, 80), "ERP", font=klein, fill=INDIGO)
    d.text((152 + d.textlength("ERP", font=klein), 80), "-Verzeichnis", font=klein, fill=TINTE)

    y = 190
    for zeile in ("Welches ERP passt", "zu meinem Betrieb?"):
        d.text((70, y), zeile, font=titel, fill=TINTE)
        y += 82
    y += 18
    for zeile in ("Unabhängiges Verzeichnis für Schweizer KMU:", "Module, Schweiz-Funktionen, Preise, Datenschutz."):
        d.text((70, y), zeile, font=text, fill=GRAU)
        y += 42
    # Knopf
    d.rounded_rectangle((70, 500, 400, 562), radius=31, fill=INDIGO)
    d.text((100, 513), "Zum ERP-Berater  →", font=klein, fill=(255, 255, 255))
    ziel = STATIC / "og-bild.png"
    bild.save(ziel, optimize=True)
    print("Gespeichert:", ziel)


if __name__ == "__main__":
    main()
