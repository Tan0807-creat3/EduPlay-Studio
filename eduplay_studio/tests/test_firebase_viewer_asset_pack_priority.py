import os
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestFirebaseViewerAssetPackPriority(unittest.TestCase):
    def test_viewer_tries_requested_asset_pack_key_before_resolved_key(self):
        viewer_path = (
            ROOT
            / "eduplay_studio"
            / "eduplay"
            / "resources"
            / "firebase_hosting"
            / "firebase_viewer.html"
        )
        viewer_text = viewer_path.read_text(encoding="utf-8")
        match = re.search(
            r"function loadAssetPack\(db, assetPackKey, assetPackProfile\)\{(?P<body>.*?)function tryLoad\(index\)\{",
            viewer_text,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "Expected loadAssetPack function in firebase_viewer.html")
        body = match.group("body")
        requested_pos = body.find("if(requestedKey){ candidates.push(requestedKey); }")
        resolved_pos = body.find("if(resolvedKey && candidates.indexOf(resolvedKey) === -1){")
        self.assertGreaterEqual(requested_pos, 0, "Expected requestedKey candidate insertion")
        self.assertGreaterEqual(resolved_pos, 0, "Expected resolvedKey candidate insertion")
        self.assertLess(
            requested_pos,
            resolved_pos,
            "Viewer must try the explicit game asset_pack_key before manifest-resolved fallbacks",
        )


if __name__ == "__main__":
    unittest.main()
