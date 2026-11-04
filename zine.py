#!/usr/bin/env python3
"""8-page one-sheet mini zine maker.

One sheet, landscape, 4 x 2 panels. Fold + one cut in the middle -> 8-page booklet.
Imposition (how the pages sit on the sheet, top row printed upside down):

    +-------+-------+-------+-------+
    |  5 ^v |  4 ^v |  3 ^v |  2 ^v |   <- upside down
    +-------+=======+=======+-------+   == cut here (middle two panels only)
    |   6   |   7   | 8 back| 1 FRONT|
    +-------+-------+-------+-------+

Usage
  Blank printable templates for every style (written to ./templates):
      python3 zine.py blank
  Your real zine from photos + captions:
      python3 zine.py make --style polaroid --photos ./photos --captions captions.txt -o my_zine.pdf

  photos/    images, used in name order (01.jpg, 02.jpg ...). Phone rotation is fixed automatically.
  captions.txt   one line per page, 8 lines, "English | 中文" (either side may be empty):
      line 1 = cover title | cover subtitle
      lines 2-7 = captions for pages 2-7
      line 8 = back-cover note
Options: --paper a4|letter, --guides full|ticks|none, --by "your name", --date "Nov 2026"
Needs: Python 3.9+, rsvg-convert (librsvg) for PDF output, Pillow only when you pass --photos,
pdfunite (poppler) only for the combined ALL_templates.pdf.

https://github.com/nurasik14/pocket-zine  ·  MIT License
"""
import argparse
import base64
import html
import io
import shutil
import subprocess
import sys
from pathlib import Path

PAPER = {"a4": (297.0, 210.0), "letter": (279.4, 215.9)}  # landscape, mm
# (page number, column, row) ; row 0 = top (upside down)
IMPOSITION = [(5, 0, 0), (4, 1, 0), (3, 2, 0), (2, 3, 0),
              (6, 0, 1), (7, 1, 1), (8, 2, 1), (1, 3, 1)]

INK = "#2b2622"
SOFT = "#8a8178"
FAINT = "#d9d3ca"
ACCENT = "#9c3b2e"   # cinnabar red, same family as the Quest Journal accent
PAPERTONE = "#f4efe6"
SERIF = "'EB Garamond','Noto Serif CJK TC','Noto Serif',serif"
CJK = "'Noto Serif CJK TC','Noto Serif CJK HK',serif"
SANS = "'Noto Sans CJK TC','Noto Sans',sans-serif"
PT = 0.3528  # 1 pt in mm
M = 5.0      # inner safe margin per panel, mm


# ---------------------------------------------------------------- helpers
def esc(s):
    return html.escape(s or "", quote=True)


def is_cjk(ch):
    o = ord(ch)
    return 0x2E80 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0xFF00 <= o <= 0xFFEF or 0x3000 <= o <= 0x303F


def text_w(s, size_pt):
    em = size_pt * PT
    return sum(em * (1.0 if is_cjk(c) else (0.28 if c == " " else 0.47)) for c in s)


def wrap(s, size_pt, width, max_lines=3):
    """Greedy wrap. Latin wraps on spaces, CJK on any character."""
    if not s:
        return []
    tokens, buf = [], ""
    for ch in s:
        if is_cjk(ch):
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
        elif ch == " ":
            buf += ch
            tokens.append(buf)
            buf = ""
        else:
            buf += ch
    if buf:
        tokens.append(buf)
    lines, cur = [], ""
    for t in tokens:
        if cur and text_w(cur + t, size_pt) > width:
            lines.append(cur.rstrip())
            cur = t.lstrip()
        else:
            cur += t
    if cur.strip():
        lines.append(cur.rstrip())
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" ,.;") + "…"
    return lines


def text(x, y, s, size_pt, fill=INK, family=SERIF, anchor="start", weight=400, spacing=0, opacity=1):
    if not s:
        return ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{family}" font-size="{size_pt * PT:.3f}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{spacing}" '
            f'opacity="{opacity}">{esc(s)}</text>')


