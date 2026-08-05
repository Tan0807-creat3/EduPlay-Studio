import struct
import tempfile
import unittest
from pathlib import Path

from eduplay.core.asset_loader import EXE_KEY_MARKER, KEY_MAGIC, SALT_SIZE, VERSION, _read_key_blob_from_exe


class TestAssetKeyEmbedding(unittest.TestCase):
    def test_read_key_blob_from_exe_tail(self):
        blob = KEY_MAGIC + bytes([VERSION]) + (b"\x11" * SALT_SIZE) + b"wrapped-seed"
        with tempfile.TemporaryDirectory() as td:
            exe_path = Path(td) / "EduPlayStudio.exe"
            exe_path.write_bytes(b"EXE" + blob + EXE_KEY_MARKER + struct.pack(">I", len(blob)))
            self.assertEqual(_read_key_blob_from_exe(exe_path), blob)

