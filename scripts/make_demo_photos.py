#!/usr/bin/env python3
"""Draw 14 made-up "street photos" (skies, hills, tower blocks, a tram, neon) for the README examples.

They're generated so the repo ships no real photos and no third-party images.
    python3 scripts/make_demo_photos.py examples/photos
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SKIES = [  # (top, bottom) colours
    ((126, 170, 214), (236, 222, 200)),   # clear afternoon
    ((244, 164, 120), (252, 226, 178)),   # golden hour
    ((58, 52, 104), (226, 130, 120)),     # dusk
    ((18, 22, 48), (60, 44, 86)),         # night
    ((176, 188, 196), (226, 228, 226)),   # overcast after rain
]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky(d, w, h, top, bottom):
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp(top, bottom, y / h))


def hills(d, w, h, base, colour, rnd, amp=0.08):
    pts = [(0, h)]
    phase = rnd.random() * 6
    for x in range(0, w + 20, 20):
        y = base + math.sin(x / w * 5 + phase) * h * amp + math.sin(x / w * 13 + phase) * h * amp * 0.3
        pts.append((x, y))
    pts.append((w, h))
    d.polygon(pts, fill=colour)


def towers(d, w, h, ground, rnd, night):
    x = -rnd.randint(0, 40)
    while x < w:
        bw = rnd.randint(int(w * 0.07), int(w * 0.16))
        bh = rnd.randint(int(h * 0.25), int(h * 0.62))
        shade = rnd.randint(40, 90) if night else rnd.randint(150, 215)
        body = (shade, shade - 6, shade - 10) if not night else (shade // 2, shade // 2, shade)
        d.rectangle([x, ground - bh, x + bw, ground], fill=body)
        win = (255, 214, 140) if night else (lerp(body, (255, 255, 255), 0.35))
        for wy in range(int(ground - bh + 14), int(ground - 10), 22):
            for wx in range(x + 8, x + bw - 10, 18):
                if not night or rnd.random() < 0.45:
                    d.rectangle([wx, wy, wx + 8, wy + 10], fill=win)
        x += bw + rnd.randint(2, 18)


def tram(d, w, ground):
    tw, th = w * 0.42, w * 0.26
    x0 = w * 0.3
    d.rectangle([x0, ground - th, x0 + tw, ground - 10], fill=(28, 104, 70))
    d.rectangle([x0 + 6, ground - th * 0.55, x0 + tw - 6, ground - th * 0.45], fill=(240, 236, 220))
    for i in range(5):
        wx = x0 + 12 + i * (tw - 24) / 5
        d.rectangle([wx, ground - th * 0.92, wx + (tw - 24) / 5 - 8, ground - th * 0.62], fill=(220, 236, 240))
    d.line([(0, ground - th - 30), (w, ground - th - 34)], fill=(40, 40, 40), width=3)
    d.ellipse([x0 + 20, ground - 22, x0 + 44, ground + 2], fill=(30, 30, 30))
    d.ellipse([x0 + tw - 44, ground - 22, x0 + tw - 20, ground + 2], fill=(30, 30, 30))


def neon(d, w, h, rnd):
    for _ in range(5):
        x, y = rnd.randint(0, w - 140), rnd.randint(int(h * 0.2), int(h * 0.6))
        col = rnd.choice([(255, 70, 110), (80, 220, 255), (255, 200, 60), (180, 110, 255)])
        bw, bh = rnd.randint(60, 140), rnd.randint(110, 240)
        d.rectangle([x, y, x + bw, y + bh], outline=col, width=6)
        for k in range(3):
            d.line([(x + 14, y + 26 + k * 34), (x + bw - 14, y + 26 + k * 34)], fill=col, width=7)


def make(i, rnd):
    portrait = i % 3 == 0
    w, h = (1200, 1600) if portrait else (1600, 1200)
    top, bottom = SKIES[i % len(SKIES)]
    night = top[0] < 30
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    sky(d, w, h, top, bottom)
    if not night and rnd.random() < 0.7:
        r = rnd.randint(50, 110)
        cx, cy = rnd.randint(r, w - r), rnd.randint(int(h * 0.1), int(h * 0.35))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=lerp(bottom, (255, 250, 230), 0.7))
    hills(d, w, h, h * 0.5, lerp(top, (40, 70, 60), 0.55), rnd)
    hills(d, w, h, h * 0.6, lerp(top, (30, 60, 45), 0.75), rnd, 0.05)
    ground = int(h * 0.86)
    kind = i % 4
    if kind in (0, 1):
        towers(d, w, h, ground, rnd, night)
    if kind == 2:
        tram(d, w, ground)
    if night:
        neon(d, w, h, rnd)
    d.rectangle([0, ground, w, h], fill=lerp(bottom, (60, 60, 60), 0.6))
    return im.filter(ImageFilter.GaussianBlur(1.2))


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/photos")
    out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(7)
    for i in range(14):
        make(i, rnd).save(out / f"{i + 1:02d}.jpg", quality=88)
    print(f"wrote 14 demo photos to {out}")


if __name__ == "__main__":
    main()
