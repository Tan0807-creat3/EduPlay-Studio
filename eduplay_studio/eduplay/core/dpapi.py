import sys
import ctypes
from ctypes import wintypes


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _raise_if_not_windows():
    if sys.platform != "win32":
        raise OSError("dpapi_not_supported")


def protect(data: bytes) -> bytes:
    _raise_if_not_windows()
    if data is None:
        data = b""
    in_buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DATA_BLOB(len(data), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_byte)))
    blob_out = _DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        wintypes.DWORD(0),
        ctypes.byref(blob_out),
    )
    if not ok:
        raise OSError("dpapi_protect_failed")
    try:
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        try:
            kernel32.LocalFree(blob_out.pbData)
        except Exception:
            pass
    return out


def unprotect(data: bytes) -> bytes:
    _raise_if_not_windows()
    if data is None:
        data = b""
    in_buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _DATA_BLOB(len(data), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_byte)))
    blob_out = _DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        wintypes.DWORD(0),
        ctypes.byref(blob_out),
    )
    if not ok:
        raise OSError("dpapi_unprotect_failed")
    try:
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        try:
            kernel32.LocalFree(blob_out.pbData)
        except Exception:
            pass
    return out
