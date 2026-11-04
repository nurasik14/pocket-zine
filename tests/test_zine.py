"""Tests for zine.py. Pure Python: no rsvg-convert or Pillow needed.

    python3 -m unittest discover -s tests -v
"""
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import zine  # noqa: E402

FAKE = "data:image/jpeg;base64,AAAA"


class Imposition(unittest.TestCase):
    def test_every_page_once(self):
        self.assertEqual(sorted(p for p, _, _ in zine.IMPOSITION), list(range(1, 9)))

    def test_standard_order(self):
        top = [p for p, c, r in sorted(zine.IMPOSITION, key=lambda t: t[1]) if r == 0]
        bottom = [p for p, c, r in sorted(zine.IMPOSITION, key=lambda t: t[1]) if r == 1]
        self.assertEqual(top, [5, 4, 3, 2])
        self.assertEqual(bottom, [6, 7, 8, 1])

    def test_top_row_is_rotated(self):
        svg = zine.build_sheet("grid")
        self.assertEqual(svg.count("rotate(180)"), 4)


class Sheets(unittest.TestCase):
    def test_every_style_is_valid_svg(self):
        for paper in zine.PAPER:
            for style in zine.STYLES:
                with self.subTest(style=style, paper=paper):
                    root = ET.fromstring(zine.build_sheet(style, paper))
                    self.assertTrue(root.tag.endswith("svg"))

    def test_paper_size(self):
        root = ET.fromstring(zine.build_sheet("grid", "a4"))
        self.assertEqual(root.get("viewBox"), "0 0 297.0 210.0")

    def test_photos_used_per_style(self):
        expected = {"grid": 0, "polaroid": 7, "fullbleed": 8, "bilingual": 7,
                    "specimen": 7, "duo": 13, "journal": 7}
        self.assertEqual(set(expected), set(zine.STYLES))
        for style, n in expected.items():
            pool = [FAKE] * 20
            zine.build_sheet(style, photos=pool)
            with self.subTest(style=style):
                self.assertEqual(20 - len(pool), n)

    def test_captions_are_escaped(self):
        caps = {2: ("Tom & Jerry <3", "大坑")}
        svg = zine.build_sheet("bilingual", captions=caps)
        ET.fromstring(svg)  # would raise on a bare & or <
        self.assertIn("Tom &amp; Jerry &lt;3", svg)
        self.assertIn("大坑", svg)


class Text(unittest.TestCase):
    def test_wrap_respects_width(self):
        s = "The fire dragon lane, quiet on a Thursday afternoon after the rain"
        for line in zine.wrap(s, 8, 50, max_lines=10):
            self.assertLessEqual(zine.text_w(line, 8), 50 + 0.01)

    def test_wrap_cjk_per_character(self):
        lines = zine.wrap("一二三四五六七八九十" * 3, 10, 20, max_lines=10)
        self.assertGreater(len(lines), 1)

    def test_wrap_ellipsis(self):
        lines = zine.wrap("word " * 80, 8, 40, max_lines=2)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[-1].endswith("…"))

    def test_load_captions(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.txt"
            p.write_text("# comment\nTitle | 標題\nonly english\n| 只有中文\n", encoding="utf-8")
            caps = zine.load_captions(p)
        self.assertEqual(caps[1], ("Title", "標題"))
        self.assertEqual(caps[2], ("only english", ""))
        self.assertEqual(caps[3], ("", "只有中文"))


if __name__ == "__main__":
    unittest.main()
