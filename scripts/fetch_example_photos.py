#!/usr/bin/env python3
"""Download the example photos from Wikimedia Commons and write their credits.

Every photo is CC0, public domain or CC BY, so the examples can be shared with attribution.
They are resized to 1400 px on the long side; nothing else is changed.

    python3 scripts/fetch_example_photos.py            # -> examples/photos/ + examples/photos/CREDITS.md
"""
import html
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# (local name, Wikimedia Commons file). Order = page order in the zine.
PHOTOS = [
    ("01.jpg", "Hong Kong Tram (9732978330).jpg"),
    ("02.jpg", "Colorful apartment buildings in Hong Kong.jpg"),
    ("03.jpg", "Building Facade in Hong Kong.jpg"),
    ("04.jpg", "HK SW 上環 Sheung Wan 皇后大道中 Queen's Road Central dried goods shop December 2023 R12S 01.jpg"),
    ("05.jpg", "Incense coils at Man Mo Temple, Tai Po - 7985907663.jpg"),
    ("06.jpg", "Hong Kong ~ Lockhart Road 駱克道 Club Bunny 霓虹燈招牌 Neon Sign.jpg"),
    ("07.jpg", "Hong Kong Alleys (53042872525).jpg"),
    ("08.jpg", "Celestial Star ferry Hong Kong (8112199340).jpg"),
    ("09.jpg", "Goldfish Market, Mongkok, Hong Kong (9729617285).jpg"),
    ("10.jpg", "Red Minibuses and Urban Density Mong Kok Hong Kong.jpg"),
    ("11.jpg", "Trams Hong Kong (8656004701).jpg"),
    ("12.jpg", "Night Market near Public Square in Hong Kong (6993753893).jpg"),
    ("13.jpg", "Hong Kong real estate agents' street advertisements 2012.jpg"),
    ("14.jpg", "Cruising Hong Kong Harbour. (14112601126).jpg"),
]
ALLOWED = re.compile(r"^(CC0|Public domain|CC BY \d\.\d)$")
UA = {"User-Agent": "pocket-zine/1.0 (https://github.com/nurasik14/pocket-zine)"}
API = "https://commons.wikimedia.org/w/api.php"


def get(url, tries=6):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and k < tries - 1:
                time.sleep(10 * (k + 1))
                continue
            raise


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def main():
    from PIL import Image

    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "examples" / "photos")
    out.mkdir(parents=True, exist_ok=True)
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "imageinfo",
        "iiprop": "url|extmetadata", "iiurlwidth": 1600,
        "titles": "|".join("File:" + f for _, f in PHOTOS)})
    pages = json.loads(get(f"{API}?{q}"))["query"]["pages"].values()
    info = {p["title"][5:]: p["imageinfo"][0] for p in pages if "imageinfo" in p}

    rows = []
    for local, name in PHOTOS:
        ii = info.get(name)
        if ii is None:
            sys.exit(f"not found on Commons: {name}")
        m = ii["extmetadata"]
        lic = m.get("LicenseShortName", {}).get("value", "").strip()
        if not ALLOWED.match(lic):
            sys.exit(f"{name}: license {lic!r} is not CC0 / public domain / CC BY")
        im = Image.open(io.BytesIO(get(ii["thumburl"]))).convert("RGB")
        im.thumbnail((1400, 1400))
        im.save(out / local, "JPEG", quality=84, optimize=True)
        rows.append((local, clean(m.get("ObjectName", {}).get("value", "")) or name,
                     clean(m.get("Artist", {}).get("value", "")) or "unknown",
                     lic, m.get("LicenseUrl", {}).get("value", ""), ii["descriptionurl"]))
        print(f"{local}  {lic:10s} {name}")
        time.sleep(1)

    lines = ["# Example photo credits", "",
             "Real photos from [Wikimedia Commons](https://commons.wikimedia.org), used under their own licenses",
             "(not the repo's MIT license). Each was resized to 1400 px on the long side; nothing else was changed.",
             "The same photos appear in `docs/images/` and `examples/*.pdf`.", "",
             "| File | Photo | Author | License |", "|---|---|---|---|"]
    for local, title, artist, lic, licurl, page in rows:
        lic_md = f"[{lic}]({licurl})" if licurl else lic
        lines.append(f"| `{local}` | [{title.replace('|', '/')}]({page}) | {artist.replace('|', '/')} | {lic_md} |")
    (out / "CREDITS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} photos + CREDITS.md to {out}")


if __name__ == "__main__":
    main()
