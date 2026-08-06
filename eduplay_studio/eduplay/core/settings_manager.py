"""
Settings Manager - Handles application settings and API keys
"""

import os
import sys
import json
import base64
import copy
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from eduplay.core.path_resolver import PathResolver


class SettingsManager:
    """Manages application settings and API keys"""

    SECRET_PREFIX = "enc_v1:"
    RC2_HEADER_TOKEN = "v1.0.0 RC2"
    RC2_HEADER_LINE = "// v1.0.0 RC2\n"
    
    def __init__(self, settings_dir: Path | None = None):
        """Initialize settings manager"""
        self.settings_dir = settings_dir or self._get_settings_directory()
        self.settings_file = self.settings_dir / "settings.json"
        self.settings = {}
        self._settings_file_header_lines: list[str] = []
        self._has_rc2_header = False
        self._needs_rc2_whats_new = False
        self._settings_file_existed_on_load = False
        self.load_settings()
    
    def _get_settings_directory(self) -> Path:
        """Get the settings directory path"""
        try:
            settings_dir = PathResolver.resolve_settings_dir()
        except Exception:
            try:
                user_profile = os.environ.get('USERPROFILE') or os.environ.get('HOME')
                base = Path(user_profile) if user_profile else Path(os.getcwd())
                settings_dir = base / "EduPlay" / "Settings"
            except Exception:
                settings_dir = Path(os.getcwd()) / ".eduplay_settings"
        try:
            settings_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            settings_dir = Path(os.getcwd()) / ".eduplay_settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir

    def _is_sensitive_path(self, key: str) -> bool:
        return (
            key == "ai_settings.proxy_token"
            or key == "device_auth.device_key"
            or key == "puter_ai.api_key"
            or key.startswith("api_keys.")
            or key.startswith("api_keys_pool.")
        )

    def _protect_secret_text(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.startswith(self.SECRET_PREFIX):
            return text
        try:
            from eduplay.core.dpapi import protect as _dpapi_protect
        except Exception:
            _dpapi_protect = None  # type: ignore
        if _dpapi_protect is None or sys.platform != "win32":
            return text
        try:
            blob = _dpapi_protect(text.encode("utf-8"))
            return self.SECRET_PREFIX + base64.b64encode(blob).decode("ascii")
        except Exception:
            return text

    def _unprotect_secret_text(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text or not text.startswith(self.SECRET_PREFIX):
            return text
        payload = text[len(self.SECRET_PREFIX) :].strip()
        if not payload:
            return ""
        try:
            from eduplay.core.dpapi import unprotect as _dpapi_unprotect
        except Exception:
            _dpapi_unprotect = None  # type: ignore
        if _dpapi_unprotect is None or sys.platform != "win32":
            return ""
        try:
            blob = base64.b64decode(payload)
            plain = _dpapi_unprotect(blob)
            return plain.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    def _encrypt_sensitive_value(self, key: str, value: Any) -> Any:
        if not self._is_sensitive_path(key):
            return value
        if key.startswith("api_keys_pool."):
            if not isinstance(value, list):
                return []
            return [self._protect_secret_text(item) for item in value if str(item or "").strip()]
        return self._protect_secret_text(value)

    def _decrypt_sensitive_value(self, key: str, value: Any) -> Any:
        if not self._is_sensitive_path(key):
            return value
        if key.startswith("api_keys_pool."):
            if not isinstance(value, list):
                return []
            out = []
            for item in value:
                plain = self._unprotect_secret_text(item)
                if plain:
                    out.append(plain)
                elif str(item or "").strip() and not str(item).startswith(self.SECRET_PREFIX):
                    out.append(str(item).strip())
            return out
        plain = self._unprotect_secret_text(value)
        if plain:
            return plain
        return str(value or "").strip() if not str(value or "").startswith(self.SECRET_PREFIX) else ""

    def _public_value_for_key(self, key: str, value: Any) -> Any:
        if key == "ai_settings" and isinstance(value, dict):
            out = copy.deepcopy(value)
            if "proxy_token" in out:
                out["proxy_token"] = self._decrypt_sensitive_value("ai_settings.proxy_token", out.get("proxy_token", ""))
            return out
        if key == "device_auth" and isinstance(value, dict):
            out = copy.deepcopy(value)
            if "device_key" in out:
                out["device_key"] = self._decrypt_sensitive_value("device_auth.device_key", out.get("device_key", ""))
            return out
        if key == "puter_ai" and isinstance(value, dict):
            out = copy.deepcopy(value)
            if "api_key" in out:
                out["api_key"] = self._decrypt_sensitive_value("puter_ai.api_key", out.get("api_key", ""))
            return out
        if key == "api_keys" and isinstance(value, dict):
            out = {}
            for service, secret in value.items():
                out[service] = self._decrypt_sensitive_value(f"api_keys.{service}", secret)
            return out
        if key == "api_keys_pool" and isinstance(value, dict):
            out = {}
            for service, secret_list in value.items():
                out[service] = self._decrypt_sensitive_value(f"api_keys_pool.{service}", secret_list)
            return out
        return value

    def _migrate_sensitive_settings(self) -> bool:
        changed = False

        api_keys = self.settings.get("api_keys")
        if isinstance(api_keys, dict):
            for service, secret in list(api_keys.items()):
                encrypted = self._encrypt_sensitive_value(f"api_keys.{service}", secret)
                if encrypted != secret:
                    api_keys[service] = encrypted
                    changed = True

        api_key_pools = self.settings.get("api_keys_pool")
        if isinstance(api_key_pools, dict):
            for service, secrets in list(api_key_pools.items()):
                encrypted = self._encrypt_sensitive_value(f"api_keys_pool.{service}", secrets)
                if encrypted != secrets:
                    api_key_pools[service] = encrypted
                    changed = True

        ai_settings = self.settings.get("ai_settings")
        if isinstance(ai_settings, dict) and "proxy_token" in ai_settings:
            secret = ai_settings.get("proxy_token", "")
            encrypted = self._encrypt_sensitive_value("ai_settings.proxy_token", secret)
            if encrypted != secret:
                ai_settings["proxy_token"] = encrypted
                changed = True

        device_auth = self.settings.get("device_auth")
        if isinstance(device_auth, dict) and "device_key" in device_auth:
            secret = device_auth.get("device_key", "")
            encrypted = self._encrypt_sensitive_value("device_auth.device_key", secret)
            if encrypted != secret:
                device_auth["device_key"] = encrypted
                changed = True

        puter_ai = self.settings.get("puter_ai")
        if isinstance(puter_ai, dict) and "api_key" in puter_ai:
            secret = puter_ai.get("api_key", "")
            encrypted = self._encrypt_sensitive_value("puter_ai.api_key", secret)
            if encrypted != secret:
                puter_ai["api_key"] = encrypted
                changed = True

        return changed
    
    def load_settings(self):
        """Load settings from file"""
        migrated = False
        try:
            if self.settings_file.exists():
                self._settings_file_existed_on_load = True
                raw_text = ""
                try:
                    raw_text = self.settings_file.read_text(encoding="utf-8")
                except Exception:
                    with open(self.settings_file, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                header_lines, json_text = self._split_settings_text(raw_text)
                self._settings_file_header_lines = header_lines
                self._has_rc2_header = self._header_has_token(header_lines, self.RC2_HEADER_TOKEN)
                self.settings = json.loads(json_text)
                migrated = self._migrate_sensitive_settings()
                self._needs_rc2_whats_new = (not self._has_rc2_header)
            else:
                # Create default settings
                self._settings_file_existed_on_load = False
                self.settings = self._get_default_settings()
                self.save_settings()
                self._needs_rc2_whats_new = False
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.settings = self._get_default_settings()
            self._settings_file_existed_on_load = False
            self._needs_rc2_whats_new = False

        try:
            changed = False
            ai_settings = self.settings.get("ai_settings", {}) if isinstance(self.settings, dict) else {}
            if not isinstance(ai_settings, dict):
                ai_settings = {}
                changed = True
            if "allow_internet" not in ai_settings:
                ai_settings["allow_internet"] = True
                changed = True
            if "allow_image_download" not in ai_settings:
                ai_settings["allow_image_download"] = True
                changed = True
            if "request_timeout_sec" not in ai_settings:
                ai_settings["request_timeout_sec"] = 600
                changed = True
            if not bool(ai_settings.get("_user_set", False)):
                if bool(ai_settings.get("allow_internet", False)) is not True:
                    ai_settings["allow_internet"] = True
                    changed = True
                if bool(ai_settings.get("allow_image_download", False)) is not True:
                    ai_settings["allow_image_download"] = True
                    changed = True
            self.settings["ai_settings"] = ai_settings
            if changed or migrated:
                try:
                    self.settings["modified_at"] = datetime.now().isoformat()
                except Exception:
                    pass
                self.save_settings()
        except Exception:
            pass
    
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                header = self._settings_file_header_lines or []
                if header:
                    fixed = []
                    for ln in header:
                        s = str(ln or "")
                        if not s.endswith("\n"):
                            s += "\n"
                        fixed.append(s)
                    f.write("".join(fixed))
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def _split_settings_text(self, raw_text: str) -> tuple[list[str], str]:
        lines = (raw_text or "").splitlines(True)
        header: list[str] = []
        i = 0
        while i < len(lines):
            ln = lines[i]
            s = str(ln or "")
            stripped = s.strip()
            if not stripped:
                header.append(s)
                i += 1
                continue
            if stripped.startswith("//") or stripped.startswith("#"):
                header.append(s)
                i += 1
                continue
            break
        json_text = "".join(lines[i:]).strip()
        return header, json_text

    def _header_has_token(self, header_lines: list[str], token: str) -> bool:
        t = str(token or "").strip().lower()
        if not t:
            return False
        for ln in header_lines or []:
            if t in str(ln or "").lower():
                return True
        return False

    def needs_rc2_whats_new(self) -> bool:
        existed = bool(getattr(self, "_settings_file_existed_on_load", False))
        return existed and bool(getattr(self, "_needs_rc2_whats_new", False))

    @property
    def settings_file_existed(self) -> bool:
        """True if settings.json already existed when SettingsManager was initialized."""
        return bool(getattr(self, "_settings_file_existed_on_load", False))

    def should_run_first_time_flow(self) -> bool:
        """True only for a genuinely new install with no pre-existing settings file."""
        existed = bool(getattr(self, "_settings_file_existed_on_load", False))
        if existed:
            return False
        try:
            return bool(self.get("first_run", True))
        except Exception:
            return True

    def ensure_rc2_header(self):
        try:
            if not self.settings_file.exists():
                return
        except Exception:
            return
        if bool(getattr(self, "_has_rc2_header", False)):
            return
        header = list(getattr(self, "_settings_file_header_lines", []) or [])
        if not self._header_has_token(header, self.RC2_HEADER_TOKEN):
            header.insert(0, self.RC2_HEADER_LINE)
        self._settings_file_header_lines = header
        self._has_rc2_header = True
        self._needs_rc2_whats_new = False
        self.save_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings"""
        return {
            "app_language": "en",
            "theme": "light",
            "brand_color": "#10B981",
            "first_run": True,
            "intro_credits_shown": False,
            "auto_save": True,
            "auto_save_interval": 300,  # 5 minutes
            "notifications": {
                "system_enabled": True,
                "only_when_background": False
            },
            "accessibility": {
                "ui_scale": 100,
                "high_contrast": False,
                "reduce_motion": False
            },
            "recent_projects": [],
            "max_recent_projects": 10,
            "ai_settings": {
                "allow_internet": True,
                "allow_image_download": True,
                "request_timeout_sec": 600,
                "server_base_url": "",
                "_user_set": False
            },
            "device_auth": {
                "device_key": "",
                "device_id": "",
                "machine_fingerprint": "",
                "last_bound_at": ""
            },
            "puter_ai": {
                "api_key": "",
                "enabled": True
            },
            "ppt_addin": {
                "auto_install_on_new_machine": True,
                "vsto_display_name": "EduPlay PowerPoint Add-in",
                "vsto_msi_filename": "EduPlayPowerPointAddin.msi",
                "installed_once": False,
                "version": "",
                "auto_seed_trusted_slides": True,
                "trusted_seed_done": False,
                "auto_seed_from_powerpoint_mru": True,
                "powerpoint_mru_poll_sec": 30,
                "last_mru_source": "",
                "mru_open_set_limit": 3,
                "trusted_cache_max_files": 3,
                "trusted_cache_max_file_mb": 0,
                "trusted_cache_use_hardlink": True,
                "trusted_cache_cleanup_mode": "mru_only"
            },
            "editor_settings": {
                "font_size": 12,
                "font_family": "Times New Roman",
                "show_line_numbers": True,
                "auto_complete": True,
                "spell_check": True
            },
            "game_defaults": {
                "quiz_time_per_question": 30,
                "fishing_speed": 5,
                "memory_flip_delay": 1000,
                "show_explanations": True,
                "randomize_questions": True,
                "points_per_question": 10,
                "auto_points_enabled": False,
                "time_limit_enabled": True,
                "cute_effects": True
            },
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat()
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value by key (supports dot notation)"""
        keys = key.split('.')
        value = self.settings
        
        try:
            for k in keys:
                value = value[k]
            if self._is_sensitive_path(key):
                return self._decrypt_sensitive_value(key, value)
            return self._public_value_for_key(key, value)
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Set setting value by key (supports dot notation)"""
        keys = key.split('.')
        settings = self.settings
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]
        
        # Set the value
        if self._is_sensitive_path(key):
            value = self._encrypt_sensitive_value(key, value)
        settings[keys[-1]] = value
        self._migrate_sensitive_settings()
        self.settings["modified_at"] = datetime.now().isoformat()
        self.save_settings()
    
    def get_api_key(self, service: str) -> str:
        """Get API key for a service"""
        val = self.get(f"api_keys.{service}", "")
        if val:
            # Strict sanitization
            import re
            return re.sub(r'[^a-zA-Z0-9_\-\.]', '', str(val))
        return ""
    
    def get_api_key_pool(self, service: str) -> list[str]:
        try:
            raw = self.get(f"api_keys_pool.{service}", [])
        except Exception:
            raw = []
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        try:
            import re
            for v in raw:
                s = re.sub(r'[^a-zA-Z0-9_\-\.]', '', str(v or ""))
                if s.strip():
                    out.append(s.strip())
        except Exception:
            for v in raw:
                try:
                    s2 = str(v or "").strip()
                except Exception:
                    s2 = ""
                if s2:
                    out.append(s2)
        return out

    def set_api_key(self, service: str, api_key: str):
        """Set API key for a service"""
        if api_key:
            # Strict sanitization
            import re
            api_key = re.sub(r'[^a-zA-Z0-9_\-\.]', '', str(api_key))
        self.set(f"api_keys.{service}", api_key)

    def set_api_key_pool(self, service: str, api_keys: list[str]):
        items: list[str] = []
        try:
            import re
            for k in api_keys or []:
                s = re.sub(r'[^a-zA-Z0-9_\-\.]', '', str(k or ""))
                if s.strip():
                    items.append(s.strip())
        except Exception:
            for k in api_keys or []:
                try:
                    s2 = str(k or "").strip()
                except Exception:
                    s2 = ""
                if s2:
                    items.append(s2)
        self.set(f"api_keys_pool.{service}", items)
    
    def has_api_key(self, service: str) -> bool:
        """Check if API key exists for a service"""
        key = self.get_api_key(service)
        if key and key.strip():
            return True
        try:
            pool = self.get_api_key_pool(service)
            if pool:
                return True
        except Exception:
            pass
        try:
            env_map = {
                "google_gemini": ["EDUPLAY_GEMINI_API_KEY", "EDUPLAY_GEMINI_FREE_KEY"],
                "openai": ["OPENAI_API_KEY"],
                "groq": ["GROQ_API_KEY", "EDUPLAY_GROQ_API_KEY", "GROQ_API_KEYS", "EDUPLAY_GROQ_API_KEYS"],
            }
            candidates = env_map.get(service, [])
            for var in candidates:
                val = os.getenv(var, '')
                if val and val.strip():
                    return True
        except Exception:
            pass
        return False
    
    def get_ai_settings(self) -> Dict[str, Any]:
        """Get AI settings"""
        return self.get("ai_settings", {})
    
    def set_ai_settings(self, settings: Dict[str, Any]):
        """Set AI settings"""
        self.set("ai_settings", settings)
    
    def get_language(self) -> str:
        """Get application language"""
        return self.get("app_language", "en")
    
    def set_language(self, language: str):
        """Set application language"""
        self.set("app_language", language)
        try:
            from eduplay.core.i18n import I18n
            I18n.set_locale(language)
        except Exception:
            pass
    
    def get_theme(self) -> str:
        """Get application theme"""
        return self.get("theme", "light")
    
    def set_theme(self, theme: str):
        """Set application theme"""
        self.set("theme", theme)
    
    def add_recent_project(self, project_id: str, project_name: str):
        """Add project to recent projects list"""
        recent = self.get("recent_projects", [])
        
        # Remove if already exists
        recent = [p for p in recent if p.get("id") != project_id]
        
        # Add to beginning
        recent.insert(0, {
            "id": project_id,
            "name": project_name,
            "opened_at": datetime.now().isoformat()
        })
        
        # Keep only max items
        max_recent = self.get("max_recent_projects", 10)
        recent = recent[:max_recent]
        
        self.set("recent_projects", recent)
    
    def get_recent_projects(self) -> list:
        """Get recent projects list"""
        return self.get("recent_projects", [])
    
    def get_editor_settings(self) -> Dict[str, Any]:
        """Get editor settings"""
        return self.get("editor_settings", {})
    
    def set_editor_settings(self, settings: Dict[str, Any]):
        """Set editor settings"""
        self.set("editor_settings", settings)

    def get_accessibility_settings(self) -> Dict[str, Any]:
        raw = self.get("accessibility", {}) or {}
        if not isinstance(raw, dict):
            raw = {}
        return {
            "ui_scale": int(raw.get("ui_scale", 100) or 100),
            "high_contrast": bool(raw.get("high_contrast", False)),
            "reduce_motion": bool(raw.get("reduce_motion", False)),
        }

    def set_accessibility_settings(self, settings: Dict[str, Any]):
        current = self.get_accessibility_settings()
        if isinstance(settings, dict):
            current.update(settings)
        try:
            current["ui_scale"] = max(90, min(150, int(current.get("ui_scale", 100) or 100)))
        except Exception:
            current["ui_scale"] = 100
        current["high_contrast"] = bool(current.get("high_contrast", False))
        current["reduce_motion"] = bool(current.get("reduce_motion", False))
        self.set("accessibility", current)
    
    def get_game_defaults(self) -> Dict[str, Any]:
        """Get game default settings"""
        return self.get("game_defaults", {})
    
    def set_game_defaults(self, settings: Dict[str, Any]):
        """Set game default settings"""
        self.set("game_defaults", settings)
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self._get_default_settings()
        self.save_settings()
    
    def export_settings(self, file_path: str):
        """Export settings to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error exporting settings: {e}")
    
    def import_settings(self, file_path: str):
        """Import settings from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # Merge with current settings
            self.settings.update(imported_settings)
            self._migrate_sensitive_settings()
            self.settings["modified_at"] = datetime.now().isoformat()
            self.save_settings()
            
        except Exception as e:
            print(f"Error importing settings: {e}")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings"""
        return self.settings.copy()
    
    def validate_api_key(self, service: str, api_key: str) -> bool:
        """Validate API key format (basic validation)"""
        if not api_key or not api_key.strip():
            return False
        
        # Basic validation for different services
        if service == "google_gemini":
            # Google Gemini API keys typically start with "AIza"
            return api_key.startswith("AIza") and len(api_key) > 30
        elif service == "openai":
            # OpenAI API keys typically start with "sk-"
            return api_key.startswith("sk-") and len(api_key) > 20
        elif service == "groq":
            return api_key.startswith("gsk_") and len(api_key) > 20
        else:
            # Generic validation - non-empty and reasonable length
            return len(api_key.strip()) > 10
