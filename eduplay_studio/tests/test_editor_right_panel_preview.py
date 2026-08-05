import os
import sys
import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from eduplay.core.i18n import I18n
from eduplay.ui.widgets.editor_right_panel import EditorRightPanel


LANGUAGES = ("en", "vi", "es", "fr", "de")


class TestEditorRightPanelPreviewI18n(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_fill_blank_preview_renders_inline_input_and_translated_accepted_answers(self):
        for lang in LANGUAGES:
            original_locale = I18n.locale
            I18n.set_locale(lang)
            try:
                panel = EditorRightPanel()
                html = panel.generate_question_html(
                    {
                        "question": "Thu do cua Viet Nam la ___",
                        "type": "fill_blank",
                        "answers": ["Ha Noi", "Hà Nội"],
                    }
                )
            finally:
                I18n.set_locale(original_locale)

            self.assertIn('class="question-text fill-blank-inline"', html, lang)
            self.assertIn('class="text-input inline-blank-input"', html, lang)
            self.assertIn("Thu do cua Viet Nam la", html, lang)
            self.assertEqual(html.count('class="question-text'), 1, lang)

            expected = I18n.t("quiz.accepted_answers", lang)
            self.assertIn(f"{expected} Ha Noi, Hà Nội", html, lang)

    def test_fill_blank_preview_appends_input_when_no_marker_exists(self):
        for lang in LANGUAGES:
            original_locale = I18n.locale
            I18n.set_locale(lang)
            try:
                panel = EditorRightPanel()
                html = panel.generate_question_html(
                    {
                        "question": "Nhap dap an dung",
                        "type": "fill_blank",
                        "answers": ["abc"],
                    }
                )
            finally:
                I18n.set_locale(original_locale)

            self.assertIn('class="question-inline-text">Nhap dap an dung</span>', html, lang)
            self.assertIn('class="text-input inline-blank-input"', html, lang)

    def test_multiple_choice_preview_uses_translated_option_fallback(self):
        for lang in LANGUAGES:
            original_locale = I18n.locale
            I18n.set_locale(lang)
            try:
                panel = EditorRightPanel()
                html = panel.generate_question_html(
                    {
                        "question": "What is 2+2?",
                        "type": "multiple_choice",
                        "options": [
                            {"text": "Three", "correct": False},
                            {"text": "", "correct": True},
                        ],
                    }
                )
            finally:
                I18n.set_locale(original_locale)

            expected_label = I18n.t("quiz.answer_option_label", lang, n=2)
            self.assertIn(f"{expected_label}", html, lang)
            self.assertIn("Three", html, lang)

    def test_true_false_preview_uses_translated_true_false_labels(self):
        for lang in LANGUAGES:
            original_locale = I18n.locale
            I18n.set_locale(lang)
            try:
                panel = EditorRightPanel()
                html = panel.generate_question_html(
                    {
                        "question": "The sky is blue",
                        "type": "true_false",
                        "correct_answer": True,
                    }
                )
            finally:
                I18n.set_locale(original_locale)

            true_text = I18n.t("quiz.true", lang)
            false_text = I18n.t("quiz.false", lang)
            self.assertIn(true_text, html, lang)
            self.assertIn(false_text, html, lang)

    def test_matching_preview_uses_translated_column_headers(self):
        for lang in LANGUAGES:
            original_locale = I18n.locale
            I18n.set_locale(lang)
            try:
                panel = EditorRightPanel()
                html = panel.generate_question_html(
                    {
                        "question": "Match them",
                        "type": "matching",
                        "pairs": [
                            {"left": "A", "right": "1"},
                        ],
                    }
                )
            finally:
                I18n.set_locale(original_locale)

            left_header = I18n.t("quiz.matching_left", lang)
            right_header = I18n.t("quiz.matching_right", lang)
            self.assertIn(left_header, html, lang)
            self.assertIn(right_header, html, lang)

    def test_short_answer_preview_uses_translated_label_and_limit(self):
        for lang in LANGUAGES:
            original_locale = I18n.locale
            I18n.set_locale(lang)
            try:
                panel = EditorRightPanel()
                html = panel.generate_question_html(
                    {
                        "question": "Say hello",
                        "type": "short_answer",
                        "answers": ["Hello"],
                        "max_length": 50,
                    }
                )
            finally:
                I18n.set_locale(original_locale)

            label = I18n.t("quiz.short_answer_label", lang)
            limit = I18n.t("quiz.limit_chars", lang, max_length=50)
            self.assertIn(label, html, lang)
            self.assertIn(limit, html, lang)

    def test_info_panel_uses_translated_type_names(self):
        type_map = {
            "multiple_choice": "quiz.type_multiple_choice",
            "true_false": "quiz.type_true_false",
            "fill_blank": "quiz.type_fill_blank",
            "matching": "quiz.type_matching",
            "short_answer": "quiz.type_short_answer",
        }

        for lang in LANGUAGES:
            original_locale = I18n.locale
            I18n.set_locale(lang)
            try:
                panel = EditorRightPanel()
                for q_type, key in type_map.items():
                    panel.update_info_panel({"type": q_type})
                    expected = I18n.t(key, lang)
                    self.assertEqual(panel.info_items["type"].text(), expected, lang)
            finally:
                I18n.set_locale(original_locale)


if __name__ == "__main__":
    unittest.main()
