import os
import sys
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestFontSettingsApply(unittest.TestCase):
    def test_theme_qss_does_not_lock_global_font_family(self):
        base = Path(__file__).parent.parent / "eduplay" / "resources" / "styles"
        light = (base / "light_theme.qss").read_text(encoding="utf-8")
        dark = (base / "dark_theme.qss").read_text(encoding="utf-8")

        self.assertEqual(light.count("font-family:"), 1)
        self.assertEqual(dark.count("font-family:"), 1)

        self.assertIn("QFrame#left-nav-drawer", light)
        self.assertIn("QFrame#left-nav-drawer", dark)

        self.assertGreater(light.find("font-family:"), light.find("QFrame#left-nav-drawer"))
        self.assertGreater(dark.find("font-family:"), dark.find("QFrame#left-nav-drawer"))

    def test_inline_styles_do_not_force_specific_ui_font_family(self):
        base = Path(__file__).parent.parent / "eduplay" / "ui"
        main_window = (base / "main_window.py").read_text(encoding="utf-8")
        chat_widget = (base / "widgets" / "chat_widget.py").read_text(encoding="utf-8")

        self.assertNotIn("font-family: 'Segoe UI', Arial, sans-serif;", main_window)
        self.assertNotIn("font-family: 'Inter', 'Segoe UI', Arial, sans-serif;", chat_widget)


if __name__ == "__main__":
    unittest.main()

