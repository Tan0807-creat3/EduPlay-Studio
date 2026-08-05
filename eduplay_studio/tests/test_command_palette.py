import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestCommandPalette(unittest.TestCase):
    def test_filter_items_ranks_prefix_match_higher(self):
        from eduplay.core.command_palette import filter_items

        items = [
            {"id": "a", "title": "Open Project", "keywords": ["open", "project"]},
            {"id": "b", "title": "Export HTML", "keywords": ["export", "html"]},
            {"id": "c", "title": "Create New Project", "keywords": ["create", "new"]},
        ]
        out = filter_items(items, "op")
        self.assertEqual(out[0]["id"], "a")

    def test_filter_items_matches_keywords(self):
        from eduplay.core.command_palette import filter_items

        items = [
            {"id": "a", "title": "Open Project", "keywords": ["open", "project"]},
            {"id": "b", "title": "Export HTML", "keywords": ["export", "html"]},
        ]
        out = filter_items(items, "htm")
        self.assertEqual(out[0]["id"], "b")

    def test_build_palette_items_includes_recent_and_current_project_flags(self):
        from eduplay.core.command_palette import build_palette_items

        projects = [
            {
                "id": "p1",
                "name": "Math Grade 5",
                "description": "Fractions",
                "game_type": "quiz_classic",
                "tags": ["math", "grade5"],
            },
            {
                "id": "p2",
                "name": "Ocean Quiz",
                "description": "Sea animals",
                "game_type": "fishing",
                "tags": ["science"],
            },
        ]
        recent_projects = [{"id": "p2", "name": "Ocean Quiz"}]

        out = build_palette_items(projects, recent_projects, current_project_id="p1", lang="en")
        ids = [item.get("id") for item in out]

        self.assertIn("action:new_project", ids)
        self.assertIn("project:p1", ids)
        self.assertIn("project:p2", ids)

        p1 = next(item for item in out if item.get("id") == "project:p1")
        p2 = next(item for item in out if item.get("id") == "project:p2")
        self.assertTrue(p1.get("is_current"))
        self.assertTrue(p2.get("is_recent"))
        self.assertIn("science", p2.get("keywords", []))

    def test_build_palette_items_localizes_default_actions(self):
        from eduplay.core.command_palette import build_palette_items
        from eduplay.core.i18n import I18n

        expected_keys = {
            "action:new_project": "command_palette.action_new_project",
            "action:open_projects": "command_palette.action_open_projects",
            "action:quick_preview": "command_palette.action_quick_preview",
            "action:full_preview": "command_palette.action_full_preview",
            "action:export_html": "command_palette.action_export_html",
        }

        for lang in ("en", "vi", "es", "fr", "de"):
            out = build_palette_items([], [], current_project_id="", lang=lang)
            titles_by_id = {item["id"]: item["title"] for item in out if str(item.get("id", "")).startswith("action:")}
            for action_id, key in expected_keys.items():
                self.assertEqual(
                    titles_by_id.get(action_id),
                    I18n.t(key, lang),
                    f"Wrong title for {action_id} in {lang}",
                )


if __name__ == "__main__":
    unittest.main()
