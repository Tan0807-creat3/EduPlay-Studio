import os
import sys
import types
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _DummyLeftPanel:
    def __init__(self, current_project=None):
        self.current_project = current_project
        self.set_project_calls = []
        self.loaded_question_titles = []

    def set_project(self, project):
        self.current_project = project
        self.set_project_calls.append(project)

    def load_questions(self):
        questions = (self.current_project or {}).get("questions") or []
        self.loaded_question_titles = [q.get("question") for q in questions if isinstance(q, dict)]
        return None

    def load_settings(self):
        return None

    def load_game_config(self):
        return None


class _DummyCenterPanel:
    def __init__(self, current_project=None):
        self.current_project = current_project
        self.loaded_project = None
        self.auto_points_check = types.SimpleNamespace(isChecked=lambda: True)

    def load_project(self, project):
        self.current_project = project
        self.loaded_project = project

    def load_game_config(self, *_args, **_kwargs):
        return None

    def set_question(self, *_args, **_kwargs):
        return None

    def apply_project_permissions(self, *_args, **_kwargs):
        return None

    def set_question(self, question, index=-1):
        self.last_question = question
        self.last_index = index


class _DummyProjectManager:
    def __init__(self, current_project=None):
        self.saved_project = None
        self.current_project = current_project

    def save_project(self, project):
        self.saved_project = project
        self.current_project = project
        return True

    def get_current_project(self):
        return self.current_project

    def duplicate_question(self, question_id):
        questions = (self.current_project or {}).get("questions") or []
        for index, question in enumerate(questions):
            if str(question.get("id") or "") != str(question_id or ""):
                continue
            duplicated = dict(question)
            duplicated["id"] = f"{question_id}_copy"
            questions.insert(index + 1, duplicated)
            self.current_project["questions"] = questions
            self.saved_project = self.current_project
            return duplicated["id"]
        return ""


