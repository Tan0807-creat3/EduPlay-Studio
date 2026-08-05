import os
import sys
import json
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestDuplicateProjectAndQuestion(unittest.TestCase):
    def test_duplicate_project_creates_new_id_and_copies_questions(self):
        from eduplay.core.project_manager import ProjectManager

        with tempfile.TemporaryDirectory() as tmp:
            pm = ProjectManager()
            pm.projects_dir = Path(tmp) / "Projects"
            pm.ensure_projects_directory()

            p = pm.create_project("Math", "desc", "quiz_classic")
            p["questions"] = [{"id": "q1", "question": "a"}, {"id": "q2", "question": "b"}]
            p["tags"] = ["Toán"]
            pm.save_project(p)

            out = pm.duplicate_project(p["id"])
            self.assertTrue(isinstance(out, dict))
            self.assertNotEqual(out["id"], p["id"])
            self.assertEqual(len(out.get("questions") or []), 2)
            self.assertNotEqual(out["questions"][0]["id"], "q1")
            self.assertNotEqual(out["questions"][1]["id"], "q2")
            self.assertEqual(out.get("tags") or [], ["Toán"])

            f = pm.projects_dir / out["id"] / f"{out['id']}.eduplay"
            self.assertTrue(f.exists())
            loaded = json.loads(f.read_text(encoding="utf-8"))
            self.assertEqual(loaded["id"], out["id"])

    def test_duplicate_question_in_current_project_assigns_new_id(self):
        from eduplay.core.project_manager import ProjectManager

        with tempfile.TemporaryDirectory() as tmp:
            pm = ProjectManager()
            pm.projects_dir = Path(tmp) / "Projects"
            pm.ensure_projects_directory()

            p = pm.create_project("x", "", "quiz_classic")
            p["questions"] = [{"id": "q1", "question": "a"}]
            pm.save_project(p)
            pm.set_current_project(p)

            new_id = pm.duplicate_question("q1")
            self.assertTrue(isinstance(new_id, str))
            qs = pm.get_current_project().get("questions") or []
            self.assertEqual(len(qs), 2)
            ids = [q.get("id") for q in qs]
            self.assertEqual(len(set(ids)), 2)
            self.assertIn(new_id, ids)


if __name__ == "__main__":
    unittest.main()

