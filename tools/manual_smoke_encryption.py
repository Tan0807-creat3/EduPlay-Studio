import json
import os
import secrets
import struct
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "eduplay_studio") not in sys.path:
    sys.path.insert(0, str(ROOT / "eduplay_studio"))

import importlib.util

_spec = importlib.util.spec_from_file_location("obfuscate_assets", ROOT / "tools" / "obfuscate_assets.py")
oa = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(oa)

from eduplay.core import asset_loader as al


def _enc(path: Path, key: bytes, plaintext: bytes) -> None:
    nonce = secrets.token_bytes(al.NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    header = al.MAGIC + struct.pack(">BI", al.VERSION, len(plaintext)) + nonce
    path.write_bytes(header + ciphertext)


def main() -> int:
    td = Path(tempfile.mkdtemp())
    os.environ["LOCALAPPDATA"] = str(td)

    dist = td / "dist"
    internal = dist / "_internal"
    (internal / "eduplay/resources/styles").mkdir(parents=True, exist_ok=True)
    (internal / "eduplay/resources/i18n").mkdir(parents=True, exist_ok=True)
    (internal / "eduplay/resources/vsto_addin").mkdir(parents=True, exist_ok=True)

    exe = dist / "EduPlayStudio.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_bytes(b"FAKEEXE" + secrets.token_bytes(2048))

    seed = secrets.token_bytes(32)
    salt = secrets.token_bytes(oa.SALT_SIZE)
    key = oa.derive_asset_key(seed, salt)
    wrapped = oa.wrap_seed(seed, salt, str(exe))
    key_blob = oa.KEY_MAGIC + bytes([oa.VERSION]) + salt + wrapped
    with open(exe, "ab") as f:
        f.write(key_blob + oa.EXE_KEY_MARKER + struct.pack(">I", len(key_blob)))

    _enc(internal / "eduplay/resources/styles/dark_theme.qss", key, b"QWidget{color:red;}")
    _enc(internal / "eduplay/resources/i18n/vi.json", key, json.dumps({"k": "v"}).encode("utf-8"))
    _enc(internal / "eduplay/resources/vsto_addin/EduPlayPowerPointAddin.msi", key, b"MSI-DATA")

    setattr(sys, "frozen", True)
    setattr(sys, "_MEIPASS", str(internal))
    sys.executable = str(exe)

    assert al.load_asset_text("eduplay/resources/styles/dark_theme.qss") == "QWidget{color:red;}"
    assert json.loads(al.load_asset_text("eduplay/resources/i18n/vi.json")) == {"k": "v"}
    out = al.materialize_asset_file("eduplay/resources/vsto_addin/EduPlayPowerPointAddin.msi")
    assert out.exists() and out.read_bytes() == b"MSI-DATA"

    print("MANUAL_OK", td)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
