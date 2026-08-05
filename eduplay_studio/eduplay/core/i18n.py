from pathlib import Path
import json

from eduplay.core.asset_loader import load_asset_text

class I18n:
    _cache = {}
    _loaded = set()
    locale = 'vi'

    @classmethod
    def set_locale(cls, lang: str):
        cls.locale = lang
        cls.load(lang)

    @classmethod
    def _base_dir(cls):
        return Path(__file__).parent.parent / "resources" / "i18n"

    @classmethod
    def load(cls, lang: str):
        if lang in cls._loaded:
            return
        try:
            file = cls._base_dir() / f"{lang}.json"
            if file.exists():
                rel_path = f"eduplay/resources/i18n/{lang}.json"
                cls._cache[lang] = json.loads(load_asset_text(rel_path))
                cls._loaded.add(lang)
        except Exception:
            pass

    @classmethod
    def t(cls, key: str, lang: str = None, **kwargs) -> str:
        if lang is None:
            lang = cls.locale
        if lang not in cls._loaded:
            cls.load(lang)
        if 'en' not in cls._loaded:
            cls.load('en')
        data = cls._cache.get(lang, {})
        val = data.get(key)
        if val is None:
             val = cls._cache.get('en', {}).get(key, key)
        
        if isinstance(val, str) and kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val
"""
Nguyen-Thanh-Tan ¬_¬
"""