def para(x, y, s, size_pt, width, max_lines=3, lead=1.25, **kw):
    """Wrapped text block; returns (svg, height_used)."""
    lines = wrap(s, size_pt, width, max_lines)
    step = size_pt * PT * lead
    out = [text(x, y + i * step, ln, size_pt, **kw) for i, ln in enumerate(lines)]
    return "".join(out), len(lines) * step


def hline(x1, x2, y, stroke=FAINT, w=0.25, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.2f}" y1="{y:.2f}" x2="{x2:.2f}" y2="{y:.2f}" stroke="{stroke}" stroke-width="{w}"{d}/>'


class Ctx:
    """Per-page context: panel size, photo supply, captions, ids."""
    _uid = 0

    def __init__(self, w, h, page, en, zh, photos, by, date):
        self.w, self.h, self.page, self.en, self.zh = w, h, page, en, zh
        self._photos, self.by, self.date = photos, by, date

    def uid(self):
        Ctx._uid += 1
        return f"c{Ctx._uid}"

    def photo(self, x, y, w, h, label="photo"):
        """Photo cropped to fill the box, or a placeholder box when none is left."""
        src = self._photos.pop(0) if self._photos else None
        if src is None:
            cm = min(w, h) * 0.12
            corners = "".join(
                f'<path d="M{cx + dx * cm:.2f},{cy:.2f} L{cx:.2f},{cy:.2f} L{cx:.2f},{cy + dy * cm:.2f}" '
                f'fill="none" stroke="{SOFT}" stroke-width="0.35"/>'
                for cx, cy, dx, dy in [(x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)])
            return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#faf8f4" '
                    f'stroke="{FAINT}" stroke-width="0.25"/>' + corners +
                    text(x + w / 2, y + h / 2 + 1, label, 7, SOFT, SANS, "middle", spacing=0.4))
        cid = self.uid()
        return (f'<clipPath id="{cid}"><rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"/></clipPath>'
                f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                f'preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})" href="{src}"/>')

    def folio(self, color=SOFT):
        """Small page number at the outer bottom corner."""
        if self.page in (1, 8):
            return ""
        return text(self.w / 2, self.h - M + 1.2, f"— {self.page} —", 6.5, color, SERIF, "middle")


# ---------------------------------------------------------------- shared cover / back
def cover_classic(c, photo_h_ratio=0.5):
    w, h = c.w, c.h
    title = c.en or "Title of the walk"
    sub = c.zh or "副標題"
    out = [text(M, M + 4, "A POCKET ZINE", 6, ACCENT, SANS, spacing=0.8, weight=700)]
    out.append(hline(M, w - M, M + 6, ACCENT, 0.35))
    t, th = para(M, M + 16, title, 17, w - 2 * M, 3, 1.1, weight=600)
    out.append(t)
    y = M + 16 + th
    out.append(text(M, y + 1, sub, 10, INK, CJK))
    ph = h * photo_h_ratio
    out.append(c.photo(M, h - M - 8 - ph, w - 2 * M, ph, "cover photo"))
    out.append(text(M, h - M, c.date or "", 6.5, SOFT, SERIF))
    out.append(text(w - M, h - M, "香港", 6.5, SOFT, CJK, "end"))
    return "".join(out)


def back_classic(c, route_box=True):
    w, h = c.w, c.h
    out = []
    if route_box:
        bx, by_, bw, bh = M, M + 6, w - 2 * M, h * 0.45
        out.append(text(M, M + 3, "THE ROUTE · 路線", 6, SOFT, SANS, spacing=0.6, weight=700))
        out.append(f'<rect x="{bx}" y="{by_}" width="{bw}" height="{bh}" fill="none" stroke="{FAINT}" '
                   f'stroke-width="0.3" stroke-dasharray="1,1"/>')
        # a few dots to sketch the walk on
        for i in range(1, 6):
            for j in range(1, 8):
                out.append(f'<circle cx="{bx + bw * i / 6:.2f}" cy="{by_ + bh * j / 8:.2f}" r="0.25" fill="{FAINT}"/>')
    note = c.en or ""
    y = h * 0.62
    if note:
        t, nh = para(M, y, note, 8.5, w - 2 * M, 4, 1.3)
        out.append(t)
        y += nh
    out.append(text(w / 2, h - M - 12, "完", 16, ACCENT, CJK, "middle"))
    out.append(text(w / 2, h - M - 4, f"made by {c.by}" if c.by else "made by ______", 6.5, SOFT, SERIF, "middle"))
    return "".join(out)


