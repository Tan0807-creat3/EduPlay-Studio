import base64
import gzip
import hashlib
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


def _decode_uploaded_base64_chunks(writes, marker):
    chunk_urls = [url for url in writes if marker in url]
    chunk_urls.sort(key=lambda url: int(url.rsplit("/", 1)[1].split(".json", 1)[0]))
    encoded = "".join(json.loads(writes[url]) for url in chunk_urls)
    try:
        return gzip.decompress(base64.b64decode(encoded)).decode("utf-8")
    except Exception:
        return base64.b64decode(encoded).decode("utf-8")


class TestPublishProgress(unittest.TestCase):
    def test_publish_to_firebase_uses_library_asset_pack_manifest_for_fishing_games(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        writes = {}
        requested_urls = []
        library_key = "ba805ea048fafe69620d391ede85e09218c128651c55464abb8462256624ff25"
        sample_asset = "data:image/png;base64,QUJDREVGRw=="
        sample_token = f"__EDUPLAY_ASSET__{hashlib.sha256(sample_asset.encode('utf-8')).hexdigest()[:24]}__"

        def _fake_get(url, *args, **kwargs):
            requested_urls.append(url)
            if url.endswith("/asset_pack_libraries/fishing.json"):
                return _FakeResponse(
                    status_code=200,
                    text=json.dumps({"key": library_key, "profile": "fishing", "library": True}),
                )
            return _FakeResponse(status_code=404, text="null")

        def _fake_put(url, data=None, headers=None):
            writes[url] = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
            return _FakeResponse()

        html = f"<html><body><img src='{sample_asset}'><h1>Fishing Game</h1></body></html>"

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "fishing.html"
            html_path.write_text(html, encoding="utf-8")

            with patch.object(ExportService, "_read_service_account_b64", return_value=""):
                with patch.object(
                    ExportService,
                    "_resolve_library_asset_pack_descriptor",
                    return_value={
                        "profile": "fishing",
                        "key": library_key,
                        "assets": {sample_token: sample_asset},
                        "manifest": {
                            "key": library_key,
                            "latest_key": library_key,
                            "versions": {
                                library_key: {
                                    "key": library_key,
                                }
                            },
                        },
                    },
                    create=True,
                ):
                    with patch("requests.get", side_effect=_fake_get):
                        with patch("requests.put", side_effect=_fake_put):
                            result = svc.publish_to_firebase(
                                str(html_path),
                                "Fishing Game",
                                "https://demo.firebaseio.com",
                                project_id="fishing-game",
                                project_data={"game_type": "fishing"},
                            )

        self.assertTrue(result.get("ok"))
        meta = json.loads(writes[result["db_link"]])
        self.assertEqual(meta.get("asset_pack_key"), library_key)
        self.assertEqual(meta.get("asset_pack_profile"), "fishing")
        self.assertEqual(meta.get("asset_pack_source"), "library")
        asset_pack_uploads = [url for url in writes if "/asset_packs/" in url]
        self.assertEqual(asset_pack_uploads, [], "library-backed publish should not upload a derived asset pack")

    def test_publish_to_firebase_falls_back_to_derived_pack_when_library_manifest_is_unavailable(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        writes = {}
        requested_urls = []
        sample_asset = "data:image/png;base64,QUJDREVGRw=="
        derived_key = hashlib.sha256(
            json.dumps(
                {
                    f"__EDUPLAY_ASSET__{hashlib.sha256(sample_asset.encode('utf-8')).hexdigest()[:24]}__": sample_asset
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        sample_token = f"__EDUPLAY_ASSET__{hashlib.sha256(sample_asset.encode('utf-8')).hexdigest()[:24]}__"

        def _fake_get(url, *args, **kwargs):
            requested_urls.append(url)
            return _FakeResponse(status_code=404, text="null")

        def _fake_put(url, data=None, headers=None):
            writes[url] = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
            return _FakeResponse()

        html = f"<html><body><img src='{sample_asset}'><h1>Fishing Missing Manifest</h1></body></html>"

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "fishing-missing-manifest.html"
            html_path.write_text(html, encoding="utf-8")

            with patch.object(ExportService, "_read_service_account_b64", return_value=""):
                with patch.object(
                    ExportService,
                    "_resolve_library_asset_pack_descriptor",
                    return_value={
                        "profile": "fishing",
                        "key": derived_key,
                        "local_key": derived_key,
                        "assets": {sample_token: sample_asset},
                        "manifest": {},
                    },
                    create=True,
                ):
                    with patch("requests.get", side_effect=_fake_get):
                        with patch("requests.put", side_effect=_fake_put):
                            result = svc.publish_to_firebase(
                                str(html_path),
                                "Fishing Missing Manifest",
                                "https://demo.firebaseio.com",
                                project_id="fishing-missing-manifest",
                                project_data={"game_type": "fishing"},
                            )

        self.assertTrue(result.get("ok"))
        meta = json.loads(writes[result["db_link"]])
        self.assertEqual(meta.get("asset_pack_key"), derived_key)
        self.assertEqual(meta.get("asset_pack_source"), "derived")
        asset_pack_uploads = [url for url in writes if "/asset_packs/" in url and "/chunks/" not in url]
        self.assertTrue(asset_pack_uploads, "missing library manifest should trigger a derived asset-pack upload")
        lightweight_html = _decode_uploaded_base64_chunks(writes, "/content_chunks/")
        self.assertNotIn(sample_asset, lightweight_html)
        self.assertIn(sample_token, lightweight_html)
        self.assertFalse(
            any("/asset_pack_libraries/" in url for url in requested_urls),
            "publish should not treat an unconfirmed library descriptor as a remote library manifest",
        )

    def test_publish_to_firebase_uploads_asset_pack_once_and_reuses_it(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        writes = {}
        existing_asset_packs = set()
        asset_put_calls = []
        sample_asset = "data:image/png;base64,QUJDREVGRw=="

        def _fake_get(url, *args, **kwargs):
            class _Resp:
                def __init__(self, status_code, payload):
                    self.status_code = status_code
                    self.text = json.dumps(payload)

                def json(self):
                    return json.loads(self.text)

            payload = None
            if "/asset_packs/" in url:
                asset_key = url.split("/asset_packs/", 1)[1].split(".json", 1)[0]
                if asset_key in existing_asset_packs:
                    payload = {"exists": True}
                    return _Resp(200, payload)
            payload = None
            return _Resp(404, payload)

        def _fake_put(url, data=None, headers=None):
            writes[url] = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
            if "/asset_packs/" in url and "/chunks/" not in url:
                asset_key = url.split("/asset_packs/", 1)[1].split(".json", 1)[0]
                existing_asset_packs.add(asset_key)
                asset_put_calls.append(url)
            return _FakeResponse()

        html_1 = f"<html><body><img src='{sample_asset}'><h1>Game A</h1></body></html>"
        html_2 = f"<html><body><img src='{sample_asset}'><h1>Game B</h1></body></html>"

        with tempfile.TemporaryDirectory() as tmp:
            path_1 = Path(tmp) / "game-a.html"
            path_2 = Path(tmp) / "game-b.html"
            path_1.write_text(html_1, encoding="utf-8")
            path_2.write_text(html_2, encoding="utf-8")

            with patch.object(ExportService, "_read_service_account_b64", return_value=""):
                with patch("requests.get", side_effect=_fake_get):
                    with patch("requests.put", side_effect=_fake_put):
                        result_1 = svc.publish_to_firebase(
                            str(path_1),
                            "Game A",
                            "https://demo.firebaseio.com",
                            project_id="game-a",
                        )
                        result_2 = svc.publish_to_firebase(
                            str(path_2),
                            "Game B",
                            "https://demo.firebaseio.com",
                            project_id="game-b",
                        )

        self.assertTrue(result_1.get("ok"))
        self.assertTrue(result_2.get("ok"))
        self.assertEqual(len(asset_put_calls), 1, "asset pack should be uploaded only once")

        game_meta_1 = json.loads(writes[result_1["db_link"]])
        game_meta_2 = json.loads(writes[result_2["db_link"]])
        self.assertTrue(game_meta_1.get("asset_pack_key"))
        self.assertEqual(game_meta_1.get("asset_pack_key"), game_meta_2.get("asset_pack_key"))
        self.assertEqual(game_meta_1.get("type"), "single_file_html_rtdb")

    def test_publish_to_firebase_avoids_stale_library_manifest_for_new_assets(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        writes = {}
        stale_library_key = "stale-fishing-library-key"
        sample_asset = "data:image/png;base64,QUJDREVGRw=="
        sample_token = f"__EDUPLAY_ASSET__{hashlib.sha256(sample_asset.encode('utf-8')).hexdigest()[:24]}__"

        def _fake_get(url, *args, **kwargs):
            return _FakeResponse(status_code=404, text="null")

        def _fake_put(url, data=None, headers=None):
            writes[url] = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
            return _FakeResponse()

        html = f"<html><body><img src='{sample_asset}'><h1>Fishing New Assets</h1></body></html>"

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "fishing-new.html"
            html_path.write_text(html, encoding="utf-8")

            with patch.object(ExportService, "_read_service_account_b64", return_value=""):
                with patch.object(
                    ExportService,
                    "_resolve_library_asset_pack_descriptor",
                    return_value={
                        "profile": "fishing",
                        "key": stale_library_key,
                        "local_key": "fresh-fishing-local-key",
                        "assets": {sample_token: sample_asset},
                    },
                    create=True,
                ):
                    with patch("requests.get", side_effect=_fake_get):
                        with patch("requests.put", side_effect=_fake_put):
                            result = svc.publish_to_firebase(
                                str(html_path),
                                "Fishing New Assets",
                                "https://demo.firebaseio.com",
                                project_id="fishing-new-assets",
                                project_data={"game_type": "fishing"},
                            )

        self.assertTrue(result.get("ok"))
        meta = json.loads(writes[result["db_link"]])
        self.assertNotEqual(meta.get("asset_pack_key"), stale_library_key)
        self.assertEqual(meta.get("asset_pack_source"), "derived")
        asset_pack_uploads = [url for url in writes if "/asset_packs/" in url and "/chunks/" not in url]
        self.assertTrue(asset_pack_uploads, "new assets should trigger a derived asset-pack upload")

    def test_publish_to_firebase_stores_lightweight_html_and_asset_reference(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        writes = {}
        sample_asset = "data:image/png;base64,QUJDREVGRw=="

        def _fake_get(url, *args, **kwargs):
            return _FakeResponse(status_code=404, text="null")

        def _fake_put(url, data=None, headers=None):
            writes[url] = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
            return _FakeResponse()

        html = (
            "<html><body>"
            f"<img src=\"{sample_asset}\">"
            "<audio src=\"data:audio/wav;base64,QUJD\"></audio>"
            "<h1>Lightweight Payload</h1>"
            "</body></html>"
        )

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "game.html"
            html_path.write_text(html, encoding="utf-8")

            with patch.object(ExportService, "_read_service_account_b64", return_value=""):
                with patch("requests.get", side_effect=_fake_get):
                    with patch("requests.put", side_effect=_fake_put):
                        result = svc.publish_to_firebase(
                            str(html_path),
                            "Lightweight Game",
                            "https://demo.firebaseio.com",
                            project_id="lightweight-game",
                        )

        self.assertTrue(result.get("ok"))
        meta_url = result["db_link"]
        meta = json.loads(writes[meta_url])
        self.assertIn("asset_pack_key", meta)
        self.assertNotIn("file_url", meta)
        self.assertNotIn("chunks", meta)

        content_chunk_urls = [url for url in writes if "/content_chunks/" in url]
        self.assertTrue(content_chunk_urls, "expected stripped html to be uploaded as content chunks")
        lightweight_html = _decode_uploaded_base64_chunks(writes, "/content_chunks/")
        self.assertNotIn(sample_asset, lightweight_html)
        self.assertIn("__EDUPLAY_ASSET__", lightweight_html)

    def test_publish_to_firebase_retries_admin_upload_with_fallback_bucket(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        store = {}
        service_account_b64 = base64.b64encode(
            json.dumps({"project_id": "eduplay-game"}).encode("utf-8")
        ).decode("ascii")

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

            def _value(self):
                node = self.root
                for part in self.path:
                    if not isinstance(node, dict) or part not in node:
                        return None
                    node = node.get(part)
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
                return self._value()

            def child(self, name):
                base = "/".join(self.path)
                next_path = f"{base}/{name}" if base else str(name)
                return _FakeRef(self.root, next_path)

        fake_firebase_admin = types.ModuleType("firebase_admin")
        fake_firebase_admin._apps = []
        fake_firebase_admin.initialize_app = lambda cred, options=None: fake_firebase_admin._apps.append((cred, options))
        fake_firebase_admin.credentials = types.SimpleNamespace(Certificate=lambda payload: {"cert": payload})
        fake_firebase_admin.db = types.SimpleNamespace(reference=lambda path: _FakeRef(store, path))

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "game.html"
            html_path.write_text(
                "<html><body><img src='data:image/png;base64,QUJDREVGRw=='>Hello RTDB Admin</body></html>",
                encoding="utf-8",
            )

            with patch.object(ExportService, "_read_service_account_b64", return_value=service_account_b64):
                with patch.dict(sys.modules, {"firebase_admin": fake_firebase_admin}):
                    with patch("requests.put", side_effect=AssertionError("REST fallback should not run")):
                        result = svc.publish_to_firebase(
                            str(html_path),
                            "Admin RTDB Game",
                            "https://demo.firebaseio.com",
                            project_id="admin-rtdb-game",
                        )

        self.assertTrue(result.get("ok"))
        game_meta = store["games"]["admin-rtdb-game"]
        self.assertEqual(game_meta.get("type"), "single_file_html_rtdb")
        self.assertTrue(game_meta.get("asset_pack_key"))
        self.assertIn("content_chunks", game_meta)
        self.assertIn(game_meta.get("asset_pack_key"), store.get("asset_packs", {}))
        self.assertEqual(result.get("file_url"), "")

    def test_publish_to_firebase_stops_after_admin_error_when_service_account_is_available(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        service_account_b64 = base64.b64encode(
            json.dumps({"project_id": "eduplay-game"}).encode("utf-8")
        ).decode("ascii")

        class _BrokenRef:
            def get(self):
                raise RuntimeError("admin db unavailable")

            def set(self, value):
                raise RuntimeError("admin db unavailable")

            def child(self, name):
                return self

        fake_firebase_admin = types.ModuleType("firebase_admin")
        fake_firebase_admin._apps = []
        fake_firebase_admin.initialize_app = lambda cred, options=None: fake_firebase_admin._apps.append((cred, options))
        fake_firebase_admin.credentials = types.SimpleNamespace(Certificate=lambda payload: {"cert": payload})
        fake_firebase_admin.db = types.SimpleNamespace(reference=lambda path: _BrokenRef())

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "game.html"
            html_path.write_text("<html><body>Hello Admin Error</body></html>", encoding="utf-8")

            with patch.object(ExportService, "_read_service_account_b64", return_value=service_account_b64):
                with patch.dict(sys.modules, {"firebase_admin": fake_firebase_admin}):
                    with patch("requests.put", side_effect=AssertionError("REST fallback should not run")):
                        result = svc.publish_to_firebase(
                            str(html_path),
                            "Storage Game",
                            "https://demo.firebaseio.com",
                            project_id="storage-game",
                        )

        self.assertFalse(result.get("ok"))
        self.assertIn("Admin SDK error:", result.get("error") or "")
        self.assertIn("admin db unavailable", result.get("error") or "")

    def test_publish_to_firebase_prefers_storage_file_and_metadata_when_admin_sdk_is_available(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
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
                parent = self._parent(create=True)
                if not self.path:
                    self.root.clear()
                    if isinstance(value, dict):
                        self.root.update(value)
                    return
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

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "game.html"
            html_path.write_text(
                "<html><body><img src='data:image/png;base64,QUJDREVGRw=='>Hello Admin RTDB</body></html>",
                encoding="utf-8",
            )

            with patch.object(ExportService, "_read_service_account_b64", return_value="e30="):
                with patch.dict(sys.modules, {"firebase_admin": fake_firebase_admin}):
                    result = svc.publish_to_firebase(
                        str(html_path),
                        "Storage Game",
                        "https://demo.firebaseio.com",
                        project_id="storage-game",
                    )

        self.assertTrue(result.get("ok"))
        stored_meta = store["games"]["storage-game"]
        self.assertNotIn("chunks", stored_meta)
        self.assertIn("content_chunks", stored_meta)
        self.assertEqual(stored_meta.get("type"), "single_file_html_rtdb")
        self.assertEqual(stored_meta.get("encoding"), "gzip+base64")
        self.assertEqual(result.get("file_url"), "")
        content_html = _decode_uploaded_base64_chunks(
            {
                f"https://demo.firebaseio.com/games/storage-game/content_chunks/{idx}.json": json.dumps(chunk)
                for idx, chunk in (stored_meta.get("content_chunks") or {}).items()
            },
            "/content_chunks/",
        )
        self.assertIn("__EDUPLAY_ASSET__", content_html)

    def test_publish_to_firebase_reports_structured_progress_from_compress_to_link(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        events = []
        uploaded_meta = {}

        def _fake_get(url, *args, **kwargs):
            return _FakeResponse(status_code=404, text="null")

        def _fake_put(url, data=None, headers=None):
            if url.endswith(".json") and "/content_chunks/" not in url and "/asset_packs/" not in url:
                uploaded_meta.update(json.loads(data.decode("utf-8")))
            return _FakeResponse()

        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "game.html"
            html_path.write_text("<html><body>Hello EduPlay</body></html>", encoding="utf-8")

            with patch.object(ExportService, "_read_service_account_b64", return_value=""):
                with patch("requests.get", side_effect=_fake_get):
                    with patch("requests.put", side_effect=_fake_put):
                        result = svc.publish_to_firebase(
                            str(html_path),
                            "Demo Game",
                            "https://demo.firebaseio.com",
                            project_id="demo-game",
                            progress_callback=lambda payload: events.append(payload),
                        )

        self.assertTrue(result.get("ok"))
        self.assertEqual(uploaded_meta.get("encoding"), "gzip+base64")
        self.assertGreaterEqual(len(events), 4, "expected progress events for compressing, uploading, finalizing, completed")
        self.assertEqual(events[0].get("stage"), "compressing")
        self.assertTrue(any(evt.get("stage") == "uploading" for evt in events))
        self.assertTrue(any(evt.get("stage") == "finalizing" for evt in events))
        self.assertEqual(events[-1].get("stage"), "completed")
        self.assertEqual(events[-1].get("play_link"), result.get("play_link"))


if __name__ == "__main__":
    unittest.main()
