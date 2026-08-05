import json
import os
import sys
import unittest
from unittest import mock

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestAcknowledgementsI18n(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_acknowledgements_keys_exist_in_all_languages(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n")
        )
        required_keys = [
            "credits.ack.title",
            "credits.ack.body",
        ]
        for lang in ("en", "vi", "fr", "de", "es"):
            with open(os.path.join(base_dir, f"{lang}.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in required_keys:
                self.assertIn(key, data, f"Missing key '{key}' in {lang}.json")
                self.assertIsInstance(data[key], str)
                self.assertTrue(data[key].strip())

    def test_startup_credits_contains_acknowledgements_labels(self):
        from eduplay.ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)

        overlay = QWidget(window)
        overlay.resize(1200, 800)

        logo = QLabel(overlay)
        logo.setGeometry(420, 120, 240, 240)

        title = QLabel(overlay)
        title.setAlignment(Qt.AlignCenter)
        original = QPixmap(420, 72)
        original.fill(Qt.white)
        title.setPixmap(original)
        title.setGeometry(390, 390, 420, 72)

        window.settings_manager = None
        window._startup_overlay = overlay
        window._startup_logo_label = logo
        window._startup_title_label = title
        window._startup_theme = "light"
        window._startup_text_anim_group = None
        window._startup_char_labels = []

        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_language", return_value="en"):
            window._show_startup_credits_content()

        credits = getattr(window, "_startup_credits_widget", None)
        self.assertIsNotNone(credits)

        ack_title = credits.findChild(QLabel, "startup-ack-title")
        ack_body = credits.findChild(QLabel, "startup-ack-body")
        self.assertIsNotNone(ack_title)
        self.assertIsNotNone(ack_body)


if __name__ == "__main__":
    unittest.main()