# ---------------------------------------------------------------- styles
def st_grid(c):
    """The fixed version of the hand-made grid: just numbered panels."""
    w, h = c.w, c.h
    label = {1: "FRONT COVER", 8: "BACK COVER"}.get(c.page, f"PAGE {c.page}")
    return (text(w / 2, h / 2 + 8, str(c.page), 60, "#ece7df", SERIF, "middle", 600) +
            text(w / 2, M + 4, label, 7, SOFT, SANS, "middle", 700, 0.8) +
            text(w / 2, h - M, "top of page is toward the middle fold ↑" if c.page in (1, 6, 7, 8) else
                 "this panel prints upside down — that's correct", 5, "#b9b1a6", SANS, "middle"))


def st_polaroid(c):
    w, h = c.w, c.h
    if c.page == 8:
        return back_classic(c)
    fw = w - 2 * M - 4
    fx = (w - fw) / 2
    side = fw - 6
    fy = M + (10 if c.page == 1 else 6)
    fh = side + 3 + 20
    out = [f'<rect x="{fx + 0.6:.2f}" y="{fy + 0.8:.2f}" width="{fw:.2f}" height="{fh:.2f}" fill="#e8e2d8"/>',
           f'<rect x="{fx:.2f}" y="{fy:.2f}" width="{fw:.2f}" height="{fh:.2f}" fill="#ffffff" stroke="{FAINT}" stroke-width="0.25"/>',
           c.photo(fx + 3, fy + 3, side, side)]
    cy = fy + 3 + side + 7
    if c.page == 1:
        out.insert(0, text(w / 2, M + 4, "A POCKET ZINE", 6, ACCENT, SANS, "middle", 700, 0.8))
        t, _ = para(fx + 4, cy, c.en or "Title of the walk", 12, fw - 8, 1, weight=600)
        out.append(t)
        out.append(text(fx + 4, cy + 6.5, c.zh or "副標題", 8.5, INK, CJK))
        out.append(text(w / 2, h - M, c.date or "", 6.5, SOFT, SERIF, "middle"))
    else:
        if c.en or c.zh:
            t, used = para(fx + 4, cy, c.en, 8, fw - 8, 2, 1.2)
            out.append(t)
            out.append(text(fx + 4, cy + max(used, 0) + (1.5 if c.en else 0), c.zh, 8, INK, CJK))
        else:
            out.append(hline(fx + 4, fx + fw - 4, cy + 1))
            out.append(hline(fx + 4, fx + fw - 4, cy + 8))
        out.append(c.folio())
    return "".join(out)


def st_fullbleed(c):
    w, h = c.w, c.h
    out = [c.photo(0, 0, w, h, "full-page photo")]
    if c.page == 1:
        out.append(f'<rect x="0" y="0" width="{w}" height="{26}" fill="#ffffff" opacity="0.88"/>')
        t, th = para(M, M + 6, c.en or "Title of the walk", 14, w - 2 * M, 1, weight=600)
        out.append(t)
        out.append(text(M, M + 13, c.zh or "副標題", 9, INK, CJK))
        out.append(text(w - M, M + 18, c.date or "", 6, SOFT, SERIF, "end"))
        return "".join(out)
    if c.page == 8:
        out.append(f'<rect x="0" y="{h - 34}" width="{w}" height="34" fill="#ffffff" opacity="0.9"/>')
        t, _ = para(M, h - 26, c.en or "", 7.5, w - 2 * M, 2)
        out.append(t)
        out.append(text(w / 2, h - M - 4, "完", 12, ACCENT, CJK, "middle"))
        out.append(text(w / 2, h - M + 1, f"made by {c.by}" if c.by else "", 5.5, SOFT, SERIF, "middle"))
        return "".join(out)
    band = 17
    out.append(f'<rect x="0" y="{h - band - 2}" width="{w}" height="{band + 2}" fill="#ffffff" opacity="0.9"/>')
    t, used = para(M, h - band + 3, c.en, 7.5, w - 2 * M - 6, 1)
    out.append(t)
    out.append(text(M, h - band + 3 + (used + 1 if c.en else 0), c.zh, 7.5, INK, CJK))
    out.append(text(w - M, h - band + 3, str(c.page), 7, ACCENT, SERIF, "end", 600))
    return "".join(out)


