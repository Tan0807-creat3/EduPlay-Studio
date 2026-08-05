import os
import sys
import unittest
from unittest import mock

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QFrame, QMainWindow, QStackedWidget, QWidget


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestUiMotionPolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_left_nav_can_show_tooltip_immediately_at_cursor(self):
        from eduplay.ui.widgets.left_nav_drawer import LeftNavDrawer

        drawer = LeftNavDrawer()
        drawer.show()
        self.app.processEvents()

        with mock.patch("eduplay.ui.widgets.left_nav_drawer.QToolTip.showText") as mocked_show:
            drawer._show_tooltip_now(drawer.btn_home, QPoint(12, 16))

        mocked_show.assert_called_once()
        args = mocked_show.call_args.args
        self.assertEqual(args[1], drawer.btn_home.toolTip())
        self.assertIs(args[2], drawer.btn_home)

    def test_left_nav_tooltip_ignores_tiny_cursor_moves(self):
        from eduplay.ui.widgets.left_nav_drawer import LeftNavDrawer

        drawer = LeftNavDrawer()
        drawer.show()
        self.app.processEvents()

        with mock.patch("eduplay.ui.widgets.left_nav_drawer.QToolTip.showText") as mocked_show:
            drawer._show_tooltip_now(drawer.btn_home, QPoint(12, 16))
            drawer._show_tooltip_now(drawer.btn_home, QPoint(14, 18))
            drawer._show_tooltip_now(drawer.btn_home, QPoint(28, 30))

        self.assertEqual(mocked_show.call_count, 2)

    def test_editor_toast_uses_parallel_position_and_opacity_animation(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        with (
            mock.patch.object(EditorScreen, "setup_ui", lambda self: self.resize(1280, 800)),
            mock.patch.object(EditorScreen, "connect_signals", lambda self: None),
            mock.patch.object(EditorScreen, "refresh_autosave_settings", lambda self: None),
            mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"),
        ):
            screen = EditorScreen(project_manager=mock.Mock(), ai_service=mock.Mock())

        screen.show()
        self.app.processEvents()
        screen.show_toast("Luu thanh cong", kind="success")

        target = screen._toast_widget
        self.assertIsNotNone(target.graphicsEffect())
        group = getattr(screen, "_toast_anim_group", None)
        self.assertIsNotNone(group)
        prop_names = []
        for index in range(group.animationCount()):
            animation = group.animationAt(index)
            if hasattr(animation, "propertyName"):
                prop_names.append(bytes(animation.propertyName()).decode("utf-8"))
        self.assertIn("pos", prop_names)
        self.assertIn("opacity", prop_names)

    def test_show_screen_reapplies_scale_after_switch(self):
        from eduplay.ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.resize(1280, 800)
        window.settings_manager = None
        window.chat_widget = mock.Mock()
        window.chat_widget.isVisible.return_value = False
        window._left_nav_drawer = None
        window._left_nav_hotzone = None
        window._startup_home_fade_done = True
        window.stacked_widget = QStackedWidget(window)
        window.stacked_widget.addWidget(QWidget())
        window.stacked_widget.addWidget(QWidget())
        window.stacked_widget.setCurrentIndex(0)

        applied_scales = []
        window._apply_global_scale = lambda scale: applied_scales.append(scale)

        with mock.patch("eduplay.ui.main_window.QTimer.singleShot", side_effect=lambda _ms, fn: fn()):
            window.show_screen("new_project")

        self.assertEqual(window.stacked_widget.currentIndex(), 1)
        self.assertTrue(applied_scales)
        self.assertAlmostEqual(applied_scales[-1], 1.0, places=2)

    def test_left_nav_drawer_animation_uses_position_and_opacity(self):
        from eduplay.ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)
        window.resize(1280, 800)
        window._left_nav_drawer = QFrame(window)
        window._left_nav_drawer.resize(124, 800)
        window._left_nav_drawer.move(-124, 0)
        window._left_nav_hotzone = QFrame(window)
        window._left_nav_anim = None
        window._left_nav_anim_group = None
        window._left_nav_anim_active = False
        window._update_left_nav_geometry = lambda force=False: None

        window._animate_left_nav(0, hide_after=False)

        group = getattr(window, "_left_nav_anim_group", None)
        self.assertIsNotNone(group)
        prop_names = []
        for index in range(group.animationCount()):
            animation = group.animationAt(index)
            if hasattr(animation, "propertyName"):
                prop_names.append(bytes(animation.propertyName()).decode("utf-8"))
        self.assertIn("pos", prop_names)
        self.assertIn("opacity", prop_names)


if __name__ == "__main__":
    unittest.main()
