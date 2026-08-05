import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSettingsManagerRc2Header(unittest.TestCase):
    def test_prefers_resolved_windows_documents_directory(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            redirected_docs = Path(tmp) / "OneDrive" / "Documents"
            expected_dir = redirected_docs / "EduPlay" / "Settings"
            with mock.patch("eduplay.core.settings_manager._resolve_documents_directory", return_value=redirected_docs):
                sm = SettingsManager()
            self.assertEqual(sm.settings_dir, expected_dir)
            self.assertTrue((expected_dir / "settings.json").exists())

    def test_detects_old_user_without_rc2_header_and_can_add_header(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            f = settings_dir / "settings.json"
            f.write_text(json.dumps({"app_language": "vi"}, ensure_ascii=False), encoding="utf-8")

            sm = SettingsManager(settings_dir=settings_dir)
            self.assertTrue(sm.needs_rc2_whats_new())

            sm.ensure_rc2_header()
            raw = f.read_text(encoding="utf-8")
            self.assertTrue("v1.0.0 RC2" in raw.splitlines()[0])

            sm2 = SettingsManager(settings_dir=settings_dir)
            self.assertFalse(sm2.needs_rc2_whats_new())
            self.assertEqual(sm2.get_language(), "vi")

    def test_parses_json_when_header_is_present(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            f = settings_dir / "settings.json"
            f.write_text("// v1.0.0 RC2\n" + json.dumps({"theme": "dark"}, ensure_ascii=False), encoding="utf-8")

            sm = SettingsManager(settings_dir=settings_dir)
            self.assertEqual(sm.get_theme(), "dark")
            self.assertFalse(sm.needs_rc2_whats_new())


if __name__ == "__main__":
    unittest.main()