def st_bilingual(c):
    w, h = c.w, c.h
    if c.page == 1:
        return cover_classic(c, 0.5)
    if c.page == 8:
        return back_classic(c)
    ph = h * 0.58
    out = [c.photo(M, M, w - 2 * M, ph)]
    y = M + ph + 6
    out.append(text(M, y, f"{c.page:02d}", 7, ACCENT, SERIF, weight=600))
    out.append(hline(M + 6, w - M, y - 1, ACCENT, 0.3))
    y += 6
    if c.en:
        t, used = para(M, y, c.en, 8.5, w - 2 * M, 2)
        out.append(t)
        y += used + 2
    else:
        out.append(hline(M, w - M, y + 1))
        y += 8
    if c.zh:
        t, used = para(M, y + 1, c.zh, 10, w - 2 * M, 2, 1.3, family=CJK)
        out.append(t)
    else:
        out.append(text(M, y + 2, "中文：", 7, SOFT, CJK))
        out.append(hline(M + 9, w - M, y + 2.5))
    out.append(c.folio())
    return "".join(out)


def st_specimen(c):
    """Apothecary field notes: each photo is a 'specimen' with a label."""
    w, h = c.w, c.h
    if c.page == 1:
        out = [f'<rect x="{M}" y="{M}" width="{w - 2 * M}" height="{h - 2 * M}" fill="none" stroke="{INK}" stroke-width="0.5"/>',
               f'<rect x="{M + 1.2}" y="{M + 1.2}" width="{w - 2 * M - 2.4}" height="{h - 2 * M - 2.4}" fill="none" stroke="{INK}" stroke-width="0.2"/>',
               text(w / 2, M + 9, "FIELD NOTES · 採集手記", 6, ACCENT, SANS, "middle", 700, 0.6)]
        t, th = para(M + 5, M + 20, c.en or "Title of the walk", 14, w - 2 * M - 10, 3, 1.1, weight=600)
        out.append(t)
        out.append(text(M + 5, M + 21 + th, c.zh or "副標題", 9, INK, CJK))
        ph = h * 0.38
        out.append(c.photo(M + 5, h - M - 12 - ph, w - 2 * M - 10, ph, "specimen photo"))
        out.append(text(w / 2, h - M - 5, c.date or "date ________", 6.5, SOFT, SERIF, "middle"))
        return "".join(out)
    if c.page == 8:
        return back_classic(c)
    out = [text(M, M + 3.5, f"SPECIMEN No. {c.page - 1:02d}", 6.5, ACCENT, SANS, weight=700, spacing=0.6),
           text(w - M, M + 3.5, f"標本 {c.page - 1}", 6.5, ACCENT, CJK, "end")]
    ph = (w - 2 * M) * 0.8
    out.append(c.photo(M, M + 6, w - 2 * M, ph, "specimen"))
    y = M + 6 + ph + 6
    # label card
    lh = h - y - M - 5
    out.append(f'<rect x="{M}" y="{y - 3}" width="{w - 2 * M}" height="{lh}" fill="none" stroke="{INK}" stroke-width="0.3"/>')
    rows = [("name / 名", c.en), ("中文", c.zh), ("place / 地點", ""), ("time / 時間", "")]
    step = (lh - 2) / len(rows)
    for i, (lab, val) in enumerate(rows):
        ry = y + 1.5 + i * step
        out.append(text(M + 2, ry, lab, 5.5, SOFT, SANS))
        if i < len(rows) - 1:
            out.append(hline(M + 2, w - M - 2, ry + step - 3.2))
        fam = CJK if lab == "中文" else SERIF
        if val:
            lines = wrap(val, 7.5, w - 2 * M - 19, 1)
            out.append(text(M + 17, ry + 0.3, lines[0], 7.5, INK, fam))
    out.append(c.folio())
    return "".join(out)


