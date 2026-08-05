import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestFirstTimeFlow(unittest.TestCase):
    def test_existing_settings_file_skips_first_time_flow(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            (settings_dir / "settings.json").write_text(
                '{\n  "first_run": true,\n  "app_language": "vi"\n}',
                encoding="utf-8",
            )

            sm = SettingsManager(settings_dir=settings_dir)

            self.assertTrue(sm.settings_file_existed)
            self.assertFalse(sm.should_run_first_time_flow())

    def test_missing_settings_file_runs_first_time_flow(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"

            sm = SettingsManager(settings_dir=settings_dir)

            self.assertFalse(sm.settings_file_existed)
            self.assertTrue(sm.should_run_first_time_flow())

    def test_second_instance_sees_file_as_existing(self):
        """A second SettingsManager built after the first created settings.json
        reports the file as pre-existing. This is why app.exec() must share ONE
        SettingsManager with AIService instead of letting AIService build its own
        internal instance first (which previously made the first-time flow never
        appear, even when settings.json was missing before launch).
        """
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)

            sm1 = SettingsManager(settings_dir=settings_dir)
            self.assertFalse(sm1.settings_file_existed)
            self.assertTrue(sm1.should_run_first_time_flow())

            # A later instance (e.g. an internal AIService SettingsManager) sees
            # the file as already existing and would skip the first-time flow.
            sm2 = SettingsManager(settings_dir=settings_dir)
            self.assertTrue(sm2.settings_file_existed)
            self.assertFalse(sm2.should_run_first_time_flow())

            # The first/shared instance remains authoritative for first-time.
            self.assertTrue(sm1.should_run_first_time_flow())

    def test_aiservice_reuses_passed_settings_manager_and_preserves_first_time(self):
        """AIService must reuse the SettingsManager passed to its constructor
        instead of creating its own. Otherwise the internal instance writes
        settings.json before the main flow runs, masking the first-time state.
        """
        from eduplay.core.settings_manager import SettingsManager
        from eduplay.core.ai_service import AIService

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / "EduPlay" / "Settings"
            settings_dir.mkdir(parents=True, exist_ok=True)

            sm = SettingsManager(settings_dir=settings_dir)
            self.assertTrue(sm.should_run_first_time_flow())

            ai = AIService(settings_manager=sm)
            # Must not have spun up a separate SettingsManager.
            self.assertIs(ai.settings_manager, sm)
            # First-time detection must still hold (no second instance created).
            self.assertTrue(sm.should_run_first_time_flow())


if __name__ == "__main__":
    unittest.main()
