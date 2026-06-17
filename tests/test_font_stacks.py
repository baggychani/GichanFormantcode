# tests/test_font_stacks.py
"""font_stacks: assets/fonts 번들 패밀리만 사용."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

import config
from utils import font_stacks as fs


class TestFontStacks(unittest.TestCase):
    def test_serif_axis_uses_bundled_stack(self):
        config.USE_POSTER_FONT_STACK = False
        self.assertEqual(fs.axis_font_list("serif"), fs.FONT_LEGACY_SERIF_AXIS)

    def test_poster_flag_same_as_legacy_serif_axis(self):
        config.USE_POSTER_FONT_STACK = True
        self.assertEqual(fs.axis_font_list("serif"), fs.FONT_LEGACY_SERIF_AXIS)
        self.assertNotIn("STIX Two Text", fs.axis_font_list("serif"))

    def test_ipa_label_charis_only(self):
        config.USE_POSTER_FONT_STACK = True
        families, serif_medium = fs.label_font_family("/o/", "serif")
        self.assertEqual(families, ["Charis SIL"])
        self.assertFalse(serif_medium)

    def test_legacy_ipa_label_charis_only(self):
        config.USE_POSTER_FONT_STACK = False
        families, _ = fs.label_font_family("/o/", "serif")
        self.assertEqual(families, ["Charis SIL"])

    def test_korean_serif_keeps_noto_first(self):
        config.USE_POSTER_FONT_STACK = True
        families, serif_medium = fs.label_font_family("모음", "serif")
        self.assertEqual(families[0], "Noto Serif KR")
        self.assertTrue(serif_medium)


if __name__ == "__main__":
    unittest.main()