def st_duo(c):
    """Two photos per inside page -> 13 photos total (good for 'shoot 15')."""
    w, h = c.w, c.h
    if c.page == 1:
        return cover_classic(c, 0.5)
    if c.page == 8:
        return back_classic(c)
    gap = 3
    cap = 14
    ph = (h - 2 * M - gap - cap) / 2
    out = [c.photo(M, M, w - 2 * M, ph, "photo A"), c.photo(M, M + ph + gap, w - 2 * M, ph, "photo B")]
    y = M + 2 * ph + gap + 5
    if c.en or c.zh:
        t, used = para(M, y, c.en, 7.5, w - 2 * M, 1)
        out.append(t)
        out.append(text(M, y + (used + 0.5 if c.en else 0), c.zh, 7.5, INK, CJK))
    else:
        out.append(hline(M, w - M, y + 1))
    out.append(text(w - M, h - M + 1.2, str(c.page), 6.5, ACCENT, SERIF, "end", 600))
    return "".join(out)


def st_journal(c):
    """Small photo + lined space to write by hand."""
    w, h = c.w, c.h
    if c.page == 1:
        return cover_classic(c, 0.42)
    if c.page == 8:
        return back_classic(c, route_box=True)
    ph = h * 0.36
    out = [c.photo(M, M, w - 2 * M, ph)]
    y = M + ph + 7
    if c.en:
        t, used = para(M, y, c.en, 8, w - 2 * M, 2)
        out.append(t)
        y += used + 1
    if c.zh:
        out.append(text(M, y + 1, c.zh, 8, INK, CJK))
        y += 5
    while y < h - M - 7:
        y += 6
        out.append(hline(M, w - M, y))
    out.append(c.folio())
    return "".join(out)


STYLES = {
    "grid": (st_grid, "Numbered panels only. The fixed, correctly ordered version of the hand-drawn grid."),
    "polaroid": (st_polaroid, "Square instant-photo frame with a caption under it."),
    "fullbleed": (st_fullbleed, "Photo fills the whole page, caption on a white band."),
    "bilingual": (st_bilingual, "Photo on top, English caption + bigger Chinese caption below."),
    "specimen": (st_specimen, "Apothecary field notes: photo + label card (name / 中文 / place / time)."),
    "duo": (st_duo, "Two photos per page, 13 photos total."),
    "journal": (st_journal, "Smaller photo + lined space to write by hand."),
}


# ---------------------------------------------------------------- sheet
def guides(W, H, mode):
    pw, ph = W / 4, H / 2
    g = []
    if mode == "full":
        for i in (1, 2, 3):
            g.append(f'<line x1="{pw * i:.2f}" y1="0" x2="{pw * i:.2f}" y2="{H}" stroke="#b9b1a6" stroke-width="0.2" stroke-dasharray="2,1.5"/>')
        g.append(f'<line x1="0" y1="{ph}" x2="{pw}" y2="{ph}" stroke="#b9b1a6" stroke-width="0.2" stroke-dasharray="2,1.5"/>')
        g.append(f'<line x1="{3 * pw}" y1="{ph}" x2="{W}" y2="{ph}" stroke="#b9b1a6" stroke-width="0.2" stroke-dasharray="2,1.5"/>')
        g.append(f'<line x1="{pw}" y1="{ph}" x2="{3 * pw}" y2="{ph}" stroke="{ACCENT}" stroke-width="0.35"/>')
        g.append(text(2 * pw, ph - 1.2, "✂ cut only along this red line", 5, ACCENT, SANS, "middle"))
    elif mode == "ticks":
        t = 3.5
        for i in (1, 2, 3):
            g.append(f'<line x1="{pw * i:.2f}" y1="0" x2="{pw * i:.2f}" y2="{t}" stroke="{SOFT}" stroke-width="0.2"/>')
            g.append(f'<line x1="{pw * i:.2f}" y1="{H - t}" x2="{pw * i:.2f}" y2="{H}" stroke="{SOFT}" stroke-width="0.2"/>')
        g.append(f'<line x1="0" y1="{ph}" x2="{t}" y2="{ph}" stroke="{SOFT}" stroke-width="0.2"/>')
        g.append(f'<line x1="{W - t}" y1="{ph}" x2="{W}" y2="{ph}" stroke="{SOFT}" stroke-width="0.2"/>')
    return "".join(g)


