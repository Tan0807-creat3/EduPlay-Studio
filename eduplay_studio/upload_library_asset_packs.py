import argparse
import hashlib
import json
import time
from pathlib import Path

from eduplay.core.export_service import ExportService


CHUNK_SIZE = 200000


class FirebaseDbWriter:
    def __init__(self, database_url: str, requests_module=None, service_account_b64: str = ""):
        self.database_url = str(database_url or "").rstrip("/")
        self.requests = requests_module
        self.service_account_b64 = str(service_account_b64 or "").strip()
        self.service = ExportService()
        self._ref_factory = None
        self._headers = {"Content-Type": "application/json; charset=utf-8"}
        self._init_admin_sdk()

    def _init_admin_sdk(self) -> None:
        if not self.service_account_b64:
            return
        try:
            import firebase_admin
            from firebase_admin import credentials, db

            service_account_info = self.service._decode_service_account_info(self.service_account_b64)
            cred = credentials.Certificate(service_account_info)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {"databaseURL": self.database_url})
            self._ref_factory = db.reference
        except Exception:
            self._ref_factory = None

    def _ref_path(self, path: str) -> str:
        return "/" + str(path or "").strip("/")

    def get(self, path: str):
        ref_path = self._ref_path(path)
        if self._ref_factory is not None:
            return self._ref_factory(ref_path).get()
        if self.requests is None:
            import requests as _requests

            self.requests = _requests
        response = self.requests.get(self.database_url + ref_path + ".json")
        if not (200 <= int(getattr(response, "status_code", 500)) < 300):
            return None
        body = str(getattr(response, "text", "") or "").strip()
        if not body or body == "null":
            return None
        try:
            return json.loads(body)
        except Exception:
            return None

    def put(self, path: str, value):
        ref_path = self._ref_path(path)
        if self._ref_factory is not None:
            self._ref_factory(ref_path).set(value)
            return value
        if self.requests is None:
            import requests as _requests

            self.requests = _requests
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        response = self.requests.put(self.database_url + ref_path + ".json", data=body, headers=self._headers)
        if not (200 <= int(getattr(response, "status_code", 500)) < 300):
            raise RuntimeError(f"PUT failed for {ref_path}: {getattr(response, 'status_code', 'unknown')}")
        return value


def _normalize_profile_files(file_paths):
    normalized = []
    seen = set()
    for item in list(file_paths or []):
        path = Path(item)
        if not path.exists() or not path.is_file():
            continue
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(path)
    normalized.sort(key=lambda value: str(value).lower())
    return normalized


