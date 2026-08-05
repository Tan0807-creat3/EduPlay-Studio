"""
PathResolver — Single source of truth for all EduPlay file-system paths.

Consolidates Documents, Settings, Projects, Cache, PublishCache, LocalAppData,
TrustedSlides and VSTO add-in paths so every module resolves them the same way,
including machines with OneDrive redirection or non-standard profiles.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional


class PathResolver:
    """Resolves EduPlay paths consistently across the application."""

    APP_NAME = "EduPlay"
    SETTINGS_SUBDIR = "Settings"
    PROJECTS_SUBDIR = "Projects"
    PUBLISH_CACHE_SUBDIR = "PublishCache"
    ADDIN_DIRNAME = "EduPlayPowerPointAddin"
    RUNTIME_CACHE_DIRNAME = "runtime_cache"
    PREVIEW_SUBDIR = "eduplay_preview_files"
    TRUSTED_SLIDES_SUBDIR = "TrustedSlides"
    ASSET_CACHE_DIRNAME = "EduPlayStudio"

    # ── Documents ──────────────────────────────────────────────────────

    @staticmethod
    def resolve_documents() -> Path:
        """Return the real Windows Documents folder, respecting OneDrive redirection.

        Falls back to Path.home()/Documents, then USERPROFILE/HOME/Documents,
        and finally cwd/Documents if everything else fails.
        """
        if sys.platform == "win32":
            try:
                import ctypes

                buf = ctypes.create_unicode_buffer(32768)
                # CSIDL_PERSONAL = 5 → user's Documents, respects redirection
                if ctypes.windll.shell32.SHGetFolderPathW(
                    None, 5, None, 0, buf
                ) == 0:
                    resolved = str(buf.value or "").strip()
                    if resolved:
                        return Path(resolved)
            except Exception:
                pass
        try:
            return Path.home() / "Documents"
        except Exception:
            user_profile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
            if user_profile:
                return Path(user_profile) / "Documents"
            return Path(os.getcwd()) / "Documents"

    # ── EduPlay root under Documents ──────────────────────────────────

    @staticmethod
    def resolve_eduplay_root() -> Path:
        """Return Documents/EduPlay."""
        return PathResolver.resolve_documents() / PathResolver.APP_NAME

    # ── Settings ──────────────────────────────────────────────────────

    @staticmethod
    def resolve_settings_dir() -> Path:
        """Return Documents/EduPlay/Settings."""
        settings_dir = PathResolver.resolve_eduplay_root() / PathResolver.SETTINGS_SUBDIR
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir

    # ── Projects ──────────────────────────────────────────────────────

    @staticmethod
    def resolve_projects_dir() -> Path:
        """Return Documents/EduPlay/Projects."""
        projects_dir = (
            PathResolver.resolve_eduplay_root() / PathResolver.PROJECTS_SUBDIR
        )
        projects_dir.mkdir(parents=True, exist_ok=True)
        return projects_dir

    # ── Publish Cache ─────────────────────────────────────────────────

    @staticmethod
    def resolve_publish_cache_dir() -> Path:
        """Return Documents/EduPlay/PublishCache."""
        cache_dir = (
            PathResolver.resolve_eduplay_root() / PathResolver.PUBLISH_CACHE_SUBDIR
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    # ── LocalAppData (per-user app data) ──────────────────────────────

    @staticmethod
    def resolve_local_app_data() -> Path:
        """Return the LOCALAPPDATA path, falling back to temp dir.

        Uses the standard Windows LOCALAPPDATA environment variable which
        points to the correct per-user AppData\\Local directory.
        """
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base)
        # Fallback: construct from USERPROFILE/HOME
        user_profile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
        if user_profile:
            return Path(user_profile) / "AppData" / "Local"
        return Path(tempfile.gettempdir())

    # ── Runtime Cache (decrypted assets) ──────────────────────────────

    @staticmethod
    def resolve_runtime_cache_dir() -> Path:
        """Return LOCALAPPDATA/EduPlayStudio/runtime_cache."""
        cache_dir = (
            PathResolver.resolve_local_app_data()
            / PathResolver.ASSET_CACHE_DIRNAME
            / PathResolver.RUNTIME_CACHE_DIRNAME
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    # ── Preview Temp Files ────────────────────────────────────────────

    @staticmethod
    def resolve_preview_dir(project_id: str) -> Path:
        """Return a per-project preview directory under the system temp folder.

        Uses tempfile.gettempdir() which is the correct cross-platform temp
        location, and sanitises the project_id to avoid path traversal.
        """
        safe_id = "".join(
            c for c in str(project_id) if c.isalnum() or c in ("-", "_")
        )
        if not safe_id:
            safe_id = "unknown"
        preview_dir = (
            Path(tempfile.gettempdir())
            / PathResolver.PREVIEW_SUBDIR
            / safe_id
        )
        preview_dir.mkdir(parents=True, exist_ok=True)
        return preview_dir

    # ── VSTO Add-in ───────────────────────────────────────────────────

    @staticmethod
    def resolve_addin_dir() -> Path:
        """Return LOCALAPPDATA/EduPlayPowerPointAddin."""
        addin_dir = (
            PathResolver.resolve_local_app_data() / PathResolver.ADDIN_DIRNAME
        )
        addin_dir.mkdir(parents=True, exist_ok=True)
        return addin_dir

    # ── Trusted Slides ────────────────────────────────────────────────

    @staticmethod
    def resolve_trusted_slides_dir() -> Path:
        """Return LOCALAPPDATA/EduPlayPowerPointAddin/TrustedSlides."""
        trusted_dir = (
            PathResolver.resolve_addin_dir() / PathResolver.TRUSTED_SLIDES_SUBDIR
        )
        trusted_dir.mkdir(parents=True, exist_ok=True)
        return trusted_dir

    # ── Asset DB ──────────────────────────────────────────────────────

    @staticmethod
    def resolve_asset_db_path() -> Path:
        """Return LOCALAPPDATA/EduPlayStudio/eduplay.db."""
        db_path = (
            PathResolver.resolve_local_app_data()
            / PathResolver.ASSET_CACHE_DIRNAME
            / "eduplay.db"
        )
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    # ── AI Token Cache ────────────────────────────────────────────────

    @staticmethod
    def resolve_ai_token_cache_path() -> Path:
        """Return Documents/EduPlay/Settings/ai_proxy_token.txt."""
        return PathResolver.resolve_settings_dir() / "ai_proxy_token.txt"
