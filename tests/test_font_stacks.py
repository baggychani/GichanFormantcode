# tests/test_font_stacks.py
"""font_stacks: 포스터 STIX 우선 / legacy 롤백."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest

import config
from utils import font_stacks as fs


class TestFontStacks(unittest.TestCase):
    def test_legacy_serif_axis_unchanged_when_poster_off(self):
        config.USE_POSTER_FONT_STACK = False
        self.assertEqual(fs.axis_font_list("serif"), fs.FONT_LEGACY_SERIF_AXIS)

    def test_poster_serif_axis_stix_first(self):
        config.USE_POSTER_FONT_STACK = True
        stack = fs.axis_font_list("serif")
        self.assertEqual(stack[0], "STIX Two Text")
        self.assertIn("Noto Serif KR", stack)
        self.assertIn("Charis SIL", stack)

    def test_poster_ipa_label_stix_before_charis(self):
        config.USE_POSTER_FONT_STACK = True
        families, serif_medium = fs.label_font_family("/o/", "serif")
        self.assertEqual(families[0], "STIX Two Text")
        self.assertIn("Charis SIL", families)
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
