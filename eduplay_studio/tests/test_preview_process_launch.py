import os
import sys
import unittest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestPreviewProcessLaunch(unittest.TestCase):
    def test_build_preview_process_command_uses_same_exe_when_frozen(self):
        from eduplay.core.preview_runner import build_preview_process_command

        program, args = build_preview_process_command(
            executable=r"C:\Apps\EduPlayStudio\EduPlayStudio.exe",
            uri="file:///C:/temp/sample_preview.html",
            title="Preview",
            frozen=True,
        )

        self.assertEqual(program, r"C:\Apps\EduPlayStudio\EduPlayStudio.exe")
        self.assertEqual(args, ["--preview-runner", "file:///C:/temp/sample_preview.html", "Preview"])

    def test_build_preview_process_command_uses_python_module_when_python_exists(self):
        from eduplay.core.preview_runner import build_preview_process_command

        program, args = build_preview_process_command(
            executable=r"C:\Python312\python.exe",
            uri="file:///C:/temp/sample_preview.html",
            title="Preview",
            frozen=False,
        )

        self.assertEqual(program, r"C:\Python312\python.exe")
        self.assertEqual(args, ["-u", "-m", "eduplay.core.preview_runner", "file:///C:/temp/sample_preview.html", "Preview"])


if __name__ == "__main__":
    unittest.main()
