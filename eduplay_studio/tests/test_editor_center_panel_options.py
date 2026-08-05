import os
import sys
import unittest

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestEditorCenterPanelOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_edit_option_uses_embedded_editor_widget(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        item = panel.options_list.item(1)
        panel.edit_option(item)
        row_widget = panel.options_list.itemWidget(item)

        self.assertIsNotNone(row_widget)
        self.assertIs(panel.options_list.currentItem(), item)
        self.assertIsNotNone(row_widget.findChild(QLineEdit, "optionEditor"))
        self.assertIsNotNone(row_widget.findChild(QPushButton, "answerDeleteButton"))
        self.assertEqual(item.text(), "")

    def test_add_option_creates_embedded_editor_widget(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        start_count = panel.options_list.count()
        panel.add_option()

        self.assertEqual(panel.options_list.count(), start_count + 1)
        new_item = panel.options_list.item(start_count)
        row_widget = panel.options_list.itemWidget(new_item)

        self.assertIs(panel.options_list.currentItem(), new_item)
        self.assertIsNotNone(row_widget)
        self.assertIsNotNone(row_widget.findChild(QLineEdit, "optionEditor"))
        self.assertEqual(new_item.text(), "")

    def test_correct_option_uses_round_indicator_and_no_green_selection_highlight(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        panel.toggle_correct_option(panel.options_list.item(1))
        row_widget = panel.options_list.itemWidget(panel.options_list.item(1))
        correct_btn = row_widget.findChild(QPushButton, "optionCorrectButton")

        self.assertTrue(correct_btn.isCheckable())
        self.assertTrue(correct_btn.isChecked())
        self.assertEqual(correct_btn.text(), "✓")
        self.assertIn("border-radius: 12px", correct_btn.styleSheet())
        self.assertIn("QListWidget::item:selected", panel.options_list.styleSheet())
        self.assertIn("background: transparent", panel.options_list.styleSheet())

    def test_clicking_round_button_marks_option_correct(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        row_widget = panel.options_list.itemWidget(panel.options_list.item(2))
        correct_btn = row_widget.findChild(QPushButton, "optionCorrectButton")

        self.assertFalse(correct_btn.isChecked())
        correct_btn.click()

        second_data = panel.options_list.item(2).data(256)
        first_data = panel.options_list.item(0).data(256)
        self.assertTrue(correct_btn.isChecked())
        self.assertTrue(second_data["correct"])
        self.assertFalse(first_data["correct"])

    def test_multiple_choice_list_is_large_enough_for_four_answers_without_scroll(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        row_height = panel.options_list.itemWidget(panel.options_list.item(0)).height()
        expected_height = (row_height * 4) + (panel.options_list.spacing() * 3) + 20

        self.assertGreaterEqual(panel.options_list.minimumHeight(), expected_height)
        self.assertGreaterEqual(row_height, 36)

    def test_delete_option_button_removes_answer_row(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        start_count = panel.options_list.count()
        item = panel.options_list.item(0)
        row_widget = panel.options_list.itemWidget(item)
        delete_btn = row_widget.findChild(QPushButton, "answerDeleteButton")

        self.assertFalse(delete_btn.isVisible())
        delete_btn.click()

        self.assertEqual(panel.options_list.count(), start_count - 1)

    def test_matching_pair_uses_two_columns_and_supports_delete(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        panel._set_question_type("matching")
        start_count = panel.matching_pairs_list.count()
        panel.add_option()

        item = panel.matching_pairs_list.item(start_count)
        row_widget = panel.matching_pairs_list.itemWidget(item)
        left_editor = row_widget.findChild(QLineEdit, "matchingLeftEditor")
        right_editor = row_widget.findChild(QLineEdit, "matchingRightEditor")
        delete_btn = row_widget.findChild(QPushButton, "answerDeleteButton")

        self.assertIsNotNone(left_editor)
        self.assertIsNotNone(right_editor)
        self.assertEqual(item.text(), "")
        self.assertFalse(panel.bulk_options_btn.isVisible())
        self.assertIn("QListWidget::item:selected", panel.matching_pairs_list.styleSheet())
        self.assertIn("background: transparent", panel.matching_pairs_list.styleSheet())

        left_editor.setText("Danh bạn")
        right_editor.setText("Gây tổn thương thể chất")
        data = panel.get_question_data()
        self.assertEqual(data["pairs"][-1]["left"], "Danh bạn")
        self.assertEqual(data["pairs"][-1]["right"], "Gây tổn thương thể chất")

        delete_btn.click()
        self.assertEqual(panel.matching_pairs_list.count(), start_count)

    def test_fill_blank_question_hint_and_placeholder_follow_selected_type(self):
        from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel

        panel = EditorCenterPanel()
        fill_blank_btn = panel.question_type_group.button(2)
        multiple_choice_btn = panel.question_type_group.button(0)

        self.assertTrue(panel.fill_blank_question_hint.isHidden())
        self.assertNotIn("___", panel.question_text.placeholderText())

        fill_blank_btn.setChecked(True)
        panel.on_question_type_changed(fill_blank_btn)

        self.assertFalse(panel.fill_blank_question_hint.isHidden())
        self.assertIn("___", panel.fill_blank_question_hint.text())
        self.assertIn("___", panel.question_text.placeholderText())

        multiple_choice_btn.setChecked(True)
        panel.on_question_type_changed(multiple_choice_btn)

        self.assertTrue(panel.fill_blank_question_hint.isHidden())
        self.assertNotIn("___", panel.question_text.placeholderText())


if __name__ == "__main__":
    unittest.main()
