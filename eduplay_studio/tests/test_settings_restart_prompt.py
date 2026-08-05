import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PySide6.QtWidgets import QApplication


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _FakeSettingsManager:
    def __init__(self, language="vi", theme="light"):
        self._language = language
        self._theme = theme

    def get_language(self):
        return self._language

    def get_theme(self):
        return self._theme


class _FakeDialogSettingsManager(_FakeSettingsManager):
    def __init__(self, language="vi", theme="light"):
        super().__init__(language=language, theme=theme)
        self.reset_called = False
        self._values = {
            "auto_save": True,
            "auto_save_interval": 300,
            "notifications.system_enabled": True,
            "notifications.only_when_background": False,
            "ppt_addin": {},
        }
        self._accessibility = {
            "ui_scale": 100,
            "high_contrast": False,
            "reduce_motion": False,
        }
        self._editor = {
            "font_family": "Arial",
            "font_size": 12,
            "show_line_numbers": True,
            "auto_complete": True,
            "spell_check": True,
        }
        self._game_defaults = {
            "quiz_time_per_question": 30,
            "show_explanations": True,
            "randomize_questions": True,
            "points_per_question": 10,
            "auto_points_enabled": False,
            "time_limit_enabled": True,
        }
        self._ai_settings = {
            "server_base_url": "",
            "groq_model": "",
            "task_model": "",
        }

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value

    def get_accessibility_settings(self):
        return dict(self._accessibility)

    def set_accessibility_settings(self, settings):
        self._accessibility.update(settings or {})

    def get_editor_settings(self):
        return dict(self._editor)

    def set_editor_settings(self, settings):
        self._editor.update(settings or {})

    def get_game_defaults(self):
        return dict(self._game_defaults)

    def set_game_defaults(self, settings):
        self._game_defaults.update(settings or {})

    def get_ai_settings(self):
        return dict(self._ai_settings)

    def set_ai_settings(self, settings):
        self._ai_settings.update(settings or {})

    def set_language(self, language):
        self._language = language

    def set_theme(self, theme):
        self._theme = theme

    def reset_to_defaults(self):
        self.reset_called = True


class _FakeMessageBox:
    Warning = object()
    AcceptRole = object()
    RejectRole = object()

    clicked_button = None
    next_clicked_label = None

    def __init__(self, parent=None):
        self.parent = parent
        self.window_title = ""
        self.text = ""
        self.icon = None
        self.buttons = []
        self.default_button = None
        self.style_sheet = ""

    def setStyleSheet(self, style_sheet):
        self.style_sheet = style_sheet

    def setIcon(self, icon):
        self.icon = icon

    def setWindowTitle(self, title):
        self.window_title = title

    def setText(self, text):
        self.text = text

    def addButton(self, label, role):
        button = SimpleNamespace(label=label, role=role)
        self.buttons.append(button)
        return button

    def setDefaultButton(self, button):
        self.default_button = button

    def exec(self):
        for button in self.buttons:
            if button.label == self.next_clicked_label:
                type(self).clicked_button = button
                return
        type(self).clicked_button = self.buttons[-1] if self.buttons else None

    def clickedButton(self):
        return type(self).clicked_button


class TestSettingsRestartPrompt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_restart_prompt_i18n_keys_exist_for_all_supported_languages(self):
        base = Path(__file__).parent.parent / "eduplay" / "resources" / "i18n"
        languages = ("en", "vi", "de", "es", "fr")
        keys = (
            "settings.restart_required_title",
            "settings.restart_required_message",
            "settings.restart_now",
            "settings.restart_later",
        )

        for language in languages:
            data = json.loads((base / f"{language}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertIn(key, data, f"Missing `{key}` in {language}.json")

    def test_restart_prompt_calls_restart_when_user_confirms(self):
        from eduplay.ui.main_window import MainWindow

        fake_window = SimpleNamespace(
            settings_manager=_FakeSettingsManager(language="vi", theme="light"),
            _restart_application=mock.Mock(),
        )

        _FakeMessageBox.next_clicked_label = "Khởi động lại ngay"

        with mock.patch("eduplay.ui.main_window.QMessageBox", _FakeMessageBox):
            result = MainWindow._show_settings_restart_prompt(fake_window)

        self.assertTrue(result)
        fake_window._restart_application.assert_called_once()

    def test_restart_prompt_does_not_restart_when_user_defers(self):
        from eduplay.ui.main_window import MainWindow

        fake_window = SimpleNamespace(
            settings_manager=_FakeSettingsManager(language="en", theme="dark"),
            _restart_application=mock.Mock(),
        )

        _FakeMessageBox.next_clicked_label = "Later"

        with mock.patch("eduplay.ui.main_window.QMessageBox", _FakeMessageBox):
            result = MainWindow._show_settings_restart_prompt(fake_window)

        self.assertFalse(result)
        fake_window._restart_application.assert_not_called()

    def test_reset_settings_emits_change_signal_for_restart_prompt_flow(self):
        from PySide6.QtWidgets import QMessageBox
        from eduplay.ui.widgets.settings_dialog import SettingsDialog

        manager = _FakeDialogSettingsManager(language="vi", theme="light")
        dialog = SettingsDialog(manager)
        signal_hits = []
        dialog.settings_changed.connect(lambda: signal_hits.append("changed"))

        with mock.patch("eduplay.ui.widgets.settings_dialog.QMessageBox.question", return_value=QMessageBox.Yes), \
             mock.patch("eduplay.ui.widgets.settings_dialog.QMessageBox.information"):
            dialog.reset_settings()

        self.assertTrue(manager.reset_called)
        self.assertEqual(signal_hits, ["changed"])

    def test_settings_dialog_ai_and_addin_texts_follow_current_locale(self):
        from eduplay.ui.widgets.settings_dialog import SettingsDialog

        manager = _FakeDialogSettingsManager(language="vi", theme="light")
        dialog = SettingsDialog(manager)

        self.assertEqual(dialog.test_groq_btn.text(), "Kiểm tra máy chủ AI")
        self.assertEqual(dialog._addin_btn_support.text(), "Mở hướng dẫn")

    def test_settings_dialog_i18n_keys_exist_for_all_supported_languages(self):
        base = Path(__file__).parent.parent / "eduplay" / "resources" / "i18n"
        languages = ("en", "vi", "de", "es", "fr")
        keys = (
            "settings.ai_server_group",
            "settings.ai_server_desc",
            "settings.ai_base_url",
            "settings.ai_task_model",
            "settings.ai_test_server",
            "settings.addin.open_support_btn",
            "settings.addin.status_installed",
            "settings.addin.status_installed_version",
            "settings.addin.status_not_installed",
            "settings.addin.status_installing",
            "settings.addin.status_install_failed",
            "settings.ai_test_result_title",
            "settings.ai_test_failed_title",
            "settings.ai_network_unavailable",
            "settings.ai_missing_base_url",
            "settings.ai_server_reachable",
            "settings.ai_server_waking",
            "settings.ai_server_status_error",
            "settings.ai_server_connect_error",
        )

        for language in languages:
            data = json.loads((base / f"{language}.json").read_text(encoding="utf-8"))
            for key in keys:
                self.assertIn(key, data, f"Missing `{key}` in {language}.json")


if __name__ == "__main__":
    unittest.main()
