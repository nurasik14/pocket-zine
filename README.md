<div align="center">

# pocket-zine

**One sheet of paper, one cut, eight pages.**<br>
Printable mini-zine templates and a small Python script that turns your photos and captions into a print-ready 8-page zine.

[![tests](https://github.com/nurasik14/pocket-zine/actions/workflows/tests.yml/badge.svg)](https://github.com/nurasik14/pocket-zine/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.9%2B-3776ab)
![paper](https://img.shields.io/badge/paper-A4%20%7C%20Letter-9c3b2e)
![license](https://img.shields.io/badge/license-MIT-green)

[Print a blank one](#print-a-blank-template) ·
[Make one from photos](#make-a-zine-from-your-photos) ·
[Fold it](#fold-it) ·
[Styles](#styles)

<img src="docs/images/hero.jpg" alt="Four example zines (polaroid, fullbleed, specimen and duo styles) laid out as printed A4 sheets" width="900">

<sub>Example sheets as they come out of the printer. The top row is upside down on purpose. Photos: Wikimedia Commons contributors, CC0 / CC BY (<a href="examples/photos/CREDITS.md">credits</a>).</sub>

</div>

---

## Contents

- [What it is](#what-it-is)
- [Print a blank template](#print-a-blank-template)
- [Make a zine from your photos](#make-a-zine-from-your-photos)
- [Fold it](#fold-it)
- [Styles](#styles)
- [Options](#options)
- [How it works](#how-it-works)
- [Development](#development)
- [Limitations](#limitations)
- [License and credits](#license-and-credits)

## What it is

A *zine* is a small, self-made booklet. The classic "one-sheet zine" is a single sheet of paper folded into
8 pages, with one cut in the middle. It's a nice home for photos from one walk, one trip or one day.

- **7 ready-to-print templates.** Polaroid frames, full-page photos, bilingual captions, field-note labels,
  two photos per page, a journal page, and a plain numbered grid.
- **Pages are in the right order.** The top row is printed upside down and pages run 5 4 3 2 / 6 7 8 1,
  so the folded booklet reads 1 → 8. You don't have to work that out yourself.
- **Photos to PDF in one command.** Put photos in a folder, write 8 lines of captions, run `zine.py`.
  Phone photos are turned the right way up and cropped to fit each frame.
- **Bilingual captions.** Every caption line is `English | 中文`. Chinese uses Noto Serif CJK TC.
- **Editable.** Each PDF comes with an `.svg` you can open in Inkscape or LibreOffice Draw to move things by hand.
- **No heavy dependencies.** Plain Python that writes SVG; `rsvg-convert` turns it into PDF.

## Print a blank template

You don't need to install anything for this. Download a PDF, print it, then glue in printed photos or draw and
write by hand.

| File | What's on it |
|---|---|
| [`templates/ALL_templates.pdf`](templates/ALL_templates.pdf) | Every template plus the folding guide, 8 pages |
| [`templates/00_how-to-fold.pdf`](templates/00_how-to-fold.pdf) | Folding steps and a map of which panel becomes which page |
| [`templates/01_grid.pdf`](templates/01_grid.pdf) | Eight equal, numbered panels, fold lines and the cut line |
| [`templates/02_polaroid.pdf`](templates/02_polaroid.pdf) | Square instant-photo frames with a caption line |
| [`templates/03_fullbleed.pdf`](templates/03_fullbleed.pdf) | Photo fills the page, caption on a white band |
| [`templates/04_bilingual.pdf`](templates/04_bilingual.pdf) | Photo, English caption, bigger Chinese caption |
| [`templates/05_specimen.pdf`](templates/05_specimen.pdf) | "Field notes": photo plus a label card (name / 中文 / place / time) |
| [`templates/06_duo.pdf`](templates/06_duo.pdf) | Two photos per page |
| [`templates/07_journal.pdf`](templates/07_journal.pdf) | Smaller photo and lines to write on |

> **Print at 100% / "Actual size"**, landscape, one-sided. "Fit to page" shrinks the panels and the folds stop
> lining up.

## Make a zine from your photos

### 1. Install

You need Python 3.9+, `rsvg-convert` (librsvg) and Pillow. Optional: Ghostscript (`gs`) shrinks photo zines from
~10 MB to ~1–2 MB, and `pdfunite` (poppler) builds the combined `ALL_templates.pdf`.

```bash
git clone https://github.com/nurasik14/pocket-zine.git
cd pocket-zine
python3 -m pip install Pillow

# rsvg-convert + pdfunite
sudo dnf install librsvg2-tools poppler-utils          # Fedora
sudo apt install librsvg2-bin poppler-utils            # Debian / Ubuntu
brew install librsvg poppler                           # macOS
```

For the intended look, also install the fonts (the script falls back to any serif font if they're missing):
[EB Garamond](https://fonts.google.com/specimen/EB+Garamond) for English and
[Noto Serif / Sans CJK TC](https://fonts.google.com/noto/specimen/Noto+Serif+TC) for Chinese
(`google-noto-serif-cjk-fonts` on Fedora, `fonts-noto-cjk` on Debian/Ubuntu).

### 2. Add your photos

Copy your photos into `my-zine/photos/` and name them in the order you want them:

```text
my-zine/photos/
├── 01.jpg   ← front cover
├── 02.jpg   ← page 2
├── ...
└── 08.jpg
```

Photos are used in file-name order. JPEG, PNG, WebP, TIFF and BMP work. Convert iPhone `.heic` files to JPEG first.
Most styles use 7 photos, `fullbleed` uses 8 and `duo` uses 13 (see [Styles](#styles)). The script tells you which
files it used and which were left over.

The photo folder is in `.gitignore`, so your photos don't end up on GitHub by accident.

### 3. Write the captions

Edit [`my-zine/captions.txt`](my-zine/captions.txt). It has 8 lines, one per page, written as `English | 中文`.
Either side can be empty, and lines starting with `#` are ignored.

```text
# line 1 = cover title | subtitle, lines 2-7 = pages 2-7, line 8 = back cover note
Tai Hang after the rain | 雨後大坑
Laundry drying on the fourth floor | 四樓晾衫
A tram bell somewhere behind the market | 電車鈴聲
Lights coming on above the noodle shop | 華燈初上
Steps up to Lin Fa Kung | 蓮花宮的石級
The fire dragon lane, quiet on a Thursday | 安靜的火龍巷
Dried herbs, sold by the tael | 乾貨藥材
One afternoon, eight pages. Thanks for walking with me. | 多謝同行
```

Keep captions short, one sentence each. Long ones wrap to two lines and then get cut off with `…`.

### 4. Build

```bash
python3 zine.py make --style polaroid \
    --photos my-zine/photos --captions my-zine/captions.txt \
    --by "your name" --date "Nov 2026" \
    -o my-zine/zine.pdf
```

Open `my-zine/zine.pdf` and print it. To try another look, change `--style` and run it again.

To try it before you have photos, use the bundled examples:

```bash
python3 zine.py make --style specimen --photos examples/photos --captions examples/captions.txt -o /tmp/try.pdf
```

## Fold it

<img src="docs/images/imposition.png" alt="The sheet: top row pages 5 4 3 2 printed upside down, bottom row 6 7 8-back 1-front, red cut line across the middle two panels" width="560">

1. Fold the sheet in half the long way (top edge to bottom edge), crease it, and unfold.
2. Fold it in half the short way, then fold each half to the middle again. You now have 8 panels. Unfold.
3. Fold it in half the long way again. **Cut along the middle crease, only across the two centre panels.**
4. Open it, fold it the long way once more, and push the two ends together. The cut opens into a diamond.
5. Flatten it into a booklet with the front cover (page 1) on the outside, and crease all the edges.

[`templates/00_how-to-fold.pdf`](templates/00_how-to-fold.pdf) has the same steps on one printable page.

## Styles

| Style | Photos used | Good for |
|---|:-:|---|
| `polaroid` | 7 | Classic instant-photo look: square photo in a white frame, caption underneath |
| `fullbleed` | 8 | Strong photos that should fill the whole page |
| `bilingual` | 7 | Language practice: an English line and a bigger Chinese line under each photo |
| `specimen` | 7 | Field notes: each photo gets a label card (name, 中文, place, time) |
| `duo` | 13 | Lots of photos: two per page |
| `journal` | 7 | More writing than photos: small photo and ruled lines |
| `grid` | 0 | A blank, numbered sheet to draw on or plan with |

The back cover (page 8) usually has a dotted box to sketch your route, your note, 完 and "made by …".

<details>
<summary><b>Show every style, filled and blank</b></summary>

| Filled with photos | Blank template |
|---|---|
| **polaroid**<br><img src="docs/images/example_polaroid.jpg" width="420"> | <img src="docs/images/template_polaroid.png" width="420"> |
| **fullbleed**<br><img src="docs/images/example_fullbleed.jpg" width="420"> | <img src="docs/images/template_fullbleed.png" width="420"> |
| **bilingual**<br><img src="docs/images/example_bilingual.jpg" width="420"> | <img src="docs/images/template_bilingual.png" width="420"> |
| **specimen**<br><img src="docs/images/example_specimen.jpg" width="420"> | <img src="docs/images/template_specimen.png" width="420"> |
| **duo**<br><img src="docs/images/example_duo.jpg" width="420"> | <img src="docs/images/template_duo.png" width="420"> |
| **journal**<br><img src="docs/images/example_journal.jpg" width="420"> | <img src="docs/images/template_journal.png" width="420"> |
| **grid** | <img src="docs/images/template_grid.png" width="420"> |
| **how to fold** | <img src="docs/images/template_how-to-fold.png" width="420"> |

</details>

## Options

```text
python3 zine.py styles                     list the styles
python3 zine.py blank  [-o DIR] [--paper]  write every blank template (default: ./templates)
python3 zine.py make   [options]           build a zine from photos and captions
```

| Option (`make`) | Default | What it does |
|---|---|---|
| `--style` | `polaroid` | `grid` `polaroid` `fullbleed` `bilingual` `specimen` `duo` `journal` |
| `--photos DIR` | none | Folder of photos, used in name order. Without it you get empty photo boxes |
| `--captions FILE` | none | `captions.txt` with 8 lines of `English \| 中文` |
| `--paper` | `a4` | `a4` or `letter` |
| `--guides` | `ticks` | `ticks` = small fold marks at the edges, `full` = every fold line and the cut line, `none` |
| `--by` | empty | Name on the back cover ("made by …") |
| `--date` | empty | Date on the cover |
| `-o FILE` | `my_zine.pdf` | Output PDF. An editable `.svg` is written next to it |

## How it works

```mermaid
flowchart LR
    A["photos/ +<br/>captions.txt"] --> B["zine.py<br/>draws 8 pages"]
    B --> C["places pages<br/>on the sheet"]
    C --> D["sheet.svg<br/>(mm units)"]
    D --> E["rsvg-convert<br/>SVG → PDF"]
    E --> F["zine.pdf<br/>print + fold"]
```

1. Each style is one function, `st_<name>(c)`, that draws a single page in millimetres. `c` holds the page
   number, its caption, and the supply of photos.
2. Pages are drawn in reading order (1 to 8), so photo `01` is always the cover, whatever the style.
3. Each page is placed on the sheet in its panel. Top-row panels get `rotate(180)` so they come out the right way
   up after folding.
4. Photos are rotated using their EXIF data, scaled to about 1000 px, and embedded in the SVG. They're cropped to
   their frames with `preserveAspectRatio="xMidYMid slice"`, so nothing is stretched or letterboxed.
5. `rsvg-convert` turns the SVG into a vector PDF. Text stays sharp, and the fonts are embedded.

### Adding a style

Write a function and register it:

```python
def st_postcard(c):
    out = [c.photo(M, M, c.w - 2 * M, c.h * 0.5)]            # takes the next photo, or draws an empty box
    out.append(text(M, c.h * 0.5 + 12, c.en, 9))            # English caption
    out.append(text(M, c.h * 0.5 + 18, c.zh, 9, family=CJK))
    out.append(c.folio())                                    # page number
    return "".join(out)

STYLES["postcard"] = (st_postcard, "Photo on top, caption underneath.")
```

Then add its photo count to `tests/test_zine.py` and run the tests.

## Development

```bash
python3 -m unittest discover -s tests -v   # 11 tests, no rsvg or Pillow needed
bash scripts/build_all.sh                  # rebuild templates/, examples/ and docs/images/
```

```text
pocket-zine/
├── zine.py                     the whole tool: styles, imposition, CLI
├── templates/                  printable blank PDFs + editable SVGs (made by `zine.py blank`)
├── my-zine/
│   ├── captions.txt            your 8 caption lines
│   └── photos/                 your photos (git-ignored)
├── examples/
│   ├── captions.txt            captions for the example zine
│   ├── photos/                 14 real Hong Kong photos + CREDITS.md
│   └── polaroid.pdf            a finished example
├── scripts/
│   ├── build_all.sh            regenerate everything
│   ├── fetch_example_photos.py downloads the example photos from Wikimedia Commons + writes credits
│   └── contact_sheet.py        builds docs/images/hero.jpg
├── docs/images/                README pictures (hero, previews, fold diagram)
├── tests/test_zine.py          imposition, every style, captions, text wrapping
└── .github/workflows/tests.yml CI: unit tests + a real PDF build on Ubuntu
```

## Limitations

- **Edges.** Home printers can't print the outer ~4 mm of a sheet, so full-page photos get a thin white rim there.
  Text is kept at least 5 mm from every edge.
- **Captions are wrapped by estimate.** SVG has no automatic line wrapping, so line breaks are worked out from
  approximate character widths. Very long captions are cut off with `…`.
- **File size.** `rsvg-convert` stores photos losslessly (~10 MB per zine). If Ghostscript is installed, `zine.py`
  re-saves them as 300 dpi JPEG automatically, which gives ~1–2 MB.
- **HEIC** (iPhone) photos need converting to JPEG first.
- **Windows** needs `rsvg-convert` from MSYS2, or use WSL.

## License and credits

- Code and templates: [MIT](LICENSE) © 2026 Nurassyl Serikov.
- The fonts aren't bundled. EB Garamond and Noto CJK are both under the SIL Open Font License.
- The example photos in `examples/photos/` (also shown in `docs/images/` and `examples/*.pdf`) are by Wikimedia
  Commons contributors and keep their own licenses, CC0 or CC BY 2.0 / 4.0, **not** MIT. Authors and links are in
  [`examples/photos/CREDITS.md`](examples/photos/CREDITS.md). They were only resized.
- The one-sheet zine fold is a traditional format that belongs to everyone.
