import os
import sys
import json
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestProjectManagerMigrations(unittest.TestCase):
    def test_load_project_assigns_missing_question_ids_and_dedupes(self):
        from eduplay.core.project_manager import ProjectManager

        with tempfile.TemporaryDirectory() as tmp:
            pm = ProjectManager()
            pm.projects_dir = Path(tmp) / "Projects"
            pm.ensure_projects_directory()

            pid = "p1"
            proj_dir = pm.projects_dir / pid
            proj_dir.mkdir(parents=True, exist_ok=True)
            proj_file = proj_dir / f"{pid}.eduplay"

            data = {
                "id": pid,
                "name": "x",
                "description": "",
                "game_type": "quiz_classic",
                "created_at": "2026-01-01T00:00:00",
                "modified_at": "2026-01-01T00:00:00",
                "questions": [
                    {"question": "a"},
                    {"id": "q_same", "question": "b"},
                    {"id": "q_same", "question": "c"},
                ],
                "game_config": {},
                "media_files": [],
            }
            proj_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

            loaded = pm.load_project(pid)
            self.assertTrue(isinstance(loaded, dict))
            qs = loaded.get("questions") or []
            self.assertEqual(len(qs), 3)
            ids = [str(q.get("id") or "") for q in qs]
            self.assertTrue(all(i.strip() for i in ids))
            self.assertEqual(len(set(ids)), len(ids))


if __name__ == "__main__":
    unittest.main()

