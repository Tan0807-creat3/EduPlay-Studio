import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


class TestDeployFirebaseHosting(unittest.TestCase):
    def test_stage_hosting_directory_supports_modern_and_legacy_sources(self):
        from deploy_firebase_hosting import stage_hosting_directory

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            modern = repo_root / "eduplay_studio" / "eduplay" / "resources" / "firebase_hosting"
            legacy = repo_root / "firebase_hosting"
            modern.mkdir(parents=True, exist_ok=True)
            legacy.mkdir(parents=True, exist_ok=True)
            (modern / "firebase_viewer.html").write_text("modern-viewer", encoding="utf-8")
            (legacy / "firebase_viewer.html").write_text("legacy-viewer", encoding="utf-8")

            modern_stage = stage_hosting_directory("modern", repo_root=repo_root)
            legacy_stage = stage_hosting_directory("legacy", repo_root=repo_root)

            self.assertEqual(
                (modern_stage / "firebase_viewer.html").read_text(encoding="utf-8"),
                "modern-viewer",
            )
            self.assertEqual(
                (legacy_stage / "firebase_viewer.html").read_text(encoding="utf-8"),
                "legacy-viewer",
            )

    def test_stage_hosting_directory_excludes_sensitive_firebase_credentials(self):
        from deploy_firebase_hosting import stage_hosting_directory

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            modern = repo_root / "eduplay_studio" / "eduplay" / "resources" / "firebase_hosting"
            modern.mkdir(parents=True, exist_ok=True)
            (modern / "firebase_viewer.html").write_text("viewer", encoding="utf-8")
            (modern / "eduplay-game-firebase-adminsdk-demo.json").write_text("secret", encoding="utf-8")
            (modern / "firebase_service_account.b64").write_text("secret", encoding="utf-8")
            (modern / "firebase_service_account.fernet").write_text("secret", encoding="utf-8")

            staged = stage_hosting_directory("modern", repo_root=repo_root)

            self.assertTrue((staged / "firebase_viewer.html").exists())
            self.assertFalse((staged / "eduplay-game-firebase-adminsdk-demo.json").exists())
            self.assertFalse((staged / "firebase_service_account.b64").exists())
            self.assertFalse((staged / "firebase_service_account.fernet").exists())


if __name__ == "__main__":
    unittest.main()
