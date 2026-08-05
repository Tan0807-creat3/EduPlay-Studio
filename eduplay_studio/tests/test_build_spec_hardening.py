import os
import sys
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestBuildSpecHardening(unittest.TestCase):
    def test_spec_includes_core_pyside6_modules(self):
        spec_path = Path(__file__).parent.parent / "EduPlayStudio.spec"
        content = spec_path.read_text(encoding="utf-8")
        self.assertIn("'PySide6.QtWidgets'", content)
        self.assertIn("'PySide6.QtCore'", content)
        self.assertIn("'PySide6.QtGui'", content)

    def test_spec_does_not_ship_firebase_hosting_directory(self):
        spec_path = Path(__file__).parent.parent / "EduPlayStudio.spec"
        content = spec_path.read_text(encoding="utf-8")
        self.assertNotIn("resources', 'firebase_hosting", content)
        self.assertNotIn("resources', 'firebase_hosting')", content)

    def test_build_script_installs_runtime_dependencies(self):
        script_path = Path(__file__).parent.parent.parent / "build_release.bat"
        content = script_path.read_text(encoding="utf-8")
        self.assertIn("pip install -r requirements.txt", content)


if __name__ == "__main__":
    unittest.main()
