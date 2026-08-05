import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestSettingsSecretStorage(unittest.TestCase):
    def test_api_key_is_not_stored_in_plaintext(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()
                secret = "gsk_test_secret_storage_1234567890"
                manager.set_api_key("groq", secret)

                raw = (settings_dir / "settings.json").read_text(encoding="utf-8")
                self.assertNotIn(secret, raw)

                reloaded = SettingsManager()
                self.assertEqual(reloaded.get_api_key("groq"), secret)

    def test_proxy_token_is_not_stored_in_plaintext(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()
                token = "proxy_token_secret_ABC123_xyz"
                manager.set("ai_settings.proxy_token", token)

                raw = (settings_dir / "settings.json").read_text(encoding="utf-8")
                self.assertNotIn(token, raw)

                reloaded = SettingsManager()
                self.assertEqual(reloaded.get("ai_settings.proxy_token", ""), token)

    def test_plaintext_secrets_are_migrated_on_load(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_file = settings_dir / "settings.json"
            payload = {
                "app_language": "vi",
                "ai_settings": {
                    "proxy_token": "legacy_proxy_secret_123",
                },
                "api_keys": {
                    "groq": "gsk_legacy_secret_1234567890",
                },
            }
            settings_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()

                self.assertEqual(manager.get_api_key("groq"), "gsk_legacy_secret_1234567890")
                self.assertEqual(manager.get("ai_settings.proxy_token", ""), "legacy_proxy_secret_123")

                raw = settings_file.read_text(encoding="utf-8")
                self.assertNotIn("gsk_legacy_secret_1234567890", raw)
                self.assertNotIn("legacy_proxy_secret_123", raw)

    def test_device_key_is_not_stored_in_plaintext(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()
                device_key = "dkey_secret_machine_binding_123456"
                manager.set("device_auth.device_key", device_key)

                raw = (settings_dir / "settings.json").read_text(encoding="utf-8")
                self.assertNotIn(device_key, raw)

                reloaded = SettingsManager()
                self.assertEqual(reloaded.get("device_auth.device_key", ""), device_key)


if __name__ == "__main__":
    unittest.main()
