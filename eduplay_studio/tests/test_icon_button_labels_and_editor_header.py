import os
import sys
import unittest
from unittest import mock

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QVBoxLayout


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestIconButtonLabelsAndEditorHeader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_strip_icon_text_removes_leading_symbols(self):
        from eduplay.ui.icon_factory import strip_icon_text

        self.assertEqual(strip_icon_text("← Back"), "Back")
        self.assertEqual(strip_icon_text("📁 Open Folder"), "Open Folder")
        self.assertEqual(strip_icon_text("💾 Save Project"), "Save Project")
        self.assertEqual(strip_icon_text("Preview"), "Preview")

    def test_editor_header_updates_all_action_labels_in_selected_language(self):
        from eduplay.ui.icon_factory import strip_icon_text
        from eduplay.ui.screens.editor_screen import EditorScreen
        from eduplay.core.i18n import I18n

        expected_labels = {
            "back_btn": "editor.back",
            "save_btn": "editor.save",
            "preview_btn": "editor.preview_title",
            "export_web_btn": "editor.export_web",
            "export_html_btn": "editor.export_html_internal",
        }

        for lang in ("en", "vi", "es", "fr", "de"):
            def _light_setup_ui(self):
                layout = QVBoxLayout(self)
                layout.setContentsMargins(0, 0, 0, 0)
                self.header = self.create_header()
                layout.addWidget(self.header)

            with (
                mock.patch.object(EditorScreen, "setup_ui", _light_setup_ui),
                mock.patch.object(EditorScreen, "connect_signals", lambda self: None),
                mock.patch.object(EditorScreen, "refresh_autosave_settings", lambda self: None),
                mock.patch("eduplay.ui.screens.editor_screen.SettingsManager.get_language", return_value=lang),
                mock.patch("eduplay.ui.screens.editor_screen.SettingsManager.get_theme", return_value="light"),
            ):
                screen = EditorScreen(project_manager=mock.Mock(), ai_service=mock.Mock())

            for attr, key in expected_labels.items():
                btn = getattr(screen, attr)
                self.assertEqual(btn.text(), strip_icon_text(I18n.t(key, lang)), f"Wrong {attr} text for {lang}")

    def test_editor_header_action_icons_exist_for_all_buttons(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        def _light_setup_ui(self):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self.header = self.create_header()
            layout.addWidget(self.header)

        with (
            mock.patch.object(EditorScreen, "setup_ui", _light_setup_ui),
            mock.patch.object(EditorScreen, "connect_signals", lambda self: None),
            mock.patch.object(EditorScreen, "refresh_autosave_settings", lambda self: None),
            mock.patch("eduplay.ui.screens.editor_screen.SettingsManager.get_language", return_value="vi"),
            mock.patch("eduplay.ui.screens.editor_screen.SettingsManager.get_theme", return_value="light"),
        ):
            screen = EditorScreen(project_manager=mock.Mock(), ai_service=mock.Mock())

        for btn in (screen.save_btn, screen.preview_btn, screen.export_web_btn, screen.export_html_btn):
            self.assertFalse(btn.icon().isNull())

    def test_editor_left_panel_action_buttons_use_regular_icons(self):
        from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel

        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"):
            panel = EditorLeftPanel()

        self.assertIsNotNone(getattr(panel, "add_btn", None))
        self.assertFalse(panel.add_btn.icon().isNull())
        self.assertEqual(panel.add_btn.text(), "Thêm câu hỏi")
        self.assertIsNotNone(getattr(panel, "import_btn", None))
        self.assertFalse(panel.import_btn.icon().isNull())

    def test_apply_selected_dialog_gets_theme_stylesheet_for_dark_and_light(self):
        from PySide6.QtWidgets import QDialog
        from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel

        def _capture_dialog_style(theme_name):
            captured = {}

            def _fake_exec(dialog_self):
                captured["style"] = dialog_self.styleSheet()
                return QDialog.Accepted

            with (
                mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value=theme_name),
                mock.patch("PySide6.QtWidgets.QDialog.exec", _fake_exec),
            ):
                panel = EditorLeftPanel()
                panel.apply_settings_with_selection()
            return captured.get("style", "")

        dark_style = _capture_dialog_style("dark")
        light_style = _capture_dialog_style("light")

        self.assertIn("QDialog", dark_style)
        self.assertIn("#111827", dark_style)
        self.assertIn("QDialog", light_style)
        self.assertIn("#FFFFFF", light_style)

    def test_home_card_icons_use_original_glyph_text(self):
        from eduplay.ui.screens.home_screen import HomeScreen

        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"):
            screen = HomeScreen()

        self.assertEqual(screen.create_icon_label.text(), "+")
        self.assertEqual(screen.edit_icon_label.text(), "✎")
        self.assertEqual(screen.play_icon_label.text(), "▶")

    def test_home_card_icons_do_not_use_custom_tuning_helpers(self):
        from eduplay.ui.screens.home_screen import HomeScreen

        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"):
            screen = HomeScreen()

        self.assertFalse(hasattr(screen, "_home_card_icon_tuning"))
        self.assertFalse(hasattr(screen, "_build_home_card_glyph_pixmap"))

    def test_settings_icon_uses_gear_glyph(self):
        from eduplay.ui.icon_factory import icon_glyph

        self.assertEqual(icon_glyph("settings"), "⚙")

    def test_help_standard_icon_uses_question_mark_glyph(self):
        from eduplay.ui.icon_factory import build_glyph_icon, build_standard_ui_icon

        class _FakeStyle:
            def standardIcon(self, _pixmap_kind):
                return QIcon()

        with mock.patch("PySide6.QtGui.QIcon.fromTheme", return_value=QIcon()):
            icon = build_standard_ui_icon("help", _FakeStyle())

        expected = build_glyph_icon("help", "#374151", 18)
        self.assertEqual(self._icon_bytes(icon), self._icon_bytes(expected))

    def _icon_bytes(self, icon, size=18):
        image = icon.pixmap(size, size).toImage()
        ptr = image.bits()
        return bytes(ptr[: image.sizeInBytes()])

    def _label_pixmap_bytes(self, label):
        pixmap = label.pixmap()
        return self._pixmap_bytes(pixmap)

    def _pixmap_bytes(self, pixmap):
        image = pixmap.toImage()
        ptr = image.bits()
        return bytes(ptr[: image.sizeInBytes()])

    def test_settings_standard_icon_falls_back_to_internal_icon_when_system_icon_missing(self):
        from eduplay.ui.icon_factory import build_line_icon, build_standard_ui_icon

        class _NullStyle:
            def standardIcon(self, _pixmap_kind):
                return QIcon()

        with (
            mock.patch("PySide6.QtGui.QIcon.fromTheme", return_value=QIcon()),
            mock.patch("eduplay.ui.icon_factory.build_stock_icon_pixmap", return_value=QPixmap()),
        ):
            icon = build_standard_ui_icon("settings", _NullStyle())

        self.assertFalse(icon.isNull())

        expected = build_line_icon("settings", "#374151", 18, stroke_width=1.9)
        self.assertEqual(self._icon_bytes(icon), self._icon_bytes(expected))

    def test_settings_standard_icon_ignores_non_gear_system_theme_icon(self):
        from eduplay.ui.icon_factory import build_line_icon, build_standard_ui_icon

        fake_icon = build_line_icon("play", "#374151", 18, stroke_width=1.9)

        class _FakeStyle:
            def standardIcon(self, _pixmap_kind):
                return fake_icon

        with mock.patch("PySide6.QtGui.QIcon.fromTheme", return_value=fake_icon):
            icon = build_standard_ui_icon("settings", _FakeStyle())

        expected = build_line_icon("settings", "#374151", 18, stroke_width=1.9)
        self.assertEqual(self._icon_bytes(icon), self._icon_bytes(expected))

    def test_browser_import_button_uses_same_regular_import_icon_as_editor_panel(self):
        from eduplay.ui.screens.browser_screen import BrowserScreen
        from eduplay.ui.icon_factory import build_app_action_icon
        from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel

        with (
            mock.patch.object(BrowserScreen, "load_projects", lambda self: None),
            mock.patch.object(BrowserScreen, "filter_projects", lambda self: None),
            mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"),
        ):
            browser = BrowserScreen()
            panel = EditorLeftPanel()

        expected_icon = build_app_action_icon("import", self.app.style(), size=16)

        self.assertEqual(
            self._icon_bytes(browser.import_btn.icon(), size=16),
            self._icon_bytes(expected_icon, size=16),
        )
        self.assertEqual(
            self._icon_bytes(panel.import_btn.icon(), size=16),
            self._icon_bytes(expected_icon, size=16),
        )


if __name__ == "__main__":
    unittest.main()
