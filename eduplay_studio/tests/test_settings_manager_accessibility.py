import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSettingsManagerAccessibility(unittest.TestCase):
    def test_default_accessibility_settings_are_present(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            sm = SettingsManager(settings_dir=Path(tmp))
            cfg = sm.get_accessibility_settings()

            self.assertEqual(cfg.get("ui_scale"), 100)
            self.assertFalse(cfg.get("high_contrast"))
            self.assertFalse(cfg.get("reduce_motion"))

    def test_get_accessibility_settings_merges_missing_keys(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            sm = SettingsManager(settings_dir=Path(tmp))
            sm.set("accessibility", {"ui_scale": 115})

            cfg = sm.get_accessibility_settings()
            self.assertEqual(cfg.get("ui_scale"), 115)
            self.assertFalse(cfg.get("high_contrast"))
            self.assertFalse(cfg.get("reduce_motion"))


if __name__ == "__main__":
    unittest.main()
