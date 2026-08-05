from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import winreg
import shutil
import urllib.parse
import hashlib

from eduplay.core.asset_loader import materialize_asset_tree
from eduplay.core.path_resolver import PathResolver


@dataclass
class _UninstallEntry:
    root_name: str
    subkey: str
    display_name: str
    display_version: str
    uninstall_string: str
    quiet_uninstall_string: str

    @property
    def product_code(self) -> str:
        s = str(self.subkey or "")
        if s.startswith("{") and s.endswith("}"):
            return s
        return ""


class PptVstoAddinService:
    DEFAULT_DISPLAY_NAME = "EduPlay PowerPoint Add-in"
    DEFAULT_MSI_FILENAME = "EduPlayPowerPointAddin.msi"
    SUPPORT_URL = "https://eduplay-game.web.app/support/addin"
    ADDIN_KEY_NAME = "EduPlayPowerPointAddin"
    ADDIN_INSTALL_DIRNAME = "EduPlayPowerPointAddin"
    OFFICE_APP = "PowerPoint"

    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager

    def support_url(self) -> str:
        return str(self.SUPPORT_URL)

    def _display_name(self) -> str:
        try:
            sm = self.settings_manager
            if sm is not None:
                v = str(sm.get("ppt_addin.vsto_display_name", "") or "").strip()
                if v:
                    return v
        except Exception:
            pass
        return str(self.DEFAULT_DISPLAY_NAME)

    def _msi_filename(self) -> str:
        try:
            sm = self.settings_manager
            if sm is not None:
                v = str(sm.get("ppt_addin.vsto_msi_filename", "") or "").strip()
                if v:
                    return v
        except Exception:
            pass
        return str(self.DEFAULT_MSI_FILENAME)

    def _is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _run_msiexec(self, args: list[str], *, elevate: bool) -> int:
        exe = "msiexec.exe"
        if not elevate or self._is_admin():
            try:
                p = subprocess.run([exe, *args], capture_output=True, text=True, check=False)
                return int(p.returncode)
            except Exception:
                return 1
        try:
            safe_args = " ".join([str(a).replace("'", "''") for a in args])
            ps = (
                "$p = Start-Process -FilePath 'msiexec.exe' "
                "-ArgumentList '" + safe_args + "' "
                "-Verb RunAs -WindowStyle Hidden -Wait -PassThru; exit $p.ExitCode"
            )
            p = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                capture_output=True,
                text=True,
                check=False,
            )
            return int(p.returncode)
        except Exception:
            return 1

    def _run_powershell_file(self, args: list[str]) -> int:
        exe = "powershell"
        try:
            p = subprocess.run(
                [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", *args],
                capture_output=True,
                text=True,
                check=False,
            )
            return int(p.returncode)
        except Exception:
            return 1

    def _msi_log_path(self) -> str:
        try:
            return str(Path(tempfile.gettempdir()) / "eduplay_msi_install.log")
        except Exception:
            return os.path.join(os.environ.get("TEMP", ""), "eduplay_msi_install.log")

    def _uninstall_roots(self) -> Iterable[Tuple[str, int, str]]:
        base = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        yield ("HKCU_64", winreg.HKEY_CURRENT_USER, base)
        yield ("HKCU_32", winreg.HKEY_CURRENT_USER, base)
        yield ("HKLM_64", winreg.HKEY_LOCAL_MACHINE, base)
        yield ("HKLM_32", winreg.HKEY_LOCAL_MACHINE, base)

    def _open_key(self, root: int, path: str, *, wow: Optional[int]) -> Optional[winreg.HKEYType]:
        try:
            access = winreg.KEY_READ
            if wow is not None:
                access |= int(wow)
            return winreg.OpenKey(root, path, 0, access)
        except Exception:
            return None

    def _read_str(self, key: winreg.HKEYType, name: str) -> str:
        try:
            v, _ = winreg.QueryValueEx(key, name)
            return str(v or "").strip()
        except Exception:
            return ""

    def _iter_uninstall_entries(self) -> Iterable[_UninstallEntry]:
        for root_name, root, base_path in self._uninstall_roots():
            for wow in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY, None):
                k = self._open_key(root, base_path, wow=wow)
                if k is None:
                    continue
                try:
                    idx = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(k, idx)
                            idx += 1
                        except OSError:
                            break
                        sk = self._open_key(root, f"{base_path}\\{sub}", wow=wow)
                        if sk is None:
                            continue
                        try:
                            dn = self._read_str(sk, "DisplayName")
                            if not dn:
                                continue
                            yield _UninstallEntry(
                                root_name=str(root_name),
                                subkey=str(sub),
                                display_name=dn,
                                display_version=self._read_str(sk, "DisplayVersion"),
                                uninstall_string=self._read_str(sk, "UninstallString"),
                                quiet_uninstall_string=self._read_str(sk, "QuietUninstallString"),
                            )
                        finally:
                            try:
                                winreg.CloseKey(sk)
                            except Exception:
                                pass
                finally:
                    try:
                        winreg.CloseKey(k)
                    except Exception:
                        pass

    def detect_installed(self) -> Dict:
        target = self._display_name().lower().strip()
        for e in self._iter_uninstall_entries():
            try:
                dn = (e.display_name or "").lower()
            except Exception:
                dn = ""
            if target and target in dn:
                scope = "user"
                try:
                    if str(e.root_name or "").upper().startswith("HKLM"):
                        scope = "machine"
                except Exception:
                    scope = "user"
                return {
                    "installed": True,
                    "display_name": e.display_name,
                    "version": e.display_version,
                    "product_code": e.product_code,
                    "scope": scope,
                }
        return {"installed": False, "display_name": self._display_name(), "version": "", "product_code": "", "scope": ""}

    def _msi_path(self) -> Path:
        name = self._msi_filename()
        if getattr(sys, "frozen", False):
            return materialize_asset_tree("eduplay/resources/vsto_addin") / name
        return Path(__file__).resolve().parents[1] / "resources" / "vsto_addin" / name

    def _vsto_payload_dir(self) -> Path:
        try:
            return self._msi_path().resolve().parent
        except Exception:
            return Path(os.getcwd())

    def msi_path(self) -> str:
        try:
            return str(self._msi_path())
        except Exception:
            return ""

    def _addin_registry_path(self) -> str:
        return rf"Software\Microsoft\Office\PowerPoint\Addins\{self.ADDIN_KEY_NAME}"

    def _installed_vsto_manifest_path(self) -> str:
        addin_dir = PathResolver.resolve_addin_dir()
        p = addin_dir / f"{self.ADDIN_KEY_NAME}.vsto"
        return str(p)

    def _file_url(self, path: str) -> str:
        try:
            p = Path(path).resolve()
            s = str(p).replace("\\", "/")
            if re.match(r"^[A-Za-z]:/", s):
                return "file:///" + s
            return "file:///" + s.lstrip("/")
        except Exception:
            return ""

    def _read_text(self, path: str) -> str:
        try:
            return Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

    def _extract_public_key_from_vsto(self, vsto_path: str) -> str:
        txt = self._read_text(vsto_path)
        if not txt:
            return ""
        m = re.search(r"(<RSAKeyValue>.*?</RSAKeyValue>)", txt, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        return str(m.group(1)).strip()

    def _write_reg_value(self, root: int, path: str, name: str, value, reg_type: int) -> None:
        k = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(k, name, 0, int(reg_type), value)
        finally:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass

    def _read_reg_str(self, root: int, path: str, name: str) -> str:
        try:
            k = winreg.OpenKey(root, path, 0, winreg.KEY_READ)
        except Exception:
            return ""
        try:
            v, _ = winreg.QueryValueEx(k, name)
            return str(v or "").strip()
        except Exception:
            return ""
        finally:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass

    def trusted_slides_dir(self) -> Path:
        p = self._read_reg_str(winreg.HKEY_CURRENT_USER, r"Software\EduPlayPowerPointAddin", "TrustedSlidesFolder")
        if p:
            try:
                return Path(p).expanduser()
            except Exception:
                pass
        return PathResolver.resolve_trusted_slides_dir()

    def trusted_slides_cache_dir(self) -> Path:
        return self.trusted_slides_dir() / "EduPlayCache"

    def _iter_candidate_presentations(self, root: Path) -> list[Path]:
        if not root.exists() or not root.is_dir():
            return []
        out: list[Path] = []
        try:
            for p in root.rglob("*"):
                try:
                    if not p.is_file():
                        continue
                    ext = p.suffix.lower()
                    if ext not in (".pptx", ".pptm"):
                        continue
                    out.append(p)
                except Exception:
                    continue
        except Exception:
            return []
        try:
            out.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        except Exception:
            pass
        return out

    def seed_trusted_slides_from_documents(self, *, max_files: int = 1) -> Dict:
        result: Dict = {"copied": [], "skipped": [], "errors": []}
        try:
            docs = PathResolver.resolve_eduplay_root()
        except Exception:
            docs = Path(os.environ.get("USERPROFILE", "") or os.getcwd()) / "Documents" / "EduPlay"
        candidates = self._iter_candidate_presentations(docs)
        if not candidates:
            return result
        dst_dir = self.trusted_slides_cache_dir()
        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            result["errors"].append(str(e))
            return result
        n = 0
        for src in candidates:
            if n >= int(max_files):
                break
            try:
                dst = dst_dir / self._trusted_cache_name_for_source(str(src))
                if dst.exists():
                    try:
                        if dst.stat().st_size == src.stat().st_size:
                            result["skipped"].append(str(src))
                            n += 1
                            continue
                    except Exception:
                        pass
                    try:
                        dst.unlink(missing_ok=True)
                    except Exception:
                        pass
                shutil.copy2(str(src), str(dst))
                result["copied"].append({"from": str(src), "to": str(dst)})
                n += 1
            except Exception as e:
                result["errors"].append(f"{src}: {e}")
        return result

    def _iter_registry_values(self, root: int, path: str) -> Iterable[Tuple[str, str]]:
        try:
            k = winreg.OpenKey(root, path, 0, winreg.KEY_READ)
        except Exception:
            return []
        out: list[Tuple[str, str]] = []
        try:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(k, i)
                    i += 1
                except OSError:
                    break
                try:
                    out.append((str(name or ""), str(value or "")))
                except Exception:
                    continue
        finally:
            try:
                winreg.CloseKey(k)
            except Exception:
                pass
        return out

    def _extract_path_from_mru_value(self, s: str) -> str:
        try:
            text = str(s or "")
        except Exception:
            return ""
        if not text:
            return ""
        try:
            m = re.search(r"(file:///[^\\s]+?\\.(pptx|pptm))", text, flags=re.IGNORECASE)
            if m:
                u = m.group(1)
                u = urllib.parse.unquote(u)
                u = u.replace("file:///", "")
                u = u.replace("/", "\\")
                return u.strip().strip('"')
        except Exception:
            pass
        try:
            m2 = re.search(r"([A-Za-z]:\\\\.*?\\.(pptx|pptm))", text, flags=re.IGNORECASE)
            if m2:
                return str(m2.group(1)).strip().strip('"')
        except Exception:
            pass
        try:
            m3 = re.search(r"(\\\\\\\\.*?\\.(pptx|pptm))", text, flags=re.IGNORECASE)
            if m3:
                return str(m3.group(1)).strip().strip('"')
        except Exception:
            pass
        return ""

    def get_latest_powerpoint_mru_path(self) -> str:
        paths = self.get_powerpoint_mru_paths(limit=1)
        if paths:
            return str(paths[0])
        return ""

    def get_powerpoint_mru_paths(self, *, limit: int = 3) -> list[str]:
        limit = max(1, int(limit))
        out: list[str] = []
        seen: set[str] = set()
        for v in ("16.0", "15.0", "14.0"):
            base = rf"Software\Microsoft\Office\{v}\PowerPoint\File MRU"
            values = list(self._iter_registry_values(winreg.HKEY_CURRENT_USER, base))
            if not values:
                continue
            items: list[Tuple[int, str]] = []
            for name, val in values:
                n = 9999
                try:
                    m = re.search(r"(\d+)", str(name))
                    if m:
                        n = int(m.group(1))
                except Exception:
                    n = 9999
                p = self._extract_path_from_mru_value(val)
                if p:
                    items.append((n, p))
            if not items:
                continue
            items.sort(key=lambda x: x[0])
            for _, p in items:
                try:
                    key = str(p).strip().lower()
                except Exception:
                    key = ""
                if not key or key in seen:
                    continue
                seen.add(key)
                out.append(str(p).strip())
                if len(out) >= limit:
                    return out
        return out

    def _trusted_cache_name_for_source(self, source_path: str) -> str:
        try:
            p = str(source_path or "")
        except Exception:
            p = ""
        try:
            sp = Path(p)
        except Exception:
            sp = None
        try:
            stem = sp.stem if sp is not None else "presentation"
            ext = sp.suffix if sp is not None and sp.suffix else ".pptx"
        except Exception:
            stem = "presentation"
            ext = ".pptx"
        try:
            h = hashlib.md5(p.strip().lower().encode("utf-8", errors="ignore")).hexdigest()[:10]
        except Exception:
            h = "cache"
        safe_stem = re.sub(r"[^A-Za-z0-9_\-]+", "_", stem).strip("_")
        if not safe_stem:
            safe_stem = "presentation"
        return f"{safe_stem}_{h}{ext}"

    def copy_to_trusted_slides(self, source_path: str) -> Dict:
        result: Dict = {"copied": None, "skipped": False, "errors": []}
        try:
            src = Path(str(source_path or "")).expanduser()
        except Exception:
            result["errors"].append("Invalid source path.")
            result["skipped"] = True
            return result
        try:
            if not src.exists() or not src.is_file():
                result["errors"].append("Source file not found.")
                result["skipped"] = True
                return result
        except Exception:
            result["errors"].append("Source file not accessible.")
            result["skipped"] = True
            return result
        try:
            if src.suffix.lower() not in (".pptx", ".pptm"):
                result["skipped"] = True
                return result
        except Exception:
            result["skipped"] = True
            return result
        try:
            sm = self.settings_manager
            max_file_mb = 30
            max_files = 3
            use_hardlink = True
            if sm is not None:
                try:
                    max_file_mb = int(sm.get("ppt_addin.trusted_cache_max_file_mb", 30) or 30)
                except Exception:
                    max_file_mb = 30
                try:
                    max_files = int(sm.get("ppt_addin.trusted_cache_max_files", 3) or 3)
                except Exception:
                    max_files = 3
                try:
                    use_hardlink = bool(sm.get("ppt_addin.trusted_cache_use_hardlink", True))
                except Exception:
                    use_hardlink = True
            if int(max_file_mb) > 0:
                max_file_mb = max(1, max_file_mb)
            max_files = max(1, max_files)
            try:
                size_mb = float(src.stat().st_size) / (1024 * 1024)
            except Exception:
                size_mb = 0.0
            if int(max_file_mb) > 0 and size_mb > float(max_file_mb):
                result["skipped"] = True
                return result
        except Exception:
            pass
        dst_dir = self.trusted_slides_cache_dir()
        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            result["errors"].append(str(e))
            return result
        try:
            try:
                if src.resolve().parent == dst_dir.resolve():
                    result["skipped"] = True
                    return result
            except Exception:
                pass
            dst = dst_dir / self._trusted_cache_name_for_source(str(src))
            if dst.exists():
                try:
                    if dst.stat().st_size == src.stat().st_size:
                        result["skipped"] = True
                        return result
                except Exception:
                    pass
                try:
                    dst.unlink(missing_ok=True)
                except Exception:
                    pass
            copied_as = "copy"
            try:
                if use_hardlink:
                    try:
                        if src.drive and dst.drive and str(src.drive).lower() == str(dst.drive).lower():
                            os.link(str(src), str(dst))
                            copied_as = "hardlink"
                        else:
                            shutil.copy2(str(src), str(dst))
                    except Exception:
                        shutil.copy2(str(src), str(dst))
                else:
                    shutil.copy2(str(src), str(dst))
            except Exception:
                shutil.copy2(str(src), str(dst))
            result["copied"] = {"from": str(src), "to": str(dst)}
            try:
                result["copied"]["mode"] = copied_as
            except Exception:
                pass
            try:
                keep = max_files
                all_files = []
                for p in dst_dir.glob("*.ppt*"):
                    try:
                        if not p.is_file():
                            continue
                        if p.suffix.lower() not in (".pptx", ".pptm"):
                            continue
                        all_files.append(p)
                    except Exception:
                        continue
                all_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                for p in all_files[keep:]:
                    try:
                        p.unlink(missing_ok=True)
                    except Exception:
                        pass
            except Exception:
                pass
            return result
        except Exception as e:
            result["errors"].append(str(e))
            return result

    def sync_trusted_slides_from_powerpoint_mru(self, *, limit: int = 3) -> Dict:
        result: Dict = {"mru": [], "copied": [], "skipped": [], "deleted": [], "errors": []}
        try:
            mru_paths = self.get_powerpoint_mru_paths(limit=int(limit))
        except Exception:
            mru_paths = []
        if not mru_paths:
            return result
        result["mru"] = list(mru_paths)
        cache_dir = self.trusted_slides_cache_dir()
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            result["errors"].append(str(e))
            return result
        desired_names: set[str] = set()
        for p in mru_paths:
            try:
                desired_names.add(self._trusted_cache_name_for_source(p).lower())
            except Exception:
                pass
            r = self.copy_to_trusted_slides(p)
            if r.get("copied"):
                result["copied"].append(r["copied"])
            elif r.get("skipped"):
                result["skipped"].append(p)
            elif r.get("errors"):
                for e in r.get("errors", []):
                    result["errors"].append(str(e))
        try:
            sm = self.settings_manager
            mode = "mru_only"
            if sm is not None:
                try:
                    mode = str(sm.get("ppt_addin.trusted_cache_cleanup_mode", "mru_only") or "mru_only").strip()
                except Exception:
                    mode = "mru_only"
            if mode.lower() == "mru_only":
                for f in cache_dir.glob("*.ppt*"):
                    try:
                        if not f.is_file():
                            continue
                        if f.name.lower() in desired_names:
                            continue
                        f.unlink(missing_ok=True)
                        result["deleted"].append(str(f))
                    except Exception:
                        continue
        except Exception:
            pass
        return result

    def _ensure_powerpoint_addin_registered(self) -> None:
        manifest = self._installed_vsto_manifest_path()
        if not manifest:
            return
        key = self._addin_registry_path()
        self._write_reg_value(winreg.HKEY_CURRENT_USER, key, "FriendlyName", self._display_name(), winreg.REG_SZ)
        self._write_reg_value(
            winreg.HKEY_CURRENT_USER, key, "Description", "EduPlay PowerPoint Add-in", winreg.REG_SZ
        )
        self._write_reg_value(winreg.HKEY_CURRENT_USER, key, "LoadBehavior", 3, winreg.REG_DWORD)
        self._write_reg_value(
            winreg.HKEY_CURRENT_USER, key, "Manifest", f"{manifest}|vstolocal", winreg.REG_SZ
        )

    def _ensure_vsto_trust_and_metadata(self) -> None:
        manifest = self._installed_vsto_manifest_path()
        if not manifest:
            return
        url = self._file_url(manifest)
        if not url:
            return
        public_key = self._extract_public_key_from_vsto(manifest)
        if public_key:
            inc_key = rf"Software\Microsoft\VSTO\Security\Inclusion\{uuid.uuid5(uuid.NAMESPACE_URL, url)}"
            self._write_reg_value(winreg.HKEY_CURRENT_USER, inc_key, "Url", url, winreg.REG_SZ)
            self._write_reg_value(winreg.HKEY_CURRENT_USER, inc_key, "PublicKey", public_key, winreg.REG_SZ)

        solution_guid = "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"eduplay:{self.ADDIN_KEY_NAME}")).upper() + "}"
        self._write_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\VSTO\SolutionMetadata",
            url,
            solution_guid,
            winreg.REG_SZ,
        )
        sm_key = rf"Software\Microsoft\VSTO\SolutionMetadata\{solution_guid}"
        self._write_reg_value(winreg.HKEY_CURRENT_USER, sm_key, "addInName", self.ADDIN_KEY_NAME, winreg.REG_SZ)
        self._write_reg_value(winreg.HKEY_CURRENT_USER, sm_key, "officeApplication", self.OFFICE_APP, winreg.REG_SZ)
        self._write_reg_value(winreg.HKEY_CURRENT_USER, sm_key, "friendlyName", self._display_name(), winreg.REG_SZ)
        self._write_reg_value(
            winreg.HKEY_CURRENT_USER, sm_key, "description", "EduPlay PowerPoint Add-in", winreg.REG_SZ
        )
        self._write_reg_value(winreg.HKEY_CURRENT_USER, sm_key, "loadBehavior", "3", winreg.REG_SZ)
        self._write_reg_value(
            winreg.HKEY_CURRENT_USER,
            sm_key,
            "compatibleFrameworks",
            '<compatibleFrameworks xmlns="urn:schemas-microsoft-com:clickonce.v2">\r\n\r\n  <framework targetVersion="4.8" profile="Full" supportedRuntime="4.0.30319" />\r\n\r\n</compatibleFrameworks>\r\n',
            winreg.REG_SZ,
        )

    def _set_do_not_disable_addin(self) -> None:
        for v in ("16.0", "15.0"):
            p = rf"Software\Microsoft\Office\{v}\PowerPoint\Resiliency\DoNotDisableAddinList"
            self._write_reg_value(winreg.HKEY_CURRENT_USER, p, self.ADDIN_KEY_NAME, 1, winreg.REG_DWORD)

    def install_or_update(self) -> Dict:
        result: Dict = {"installed": False, "version": "", "errors": [], "warnings": []}
        msi = self._msi_path()
        if not msi.exists():
            result["errors"].append(f"Missing MSI: {msi}")
            return result

        detected_before = self.detect_installed()
        already = bool(detected_before.get("installed"))
        scope = str(detected_before.get("scope", "") or "").strip().lower()
        elevate = scope == "machine"

        log_path = self._msi_log_path()
        args = ["/i", str(msi), "/qn", "/norestart", "/L*V", log_path]

        code = self._run_msiexec(args, elevate=bool(elevate))
        if int(code) != 0 and not elevate:
            code = self._run_msiexec(args, elevate=True)
        if int(code) != 0:
            if log_path:
                result["errors"].append(f"msiexec exited with code {code}. Log: {log_path}")
            else:
                result["errors"].append(f"msiexec exited with code {code}")
            return result

        detected_after = self.detect_installed()
        if not bool(detected_after.get("installed")):
            result["errors"].append("Add-in not detected after install.")
            return result

        result["installed"] = True
        result["version"] = str(detected_after.get("version", "") or "").strip()

        try:
            self._ensure_powerpoint_addin_registered()
            self._ensure_vsto_trust_and_metadata()
            self._set_do_not_disable_addin()
        except Exception:
            result["warnings"].append("Could not verify Office add-in registration. Try restarting PowerPoint.")

        try:
            sm = self.settings_manager
            if sm is not None:
                sm.set("ppt_addin.installed_once", True)
                sm.set("ppt_addin.version", result["version"])
        except Exception:
            pass

        try:
            pass
        except Exception:
            pass

        return result

    def prepare_activex_environment(self) -> Dict:
        return {"ok": True, "ran": False, "error": ""}

