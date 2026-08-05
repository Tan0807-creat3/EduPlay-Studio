import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON body")
        return self._json_data


class TestAiGatewayDeviceAuth(unittest.TestCase):
    def test_check_ready_fast_uses_server_config_and_persists_device_key(self):
        from eduplay.core.ai_service import AIService
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()
                manager.set("ai_settings.server_base_url", "https://site--eduplay-ai--sx2zlgv27rbh.code.run/openai/v1")

                service = AIService(settings_manager=manager)

                self.assertTrue(service.check_ready_fast())
                device_key = manager.get("device_auth.device_key", "")
                self.assertTrue(str(device_key).startswith("dkey_"))
                self.assertGreater(len(str(device_key)), 20)

                raw = (settings_dir / "settings.json").read_text(encoding="utf-8")
                self.assertNotIn(device_key, raw)

    def test_manual_proxy_tokens_are_ignored_without_cached_server_token(self):
        from eduplay.core.ai_service import AIService
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()
                manager.set("ai_settings.server_base_url", "https://site--eduplay-ai--sx2zlgv27rbh.code.run/openai/v1")
                manager.set("ai_settings.proxy_token", "legacy_manual_proxy_token")

                with patch.dict(
                    os.environ,
                    {
                        "EDUPLAY_AI_PROXY_TOKEN": "env_proxy_token_should_be_ignored",
                        "EDUPLAY_PROXY_TOKEN": "env_proxy_token_should_be_ignored_2",
                    },
                    clear=False,
                ):
                    service = AIService(settings_manager=manager)
                    self.assertEqual(service._get_proxy_token(), "")

    def test_setup_ai_does_not_block_on_server_wakeup(self):
        from eduplay.core.ai_service import AIService
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()
                manager.set("ai_settings.server_base_url", "https://site--eduplay-ai--sx2zlgv27rbh.code.run/openai/v1")
                service = AIService(settings_manager=manager)

                with patch("eduplay.core.ai_service.requests.post") as mocked_post:
                    self.assertTrue(service.setup_ai())
                    mocked_post.assert_not_called()

    def test_chat_messages_retries_while_server_is_waking_up(self):
        from eduplay.core.ai_service import AIService
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()
                manager.set("ai_settings.server_base_url", "https://site--eduplay-ai--sx2zlgv27rbh.code.run/openai/v1")
                service = AIService(settings_manager=manager)
                self.assertTrue(service.setup_ai())

                events = []
                attempts = {"chat": 0, "register": 0}

                def fake_post(url, headers=None, json=None, timeout=None):
                    if url.endswith("/device/register"):
                        attempts["register"] += 1
                        self.assertTrue(str((json or {}).get("device_id") or "").startswith("dev_"))
                        self.assertTrue(str((json or {}).get("device_key") or "").startswith("dkey_"))
                        self.assertTrue(str((json or {}).get("machine_fingerprint") or "").startswith("mfp_"))
                        return _FakeResponse(
                            200,
                            json_data={
                                "access_token": "nf_access_token_123",
                                "device_key_accepted": True,
                                "binding_status": "registered",
                            },
                            text='{"access_token":"nf_access_token_123","device_key_accepted":true}',
                        )
                    if url.endswith("/chat/completions"):
                        attempts["chat"] += 1
                        self.assertEqual((headers or {}).get("Authorization"), "Bearer nf_access_token_123")
                        self.assertTrue(str((headers or {}).get("X-Device-Id") or "").startswith("dev_"))
                        self.assertTrue(str((headers or {}).get("X-Device-Key") or "").startswith("dkey_"))
                        self.assertTrue(str((headers or {}).get("X-Machine-Fingerprint") or "").startswith("mfp_"))
                        if attempts["chat"] == 1:
                            return _FakeResponse(503, json_data={"error": {"message": "server_starting"}}, text="server_starting")
                        return _FakeResponse(
                            200,
                            json_data={"choices": [{"message": {"content": "Xin chao tu Key AI"}}]},
                            text='{"choices":[{"message":{"content":"Xin chao tu Key AI"}}]}',
                        )
                    raise AssertionError(f"Unexpected URL: {url}")

                with patch("eduplay.core.ai_service.requests.post", side_effect=fake_post):
                    with patch("eduplay.core.ai_service.time.sleep", return_value=None):
                        result = service.chat_messages(
                            [{"role": "user", "content": "Xin chao"}],
                            progress_cb=events.append,
                        )

                self.assertEqual(result, "Xin chao tu Key AI")
                self.assertEqual(attempts["register"], 1)
                self.assertEqual(attempts["chat"], 2)
                joined = " | ".join(str(item) for item in events)
                self.assertIn("Đang gọi AI", joined)
                self.assertIn("khởi động", joined.lower())

    def test_legacy_server_url_is_normalized_to_current_server(self):
        from eduplay.core.ai_service import AIService
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp)
            with patch.object(SettingsManager, "_get_settings_directory", return_value=settings_dir):
                manager = SettingsManager()
                manager.set("ai_settings.server_base_url", "https://eduplay-ai.northflank.app/openai/v1")

                service = AIService(settings_manager=manager)

                self.assertEqual(
                    service.base_url,
                    "https://site--eduplay-ai--sx2zlgv27rbh.code.run/openai/v1",
                )


if __name__ == "__main__":
    unittest.main()