def build_sheet(style, paper="a4", photos=None, captions=None, by="", date="", guide_mode="full"):
    W, H = PAPER[paper]
    pw, ph = W / 4, H / 2
    fn = STYLES[style][0]
    photos = photos if photos is not None else []  # consumed in place
    captions = captions or {}
    parts = [f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    # consume photos in reading order (page 1..8), not sheet order
    rendered = {}
    for page in range(1, 9):
        en, zh = captions.get(page, ("", ""))
        rendered[page] = fn(Ctx(pw, ph, page, en, zh, photos, by, date))
    for page, col, row in IMPOSITION:
        x, y = col * pw, row * ph
        if row == 0:  # upside down: top of the page faces the middle fold
            tf = f"translate({x + pw:.3f},{y + ph:.3f}) rotate(180)"
        else:
            tf = f"translate({x:.3f},{y:.3f})"
        parts.append(f'<g transform="{tf}">{rendered[page]}</g>')
    parts.append(guides(W, H, guide_mode))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">' + "".join(parts) + "</svg>")


def fold_guide(paper="a4"):
    """One-page illustrated how-to."""
    W, H = PAPER[paper]
    s = [f'<rect width="{W}" height="{H}" fill="#fff"/>',
         text(15, 22, "How to fold the 8-page zine", 20, INK, SERIF, weight=600),
         text(15, 30, "一張紙摺成八頁小誌", 11, ACCENT, CJK)]
    steps = [
        "1. Print the sheet at 100% / “Actual size” (not “Fit to page”), landscape, one-sided.",
        "2. Fold it in half the long way (top edge to bottom edge), crease, unfold.",
        "3. Fold it in half the short way, crease, unfold. Then fold each half again to the middle: 8 panels.",
        "4. Fold it in half the long way again. Cut along the middle crease, ONLY across the two centre panels (red line).",
        "5. Open it, fold long-ways again, and push the ends together so the cut opens into a diamond / plus shape.",
        "6. Flatten it into a booklet, front cover (page 1) on the outside. Crease all edges firmly.",
        "",
        "Why the top row is upside down: when you fold, those pages turn over and end up the right way up.",
        "Tip: phone photos with EXIF rotation are fixed by zine.py automatically.",
        "Tip: home printers can't print the last ~4 mm at the edges; full-page photos get a thin white rim there. That's normal.",
    ]
    for i, st in enumerate(steps):
        s.append(text(15, 45 + i * 7.5, st, 10, INK if st[:1].isdigit() else SOFT, SERIF))
    # mini imposition diagram
    dx, dy, dw, dh = 15, 128, 140, 70
    cw, ch = dw / 4, dh / 2
    for page, col, row in IMPOSITION:
        x, y = dx + col * cw, dy + row * ch
        s.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" fill="#faf8f4" stroke="{SOFT}" stroke-width="0.3"/>')
        lab = {1: "1 front", 8: "8 back"}.get(page, str(page))
        if row == 0:
            s.append(f'<g transform="translate({x + cw / 2},{y + ch / 2}) rotate(180)">'
                     + text(0, 2.5, lab, 11, INK, SERIF, "middle", 600) + "</g>")
        else:
            s.append(text(x + cw / 2, y + ch / 2 + 2.5, lab, 11, INK, SERIF, "middle", 600))
    s.append(f'<line x1="{dx + cw}" y1="{dy + ch}" x2="{dx + 3 * cw}" y2="{dy + ch}" stroke="{ACCENT}" stroke-width="0.8"/>')
    s.append(text(dx + dw / 2, dy + dh + 7, "red = the only cut. Top row prints upside down on purpose.", 8, ACCENT, SERIF, "middle"))
    s.append(text(170, 140, "Reading order after folding:", 10, INK, SERIF, weight=600))
    s.append(text(170, 148, "1 front cover → 2 → 3 → 4 → 5 → 6 → 7 → 8 back cover", 9, INK, SERIF))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">'
            + "".join(s) + "</svg>")