class _DummyQuestionList:
    def __init__(self):
        self._items = []
        self.current_item = None
        self.current_row = -1

    def count(self):
        return len(self._items)

    def item(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def setCurrentItem(self, item):
        self.current_item = item

    def currentRow(self):
        return self.current_row


class TestEditorSettingsPayloads(unittest.TestCase):
    def test_on_question_settings_applied_updates_randomize_and_auto_points(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        dummy = types.SimpleNamespace()
        dummy.current_project = {
            "id": "p1",
            "questions": [
                {"id": "q1", "question": "Q1", "time_limit": 10, "points": 10},
                {"id": "q2", "question": "Q2", "time_limit": 10, "points": 10},
            ],
            "game_config": {
                "question_time": 10,
                "randomize_questions": False,
                "auto_points_enabled": True,
                "total_points": 100,
            },
        }
        dummy.left_panel = _DummyLeftPanel()
        dummy.center_panel = _DummyCenterPanel()
        dummy.project_manager = _DummyProjectManager()
        dummy.current_question_index = 0
        dummy._copy_file_to_project_media = lambda p: p
        dummy.show_toast = lambda *args, **kwargs: None

        EditorScreen.on_question_settings_applied(
            dummy,
            {
                "default_question_time": 30,
                "is_millionaire": False,
                "music_mode": "builtin_1",
                "custom_music_path": "",
                "randomize_questions": True,
                "auto_points_enabled": False,
                "total_points": 100,
            },
        )

        cfg = dummy.current_project.get("game_config") or {}
        self.assertEqual(cfg.get("question_time"), 30)
        self.assertTrue(cfg.get("randomize_questions"))
        self.assertFalse(cfg.get("auto_points_enabled"))
        self.assertEqual(cfg.get("total_points"), 100)
        self.assertTrue(all(q.get("time_limit") == 30 for q in dummy.current_project.get("questions") or []))

    def test_on_question_settings_applied_resyncs_left_and_center_panel_projects(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        stale_project = {
            "id": "stale",
            "questions": [{"id": "old-q", "question": "Old"}],
            "game_config": {"question_time": 15},
        }
        live_project = {
            "id": "live",
            "questions": [{"id": "q1", "question": "Q1", "time_limit": 10}],
            "game_config": {"question_time": 10},
        }

        left_panel = _DummyLeftPanel(current_project=stale_project)
        center_panel = _DummyCenterPanel(current_project=stale_project)

        dummy = types.SimpleNamespace()
        dummy.current_project = live_project
        dummy.left_panel = left_panel
        dummy.center_panel = center_panel
        dummy.project_manager = _DummyProjectManager()
        dummy.current_question_index = -1
        dummy._copy_file_to_project_media = lambda p: p
        dummy.show_toast = lambda *args, **kwargs: None

        EditorScreen.on_question_settings_applied(
            dummy,
            {
                "default_question_time": 45,
                "is_millionaire": False,
                "music_mode": "builtin_1",
                "custom_music_path": "",
            },
        )

        self.assertIs(left_panel.current_project, dummy.current_project)
        self.assertIs(center_panel.current_project, dummy.current_project)
        self.assertIs(center_panel.loaded_project, dummy.current_project)

    def test_on_question_updated_save_resyncs_left_panel_and_refreshes_titles(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        stale_project = {
            "id": "stale",
            "questions": [{"id": "q1", "question": "New Question"}],
            "game_config": {},
        }
        live_project = {
            "id": "live",
            "questions": [{"id": "q1", "question": "New Question"}],
            "game_config": {},
        }

        left_panel = _DummyLeftPanel(current_project=stale_project)
        center_panel = _DummyCenterPanel(current_project=stale_project)
        dummy = types.SimpleNamespace()
        dummy.current_project = live_project
        dummy.left_panel = left_panel
        dummy.center_panel = center_panel
        dummy.project_manager = _DummyProjectManager()
        dummy.current_question_index = 0
        dummy._copy_file_to_project_media = lambda p: p
        dummy._normalize_question_media = lambda q: q
        dummy.show_toast = lambda *args, **kwargs: None

        EditorScreen.on_question_updated(
            dummy,
            {"question": {"id": "q1", "question": "Câu hỏi đã lưu"}},
        )

        self.assertIs(left_panel.current_project, dummy.current_project)
        self.assertEqual(left_panel.loaded_question_titles, ["Câu hỏi đã lưu"])

    def test_on_question_updated_delete_rebalances_points_when_auto_points_enabled(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        project = {
            "id": "p1",
            "questions": [
                {"id": "q1", "question": "Q1", "points": 34},
                {"id": "q2", "question": "Q2", "points": 33},
                {"id": "q3", "question": "Q3", "points": 33},
            ],
            "game_config": {
                "auto_points_enabled": True,
                "total_points": 100,
            },
        }

        left_panel = _DummyLeftPanel(current_project=project)
        center_panel = _DummyCenterPanel(current_project=project)
        dummy = types.SimpleNamespace()
        dummy.current_project = project
        dummy.left_panel = left_panel
        dummy.center_panel = center_panel
        dummy.project_manager = _DummyProjectManager()
        dummy.current_question_index = 1
        dummy._copy_file_to_project_media = lambda p: p
        dummy._normalize_question_media = lambda q: q
        dummy.show_toast = lambda *args, **kwargs: None

        EditorScreen.on_question_updated(
            dummy,
            {"action": "delete", "question": {"id": "q2"}, "index": 1},
        )

        self.assertEqual(len(dummy.current_project.get("questions") or []), 2)
        self.assertEqual(
            [q.get("points") for q in dummy.current_project.get("questions") or []],
            [50, 50],
        )

    def test_on_question_updated_duplicate_uses_project_manager_and_assigns_new_id(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        project = {
            "id": "p1",
            "questions": [
                {"id": "q1", "question": "Q1", "points": 10},
            ],
            "game_config": {},
        }

        left_panel = _DummyLeftPanel(current_project=project)
        center_panel = _DummyCenterPanel(current_project=project)
        project_manager = _DummyProjectManager(project)
        dummy = types.SimpleNamespace()
        dummy.current_project = project
        dummy.left_panel = left_panel
        dummy.center_panel = center_panel
        dummy.project_manager = project_manager
        dummy.current_question_index = 0
        dummy._copy_file_to_project_media = lambda p: p
        dummy._normalize_question_media = lambda q: q
        dummy.show_toast = lambda *args, **kwargs: None

        EditorScreen.on_question_updated(
            dummy,
            {"action": "duplicate", "question": {"id": "q1", "question": "Q1"}},
        )

        ids = [q.get("id") for q in dummy.current_project.get("questions") or []]
        self.assertEqual(ids, ["q1", "q1_copy"])
        self.assertIs(project_manager.saved_project, dummy.current_project)

    def test_on_question_settings_applied_can_limit_apply_to_selected_fields(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        dummy = types.SimpleNamespace()
        dummy.current_project = {
            "id": "p1",
            "questions": [
                {"id": "q1", "question": "Q1", "time_limit": 10, "points": 10},
                {"id": "q2", "question": "Q2", "time_limit": 10, "points": 10},
            ],
            "game_config": {
                "question_time": 10,
                "randomize_questions": False,
                "auto_points_enabled": True,
                "total_points": 100,
            },
        }
        dummy.left_panel = _DummyLeftPanel()
        dummy.center_panel = _DummyCenterPanel()
        dummy.project_manager = _DummyProjectManager(dummy.current_project)
        dummy.current_question_index = 0
        dummy._copy_file_to_project_media = lambda p: p
        dummy.show_toast = lambda *args, **kwargs: None

        EditorScreen.on_question_settings_applied(
            dummy,
            {
                "default_question_time": 30,
                "is_millionaire": False,
                "music_mode": "builtin_1",
                "custom_music_path": "",
                "randomize_questions": True,
                "auto_points_enabled": False,
                "apply_to_all_fields": ["randomize_questions"],
            },
        )

        cfg = dummy.current_project.get("game_config") or {}
        self.assertEqual(cfg.get("question_time"), 10)
        self.assertTrue(cfg.get("randomize_questions"))
        self.assertTrue(cfg.get("auto_points_enabled"))
        self.assertTrue(all(q.get("time_limit") == 10 for q in dummy.current_project.get("questions") or []))

    def test_left_panel_add_question_rebalances_points_immediately_when_auto_points_enabled(self):
        from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel

        project = {
            "id": "p1",
            "questions": [
                {"id": "q1", "question": "Q1", "points": 50},
                {"id": "q2", "question": "Q2", "points": 50},
            ],
            "game_config": {
                "auto_points_enabled": True,
                "total_points": 100,
            },
        }

        dummy = types.SimpleNamespace()
        dummy.current_project = project
        dummy.questions_list = _DummyQuestionList()
        dummy.load_questions = lambda: None
        dummy.on_question_selected = lambda *_args, **_kwargs: None

        EditorLeftPanel.add_question(dummy)

        questions = dummy.current_project.get("questions") or []
        self.assertEqual(len(questions), 3)
        self.assertEqual(
            [q.get("points") for q in questions],
            [34, 33, 33],
        )

    def test_on_question_selected_rebalances_and_persists_auto_points_before_question_save(self):
        from eduplay.ui.screens.editor_screen import EditorScreen

        project = {
            "id": "p1",
            "questions": [
                {"id": "q1", "question": "Q1", "points": 50},
                {"id": "q2", "question": "Q2", "points": 50},
                {"id": "q3", "question": "Q3", "points": 0},
            ],
            "game_config": {
                "auto_points_enabled": True,
                "total_points": 100,
            },
        }

        question_list = _DummyQuestionList()
        question_list.current_row = 2
        left_panel = types.SimpleNamespace(
            current_project=project,
            questions_list=question_list,
        )
        center_panel = _DummyCenterPanel(current_project=project)
        project_manager = _DummyProjectManager()

        dummy = types.SimpleNamespace()
        dummy.current_project = project
        dummy.left_panel = left_panel
        dummy.center_panel = center_panel
        dummy.project_manager = project_manager
        dummy.current_question_index = -1

        EditorScreen.on_question_selected(dummy, project["questions"][2])

        self.assertEqual(
            [q.get("points") for q in project.get("questions") or []],
            [34, 33, 33],
        )
        self.assertIs(center_panel.last_question, project["questions"][2])
        self.assertEqual(center_panel.last_index, 2)
        self.assertIs(project_manager.saved_project, project)


if __name__ == "__main__":
    unittest.main()
