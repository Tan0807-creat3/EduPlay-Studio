import os
import sys
import json
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestProjectManagerBrowserFilters(unittest.TestCase):
    def test_filter_projects_supports_search_recent_template_and_tag(self):
        from eduplay.core.project_manager import ProjectManager

        pm = ProjectManager()
        projects = [
            {
                "id": "p1",
                "name": "Math Grade 5",
                "description": "Fractions",
                "game_type": "quiz_classic",
                "tags": ["math", "grade5"],
                "modified_at": "2026-06-01T10:00:00",
            },
            {
                "id": "p2",
                "name": "History Challenge",
                "description": "Ancient world",
                "game_type": "quiz_millionaire",
                "tags": ["history"],
                "modified_at": "2026-06-02T10:00:00",
            },
            {
                "id": "p3",
                "name": "Ocean Hunt",
                "description": "Sea animals",
                "game_type": "fishing",
                "tags": ["science", "ocean"],
                "modified_at": "2026-06-03T10:00:00",
            },
        ]

        out = pm.filter_projects(
            projects,
            search_text="grade5",
            template_filter="all",
            tag_filter="all",
            recent_only=False,
            recent_project_ids=[],
        )
        self.assertEqual([p.get("id") for p in out], ["p1"])

        out = pm.filter_projects(
            projects,
            search_text="",
            template_filter="fishing",
            tag_filter="science",
            recent_only=False,
            recent_project_ids=[],
        )
        self.assertEqual([p.get("id") for p in out], ["p3"])

        out = pm.filter_projects(
            projects,
            search_text="",
            template_filter="all",
            tag_filter="all",
            recent_only=True,
            recent_project_ids=["p2", "p1"],
        )
        self.assertEqual([p.get("id") for p in out], ["p2", "p1"])

    def test_update_project_tags_persists_unique_normalized_values(self):
        from eduplay.core.project_manager import ProjectManager

        with tempfile.TemporaryDirectory() as tmp:
            pm = ProjectManager()
            pm.projects_dir = Path(tmp) / "Projects"
            pm.ensure_projects_directory()

            project = pm.create_project("Math", "desc", "quiz_classic")
            updated = pm.update_project_tags(project["id"], [" math ", "", "science", "math", None, "science "])

            self.assertEqual(updated.get("tags") or [], ["math", "science"])

            project_file = pm.projects_dir / project["id"] / f"{project['id']}.eduplay"
            saved = json.loads(project_file.read_text(encoding="utf-8"))
            self.assertEqual(saved.get("tags") or [], ["math", "science"])


if __name__ == "__main__":
    unittest.main()