def build_library_asset_packs(assets_root=None, profiles=None):
    service = ExportService()
    assets_root_path = Path(assets_root).resolve() if assets_root else None
    profile_map = {}
    if profiles:
        for profile, file_paths in dict(profiles).items():
            profile_map[str(profile or "").strip().lower()] = _normalize_profile_files(file_paths)
    else:
        for profile in sorted(service.LIBRARY_ASSET_PACK_KEYS):
            profile_map[profile] = _normalize_profile_files(service._library_profile_files(profile))

    packs = {}
    for profile, file_paths in profile_map.items():
        assets = {}
        for file_path in file_paths:
            current_path = file_path
            if assets_root_path and not current_path.is_absolute():
                current_path = assets_root_path / current_path
            data_uri = service._file_to_base64(str(current_path))
            if not data_uri:
                continue
            assets[service._stable_asset_token(data_uri)] = data_uri
        canonical = json.dumps(assets, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        pack_key = service.LIBRARY_ASSET_PACK_KEYS.get(profile, "")
        if canonical:
            pack_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        payload = service._encode_asset_pack(assets, pack_key) if pack_key and assets else {
            "encoding": "base64",
            "encoded": "",
            "size_bytes": 0,
            "chunks": [""],
        }
        packs[profile] = {
            "profile": profile,
            "key": pack_key,
            "assets": assets,
            "payload": payload,
            "meta": {
                "type": "asset_pack",
                "profile": profile,
                "encoding": str(payload.get("encoding") or "base64"),
                "chunk_size": CHUNK_SIZE,
                "total_chunks": len(list(payload.get("chunks") or [""])),
                "asset_count": len(assets),
                "hash": pack_key,
                "size_bytes": int(payload.get("size_bytes") or 0),
                "library": True,
                "never_delete": True,
                "pinned": True,
            },
        }
    return packs


def _build_manifest_version_entry(profile: str, pack_key: str, meta: dict, updated_at: int) -> dict:
    return {
        "key": pack_key,
        "storage_key": pack_key,
        "profile": profile,
        "asset_count": int((meta or {}).get("asset_count") or 0),
        "total_chunks": int((meta or {}).get("total_chunks") or 0),
        "encoding": str((meta or {}).get("encoding") or ""),
        "library": True,
        "never_delete": True,
        "pinned": True,
        "updated_at": int(updated_at or 0),
        "hash": str((meta or {}).get("hash") or pack_key),
    }


def upload_library_asset_packs(database_url: str, packs: dict, requests_module=None, service_account_b64: str = ""):
    service = ExportService()
    writer = FirebaseDbWriter(
        database_url=database_url,
        requests_module=requests_module,
        service_account_b64=service_account_b64,
    )
    stored_manifests = {}

    for profile in sorted(dict(packs or {})):
        pack = dict((packs or {}).get(profile) or {})
        pack_key = str(pack.get("key") or "").strip()
        if not pack_key:
            continue
        payload = dict(pack.get("payload") or {})
        pack_meta = dict(pack.get("meta") or {})
        now_ts = int(time.time())
        asset_meta = {
            "type": "asset_pack",
            "profile": profile,
            "encoding": str(payload.get("encoding") or pack_meta.get("encoding") or "base64"),
            "created_at": now_ts,
            "updated_at": now_ts,
            "chunk_size": int(pack_meta.get("chunk_size") or CHUNK_SIZE),
            "total_chunks": len(list(payload.get("chunks") or [""])),
            "asset_count": int(pack_meta.get("asset_count") or 0),
            "hash": str(pack_meta.get("hash") or pack_key),
            "size_bytes": int(payload.get("size_bytes") or pack_meta.get("size_bytes") or 0),
            "library": True,
            "never_delete": True,
            "pinned": True,
        }

        existing_pack = writer.get(f"/asset_packs/{pack_key}")
        if not existing_pack:
            writer.put(f"/asset_packs/{pack_key}", asset_meta)
            for idx, chunk in enumerate(list(payload.get("chunks") or [""])):
                writer.put(f"/asset_packs/{pack_key}/chunks/{idx}", chunk)

        existing_manifest = writer.get(f"/asset_pack_libraries/{profile}") or {}
        normalized_manifest = service._normalize_library_manifest(profile, existing_manifest)
        versions = dict(normalized_manifest.get("versions") or {})
        versions[pack_key] = _build_manifest_version_entry(profile, pack_key, asset_meta, now_ts)
        manifest = {
            "profile": profile,
            "key": pack_key,
            "latest_key": pack_key,
            "library": True,
            "never_delete": True,
            "pinned": True,
            "updated_at": now_ts,
            "asset_count": int(asset_meta.get("asset_count") or 0),
            "total_chunks": int(asset_meta.get("total_chunks") or 0),
            "encoding": str(asset_meta.get("encoding") or ""),
            "hash": str(asset_meta.get("hash") or pack_key),
            "versions": versions,
            "known_keys": {key: True for key in sorted(versions)},
            "version_count": len(versions),
        }
        writer.put(f"/asset_pack_libraries/{profile}", manifest)
        stored_manifests[profile] = manifest

    return stored_manifests


def _default_profile_file_map():
    service = ExportService()
    return {
        profile: service._library_profile_files(profile)
        for profile in sorted(service.LIBRARY_ASSET_PACK_KEYS)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload shared EduPlay library asset packs to Firebase Realtime Database.")
    parser.add_argument("database_url")
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--service-account-b64", default="")
    args = parser.parse_args()

    available_profiles = _default_profile_file_map()
    selected_profiles = [str(item or "").strip().lower() for item in (args.profile or []) if str(item or "").strip()]
    if selected_profiles:
        profile_files = {profile: available_profiles[profile] for profile in selected_profiles if profile in available_profiles}
    else:
        profile_files = available_profiles

    service = ExportService()
    service_account_b64 = str(args.service_account_b64 or "").strip() or service._read_service_account_b64()
    packs = build_library_asset_packs(profiles=profile_files)
    manifest = upload_library_asset_packs(
        args.database_url,
        packs,
        service_account_b64=service_account_b64,
    )
    print(json.dumps({profile: data.get("key") for profile, data in manifest.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