# ---------------------------------------------------------------- io
def load_photos(folder):
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("Pillow is needed for photos:  python3 -m pip install Pillow")
    if not Path(folder).expanduser().is_dir():
        sys.exit(f"photo folder not found: {folder}")
    exts = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff", ".bmp"}
    files = sorted(p for p in Path(folder).expanduser().iterdir() if p.suffix.lower() in exts)
    out = []
    for p in files:
        try:
            im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        except Exception as e:  # e.g. HEIC without a plugin
            print(f"skip {p.name}: {e}", file=sys.stderr)
            continue
        im.thumbnail((1000, 1000))  # ~300 dpi on a 74 x 105 mm page
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=86)
        out.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
    return out, [p.name for p in files]


def load_captions(path):
    caps = {}
    if not path:
        return caps
    lines = [ln.rstrip("\n") for ln in Path(path).expanduser().read_text(encoding="utf-8").splitlines()]
    lines = [ln for ln in lines if not ln.lstrip().startswith("#")]
    for i, ln in enumerate(lines[:8], start=1):
        en, _, zh = ln.partition("|")
        caps[i] = (en.strip(), zh.strip())
    return caps


def write_pdf(svg, out_pdf):
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    svg_path = out_pdf.with_suffix(".svg")
    svg_path.write_text(svg, encoding="utf-8")
    if not shutil.which("rsvg-convert"):
        sys.exit(f"wrote {svg_path}, but rsvg-convert is missing so no PDF was made.\n"
                 "Install librsvg: Fedora `sudo dnf install librsvg2-tools`, Debian/Ubuntu "
                 "`sudo apt install librsvg2-bin`, macOS `brew install librsvg`.")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(out_pdf), str(svg_path)], check=True)
    return out_pdf


def main():
    ap = argparse.ArgumentParser(description="8-page one-sheet mini zine maker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("blank", help="write blank printable templates for every style")
    b.add_argument("-o", "--out", default=str(Path(__file__).with_name("templates")))
    b.add_argument("--paper", choices=PAPER, default="a4")
    m = sub.add_parser("make", help="build a zine from photos + captions")
    m.add_argument("--style", choices=STYLES, default="polaroid")
    m.add_argument("--photos", help="folder of photos (used in name order)")
    m.add_argument("--captions", help="captions.txt: 8 lines 'English | 中文'")
    m.add_argument("--paper", choices=PAPER, default="a4")
    m.add_argument("--guides", choices=["full", "ticks", "none"], default="ticks")
    m.add_argument("--by", default="")
    m.add_argument("--date", default="")
    m.add_argument("-o", "--out", default="my_zine.pdf")
    sub.add_parser("styles", help="list styles")
    a = ap.parse_args()

    if a.cmd == "styles":
        for k, (_, d) in STYLES.items():
            print(f"{k:10s} {d}")
        return
    if a.cmd == "blank":
        out = Path(a.out)
        pdfs = [write_pdf(fold_guide(a.paper), out / "00_how-to-fold.pdf")]
        for i, k in enumerate(STYLES, start=1):
            pdfs.append(write_pdf(build_sheet(k, a.paper, guide_mode="full"), out / f"{i:02d}_{k}.pdf"))
        if shutil.which("pdfunite"):
            subprocess.run(["pdfunite", *map(str, pdfs), str(out / "ALL_templates.pdf")], check=False)
        print(f"wrote {len(pdfs)} templates to {out}")
        return
    photos, names = load_photos(a.photos) if a.photos else ([], [])
    caps = load_captions(a.captions)
    pool = list(photos)
    p = write_pdf(build_sheet(a.style, a.paper, pool, caps, a.by, a.date, a.guides), a.out)
    if a.photos:
        used = len(photos) - len(pool)
        print(f"{len(photos)} photos found; style '{a.style}' used {used}: {', '.join(names[:used])}")
        if pool:
            print(f"  unused: {', '.join(names[used:])}")
    print(f"wrote {p} (+ editable {p.with_suffix('.svg').name})")


if __name__ == "__main__":
    main()
