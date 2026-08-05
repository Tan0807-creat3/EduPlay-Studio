import os
import sys
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestMillionaireSingleFileExport(unittest.TestCase):
    def _extract_game_data(self, html: str) -> dict:
        match = re.search(r'<script id="game-data" type="application/json">(.+?)</script>', html, re.DOTALL)
        self.assertIsNotNone(match, "missing game-data script tag")
        return json.loads(match.group(1))

    def _write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _write_bytes(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def test_export_millionaire_single_file_embeds_local_assets(self):
        from eduplay.core.export_service import ExportService

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            millionaire_dir = root / "assets_bundle" / "millionaire"

            self._write_text(
                millionaire_dir / "index.html",
                """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="css/styles.css">
<link rel="stylesheet" href="css/mobile.css">
<script src="js/sounds.js"></script>
<script src="js/app.js"></script>
<script src="js/functions.js"></script>
</head>
<body>
<img id="logo" src="images/Logo.png">
<div id="banner"></div>
<audio id="music" src="sounds/Music/0_to_1000.mp3"></audio>
<audio id="effects" src="sounds/Effects/correct answer.mp3"></audio>
<video id="introVideo" preload="auto"><source src="images/IntroVideo.mp4"></video>
</body>
</html>
""".strip(),
            )
            self._write_text(
                millionaire_dir / "css" / "styles.css",
                'body{background-image:url("../images/background.png");}',
            )
            self._write_text(
                millionaire_dir / "css" / "mobile.css",
                '#banner{background-image:url("../images/backgroundGame.png");}',
            )
            self._write_text(millionaire_dir / "js" / "sounds.js", "window.SOUNDS = true;")
            self._write_text(millionaire_dir / "js" / "app.js", "window.APP = true;")
            self._write_text(millionaire_dir / "js" / "functions.js", "window.FNS = true;")

            for rel_path in [
                "images/Logo.png",
                "images/background.png",
                "images/backgroundGame.png",
                "images/IntroVideo.mp4",
                "sounds/Music/0_to_1000.mp3",
                "sounds/Effects/correct answer.mp3",
            ]:
                self._write_bytes(millionaire_dir / rel_path, b"eduplay")

            def fake_load_asset_text(asset_path: str) -> str:
                prefix = "assets_bundle/millionaire/"
                self.assertTrue(asset_path.startswith(prefix))
                local_path = millionaire_dir / asset_path[len(prefix):]
                return local_path.read_text(encoding="utf-8")

            svc = ExportService()
            svc.assets_dir = root / "assets_bundle"
            output_file = root / "millionaire.html"
            project = {
                "id": "p1",
                "name": "Ai la trieu phu",
                "language": "vi",
                "questions": [
                    {
                        "question": "Thu do Nhat Ban?",
                        "options": ["Kyoto", "Tokyo", "Osaka", "Nagoya"],
                        "correct_answer": 1,
                        "time_limit": 45,
                    }
                ],
                "game_config": {"game_type": "Ai là triệu phú"},
            }

            with patch("eduplay.core.export_service.load_asset_text", side_effect=fake_load_asset_text):
                ok = svc.export_millionaire_single_file(project, str(output_file), project["questions"])

            self.assertTrue(ok)
            html = output_file.read_text(encoding="utf-8")
            self.assertIn("data:image/png;base64,", html)
            self.assertIn("data:audio/mpeg;base64,", html)
            self.assertIn("data:video/mp4;base64,", html)
            self.assertIn(".explanationBlock{", html)
            self.assertIn("background:transparent", html)
            self.assertNotIn('href="css/styles.css"', html)
            self.assertNotIn('src="js/app.js"', html)
            self.assertNotIn('src="images/Logo.png"', html)
            self.assertNotIn('src="sounds/Music/0_to_1000.mp3"', html)

    def test_export_millionaire_single_file_preserves_per_question_time_limits_and_mode(self):
        from eduplay.core.export_service import ExportService

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            millionaire_dir = root / "assets_bundle" / "millionaire"

            self._write_text(
                millionaire_dir / "index.html",
                """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="css/styles.css">
<script src="js/app.js"></script>
<script src="js/functions.js"></script>
</head>
<body>
<div id="timer" data-timer="60"></div>
</body>
</html>
""".strip(),
            )
            self._write_text(millionaire_dir / "css" / "styles.css", "body{color:#fff;}")
            self._write_text(millionaire_dir / "js" / "app.js", "window.APP = true;")
            self._write_text(millionaire_dir / "js" / "functions.js", "window.FNS = true;")

            def fake_load_asset_text(asset_path: str) -> str:
                prefix = "assets_bundle/millionaire/"
                self.assertTrue(asset_path.startswith(prefix))
                local_path = millionaire_dir / asset_path[len(prefix):]
                return local_path.read_text(encoding="utf-8")

            svc = ExportService()
            svc.assets_dir = root / "assets_bundle"
            output_file = root / "millionaire.html"
            project = {
                "id": "p1",
                "name": "Ai la trieu phu",
                "language": "vi",
                "questions": [
                    {
                        "question": "Q1",
                        "options": ["A1", "B1", "C1", "D1"],
                        "correct_answer": 1,
                        "time_limit": 45,
                    },
                    {
                        "question": "Q2",
                        "options": ["A2", "B2", "C2", "D2"],
                        "correct_answer": 2,
                        "time_limit": 20,
                    },
                ],
                "game_config": {
                    "game_type": "Ai là triệu phú",
                    "question_time": 30,
                    "export_mode": "teaching",
                },
            }

            with patch("eduplay.core.export_service.load_asset_text", side_effect=fake_load_asset_text):
                ok = svc.export_millionaire_single_file(project, str(output_file), project["questions"])

            self.assertTrue(ok)
            html = output_file.read_text(encoding="utf-8")
            self.assertIn('"export_mode": "teaching"', html)
            self.assertIn('"time_limit": 45', html)
            self.assertIn('"time_limit": 20', html)
            self.assertNotIn("default_time === 45", html)

    def test_export_millionaire_single_file_normalizes_object_options_for_quick_preview_runtime(self):
        from eduplay.core.export_service import ExportService

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            millionaire_dir = root / "assets_bundle" / "millionaire"

            self._write_text(
                millionaire_dir / "index.html",
                """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="css/styles.css">
<script src="js/app.js"></script>
<script src="js/functions.js"></script>
</head>
<body>
<div id="gameWindow"></div>
<div id="question"></div>
<span id="ans1"></span>
<span id="ans2"></span>
<span id="ans3"></span>
<span id="ans4"></span>
</body>
</html>
""".strip(),
            )
            self._write_text(millionaire_dir / "css" / "styles.css", "body{color:#fff;}")
            self._write_text(millionaire_dir / "js" / "app.js", "window.APP = true;")
            self._write_text(millionaire_dir / "js" / "functions.js", "window.FNS = true;")

            def fake_load_asset_text(asset_path: str) -> str:
                prefix = "assets_bundle/millionaire/"
                self.assertTrue(asset_path.startswith(prefix))
                local_path = millionaire_dir / asset_path[len(prefix):]
                return local_path.read_text(encoding="utf-8")

            svc = ExportService()
            svc.assets_dir = root / "assets_bundle"
            output_file = root / "millionaire.html"
            project = {
                "id": "p-obj",
                "name": "Ai la trieu phu",
                "language": "vi",
                "questions": [
                    {
                        "question": "Hanh tinh nao duoc goi la Hanh tinh do?",
                        "options": [
                            {"text": "Sao Kim", "correct": False},
                            {"text": "Sao Hoa", "correct": True},
                            {"text": "Sao Moc", "correct": False},
                            {"text": "Sao Tho", "correct": False},
                        ],
                        "time_limit": 41,
                    }
                ],
                "game_config": {"game_type": "Ai là triệu phú"},
            }

            with patch("eduplay.core.export_service.load_asset_text", side_effect=fake_load_asset_text):
                ok = svc.export_millionaire_single_file(project, str(output_file), project["questions"])

            self.assertTrue(ok)
            html = output_file.read_text(encoding="utf-8")
            game_data = self._extract_game_data(html)
            question = (game_data.get("questions") or [])[0]

            self.assertEqual(question.get("options"), ["Sao Kim", "Sao Hoa", "Sao Moc", "Sao Tho"])

    def test_export_millionaire_single_file_strips_quiz_feedback_sound_pools(self):
        from eduplay.core.export_service import ExportService

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            millionaire_dir = root / "assets_bundle" / "millionaire"

            self._write_text(
                millionaire_dir / "index.html",
                """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="js/sounds.js"></script>
</head>
<body>
<div id="gameWindow"></div>
</body>
</html>
""".strip(),
            )
            self._write_text(millionaire_dir / "js" / "sounds.js", "window.SOUNDS = true;")

            def fake_load_asset_text(asset_path: str) -> str:
                prefix = "assets_bundle/millionaire/"
                self.assertTrue(asset_path.startswith(prefix))
                local_path = millionaire_dir / asset_path[len(prefix):]
                return local_path.read_text(encoding="utf-8")

            svc = ExportService()
            svc.assets_dir = root / "assets_bundle"
            output_file = root / "millionaire.html"
            project = {
                "id": "p-feedback",
                "name": "Ai la trieu phu",
                "language": "vi",
                "questions": [
                    {
                        "question": "Q1",
                        "options": ["A1", "B1", "C1", "D1"],
                        "correct_answer": 1,
                    }
                ],
                "game_config": {
                    "game_type": "Ai là triệu phú",
                    "feedback_sound_pools": {
                        "correct": [{"src": "data:audio/wav;base64,AAAA", "text": "Correct!"}],
                        "wrong": [{"src": "data:audio/wav;base64,BBBB", "text": "Keep trying!"}],
                    },
                },
            }

            with patch("eduplay.core.export_service.load_asset_text", side_effect=fake_load_asset_text):
                ok = svc.export_millionaire_single_file(project, str(output_file), project["questions"])

            self.assertTrue(ok)
            game_data = self._extract_game_data(output_file.read_text(encoding="utf-8"))
            self.assertNotIn("feedback_sound_pools", game_data.get("game_config") or {})

    def test_millionaire_template_applies_logo_assets_even_after_dom_is_ready(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "millionaire"
            / "index.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("function applyBundledAssets()", html)
        self.assertIn("if(document.readyState==='loading')", html)
        self.assertIn("else { applyBundledAssets(); }", html)
        self.assertIn("img.logo, img.logoSm, img.loaderLogo", html)

    def test_millionaire_template_falls_back_to_default_logo_when_bundled_logo_missing(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "millionaire"
            / "index.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("var fallbackLogo = img.getAttribute('data-default') || 'images/Logo.png';", html)
        self.assertIn("if (!img.getAttribute('src'))", html)
        self.assertIn("img.setAttribute('src', fallbackLogo);", html)

    def test_millionaire_template_jquery_shim_supports_one_for_answer_click_binding(self):
        template_path = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "millionaire"
            / "index.html"
        )
        html = template_path.read_text(encoding="utf-8")

        self.assertIn("one:function(evt,fn)", html)

    def test_millionaire_template_jquery_shim_supports_document_ready_for_game_bootstrap(self):
        template_root = (
            Path(__file__).resolve().parents[1]
            / "assets_bundle"
            / "millionaire"
        )
        html = (template_root / "index.html").read_text(encoding="utf-8")
        app_js = (template_root / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("$(document).ready(function (){", app_js)
        self.assertIn("ready:function(fn)", html)


if __name__ == "__main__":
    unittest.main()
