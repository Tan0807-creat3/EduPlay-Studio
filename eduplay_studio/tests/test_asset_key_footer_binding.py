import secrets
import struct
import tempfile
import unittest
from pathlib import Path
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from eduplay.core.asset_loader import EXE_KEY_MARKER, _build_binding_digest


class TestAssetKeyFooterBinding(unittest.TestCase):
    def test_binding_digest_ignores_embedded_key_footer(self):
        with tempfile.TemporaryDirectory() as td:
            exe = Path(td) / "EduPlayStudio.exe"
            exe.write_bytes(b"EXE" + secrets.token_bytes(1024))
            before = _build_binding_digest(exe)
            key_blob = b"X" * 80
            with open(exe, "ab") as f:
                f.write(key_blob + EXE_KEY_MARKER + struct.pack(">I", len(key_blob)))
            after = _build_binding_digest(exe)
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
