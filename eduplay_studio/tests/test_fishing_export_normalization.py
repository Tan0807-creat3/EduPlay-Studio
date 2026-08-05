import os
import sys
import json
import re
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestFishingExportNormalization(unittest.TestCase):
    def _extract_game_data(self, html: str) -> dict:
        m = re.search(r'<script id="game-data" type="application/json">(.+?)</script>', html, re.DOTALL)
        self.assertIsNotNone(m, "missing game-data script tag")
        payload = m.group(1)
        return json.loads(payload)

    def test_export_fishing_preserves_5_question_types_and_string_options(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()

        project_data = {
            "id": "p1",
            "name": "Fishing",
            "language": "vi",
            "questions": [
                {
                    "question": "Q1",
                    "type": "multiple_choice",
                    "options": [
                        {"text": "A", "correct": True},
                        {"text": "B", "correct": False},
                    ],
                },
                {"question": "Q2", "type": "true_false", "correct_answer": True},
                {"question": "Q3", "type": "fill_blank", "answers": ["x", "y"], "case_sensitive": False},
                {"question": "Q4", "type": "matching", "pairs": [{"left": "a", "right": "1"}]},
                {"question": "Q5", "type": "short_answer", "answers": ["abc"], "max_length": 100},
            ],
            "game_config": {
                "randomize_questions": False,
                "fish_count": 10,
                "fish_objects": [
                    {
                        "sprite_base64": "data:image/png;base64,AAAA",
                        "wrong_sprite_base64": "data:image/png;base64,BBBB",
                    }
                ],
                "tiny_fish_base64": ["data:image/png;base64,CCCC"],
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            ok = svc._export_fishing_single_file(project_data, out)
            self.assertTrue(ok)
            html = out.read_text(encoding="utf-8")
            game_data = self._extract_game_data(html)
            qs = game_data.get("questions") or []

            self.assertGreaterEqual(len(qs), 5)
            types = {q.get("type") for q in qs}
            self.assertTrue(
                {"multiple_choice", "true_false", "fill_blank", "matching", "short_answer"}.issubset(types)
            )

            mcq = next(q for q in qs if q.get("type") == "multiple_choice")
            self.assertEqual(mcq.get("options"), ["A", "B"])
            self.assertIn(mcq.get("correctAnswer", mcq.get("correct_answer")), [0, "0"])

    def test_export_fishing_single_file_preserves_export_mode_for_runtime(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()

        project_data = {
            "id": "p1",
            "name": "Fishing Teaching",
            "language": "vi",
            "questions": [
                {
                    "question": "Q1",
                    "type": "multiple_choice",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0,
                }
            ],
            "game_config": {
                "question_time": 25,
                "export_mode": "teaching",
                "fish_objects": [
                    {
                        "sprite_base64": "data:image/png;base64,AAAA",
                        "wrong_sprite_base64": "data:image/png;base64,BBBB",
                    }
                ],
                "tiny_fish_base64": ["data:image/png;base64,CCCC"],
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            ok = svc._export_fishing_single_file(project_data, out)
            self.assertTrue(ok)
            html = out.read_text(encoding="utf-8")
            game_data = self._extract_game_data(html)

            self.assertEqual(
                ((game_data.get("game_config") or {}).get("export_mode")),
                "teaching",
            )

    def test_export_fishing_single_file_does_not_embed_quiz_feedback_sound_pools(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()

        project_data = {
            "id": "p-feedback",
            "name": "Fishing No Quiz Feedback Pool",
            "language": "vi",
            "questions": [
                {
                    "question": "Q1",
                    "type": "multiple_choice",
                    "options": ["A", "B"],
                    "correct_answer": 0,
                }
            ],
            "game_config": {
                "feedback_sound_pools": {
                    "correct": [{"src": "data:audio/wav;base64,AAAA", "text": "Correct!"}],
                    "wrong": [{"src": "data:audio/wav;base64,BBBB", "text": "Keep trying!"}],
                }
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            ok = svc._export_fishing_single_file(project_data, out)
            self.assertTrue(ok)
            html = out.read_text(encoding="utf-8")
            game_data = self._extract_game_data(html)

            self.assertNotIn("feedback_sound_pools", game_data.get("game_config") or {})
            self.assertIn("initFeedbackSoundPools(cfg.feedback_sound_pools || {});", html)

    def test_export_fishing_single_file_preserves_question_image_for_quick_preview(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()

        project_data = {
            "id": "p-img",
            "name": "Fishing Image",
            "language": "vi",
            "questions": [
                {
                    "question": "Con ca nay mau gi?",
                    "type": "multiple_choice",
                    "options": ["Xanh", "Do"],
                    "correct_answer": 0,
                    "image_base64": "data:image/png;base64,AAAA",
                }
            ],
            "game_config": {
                "randomize_questions": False,
                "fish_objects": [
                    {
                        "sprite_base64": "data:image/png;base64,AAAA",
                        "wrong_sprite_base64": "data:image/png;base64,BBBB",
                    }
                ],
                "tiny_fish_base64": ["data:image/png;base64,CCCC"],
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            ok = svc._export_fishing_single_file(project_data, out)
            self.assertTrue(ok)
            html = out.read_text(encoding="utf-8")
            game_data = self._extract_game_data(html)
            question = (game_data.get("questions") or [])[0]

            self.assertEqual(question.get("image_base64"), "data:image/png;base64,AAAA")
            self.assertIn('id="question-image"', html)
            self.assertIn('id="question-image-container"', html)

    def test_export_fishing_single_file_bundles_scene_assets_used_by_background_hud(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()

        project_data = {
            "id": "p-scene",
            "name": "Fishing Scene Assets",
            "language": "vi",
            "questions": [
                {
                    "question": "Q1",
                    "type": "multiple_choice",
                    "options": ["A", "B"],
                    "correct_answer": 0,
                }
            ],
            "game_config": {},
        }

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            ok = svc._export_fishing_single_file(project_data, out)
            self.assertTrue(ok)
            html = out.read_text(encoding="utf-8")
            game_data = self._extract_game_data(html)
            scene_map = ((game_data.get("game_config") or {}).get("scene_asset_map_base64")) or {}

            for asset_name in (
                "terrain_dirt_a.png",
                "terrain_dirt_d.png",
                "fish_orange.png",
                "fish_brown.png",
                "fish_grey_long_a.png",
                "fish_red_skeleton.png",
            ):
                self.assertIn(asset_name, scene_map)
                self.assertTrue(str(scene_map[asset_name]).startswith("data:image/"))

    def test_export_fishing_single_file_runtime_prefers_bundled_scene_assets(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()

        project_data = {
            "id": "p-scene-runtime",
            "name": "Fishing Scene Runtime",
            "language": "vi",
            "questions": [
                {
                    "question": "Q1",
                    "type": "multiple_choice",
                    "options": ["A", "B"],
                    "correct_answer": 0,
                }
            ],
            "game_config": {},
        }

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            ok = svc._export_fishing_single_file(project_data, out)
            self.assertTrue(ok)
            html = out.read_text(encoding="utf-8")

            self.assertIn("let sceneAssetMap = {};", html)
            self.assertIn("sceneAssetMap = cfg.scene_asset_map_base64 || {};", html)
            self.assertIn("function setSceneImage(img, assetName, explicitPath = '') {", html)
            self.assertIn("setSceneImage(sImg, sName);", html)
            self.assertIn("setSceneImage(img, item.src);", html)

    def test_export_fishing_single_file_runtime_preserves_matching_question_fields(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()

        project_data = {
            "id": "p-matching-runtime",
            "name": "Fishing Matching Runtime",
            "language": "vi",
            "questions": [
                {
                    "question": "Ghép nối",
                    "type": "matching",
                    "pairs": [{"left": "Biện pháp A", "right": "Mục tiêu 1"}],
                }
            ],
            "game_config": {},
        }

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.html"
            ok = svc._export_fishing_single_file(project_data, out)
            self.assertTrue(ok)
            html = out.read_text(encoding="utf-8")

            self.assertIn("const normalizedType = normalizeFishingQuestionType(src);", html)
            self.assertIn("type: normalizedType,", html)
            self.assertIn("match_pairs: src.match_pairs || src.pairs || src.matchPairs || []", html)
            self.assertIn("questionPanel.classList.toggle('matching-mode', currentQuestionType === 'matching')", html)
            self.assertIn("buildMatchingBoard(pairs);", html)
            self.assertIn("board.className = 'matching-board';", html)
            self.assertIn("svg.classList.add('match-link-layer');", html)
            self.assertIn("btn.className = 'match-card match-card-left';", html)
            self.assertIn("btn.className = 'match-card match-card-right';", html)
            self.assertIn("function drawMatchingLinks()", html)
            self.assertNotIn("sel.className = 'match-select';", html)


if __name__ == "__main__":
    unittest.main()
