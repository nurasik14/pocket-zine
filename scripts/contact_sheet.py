#!/usr/bin/env python3
"""Combine the example renders into one hero image for the README (docs/images/hero.png)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMG = Path(__file__).resolve().parent.parent / "docs" / "images"
STYLES = ["polaroid", "fullbleed", "specimen", "duo"]


def main():
    shots = [Image.open(IMG / f"example_{s}.png").convert("RGB") for s in STYLES]
    tw = 900
    shots = [s.resize((tw, round(s.height * tw / s.width)), Image.LANCZOS) for s in shots]
    pad, label = 28, 44
    th = shots[0].height
    W = pad + 2 * (tw + pad)
    H = pad + 2 * (th + label + pad)
    sheet = Image.new("RGB", (W, H), (244, 239, 230))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    for i, (s, name) in enumerate(zip(shots, STYLES)):
        x = pad + (i % 2) * (tw + pad)
        y = pad + (i // 2) * (th + label + pad)
        d.text((x, y), f"--style {name}", fill=(156, 59, 46), font=font)
        d.rectangle([x + 3, y + label + 3, x + tw + 3, y + label + th + 3], fill=(214, 206, 194))
        sheet.paste(s, (x, y + label))
    sheet.save(IMG / "hero.png", optimize=True)
    print("wrote", IMG / "hero.png")


if __name__ == "__main__":
    main()
