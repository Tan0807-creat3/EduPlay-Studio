import json
import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestI18nKeyCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n")
        )
        cls.languages = ("en", "vi", "es", "fr", "de")
        cls.data = {}
        for lang in cls.languages:
            with open(os.path.join(cls.base_dir, f"{lang}.json"), "r", encoding="utf-8") as f:
                cls.data[lang] = json.load(f)

    def _assert_key_exists(self, key):
        for lang in self.languages:
            self.assertIn(
                key,
                self.data[lang],
                f"Missing i18n key '{key}' in {lang}.json",
            )

    def test_acknowledgements_keys_exist(self):
        self._assert_key_exists("credits.ack.title")
        self._assert_key_exists("credits.ack.body")

    def test_editor_center_action_keys_exist(self):
        keys = [
            "editor.center.duplicate",
            "editor.center.save",
            "editor.center.delete",
            "editor.center.quick_preview",
            "editor.center.option_placeholder",
            "editor.center.left_column",
            "editor.center.right_column",
            "editor.center.true",
            "editor.center.false",
            "editor.center.question_text",
            "editor.center.question_placeholder",
            "editor.center.acceptable_answers",
            "editor.center.acceptable_placeholder",
            "editor.center.case_sensitive",
            "editor.center.matching_pairs",
            "editor.center.matching_placeholder",
            "editor.center.expected",
            "editor.center.expected_placeholder",
            "editor.center.keywords_label",
            "editor.center.keywords_placeholder",
            "editor.center.max_points",
            "editor.center.rubric_label",
            "editor.center.rubric_placeholder",
            "editor.center.save_question",
            "editor.center.welcome",
            "editor.center.no_question",
            "editor.center.remove_btn",
        ]
        for key in keys:
            self._assert_key_exists(key)

    def test_editor_left_panel_keys_exist(self):
        keys = [
            "editor.left.tab_questions",
            "editor.left.tab_settings",
            "editor.left.add_question_btn",
            "editor.left.import_btn",
            "editor.left.game_type_label",
            "editor.left.game_type_quiz",
            "editor.left.game_type_millionaire",
            "editor.left.game_type_fishing",
            "editor.left.difficulty_label",
            "editor.left.difficulty_easy",
            "editor.left.difficulty_medium",
            "editor.left.difficulty_hard",
            "editor.left.time_settings_label",
            "editor.left.question_time_label",
            "editor.left.enable_time_limit",
            "editor.left.scoring_label",
            "editor.left.basic_settings_label",
            "editor.left.show_explanations",
            "editor.left.randomize_questions",
            "editor.left.settings_group_title",
            "editor.left.settings_default_time_label",
            "editor.left.settings_music_label",
            "editor.left.settings_music_custom",
            "editor.left.settings_music_random",
            "editor.left.settings_music_builtin_1",
            "editor.left.settings_music_builtin_2",
            "editor.left.settings_custom_music_label",
            "editor.left.settings_custom_music_placeholder",
            "editor.left.settings_browse_btn",
            "editor.left.settings_apply_btn",
            "editor.left.settings_apply_selected_btn",
            "editor.left.settings_apply_selected_title",
            "editor.left.settings_apply_selected_desc",
            "editor.left.settings_field_time",
            "editor.left.settings_field_shuffle",
            "editor.left.settings_field_music",
            "editor.left.settings_field_export_mode",
            "editor.left.settings_field_auto_points",
            "editor.left.delete_confirm_title",
            "editor.left.delete_confirm_message",
            "editor.left.new_question",
            "editor.left.search_placeholder",
            "editor.left.search_btn",
            "editor.left.media_categories_title",
            "editor.left.asset_categories",
            "editor.left.assets_group",
        ]
        for key in keys:
            self._assert_key_exists(key)

    def test_editor_screen_header_keys_exist(self):
        keys = [
            "editor.back",
            "editor.save",
            "editor.preview_title",
            "editor.export_web",
            "editor.export_html",
            "editor.unsaved_title",
            "editor.unsaved_msg",
            "editor.unsaved_exit_msg",
        ]
        for key in keys:
            self._assert_key_exists(key)

    def test_home_and_nav_keys_exist(self):
        keys = [
            "nav.home",
            "nav.projects",
            "nav.preview",
            "nav.quick_actions",
            "home.quick.create",
            "home.quick.recent",
            "home.quick.import",
            "home.quick.publish",
            "home.quick.resume",
            "tooltip.leftnav.home",
            "tooltip.leftnav.projects",
            "tooltip.leftnav.preview",
            "tooltip.quick.recent",
            "tooltip.quick.publish",
            "tooltip.quick.resume",
        ]
        for key in keys:
            self._assert_key_exists(key)

    def test_quiz_preview_keys_exist(self):
        keys = [
            "quiz.true",
            "quiz.false",
            "quiz.answer_option_label",
            "quiz.accepted_answers",
            "quiz.matching_left",
            "quiz.matching_right",
            "quiz.short_answer_label",
            "quiz.limit_chars",
            "quiz.type_multiple_choice",
            "quiz.type_true_false",
            "quiz.type_fill_blank",
            "quiz.type_matching",
            "quiz.type_short_answer",
            "quiz.correct_answer",
        ]
        for key in keys:
            self._assert_key_exists(key)

    def test_command_palette_keys_exist(self):
        keys = [
            "command_palette.title",
            "command_palette.placeholder",
            "command_palette.hint",
            "command_palette.action_new_project",
            "command_palette.action_open_projects",
            "command_palette.action_quick_preview",
            "command_palette.action_full_preview",
            "command_palette.action_export_html",
        ]
        for key in keys:
            self._assert_key_exists(key)

    def test_preview_keys_exist(self):
        keys = [
            "preview.placeholder_heading",
            "preview.placeholder_sub",
        ]
        for key in keys:
            self._assert_key_exists(key)

    def test_settings_keys_exist(self):
        keys = [
            "settings.restart_required_title",
            "settings.restart_required_message",
            "settings.restart_now",
            "settings.restart_later",
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
        ]
        for key in keys:
            self._assert_key_exists(key)


if __name__ == "__main__":
    unittest.main()
