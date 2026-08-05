import os
import sys
import types
import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication, QMessageBox


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestEditorQuestionActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def _build_project(self):
        return {
            "id": "project-1",
            "name": "Demo",
            "questions": [
                {"id": "q1", "question": "Cau 1"},
                {"id": "q2", "question": "Cau 2"},
            ],
            "game_config": {},
        }

    def test_left_panel_no_longer_renders_selected_question_action_buttons(self):
        from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel

        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"):
            panel = EditorLeftPanel()

        panel.set_project(self._build_project())

        self.assertFalse(hasattr(panel, "delete_selected_btn"))
        self.assertFalse(hasattr(panel, "preview_selected_btn"))

    def test_left_panel_delete_selected_question_emits_payload_for_current_item(self):
        from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel

        captured = []
        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"):
            panel = EditorLeftPanel()
        panel.delete_question_requested.connect(captured.append)
        panel.set_project(self._build_project())
        panel.questions_list.setCurrentRow(1)

        panel.request_delete_selected_question()

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["question_id"], "q2")
        self.assertEqual(captured[0]["index"], 1)

    def test_left_panel_preview_selected_question_emits_payload_for_current_item(self):
        from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel

        captured = []
        with mock.patch("eduplay.core.settings_manager.SettingsManager.get_theme", return_value="light"):
            panel = EditorLeftPanel()
        panel.preview_question_requested.connect(captured.append)
        panel.set_project(self._build_project())
        panel.questions_list.setCurrentRow(0)

        panel.request_preview_selected_question()

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["question_id"], "q1")
        self.assertEqual(captured[0]["index"], 0)

    def test_editor_screen_delete_selected_question_requires_confirmation(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        payload = {"question": {"id": "q2", "question": "Cau 2"}, "question_id": "q2", "index": 1}
        dummy = types.SimpleNamespace(
            current_project=self._build_project(),
            on_question_updated=mock.Mock(),
        )

        with mock.patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.No):
            EditorScreen.on_delete_selected_question_requested(dummy, payload)

        dummy.on_question_updated.assert_not_called()

    def test_editor_screen_delete_selected_question_calls_delete_after_confirmation(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        payload = {"question": {"id": "q2", "question": "Cau 2"}, "question_id": "q2", "index": 1}
        dummy = types.SimpleNamespace(
            current_project=self._build_project(),
            on_question_updated=mock.Mock(),
        )

        with mock.patch("PySide6.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes):
            EditorScreen.on_delete_selected_question_requested(dummy, payload)

        dummy.on_question_updated.assert_called_once_with(
            {
                "action": "delete",
                "question": payload["question"],
                "question_id": "q2",
                "index": 1,
            }
        )

    def test_editor_screen_preview_selected_question_opens_quick_preview_for_selected_index(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        question = {"id": "q2", "question": "Cau 2"}
        dummy = types.SimpleNamespace(
            current_project=self._build_project(),
            current_question_index=-1,
            center_panel=types.SimpleNamespace(set_question=mock.Mock()),
            open_preview_window=mock.Mock(),
        )

        EditorScreen.on_preview_selected_question_requested(
            dummy,
            {"question": question, "question_id": "q2", "index": 1},
        )

        self.assertEqual(dummy.current_question_index, 1)
        dummy.center_panel.set_question.assert_called_once_with(question, 1)
        dummy.open_preview_window.assert_called_once_with(preview_mode="quick")

    def test_inject_quick_preview_autostart_adds_bootstrap_script(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        html = "<html><body><div id='app'></div></body></html>"

        updated = inject_quick_preview_autostart(html)

        self.assertIn('window["__EDUPLAY_QUICK_PREVIEW_AUTO_START"] = true;', updated)
        self.assertIn("introComplete", updated)
        self.assertIn("onStartClick", updated)
        self.assertIn("start-btn", updated)
        self.assertIn("</body>", updated)

    def test_inject_quick_preview_autostart_includes_fishing_overlay_and_first_question_hooks(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        html = "<html><body><div id='start-overlay'></div></body></html>"

        updated = inject_quick_preview_autostart(html)

        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_HIDE_OVERLAY", updated)
        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_OPEN_FIRST_QUESTION", updated)
        self.assertIn("start-overlay", updated)
        self.assertIn("showQuestion(0)", updated)

    def test_inject_quick_preview_autostart_handles_millionaire_preloader_and_intro_video(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        html = "<html><body><section id='preloader'></section><video id='introVideo'></video><div id='playGameBtn'></div></body></html>"

        updated = inject_quick_preview_autostart(html)

        self.assertIn("preloader", updated)
        self.assertIn("introVideo", updated)
        self.assertIn("dispatchEvent", updated)
        self.assertIn("playGameBtn", updated)
        self.assertIn("window.dispatchEvent(loadEvent)", updated)
        self.assertIn("new MouseEvent('click'", updated)
        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_DIRECT_RENDER_MILLIONAIRE", updated)
        self.assertIn("document.getElementById('question')", updated)
        self.assertIn("document.getElementById('ans1')", updated)

    def test_inject_quick_preview_autostart_does_not_intercept_desktop_press_events_for_millionaire_controls(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        html = "<html><body><div id='gameWindow'></div><div id='ans1B'></div><div id='playGameBtn'></div></body></html>"

        updated = inject_quick_preview_autostart(html)

        self.assertNotIn("document.addEventListener('pointerdown', bridgeDownToClick, true);", updated)
        self.assertNotIn("document.addEventListener('mousedown', bridgeDownToClick, true);", updated)

    def test_inject_quick_preview_autostart_binds_manual_millionaire_preview_controls(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        html = "<html><body><div id='gameWindow'></div><div id='ans1B'><p class='answerText'><span id='ans1'></span></p></div><div id='ll5050'><div class='llText'>50:50</div></div></body></html>"

        updated = inject_quick_preview_autostart(html)

        self.assertIn(".answerText, .answerText *, .llText, .llText *", updated)
        self.assertIn("function bindMillionairePreviewAction(target, flagName, handler)", updated)
        self.assertIn("function installMillionairePreviewAnswerFallback(question, answerBlocks, answerTexts)", updated)
        self.assertIn("function bindMillionairePreviewLifelines(question, answerBlocks, answerTexts)", updated)
        self.assertIn("function resetMillionairePreviewState(answerBlocks)", updated)
        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_MILLIONAIRE_RESOLVED = false;", updated)
        self.assertIn("highlightAnswerReset", updated)
        self.assertIn("remove('answerCorrect', 'answerIncorrect', 'answerCheck', 'locked')", updated)
        self.assertIn("bindMillionairePreviewAction(block, '__EDUPLAY_PREVIEW_ANSWER_BOUND'", updated)
        self.assertIn("installMillionairePreviewAnswerFallback(question, answerBlocks, answerTexts);", updated)
        self.assertIn("bindMillionairePreviewAction(document.getElementById('ll5050')", updated)

    def test_inject_quick_preview_autostart_defers_overlay_hiding_until_gameplay_is_visible(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        html = "<html><head></head><body><div id='start-overlay'></div><div id='question-panel'></div></body></html>"

        updated = inject_quick_preview_autostart(html)

        self.assertNotIn("eduplay-quick-preview-style-head", updated)
        self.assertIn("function hasVisibleGameplay()", updated)
        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_MARK_STARTED", updated)
        self.assertIn("lateBootstrap", updated)

    def test_inject_quick_preview_autostart_does_not_use_hidden_question_text_as_started_signal(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        updated = inject_quick_preview_autostart("<html><body><div id='question-text'>Loading</div></body></html>")

        self.assertIn("questionText && isElementVisible(questionText)", updated)

    def test_inject_quick_preview_autostart_keeps_template_specific_open_first_question_hook(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        updated = inject_quick_preview_autostart("<html><body><div id='app'></div></body></html>")

        self.assertNotIn("window.__EDUPLAY_QUICK_PREVIEW_OPEN_FIRST_QUESTION = function ()", updated)
        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_FALLBACK_OPEN_FIRST_QUESTION", updated)
        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_DIRECT_RENDER_FISH", updated)

    def test_inject_quick_preview_autostart_is_idempotent(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        html = "<html><body><div id='app'></div></body></html>"

        once = inject_quick_preview_autostart(html)
        twice = inject_quick_preview_autostart(once)

        self.assertEqual(twice.count('window["__EDUPLAY_QUICK_PREVIEW_AUTO_START"] = true;'), 1)

    def test_inject_quick_preview_autostart_still_injects_when_template_only_references_auto_start_flag(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        html = """
<html>
<head>
  <script>
    function isQuickPreviewAutoStart() {
      return !!window.__EDUPLAY_QUICK_PREVIEW_AUTO_START;
    }
  </script>
</head>
<body><div id='app'></div></body>
</html>
""".strip()

        updated = inject_quick_preview_autostart(html)

        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_BOOTSTRAPPED", updated)
        self.assertIn("window[\"__EDUPLAY_QUICK_PREVIEW_AUTO_START\"] = true;", updated)

    def test_inject_quick_preview_autostart_adds_early_style_to_hide_preloaders(self):
        from eduplay.core.preview_utils import inject_quick_preview_autostart

        updated = inject_quick_preview_autostart("<html><head></head><body><div id='preloader'></div></body></html>")

        self.assertIn("eduplay-quick-preview-early-style", updated)
        self.assertIn("#start-overlay, #intro-screen, #mainMenu, #preloader", updated)
        self.assertIn("-webkit-app-region: no-drag", updated)

    def test_editor_screen_quick_preview_skips_placeholder_boot_file(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        self.assertFalse(EditorScreen._should_use_preview_placeholder("quick"))
        self.assertTrue(EditorScreen._should_use_preview_placeholder("full"))

    def test_fishing_template_retries_quick_preview_auto_open_without_user_click(self):
        template_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "assets_bundle",
                "templates_fish",
                "fishing_game.html",
            )
        )
        with open(template_path, "r", encoding="utf-8") as fh:
            html = fh.read()

        self.assertIn("function scheduleQuickPreviewAutoOpen(", html)
        self.assertIn("window.__EDUPLAY_QUICK_PREVIEW_OPEN_FIRST_QUESTION()", html)
        self.assertIn("window.setTimeout(function () {", html)

    def test_editor_center_panel_uses_translated_action_labels_for_current_locale(self):
        from eduplay.core.i18n import I18n
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        expected = {
            "en": {
                "duplicate_question_btn": "Duplicate",
                "save_question_btn": "Save Question",
                "quick_preview_question_btn": "Preview Question",
                "delete_question_btn": "Delete Question",
            },
            "vi": {
                "duplicate_question_btn": "Nhân bản",
                "save_question_btn": "Lưu câu hỏi",
                "quick_preview_question_btn": "Xem câu hỏi",
                "delete_question_btn": "Xoá câu hỏi",
            },
            "es": {
                "duplicate_question_btn": "Duplicar",
                "save_question_btn": "Save Question",
                "quick_preview_question_btn": "Preview Question",
                "delete_question_btn": "Eliminar pregunta",
            },
            "fr": {
                "duplicate_question_btn": "Dupliquer",
                "save_question_btn": "Save Question",
                "quick_preview_question_btn": "Preview Question",
                "delete_question_btn": "Supprimer la question",
            },
            "de": {
                "duplicate_question_btn": "Duplizieren",
                "save_question_btn": "Save Question",
                "quick_preview_question_btn": "Preview Question",
                "delete_question_btn": "Frage löschen",
            },
        }

        original_locale = I18n.locale
        for lang, labels in expected.items():
            I18n.set_locale(lang)
            try:
                with mock.patch("eduplay.core.settings_manager.SettingsManager.get_language", return_value=lang):
                    panel = EditorCenterPanel()
            finally:
                I18n.set_locale(original_locale)

            for attr, text in labels.items():
                btn_text = getattr(panel, attr).text()
                self.assertIn(text, btn_text, f"Missing '{text}' in {attr} for {lang}")

    def test_editor_screen_ignores_stale_preview_process_finish(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        old_proc = object()
        new_proc = object()
        dummy = types.SimpleNamespace(_preview_process=new_proc)
        hide = mock.Mock()
        fail = mock.Mock()

        EditorScreen._handle_preview_process_finished(dummy, old_proc, 1, hide, fail, "stale")

        self.assertIs(dummy._preview_process, new_proc)
        hide.assert_not_called()
        fail.assert_not_called()

    def test_editor_screen_current_preview_process_finish_reports_failure(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        proc = object()
        dummy = types.SimpleNamespace(_preview_process=proc)
        hide = mock.Mock()
        fail = mock.Mock()

        EditorScreen._handle_preview_process_finished(dummy, proc, 1, hide, fail, "boom")

        self.assertIsNone(dummy._preview_process)
        hide.assert_not_called()
        fail.assert_called_once_with("boom")


if __name__ == "__main__":
    unittest.main()
