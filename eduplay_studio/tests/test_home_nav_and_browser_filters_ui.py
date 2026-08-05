import os
import sys
import unittest
from unittest import mock

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestHomeNavAndBrowserFiltersUi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_left_nav_drawer_exposes_three_quick_actions_and_resume_context(self):
        from eduplay.ui.widgets.left_nav_drawer import LeftNavDrawer

        drawer = LeftNavDrawer()
        drawer.setFixedSize(126, 548)
        drawer.set_language("vi")
        drawer.show()
        self.app.processEvents()

        self.assertEqual(drawer.quick_section_label.text(), "THAO TÁC\nNHANH")
        self.assertEqual(drawer.btn_recent.text(), "Mở gần\nđây")
        self.assertEqual(drawer.btn_publish.text(), "Xuất bản\nnhanh")
        self.assertEqual(drawer.btn_resume.text(), "Tiếp tục\nchỉnh sửa")
        self.assertTrue(drawer.btn_resume.isVisible())

        drawer.set_quick_context(True)
        self.assertTrue(drawer.btn_resume.isVisible())

    def test_left_nav_drawer_i18n_keys_exist_for_all_languages(self):
        from eduplay.ui.widgets.left_nav_drawer import LeftNavDrawer
        from eduplay.core.i18n import I18n

        drawer = LeftNavDrawer()
        required_keys = [
            "nav.quick_actions",
            "home.quick.recent",
            "home.quick.publish",
            "home.quick.resume",
            "tooltip.leftnav.home",
            "tooltip.leftnav.projects",
            "tooltip.leftnav.preview",
            "tooltip.quick.recent",
            "tooltip.quick.publish",
            "tooltip.quick.resume",
        ]

        for lang in ("en", "vi", "es", "fr", "de"):
            for key in required_keys:
                text = I18n.t(key, lang)
                self.assertNotEqual(text, key, f"Missing '{key}' in {lang}")
                self.assertTrue(text.strip(), f"Empty translation for '{key}' in {lang}")

    def test_left_nav_drawer_set_language_does_not_raise_for_supported_languages(self):
        from eduplay.ui.widgets.left_nav_drawer import LeftNavDrawer

        drawer = LeftNavDrawer()
        for lang in ("en", "vi", "es", "fr", "de"):
            try:
                drawer.set_language(lang)
            except Exception as exc:
                self.fail(f"set_language({lang!r}) raised {exc}")

    def test_browser_screen_uses_only_scope_and_game_filters(self):
        from eduplay.ui.screens.browser_screen import BrowserScreen

        with mock.patch.object(BrowserScreen, "load_projects", lambda self: None), \
             mock.patch.object(BrowserScreen, "filter_projects", lambda self: None):
            screen = BrowserScreen()

        screen.project_manager = None
        screen.all_projects = []
        screen._populate_filter_controls("vi")

        self.assertTrue(hasattr(screen, "recent_combo"))
        self.assertTrue(hasattr(screen, "filter_combo"))
        self.assertFalse(hasattr(screen, "tag_combo"))
        self.assertEqual(screen.recent_combo.count(), 2)
        self.assertEqual(screen.filter_combo.count(), 4)
        self.assertEqual(screen.recent_combo.currentData(), "all")
        self.assertEqual(screen.filter_combo.currentData(), "all")

    def test_home_screen_uses_original_text_icons_for_cards(self):
        from eduplay.ui.screens.home_screen import HomeScreen

        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"):
            screen = HomeScreen()
        screen.show()
        self.app.processEvents()

        self.assertEqual(screen.create_icon_label.text(), "+")
        self.assertEqual(screen.edit_icon_label.text(), "✎")
        self.assertEqual(screen.play_icon_label.text(), "▶")

    def test_home_screen_does_not_define_custom_icon_tuning_helpers(self):
        from eduplay.ui.screens.home_screen import HomeScreen

        screen = HomeScreen()

        self.assertFalse(hasattr(screen, "_home_card_icon_tuning"))
        self.assertFalse(hasattr(screen, "_build_home_card_glyph_pixmap"))

    def test_help_and_settings_use_requested_glyphs(self):
        from eduplay.ui.icon_factory import build_glyph_icon, build_standard_ui_icon, icon_glyph

        self.assertEqual(icon_glyph("help"), "❓")
        self.assertEqual(icon_glyph("settings"), "⚙️")

        expected_help = build_glyph_icon("help", "#334155", 18).pixmap(QSize(18, 18))
        expected_settings = build_glyph_icon("settings", "#334155", 18).pixmap(QSize(18, 18))
        actual_help = build_standard_ui_icon("help", self.app.style(), color_hex="#334155", size=18).pixmap(QSize(18, 18))
        actual_settings = build_standard_ui_icon("settings", self.app.style(), color_hex="#334155", size=18).pixmap(QSize(18, 18))

        self.assertEqual(actual_help.toImage(), expected_help.toImage())
        self.assertEqual(actual_settings.toImage(), expected_settings.toImage())

    def test_browser_and_editor_import_buttons_share_same_regular_import_icon(self):
        from eduplay.ui.icon_factory import build_app_action_icon
        from eduplay.ui.screens.browser_screen import BrowserScreen
        from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel

        with mock.patch.object(BrowserScreen, "load_projects", lambda self: None), \
             mock.patch.object(BrowserScreen, "filter_projects", lambda self: None):
            browser = BrowserScreen()
        editor_left = EditorLeftPanel()
        browser.show()
        editor_left.show()
        self.app.processEvents()

        browser_icon = browser.import_btn.icon().pixmap(QSize(16, 16))
        editor_icon = editor_left.import_btn.icon().pixmap(QSize(16, 16))
        expected_icon = build_app_action_icon("import", self.app.style(), size=16).pixmap(QSize(16, 16))

        self.assertFalse(browser_icon.isNull())
        self.assertFalse(editor_icon.isNull())
        self.assertFalse(expected_icon.isNull())
        self.assertEqual(browser_icon.toImage(), expected_icon.toImage())
        self.assertEqual(editor_icon.toImage(), expected_icon.toImage())

    def test_browser_title_keeps_high_contrast_in_light_theme_after_scaling(self):
        from eduplay.ui.screens.browser_screen import BrowserScreen

        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"), \
             mock.patch.object(BrowserScreen, "load_projects", lambda self: None), \
             mock.patch.object(BrowserScreen, "filter_projects", lambda self: None):
            screen = BrowserScreen()

        screen.set_scale(1.15)
        title_style = screen.title_label.styleSheet()
        self.assertIn("#0F1728", title_style)

    def test_browser_screen_locks_scale_after_first_apply(self):
        from eduplay.ui.screens.browser_screen import BrowserScreen

        with mock.patch.object(BrowserScreen, "load_projects", lambda self: None), \
             mock.patch.object(BrowserScreen, "filter_projects", lambda self: None):
            screen = BrowserScreen()

        screen.set_scale(1.25)
        first_height = screen.back_btn.height()
        screen.set_scale(0.8)
        self.assertEqual(screen.back_btn.height(), first_height)

if __name__ == "__main__":
    unittest.main()
