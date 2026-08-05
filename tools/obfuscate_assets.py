"""
EduPlay Studio — encrypt sensitive shipped assets with AES-GCM.

Usage:
    python obfuscate_assets.py <dist_dir> [exe_path]
"""

import hashlib
import os
import secrets
import struct
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"EPLA"
KEY_MAGIC = b"EPLK"
EXE_KEY_MARKER = b"EPLX"
VERSION = 2
NONCE_SIZE = 12
SALT_SIZE = 16
EMBEDDED_CODE_KEY = bytes.fromhex(
    "dc4aefd74a8ff1c75c96e7820d3a8d9976196a85c47d3c7656203946b029487f"
)

OBFUSCATE_EXTS = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".ttf",
    ".otf",
    ".qss",
    ".json",
    ".msi",
    ".dll",
    ".cab",
    ".xml",
    ".vsto",
    ".manifest",
    ".fernet",
}
TARGET_SUBDIRS = [
    os.path.join("assets_bundle", "templates_fish"),
    os.path.join("assets_bundle", "millionaire"),
    os.path.join("assets_bundle", "millionaire_ngdat"),
    os.path.join("assets_bundle", "millionaire_exam"),
    os.path.join("assets_bundle", "templates"),
    os.path.join("eduplay", "resources", "styles"),
    os.path.join("eduplay", "resources", "i18n"),
    os.path.join("eduplay", "resources", "fonts"),
    os.path.join("eduplay", "resources", "vsto_addin"),
]
TARGET_FILES = [
    os.path.join("eduplay", "resources", "firebase_service_account.fernet"),
]
SKIP_SUBSTRINGS = (
    os.path.join("sounds", ""),
    os.path.join("images", ""),
    os.path.join("scss", ""),
)


def derive_asset_key(seed: bytes, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        seed,
        salt + b"EduPlayStudioAssetKey",
        240000,
        dklen=32,
    )


def build_binding_digest(exe_path: str) -> bytes:
    size = os.path.getsize(exe_path)
    try:
        if size >= 8:
            with open(exe_path, "rb") as handle:
                handle.seek(-8, 2)
                tail = handle.read(8)
                if len(tail) == 8 and tail[:4] == EXE_KEY_MARKER:
                    blob_len = struct.unpack(">I", tail[4:8])[0]
                    footer = 8 + int(blob_len)
                    if 0 < footer < size:
                        size -= footer
    except Exception:
        size = os.path.getsize(exe_path)

    digest = hashlib.sha256()
    digest.update(os.path.basename(exe_path).encode("utf-8", errors="ignore"))
    digest.update(str(size).encode("ascii"))
    with open(exe_path, "rb") as handle:
        remaining = int(size)
        while remaining > 0:
            chunk = handle.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            digest.update(chunk)
            remaining -= len(chunk)
    return digest.digest()


def wrap_seed(seed: bytes, salt: bytes, exe_path: str) -> bytes:
    binding_digest = build_binding_digest(exe_path)
    wrap_key = hashlib.pbkdf2_hmac(
        "sha256",
        EMBEDDED_CODE_KEY + binding_digest,
        salt + b"EduPlayStudioKeyWrap",
        320000,
        dklen=32,
    )
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = AESGCM(wrap_key).encrypt(nonce, seed, None)
    return nonce + ciphertext


def should_encrypt(rel_path: str) -> bool:
    normalized = rel_path.replace("/", os.sep).replace("\\", os.sep).lower()
    if os.path.splitext(normalized)[1] not in OBFUSCATE_EXTS:
        return False
    return not any(token in normalized for token in SKIP_SUBSTRINGS)


def encrypt_file(path: str, key: bytes) -> bool:
    """Encrypt a single file in-place, prepend the EduPlay header."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        if data[:4] == MAGIC:
            return True
        nonce = secrets.token_bytes(NONCE_SIZE)
        encrypted = AESGCM(key).encrypt(nonce, data, None)
        header = MAGIC + struct.pack(">BI", VERSION, len(data)) + nonce
        with open(path, "wb") as f:
            f.write(header + encrypted)
        return True
    except Exception as e:
        print(f"  [WARN] Could not encrypt {path}: {e}")
        return False


def encrypt_target_file(dist_dir: str, rel_path: str, key: bytes) -> tuple[int, int]:
    full_path = os.path.join(dist_dir, rel_path)
    if not os.path.isfile(full_path):
        return 0, 0
    if encrypt_file(full_path, key):
        print(f"  [OK] {rel_path}")
        return 1, 0
    return 0, 1


def resolve_exe_path(dist_dir: str, exe_path_arg: str | None) -> str:
    if exe_path_arg:
        return exe_path_arg

    for entry in os.listdir(dist_dir):
        if entry.lower().endswith(".exe"):
            return os.path.join(dist_dir, entry)
    raise FileNotFoundError("No executable found in dist directory")


def resolve_payload_root(dist_dir: str) -> str:
    internal_dir = os.path.join(dist_dir, "_internal")
    if os.path.isdir(internal_dir):
        return internal_dir
    return dist_dir


def main():
    if len(sys.argv) < 2:
        print("Usage: obfuscate_assets.py <dist_dir> [exe_path]")
        sys.exit(1)

    dist_dir = os.path.abspath(sys.argv[1])
    if not os.path.isdir(dist_dir):
        print(f"[ERROR] Directory not found: {dist_dir}")
        sys.exit(1)

    exe_path = os.path.abspath(resolve_exe_path(dist_dir, sys.argv[2] if len(sys.argv) > 2 else None))
    if not os.path.isfile(exe_path):
        print(f"[ERROR] Executable not found: {exe_path}")
        sys.exit(1)
    payload_root = resolve_payload_root(dist_dir)

    seed = secrets.token_bytes(32)
    salt = secrets.token_bytes(SALT_SIZE)
    key = derive_asset_key(seed, salt)

    processed = 0
    failed = 0

    for rel_path in TARGET_FILES:
        ok_count, fail_count = encrypt_target_file(payload_root, rel_path, key)
        processed += ok_count
        failed += fail_count

    for subdir in TARGET_SUBDIRS:
        target = os.path.join(payload_root, subdir)
        if not os.path.isdir(target):
            continue
        for root, dirs, files in os.walk(target):
            dirs[:] = [name for name in dirs if name.lower() not in {"images", "sounds", "scss"}]
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, payload_root)
                if not should_encrypt(rel):
                    continue
                if encrypt_file(full, key):
                    processed += 1
                    print(f"  [OK] {rel}")
                else:
                    failed += 1

    wrapped_seed = wrap_seed(seed, salt, exe_path)
    key_blob = KEY_MAGIC + bytes([VERSION]) + salt + wrapped_seed
    with open(exe_path, "ab") as f:
        f.write(key_blob + EXE_KEY_MARKER + struct.pack(">I", len(key_blob)))

    legacy_key_path = os.path.join(dist_dir, "_key.dat")
    if os.path.exists(legacy_key_path):
        try:
            os.remove(legacy_key_path)
        except Exception:
            pass

    print(f"\n  Key embedded into: {exe_path}")
    print(f"  Files encrypted: {processed}, failed: {failed}")

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
