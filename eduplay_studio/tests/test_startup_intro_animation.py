import os
import sys
import unittest
from unittest import mock

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QShowEvent
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestStartupIntroAnimation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_home_card_entrance_animates_position_and_opacity(self):
        from eduplay.ui.screens.home_screen import HomeScreen

        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"):
            screen = HomeScreen()

        screen.show()
        self.app.processEvents()
        screen.animate_cards_entrance()

        groups = getattr(screen, "_entrance_anim_refs", [])
        self.assertEqual(len(groups), 3)

        for group in groups:
            prop_names = []
            for index in range(group.animationCount()):
                animation = group.animationAt(index)
                if hasattr(animation, "propertyName"):
                    prop_names.append(bytes(animation.propertyName()).decode("utf-8"))
            self.assertIn("opacity", prop_names)
            self.assertIn("pos", prop_names)

    def test_startup_credits_sequence_keeps_title_pixmap_for_smooth_scaling(self):
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
        window._startup_logo_anim = None
        window._startup_text_anim_group = None
        window._startup_char_labels = []

        window._start_startup_credits_sequence(force_credits=True)

        self.assertTrue(title.hasScaledContents())
        self.assertEqual(title.pixmap().size(), original.size())

    def test_show_event_requests_startup_intro_once(self):
        from eduplay.ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window._startup_animation_requested = False
        window._hide_loading = mock.Mock()
        window.start_startup_animation = mock.Mock()

        event = QShowEvent()
        window.showEvent(event)
        window.showEvent(event)

        window.start_startup_animation.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
