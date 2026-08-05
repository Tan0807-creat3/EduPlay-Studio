import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _FakeResponse:
    def __init__(self, status_code=200, text="{}"):
        self.status_code = status_code
        self.text = text


class TestUploadLibraryAssetPacks(unittest.TestCase):
    def test_build_library_asset_packs_marks_library_and_never_delete(self):
        from upload_library_asset_packs import build_library_asset_packs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            classic_audio = root / "classic_click.wav"
            fishing_sprite = root / "fish_blue.png"
            millionaire_logo = root / "logo.png"
            classic_audio.write_bytes(b"RIFFdemo")
            fishing_sprite.write_bytes(b"\x89PNGdemo")
            millionaire_logo.write_bytes(b"\x89PNGmillionaire")

            packs = build_library_asset_packs(
                assets_root=root,
                profiles={
                    "classic": [classic_audio],
                    "fishing": [fishing_sprite],
                    "millionaire": [millionaire_logo],
                },
            )

        self.assertEqual(set(packs.keys()), {"classic", "fishing", "millionaire"})
        self.assertTrue(packs["classic"]["key"])
        self.assertEqual(packs["fishing"]["meta"].get("profile"), "fishing")
        self.assertTrue(packs["millionaire"]["meta"].get("library"))
        self.assertTrue(packs["millionaire"]["meta"].get("never_delete"))
        self.assertGreaterEqual(packs["classic"]["meta"].get("asset_count") or 0, 1)
        self.assertGreaterEqual(packs["classic"]["meta"].get("total_chunks") or 0, 1)

    def test_upload_library_asset_packs_writes_manifest_and_skips_existing_pack(self):
        from upload_library_asset_packs import build_library_asset_packs, upload_library_asset_packs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            classic_audio = root / "classic_click.wav"
            fishing_sprite = root / "fish_blue.png"
            millionaire_logo = root / "logo.png"
            classic_audio.write_bytes(b"RIFFdemo")
            fishing_sprite.write_bytes(b"\x89PNGdemo")
            millionaire_logo.write_bytes(b"\x89PNGmillionaire")

            packs = build_library_asset_packs(
                assets_root=root,
                profiles={
                    "classic": [classic_audio],
                    "fishing": [fishing_sprite],
                    "millionaire": [millionaire_logo],
                },
            )

        writes = {}
        existing_key = packs["classic"]["key"]

        class _Requests:
            @staticmethod
            def get(url):
                if f"/asset_packs/{existing_key}.json" in url:
                    return _FakeResponse(200, json.dumps({"exists": True}))
                return _FakeResponse(404, "null")

            @staticmethod
            def put(url, data=None, headers=None):
                writes[url] = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
                return _FakeResponse(200, "{}")

        manifest = upload_library_asset_packs(
            "https://demo.firebaseio.com",
            packs,
            requests_module=_Requests,
        )

        self.assertEqual(set(manifest.keys()), {"classic", "fishing", "millionaire"})
        self.assertEqual(manifest["classic"]["key"], existing_key)
        self.assertIn(
            "https://demo.firebaseio.com/asset_pack_libraries/classic.json",
            writes,
        )
        self.assertNotIn(
            f"https://demo.firebaseio.com/asset_packs/{existing_key}.json",
            writes,
        )
        classic_manifest = json.loads(writes["https://demo.firebaseio.com/asset_pack_libraries/classic.json"])
        self.assertEqual(classic_manifest.get("key"), existing_key)
        self.assertIn(existing_key, classic_manifest.get("versions", {}))
        self.assertTrue(classic_manifest.get("known_keys", {}).get(existing_key))
        self.assertEqual(
            classic_manifest.get("versions", {}).get(existing_key, {}).get("storage_key"),
            existing_key,
        )
        fishing_meta_url = f"https://demo.firebaseio.com/asset_packs/{packs['fishing']['key']}.json"
        self.assertIn(fishing_meta_url, writes)

    def test_upload_library_asset_packs_preserves_legacy_library_keys_in_manifest_versions(self):
        from upload_library_asset_packs import build_library_asset_packs, upload_library_asset_packs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            classic_audio = root / "classic_click.wav"
            classic_audio.write_bytes(b"RIFFnew-demo")
            packs = build_library_asset_packs(
                assets_root=root,
                profiles={"classic": [classic_audio]},
            )

        new_key = packs["classic"]["key"]
        legacy_key = "legacy-classic-pack-key"
        writes = {}

        class _Requests:
            @staticmethod
            def get(url):
                if url.endswith(f"/asset_packs/{new_key}.json"):
                    return _FakeResponse(404, "null")
                if url.endswith("/asset_pack_libraries/classic.json"):
                    return _FakeResponse(
                        200,
                        json.dumps(
                            {
                                "key": legacy_key,
                                "profile": "classic",
                                "library": True,
                                "updated_at": 111,
                            }
                        ),
                    )
                return _FakeResponse(404, "null")

            @staticmethod
            def put(url, data=None, headers=None):
                writes[url] = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
                return _FakeResponse(200, "{}")

        manifest = upload_library_asset_packs(
            "https://demo.firebaseio.com",
            packs,
            requests_module=_Requests,
        )

        self.assertEqual(manifest["classic"]["key"], new_key)
        stored_manifest = json.loads(writes["https://demo.firebaseio.com/asset_pack_libraries/classic.json"])
        self.assertEqual(stored_manifest.get("key"), new_key)
        self.assertIn(legacy_key, stored_manifest.get("versions", {}))
        self.assertIn(new_key, stored_manifest.get("versions", {}))
        self.assertTrue(stored_manifest.get("known_keys", {}).get(legacy_key))
        self.assertTrue(stored_manifest.get("known_keys", {}).get(new_key))
        self.assertEqual(stored_manifest.get("versions", {}).get(new_key, {}).get("storage_key"), new_key)

    def test_upload_library_asset_packs_prefers_admin_sdk_when_service_account_exists(self):
        from upload_library_asset_packs import build_library_asset_packs, upload_library_asset_packs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            classic_audio = root / "classic_click.wav"
            fishing_sprite = root / "fish_blue.png"
            millionaire_logo = root / "logo.png"
            classic_audio.write_bytes(b"RIFFdemo")
            fishing_sprite.write_bytes(b"\x89PNGdemo")
            millionaire_logo.write_bytes(b"\x89PNGmillionaire")

            packs = build_library_asset_packs(
                assets_root=root,
                profiles={
                    "classic": [classic_audio],
                    "fishing": [fishing_sprite],
                    "millionaire": [millionaire_logo],
                },
            )

        store = {}

        class _FakeRef:
            def __init__(self, root, path=""):
                self.root = root
                self.path = [p for p in str(path or "").strip("/").split("/") if p]

            def _parent(self, create=False):
                node = self.root
                for part in self.path[:-1]:
                    if create and part not in node:
                        node[part] = {}
                    node = node.setdefault(part, {}) if create else node.get(part, {})
                return node

            def set(self, value):
                if not self.path:
                    self.root.clear()
                    if isinstance(value, dict):
                        self.root.update(value)
                    return
                parent = self._parent(create=True)
                parent[self.path[-1]] = value

            def get(self):
                node = self.root
                for part in self.path:
                    if not isinstance(node, dict) or part not in node:
                        return None
                    node = node.get(part)
                return node

            def child(self, name):
                base = "/".join(self.path)
                next_path = f"{base}/{name}" if base else str(name)
                return _FakeRef(self.root, next_path)

        fake_firebase_admin = types.ModuleType("firebase_admin")
        fake_firebase_admin._apps = []
        fake_firebase_admin.initialize_app = lambda cred, options=None: fake_firebase_admin._apps.append((cred, options))
        fake_firebase_admin.credentials = types.SimpleNamespace(Certificate=lambda payload: {"cert": payload})
        fake_firebase_admin.db = types.SimpleNamespace(reference=lambda path: _FakeRef(store, path))

        class _Requests:
            @staticmethod
            def get(url):
                raise AssertionError("REST should not run when admin sdk is available")

            @staticmethod
            def put(url, data=None, headers=None):
                raise AssertionError("REST should not run when admin sdk is available")

        service_account_b64 = "e30="
        with patch.dict(sys.modules, {"firebase_admin": fake_firebase_admin}):
            manifest = upload_library_asset_packs(
                "https://demo.firebaseio.com",
                packs,
                requests_module=_Requests,
                service_account_b64=service_account_b64,
            )

        self.assertEqual(set(manifest.keys()), {"classic", "fishing", "millionaire"})
        self.assertIn("asset_packs", store)
        self.assertIn("asset_pack_libraries", store)
        self.assertEqual(store["asset_pack_libraries"]["classic"]["key"], packs["classic"]["key"])
        self.assertIn(packs["classic"]["key"], store["asset_pack_libraries"]["classic"]["versions"])


if __name__ == "__main__":
    unittest.main()
