import os
import secrets
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "eduplay_studio") not in sys.path:
    sys.path.insert(0, str(ROOT / "eduplay_studio"))

from tools import obfuscate_assets
from eduplay.core import asset_loader


class TestAssetHardeningRuntime(unittest.TestCase):
    def test_obfuscation_targets_include_protected_resource_dirs(self):
        self.assertIn(os.path.join("eduplay", "resources", "styles"), obfuscate_assets.TARGET_SUBDIRS)
        self.assertIn(os.path.join("eduplay", "resources", "i18n"), obfuscate_assets.TARGET_SUBDIRS)
        self.assertIn(os.path.join("eduplay", "resources", "fonts"), obfuscate_assets.TARGET_SUBDIRS)
        self.assertIn(os.path.join("eduplay", "resources", "vsto_addin"), obfuscate_assets.TARGET_SUBDIRS)

    def test_should_encrypt_qss_json_and_vsto_payloads(self):
        self.assertTrue(
            obfuscate_assets.should_encrypt(os.path.join("eduplay", "resources", "styles", "dark_theme.qss"))
        )
        self.assertTrue(
            obfuscate_assets.should_encrypt(os.path.join("eduplay", "resources", "i18n", "vi.json"))
        )
        self.assertTrue(
            obfuscate_assets.should_encrypt(os.path.join("eduplay", "resources", "fonts", "FC-Ethnocentric-Rg.otf"))
        )
        self.assertTrue(
            obfuscate_assets.should_encrypt(
                os.path.join("eduplay", "resources", "vsto_addin", "EduPlayPowerPointAddin.msi")
            )
        )

    def test_materialize_asset_file_decrypts_to_cache(self):
        key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(asset_loader.NONCE_SIZE)
        plaintext = b"secret-payload"
        encrypted = (
            asset_loader.MAGIC
            + struct.pack(">BI", asset_loader.VERSION, len(plaintext))
            + nonce
            + AESGCM(key).encrypt(nonce, plaintext, None)
        )

        with tempfile.TemporaryDirectory() as td:
            runtime_root = Path(td) / "_internal"
            runtime_root.mkdir(parents=True)
            source = runtime_root / "eduplay" / "resources" / "vsto_addin" / "EduPlayPowerPointAddin.msi"
            source.parent.mkdir(parents=True)
            source.write_bytes(encrypted)
            cache_dir = Path(td) / "cache"
            with mock.patch.object(asset_loader, "_get_runtime_root", return_value=runtime_root):
                with mock.patch.object(asset_loader, "_get_runtime_cache_dir", return_value=cache_dir):
                    with mock.patch.object(asset_loader, "load_key", return_value=key):
                        materialized = asset_loader.materialize_asset_file(
                            "eduplay/resources/vsto_addin/EduPlayPowerPointAddin.msi"
                        )
            self.assertTrue(materialized.exists())
            self.assertEqual(materialized.read_bytes(), plaintext)


if __name__ == "__main__":
    unittest.main()
