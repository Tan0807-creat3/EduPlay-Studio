import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestPreviewPlaceholder(unittest.TestCase):
    def test_build_preview_placeholder_html_contains_placeholder_root(self):
        from eduplay.core.preview_utils import build_preview_placeholder_html
        from eduplay.core.i18n import I18n

        for lang in ["vi", "en", "fr", "es", "de"]:
            html = build_preview_placeholder_html(lang=lang, title="T")
            self.assertIn('id="eduplay-preview-placeholder"', html)
            heading = I18n.t("preview.placeholder_heading", lang)
            self.assertNotEqual(heading, "preview.placeholder_heading")
            self.assertIn(heading, html)

    def test_ensure_preview_placeholder_file_creates_file(self):
        from eduplay.core.preview_utils import ensure_preview_placeholder_file

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "preview.html"
            self.assertFalse(p.exists())
            ensure_preview_placeholder_file(p, title="X", lang="vi")
            self.assertTrue(p.exists())
            s = p.read_text(encoding="utf-8")
            self.assertIn('id="eduplay-preview-placeholder"', s)


if __name__ == "__main__":
    unittest.main()
