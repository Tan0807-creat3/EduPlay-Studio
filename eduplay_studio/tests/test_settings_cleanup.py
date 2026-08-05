import os
import sys
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSettingsCleanup(unittest.TestCase):
    def test_game_defaults_does_not_include_tts_enabled(self):
        from eduplay.core.settings_manager import SettingsManager

        sm = SettingsManager()
        defaults = sm._get_default_settings()
        game_defaults = defaults.get("game_defaults") or {}
        self.assertNotIn("tts_enabled", game_defaults)
        self.assertNotIn("tts_voice_lang", game_defaults)

    def test_theme_qss_contains_spinbox_arrow_selectors(self):
        base = Path(__file__).parent.parent / "eduplay" / "resources" / "styles"
        light = (base / "light_theme.qss").read_text(encoding="utf-8")
        dark = (base / "dark_theme.qss").read_text(encoding="utf-8")
        self.assertNotIn("QSpinBox::up-arrow", light)
        self.assertNotIn("QSpinBox::down-arrow", light)
        self.assertNotIn("QSpinBox::up-arrow", dark)
        self.assertNotIn("QSpinBox::down-arrow", dark)
        self.assertNotIn("QSpinBox::up-button", light)
        self.assertNotIn("QSpinBox::down-button", light)
        self.assertNotIn("QSpinBox::up-button", dark)
        self.assertNotIn("QSpinBox::down-button", dark)


if __name__ == "__main__":
    unittest.main()
