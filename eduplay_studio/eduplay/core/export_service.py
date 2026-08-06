"""
Export Service - Handles HTML and native game exports
"""

import os
import json
import shutil
import zipfile
import base64
import hashlib
import mimetypes
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote
from jinja2 import Template
from eduplay.core.i18n import I18n
from eduplay.core.asset_bundler import AssetBundler
from eduplay.core.asset_loader import load_asset_text, load_asset_bytes, get_asset_path
try:
    from eduplay.core.template_merger import MillionaireTemplateMerger
except Exception:
    MillionaireTemplateMerger = None

class ExportService:
    """Service for exporting projects to various formats"""

    LIBRARY_ASSET_PACK_KEYS = {
        "classic": "5c86aa11079c72167599af103a954f3515faea6443bb8e3482b2803fe3c89ce9",
        "fishing": "ba805ea048fafe69620d391ede85e09218c128651c55464abb8462256624ff25",
        "millionaire": "845a60a2515f53b2a0257d057ec987273a24de50f0a32b7bd345c2ccd8796597",
    }
    
    def __init__(self):
        """Initialize export service"""
        self.templates_dir = Path(__file__).parent.parent.parent / "assets_bundle" / "templates"
        self.assets_dir = Path(__file__).parent.parent.parent / "assets_bundle"

    def _emit_publish_progress(self, progress_callback, payload: Dict) -> None:
        if not progress_callback:
            return
        safe_payload = dict(payload or {})
        try:
            progress_callback(safe_payload)
            return
        except TypeError:
            pass
        except Exception:
            return
        if safe_payload.get("stage") == "uploading":
            try:
                progress_callback(int(safe_payload.get("current") or 0), int(safe_payload.get("total") or 0))
                return
            except Exception:
                return
        message = str(safe_payload.get("message") or "").strip()
        if not message:
            return
        try:
            progress_callback(message)
        except Exception:
            pass

    def _decode_service_account_info(self, service_account_b64: str) -> Dict:
        try:
            normalized = self._normalize_service_account_payload(service_account_b64)
            if not normalized:
                return {}
            raw = base64.b64decode(normalized).decode("utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _normalize_service_account_payload(self, payload: str) -> str:
        text = str(payload or "").strip()
        if not text:
            return ""
        if text.startswith("{"):
            try:
                json.loads(text)
                return base64.b64encode(text.encode("utf-8")).decode("utf-8")
            except Exception:
                return ""
        try:
            raw = base64.b64decode(text).decode("utf-8")
            json.loads(raw)
            return text
        except Exception:
            return ""

    def _firebase_service_account_fernet_key(self) -> bytes:
        env_key = str(os.environ.get("EDUPLAY_FIREBASE_SERVICE_ACCOUNT_FERNET_KEY") or "").strip()
        if env_key:
            return env_key.encode("utf-8")
        # Obfuscation only: bundled builds still need a deterministic runtime key.
        seed = "".join(
            (
                "eduplay::desktop::firebase::",
                "service-account::bundle::",
                "fbsvc::d48fafeb3b::",
                "publish::runtime::v1",
            )
        ).encode("utf-8")
        return base64.urlsafe_b64encode(hashlib.sha256(seed).digest())

    def _decrypt_service_account_fernet(self, token_text: str) -> str:
        text = str(token_text or "").strip()
        if not text:
            return ""
        try:
            from cryptography.fernet import Fernet

            plain = Fernet(self._firebase_service_account_fernet_key()).decrypt(text.encode("utf-8"))
            return plain.decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    def _firebase_storage_bucket_candidates(self, project_id: str = "", service_account: Optional[Dict] = None) -> List[str]:
        candidates = []

        def _add(value) -> None:
            bucket = str(value or "").strip()
            if bucket and bucket not in candidates:
                candidates.append(bucket)

        try:
            _add(os.environ.get("EDUPLAY_FIREBASE_STORAGE_BUCKET"))
        except Exception:
            pass

        service_account = service_account or {}
        if isinstance(service_account, dict):
            _add(service_account.get("storage_bucket"))
            _add(service_account.get("storageBucket"))

        project_ids = []
        for value in (
            (service_account or {}).get("project_id"),
            os.environ.get("EDUPLAY_FIREBASE_PROJECT_ID"),
        ):
            pid = str(value or "").strip()
            if pid and pid not in project_ids:
                project_ids.append(pid)

        for pid in project_ids:
            _add(f"{pid}.firebasestorage.app")
            _add(f"{pid}.appspot.com")

        if not candidates:
            _add("eduplay-game.firebasestorage.app")
            _add("eduplay-game.appspot.com")
        return candidates

    def _firebase_storage_bucket(self, project_id: str = "", service_account: Optional[Dict] = None) -> str:
        buckets = self._firebase_storage_bucket_candidates(project_id=project_id, service_account=service_account)
        if buckets:
            return buckets[0]
        return ""

    def _firebase_storage_download_url(self, bucket_name: str, object_name: str, token: str) -> str:
        return (
            f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/"
            f"{quote(str(object_name or ''), safe='')}?alt=media&token={quote(str(token or ''), safe='')}"
        )

    def _safe_json_dumps(self, data) -> str:
        try:
            s = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        except Exception:
            s = json.dumps(data, separators=(',', ':'))
        try:
            s = s.replace("</", "<\\/")
            s = s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        except Exception:
            pass
        return s
    
    def _resource_path(self, p: str) -> str:
        try:
            if not p:
                return ''
            if isinstance(p, str) and p.startswith('data:'):
                return p
            p = str(p).replace('file://', '')
            p = p.strip().strip('"').strip("'").replace('\\', '/')
            if os.path.isabs(p) and os.path.exists(p):
                return p
            if p.startswith('assets/'):
                rel = p[len('assets/'):]
                full = str(self.assets_dir / rel)
                if os.path.exists(full):
                    return full
            full = str(self.assets_dir / p)
            if os.path.exists(full):
                return full
            return p
        except Exception:
            return str(p or '')
    
    def _file_to_base64(self, file_path: str) -> str:
        """Convert a file to Base64 string"""
        try:
            if isinstance(file_path, str) and file_path.startswith('data:'):
                return file_path
            if isinstance(file_path, str) and file_path.startswith('file://'):
                file_path = file_path.replace('file://', '')
            if isinstance(file_path, str):
                file_path = file_path.strip().strip('"').strip("'")
            path = Path(file_path)
            if not path.exists():
                return ""
            
            with open(path, 'rb') as f:
                file_data = f.read()
                base64_data = base64.b64encode(file_data).decode('utf-8')
                mime_type, _ = mimetypes.guess_type(str(path))
                if mime_type:
                    return f"data:{mime_type};base64,{base64_data}"
                return f"data:application/octet-stream;base64,{base64_data}"
        except Exception as e:
            print(f"Error converting file to Base64: {e}")
            return ""

    def _inject_favicon(self, html: str) -> str:
        """Inject EduPlay favicon (icon.ico) as base64 data URL into HTML head"""
        try:
            icon_root = Path(__file__).parent.parent.parent / "eduplay" / "resources" / "icons" / "icon.ico"
            icon_data = self._file_to_base64(str(icon_root))
            if not icon_data:
                icon_root = Path(__file__).parent.parent.parent / "eduplay" / "resources" / "icons" / "icon.png"
                icon_data = self._file_to_base64(str(icon_root))
            if not icon_data:
                return html
            favicon_tag = f'<link rel="icon" type="image/x-icon" href="{icon_data}">'
            if '</head>' in html:
                import re as _re
                html = _re.sub(r'<link[^>]+rel=["\'](?:shortcut\\s+)?icon["\'][^>]*>\\s*', '', html, flags=_re.IGNORECASE)
                html = html.replace('</head>', favicon_tag + '\n</head>')
            else:
                html = favicon_tag + '\n' + html
            return html
        except Exception:
            return html
    
    def _bundle_media_files(self, project_data: Dict) -> Dict:
        """Bundle media files as Base64 in project data"""
        bundled_data = project_data.copy()
        # Normalize top-level game_type from game_config to ensure correct preview variant
        try:
            cfg_gt = str((bundled_data.get('game_config', {}) or {}).get('game_type') or '').lower()
            top_gt = str(bundled_data.get('game_type') or '').lower()
            name_gt = str(bundled_data.get('name') or '').lower()
            if (
                ('triệu phú' in cfg_gt) or ('millionaire' in cfg_gt) or ('ai la trieu phu' in cfg_gt) or ('altp' in cfg_gt) or
                ('triệu phú' in top_gt) or ('millionaire' in top_gt) or ('ai la trieu phu' in top_gt) or ('altp' in top_gt) or
                ('triệu phú' in name_gt) or ('millionaire' in name_gt) or ('ai la trieu phu' in name_gt) or ('altp' in name_gt)
            ):
                bundled_data['game_type'] = 'quiz_millionaire'
        except Exception:
            pass
        try:
            cfg = bundled_data.get('game_config', {}) or {}
            cfg_gt = str(cfg.get('game_type') or '').lower()
            top_gt = str(bundled_data.get('game_type') or '').lower()
            fishing_markers = ('fishing', 'fish', 'câu cá', 'cau ca', 'bắt cá', 'bat ca')
            if (top_gt == 'fishing') or (not top_gt and any(token in cfg_gt for token in fishing_markers)):
                bundled_data['game_type'] = 'fishing'
        except Exception:
            pass
        
        # Process questions for media references
        if 'questions' in bundled_data:
            for question in bundled_data['questions']:
                # Bundle question images
                if 'image' in question and question['image']:
                    image_path = question['image']
                    if os.path.exists(image_path):
                        question['image_base64'] = self._file_to_base64(image_path)
                
                # Bundle question audio
                if 'audio' in question and question['audio']:
                    audio_path = question['audio']
                    if os.path.exists(audio_path):
                        question['audio_base64'] = self._file_to_base64(audio_path)
                
                # Bundle option images for multiple choice
                if 'options' in question and 'option_images' in question:
                    bundled_option_images = []
                    for img_path in question['option_images']:
                        if img_path and os.path.exists(img_path):
                            bundled_option_images.append(self._file_to_base64(img_path))
                        else:
                            bundled_option_images.append("")
                    question['option_images_base64'] = bundled_option_images
                # Normalize schema for quiz questions
                try:
                    raw_type = question.get('type') or question.get('question_type') or question.get('q_type') or question.get('kind') or ''
                    rt = str(raw_type).strip().lower().replace(' ', '_').replace('-', '_').replace('/', '_')
                    if rt in ('multiple_choice', 'multiple', 'mcq', 'choice', 'quiz', 'trac_nghiem', 'trắc_nghiệm'):
                        question['type'] = 'multiple_choice'
                    elif rt in ('true_false', 'truefalse', 'true__false', 'true-false', 'boolean', 'tf', 'dung_sai', 'đúng_sai'):
                        question['type'] = 'true_false'
                    elif rt in ('fill_blank', 'fillblank', 'cloze', 'dien_cho_trong', 'điền_chỗ_trống'):
                        question['type'] = 'fill_blank'
                    elif rt in ('short_answer', 'shortanswer', 'essay', 'tu_luan', 'tự_luận'):
                        question['type'] = 'short_answer'
                    elif rt in ('matching', 'match', 'pairing', 'ghép_đôi', 'ghep_doi'):
                        question['type'] = 'matching'
                    else:
                        if question.get('pairs') or question.get('match_pairs'):
                            question['type'] = 'matching'
                        elif isinstance(question.get('correct_answer'), bool) or isinstance(question.get('correctAnswer'), bool):
                            question['type'] = 'true_false'
                        else:
                            question['type'] = 'multiple_choice'
                    # Map camelCase to snake_case
                    if question.get('correctAnswer') is not None and question.get('correct_answer') is None:
                        question['correct_answer'] = question.get('correctAnswer')
                    if question.get('type') == 'true_false':
                        ca = question.get('correct_answer')
                        if isinstance(ca, bool):
                            question['correct_answer'] = ca
                        elif isinstance(ca, (int, float)):
                            question['correct_answer'] = bool(ca)
                        else:
                            s = str(ca if ca is not None else '').strip().lower()
                            if s in ('true', 'đúng', 'dung', 'a', '1', 'yes', 'y'):
                                question['correct_answer'] = True
                            elif s in ('false', 'sai', 'b', '0', 'no', 'n'):
                                question['correct_answer'] = False
                    # Ensure options array exists for multiple choice
                    if question['type'] == 'multiple_choice' and not question.get('options'):
                        opts = question.get('answers') or question.get('choices') or []
                        # Map common teacher-bank variants
                        if not opts:
                            variants = [
                                ('option_a','option_b','option_c','option_d'),
                                ('answerA','answerB','answerC','answerD'),
                                ('A','B','C','D'),
                                ('option1','option2','option3','option4'),
                                ('pa','pb','pc','pd'),
                                ('ansA','ansB','ansC','ansD')
                            ]
                            for keys in variants:
                                arr = [question.get(keys[0]), question.get(keys[1]), question.get(keys[2]), question.get(keys[3])]
                                arr = [x for x in arr if x is not None]
                                if arr and len(arr) >= 2:
                                    opts = arr
                                    break
                        if isinstance(opts, list) and opts:
                            question['options'] = opts
                        # OpenTDB-style fallback
                        if not question.get('options'):
                            try:
                                inc = list(question.get('incorrect_answers') or [])
                                ca = question.get('correct_answer')
                                if ca is None:
                                    ca = question.get('correctAnswer')
                                base = []
                                if ca is not None:
                                    base.append(ca)
                                base.extend(inc)
                                import random as _r
                                _r.shuffle(base)
                                cand = [str(x) for x in base if str(x).strip()][:4]
                                if len(cand) >= 2:
                                    question['options'] = cand
                                    # resolve correct index
                                    try:
                                        question['correct_answer'] = cand.index(str(ca))
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    if question.get('type') == 'multiple_choice' and isinstance(question.get('options'), list):
                        opts = question.get('options') or []
                        if opts and isinstance(opts[0], dict):
                            texts = []
                            correct_idx = None
                            for i, o in enumerate(opts):
                                if not isinstance(o, dict):
                                    texts.append(str(o))
                                    continue
                                texts.append(str(o.get('text', '') if o.get('text', '') is not None else ''))
                                try:
                                    if correct_idx is None and bool(o.get('correct', False)):
                                        correct_idx = i
                                except Exception:
                                    pass
                            question['options'] = texts
                            if correct_idx is not None and question.get('correct_answer') is None:
                                question['correct_answer'] = int(correct_idx)
                except Exception:
                    pass
        
        # Bundle global media files
        if 'media_files' in bundled_data:
            bundled_media_files = []
            for media_file in bundled_data['media_files']:
                if 'path' in media_file and os.path.exists(media_file['path']):
                    bundled_file = media_file.copy()
                    bundled_file['base64_data'] = self._file_to_base64(media_file['path'])
                    bundled_media_files.append(bundled_file)
            bundled_data['media_files'] = bundled_media_files
        
        # Bundle game_config assets (fish sprites, sounds)
        game_config = bundled_data.get('game_config', {})
        
        fish_objects = game_config.get('fish_objects', [])
        try:
            gt_top = str(project_data.get('game_type') or '').lower()
        except Exception:
            gt_top = ''
        gt_cfg = str(game_config.get('game_type') or '').lower()
        base_text = gt_cfg
        is_fishing_mode = (gt_top == 'fishing') or (not gt_top and any(x in base_text for x in ('fishing', 'fish', 'câu cá', 'cau ca')))
        if not fish_objects and is_fishing_mode:
            try:
                fish_types = ['blue', 'green', 'pink', 'orange']
                fish_objects = [
                    {
                        'sprite': f'assets/kenney_platformer-kit/PNG/Default/fish_{t}.png',
                        'wrong_sprite': f'assets/kenney_platformer-kit/PNG/Default/fish_{t}_skeleton.png',
                        'sound': 'assets/sound/click.wav'
                    } for t in fish_types
                ]
                game_config['fish_objects'] = fish_objects
            except Exception:
                pass
        bundled_fish_objects = []
        
        def resolve_asset_path(p: str) -> str:
            if not p:
                return ''
            if isinstance(p, str) and p.startswith('data:'):
                return p
            p = p.replace('file://', '')
            p = p.strip().strip('"').strip("'")
            p = p.replace('\\', '/')
            # Check if it's an absolute path first
            if os.path.isabs(p) and os.path.exists(p):
                return p
            # Check if it's a path relative to assets
            if p.startswith('assets/'):
                rel = p[len('assets/'):]
                full = str(self.assets_dir / rel)
                if os.path.exists(full):
                    return full
            # Check if it's a direct file in assets
            full = str(self.assets_dir / p)
            if os.path.exists(full):
                return full
            return p
        
        # Process fish objects
        for fish in fish_objects:
            f = dict(fish)
            sprite_path = f.get('sprite')
            wrong_path = f.get('wrong_sprite')
            sound_path = f.get('sound')
            
            # Resolve and bundle sprite
            if sprite_path:
                sp = resolve_asset_path(sprite_path)
                if isinstance(sp, str) and sp.startswith('data:'):
                    f['sprite_base64'] = sp
                elif os.path.exists(sp):
                    f['sprite_base64'] = self._file_to_base64(sp)
                else:
                    print(f"Warning: Fish sprite not found: {sprite_path}")
            
            # Resolve and bundle wrong sprite (skeleton)
            if wrong_path:
                wp = resolve_asset_path(wrong_path)
                if isinstance(wp, str) and wp.startswith('data:'):
                    f['wrong_sprite_base64'] = wp
                elif os.path.exists(wp):
                    f['wrong_sprite_base64'] = self._file_to_base64(wp)
                else:
                    print(f"Warning: Wrong fish sprite not found: {wrong_path}")
            
            # Resolve and bundle sound
            if sound_path:
                sd = resolve_asset_path(sound_path)
                if isinstance(sd, str) and sd.startswith('data:'):
                    f['sound_base64'] = sd
                elif os.path.exists(sd):
                    f['sound_base64'] = self._file_to_base64(sd)
                else:
                    print(f"Warning: Fish sound not found: {sound_path}")
            
            bundled_fish_objects.append(f)
        
        game_config['fish_objects'] = bundled_fish_objects
        
        # Bundle global sounds/music
        def bundle_cfg_sound(key: str, out_key: str):
            p = game_config.get(key)
            if not p:
                # Fallback to default bundled sounds in assets/sound
                defaults = {
                    'correct_sound': self.assets_dir / 'sound' / 'correct.wav',
                    'wrong_sound': self.assets_dir / 'sound' / 'wrong.wav',
                    'click_sound': self.assets_dir / 'sound' / 'click.wav',
                    'background_music': self.assets_dir / 'sound' / 'background.mp3'
                }
                df = defaults.get(key)
                if df and df.exists():
                    try:
                        game_config[out_key] = self._file_to_base64(str(df))
                    except Exception:
                        pass
                return
                
            p = p.replace('\\', '/')
            full_path = self._resource_path(p)
            
            if os.path.exists(full_path):
                game_config[out_key] = self._file_to_base64(full_path)
            else:
                try:
                    import os as _os
                    if _os.environ.get('EDUPLAY_VERBOSE_AUDIO', '') == '1':
                        print(f"Warning: Sound file not found: {p}")
                except Exception:
                    pass
                # Compatibility mapping for legacy Millionaire paths (Who-wants-to-be-a-millionaire)
                try:
                    legacy = p.replace('\\', '/')
                    rep = None
                    if 'Who-wants-to-be-a-millionaire' in legacy:
                        if legacy.endswith('/GoodAnswer.wav'):
                            rep = self.assets_dir / 'millionaire' / 'sounds' / 'Effects' / 'correct answer.mp3'
                        elif legacy.endswith('/BadAnswer.wav'):
                            rep = self.assets_dir / 'millionaire' / 'sounds' / 'Effects' / 'wrong answer.mp3'
                        elif legacy.endswith('/Click.wav'):
                            rep = self.assets_dir / 'sound' / 'click.wav'
                        elif legacy.endswith('/QuestionBG.wav'):
                            rep = self.assets_dir / 'millionaire' / 'sounds' / 'Music' / '0_to_1000.mp3'
                    if rep and rep.exists():
                        try:
                            game_config[out_key] = self._file_to_base64(str(rep))
                            return
                        except Exception:
                            pass
                except Exception:
                    pass
                # Provide default sound if available
                defaults = {
                    'correct_sound': self.assets_dir / 'sound' / 'correct.wav',
                    'wrong_sound': self.assets_dir / 'sound' / 'wrong.wav',
                    'click_sound': self.assets_dir / 'sound' / 'click.wav',
                    'background_music': self.assets_dir / 'sound' / 'background.mp3'
                }
                df = defaults.get(key)
                if df and df.exists():
                    try:
                        game_config[out_key] = self._file_to_base64(str(df))
                    except Exception:
                        pass
        
        # Bundle all required sounds
        bundle_cfg_sound('correct_sound', 'correct_sound_base64')
        bundle_cfg_sound('wrong_sound', 'wrong_sound_base64')
        bundle_cfg_sound('click_sound', 'click_sound_base64')
        bundle_cfg_sound('background_music', 'bgm_base64')
        try:
            if game_config.get('bgm_base64') and not game_config.get('question_bg_sound_base64'):
                game_config['question_bg_sound_base64'] = game_config['bgm_base64']
        except Exception:
            pass
        
        # Bundle background image if specified
        bg_image = game_config.get('background_image')
        if bg_image:
            bg_path = self._resource_path(bg_image)
            if os.path.exists(bg_path):
                game_config['background_image_base64'] = self._file_to_base64(bg_path)
            else:
                print(f"Warning: Background image not found: {bg_image}")



        # Bundle fishing environment assets (backgrounds and seaweed)
        try:
            default_dir = self.assets_dir / 'kenney_platformer-kit' / 'PNG' / 'Default'
            if default_dir.exists():
                def _bundle_default_pngs(names):
                    encoded = {}
                    for fn in names:
                        fp = default_dir / fn
                        if fp.exists():
                            try:
                                encoded[fn] = self._file_to_base64(str(fp))
                            except Exception:
                                pass
                    return encoded
                bg_files = [
                    'background_seaweed_a.png','background_seaweed_b.png','background_seaweed_c.png','background_seaweed_d.png',
                    'background_seaweed_e.png','background_seaweed_f.png','background_seaweed_g.png','background_seaweed_h.png',
                    'background_rock_a.png','background_rock_b.png','background_terrain.png','background_terrain_top.png'
                ]
                bgs64 = list(_bundle_default_pngs(bg_files).values())
                if bgs64:
                    game_config['backgrounds_base64'] = bgs64
                seaweed_files = [
                    'seaweed_grass_a.png','seaweed_grass_b.png',
                    'seaweed_green_a.png','seaweed_green_b.png','seaweed_green_c.png','seaweed_green_d.png',
                    'seaweed_orange_a.png','seaweed_orange_b.png',
                    'seaweed_pink_a.png','seaweed_pink_b.png','seaweed_pink_c.png','seaweed_pink_d.png'
                ]
                sw64 = list(_bundle_default_pngs(seaweed_files).values())
                if sw64:
                    game_config['seaweed_assets_base64'] = sw64
                tile_files = [
                    'terrain_sand_top_a.png','terrain_sand_top_b.png','terrain_sand_top_c.png','terrain_sand_top_d.png',
                    'terrain_sand_a.png','terrain_sand_b.png','terrain_sand_c.png','terrain_sand_d.png'
                ]
                tiles64 = list(_bundle_default_pngs(tile_files).values())
                if tiles64:
                    game_config['terrain_tiles_base64'] = tiles64
                rocks64 = list(_bundle_default_pngs(['background_rock_a.png','background_rock_b.png']).values())
                if rocks64:
                    game_config['decor_rocks_base64'] = rocks64
                rock_assets64 = list(_bundle_default_pngs(['rock_a.png', 'rock_b.png']).values())
                if rock_assets64:
                    game_config['rock_assets_base64'] = rock_assets64
                tiny_types = ['blue','green','pink','orange']
                tiny64 = []
                for t in tiny_types:
                    fp = default_dir / f'fish_{t}.png'
                    if fp.exists():
                        try:
                            tiny64.append(self._file_to_base64(str(fp)))
                        except Exception:
                            pass
                if tiny64:
                    game_config['tiny_fish_base64'] = tiny64
                scene_asset_files = [
                    'background_seaweed_a.png','background_seaweed_b.png','background_seaweed_c.png','background_seaweed_d.png',
                    'background_seaweed_e.png','background_seaweed_f.png','background_seaweed_g.png','background_seaweed_h.png',
                    'background_rock_a.png','background_rock_b.png','background_terrain.png','background_terrain_top.png',
                    'fish_blue.png','fish_green.png','fish_pink.png','fish_orange.png','fish_red.png','fish_brown.png',
                    'fish_grey.png','fish_grey_long_a.png','fish_grey_long_b.png',
                    'fish_blue_skeleton.png','fish_green_skeleton.png','fish_pink_skeleton.png','fish_orange_skeleton.png','fish_red_skeleton.png',
                    'seaweed_grass_a.png','seaweed_grass_b.png',
                    'seaweed_green_a.png','seaweed_green_b.png','seaweed_green_c.png','seaweed_green_d.png',
                    'seaweed_orange_a.png','seaweed_orange_b.png',
                    'seaweed_pink_a.png','seaweed_pink_b.png','seaweed_pink_c.png','seaweed_pink_d.png',
                    'rock_a.png','rock_b.png',
                    'terrain_sand_top_a.png','terrain_sand_top_b.png','terrain_sand_top_c.png','terrain_sand_top_d.png',
                    'terrain_sand_top_e.png','terrain_sand_top_f.png','terrain_sand_top_g.png','terrain_sand_top_h.png',
                    'terrain_sand_a.png','terrain_sand_b.png','terrain_sand_c.png','terrain_sand_d.png',
                    'terrain_dirt_a.png','terrain_dirt_b.png','terrain_dirt_c.png','terrain_dirt_d.png',
                    'terrain_dirt_top_a.png','terrain_dirt_top_b.png','terrain_dirt_top_c.png','terrain_dirt_top_d.png',
                    'terrain_dirt_top_e.png','terrain_dirt_top_f.png','terrain_dirt_top_g.png','terrain_dirt_top_h.png'
                ]
                scene_asset_map = _bundle_default_pngs(scene_asset_files)
                if scene_asset_map:
                    game_config['scene_asset_map_base64'] = scene_asset_map
        except Exception:
            pass
        
        bundled_data['game_config'] = game_config
        
        return bundled_data
    
    def _read_service_account_b64(self) -> str:
        """Return base64 of Firebase service account JSON if available without exposing secrets.
        Priority: env var EDUPLAY_FIREBASE_SERVICE_ACCOUNT_B64 -> env var Fernet -> resources .fernet -> resources .b64 -> resources .json -> empty string.
        """
        try:
            b64 = os.environ.get('EDUPLAY_FIREBASE_SERVICE_ACCOUNT_B64') or ''
            if b64:
                return self._normalize_service_account_payload(b64.strip())
            fernet_env = os.environ.get("EDUPLAY_FIREBASE_SERVICE_ACCOUNT_FERNET") or ""
            if fernet_env:
                decrypted = self._decrypt_service_account_fernet(fernet_env)
                normalized = self._normalize_service_account_payload(decrypted)
                if normalized:
                    return normalized
            res_dir = Path(__file__).parent.parent / "resources"
            fernet_path = res_dir / "firebase_service_account.fernet"
            if fernet_path.exists():
                try:
                    token = (load_asset_text('eduplay/resources/firebase_service_account.fernet') or '').strip()
                    decrypted = self._decrypt_service_account_fernet(token)
                    normalized = self._normalize_service_account_payload(decrypted)
                    if normalized:
                        return normalized
                except Exception:
                    pass
            b64_path = res_dir / "firebase_service_account.b64"
            if b64_path.exists():
                try:
                    txt = (load_asset_text('eduplay/resources/firebase_service_account.b64') or '').strip()
                    normalized = self._normalize_service_account_payload(txt)
                    if normalized:
                        return normalized
                except Exception:
                    pass
            for res_path in sorted(res_dir.glob("eduplay-game-firebase-adminsdk-fbsvc-*.json")):
                try:
                    raw = load_asset_text(f"eduplay/resources/{res_path.name}")
                    normalized = self._normalize_service_account_payload(raw)
                    if normalized:
                        return normalized
                except Exception:
                    continue
        except Exception:
            pass
        return ""

    def _slugify_publish_key(self, text: str) -> str:
        try:
            import re as _re
            import unicodedata as _ud

            t = _ud.normalize("NFKD", str(text or ""))
            t = "".join(c for c in t if not _ud.combining(c))
            t = t.lower()
            t = _re.sub(r"[^a-z0-9]+", "-", t).strip("-")
            return t or "game"
        except Exception:
            return "game"

    def _chunk_string_payload(self, text: str, chunk_size: int = 200000) -> List[str]:
        payload = str(text or "")
        if chunk_size <= 0:
            chunk_size = 200000
        return [payload[i:i + chunk_size] for i in range(0, len(payload), chunk_size)] or [""]

    def _encode_text_payload(self, raw_text: str) -> Dict:
        try:
            import gzip

            raw_bytes = str(raw_text or "").encode("utf-8")
            compressed = gzip.compress(raw_bytes, compresslevel=9)
            encoded = base64.b64encode(compressed).decode("ascii")
            return {
                "encoding": "gzip+base64",
                "encoded": encoded,
                "size_bytes": len(compressed),
                "chunks": self._chunk_string_payload(encoded),
            }
        except Exception:
            raw_bytes = str(raw_text or "").encode("utf-8")
            encoded = base64.b64encode(raw_bytes).decode("ascii")
            return {
                "encoding": "base64",
                "encoded": encoded,
                "size_bytes": len(raw_bytes),
                "chunks": self._chunk_string_payload(encoded),
            }

    def _xor_with_hex_key(self, data: bytes, key_hex: str) -> bytes:
        try:
            key_bytes = bytes.fromhex(str(key_hex or "").strip())
        except Exception:
            key_bytes = b""
        if not key_bytes:
            try:
                import hashlib

                key_bytes = hashlib.sha256(str(key_hex or "").encode("utf-8")).digest()
            except Exception:
                key_bytes = b"eduplay"
        return bytes((byte ^ key_bytes[idx % len(key_bytes)]) for idx, byte in enumerate(data or b""))

    def _stable_asset_token(self, data_uri: str) -> str:
        digest = hashlib.sha256(str(data_uri or "").encode("utf-8")).hexdigest()
        return f"__EDUPLAY_ASSET__{digest[:24]}__"

    def _resolve_library_asset_pack_profile(self, project_data: Optional[Dict] = None) -> str:
        data = dict(project_data or {})
        explicit = str(data.get("asset_pack_profile") or "").strip().lower()
        if explicit in self.LIBRARY_ASSET_PACK_KEYS:
            return explicit
        cfg = dict(data.get("game_config") or {})
        cfg_explicit = str(cfg.get("asset_pack_profile") or "").strip().lower()
        if cfg_explicit in self.LIBRARY_ASSET_PACK_KEYS:
            return cfg_explicit

        def _contains_any(text: str, markers) -> bool:
            lower = str(text or "").lower()
            return any(marker in lower for marker in markers)

        candidates = [
            str(data.get("force_variant") or ""),
            str(data.get("game_type") or ""),
            str(data.get("name") or ""),
            str(cfg.get("game_type") or ""),
            str(cfg.get("template") or ""),
        ]
        if any(_contains_any(text, ("millionaire", "triệu phú", "trieu phu", "altp")) for text in candidates):
            return "millionaire"
        if any(_contains_any(text, ("fishing", "fish", "câu cá", "cau ca", "bắt cá", "bat ca")) for text in candidates):
            return "fishing"
        return "classic"

    def _library_profile_files(self, profile: str) -> List[Path]:
        name = str(profile or "").strip().lower()
        assets_root = self.assets_dir
        if name == "fishing":
            files = list((assets_root / "kenney_platformer-kit" / "PNG" / "Default").glob("*.png"))
            files.extend((assets_root / "kenney_platformer-kit" / "sound").glob("*.mp3"))
        elif name == "millionaire":
            files = list((assets_root / "millionaire" / "images").glob("*.*"))
            files.extend((assets_root / "millionaire" / "sounds").rglob("*.mp3"))
            files.extend((assets_root / "millionaire" / "sounds").rglob("*.wav"))
        else:
            files = [
                assets_root / "sound" / "background.mp3",
                assets_root / "sound" / "background2.mp3",
                assets_root / "sound" / "click.wav",
                assets_root / "sound" / "correct.wav",
                assets_root / "sound" / "wrong.wav",
            ]
        seen = set()
        normalized = []
        for item in files:
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

    def _read_library_asset_pack_manifest(self, profile: str, database_url: str, service_account_b64: str = "", service_account_info: Optional[Dict] = None) -> Dict:
        profile_name = str(profile or "").strip().lower()
        if not profile_name or not database_url:
            return {}
        try:
            import firebase_admin
            from firebase_admin import credentials, db

            token = str(service_account_b64 or "").strip()
            if token:
                info = service_account_info or self._decode_service_account_info(token)
                cred = credentials.Certificate(info)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred, {"databaseURL": database_url})
                data = db.reference(f"/asset_pack_libraries/{profile_name}").get()
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        try:
            import requests

            response = requests.get(database_url.rstrip("/") + f"/asset_pack_libraries/{profile_name}.json")
            body = str(getattr(response, "text", "") or "").strip()
            if 200 <= int(getattr(response, "status_code", 500)) < 300 and body and body != "null":
                payload = json.loads(body)
                if isinstance(payload, dict):
                    return payload
        except Exception:
            pass
        return {}

    def _normalize_library_manifest(self, profile: str, manifest: Optional[Dict] = None) -> Dict:
        profile_name = str(profile or "").strip().lower()
        data = dict(manifest or {})
        versions = {}
        raw_versions = data.get("versions")
        if isinstance(raw_versions, dict):
            for version_key, payload in raw_versions.items():
                entry = dict(payload or {})
                key = str(entry.get("key") or version_key or "").strip()
                if not key:
                    continue
                versions[key] = {
                    "key": key,
                    "profile": str(entry.get("profile") or profile_name),
                    "asset_count": int(entry.get("asset_count") or 0),
                    "total_chunks": int(entry.get("total_chunks") or 0),
                    "encoding": str(entry.get("encoding") or ""),
                    "library": True,
                    "never_delete": True,
                    "pinned": True,
                    "updated_at": int(entry.get("updated_at") or 0),
                    "hash": str(entry.get("hash") or key),
                }

        primary_key = str(data.get("key") or "").strip()
        latest_key = str(data.get("latest_key") or "").strip()
        fallback_keys = [primary_key, latest_key]
        known_keys = data.get("known_keys")
        if isinstance(known_keys, dict):
            fallback_keys.extend(str(item).strip() for item, enabled in known_keys.items() if enabled)

        for key in fallback_keys:
            if not key or key in versions:
                continue
            versions[key] = {
                "key": key,
                "profile": profile_name,
                "asset_count": int(data.get("asset_count") or 0),
                "total_chunks": int(data.get("total_chunks") or 0),
                "encoding": str(data.get("encoding") or ""),
                "library": True,
                "never_delete": True,
                "pinned": True,
                "updated_at": int(data.get("updated_at") or 0),
                "hash": str(data.get("hash") or key),
            }

        if not latest_key and versions:
            latest_key = max(
                versions,
                key=lambda item: (
                    int((versions.get(item) or {}).get("updated_at") or 0),
                    item,
                ),
            )
        if not primary_key:
            primary_key = latest_key

        normalized = dict(data)
        normalized.update(
            {
                "profile": profile_name,
                "key": primary_key,
                "latest_key": latest_key,
                "versions": versions,
                "known_keys": {key: True for key in sorted(versions)},
                "version_count": len(versions),
            }
        )
        return normalized

    def _resolve_library_asset_pack_descriptor(self, profile: str, database_url: str = "", service_account_b64: str = "", service_account_info: Optional[Dict] = None) -> Dict:
        profile_name = str(profile or "").strip().lower()
        if profile_name not in self.LIBRARY_ASSET_PACK_KEYS:
            return {}
        assets = {}
        for file_path in self._library_profile_files(profile_name):
            data_uri = self._file_to_base64(str(file_path))
            if not data_uri:
                continue
            assets[self._stable_asset_token(data_uri)] = data_uri
        manifest = self._read_library_asset_pack_manifest(
            profile_name,
            database_url=database_url,
            service_account_b64=service_account_b64,
            service_account_info=service_account_info,
        )
        normalized_manifest = self._normalize_library_manifest(profile_name, manifest)
        canonical = ""
        local_pack_key = ""
        if assets:
            canonical = json.dumps(assets, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            local_pack_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        versions = dict((normalized_manifest or {}).get("versions") or {})
        latest_key = str((normalized_manifest or {}).get("latest_key") or "").strip()
        primary_key = str((normalized_manifest or {}).get("key") or "").strip()

        pack_key = ""
        if local_pack_key and local_pack_key in versions:
            pack_key = local_pack_key
        elif local_pack_key and not versions:
            pack_key = local_pack_key
        elif latest_key:
            pack_key = latest_key
        elif primary_key:
            pack_key = primary_key
        elif local_pack_key:
            pack_key = local_pack_key
        else:
            pack_key = self.LIBRARY_ASSET_PACK_KEYS.get(profile_name, "")
        return {
            "profile": profile_name,
            "key": pack_key,
            "assets": assets,
            "local_key": local_pack_key,
            "manifest": normalized_manifest,
            "available_keys": sorted(versions),
        }

    def _extract_asset_pack_from_html(self, html_text: str) -> Dict:
        try:
            import re

            text = str(html_text or "")
            pattern = re.compile(
                r"data:[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+(?:;[a-zA-Z0-9!#$&^_.=+-]+)*;base64,[A-Za-z0-9+/=]+"
            )
            matches = pattern.findall(text)
            if not matches:
                return {"html": text, "assets": {}, "asset_pack_key": ""}

            replacements = {}
            for data_uri in matches:
                token = self._stable_asset_token(data_uri)
                replacements[token] = data_uri

            stripped_html = text
            for token, data_uri in replacements.items():
                stripped_html = stripped_html.replace(data_uri, token)

            canonical = json.dumps(replacements, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            asset_pack_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            return {
                "html": stripped_html,
                "assets": replacements,
                "asset_pack_key": asset_pack_key,
            }
        except Exception:
            return {"html": str(html_text or ""), "assets": {}, "asset_pack_key": ""}

    def _encode_asset_pack(self, assets_map: Dict, asset_pack_key: str) -> Dict:
        try:
            import gzip

            payload = json.dumps({"assets": dict(assets_map or {})}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            compressed = gzip.compress(payload.encode("utf-8"), compresslevel=9)
            encrypted = self._xor_with_hex_key(compressed, asset_pack_key)
            encoded = base64.b64encode(encrypted).decode("ascii")
            return {
                "encoding": "xor+gzip+base64",
                "encoded": encoded,
                "size_bytes": len(encrypted),
                "chunks": self._chunk_string_payload(encoded),
            }
        except Exception:
            return {
                "encoding": "base64",
                "encoded": "",
                "size_bytes": 0,
                "chunks": [""],
            }

    def publish_to_firebase(self, html_file_path: str, project_name: str, database_url: str, project_id: str = "", progress_callback=None, project_data: Optional[Dict] = None) -> Dict:
        """Upload lightweight HTML + shared asset pack references to Firebase Realtime Database."""
        result = {"ok": False, "db_link": "", "play_link": "", "key": "", "file_url": "", "error": ""}
        try:
            from pathlib import Path
            import time, requests

            fp = Path(html_file_path)
            if not fp.exists():
                return result
            raw = fp.read_text(encoding='utf-8', errors='ignore')
            service_account_b64 = self._read_service_account_b64()
            service_account_info = self._decode_service_account_info(service_account_b64)
            self._emit_publish_progress(progress_callback, {
                "stage": "compressing",
                "message": "Preparing lightweight HTML payload...",
            })
            asset_info = self._extract_asset_pack_from_html(raw)
            stripped_html = str(asset_info.get("html") or "")
            assets_map = dict(asset_info.get("assets") or {})
            asset_pack_key = str(asset_info.get("asset_pack_key") or "")
            asset_pack_source = "derived" if asset_pack_key and assets_map else ""
            asset_pack_profile = ""
            library_profile = self._resolve_library_asset_pack_profile(project_data)
            if assets_map and library_profile:
                library_pack = self._resolve_library_asset_pack_descriptor(
                    library_profile,
                    database_url=database_url,
                    service_account_b64=service_account_b64,
                    service_account_info=service_account_info,
                )
                library_assets = dict((library_pack or {}).get("assets") or {})
                matched_assets = {
                    token: data_uri
                    for token, data_uri in assets_map.items()
                    if library_assets.get(token) == data_uri
                }
                library_pack_key = str((library_pack or {}).get("key") or "")
                library_local_key = str((library_pack or {}).get("local_key") or "")
                library_manifest = dict((library_pack or {}).get("manifest") or {})
                library_versions = dict((library_manifest or {}).get("versions") or {})
                manifest_key = str((library_manifest or {}).get("key") or "").strip()
                manifest_latest_key = str((library_manifest or {}).get("latest_key") or "").strip()
                remote_library_confirmed = bool(
                    library_pack_key
                    and (
                        library_pack_key in library_versions
                        or manifest_key == library_pack_key
                        or manifest_latest_key == library_pack_key
                    )
                )
                if (
                    library_pack_key
                    and matched_assets
                    and remote_library_confirmed
                    and (not library_local_key or library_pack_key == library_local_key)
                ):
                    stripped_html = raw
                    for token, data_uri in matched_assets.items():
                        stripped_html = stripped_html.replace(data_uri, token)
                    assets_map = {}
                    asset_pack_key = library_pack_key
                    asset_pack_source = "library"
                    asset_pack_profile = library_profile
            try:
                content_hash = hashlib.sha256(stripped_html.encode('utf-8')).hexdigest()
            except Exception:
                content_hash = ""
            content_payload = self._encode_text_payload(stripped_html)
            asset_payload = None
            if asset_pack_key and assets_map:
                self._emit_publish_progress(progress_callback, {
                    "stage": "compressing",
                    "message": "Compressing and encrypting shared asset pack...",
                })
                asset_payload = self._encode_asset_pack(assets_map, asset_pack_key)
            ts = int(time.time())
            name = project_name or "EduPlay Game"
            slug_source = project_id or name
            base_key = self._slugify_publish_key(slug_source)
            key = base_key
            chunk_size = 200000
            content_chunks = list(content_payload.get("chunks") or [""])
            meta = {
                "name": name,
                "encoding": str(content_payload.get("encoding") or "base64"),
                "created_at": ts,
                "expires_at": ts + 15*24*60*60,
                "type": "single_file_html_rtdb",
                "chunk_size": chunk_size,
                "total_chunks": len(content_chunks),
                "content_hash": content_hash,
                "asset_pack_key": asset_pack_key,
                "asset_pack_profile": asset_pack_profile,
                "asset_pack_source": asset_pack_source,
                "asset_pack_encoding": str((asset_payload or {}).get("encoding") or ""),
                "asset_pack_required": bool(asset_pack_key),
            }
            try:
                import math as _math
                safe_meta = {}
                for k, v in meta.items():
                    sk = str(k)
                    if isinstance(v, float) and (_math.isnan(v) or _math.isinf(v)):
                        v = None
                    safe_meta[sk] = v
                meta = safe_meta
                _ = json.dumps(meta, ensure_ascii=False, allow_nan=False)
            except Exception:
                pass

            asset_meta = {}
            asset_chunks = []
            if asset_pack_key and asset_payload:
                asset_chunks = list(asset_payload.get("chunks") or [""])
                asset_meta = {
                    "type": "asset_pack",
                    "encoding": str(asset_payload.get("encoding") or "base64"),
                    "created_at": ts,
                    "updated_at": ts,
                    "chunk_size": chunk_size,
                    "total_chunks": len(asset_chunks),
                    "asset_count": len(assets_map),
                    "hash": asset_pack_key,
                    "size_bytes": int(asset_payload.get("size_bytes") or 0),
                }

            try:
                import firebase_admin
                from firebase_admin import credentials, db

                print(f"[FIREBASE] Service account loaded: {bool(service_account_b64)}, length: {len(service_account_b64) if service_account_b64 else 0}")
                if service_account_b64:
                    cred = credentials.Certificate(service_account_info)
                    try:
                        import os
                        os.environ['EDUPLAY_FIREBASE_SERVICE_ACCOUNT_B64'] = service_account_b64
                    except Exception:
                        pass
                    if not firebase_admin._apps:
                        firebase_admin.initialize_app(cred, {
                            'databaseURL': database_url,
                        })
                    games_ref = db.reference(f"/games/{key}")
                    uploaded_units = 0
                    upload_total = len(content_chunks) + (len(asset_chunks) if asset_chunks else 0)
                    upload_total = upload_total or 1

                    def _emit_upload_progress(message: str) -> None:
                        percent = int((uploaded_units / upload_total) * 100) if upload_total else 100
                        self._emit_publish_progress(progress_callback, {
                            "stage": "uploading",
                            "current": uploaded_units,
                            "total": upload_total,
                            "percent": percent,
                            "message": message,
                        })

                    if asset_pack_key and asset_chunks:
                        asset_ref = db.reference(f"/asset_packs/{asset_pack_key}")
                        existing_asset = asset_ref.get()
                        has_existing_asset = bool(existing_asset)
                        if not has_existing_asset:
                            asset_ref.set(asset_meta)
                            for idx, chunk in enumerate(asset_chunks):
                                asset_ref.child("chunks").child(str(idx)).set(chunk)
                                uploaded_units += 1
                                _emit_upload_progress(
                                    f"Uploading shared asset pack: {uploaded_units}/{upload_total} chunks"
                                )
                    games_ref.set(meta)
                    self._emit_publish_progress(progress_callback, {
                        "stage": "uploading",
                        "current": uploaded_units,
                        "total": upload_total,
                        "percent": 0,
                        "message": "Uploading lightweight HTML payload...",
                    })
                    games_ref.child("content_chunks").set({})
                    for idx, chunk in enumerate(content_chunks):
                        games_ref.child("content_chunks").child(str(idx)).set(chunk)
                        uploaded_units += 1
                        _emit_upload_progress(
                            f"Uploading lightweight HTML payload: {uploaded_units}/{upload_total} chunks"
                        )
                    self._emit_publish_progress(progress_callback, {
                        "stage": "finalizing",
                        "message": "Generating share link...",
                    })
                    result["ok"] = True
                    result["db_link"] = database_url.rstrip('/') + f"/games/{key}.json"
                    result["play_link"] = f"https://eduplay-game.web.app/{key}"
                    result["key"] = key
                    result["file_url"] = ""
                    result["error"] = ""
                    self._emit_publish_progress(progress_callback, {
                        "stage": "completed",
                        "play_link": result["play_link"],
                        "db_link": result["db_link"],
                        "key": result["key"],
                        "message": "Share link is ready.",
                    })
                    return result
            except Exception as e_admin:
                print(f"[FIREBASE] Admin SDK failed: {e_admin}")
                try:
                    result["error"] = f"Admin SDK error: {e_admin}"
                except Exception:
                    pass
                if service_account_b64:
                    return result

            print(f"[FIREBASE] Using REST API fallback...")
            base = database_url.rstrip('/')
            try:
                headers = {"Content-Type": "application/json; charset=utf-8"}
                uploaded_units = 0
                upload_total = len(content_chunks) + (len(asset_chunks) if asset_chunks else 0)
                upload_total = upload_total or 1

                def _emit_upload_progress(message: str) -> None:
                    percent = int((uploaded_units / upload_total) * 100) if upload_total else 100
                    self._emit_publish_progress(progress_callback, {
                        "stage": "uploading",
                        "current": uploaded_units,
                        "total": upload_total,
                        "percent": percent,
                        "message": message,
                    })

                def _rest_get_json(url: str):
                    try:
                        response = requests.get(url)
                        if not (200 <= response.status_code < 300):
                            return None
                        body = str(getattr(response, "text", "") or "").strip()
                        if not body or body == "null":
                            return None
                        return json.loads(body)
                    except Exception:
                        return None

                if asset_pack_key and asset_chunks:
                    existing_asset = _rest_get_json(base + f"/asset_packs/{asset_pack_key}.json")
                    has_existing_asset = bool(existing_asset)
                    if not has_existing_asset:
                        asset_meta_url = base + f"/asset_packs/{asset_pack_key}.json"
                        asset_meta_body = json.dumps(asset_meta, ensure_ascii=False).encode("utf-8")
                        asset_meta_resp = requests.put(asset_meta_url, data=asset_meta_body, headers=headers)
                        if not (200 <= asset_meta_resp.status_code < 300):
                            result["error"] = f"REST ASSET META {asset_meta_resp.status_code}"
                            return result
                        for idx, chunk in enumerate(asset_chunks):
                            asset_chunk_url = base + f"/asset_packs/{asset_pack_key}/chunks/{idx}.json"
                            asset_chunk_body = json.dumps(chunk).encode("utf-8")
                            asset_chunk_resp = requests.put(asset_chunk_url, data=asset_chunk_body, headers=headers)
                            if not (200 <= asset_chunk_resp.status_code < 300):
                                result["error"] = f"REST ASSET CHUNK {idx} {asset_chunk_resp.status_code}"
                                return result
                            uploaded_units += 1
                            _emit_upload_progress(
                                f"Uploading shared asset pack: {uploaded_units}/{upload_total} chunks"
                            )

                url_meta = base + f"/games/{key}.json"
                body_meta = json.dumps(meta, ensure_ascii=False).encode("utf-8")
                r = requests.put(url_meta, data=body_meta, headers=headers)
                if not (200 <= r.status_code < 300):
                    try:
                        txt = ""
                        try:
                            txt = r.text
                        except Exception:
                            txt = ""
                        result["error"] = f"REST META {r.status_code}: {txt[:300]}"
                    except Exception:
                        result["error"] = f"REST META {r.status_code}"
                    return result
                for idx, chunk in enumerate(content_chunks):
                    url_chunk = base + f"/games/{key}/content_chunks/{idx}.json"
                    body_chunk = json.dumps(chunk).encode("utf-8")
                    cr = requests.put(url_chunk, data=body_chunk, headers=headers)
                    if not (200 <= cr.status_code < 300):
                        try:
                            txt = ""
                            try:
                                txt = cr.text
                            except Exception:
                                txt = ""
                            result["error"] = f"REST CHUNK {idx} {cr.status_code}: {txt[:300]}"
                        except Exception:
                            result["error"] = f"REST CHUNK {idx} {cr.status_code}"
                        return result
                    uploaded_units += 1
                    _emit_upload_progress(
                        f"Uploading lightweight HTML payload: {uploaded_units}/{upload_total} chunks"
                    )
                self._emit_publish_progress(progress_callback, {
                    "stage": "finalizing",
                    "message": "Generating share link...",
                })
                result["ok"] = True
                result["db_link"] = url_meta
                result["play_link"] = f"https://eduplay-game.web.app/{key}"
                result["key"] = key
                result["file_url"] = ""
                self._emit_publish_progress(progress_callback, {
                    "stage": "completed",
                    "play_link": result["play_link"],
                    "db_link": result["db_link"],
                    "key": result["key"],
                    "message": "Share link is ready.",
                })
            except Exception as e_rest:
                try:
                    result["error"] = f"REST error: {e_rest}"
                except Exception:
                    pass
            return result
        except Exception as e:
            print(f"Publish to Firebase error: {e}")
            try:
                result["error"] = str(e)
            except Exception:
                pass
            return result

    def cleanup_firebase_old(self, database_url: str, days: int = 30, max_items: Optional[int] = None) -> Dict:
        """Delete games older than `days` and enforce max_items (delete oldest) from Firebase Realtime Database."""
        info = {"deleted": [], "checked": 0, "error": ""}
        try:
            import time, requests
            now = int(time.time())
            cutoff = now - days*24*60*60
            # Try admin first
            try:
                import firebase_admin
                from firebase_admin import credentials, db, storage
                b64 = self._read_service_account_b64()
                if b64:
                    service_account_info = self._decode_service_account_info(b64)
                    cred = credentials.Certificate(service_account_info)
                    storage_bucket = self._firebase_storage_bucket(service_account=service_account_info)
                    if not firebase_admin._apps:
                        firebase_admin.initialize_app(cred, {'databaseURL': database_url, 'storageBucket': storage_bucket})
                    ref = db.reference("/games")
                    def _delete_storage_payload(item):
                        try:
                            storage_path = str((item or {}).get("storage_path") or "").strip()
                            if not storage_path:
                                return
                            bucket_name = str((item or {}).get("storage_bucket") or storage_bucket).strip() or storage_bucket
                            bucket = storage.bucket(bucket_name)
                            blob = bucket.blob(storage_path)
                            blob.delete()
                        except Exception:
                            pass
                    data = ref.get() or {}
                    items = list((data.items() if isinstance(data, dict) else []))
                    for k, v in items:
                        info["checked"] += 1
                        try:
                            created = int((v or {}).get("created_at") or 0)
                            if created and created < cutoff:
                                _delete_storage_payload(v)
                                ref.child(k).delete()
                                info["deleted"].append(k)
                        except Exception:
                            pass
                    if max_items is not None:
                        try:
                            # Enforce capacity: delete oldest by created_at until within limit
                            remaining = []
                            data2 = ref.get() or {}
                            for k, v in (data2.items() if isinstance(data2, dict) else []):
                                try:
                                    created = int((v or {}).get("created_at") or 0)
                                except Exception:
                                    created = 0
                                remaining.append((created, k))
                            remaining.sort(key=lambda x: x[0] or 0)
                            while len(remaining) > max_items:
                                _, del_key = remaining.pop(0)
                                try:
                                    item = {}
                                    try:
                                        item = data2.get(del_key) or {}
                                    except Exception:
                                        item = {}
                                    _delete_storage_payload(item)
                                    ref.child(del_key).delete()
                                    info["deleted"].append(del_key)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    return info
            except Exception:
                pass
            # Fallback to REST
            url = database_url.rstrip('/') + "/games.json"
            r = requests.get(url)
            if not (200 <= r.status_code < 300):
                info["error"] = f"GET failed {r.status_code}"
                return info
            data = r.json() or {}
            items = list((data.items() if isinstance(data, dict) else []))
            for k, v in items:
                info["checked"] += 1
                try:
                    created = int((v or {}).get("created_at") or 0)
                    if created and created < cutoff:
                        del_url = database_url.rstrip('/') + f"/games/{k}.json"
                        dr = requests.delete(del_url)
                        if 200 <= dr.status_code < 300:
                            info["deleted"].append(k)
                except Exception:
                    pass
            if max_items is not None:
                try:
                    remaining = []
                    # Re-fetch remaining for accurate count
                    r2 = requests.get(url)
                    data2 = r2.json() if (200 <= r2.status_code < 300) else {}
                    for k, v in (data2.items() if isinstance(data2, dict) else []):
                        try:
                            created = int((v or {}).get("created_at") or 0)
                        except Exception:
                            created = 0
                        remaining.append((created, k))
                    remaining.sort(key=lambda x: x[0] or 0)
                    while len(remaining) > max_items:
                        _, del_key = remaining.pop(0)
                        del_url = database_url.rstrip('/') + f"/games/{del_key}.json"
                        try:
                            dr = requests.delete(del_url)
                            if 200 <= dr.status_code < 300:
                                info["deleted"].append(del_key)
                        except Exception:
                            pass
                except Exception:
                    pass
            return info
        except Exception as e:
            info["error"] = str(e)
            return info

    def export_to_html(self, project_data: Dict, output_dir: str, bundle_resources: bool = True, single_file: bool = False, output_filename: Optional[str] = None) -> bool:
        """Export project to HTML5 format
        If single_file is True, writes a single `[project_name].html` and skips helper files.
        For Millionaire games, uses special single-file export with embedded assets.
        """
        try:
            try:
                self._last_export_error = ""
            except Exception:
                pass
            try:
                import copy as _copy
                project_data = _copy.deepcopy(project_data) if isinstance(project_data, dict) else {}
            except Exception:
                project_data = dict(project_data) if isinstance(project_data, dict) else {}
            try:
                from eduplay.core.settings_manager import SettingsManager
                app_lang = SettingsManager().get_language()
                if app_lang and str(app_lang).strip():
                    project_data["language"] = str(app_lang).strip()
            except Exception:
                pass
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            game_type = project_data.get("game_type", "")
            force_variant = str(project_data.get("force_variant") or "").lower()
            cfg_full = (project_data.get('game_config', {}) or {})
            cfg_gt = str(cfg_full.get('game_type') or '').lower()
            is_millionaire = (
                force_variant == 'millionaire' or
                game_type in ("quiz_millionaire", "millionaire", "ai la trieu phu") or
                ("triệu phú" in cfg_gt) or ("millionaire" in cfg_gt) or ("altp" in cfg_gt) or
                ("triệu phú" in str(project_data.get("name", "")).lower()) or
                ("millionaire" in str(project_data.get("name", "")).lower()) or
                ("ai la trieu phu" in str(project_data.get("name", "")).lower()) or
                ("altp" in str(project_data.get("name", "")).lower())
            )
            
            if is_millionaire and single_file:
                name = output_filename or project_data.get('name', 'Millionaire')
                safe = ''.join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_') or 'Millionaire'
                html_file = output_path / (safe + '.html')
                try:
                    base_dir = self.assets_dir / 'millionaire'
                    if (base_dir / 'index.html').exists():
                        return self.export_millionaire_single_file(project_data, str(html_file), project_data.get('questions', []))
                except Exception:
                    pass
                try:
                    html_content = self._generate_quiz_game_html(project_data, 'classic')
                    html_content = self._inject_favicon(html_content)
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    try:
                        self._last_export_error = "Millionaire assets missing; exported Classic HTML"
                    except Exception:
                        pass
                    return True
                except Exception as e:
                    try:
                        self._last_export_error = str(e)
                    except Exception:
                        pass
                    return False
            gt_lower = str(game_type).lower()
            def _looks_like_fishing_config(cfg: Dict) -> bool:
                try:
                    if not isinstance(cfg, dict):
                        return False
                    if isinstance(cfg.get("fish_objects"), list) and len(cfg.get("fish_objects") or []) > 0:
                        return True
                    if isinstance(cfg.get("fishing_settings"), dict) and len(cfg.get("fishing_settings") or {}) > 0:
                        return True
                    if isinstance(cfg.get("fish_count"), (int, float)) or isinstance(cfg.get("base_speed"), (int, float)):
                        return True
                    if isinstance(cfg.get("fish_speed"), (int, float)):
                        return True
                    if cfg.get("score_per_fish") is not None:
                        return True
                    return False
                except Exception:
                    return False
            cfg_gt = str(((project_data.get('game_config', {}) or {}).get('game_type') or '')).lower()
            marker = str(project_data.get('variant_marker') or '').lower()
            cfg_marker = str((project_data.get('game_config', {}) or {}).get('variant_marker') or '').lower()
            is_fishing = (
                gt_lower == 'fishing'
                or 'fishing' in gt_lower
                or 'fish' in gt_lower
                or ('bắt cá' in gt_lower) or ('bat ca' in gt_lower) or ('câu cá' in gt_lower) or ('cau ca' in gt_lower)
                or gt_lower in ('bat_ca', 'bắt cá', 'tro_choi_cau_ca', 'trò_chơi_câu_cá')
                or gt_lower in ('fishing game', 'tro choi cau ca', 'trò chơi câu cá')
                or force_variant == 'fishing'
                or ('fishing' in cfg_gt) or ('fish' in cfg_gt) or ('bắt cá' in cfg_gt) or ('bat ca' in cfg_gt) or ('câu cá' in cfg_gt) or ('cau ca' in cfg_gt)
                or marker == 'fishing'
                or cfg_marker == 'fishing'
            )
            if is_fishing:
                if bundle_resources:
                    fishing_data = self._bundle_media_files(project_data)
                else:
                    fishing_data = project_data
                name = output_filename or project_data.get('name', 'Fishing_Game')
                safe = ''.join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_') or 'Fishing_Game'
                if single_file:
                    html_file = output_path / (safe + '.html')
                    ok = self._export_fishing_single_file(fishing_data, html_file)
                else:
                    # For multi-file export, we still use the fishing template but with separate data file
                    html_file = output_path / "index.html"
                    ok = self._export_fishing_single_file(fishing_data, html_file)
                    if ok:
                        # Create game data JSON for multi-file mode
                        game_data = {
                            "project_name": fishing_data.get("name", "Fishing Game"),
                            "questions": fishing_data.get("questions", []),
                            "game_config": fishing_data.get("game_config", {}),
                            "game_type": "fishing"
                        }
                        data_file = output_path / "game_data.json"
                        with open(data_file, 'w', encoding='utf-8') as f:
                            json.dump(game_data, f, indent=2, ensure_ascii=False)
                        
                        self._create_run_script(output_path)
                        self._create_readme(output_path, "HTML")
                return ok
            
            # Regular HTML export for other games
            if bundle_resources:
                bundled_data = self._bundle_media_files(project_data)
            else:
                bundled_data = project_data
            
            # Create HTML file
            html_content = self._generate_html_content(bundled_data)
            html_content = self._inject_favicon(html_content)
            def _sanitize_name(name: str) -> str:
                keep = [c for c in name if c.isalnum() or c in (' ', '-', '_')]
                s = ''.join(keep).strip()
                s = s.replace(' ', '_')
                return s or 'EduPlay_Game'
            if single_file:
                base = output_filename or bundled_data.get("name", "EduPlay Game")
                fname = _sanitize_name(base) + ".html"
                html_file = output_path / fname
            else:
                html_file = output_path / "index.html"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # If not bundling resources, write separate JSON data (multi-file mode only)
            if (not bundle_resources) and (not single_file):
                game_data = {
                    "project_name": bundled_data.get("name", "Game"),
                    "questions": bundled_data.get("questions", []),
                    "game_config": bundled_data.get("game_config", {}),
                    "game_type": bundled_data.get("game_type", "quiz_classic")
                }
                data_file = output_path / "game_data.json"
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(game_data, f, indent=2, ensure_ascii=False)
            
            # Copy assets (only if not bundling resources and multi-file mode)
            if (not bundle_resources) and (not single_file):
                self._copy_game_assets(output_path, project_data)
            
            # Helper files only for multi-file mode
            if not single_file:
                self._create_run_script(output_path)
                self._create_readme(output_path, "HTML")
            
            return True
            
        except Exception as e:
            try:
                self._last_export_error = str(e)
            except Exception:
                pass
            print(f"Error exporting to HTML: {e}")
            return False
            if not single_file:
                self._create_run_script(output_path)
                self._create_readme(output_path, "HTML")
            
            return True
            
        except Exception as e:
            print(f"Error exporting to HTML: {e}")
            return False
    
    def export_to_native(self, project_data: Dict, output_dir: str, platform: str = "windows") -> bool:
        """Export project to native format (PyGame)"""
        try:
            try:
                from eduplay.core.settings_manager import SettingsManager
                app_lang = SettingsManager().get_language()
                if app_lang and str(app_lang).strip():
                    project_data = dict(project_data) if isinstance(project_data, dict) else {}
                    project_data["language"] = str(app_lang).strip()
            except Exception:
                pass
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Bundle media files for native as well (so PyGame can decode base64 at runtime)
            bundled_data = self._bundle_media_files(project_data)
            # Generate Python game script
            game_script = self._generate_pygame_script(bundled_data)
            script_file = output_path / "game.py"
            
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(game_script)
            
            # Create game data JSON
            game_data = {
                "project_name": bundled_data.get("name", "Game"),
                "language": bundled_data.get("language", project_data.get("language", "en")),
                "questions": bundled_data.get("questions", []),
                "game_config": bundled_data.get("game_config", {}),
                "game_type": bundled_data.get("game_type", "quiz_classic")
            }
            
            data_file = output_path / "game_data.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(game_data, f, indent=2, ensure_ascii=False)
            
            # Copy assets
            self._copy_game_assets(output_path, project_data)
            
            # Create run script
            if platform == "windows":
                self._create_run_script(output_path, "python game.py")
            else:  # macOS/Linux
                self._create_run_script(output_path, "python3 game.py", shell_script=True)
            
            # Create README
            self._create_readme(output_path, "Native")
            
            return True
            
        except Exception as e:
            print(f"Error exporting to native: {e}")
            return False

    def export_to_exe(self, project_data: Dict, output_dir: str) -> bool:
        """Export project to Windows executable using PyInstaller.
        Creates game script and a build script that users can run. Checks Python and PyInstaller.
        """
        try:
            try:
                from eduplay.core.settings_manager import SettingsManager
                app_lang = SettingsManager().get_language()
                if app_lang and str(app_lang).strip():
                    project_data = dict(project_data) if isinstance(project_data, dict) else {}
                    project_data["language"] = str(app_lang).strip()
            except Exception:
                pass
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Generate Python game script (reuse native export script)
            game_script = self._generate_pygame_script(project_data)
            script_file = output_path / "game.py"
            script_file.write_text(game_script, encoding='utf-8')

            # Write game data JSON
            data_file = output_path / "game_data.json"
            data = {
                "project_name": project_data.get("name", "Game"),
                "language": project_data.get("language", "en"),
                "questions": project_data.get("questions", []),
                "game_config": project_data.get("game_config", {}),
                "game_type": project_data.get("game_type", "quiz_classic")
            }
            data_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

            # Copy assets
            self._copy_game_assets(output_path, project_data)

            # Create build script for Windows using PyInstaller
            build_bat = output_path / "build_exe.bat"
            build_bat.write_text(
                """@echo off
setlocal
echo Checking Python and PyInstaller...
python --version || (echo Python not found. Please install Python. & exit /b 1)
pyinstaller --version || (echo PyInstaller not found. Installing... & python -m pip install pyinstaller)
echo Building executable...
pyinstaller --noconfirm --onedir --name EduPlayGame --add-data "game_data.json;." --add-data "assets;assets" game.py
echo Build finished. Look in the dist\\ folder for EduPlayGame.exe
pause
""",
                encoding='utf-8'
            )

            # Create README with instructions
            self._create_readme(output_path, "Executable")

            # Auto-build executable using PyInstaller
            try:
                import subprocess, sys
                # Ensure PyInstaller is available
                result = subprocess.run(["pyinstaller", "--version"], capture_output=True, text=True)
                if result.returncode != 0:
                    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
                # Build
                cmd = [
                    "pyinstaller", "--noconfirm", "--onefile", "--name", "EduPlayGame",
                    "--add-data", "game_data.json;.",
                    "--add-data", "assets;assets",
                    "game.py"
                ]
                subprocess.run(cmd, cwd=str(output_path), check=True)
            except Exception as build_err:
                print(f"Auto-build EXE skipped or failed: {build_err}")

            return True
        except Exception as e:
            print(f"Error exporting to EXE: {e}")
            return False
    
    def _generate_html_content(self, project_data: Dict) -> str:
        """Generate HTML content for the game"""
        game_type = project_data.get("game_type", "quiz_classic")
        gt_lower = str(game_type or "").lower()
        # Robust detection: also consider game_config
        try:
            cfg_gt = str((project_data.get('game_config', {}) or {}).get('game_type') or '').lower()
        except Exception:
            cfg_gt = ''
        
        # Kiểm tra xem có phải fishing game không - sử dụng logic mạnh hơn
        def looks_like_fishing_config(cfg_dict):
            try:
                if not isinstance(cfg_dict, dict):
                    return False
                if isinstance(cfg_dict.get("fish_objects"), list) and len(cfg_dict.get("fish_objects") or []) > 0:
                    return True
                if isinstance(cfg_dict.get("fishing_settings"), dict) and len(cfg_dict.get("fishing_settings") or {}) > 0:
                    return True
                if isinstance(cfg_dict.get("fish_count"), (int, float)) or isinstance(cfg_dict.get("base_speed"), (int, float)):
                    return True
                if isinstance(cfg_dict.get("fish_speed"), (int, float)):
                    return True
                if cfg_dict.get("score_per_fish") is not None:
                    return True
                return False
            except Exception:
                return False
        
        # Nhận diện fishing game với logic mạnh hơn
        force_variant = str(project_data.get('force_variant') or '').lower()
        cfg = project_data.get('game_config', {}) or {}
        cfg_gt = str((cfg.get('game_type') or '')).lower()
        marker = str(project_data.get('variant_marker') or '').lower()
        cfg_marker = str((project_data.get('game_config', {}) or {}).get('variant_marker') or '').lower()
        name_str = str(project_data.get('name') or '')
        is_fishing = (
            gt_lower == 'fishing'
            or 'fishing' in gt_lower
            or 'fish' in gt_lower
            or ('bắt cá' in gt_lower) or ('bat ca' in gt_lower) or ('câu cá' in gt_lower) or ('cau ca' in gt_lower)
            or gt_lower in ('bat_ca', 'bắt cá', 'tro_choi_cau_ca', 'trò_chơi_câu_cá')
            or gt_lower in ('fishing game', 'tro choi cau ca', 'trò chơi câu cá')
            or force_variant == 'fishing'
            or ('fishing' in cfg_gt) or ('fish' in cfg_gt) or ('bắt cá' in cfg_gt) or ('bat ca' in cfg_gt) or ('câu cá' in cfg_gt) or ('cau ca' in cfg_gt)
            or marker == 'fishing'
            or cfg_marker == 'fishing'
            or ('🎣' in name_str)
        )
        
        # Always prioritize explicit fishing mode using structural markers, not name keywords
        try:
            if is_fishing:
                return self._generate_fishing_game_html(project_data)
        except Exception:
            pass
        # Disable broad heuristic to avoid misrouting classic quizzes into Millionaire
        # Millionaire rendering is handled explicitly via force_variant / game_type / name keywords below
        # Strong routing by explicit type/variant only
        try:
            fv = str(project_data.get('force_variant') or '').lower()
            if fv == 'altp_vn':
                return self._generate_altp_vn_html(project_data)
            if fv == 'wwbm':
                return self._generate_wwbm_html(project_data)
            if fv == 'millionaire':
                return self._generate_millionaire_html(project_data)
        except Exception:
            pass
        if gt_lower == "fishing":
            return self._generate_fishing_game_html(project_data)
        if gt_lower in ("quiz_millionaire","millionaire","ai la trieu phu"):
            return self._generate_millionaire_html(project_data)
        html = self._generate_quiz_game_html(project_data, 'classic')
        return self._inject_favicon(html)
    
    def _normalize_millionaire_questions_for_runtime(self, questions: List[Dict]) -> List[Dict]:
        normalized: List[Dict] = []
        for raw_question in list(questions or []):
            q = raw_question if isinstance(raw_question, dict) else {}
            options = q.get('options') or q.get('answers') or q.get('choices') or []
            if not options:
                variants = [
                    ('option_a', 'option_b', 'option_c', 'option_d'),
                    ('answerA', 'answerB', 'answerC', 'answerD'),
                    ('A', 'B', 'C', 'D'),
                    ('option1', 'option2', 'option3', 'option4'),
                    ('pa', 'pb', 'pc', 'pd'),
                    ('ansA', 'ansB', 'ansC', 'ansD'),
                ]
                for keys in variants:
                    arr = [q.get(keys[0]), q.get(keys[1]), q.get(keys[2]), q.get(keys[3])]
                    arr = [x for x in arr if x is not None]
                    if len(arr) >= 2:
                        options = arr
                        break

            if isinstance(options, dict):
                ordered = []
                for key in ['A', 'B', 'C', 'D', 'E', 'F']:
                    if key in options:
                        ordered.append(options.get(key))
                options = ordered or list(options.values())

            correct_index = 0
            normalized_options: List[str] = []
            if isinstance(options, list) and options and isinstance(options[0], dict):
                for idx, option in enumerate(options):
                    text = option.get('text')
                    if text is None:
                        text = option.get('label')
                    if text is None:
                        text = option.get('value')
                    normalized_options.append(str(text or ''))
                    try:
                        if bool(option.get('correct', False)):
                            correct_index = idx
                    except Exception:
                        pass
            elif isinstance(options, list):
                normalized_options = [str(option or '') for option in options]

            correct_value = q.get('correct_answer')
            if correct_value is None:
                correct_value = q.get('correctAnswer')
            if correct_value is None:
                correct_value = q.get('correctIndex')

            if isinstance(correct_value, (int, float)):
                try:
                    correct_index = int(correct_value)
                except Exception:
                    pass
            elif isinstance(correct_value, str):
                labels = ['A', 'B', 'C', 'D', 'E', 'F']
                upper = correct_value.strip().upper()
                if upper in labels:
                    correct_index = labels.index(upper)
                else:
                    try:
                        matched = normalized_options.index(correct_value)
                        correct_index = matched
                    except ValueError:
                        pass

            if (not normalized_options) and isinstance(q.get('incorrect_answers'), list):
                incorrect_answers = [str(item or '') for item in list(q.get('incorrect_answers') or [])]
                correct_text = ''
                if isinstance(correct_value, str):
                    correct_text = correct_value
                elif isinstance(correct_value, (int, float)) and normalized_options:
                    idx = int(correct_value)
                    if 0 <= idx < len(normalized_options):
                        correct_text = normalized_options[idx]
                elif correct_value is not None:
                    correct_text = str(correct_value)
                normalized_options = ([correct_text] if str(correct_text).strip() else []) + incorrect_answers

            if len(normalized_options) < 2:
                normalized_options = ['Option 1', 'Option 2', 'Option 3', 'Option 4']
                correct_index = 0

            if correct_index < 0 or correct_index >= len(normalized_options):
                correct_index = 0

            normalized_question = {
                'question': q.get('question') or q.get('text') or '',
                'options': normalized_options,
                'correct_answer': correct_index,
                'correctAnswer': correct_index,
                'incorrect_answers': [
                    option for idx, option in enumerate(normalized_options) if idx != correct_index
                ][:3],
                'time_limit': q.get('time_limit', q.get('time')),
                'explanation': q.get('explanation') or q.get('explain') or q.get('detail') or q.get('solution') or '',
            }
            image_base64 = q.get('image_base64') or ''
            if (not image_base64) and isinstance(q.get('image'), str) and str(q.get('image')).startswith('data:'):
                image_base64 = str(q.get('image'))
            if image_base64:
                normalized_question['image_base64'] = image_base64
            normalized.append(normalized_question)
        return normalized

    def _ensure_feedback_sound_pools(self, game_config: Dict) -> Dict:
        try:
            gc = dict(game_config or {})
        except Exception:
            gc = {}
        try:
            sound_dir = self.assets_dir / 'sound'

            def _bundle_feedback_pool(entries):
                bundled = []
                for filename, text in entries:
                    fp = sound_dir / filename
                    if not fp.exists():
                        continue
                    try:
                        bundled.append({
                            'src': self._file_to_base64(str(fp)),
                            'text': text,
                        })
                    except Exception:
                        continue
                return bundled

            existing_pools = gc.get('feedback_sound_pools') if isinstance(gc.get('feedback_sound_pools'), dict) else {}
            correct_pool = list(existing_pools.get('correct') or [])
            wrong_pool = list(existing_pools.get('wrong') or [])
            if not correct_pool:
                correct_pool = _bundle_feedback_pool([
                    ('Well_done!.wav', 'Well done!'),
                    ('Correct!.wav', 'Correct!'),
                    ('Good_job!.wav', 'Good job!'),
                    ('Great!.wav', 'Great!'),
                ])
            if not wrong_pool:
                wrong_pool = _bundle_feedback_pool([
                    ('Keep_learning!.wav', 'Keep learning!'),
                    ('Keep_trying!.wav', 'Keep trying!'),
                    ('Keep_going!.wav', 'Keep going!'),
                    ('Good_try!.wav', 'Good try!'),
                ])
            if correct_pool or wrong_pool:
                gc['feedback_sound_pools'] = {
                    'correct': correct_pool,
                    'wrong': wrong_pool,
                }
                if correct_pool and not gc.get('correct_sound_base64'):
                    gc['correct_sound_base64'] = correct_pool[0].get('src')
                if wrong_pool and not gc.get('wrong_sound_base64'):
                    gc['wrong_sound_base64'] = wrong_pool[0].get('src')
        except Exception:
            pass
        return gc

    def _without_feedback_sound_pools(self, game_config: Dict) -> Dict:
        try:
            gc = dict(game_config or {})
        except Exception:
            gc = {}
        try:
            gc.pop('feedback_sound_pools', None)
        except Exception:
            pass
        return gc

    def export_millionaire_single_file(self, project_data: Dict, output_path: str, 
                                     teacher_questions: List[Dict]) -> bool:
        """Export Millionaire game as single HTML file with all assets embedded (inline CSS/JS and base64 assets)"""
        try:
            ofp = output_path if str(output_path).lower().endswith('.html') else str(output_path) + '.html'
            output_file = Path(ofp)
            base_dir = self.assets_dir / 'millionaire'
            # Load base Millionaire index (with decryption if built)
            html = load_asset_text('assets_bundle/millionaire/index.html')

            # Inline CSS and rewrite url(...) to data URIs; strip external CSS links
            def inline_css(h):
                # Remove external CSS includes
                extern_css = [
                    'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
                    'https://use.fontawesome.com/releases/v5.2.0/css/all.css',
                    'https://cdn.rawgit.com/konpa/devicon/df6431e323547add1b4cf45992913f15286456d3/devicon.min.css',
                    'https://fonts.googleapis.com/css?family=Roboto',
                    'https://cdnjs.cloudflare.com/ajax/libs/timecircles/1.5.3/TimeCircles.min.css'
                ]
                for url in extern_css:
                    h = h.replace(f'<link href="{url}" rel="stylesheet">', '')
                    h = h.replace(f'<link rel="stylesheet" href="{url}">', '')

                import re
                def rewrite_css_urls(css_text: str) -> str:
                    def repl(m):
                        raw = m.group(1).strip().strip('"').strip("'")
                        if raw.startswith('http://') or raw.startswith('https://'):
                            return 'url()'
                        rp = raw.lstrip('./')
                        pth = (base_dir / rp).resolve()
                        try:
                            if pth.exists():
                                return 'url(' + to_data_uri(pth) + ')'
                        except Exception:
                            pass
                        return 'url()'
                    return re.sub(r'url\(\s*([^\)]+)\s*\)', repl, css_text)

                for css_name in ['css/styles.css','css/mobile.css']:
                    try:
                        css = load_asset_text(f'assets_bundle/millionaire/{css_name}')
                        css = rewrite_css_urls(css)
                        h = h.replace(f'<link rel="stylesheet" href="{css_name}">', f'<style>\n{css}\n</style>')
                        h = h.replace(f'<link href="{css_name}" rel="stylesheet">', f'<style>\n{css}\n</style>')
                    except Exception:
                        pass
                return h

            # Inline JS and strip external script tags
            def inline_js(h):
                for js_name in ['js/sounds.js','js/app.js','js/functions.js']:
                    try:
                        js = load_asset_text(f'assets_bundle/millionaire/{js_name}')
                        h = h.replace(f'<script src="{js_name}"></script>', f'<script>\n{js}\n</script>')
                        h = h.replace(f'<script src="./{js_name}"></script>', f'<script>\n{js}\n</script>')
                    except Exception:
                        pass
                # drop leaderboard.js entirely (uses Firebase)
                h = h.replace('<script src="js/leaderboard.js"></script>', '')
                h = h.replace('<script src="./js/leaderboard.js"></script>', '')
                external_scripts = [
                    'https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js',
                    'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js',
                    'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js',
                    'https://rawgithub.com/hiddentao/google-tts/master/google-tts.min.js',
                    'https://cdnjs.cloudflare.com/ajax/libs/jquery-animateNumber/0.0.14/jquery.animateNumber.min.js',
                    'https://cdnjs.cloudflare.com/ajax/libs/timecircles/1.5.3/TimeCircles.min.js',
                    'https://www.gstatic.com/firebasejs/5.0.4/firebase-app.js',
                    'https://www.gstatic.com/firebasejs/5.0.4/firebase-database.js',
                    'https://cdnjs.cloudflare.com/ajax/libs/howler/2.0.15/howler.core.min.js'
                ]
                for url in external_scripts:
                    h = h.replace(f'<script src="{url}"></script>', '')
                return h

            # Base64 helpers
            import base64, mimetypes
            def to_data_uri(path: Path) -> str:
                mime, _ = mimetypes.guess_type(path.name)
                if not mime:
                    # fallback by extension
                    ext = path.suffix.lower()
                    if ext in ['.png']: mime='image/png'
                    elif ext in ['.jpg','.jpeg']: mime='image/jpeg'
                    elif ext in ['.mp3']: mime='audio/mpeg'
                    elif ext in ['.mp4']: mime='video/mp4'
                    else: mime='application/octet-stream'
                data = base64.b64encode(path.read_bytes()).decode('ascii')
                return f'data:{mime};base64,{data}'

            # Inline images/video by replacing both relative and ./relative occurrences
            def inline_images(h):
                targets = ['images/Logo.png','images/background.png','images/backgroundGame.png','images/QuestionBox.png','images/QuestionBoxMOB.png','images/MoneyCounter.png','images/block.png','images/blockHover.png','images/blockCorrect.png','images/blockIncorrect.png','images/cross.png','images/IntroVideo.mp4']
                for img in targets:
                    p = base_dir / img
                    if p.exists():
                        uri = to_data_uri(p)
                        h = h.replace(img, uri)
                        h = h.replace(f'./{img}', uri)
                try:
                    h = h.replace('<video id="introVideo" preload="auto">', '<video id="introVideo" preload="auto" muted>')
                except Exception:
                    pass
                return h

            # Inline audio by replacing both relative and ./relative occurrences
            def inline_audio(h):
                music = ['sounds/Music/0_to_1000.mp3','sounds/Music/2000_to_32000.mp3','sounds/Music/64000.mp3','sounds/Music/125000_to_250000.mp3','sounds/Music/500000.mp3','sounds/Music/1000000.mp3']
                effects = ['sounds/Effects/correct answer.mp3','sounds/Effects/final answer.mp3','sounds/Effects/lets play.mp3','sounds/Effects/phone a friend.mp3','sounds/Effects/wrong answer.mp3','sounds/Effects/commerical break.mp3','sounds/Effects/blast.mp3','sounds/Effects/Winner.mp3','sounds/Effects/tick-tock.mp3']
                for a in music + effects:
                    p = base_dir / a
                    if p.exists():
                        uri = to_data_uri(p)
                        h = h.replace(a, uri)
                        h = h.replace(f'./{a}', uri)
                return h

            html = inline_css(html)
            html = inline_js(html)
            html = inline_images(html)
            html = inline_audio(html)
            try:
                html = html.replace(
                    "</head>",
                    "<style>"
                    ".progressBar{background:#020617 !important;border:1px solid rgba(227,171,40,0.75) !important;border-radius:10px !important;overflow:hidden !important;}"
                    ".progressLevel{background:#E3AB28 !important;min-height:24px !important;border-radius:9px !important;}"
                    ".explanationBlock{background:transparent !important;border:none !important;box-shadow:none !important;padding:0 !important;}"
                    ".explanationBox{border-radius:14px !important;}"
                    "</style></head>"
                )
            except Exception:
                pass
            try:
                html = html.replace('</head>', '<meta name="google" content="notranslate"><style>#leaderboard{display:none}#gameWindow{display:none}#endGameCutScene{display:none}</style></head>')
            except Exception:
                pass
            # Inject minimal stub for jQuery/TimeCircles to run offline
            stub_js = """
<script>(function(){
function $(sel){var els=Array.prototype.slice.call(document.querySelectorAll(sel));function W(els){return {els:els,html:function(v){if(v!==undefined){els.forEach(function(e){e.innerHTML=v});return this;}return els[0]?els[0].innerHTML:'';},text:function(v){if(v!==undefined){els.forEach(function(e){e.textContent=v});return this;}return els[0]?els[0].textContent:'';},prop:function(n,v){els.forEach(function(e){e[n]=v});return this;},animateNumber:function(opts){var t=els[0];if(t){if(opts&&typeof opts.numberStep==='function'){opts.numberStep(opts.number,{elem:t});}else{t.textContent=String((opts&&opts.number)||'');}}return this;},fadeIn:function(){els.forEach(function(e){e.style.display=''});return this;},fadeOut:function(){els.forEach(function(e){e.style.display='none'});return this;},stop:function(){return this;},addClass:function(c){els.forEach(function(e){e.classList.add(c)});return this;},removeClass:function(c){els.forEach(function(e){e.classList.remove(c)});return this;},hide:function(){els.forEach(function(e){e.style.display='none'});return this;},show:function(){els.forEach(function(e){e.style.display=''});return this;},one:function(evt,fn){els.forEach(function(e){function once(ev){fn.call(e,ev);e.removeEventListener(evt,once);}e.addEventListener(evt,once);});return this;},on:function(evt,fn){els.forEach(function(e){e.addEventListener(evt,fn)});return this;},closest:function(sel){return W(els.map(function(e){return e.closest(sel)}).filter(Boolean));},TimeCircles:function(opts){var el=els[0];if(!el) return {};if(!el.__tc){(function(){var time=parseInt(el.getAttribute('data-timer')||'60',10);var interval=null;var listeners=[];el.__tc={stop:function(){if(interval){clearInterval(interval);interval=null;}},restart:function(){this.stop();time=parseInt(el.getAttribute('data-timer')||'60',10);interval=setInterval(function(){time--;listeners.forEach(function(cb){cb();});},1000);},addListener:function(cb){listeners.push(function(){cb();});},getTime:function(){return time;}}})();}return el.__tc;}};}return W(els);}window.$=$;})();</script>
"""
            html = html
            # Replace the above stub with a syntax-safe version to avoid parse errors
            safe_stub = r"""
<script>(function(){
 function wrap(els){var api={els:els,fn:{},html:function(v){if(v!==undefined){els.forEach(function(e){e.innerHTML=v});return this;}return els[0]?els[0].innerHTML:'';},text:function(v){if(v!==undefined){els.forEach(function(e){e.textContent=v});return this;}return els[0]?els[0].textContent:'';},prop:function(n,v){els.forEach(function(e){e[n]=v});return this;},data:function(k,v){if(v===undefined){return els[0]? els[0].getAttribute('data-'+k): undefined;} els.forEach(function(e){e.setAttribute('data-'+k,v)}); return this;},animate:function(props,dur){els.forEach(function(e){ for(var k in (props||{})){ try{ e.style[k]=String(props[k]); }catch(ex){} } }); return this;},animateNumber:function(opts){var t=els[0];if(t){if(opts&&typeof opts.numberStep==='function'){opts.numberStep(opts.number,{elem:t});}else{t.textContent=String((opts&&opts.number)||'');}}return this;},fadeIn:function(){els.forEach(function(e){e.style.display='block'});return this;},fadeOut:function(){els.forEach(function(e){e.style.display='none'});return this;},stop:function(){return this;},addClass:function(c){els.forEach(function(e){ String(c||'').split(/\s+/).filter(Boolean).forEach(function(tok){ try{ e.classList.add(tok); }catch(ex){} }); });return this;},removeClass:function(c){els.forEach(function(e){ String(c||'').split(/\s+/).filter(Boolean).forEach(function(tok){ try{ e.classList.remove(tok); }catch(ex){} }); });return this;},hide:function(){els.forEach(function(e){e.style.display='none'});return this;},show:function(){els.forEach(function(e){e.style.display='block'});return this;},focus:function(){ try{ if(els[0]&&typeof els[0].focus==='function'){ els[0].focus(); } }catch(e){} return this; },one:function(evt,fn){els.forEach(function(e){function once(ev){fn.call(e,ev);e.removeEventListener(evt,once);}e.addEventListener(evt,once);});return this;},on:function(evt,fn){els.forEach(function(e){e.__listeners=e.__listeners||{};e.__listeners[evt]=e.__listeners[evt]||[];e.__listeners[evt].push(fn);e.addEventListener(evt,fn)});return this;},off:function(evt){els.forEach(function(e){try{if(e.__listeners&&e.__listeners[evt]){e.__listeners[evt].forEach(function(fn){e.removeEventListener(evt,fn)});e.__listeners[evt]=[];}}catch(ex){} });return this;},click:function(fn){return this.on('click',fn);},closest:function(sel){return wrap(els.map(function(e){return e.closest(sel)}).filter(Boolean));},ready:function(fn){var d=(els[0]===document); if(d){ if(document.readyState!=='loading'){ try{ fn(); }catch(e){} } else { document.addEventListener('DOMContentLoaded', fn); } } return this;},TimeCircles:function(){var el=els[0];if(!el) return {stop:function(){},restart:function(){},addListener:function(){},getTime:function(){return 0;}}; if(!el.__tc){(function(){var time=parseInt(el.getAttribute('data-timer')||'60',10);var interval=null;var listeners=[];el.__tc={stop:function(){if(interval){clearInterval(interval);interval=null;}},restart:function(){if(interval){clearInterval(interval);} time=parseInt(el.getAttribute('data-timer')||'60',10); interval=setInterval(function(){time--;listeners.forEach(function(cb){try{cb();}catch(e){}});},1000);},addListener:function(cb){listeners.push(cb);},getTime:function(){return time;}};})();} return el.__tc;}};els.forEach(function(e,i){api[i]=e});return api}
function $(arg){
  if(typeof arg==='function'){if(document.readyState!=='loading'){arg();}else{document.addEventListener('DOMContentLoaded', arg);}return wrap([document]);}
  var isWin=(arg===window)||(Object.prototype.toString.call(arg)==='[object Window]');
  if(isWin||arg===document){return wrap([isWin?window:document]);}
  if(arg&&arg.nodeType===1){return wrap([arg]);}
  var sel=String(arg||'');
  // Support jQuery :contains("text") pseudo
  var containsMatch = sel.match(/^(.*?):contains\((['\"]?)(.*?)\2\)/);
  var els;
  if(containsMatch){
    var baseSel = containsMatch[1] || '*';
    var text = containsMatch[3] || '';
    try{
      els = Array.prototype.slice.call(document.querySelectorAll(baseSel)).filter(function(e){ return (e.textContent||'').indexOf(text) !== -1; });
    }catch(e){ els = []; }
  } else {
    els = Array.prototype.slice.call(document.querySelectorAll(sel));
  }
  return wrap(els)
}
window.$=$;window.jQuery=$;
 // Add .ready on wrapper for $(document).ready(...)
 try{ var dW = wrap([document]); dW.ready = function(fn){ if(document.readyState!=='loading'){ try{ fn(); }catch(e){} } else { document.addEventListener('DOMContentLoaded', fn); } return dW; }; }catch(e){}
 // Provide $.animateNumber.numberStepFactories.separator
 try{ $.animateNumber = { numberStepFactories: { separator: function(sep){ return function(now, tween){ try{ var el = tween.elem; var s = String(Math.round(now)); el.textContent = s.replace(/\B(?=(\d{3})+(?!\d))/g, sep); }catch(e){} }; } } }; }catch(e){}
 try{ $.getJSON = function(url, cb){ try{ fetch(url).then(function(r){ return r.json(); }).then(function(data){ try{ cb(data); }catch(e){} }).catch(function(){ try{ cb({results:[]}); }catch(e){} }); } catch(e){ try{ cb({results:[]}); }catch(_){ } } }; }catch(e){}
 // Provide $.proxy minimal implementation
 try{ $.proxy = function(fn, ctx){ try{ if (typeof fn === 'string' && ctx && typeof ctx[fn] === 'function'){ var f = ctx[fn]; return function(){ return f.apply(ctx, arguments); }; } if (typeof fn === 'function'){ return function(){ return fn.apply(ctx || this, arguments); }; } }catch(e){} return function(){}; }; }catch(e){}
})();</script>
"""
            import re
            html = re.sub(r'<script>[^<]*TimeCircles[^<]*</script>', '', html)
            # Remove any external http(s) script/link tags
            html = re.sub(r'<script[^>]+src\s*=\s*"https?://[^"]+"[^>]*></script>', '', html)
            html = re.sub(r'<link[^>]+href\s*=\s*"https?://[^"]+"[^>]*>', '', html)
            html = html.replace('</head>', safe_stub + '</head>')

            # Inject teacher questions
            import json as _json
            # Build millionaire assets base64 mapping
            try:
                m_assets = {}
                def enc(rel):
                    p = base_dir / rel
                    return to_data_uri(p) if p.exists() else ''
                m_assets['logo_base64'] = enc('images/Logo.png')
                m_assets['intro_video_base64'] = enc('images/IntroVideo.mp4')
                m_assets['music_tracks_base64'] = [
                    enc('sounds/Music/0_to_1000.mp3'),
                    enc('sounds/Music/2000_to_32000.mp3'),
                    enc('sounds/Music/64000.mp3'),
                    enc('sounds/Music/125000_to_250000.mp3'),
                    enc('sounds/Music/500000.mp3'),
                    enc('sounds/Music/1000000.mp3')
                ]
                m_assets['effects_tracks_base64'] = [
                    enc('sounds/Effects/correct answer.mp3'),
                    enc('sounds/Effects/final answer.mp3'),
                    enc('sounds/Effects/lets play.mp3'),
                    enc('sounds/Effects/phone a friend.mp3'),
                    enc('sounds/Effects/wrong answer.mp3'),
                    enc('sounds/Effects/commerical break.mp3'),
                    enc('sounds/Effects/blast.mp3'),
                    enc('sounds/Effects/Winner.mp3'),
                    enc('sounds/Effects/tick-tock.mp3')
                ]
                m_assets['background_images_base64'] = {
                    'Background': enc('images/background.png'),
                    'BackgroundGame': enc('images/backgroundGame.png'),
                    'QuestionBox': enc('images/QuestionBox.png'),
                    'QuestionBoxMOB': enc('images/QuestionBoxMOB.png'),
                    'MoneyCounter': enc('images/MoneyCounter.png'),
                    'Block': enc('images/block.png'),
                    'BlockHover': enc('images/blockHover.png'),
                    'BlockCorrect': enc('images/blockCorrect.png'),
                    'BlockIncorrect': enc('images/blockIncorrect.png'),
                    'Cross': enc('images/cross.png')
                }
            except Exception:
                m_assets = {}
            normalized_questions = self._normalize_millionaire_questions_for_runtime(
                list(project_data.get('questions', []) or [])
            )
            enriched_game_config = self._without_feedback_sound_pools(project_data.get('game_config', {}) or {})
            payload = _json.dumps({
                'project_name': project_data.get('name','Ai Là Triệu Phú'),
                'language': project_data.get('language','vi'),
                'questions': normalized_questions,
                'game_config': { **enriched_game_config, 'millionaire_assets': m_assets }
            }, ensure_ascii=False)
            inject_tag = f"<script id=\"game-data\" type=\"application/json\">{payload}</script>"
            teacher_map = (
                "<script>(function(){try{var gd=document.getElementById('game-data');"
                "var obj=gd? JSON.parse(gd.textContent||'{}') : {};"
                "var qs=Array.isArray(obj.questions)? obj.questions: [];"
                "window.EDU_PROJECT=obj;"
                "window.EDU_MILLIONAIRE_MODE=String((obj.game_config&&obj.game_config.export_mode)||'student').toLowerCase()==='teaching'?'teaching':'student';"
                "window.__EP_MILLIONAIRE_TEACHING=window.EDU_MILLIONAIRE_MODE==='teaching';"
                "function normalizeOptions(q){"
                "var opts=q.options||q.answers||q.choices||null;"
                "if(!Array.isArray(opts)||opts.length<2){"
                "var variants=[['option_a','option_b','option_c','option_d'],['answerA','answerB','answerC','answerD'],['A','B','C','D'],['option1','option2','option3','option4'],['pa','pb','pc','pd'],['ansA','ansB','ansC','ansD']];"
                "for(var vi=0;vi<variants.length;vi++){var keys=variants[vi];var arr=[q[keys[0]],q[keys[1]],q[keys[2]],q[keys[3]]].filter(function(x){return x!==undefined&&x!==null});if(arr&&arr.length>=2){opts=arr;break;}}"
                "}"
                "if(Array.isArray(opts)&&opts.length&&typeof opts[0]==='object'){"
                "opts=opts.map(function(opt){if(!opt||typeof opt!=='object'){return String(opt||'');}return String(opt.text||opt.label||opt.value||'');});"
                "}"
                "opts=Array.isArray(opts)? opts.slice(0,4):[]; while(opts.length<4) opts.push(''); return opts;}"
                "function map(q){var opts=normalizeOptions(q);"
                "var ca=(q.correct_answer!==undefined&&q.correct_answer!==null)? q.correct_answer : q.correctAnswer;"
                "var idx=0; if(typeof ca==='number'){idx=Math.max(0,Math.min(3,ca));}"
                "else if(typeof ca==='string'){var L=['A','B','C','D'];var up=ca.toUpperCase();var li=L.indexOf(up);"
                "idx=li>=0?li:Math.max(0,(opts.indexOf(ca)));}"
                "var tl=parseInt(q.time_limit||q.time||(obj.game_config&&obj.game_config.question_time)||60,10);"
                "if(!isFinite(tl)||tl<=0){tl=parseInt((obj.game_config&&obj.game_config.question_time)||60,10);}"
                "var expl=(q.explanation||q.explain||q.detail||q.solution||'');"
                "return {question:(q.question||q.text||''),correct_answer:String(opts[idx]||''),"
                "incorrect_answers:opts.filter(function(o,i){return i!==idx;}).slice(0,3),time_limit:tl,explanation:expl};}"
                "window.EDU_QUESTIONS=qs.map(map).slice(0,15);"
                "var assets=(obj.game_config&&obj.game_config.millionaire_assets)||{};"
                "window.EDU_MILLIONAIRE_ASSETS=assets;"
                "try{var m=assets.music_tracks_base64||[];var efx=assets.effects_tracks_base64||[];"
                "var ms=document.querySelectorAll('audio#music');"
                "for(var i=0;i<ms.length;i++){var u=m[i]||m[0];if(!u)continue;try{ms[i].src=u;var s=ms[i].querySelector('source');if(s)s.src=u;}catch(ex){}}"
                "var es=document.querySelectorAll('audio#effects');"
                "for(var j=0;j<es.length;j++){var u2=efx[j]||efx[0];if(!u2)continue;try{es[j].src=u2;var s2=es[j].querySelector('source');if(s2)s2.src=u2;}catch(ex2){}}"
                "}catch(_){}}catch(e){}})();</script>"
            )
            if '<body>' in html:
                html = html.replace('<body>', '<body>\n' + inject_tag + "\n" + teacher_map)
            else:
                html = html + "\n" + inject_tag + "\n" + teacher_map

            # Re-bind Exit button (Exit Game) without Firebase leaderboard.js
            exit_handler = (
                "<script>(function(){"
                "function bindExit(){"
                " try{var b=document.getElementById('exitGameBtn');if(!b)return;"
                " b.addEventListener('click',function(){"
                "  try{var gw=document.getElementById('gameWindow');if(gw){gw.style.display='none';}}catch(e){}"
                "  setTimeout(function(){"
                "   try{if(typeof window.resetToHome==='function'){window.resetToHome();}else{location.reload();}}catch(e){}"
                "  },600);"
                " });}catch(e){}"
                "}"
                "if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',bindExit);}else{bindExit();}"
                "})();</script>"
            )
            if '</body>' in html:
                html = html.replace('</body>', exit_handler + '</body>')
            else:
                html = html + exit_handler

            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(html, encoding='utf-8')
            return True
        
        except Exception as e:
            print(f"Error exporting Millionaire single file: {e}")
            return False

    def _export_millionaire_packed(self, project_data: Dict, html_file: Path, css_file: Path, js_file: Path) -> bool:
        try:
            base_dir = self.assets_dir / 'millionaire'
            # Load millionaire index.html with decryption if bundled
            try:
                html = load_asset_text('assets_bundle/millionaire/index.html')
            except FileNotFoundError:
                print('Millionaire index.html missing')
                return False
            # Remove external CSS links
            extern_css = [
                'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
                'https://use.fontawesome.com/releases/v5.2.0/css/all.css',
                'https://cdn.rawgit.com/konpa/devicon/df6431e323547add1b4cf45992913f15286456d3/devicon.min.css',
                'https://fonts.googleapis.com/css?family=Roboto',
                'https://cdnjs.cloudflare.com/ajax/libs/timecircles/1.5.3/TimeCircles.min.css'
            ]
            for url in extern_css:
                html = html.replace(f'<link rel="stylesheet" href="{url}">', '')
                html = html.replace(f'<link href="{url}" rel="stylesheet">', '')
            # Build bundled CSS from local files, rewriting url(...) to data URIs
            import re, mimetypes, base64
            def to_data_uri(path: Path) -> str:
                mime, _ = mimetypes.guess_type(path.name)
                if not mime:
                    ext = path.suffix.lower()
                    if ext in ['.png']: mime='image/png'
                    elif ext in ['.jpg','.jpeg']: mime='image/jpeg'
                    else: mime='application/octet-stream'
                data = base64.b64encode(path.read_bytes()).decode('ascii')
                return f'data:{mime};base64,{data}'
            def rewrite_css_urls(css_text: str) -> str:
                def repl(m):
                    raw = m.group(1).strip().strip('"').strip("'")
                    if raw.startswith('http://') or raw.startswith('https://'):
                        return 'url()'
                    rp = raw.lstrip('./')
                    pth = (base_dir / rp).resolve()
                    if pth.exists():
                        return 'url(' + to_data_uri(pth) + ')'
                    return 'url()'
                return re.sub(r'url\(\s*([^\)]+)\s*\)', repl, css_text)
            css_bundle = ''
            for css_name in ['css/styles.css','css/mobile.css']:
                try:
                    css = load_asset_text(f'assets_bundle/millionaire/{css_name}')
                    css_bundle += rewrite_css_urls(css) + '\n'
                except FileNotFoundError:
                    pass
            css_bundle += """
.progressBar{background:#020617 !important;border:1px solid rgba(227,171,40,0.75) !important;border-radius:10px !important;overflow:hidden !important;}
.progressLevel{background:#E3AB28 !important;min-height:24px !important;border-radius:9px !important;}
.progressLevel:after{content:"" !important;position:absolute !important;left:50% !important;top:0px !important;transform:translate(-50%,-50%) !important;width:14px !important;height:14px !important;border-radius:50% !important;background:#E3AB28 !important;border:2px solid #020617 !important;}
"""
            css_file.parent.mkdir(parents=True, exist_ok=True)
            css_file.write_text(css_bundle, encoding='utf-8')
            # Remove local CSS tags and insert bundled one
            for css_name in ['css/styles.css','css/mobile.css']:
                html = html.replace(f'<link rel="stylesheet" href="{css_name}">', '')
                html = html.replace(f'<link href="{css_name}" rel="stylesheet">', '')
            html = html.replace('</head>', f'<link rel="stylesheet" href="{css_file.name}"></head>')
            # Build bundled JS: include stub for jQuery/TimeCircles then local scripts
            stub_js = (
                "(function(){\n"+
                "var $ = function(sel){\n"+
                " if (typeof sel==='function'){if(document.readyState!=='loading'){sel();}else{document.addEventListener('DOMContentLoaded', sel);} return {els:[document], on:function(){return this;}, one:function(){return this;}, fadeIn:function(){return this;}, fadeOut:function(){return this;}, html:function(){return this;}, text:function(){return this;}, animateNumber:function(){return this;}, TimeCircles:function(){return {stop:function(){},restart:function(){},addListener:function(){},getTime:function(){return 60;}}} };}\n"+
                " var els = Array.prototype.slice.call(document.querySelectorAll(String(sel||'')));\n"+
                " return { els: els,\n"+
                "  on:function(evt,fn){els.forEach(function(e){e.addEventListener(evt,fn);});return this;},\n"+
                "  one:function(evt,fn){els.forEach(function(e){function once(ev){fn.call(e,ev);e.removeEventListener(evt,once);}e.addEventListener(evt,once);}return this;},\n"+
                "  fadeIn:function(){els.forEach(function(e){e.style.display='';});return this;},\n"+
                "  fadeOut:function(){els.forEach(function(e){e.style.display='none';});return this;},\n"+
                "  stop:function(){return this;},\n"+
                "  html:function(v){if(v!==undefined){els.forEach(function(e){e.innerHTML=v;});return this;}return els[0]?els[0].innerHTML:'';},\n"+
                "  text:function(v){if(v!==undefined){els.forEach(function(e){e.textContent=v;});return this;}return els[0]?els[0].textContent:'';},\n"+
                "  animate:function(props,dur){els.forEach(function(e){ for(var k in (props||{})){ try{ e.style[k]=String(props[k]); }catch(ex){} } }); return this;},\n"+
                "  animateNumber:function(opts){var t=els[0];if(!t)return this;if(opts&&typeof opts.numberStep==='function'){opts.numberStep(opts.number,{elem:t});}else{t.textContent=String((opts&&opts.number)||'');}return this;},\n"+
                "  TimeCircles:function(){var el=els[0];if(!el)return {stop:function(){},restart:function(){},addListener:function(){},getTime:function(){return 60;}}; if(!el.__tc){(function(){var time=parseInt(el.getAttribute('data-timer')||'60',10);var interval=null;var listeners=[]; el.__tc={ stop:function(){if(interval){clearInterval(interval);interval=null;}}, restart:function(){if(interval){clearInterval(interval);} time=parseInt(el.getAttribute('data-timer')||'60',10); interval=setInterval(function(){time--;listeners.forEach(function(cb){try{cb();}catch(e){});},1000);}, addListener:function(cb){listeners.push(cb);}, getTime:function(){return time;} };})();} return el.__tc;}\n"+
                " };\n"+
                "};\n"+
                "$.fn = {}; window.$ = $; window.jQuery = $;\n"+
                "})();\n"
            )
            js_bundle = stub_js
            for js_name in ['js/sounds.js','js/app.js','js/functions.js']:
                try:
                    js_bundle += load_asset_text(f'assets_bundle/millionaire/{js_name}') + '\n'
                except FileNotFoundError:
                    pass
            # Append lightweight handler for Exit Game button (no Firebase)
            js_bundle += (
                "(function(){"
                "function bindExit(){"
                " try{var b=document.getElementById('exitGameBtn');if(!b)return;"
                " b.addEventListener('click',function(){"
                "  try{var gw=document.getElementById('gameWindow');if(gw){gw.style.display='none';}}catch(e){}"
                "  setTimeout(function(){"
                "   try{if(typeof window.resetToHome==='function'){window.resetToHome();}else{location.reload();}}catch(e){}"
                "  },600);"
                " });}catch(e){}"
                "}"
                "if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',bindExit);}else{bindExit();}"
                "})();\n"
            )
            js_file.parent.mkdir(parents=True, exist_ok=True)
            js_file.write_text(js_bundle, encoding='utf-8')
            # Remove all JS script tags and add one bundle reference
            import re
            html = re.sub(r'<script[^>]+src="[^"]+"[^>]*></script>', '', html)
            html = html.replace('</body>', f'<script src="{js_file.name}"></script></body>')
            # Inline images/video/audio sources to data URIs
            def to_data_uri_any(p: Path) -> str:
                mime, _ = mimetypes.guess_type(p.name)
                if not mime:
                    ext = p.suffix.lower()
                    if ext in ['.png']: mime='image/png'
                    elif ext in ['.jpg','.jpeg']: mime='image/jpeg'
                    elif ext in ['.mp3']: mime='audio/mpeg'
                    elif ext in ['.mp4']: mime='video/mp4'
                    else: mime='application/octet-stream'
                data = base64.b64encode(p.read_bytes()).decode('ascii')
                return f'data:{mime};base64,{data}'
            media_targets = [
                'images/Logo.png','images/background.png','images/backgroundGame.png','images/QuestionBox.png','images/QuestionBoxMOB.png','images/MoneyCounter.png','images/block.png','images/blockHover.png','images/blockCorrect.png','images/blockIncorrect.png','images/cross.png','images/IntroVideo.mp4'
            ]
            for t in media_targets:
                p = base_dir / t
                if p.exists():
                    uri = to_data_uri_any(p)
                    html = html.replace(t, uri)
                    html = html.replace('./'+t, uri)
            for a in ['sounds/Music/0_to_1000.mp3','sounds/Music/2000_to_32000.mp3','sounds/Music/64000.mp3','sounds/Music/125000_to_250000.mp3','sounds/Music/500000.mp3','sounds/Music/1000000.mp3','sounds/Effects/correct answer.mp3','sounds/Effects/final answer.mp3','sounds/Effects/lets play.mp3','sounds/Effects/phone a friend.mp3','sounds/Effects/wrong answer.mp3','sounds/Effects/commerical break.mp3','sounds/Effects/blast.mp3','sounds/Effects/Winner.mp3','sounds/Effects/tick-tock.mp3']:
                p = base_dir / a
                if p.exists():
                    uri = to_data_uri_any(p)
                    html = html.replace(a, uri)
                    html = html.replace('./'+a, uri)
            enriched_game_config = self._without_feedback_sound_pools(project_data.get('game_config', {}) or {})
            payload = self._safe_json_dumps({
                'project_name': project_data.get('name','Ai Là Triệu Phú'),
                'language': project_data.get('language','vi'),
                'questions': list(project_data.get('questions',[]) or []),
                'game_config': enriched_game_config
            })
            inject_tag = f"<script id=\"game-data\" type=\"application/json\">{payload}</script>"
            bridge_tag = (
                "<script>(function(){try{var gd=document.getElementById('game-data');"
                "var p=gd?JSON.parse(gd.textContent||'{}'):{};"
                "var qs=Array.isArray(p.questions)?p.questions:[];"
                "function map(q){var opts=q.options||q.answers||q.choices||[];"
                "opts=Array.isArray(opts)?opts.slice(0,4):[];while(opts.length<4)opts.push('');"
                "var ca=(q.correct_answer!==undefined&&q.correct_answer!==null)?q.correct_answer:q.correctAnswer;"
                "var idx=0;if(typeof ca==='number'){idx=Math.max(0,Math.min(3,ca));}"
                "else if(typeof ca==='string'){var L=['A','B','C','D'];var up=ca.toUpperCase();var li=L.indexOf(up);idx=li>=0?li:Math.max(0,opts.indexOf(ca));}"
                "var tl=parseInt(q.time_limit||q.time||(p.game_config&&p.game_config.question_time)||60,10);"
                "if(!isFinite(tl)||tl<=0){tl=parseInt((p.game_config&&p.game_config.question_time)||60,10);}"
                "return{question:(q.question||q.text||''),correct_answer:String(opts[idx]||''),incorrect_answers:opts.filter(function(o,i){return i!==idx;}).slice(0,3),time_limit:tl,explanation:(q.explanation||q.explain||q.detail||q.solution||'')};}"
                "window.EDU_PROJECT=p;"
                "window.EDU_MILLIONAIRE_MODE=String((p.game_config&&p.game_config.export_mode)||'student').toLowerCase()==='teaching'?'teaching':'student';"
                "window.__EP_MILLIONAIRE_TEACHING=window.EDU_MILLIONAIRE_MODE==='teaching';"
                "window.DEFAULT_QUESTION_TIME=parseInt((p.game_config&&(p.game_config.question_time||p.game_config.time_limit))||60,10);"
                "window.EDU_QUESTIONS=qs.map(map).slice(0,15);}catch(e){}})();</script>"
            )
            if '<body>' in html:
                html = html.replace('<body>', '<body>\n' + inject_tag + "\n" + bridge_tag)
            else:
                html = html + "\n" + inject_tag + "\n" + bridge_tag
            html = self._inject_favicon(html)
            html_file.write_text(html, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error exporting Millionaire packed: {e}")
            return False

    def _export_fishing_single_file(self, project_data: Dict, output_file: Path) -> bool:
        try:
            # Load template (with decryption if built from asset_loader)
            content = load_asset_text('assets_bundle/templates_fish/fishing_game.html')
            from jinja2 import Template as _T
            _tmpl = _T(content)

            # Build context based on existing generator, but ensure base64 everywhere
            game_config = dict(project_data.get('game_config', {}) or {})
            fishing_settings = dict(game_config.get('fishing_settings', {}) or {})
            fish_count = int(game_config.get('fish_count', fishing_settings.get('fish_count', 10)) or 10)
            base_speed = float(game_config.get('base_speed', fishing_settings.get('fish_speed', 2.0)) or 2.0)
            time_limit = int(game_config.get('time_limit', 60) or 60)
            question_time = int(game_config.get('question_time', game_config.get('question_time_per_question', 30)) or 30)
            show_explanations = bool(game_config.get('show_explanations', game_config.get('show_correct_answer', True)))
            randomize_questions = bool(game_config.get('randomize_questions', True))
            lang_for_text = project_data.get('language', 'vi')

            # Normalize questions
            qs_in = list(project_data.get('questions', []) or [])
            norm_qs: List[Dict] = []
            def _norm_type(q: Dict) -> str:
                raw_type = (q.get('type') or q.get('question_type') or q.get('q_type') or q.get('kind') or '')
                rt = str(raw_type or '').strip().lower().replace('-', '_').replace(' ', '_').replace('/', '_')
                if rt in ('multiple_choice', 'multiple', 'mcq', 'choice', 'quiz', 'trac_nghiem', 'trắc_nghiệm'):
                    return 'multiple_choice'
                if rt in ('true_false', 'truefalse', 'boolean', 'tf', 'dung_sai', 'đúng_sai'):
                    return 'true_false'
                if rt in ('fill_blank', 'fillblank', 'cloze', 'dien_cho_trong', 'điền_chỗ_trống'):
                    return 'fill_blank'
                if rt in ('short_answer', 'shortanswer', 'essay', 'tu_luan', 'tự_luận'):
                    return 'short_answer'
                if rt in ('matching', 'match', 'pairing', 'ghep_doi', 'ghép_đôi'):
                    return 'matching'
                pairs_guess = q.get('match_pairs') or q.get('pairs') or q.get('matchPairs') or q.get('pairs_data') or []
                if isinstance(pairs_guess, list) and len(pairs_guess) > 0:
                    return 'matching'
                ca = q.get('correct_answer')
                if isinstance(ca, bool):
                    return 'true_false'
                return 'multiple_choice'

            def _norm_pairs(pairs_in) -> List[Dict]:
                if not isinstance(pairs_in, list):
                    return []
                out: List[Dict] = []
                for p in pairs_in:
                    if isinstance(p, (list, tuple)) and len(p) >= 2:
                        out.append({'left': str(p[0]), 'right': str(p[1])})
                        continue
                    if isinstance(p, dict) and ('left' in p) and ('right' in p):
                        out.append({'left': str(p.get('left', '')), 'right': str(p.get('right', ''))})
                        continue
                return out

            def _norm_options_and_correct(q: Dict) -> tuple[list[str], int]:
                options = q.get('options') or q.get('choices') or q.get('answers') or []
                if not options:
                    variants = [
                        ('option_a', 'option_b', 'option_c', 'option_d'),
                        ('answerA', 'answerB', 'answerC', 'answerD'),
                        ('A', 'B', 'C', 'D'),
                        ('option1', 'option2', 'option3', 'option4'),
                        ('pa', 'pb', 'pc', 'pd'),
                        ('ansA', 'ansB', 'ansC', 'ansD'),
                    ]
                    for keys in variants:
                        arr = [q.get(keys[0]), q.get(keys[1]), q.get(keys[2]), q.get(keys[3])]
                        arr = [x for x in arr if x is not None]
                        if arr and len(arr) >= 2:
                            options = arr
                            break

                correct_idx = 0
                opts_out: list[str] = []
                if isinstance(options, dict):
                    ordered = []
                    for k in ['A', 'B', 'C', 'D', 'E', 'F']:
                        if k in options:
                            ordered.append(options.get(k))
                    if not ordered:
                        ordered = list(options.values())
                    options = ordered

                if isinstance(options, list) and options and isinstance(options[0], dict):
                    for idx, opt in enumerate(options):
                        text = opt.get('text')
                        if text is None:
                            text = opt.get('label')
                        if text is None:
                            text = ''
                        opts_out.append(str(text))
                        try:
                            if bool(opt.get('correct', False)):
                                correct_idx = idx
                        except Exception:
                            pass
                elif isinstance(options, list):
                    opts_out = [str(o) for o in options]
                else:
                    opts_out = []

                ca_raw = q.get('correctAnswer')
                if ca_raw is None:
                    ca_raw = q.get('correct_answer')
                if ca_raw is None:
                    ca_raw = q.get('correctIndex')

                if isinstance(ca_raw, (int, float)):
                    try:
                        correct_idx = int(ca_raw)
                    except Exception:
                        pass
                elif isinstance(ca_raw, str):
                    letters = ['A', 'B', 'C', 'D', 'E', 'F']
                    s = ca_raw.strip().upper()
                    if s in letters:
                        correct_idx = letters.index(s)
                    else:
                        try:
                            correct_idx = opts_out.index(ca_raw)
                        except Exception:
                            pass

                if (not opts_out) or len(opts_out) < 2:
                    try:
                        opts_out = [
                            I18n.t('import.default.option_1', lang_for_text),
                            I18n.t('import.default.option_2', lang_for_text),
                            I18n.t('import.default.option_3', lang_for_text),
                            I18n.t('import.default.option_4', lang_for_text),
                        ]
                    except Exception:
                        opts_out = ['Option 1', 'Option 2', 'Option 3', 'Option 4']
                    correct_idx = 0

                if correct_idx < 0 or correct_idx >= len(opts_out):
                    correct_idx = 0

                return opts_out, correct_idx

            for q in qs_in:
                q_type = _norm_type(q if isinstance(q, dict) else {})
                qd = q if isinstance(q, dict) else {}
                nq: Dict = {
                    'question': qd.get('question') or qd.get('text') or '',
                    'type': q_type,
                    'time_limit': qd.get('time_limit'),
                    'explanation': qd.get('explanation') or qd.get('feedback') or '',
                }
                try:
                    image_base64 = qd.get('image_base64') or ''
                    if (not image_base64) and isinstance(qd.get('image'), str) and str(qd.get('image')).startswith('data:'):
                        image_base64 = str(qd.get('image'))
                    if image_base64:
                        nq['image_base64'] = image_base64
                except Exception:
                    pass

                if q_type == 'multiple_choice':
                    opts, ca_idx = _norm_options_and_correct(qd)
                    nq['options'] = opts
                    nq['correctAnswer'] = ca_idx
                    nq['correct_answer'] = ca_idx
                elif q_type == 'true_false':
                    ca = qd.get('correct_answer')
                    if ca is None:
                        ca = qd.get('correctAnswer')
                    if ca is None:
                        ca = qd.get('correct_answer_bool')
                    try:
                        if isinstance(ca, bool):
                            nq['correct_answer'] = ca
                        elif isinstance(ca, (int, float)):
                            nq['correct_answer'] = bool(ca)
                        else:
                            s = str(ca or '').strip().lower()
                            nq['correct_answer'] = s in ('true', 'đúng', 'dung', '1', 'yes', 'y')
                    except Exception:
                        nq['correct_answer'] = False
                    nq['options'] = ['Đúng', 'Sai']
                elif q_type in ('fill_blank', 'short_answer'):
                    ans = qd.get('answers') or qd.get('answer_list') or qd.get('correct_answers') or []
                    if not ans:
                        single_answer = qd.get('correct_answer')
                        if single_answer is None:
                            single_answer = qd.get('correctAnswer')
                        if single_answer is not None:
                            ans = [single_answer]
                    if isinstance(ans, str):
                        try:
                            ans = [s.strip() for s in ans.splitlines() if s.strip()]
                        except Exception:
                            ans = []
                    elif not isinstance(ans, list):
                        ans = [ans] if str(ans).strip() else []
                    normalized_answers = [str(a) for a in ans if str(a).strip()]
                    nq['answers'] = normalized_answers
                    nq['correct_answers'] = normalized_answers
                    if normalized_answers:
                        nq['correct_answer'] = normalized_answers[0]
                    try:
                        nq['case_sensitive'] = bool(qd.get('case_sensitive', False))
                    except Exception:
                        nq['case_sensitive'] = False
                    try:
                        nq['max_length'] = int(qd.get('max_length', 100))
                    except Exception:
                        nq['max_length'] = 100
                elif q_type == 'matching':
                    pairs_in = qd.get('match_pairs') or qd.get('pairs') or qd.get('matchPairs') or qd.get('pairs_data') or []
                    nq['pairs'] = _norm_pairs(pairs_in)
                    nq['match_pairs'] = nq.get('pairs')
                norm_qs.append(nq)
            # Always reorder question prefixes sequentially regardless of shuffle setting
            if isinstance(norm_qs, list):
                if randomize_questions:
                    import random as _rnd
                    _rnd.shuffle(norm_qs)
                norm_qs = norm_qs[:max(1, fish_count)]
                
                # Reorder question prefixes sequentially
                try:
                    for idx, q in enumerate(norm_qs):
                        raw_question = str(q.get('question', '') or '')
                        import re as _re
                        # Remove any repeated existing prefix patterns (câu 1, question 1, etc.)
                        cleaned = _re.sub(r'^(?:\s*(?:câu|question|pregunta|frage|q)\s*\d+\s*[:.-]?\s*)+', '', raw_question, flags=_re.IGNORECASE)
                        # Add new sequential prefix
                        qprefix = I18n.t('editor.question_prefix', lang_for_text)
                        q['question'] = f"{qprefix} {idx + 1}: {cleaned}"
                except Exception:
                    pass

            # Fish objects: prefer embedded base64; fall back to tiny_fish_base64
            fish_objects = list(game_config.get('fish_objects', []) or [])
            out_fish_objs: List[Dict] = []
            tiny64 = list(game_config.get('tiny_fish_base64', []) or [])
            for i, fo in enumerate(fish_objects):
                sprite_b64 = fo.get('sprite_base64') or fo.get('sprite')
                wrong_b64 = fo.get('wrong_sprite_base64') or fo.get('wrong_sprite')
                def _to_data_uri(s: str, def_fallback: Optional[str] = None) -> Optional[str]:
                    if not s: return def_fallback
                    s = str(s)
                    if s.startswith('data:'): return s
                    # Try reading relative asset path
                    try:
                        p = Path(s)
                        if not p.is_absolute():
                            base = self.assets_dir / 'kenney_platformer-kit' / 'PNG' / 'Default'
                            p = base / p.name
                        if p.exists():
                            import base64, mimetypes
                            mime, _ = mimetypes.guess_type(p.name)
                            data = base64.b64encode(p.read_bytes()).decode('ascii')
                            return f'data:{mime or "image/png"};base64,{data}'
                    except Exception:
                        pass
                    return def_fallback
                sprite_uri = _to_data_uri(sprite_b64, (tiny64[i % len(tiny64)] if tiny64 else None))
                wrong_uri = _to_data_uri(wrong_b64, sprite_uri)
                out_fish_objs.append({'sprite_base64': sprite_uri, 'wrong_sprite_base64': wrong_uri})
            if not out_fish_objs:
                # Build from tiny fish sources
                for i in range(max(4, min(8, len(tiny64) or 4))):
                    src = tiny64[i % len(tiny64)] if tiny64 else None
                    out_fish_objs.append({'sprite_base64': src or '', 'wrong_sprite_base64': src or ''})

            context = {
                'project_name': project_data.get('name', 'Fishing Game'),
                'questions': norm_qs,
                'game_config': {
                    'fish_count': fish_count,
                    'base_speed': base_speed,
                    'time_limit': time_limit,
                    'question_time': question_time,
                    'export_mode': str(game_config.get('export_mode', 'student') or 'student'),
                    'show_explanations': show_explanations,
                    'randomize_questions': randomize_questions,
                    'fish_objects': out_fish_objs,
                    'background_image_base64': game_config.get('background_image_base64'),
                    'backgrounds_base64': game_config.get('backgrounds_base64'),
                    'seaweed_assets_base64': game_config.get('seaweed_assets_base64'),
                    'decor_rocks_base64': game_config.get('decor_rocks_base64'),
                    'terrain_tiles_base64': game_config.get('terrain_tiles_base64'),
                    'tiny_fish_base64': game_config.get('tiny_fish_base64'),
                    'background_terrain_base64': game_config.get('background_terrain_base64'),
                    'background_terrain_top_base64': game_config.get('background_terrain_top_base64'),
                    'rock_assets_base64': game_config.get('rock_assets_base64'),
                    'background_soft_base64': game_config.get('background_soft_base64'),
                    'hud_digits_base64': game_config.get('hud_digits_base64'),
                    'scene_asset_map_base64': game_config.get('scene_asset_map_base64'),
                    'bgm_base64': game_config.get('bgm_base64'),
                    'click_sound_base64': game_config.get('click_sound_base64'),
                    'correct_sound_base64': game_config.get('correct_sound_base64'),
                    'wrong_sound_base64': game_config.get('wrong_sound_base64'),
                    'cute_effects': bool(game_config.get('cute_effects', False)),
                    'fish_size': fishing_settings.get('fish_size', 'Vừa')
                },
                'language': project_data.get('language', 'vi'),
                'game_type': 'fishing'
            }
            try:
                import base64, mimetypes
                from pathlib import Path as _P
                def _enc(name: str):
                    p = self.assets_dir / 'kenney_platformer-kit' / 'PNG' / 'Default' / name
                    if p.exists():
                        mime, _ = mimetypes.guess_type(p.name)
                        return f"data:{(mime or 'image/png')};base64," + base64.b64encode(p.read_bytes()).decode('ascii')
                    return ''
                gcx = context['game_config']
                scene_asset_files = [
                    'background_seaweed_a.png','background_seaweed_b.png','background_seaweed_c.png','background_seaweed_d.png',
                    'background_seaweed_e.png','background_seaweed_f.png','background_seaweed_g.png','background_seaweed_h.png',
                    'background_rock_a.png','background_rock_b.png','background_terrain.png','background_terrain_top.png',
                    'fish_blue.png','fish_green.png','fish_pink.png','fish_orange.png','fish_red.png','fish_brown.png',
                    'fish_grey.png','fish_grey_long_a.png','fish_grey_long_b.png',
                    'fish_blue_skeleton.png','fish_green_skeleton.png','fish_pink_skeleton.png','fish_orange_skeleton.png','fish_red_skeleton.png',
                    'seaweed_grass_a.png','seaweed_grass_b.png',
                    'seaweed_green_a.png','seaweed_green_b.png','seaweed_green_c.png','seaweed_green_d.png',
                    'seaweed_orange_a.png','seaweed_orange_b.png',
                    'seaweed_pink_a.png','seaweed_pink_b.png','seaweed_pink_c.png','seaweed_pink_d.png',
                    'rock_a.png','rock_b.png',
                    'terrain_sand_top_a.png','terrain_sand_top_b.png','terrain_sand_top_c.png','terrain_sand_top_d.png',
                    'terrain_sand_top_e.png','terrain_sand_top_f.png','terrain_sand_top_g.png','terrain_sand_top_h.png',
                    'terrain_sand_a.png','terrain_sand_b.png','terrain_sand_c.png','terrain_sand_d.png',
                    'terrain_dirt_a.png','terrain_dirt_b.png','terrain_dirt_c.png','terrain_dirt_d.png',
                    'terrain_dirt_top_a.png','terrain_dirt_top_b.png','terrain_dirt_top_c.png','terrain_dirt_top_d.png',
                    'terrain_dirt_top_e.png','terrain_dirt_top_f.png','terrain_dirt_top_g.png','terrain_dirt_top_h.png'
                ]
                if not gcx.get('scene_asset_map_base64'):
                    gcx['scene_asset_map_base64'] = {name: data for name, data in ((n, _enc(n)) for n in scene_asset_files) if data}
                if not gcx.get('background_terrain_base64'):
                    gcx['background_terrain_base64'] = _enc('background_terrain.png')
                if not gcx.get('background_terrain_top_base64'):
                    gcx['background_terrain_top_base64'] = _enc('background_terrain_top.png')
                if not (gcx.get('rock_assets_base64') or []):
                    gcx['rock_assets_base64'] = [a for a in [_enc('rock_a.png'), _enc('rock_b.png')] if a]
                if not gcx.get('hud_digits_base64'):
                    digits = {str(i): _enc(f"hud_number_{i}.png") for i in range(0, 10)}
                    digits.update({
                        'percent': _enc('hud_percent.png'),
                        'plus': _enc('hud_plus.png'),
                        'colon': _enc('hud_colon.png'),
                        'dot': _enc('hud_dot.png'),
                    })
                    gcx['hud_digits_base64'] = {k: v for k, v in digits.items() if v}
            except Exception:
                pass
            # Localized labels
            try:
                lang = context['language'] or 'vi'
                context.update({
                    'i18n_title': I18n.t('fishing.title', lang),
                    'i18n_score': I18n.t('quiz.score', lang),
                    'i18n_time': I18n.t('editor.time', lang),
                    'i18n_completed': I18n.t('quiz.completed', lang),
                    'i18n_play_again': I18n.t('quiz.play_again', lang),
                    'i18n_submit': I18n.t('quiz.submit', lang),
                    'i18n_next': I18n.t('quiz.next', lang),
                    'i18n_explain': I18n.t('quiz.explain', lang),
                    'i18n_correct_answer': I18n.t('quiz.correct_answer', lang),
                    'i18n_true': I18n.t('quiz.true', lang),
                    'i18n_false': I18n.t('quiz.false', lang),
                    'i18n_start_title': I18n.t('fishing.start_title', lang),
                    'i18n_start_button': I18n.t('fishing.start_button', lang),
                    'i18n_start_rules': I18n.t('fishing.start_rules', lang),
                    'i18n_audio_not_supported': I18n.t('fishing.audio_not_supported', lang),
                    'i18n_msg_low': I18n.t('quiz.msg_low', lang) or 'Cố gắng lên nhé!',
                    'i18n_msg_mid': I18n.t('quiz.msg_mid', lang) or 'Gần được rồi!',
                    'i18n_msg_high': I18n.t('quiz.msg_high', lang) or 'Xuất Sắc!',
                })
            except Exception:
                pass
            # Hard fallbacks to avoid blank start overlay if localization fails
            try:
                if not context.get('i18n_start_title'):
                    context['i18n_start_title'] = 'Start Game'
                if not context.get('i18n_start_button'):
                    context['i18n_start_button'] = 'Start'
                if not context.get('i18n_next'):
                    context['i18n_next'] = 'Next'
                if not context.get('i18n_explain'):
                    context['i18n_explain'] = 'Explanation'
                if not context.get('i18n_true'):
                    context['i18n_true'] = 'True'
                if not context.get('i18n_false'):
                    context['i18n_false'] = 'False'
            except Exception:
                pass

            html = _tmpl.render(**context)
            game_data_script = f'<script id="game-data" type="application/json">{self._safe_json_dumps(context)}</script>'
            if '</body>' in html:
                html = html.replace('</body>', game_data_script + '\n</body>')
            html = self._inject_favicon(html)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(html, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error exporting Fishing single file: {e}")
            return False

    def _generate_millionaire_html(self, project_data: Dict) -> str:
        """Render Millionaire using bundled index.html with teacher questions"""
        try:
            index_rel = 'assets_bundle/millionaire/index.html'
            if not get_asset_path(index_rel).exists():
                return "<html><body><h3>Millionaire index.html missing</h3></body></html>"
            content = load_asset_text(index_rel)
            # Inline local CSS/JS and key images to avoid broken assets in preview
            try:
                base_dir = self.assets_dir / 'millionaire'
                def _inline_css(h):
                    extern = [
                        'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css',
                        'https://use.fontawesome.com/releases/v5.2.0/css/all.css',
                        'https://cdn.rawgit.com/konpa/devicon/df6431e323547add1b4cf45992913f15286456d3/devicon.min.css',
                        'https://fonts.googleapis.com/css?family=Roboto',
                        'https://cdnjs.cloudflare.com/ajax/libs/timecircles/1.5.3/TimeCircles.min.css'
                    ]
                    for url in extern:
                        h = h.replace(f'<link rel="stylesheet" href="{url}">','')
                        h = h.replace(f'<link href="{url}" rel="stylesheet">','')
                    for css_name in ['css/styles.css','css/mobile.css']:
                        rel = f'assets_bundle/millionaire/{css_name}'
                        if get_asset_path(rel).exists():
                            css = load_asset_text(rel)
                            h = h.replace(f'<link rel="stylesheet" href="{css_name}">', f'<style>\n{css}\n</style>')
                    return h
                def _inline_js(h):
                    for js_name in ['js/sounds.js','js/app.js','js/functions.js']:
                        rel = f'assets_bundle/millionaire/{js_name}'
                        if get_asset_path(rel).exists():
                            js = load_asset_text(rel)
                            try:
                                import re as _re
                                # Remove hard dependency on jQuery .stop so code never breaks
                                js = _re.sub(r"\.stop\s*\([^)]*\)\s*\.animate\s*\(", ".animate(", js)
                                js = _re.sub(r"\.stop\s*\([^)]*\)", "", js)
                                # Explicitly remove chained "$(selector).stop(...)" patterns
                                js = _re.sub(r"(\$\([^)]*\))\s*\.stop\s*\([^)]*\)", r"\1", js)
                                # Guard TimeCircles().stop()
                                js = _re.sub(r"TimeCircles\(\)\.stop\(\)", "try{$('#timer').TimeCircles().stop();}catch(e){}", js)
                            except Exception:
                                pass
                            h = h.replace(f'<script src="{js_name}"></script>', f'<script>\n{js}\n</script>')
                            h = h.replace(f'<script src="./{js_name}"></script>', f'<script>\n{js}\n</script>')
                    # Patch inline shim in index.html to add stop method if missing
                    try:
                        import re as _re2
                        h = _re2.sub(r"(var\s+api\s*=\s*\{\s*els:els,)", r"\1 stop:function(){return api;},", h)
                    except Exception:
                        pass
                    extern = [
                        'https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js',
                        'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js',
                        'https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js',
                        'https://rawgithub.com/hiddentao/google-tts/master/google-tts.min.js',
                        'https://cdnjs.cloudflare.com/ajax/libs/jquery-animateNumber/0.0.14/jquery.animateNumber.min.js',
                        'https://cdnjs.cloudflare.com/ajax/libs/timecircles/1.5.3/TimeCircles.min.js',
                        'https://www.gstatic.com/firebasejs/5.0.4/firebase-app.js',
                        'https://www.gstatic.com/firebasejs/5.0.4/firebase-database.js'
                    ]
                    for url in extern:
                        h = h.replace(f'<script src="{url}"></script>','')
                    import re
                    # Remove any remaining http(s) script tags
                    h = re.sub(r'<script[^>]+src="https?://[^"]+"[^>]*></script>', '', h)
                    # Remove local plugin scripts we don't need (we stubbed equivalents)
                    for local in ['js/jquery.animateNumber.min.js','js/bootstrap.min.js','js/util.js','js/TimeCircles.min.js']:
                        h = h.replace(f'<script src="{local}"></script>', '')
                    return h
                def _inline_images(h):
                    from pathlib import Path
                    import base64, mimetypes
                    def to_uri(p: Path):
                        mime, _ = mimetypes.guess_type(p.name)
                        if not mime:
                            mime = 'image/png'
                        return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode('ascii')
                    for img in ['images/Logo.png','images/background.png','images/backgroundGame.png','images/QuestionBox.png','images/QuestionBoxMOB.png','images/MoneyCounter.png','images/block.png','images/blockHover.png','images/blockCorrect.png','images/blockIncorrect.png','images/cross.png','images/IntroVideo.mp4']:
                        p = base_dir / img
                        if p.exists():
                            uri = to_uri(p)
                            h = h.replace(img, uri)
                            h = h.replace(f'./{img}', uri)
                    return h
                def _inline_audio(h):
                    from pathlib import Path
                    import base64, mimetypes
                    def to_uri(p: Path):
                        mime, _ = mimetypes.guess_type(p.name)
                        if not mime:
                            mime = 'audio/mpeg'
                        return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode('ascii')
                    music = ['sounds/Music/0_to_1000.mp3','sounds/Music/2000_to_32000.mp3','sounds/Music/64000.mp3','sounds/Music/125000_to_250000.mp3','sounds/Music/500000.mp3','sounds/Music/1000000.mp3']
                    effects = ['sounds/Effects/correct answer.mp3','sounds/Effects/final answer.mp3','sounds/Effects/lets play.mp3','sounds/Effects/phone a friend.mp3','sounds/Effects/wrong answer.mp3','sounds/Effects/commerical break.mp3','sounds/Effects/blast.mp3','sounds/Effects/Winner.mp3','sounds/Effects/tick-tock.mp3']
                    for a in music + effects:
                        p = base_dir / a
                        if p.exists():
                            uri = to_uri(p)
                            h = h.replace(a, uri)
                            h = h.replace(f'./{a}', uri)
                    return h
                content = _inline_audio(_inline_images(_inline_js(_inline_css(content))))
                try:
                    content = content.replace('</head>', '<style>#leaderboard{display:none}#gameWindow{display:none}#endGameCutScene{display:none}</style></head>')
                except Exception:
                    pass
                try:
                    import re as _re3
                    # As a final guard, strip any residual jQuery .stop(...) calls across the whole HTML
                    content = _re3.sub(r"\.stop\s*\([^)]*\)", "", content)
                    content = _re3.sub(r"(\$\([^)]*\))\s*\.stop\s*\([^)]*\)", r"\1", content)
                except Exception:
                    pass
                # Inject minimal jQuery/TimeCircles stub so app.js runs offline in preview
                stub_js = """
<script>(function(){
function wrapElements(arr){
  var els = arr;
  var api = { els: els, length: els.length, fn: {},
    hide:function(){ els.forEach(function(e){ e.style.display='none'; }); return this; },
    show:function(){ els.forEach(function(e){ e.style.display=''; }); return this; },
    fadeIn:function(){ els.forEach(function(e){ e.style.display=''; }); return this; },
    fadeOut:function(){ els.forEach(function(e){ e.style.display='none'; }); return this; },
    stop:function(){ return this; },
    animate:function(props,dur){ els.forEach(function(e){ for(var k in (props||{})){ try{ e.style[k]=String(props[k]); }catch(ex){} } }); return this; },
    on:function(evt,fn){ els.forEach(function(e){ e.addEventListener(evt,fn); }); return this; },
    one:function(evt,fn){ els.forEach(function(e){ function once(ev){ fn.call(e,ev); e.removeEventListener(evt,once);} e.addEventListener(evt,once);} ); return this; },
    prop:function(n,v){ els.forEach(function(e){ e[n]=v; }); return this; },
    text:function(v){ if(v!==undefined){ els.forEach(function(e){ e.textContent=v; }); return this; } return els[0]?els[0].textContent:''; },
    html:function(v){ if(v!==undefined){ els.forEach(function(e){ e.innerHTML=v; }); return this; } return els[0]?els[0].innerHTML:''; },
    closest:function(sel){ return wrapElements(els.map(function(e){ return e.closest(sel); }).filter(Boolean)); },
    animateNumber:function(opts){ var t = els[0]; if(!t) return this; if (opts && typeof opts.numberStep==='function'){ opts.numberStep(opts.number,{elem:t}); } else { t.textContent = String((opts&&opts.number)||''); } return this; },
    TimeCircles:function(){ var el = els[0]; if(!el) return {stop:function(){},restart:function(){},addListener:function(){},getTime:function(){return 0;}}; if(!el.__tc){ (function(){ var time = parseInt(el.getAttribute('data-timer')||'60',10); var interval=null; var listeners=[]; el.__tc={ stop:function(){ if(interval){ clearInterval(interval); interval=null; } }, restart:function(){ if(interval){ clearInterval(interval); } time = parseInt(el.getAttribute('data-timer')||'60',10); interval=setInterval(function(){ time--; listeners.forEach(function(cb){ try{ cb(); }catch(e){} }); }, 1000); }, addListener:function(cb){ listeners.push(cb); }, getTime:function(){ return time; } }; })(); } return el.__tc; }
  };
  els.forEach(function(e,i){ api[i]=e; });
  return api;
}
function $(arg){
  if (typeof arg === 'function') { if (document.readyState !== 'loading') { arg(); } else { document.addEventListener('DOMContentLoaded', arg); } return wrapElements([document]); }
  var isWin = (arg===window) || (Object.prototype.toString.call(arg)==='[object Window]');
  if (isWin || arg===document) { return wrapElements([isWin?window:document]); }
  if (arg && arg.nodeType===1) { return wrapElements([arg]); }
  var sel = String(arg||'');
  var els = Array.prototype.slice.call(document.querySelectorAll(sel));
  return wrapElements(els);
}
window.$ = $; window.jQuery = $;
})();</script>
"""
                content = content.replace('</head>', stub_js + '</head>')
            except Exception:
                pass
            import json as _json
            inline_data = {
                'project_name': project_data.get('name','Ai Là Triệu Phú'),
                'language': project_data.get('language','vi'),
                'questions': list(project_data.get('questions',[]) or []),
                'game_config': self._without_feedback_sound_pools(project_data.get('game_config', {}) or {})
            }
            payload = _json.dumps(inline_data, ensure_ascii=False)
            # Inject game-data script right after <body>
            inject_tag = f"<script id=\"game-data\" type=\"application/json\">{payload}</script>"
            if '<body>' in content:
                content = content.replace('<body>', '<body>\n' + inject_tag)
            else:
                # Fallback: append at end
                content = content + "\n" + inject_tag
            bridge_js = (
                "<script>(function(){"
                "var el=document.getElementById('game-data');"
                "if(!el) return;"
                "try{ var p = JSON.parse(el.textContent||'{}');"
                "var qs = Array.isArray(p.questions) ? p.questions : [];"
                "function normalizeOptions(q){"
                " var opts = q.options || q.answers || q.choices || null;"
                " if(!Array.isArray(opts) || opts.length<2){"
                "  var variants=[['option_a','option_b','option_c','option_d'],['answerA','answerB','answerC','answerD'],['A','B','C','D'],['option1','option2','option3','option4'],['pa','pb','pc','pd'],['ansA','ansB','ansC','ansD']];"
                "  for(var vi=0;vi<variants.length;vi++){"
                "   var keys=variants[vi];"
                "   var arr=[q[keys[0]],q[keys[1]],q[keys[2]],q[keys[3]]].filter(function(x){return x!==undefined && x!==null});"
                "   if(arr && arr.length>=2){ opts=arr; break; }"
                "  }"
                " }"
                " if((!opts || !opts.length) && Array.isArray(q.incorrect_answers)){"
                "  var ca=(q.correct_answer!==undefined && q.correct_answer!==null) ? q.correct_answer : q.correctAnswer;"
                "  var base=[]; if(ca!==undefined && ca!==null){ base.push(ca); }"
                "  for(var i=0;i<q.incorrect_answers.length;i++){ base.push(q.incorrect_answers[i]); }"
                "  opts=base;"
                " }"
                " opts = Array.isArray(opts) ? opts.slice(0,4) : []; while(opts.length<4) opts.push('');"
                " // strip '==' marker convention"
                " var idxMarked=-1;"
                " for(var i=0;i<opts.length;i++){ var s=String(opts[i]||''); if(s.indexOf('==')!==-1){ idxMarked=i; opts[i]=s.replace('==','').trim(); }}"
                " return {options:opts, markedIndex:idxMarked};"
                "}"
                "function map(q){"
                " var norm = normalizeOptions(q); var opts = norm.options; var idx = 0;"
                " var ca = (q.correct_answer!==undefined && q.correct_answer!==null) ? q.correct_answer : q.correctAnswer;"
                " if(typeof ca==='number'){ idx = Math.max(0, Math.min(3, ca)); }"
                " else if(typeof ca==='string'){ var L=['A','B','C','D']; var up = ca.toUpperCase(); var li = L.indexOf(up); if(li>=0){ idx = li; } else { var pos = opts.indexOf(ca); idx = pos>=0 ? pos : 0; }}"
                " if(norm.markedIndex>=0){ idx = norm.markedIndex; }"
                " var tl = parseInt(q.time_limit || q.time || (p.game_config && p.game_config.question_time) || 60, 10);"
                " var expl = (q.explanation || q.explain || q.detail || q.solution || '');"
                " return { question: (q.question || q.text || ''), correct_answer: String(opts[idx]||''), incorrect_answers: opts.filter(function(o,i){return i!==idx;}).slice(0,3), time_limit: tl, explanation: expl };"
                "}"
                "window.EDU_PROJECT = p;"
                "window.EDU_MILLIONAIRE_MODE = String((p.game_config && p.game_config.export_mode) || 'student').toLowerCase()==='teaching' ? 'teaching' : 'student';"
                "window.__EP_MILLIONAIRE_TEACHING = window.EDU_MILLIONAIRE_MODE === 'teaching';"
                "window.DEFAULT_QUESTION_TIME = parseInt((p.game_config && (p.game_config.question_time || p.game_config.time_limit)) || 60, 10);"
                "window.EDU_QUESTIONS = qs.map(map).slice(0,15);"
                "}catch(e){}"
                "})();</script>"
            )
            content = content.replace('</body>', bridge_js + '</body>')
            try:
                compat_js = (
                    "<script>(function(){"
                    "try{"
                    " if(typeof window.$==='function'){"
                    "  try{ window.$.animateNumber = window.$.animateNumber || { numberStepFactories: { separator: function(sep){ return function(now, tween){ try{ var el = tween.elem; var s = String(Math.round(now)); el.textContent = s.replace(/\\B(?=(\\d{3})+(?!\\d))/g, sep); }catch(e){} }; } } }; }catch(e){}"
                    "  try{ window.$.proxy = function(fn, ctx){ try{ if (typeof fn === 'string' && ctx && typeof ctx[fn] === 'function'){ var f = ctx[fn]; return function(){ return f.apply(ctx, arguments); }; } if (typeof fn === 'function'){ return function(){ return fn.apply(ctx || this, arguments); }; } }catch(e){} return function(){}; }; }catch(e){}"
                    "  try{ window.$.fn = window.$.fn || {}; }catch(e){}"
                    "  try{ window.$.fn.stop = function(){ return this; }; }catch(e){}"
                    "  try{ window.$.fn.animate = function(props, dur){ try{ if(this && this.els){ this.els.forEach(function(e){ for(var k in (props||{})){ try{ e.style[k] = String(props[k]); }catch(_ex){} } }); } }catch(_e){} return this; }; }catch(e){}"
                    "  try{ var _$orig = window.$; window.$ = function(a){ var r = _$orig(a); try{ if(r && typeof r.stop !== 'function'){ r.stop = function(){ return this; }; } if(r && typeof r.animate !== 'function'){ r.animate = function(props,dur){ try{ if(this && this.els){ this.els.forEach(function(e){ for(var k in (props||{})){ try{ e.style[k]=String(props[k]); }catch(_ex){} } }); } }catch(_e){} return this; }; } }catch(_e){} return r; }; }catch(e){}"
                        "  try{ document.addEventListener('DOMContentLoaded', function(){ try{ var _$o = window.$; window.$ = function(s){ var r = _$o(s); try{ if(r && typeof r.stop!=='function'){ r.stop=function(){ return this; }; } }catch(_e){} return r; }; }catch(_e){} }); }catch(e){}"
                    " }"
                    "}catch(e){}"
                    "})();</script>"
                )
                content = content.replace('</body>', compat_js + '</body>')
            except Exception:
                pass
            content = self._inject_favicon(content)
            return content
        except Exception as e:
            return f"<html><body><h3>Error rendering Millionaire: {e}</h3></body></html>"

    def _generate_wwbm_html(self, project_data: Dict) -> str:
        """Render WWBM web template with teacher questions injected"""
        try:
            template_path = self.templates_dir / 'wwbm.html'
            if not template_path.exists():
                return "<html><body><h3>WWBM template missing</h3></body></html>"
            content = template_path.read_text(encoding='utf-8')
            from jinja2 import Template as _T
            _tmpl = _T(content)
            import json as _json
            inline_data = {
                'project_name': project_data.get('name','WWBM'),
                'language': project_data.get('language','vi'),
                'questions': list(project_data.get('questions',[]) or []),
                'game_config': dict(project_data.get('game_config',{}) or {})
            }
            html = _tmpl.render(project_name=inline_data['project_name'], language=inline_data['language'], game_json=_json.dumps(inline_data, ensure_ascii=False))
            return self._inject_favicon(html)
        except Exception as e:
            return f"<html><body><h3>Error rendering WWBM: {e}</h3></body></html>"

    def _generate_altp_vn_html(self, project_data: Dict) -> str:
        """Render Vietnamese ALTPh template (AiLaTrieuPhu-main) with teacher questions"""
        try:
            template_path = self.templates_dir / 'altp_vn.html'
            if not template_path.exists():
                return "<html><body><h3>ALTPh VN template missing</h3></body></html>"
            content = template_path.read_text(encoding='utf-8')
            from jinja2 import Template as _T
            _tmpl = _T(content)
            import json as _json
            inline_data = {
                'project_name': project_data.get('name','Ai Là Triệu Phú'),
                'language': project_data.get('language','vi'),
                'questions': list(project_data.get('questions',[]) or []),
                'game_config': dict(project_data.get('game_config',{}) or {})
            }
            html = _tmpl.render(project_name=inline_data['project_name'], language=inline_data['language'], game_json=_json.dumps(inline_data, ensure_ascii=False))
            return self._inject_favicon(html)
        except Exception as e:
            return f"<html><body><h3>Error rendering ALTPh VN: {e}</h3></body></html>"
    
    def _generate_quiz_game_html(self, project_data: Dict, variant: str = "classic") -> str:
        # For Millionaire variant, render via NGDAT/Exam template with embedded assets
        if variant == 'millionaire':
            try:
                ngdat_dir = self.assets_dir / "millionaire_ngdat"
                millionaire_assets_dir = ngdat_dir if ngdat_dir.exists() else (self.assets_dir / "millionaire_exam")
                template_path = millionaire_assets_dir / "template.html"
                if not template_path.exists():
                    return "<html><body><h3>Millionaire template missing</h3></body></html>"
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_template = f.read()
                merger = MillionaireTemplateMerger(millionaire_assets_dir)
                teacher_questions = project_data.get('questions', [])
                single_file_html = merger.create_single_file_export(html_template, project_data, teacher_questions)
                return self._inject_favicon(single_file_html)
            except Exception as e:
                return f"<html><body><h3>Error rendering Millionaire preview: {e}</h3></body></html>"

        lang = project_data.get('language', 'en')
        labels = {
            'question': I18n.t('quiz.question', lang),
            'score': I18n.t('quiz.score', lang),
            'correct': I18n.t('quiz.correct', lang),
            'loading': I18n.t('quiz.loading', lang),
            'submit': I18n.t('quiz.submit', lang),
            'next': I18n.t('quiz.next', lang),
            'completed': I18n.t('quiz.completed', lang),
            'play_again': I18n.t('quiz.play_again', lang),
            'explain': I18n.t('quiz.explain', lang),
            'correct_answer': I18n.t('quiz.correct_answer', lang),
            'no_questions': I18n.t('quiz.no_questions', lang),
            'lifeline_fifty': I18n.t('lifeline.fifty', lang),
            'lifeline_phone': I18n.t('lifeline.phone', lang),
            'lifeline_audience': I18n.t('lifeline.audience', lang),
            'lifeline_phone_says': I18n.t('lifeline.phone_says', lang),
            'lifeline_audience_result': I18n.t('lifeline.audience_result', lang),
            'start': I18n.t('quiz.start', lang),
            'rules': I18n.t('quiz.rules', lang),
            'time': I18n.t('editor.time', lang),
            'tts_voice': I18n.t('quiz.tts_voice', lang),
            'tts_toggle': I18n.t('quiz.tts_toggle', lang),
            'ok': I18n.t('common.ok', lang),
            'select_prompt': I18n.t('quiz.select_prompt', lang),
            'input_placeholder': I18n.t('quiz.input_placeholder', lang),
            'stopped_title': I18n.t('quiz.stopped_title', lang),
            'win_title': I18n.t('quiz.win_title', lang),
            'zoom': I18n.t('quiz.zoom', lang),
            'spacing': I18n.t('quiz.spacing', lang),
            'result_summary': I18n.t('quiz.result_summary', lang),
            'total': I18n.t('quiz.total', lang),
            'true': I18n.t('quiz.true', lang),
            'false': I18n.t('quiz.false', lang),
            'msg_low': I18n.t('quiz.msg_low', lang) or 'Cố gắng lên nhé!',
            'msg_mid': I18n.t('quiz.msg_mid', lang) or 'Gần được rồi!',
            'msg_high': I18n.t('quiz.msg_high', lang) or 'Xuất Sắc!',
        }
        import json as _json
        labels_json = self._safe_json_dumps(labels)
        bg_start = '#E0F2FE'
        bg_end = '#ECFDF3'
        accent = '#22C55E'
        if variant == 'platformer':
            bg_start = '#0b1023'
            bg_end = '#123'
            accent = '#57c1ff'
        elif variant == 'adventure':
            bg_start = '#0c2e2d'
            bg_end = '#1a3b3a'
            accent = '#12B76A'
        elif variant == 'millionaire':
            bg_start = '#23283a'
            bg_end = '#343a4d'
            accent = '#7F56D9'
        else:
            try:
                cfg = project_data.get('game_config', {}) or {}
                if cfg.get('cute_effects'):
                    accent = '#7C3AED'
            except Exception:
                pass
        is_millionaire = (variant == 'millionaire')
        html_template = """
<!DOCTYPE html>
<html lang="{{ lang_attr }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ project_name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        html, body { min-height: 100%; }
        body {
            font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
            font-size: clamp(14px, 1.0vw, 17px);
            background: linear-gradient(135deg, {{ bg_start }} 0%, {{ bg_end }} 100%);
            color: {{ '#FFFFFF' if is_millionaire else '#0F172A' }};
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: {{ 'center' if is_millionaire else 'flex-start' }};
            padding: clamp(10px, 2vw, 18px);
            overflow-x: hidden;
            overflow-y: {{ 'hidden' if is_millionaire else 'auto' }};
        }
        .bg-layer{position:fixed;left:0;top:0;right:0;bottom:0;background-size:cover;background-position:center;background-repeat:no-repeat;z-index:-1;opacity:0.75}
        .sprite{display:block; background-repeat:no-repeat;}
        .spr-logo{width:180px;height:180px;margin:0 auto 12px;object-fit:contain}
        .logo-sprite{width:220px;height:220px;margin:0 auto 6px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -5px 0px; background-size: auto; border-radius:50%; box-shadow: 0 4px 18px rgba(0,0,0,0.35)}
        .spr-5050,.spr-phone,.spr-audience{width:24px;height:24px;display:inline-block;margin-right:8px;vertical-align:middle;border-radius:50%;background-image:url('{{ circle_url }}'); background-size:cover; background-position:center;}
        .spr-opt-blue,.spr-opt-yellow,.spr-opt-green,.spr-opt-red,.spr-opt-grey{border-radius:10px;background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; position:relative; overflow:hidden}
        /* Sprite crop positions from Textures.png as per C++ mapping */
        /* Buttons per official coordinates */
        .btn-yellow-left{ width:454px; height:144px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -33px -1233px; }
        .btn-yellow-right{ width:480px; height:144px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -531px -1231px; }
        .btn-red-left{ width:456px; height:160px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -33px -1405px; }
        .btn-red-right{ width:472px; height:152px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -533px -1405px; }
        .btn-green-left{ width:451px; height:146px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -25px -1587px; }
        .btn-green-right{ width:473px; height:145px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -529px -1588px; }
        .btn-blue-left{ width:463px; height:146px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -20px -1769px; }
        .btn-blue-right{ width:476px; height:155px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -528px -1765px; }
        /* Lifeline icons */
        .spr-help1{ width:341px; height:255px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -847px -477px; transform: scale(0.22); transform-origin:left center; }
        .spr-help1-x{ width:334px; height:264px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -1210px -484px; transform: scale(0.22); transform-origin:left center; }
        .spr-help2{ width:318px; height:242px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -860px -746px; transform: scale(0.23); transform-origin:left center; }
        .spr-help2-x{ width:323px; height:243px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -1213px -751px; transform: scale(0.23); transform-origin:left center; }
        .spr-help3{ width:295px; height:225px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -865px -996px; transform: scale(0.25); transform-origin:left center; }
        .spr-help3-x{ width:306px; height:226px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -1222px -1022px; transform: scale(0.25); transform-origin:left center; }
        /* Result marks */
        .spr-red-x{ width:256px; height:256px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -780px -2188px; transform: scale(0.32); transform-origin:right top; }
        .spr-green-ok{ width:240px; height:240px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-position: -472px -2196px; transform: scale(0.32); transform-origin:right top; }
        .result-mark{ position:absolute; top:8px; right:10px; z-index:4; }
        .spr-opt-blue::after{content:""; position:absolute; inset:0; background:linear-gradient(135deg, rgba(70,90,180,0.65), rgba(30,40,70,0.65));}
        .spr-opt-yellow::after{content:""; position:absolute; inset:0; background:linear-gradient(135deg, rgba(240,200,80,0.65), rgba(120,90,20,0.65));}
        .spr-opt-green::after{content:""; position:absolute; inset:0; background:linear-gradient(135deg, rgba(40,170,120,0.65), rgba(20,70,50,0.65));}
        .spr-opt-red::after{content:""; position:absolute; inset:0; background:linear-gradient(135deg, rgba(220,70,70,0.65), rgba(80,25,25,0.65));}
        .spr-opt-grey::after{content:""; position:absolute; inset:0; background:linear-gradient(135deg, rgba(120,120,140,0.55), rgba(60,60,80,0.55));}
        .options-container { display:block; margin-top: 16px; }
        .option-wrap { position: relative; margin: var(--sp-gap) 0; border-radius: 12px; }
        .option-label { position: absolute; left: 18px; top: 50%; transform: translateY(-50%); color: #FFFFFF; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,0.35); z-index: 2; pointer-events: none; }
        .option-button { position: relative; width: 100%; background: transparent; border: none; cursor: pointer; }
        .option-wrap .option-button { position: absolute; left:0; top:0; width:100%; height:100%; z-index: 3 }
        .option-sprite { pointer-events: none; }
        .scale-80 { transform: scale(0.92); transform-origin: left center; }
        .ladder{list-style:none;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0 0 12px;padding:0}
        .ladder li{background:rgba(30,30,36,0.7);border:1px solid #3A3A40;border-radius:10px;color:#EDEEF3;padding:8px 10px;font-weight:600;text-align:center}
        .ladder li.active{border-color: {{ accent }}; color: {{ accent }}; box-shadow: 0 0 8px rgba(34,197,94,0.45)}
        .ladder li.passed{opacity:0.75}
        .ladder li.safe{background:rgba(30,36,30,0.85); border-color:#12B76A}
        .amount-bars{display:flex; gap:14px; justify-content:center; align-items:center; margin: 8px 0 16px}
        .spr-bar-blue,.spr-bar-green,.spr-bar-red,.spr-bar-orange{background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; position:relative; border-radius:12px}
        .spr-bar-blue{ width:457px; height:139px; background-position: -542px -1768px; }
        .spr-bar-green{ width:457px; height:139px; background-position: -542px -1590px; }
        .spr-bar-red{ width:457px; height:139px; background-position: -542px -1412px; }
        .spr-bar-orange{ width:457px; height:139px; background-position: -542px -1234px; }
        .bar-label{position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); color:#EDEEF3; font-weight:700; text-shadow:0 1px 2px rgba(0,0,0,0.35)}
        @media (max-width: 900px){ .spr-bar-blue, .spr-bar-green, .spr-bar-red, .spr-bar-orange{ transform: scale(0.75); transform-origin: center; } .amount-bars{ display:none !important } }
        .pb-panel{width:465px; height:770px; background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; margin: 8px auto; border-radius:16px; box-shadow:0 6px 18px rgba(0,0,0,0.35)}
        .spr-pb-normal{ background-position: -1211px -1745px; width:454px; height:752px }
        .spr-pb-medium{ background-position: -1696px 0px }
        .spr-pb-hard{ background-position: -1699px -786px; width:454px; height:752px }
        .lang-banner{ position:absolute; top:6px; right:6px; width: clamp(90px, 18vw, 160px); height: clamp(45px, 9vw, 80px); background-image:url('{{ sprite_url }}'); background-repeat:no-repeat; background-size: cover; background-position: center; opacity:0.85; border-radius: 8px; box-shadow: 0 3px 10px rgba(0,0,0,0.3); pointer-events: none; z-index: 1 }
        .spr-hun{ background-position: -1037px -1286px }
        .spr-ger{ background-position: -1037px -1438px }
        .spr-eng{ background-position: -1037px -1590px }
        
        .game-container {
            background: {{ 'rgba(45, 47, 58, 0.9)' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98))' }};
            border-radius: 20px;
            padding: clamp(14px, 2vw, 22px);
            max-width: {{ '1400px' if is_millionaire else '1180px' }};
            width: 100%;
            box-shadow: {{ '0 20px 40px rgba(0, 0, 0, 0.3)' if is_millionaire else '0 30px 80px rgba(15, 23, 42, 0.16), 0 12px 30px rgba(34, 197, 94, 0.08)' }};
            backdrop-filter: blur(10px);
            border: 1px solid {{ 'transparent' if is_millionaire else 'rgba(255, 255, 255, 0.78)' }};
            aspect-ratio: {{ '16 / 9' if is_millionaire else 'unset' }};
            transform-origin: center;
            height: {{ 'min(calc(100vh - 24px), 800px)' if is_millionaire else 'auto' }};
            min-height: {{ '0' if is_millionaire else 'min(560px, calc(100vh - 24px))' }};
            max-height: {{ 'min(calc(100vh - 24px), 800px)' if is_millionaire else 'none' }};
            display: flex;
            flex-direction: column;
            overflow: {{ 'hidden' if is_millionaire else 'visible' }};
            margin-bottom: 8px;
        }
        #game-content {
            padding: 12px 14px 10px 14px;
            margin-top: 6px;
            border-radius: 16px;
            background: {{ 'transparent' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.82), rgba(248,250,252,0.58))' }};
            flex: {{ '1 1 auto' if is_millionaire else '0 1 auto' }};
            min-height: 0;
            overflow-y: {{ 'auto' if is_millionaire else 'visible' }};
            overflow-x: hidden;
            scrollbar-width: thin;
            scrollbar-color: rgba(127,86,217,0.4) transparent;
        }
        #game-content::-webkit-scrollbar { width: 12px; }
        #game-content::-webkit-scrollbar-track { background: rgba(2, 6, 23, 0.10); border-radius: 999px; }
        #game-content::-webkit-scrollbar-thumb { background: {{ 'rgba(127,86,217,0.90)' if is_millionaire else 'rgba(34,197,94,0.55)' }}; border-radius: 999px; border: 3px solid {{ 'rgba(255,255,255,0.65)' if is_millionaire else 'rgba(255,255,255,0.95)' }}; }
        /* allow native scrollbars */
        .intro-screen{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:{{ 'rgba(0,0,0,0.75)' if is_millionaire else 'linear-gradient(180deg, rgba(240,249,255,0.92), rgba(236,253,245,0.94))' }};z-index:10}
        .intro-card{
            background: {{ 'rgba(15,23,42,0.96)' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98))' }};
            border-radius: 20px;
            padding: 28px 30px;
            text-align: center;
            max-width: 560px;
            width: min(92vw, 560px);
            color: {{ '#EDEEF3' if is_millionaire else '#0F172A' }};
            box-shadow: {{ '0 20px 40px rgba(0,0,0,0.45)' if is_millionaire else '0 28px 60px rgba(15, 23, 42, 0.14)' }};
            border: 1px solid {{ 'rgba(148,163,184,0.45)' if is_millionaire else 'rgba(148, 163, 184, 0.24)' }};
            position: relative;
            overflow: hidden;
        }
        .intro-card::before{
            content:"";
            position:absolute;
            inset:0 0 auto 0;
            height:6px;
            background: linear-gradient(90deg, {{ accent }}, {{ '#A7F3D0' if is_millionaire else '#93C5FD' }});
        }
        .intro-title{
            font-size: clamp(1.35rem, 2.5vw, 1.8rem);
            margin-bottom: 12px;
            font-weight: 800;
            color: inherit;
        }
        .intro-description{
            font-size: 0.97rem;
            line-height: 1.7;
            margin-bottom: 20px;
            color: {{ '#CBD5E1' if is_millionaire else '#475569' }};
        }
        .circle-bg{width:420px;height:420px;border-radius:50%;background:radial-gradient(circle, rgba(34,197,94,0.38) 0%, rgba(0,0,0,0.0) 60%);position:absolute;}
        .start-button{background:linear-gradient(135deg, {{ accent }} 0%, #16A34A 100%);color:#fff;border:none;border-radius:14px;padding:14px 26px;font-size:1.05em;font-weight:700;margin-top:4px;box-shadow:0 14px 28px rgba(34,197,94,0.22)}
        .start-button:hover{filter:brightness(1.1)}
        .popup-overlay{position:fixed;inset:0;background:{{ 'rgba(0,0,0,0.65)' if is_millionaire else 'rgba(226, 232, 240, 0.55)' }};display:none;align-items:center;justify-content:center;z-index:15;padding:18px}
        .popup-panel{background:{{ '#1E1E24' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98))' }};border:1px solid {{ '#3A3A40' if is_millionaire else 'rgba(148, 163, 184, 0.28)' }};border-radius:18px;padding:20px;max-width:520px;width:92%;color:{{ '#EDEEF3' if is_millionaire else '#0F172A' }};box-shadow:{{ '0 24px 48px rgba(0,0,0,0.40)' if is_millionaire else '0 20px 44px rgba(15, 23, 42, 0.16)' }}}
        .popup-panel h3{margin-bottom:10px;font-size:1.08rem}
        .popup-panel p{line-height:1.6;color:{{ '#CBD5E1' if is_millionaire else '#475569' }}}
        .feedback-popup{position:fixed;inset:0;display:none;align-items:center;justify-content:center;pointer-events:none;z-index:22;padding:24px}
        .feedback-popup-text{
            max-width:min(780px, 94vw);
            padding:8px 12px;
            background:transparent;
            border:none;
            border-radius:0;
            font-size:clamp(1.8rem, 5vw, 4.4rem);
            font-weight:900;
            font-style:italic;
            line-height:1.1;
            letter-spacing:0.03em;
            text-align:center;
            color:#FFFFFF;
            box-shadow:none;
            text-shadow:0 5px 16px rgba(15,23,42,0.34);
            transform:scale(0.18) rotate(-10deg);
            transform-origin:center center;
            opacity:0;
            will-change:transform,opacity;
        }
        .feedback-popup-text.correct{color:#22C55E;-webkit-text-stroke:1px rgba(6,95,70,0.22)}
        .feedback-popup-text.wrong{color:#F97316;-webkit-text-stroke:1px rgba(124,45,18,0.22)}
        .bars{display:flex;gap:8px;align-items:flex-end;height:160px;margin-top:10px}
        .bar{flex:1;background:linear-gradient(180deg, {{ accent }}, #16A34A);border-radius:8px;position:relative}
        .bar span{position:absolute;bottom:6px;left:6px;font-weight:700;color:#fff}
        .countdown{font-weight:700;font-size:1.4em;text-align:center;margin-top:8px;color:{{ '#EDEEF3' if is_millionaire else '#0F172A' }}}
        .voice-toolbar { position: fixed; top: 18px; right: 18px; display: flex; gap: 8px; align-items: center; background: {{ 'rgba(27,31,42,0.55)' if is_millionaire else 'rgba(255,255,255,0.92)' }}; border: 1px solid {{ '#2A2F3A' if is_millionaire else 'rgba(148, 163, 184, 0.24)' }}; border-radius: 12px; padding: 8px 10px; box-shadow: {{ 'none' if is_millionaire else '0 10px 24px rgba(15, 23, 42, 0.10)' }}; backdrop-filter: blur(12px); }
        .voice-toolbar label { color: {{ '#EDEEF3' if is_millionaire else '#334155' }}; font-size: 12px; font-weight: 600; }
        .voice-toolbar select { background: {{ '#1B1F2A' if is_millionaire else '#F8FAFC' }}; color: {{ '#EDEEF3' if is_millionaire else '#0F172A' }}; border: 1px solid {{ '#2A2F3A' if is_millionaire else 'rgba(148, 163, 184, 0.38)' }}; border-radius: 8px; padding: 6px 8px; min-width: 160px; }
        .voice-toolbar input[type="checkbox"] { accent-color: {{ accent }}; }
        /* .zoom-toolbar removed */
        
        .game-header {
            position: relative;
            text-align: center;
            margin-bottom: 16px;
            padding: {{ '0' if is_millionaire else '8px 12px 4px' }};
            border-radius: {{ '0' if is_millionaire else '18px' }};
            background: {{ 'transparent' if is_millionaire else 'linear-gradient(180deg, rgba(240,249,255,0.78), rgba(236,253,245,0.35))' }};
            border: {{ 'none' if is_millionaire else '1px solid rgba(191, 219, 254, 0.52)' }};
        }
        
        .game-title {
            font-size: 2.15em;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(45deg, {{ accent }}, #A7F3D0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            user-select: none;
        }
        
        .game-stats {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 14px;
            padding: 12px;
            background: {{ 'rgba(255, 255, 255, 0.10)' if is_millionaire else 'linear-gradient(180deg, rgba(248,250,252,0.86), rgba(241,245,249,0.72))' }};
            border: 1px solid {{ 'rgba(148, 163, 184, 0.22)' if is_millionaire else 'rgba(191, 219, 254, 0.64)' }};
            border-radius: 18px;
            color: {{ '#EDEEF3' if is_millionaire else '#111827' }};
            backdrop-filter: blur(8px);
            box-shadow: {{ 'none' if is_millionaire else 'inset 0 1px 0 rgba(255,255,255,0.75), 0 14px 30px rgba(15, 23, 42, 0.06)' }};
        }
        
        .stat-item {
            text-align: center;
            flex: 1 1 120px;
            min-width: 110px;
            padding: {{ '0' if is_millionaire else '12px 12px 10px' }};
            border-radius: {{ '0' if is_millionaire else '16px' }};
            background: {{ 'transparent' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.9))' }};
            border: {{ 'none' if is_millionaire else '1px solid rgba(226, 232, 240, 0.96)' }};
            box-shadow: {{ 'none' if is_millionaire else '0 10px 22px rgba(148, 163, 184, 0.10)' }};
        }
        
        .stat-value {
            font-size: 1.5em;
            font-weight: 800;
            color: {{ accent }};
            margin-bottom: 4px;
        }
        
        :root { --sp-gap: 4px; --sp-qmargin: 6px; }
        .question-container {
            margin-bottom: var(--sp-qmargin);
            overflow: visible;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        
        .question-text {
            font-size: 1.12em;
            line-height: 1.65;
            margin-bottom: 0;
            padding: 18px 20px;
            background: {{ 'rgba(17, 24, 39, 0.35)' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.94))' }};
            border-radius: 18px;
            border: 1px solid {{ 'rgba(148, 163, 184, 0.22)' if is_millionaire else 'rgba(191, 219, 254, 0.78)' }};
            border-left: 6px solid {{ accent }};
            text-align: left;
            text-indent: 0;
            color: {{ '#EDEEF3' if is_millionaire else '#111827' }};
            box-shadow: {{ '0 8px 18px rgba(15, 23, 42, 0.10)' if is_millionaire else '0 16px 30px rgba(15, 23, 42, 0.08)' }};
        }
        .question-text.fill-blank-inline { display:block; text-align:center; }
        .question-inline-wrap {
            display: inline-flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: center;
            gap: 8px;
            max-width: 100%;
        }
        .question-inline-text {
            white-space: pre-wrap;
            word-break: break-word;
        }
        
        .image-container { position: relative; width: 100%; border-radius: 18px; overflow: hidden; margin-bottom: 0; display:none; border: {{ 'none' if is_millionaire else '1px solid rgba(191, 219, 254, 0.8)' }}; background: {{ 'transparent' if is_millionaire else 'rgba(255,255,255,0.82)' }}; box-shadow: {{ 'none' if is_millionaire else '0 12px 26px rgba(148, 163, 184, 0.14)' }}; }
        .image-container.loading::before { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(255,255,255,0.06) 25%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.06) 75%); animation: shimmer 1.2s infinite; }
        .question-image {
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            display: block;
        }
        
        .options-container {
            display: grid;
            gap: {{ 'var(--sp-gap)' if is_millionaire else '14px' }};
            grid-template-columns: {{ '1fr' if is_millionaire else 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))' }};
            align-items: start;
            align-content: start;
            grid-auto-rows: max-content;
        }
        
        @media (max-width: 640px) {
            .options-container { grid-template-columns: 1fr !important; }
            .question-text { font-size: 1.15em; }
            .option-button.btn-classic { font-size: 1em; }
            .option-inner { min-height: 76px; padding: 13px 14px; gap: 12px; }
            .controls { flex-direction: column; }
            .control-button { width: 100%; }
        }
        
        .option-button.btn-classic {
            display: block;
            background: linear-gradient(135deg, #FFFFFF 0%, #F0FDF4 52%, #EFF6FF 100%);
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 18px;
            padding: 0;
            color: #111827;
            font-size: 0.95em;
            text-align: left;
            cursor: pointer;
            width: 100%;
            min-height: 72px;
            line-height: 1.45;
            box-shadow: 0 14px 28px rgba(15, 23, 42, 0.10);
            transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, border-color 160ms ease, filter 160ms ease;
            overflow: hidden;
            isolation: isolate;
            align-self: start;
            height: auto;
        }
        .option-button.btn-classic { position: relative; }
        .option-button.btn-classic::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(120deg, rgba(255,255,255,0) 25%, rgba(255,255,255,0.72) 50%, rgba(255,255,255,0) 75%);
            transform: translateX(-135%);
            opacity: 0;
            transition: opacity 150ms ease;
            pointer-events: none;
            z-index: 0;
        }
        .option-button.btn-classic::after {
            content: "";
            position: absolute;
            left: 50%;
            top: 50%;
            width: 22px;
            height: 22px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(34,197,94,0.24) 0%, rgba(59,130,246,0.16) 45%, rgba(255,255,255,0) 72%);
            transform: translate(-50%, -50%) scale(0.25);
            opacity: 0;
            pointer-events: none;
            z-index: 0;
        }
        .option-button.btn-classic > .option-inner { position: relative; z-index: 1; }
        .option-button.btn-classic > .result-mark { position: absolute; z-index: 4; }
        .option-inner {
            display: flex;
            align-items: center;
            gap: 14px;
            width: 100%;
            min-height: 72px;
            padding: 15px 16px;
        }
        .option-prefix {
            width: 38px;
            min-width: 38px;
            height: 38px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
            background: linear-gradient(135deg, rgba(34,197,94,0.14), rgba(59,130,246,0.12));
            border: 1px solid rgba(34,197,94,0.16);
            color: {{ accent }};
            font-weight: 800;
            font-size: 0.95rem;
            letter-spacing: 0.04em;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
            flex-shrink: 0;
        }
        .option-copy-wrap {
            display: flex;
            flex-direction: column;
            gap: 2px;
            min-width: 0;
            flex: 1;
        }
        .option-copy {
            display: block;
            font-weight: 700;
            color: #0F172A;
            word-break: break-word;
        }
        .option-hint {
            display: block;
            font-size: 0.78rem;
            color: #64748B;
            font-weight: 600;
            letter-spacing: 0.01em;
        }
        .option-trail {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            min-width: 28px;
            height: 28px;
            border-radius: 999px;
            background: rgba(255,255,255,0.86);
            border: 1px solid rgba(191,219,254,0.9);
            color: #0F172A;
            font-size: 1rem;
            font-weight: 800;
            box-shadow: 0 6px 14px rgba(148, 163, 184, 0.14);
            transition: transform 160ms ease, background 160ms ease, color 160ms ease;
            flex-shrink: 0;
        }
        
        .option-button.btn-classic:hover {
            border-color: {{ accent }};
            background: linear-gradient(135deg, #F8FAFC 0%, #DCFCE7 52%, #DBEAFE 100%);
            transform: translateY(-3px);
            box-shadow: 0 20px 38px rgba(15, 23, 42, 0.15), 0 8px 18px rgba(34, 197, 94, 0.10);
            filter: saturate(1.02);
        }
        .option-button.btn-classic:hover::before { opacity: 1; }
        .option-button.btn-classic:hover .option-trail {
            transform: translateX(2px);
            background: rgba(220,252,231,0.92);
            color: {{ accent }};
        }
        .option-button.btn-classic:active { transform: translateY(1px) scale(0.996); box-shadow: 0 10px 20px rgba(15, 23, 42, 0.10); }
        .option-button.btn-classic:focus-visible { outline: 3px solid {{ accent }}; outline-offset: 3px; }
        .option-button.btn-classic.press-pop {
            animation: optionPressPop 360ms cubic-bezier(0.22, 1, 0.36, 1);
        }
        .option-button.btn-classic.press-pop::after {
            animation: optionPressRipple 420ms ease-out;
        }

        .btn-tf.btn-true { border-color: #12B76A; background: linear-gradient(135deg, rgba(18,183,106,0.14) 0%, rgba(34,197,94,0.18) 100%); }
        .btn-tf.btn-false { border-color: #F97066; background: linear-gradient(135deg, rgba(249,112,102,0.14) 0%, rgba(244,63,94,0.16) 100%); }

        .text-input {
            grid-column: 1 / -1;
            display: block;
            width: min(92%, 560px);
            max-width: 100%;
            margin: 0 auto;
            box-sizing: border-box;
            padding: 12px 14px;
            border-radius: 12px;
            border: 1px solid rgba(147,197,253,0.75);
            background: rgba(255, 255, 255, 0.96);
            color: #111827;
            font-size: 1rem;
            box-shadow: 0 10px 20px rgba(15, 23, 42, 0.10);
            outline: none;
        }
        .text-input:focus { border-color: {{ accent }}; box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.18), 0 12px 22px rgba(15, 23, 42, 0.12); }
        .text-input.input-incorrect { border-color: #F04438; background: rgba(254, 242, 242, 0.96); box-shadow: 0 0 0 4px rgba(240, 68, 56, 0.16), 0 12px 22px rgba(15, 23, 42, 0.12); }
        .text-input::placeholder { color: #94A3B8; }
        .inline-blank-input {
            display: inline-block;
            width: clamp(140px, 24vw, 240px);
            min-width: 140px;
            max-width: 100%;
            margin: 4px 0;
            text-align: center;
            vertical-align: middle;
        }

        .option-button.btn-classic.pending {
            outline: 3px solid {{ accent }};
            outline-offset: 2px;
        }

        .matching-grid { display:grid; grid-template-columns: minmax(0,1fr) minmax(0,1fr); column-gap: 80px; row-gap:14px; align-items:start; justify-items:stretch; width:100%; }
        .matching-col { flex:1; display:flex; flex-direction:column; gap:10px; position: relative; z-index: 1; width: 100%; }
        .matching-summary { margin-top: 12px; color: {{ '#EDEEF3' if is_millionaire else '#111827' }}; font-size: 0.95em; }
        .matching-chip { display:inline-block; margin:6px 8px 0 0; padding:6px 10px; border-radius:999px; background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.35); color: {{ '#A7F3D0' if is_millionaire else '#065F46' }}; }
        .matching-wrap { position: relative; width: 100%; }
        .matching-lines { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:2; overflow: visible; }
        .match-line-shadow { stroke: rgba(0,0,0,0.22); stroke-width: 8; fill:none; opacity:0.38; }
        .match-line { stroke: {{ accent }}; stroke-width: 4; fill: none; opacity: 0.95; stroke-linecap: round; }
        .match-dot { fill: {{ accent }}; opacity: 0.98; }
        .matching-anchor { position: absolute; top: 50%; width: 0; height: 0; pointer-events: none; }
        .matching-anchor-left { left: 0; transform: translate(-1px, -50%); }
        .matching-anchor-right { right: 0; transform: translate(1px, -50%); }
        
        .option-button.btn-classic.selected {
            border-color: {{ accent }};
            background: linear-gradient(135deg, rgba(34,197,94,0.18) 0%, rgba(59,130,246,0.15) 100%);
            color: #065F46;
            box-shadow: 0 0 0 4px rgba(34,197,94,0.12), 0 22px 38px rgba(15, 23, 42, 0.12);
            transform: translateY(-2px) scale(1.01);
        }
        .option-button.btn-classic.selected::before {
            opacity: 1;
            animation: optionSelectedShine 820ms ease;
        }
        .option-button.btn-classic.selected .option-prefix {
            background: linear-gradient(135deg, rgba(34,197,94,0.20), rgba(16,185,129,0.20));
            border-color: rgba(22,163,74,0.20);
            color: #047857;
        }
        .option-button.btn-classic.selected .option-copy { color: #065F46; }
        .option-button.btn-classic.selected .option-trail {
            background: linear-gradient(135deg, rgba(220,252,231,0.98), rgba(240,253,250,0.98));
            border-color: rgba(34,197,94,0.28);
            color: #047857;
            transform: translateX(3px);
        }
        
        .option-button.btn-classic.correct {
            border-color: #12B76A;
            background: linear-gradient(135deg, rgba(18,183,106,0.18) 0%, rgba(167,243,208,0.32) 100%);
            color: #065F46;
            animation: optionCorrectPulse 520ms cubic-bezier(0.22, 1, 0.36, 1);
            box-shadow: 0 0 0 4px rgba(18,183,106,0.14), 0 18px 34px rgba(22,163,74,0.16);
        }
        .option-button.btn-classic.correct .option-prefix {
            background: linear-gradient(135deg, rgba(18,183,106,0.24), rgba(167,243,208,0.34));
            border-color: rgba(18,183,106,0.30);
            color: #047857;
        }
        .option-button.btn-classic.correct .option-copy,
        .option-button.btn-classic.correct .option-trail { color: #065F46; }
        
        .option-button.btn-classic.incorrect {
            border-color: #F79009;
            background: linear-gradient(135deg, rgba(249,112,102,0.16) 0%, rgba(254,226,226,0.82) 100%);
            color: #9A3412;
            animation: optionWrongShake 420ms ease;
            box-shadow: 0 0 0 4px rgba(249,112,102,0.10), 0 14px 26px rgba(249,112,102,0.14);
        }
        .option-button.btn-classic.incorrect .option-prefix {
            background: linear-gradient(135deg, rgba(249,112,102,0.18), rgba(254,226,226,0.72));
            border-color: rgba(249,112,102,0.26);
            color: #C2410C;
        }
        .option-button.btn-classic.incorrect .option-copy,
        .option-button.btn-classic.incorrect .option-trail { color: #9A3412; }
        
        .option-image {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .option-image-wrap { position: relative; display:inline-block; width: 84px; height: 84px; border-radius: 8px; overflow: hidden; margin-right: 15px; vertical-align: middle; }
        .option-image-wrap.loading::before { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, rgba(255,255,255,0.08) 25%, rgba(255,255,255,0.18) 50%, rgba(255,255,255,0.08) 75%); animation: shimmer 1.2s infinite; }
        
        .lifelines { display:flex; gap:12px; justify-content:center; align-items:center; margin: 4px 0 12px; flex-wrap: wrap; }
        .lifeline-btn { display:inline-flex; align-items:center; gap:8px; background: linear-gradient(135deg, {{ '#3A3C47 0%, #4A4E5A 100%' if is_millionaire else '#FFFFFF 0%, #F8FAFC 100%' }}); border: 2px solid {{ '#4A4E5A' if is_millionaire else 'rgba(148, 163, 184, 0.24)' }}; border-radius: 12px; padding: 8px 12px; min-width: 120px; height: 42px; color: {{ '#FFFFFF' if is_millionaire else '#0F172A' }}; font-size: 0.92em; font-weight: 600; cursor: pointer; box-shadow: {{ 'none' if is_millionaire else '0 10px 20px rgba(15, 23, 42, 0.08)' }}; }
        .lifeline-btn:disabled { background:{{ '#3A3C47' if is_millionaire else '#E2E8F0' }}; opacity:0.6; cursor:not-allowed; }
        .controls {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 14px;
            padding-top: 10px;
            flex-shrink: 0;
            flex-wrap: wrap;
        }
        
        .control-button {
            background: linear-gradient(135deg, {{ accent }} 0%, #16A34A 100%);
            border: none;
            border-radius: 16px;
            padding: 13px 28px;
            color: #FFFFFF;
            font-size: 1.05em;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 14px 28px rgba(34,197,94,0.22);
            transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
        }
        
        .control-button:hover {
            background: linear-gradient(135deg, #22C55E 0%, #16A34A 100%);
            transform: translateY(-2px);
            box-shadow: 0 18px 34px rgba(34,197,94,0.24);
            filter: saturate(1.03);
        }
        
        .control-button:disabled {
            background: {{ '#4A4E5A' if is_millionaire else '#CBD5E1' }};
            color: {{ '#FFFFFF' if is_millionaire else '#64748B' }};
            cursor: not-allowed;
            box-shadow: none;
        }
        
        .explanation {
            margin-top: 20px;
            padding: 16px 16px;
            background: {{ 'rgba(16, 185, 129, 0.10)' if is_millionaire else 'linear-gradient(135deg, rgba(167,243,208,0.55), rgba(219,234,254,0.55))' }};
            border: 1px solid {{ 'rgba(16, 185, 129, 0.35)' if is_millionaire else 'rgba(34,197,94,0.28)' }};
            border-left: 6px solid {{ accent }};
            border-radius: 14px;
            display: none;
            color: {{ '#E5E7EB' if is_millionaire else '#111827' }};
            box-shadow: 0 8px 16px rgba(15, 23, 42, 0.18);
            backdrop-filter: blur(8px);
            /* Explanation must be below options and inside Region 2 */
            position: relative;
            z-index: 1;
            max-height: none;
            overflow: visible;
        }
        .result-badge { position: absolute; top: 8px; right: 12px; background: {{ '#2A2D3A' if is_millionaire else 'rgba(255,255,255,0.95)' }}; border: 1px solid {{ '#4A4E5A' if is_millionaire else 'rgba(148, 163, 184, 0.32)' }}; color: {{ '#FFFFFF' if is_millionaire else '#0F172A' }}; padding: 4px 8px; border-radius: 999px; font-size: 0.85em; box-shadow: {{ 'none' if is_millionaire else '0 8px 18px rgba(15, 23, 42, 0.08)' }}; animation: badgeReveal 260ms ease-out; }
        .result-badge.correct { border-color: #12B76A; color: #12B76A; }
        .result-badge.incorrect { border-color: #F79009; color: #F79009; }
        .time-progress { height: 12px; background: {{ '#2D2F3A' if is_millionaire else 'rgba(226, 232, 240, 0.9)' }}; border: 1px solid {{ '#4A4E5A' if is_millionaire else 'rgba(148, 163, 184, 0.24)' }}; border-radius: 999px; margin: 10px 0 20px; overflow: hidden; box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.08); }
        .time-bar { height: 100%; width: 0%; background: {{ accent }}; transition: width 0.3s ease; }
        .time-bar.urgent { background: linear-gradient(90deg, #F79009 0%, #FF1A1A 100%); animation: pulse 0.9s ease-in-out infinite; }
        
        .explanation.show {
            display: block;
            animation: fadeIn 0.5s ease;
        }
        
        .explanation h3 {
            color: {{ accent }};
            margin-bottom: 8px;
            font-size: 1.02em;
            letter-spacing: 0.2px;
        }
        .explanation p { line-height: 1.6; opacity: 0.95; }
        
        .game-over {
            position: fixed;
            inset: 0;
            display: none;
            align-items: center;
            justify-content: center;
            background: {{ 'rgba(2, 6, 23, 0.62)' if is_millionaire else 'rgba(241, 245, 249, 0.72)' }};
            padding: 20px;
            z-index: 50;
        }
        .game-over-card {
            width: min(720px, 92vw);
            text-align: center;
            padding: 26px 24px;
            background: {{ 'rgba(15, 23, 42, 0.90)' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98))' }};
            border: 1px solid {{ 'rgba(148, 163, 184, 0.35)' if is_millionaire else 'rgba(148, 163, 184, 0.28)' }};
            border-radius: 22px;
            box-shadow: {{ '0 30px 80px rgba(0,0,0,0.55)' if is_millionaire else '0 28px 70px rgba(15, 23, 42, 0.16)' }};
            backdrop-filter: blur(10px);
        }
        
        .game-over h2 {
            font-size: 2em;
            margin-bottom: 20px;
            background: linear-gradient(45deg, {{ accent }}, #A7F3D0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .game-over-desc { color: {{ '#E5E7EB' if is_millionaire else '#475569' }}; font-size: 1.02em; line-height: 1.5; margin: 10px 0 16px; }
        .result-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 14px 0 18px; }
        .result-item { background: {{ 'rgba(255,255,255,0.06)' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.95), rgba(240,249,255,0.92))' }}; border: 1px solid {{ 'rgba(148,163,184,0.18)' if is_millionaire else 'rgba(191, 219, 254, 0.85)' }}; border-radius: 16px; padding: 12px 10px; box-shadow: {{ 'none' if is_millionaire else '0 12px 24px rgba(148, 163, 184, 0.10)' }}; }
        .result-label { color: {{ 'rgba(229,231,235,0.88)' if is_millionaire else '#64748B' }}; font-size: 12px; letter-spacing: 0.2px; }
        .result-value { margin-top: 6px; color: {{ '#FFFFFF' if is_millionaire else '#0F172A' }}; font-weight: 800; font-size: 20px; }
        .loading-overlay{
            position:fixed;
            inset:0;
            display:none;
            align-items:center;
            justify-content:center;
            background: {{ 'rgba(0,0,0,0.6)' if is_millionaire else 'rgba(241, 245, 249, 0.72)' }};
            z-index:9999;
            padding:18px;
        }
        .loading-card{
            min-width:min(320px, 88vw);
            padding:18px 22px;
            border-radius:18px;
            text-align:center;
            color: {{ '#EDEEF3' if is_millionaire else '#0F172A' }};
            background: {{ 'rgba(15,23,42,0.96)' if is_millionaire else 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98))' }};
            border: 1px solid {{ 'rgba(148,163,184,0.45)' if is_millionaire else 'rgba(148, 163, 184, 0.24)' }};
            box-shadow: {{ '0 20px 40px rgba(0,0,0,0.45)' if is_millionaire else '0 20px 48px rgba(15, 23, 42, 0.14)' }};
        }
        .loading-title{
            font-weight:800;
            font-size:22px;
            font-family:'Inter', 'Segoe UI', sans-serif;
        }
        
        @media (max-width: 720px) { .result-grid { grid-template-columns: 1fr; } }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes optionPressPop {
            0% { transform: translateY(1px) scale(0.985); }
            42% { transform: translateY(-2px) scale(1.022); }
            100% { transform: scale(1); }
        }
        @keyframes optionPressRipple {
            0% { opacity: 0.28; transform: translate(-50%, -50%) scale(0.25); }
            100% { opacity: 0; transform: translate(-50%, -50%) scale(10); }
        }
        @keyframes optionSelectedShine {
            0% { transform: translateX(-135%); opacity: 0; }
            18% { opacity: 0.95; }
            100% { transform: translateX(135%); opacity: 0; }
        }
        @keyframes optionCorrectPulse {
            0% { transform: scale(1); }
            40% { transform: scale(1.035); }
            100% { transform: scale(1); }
        }
        @keyframes optionWrongShake {
            0%, 100% { transform: translateX(0); }
            20% { transform: translateX(-6px); }
            40% { transform: translateX(5px); }
            60% { transform: translateX(-4px); }
            80% { transform: translateX(3px); }
        }
        @keyframes badgeReveal {
            from { opacity: 0; transform: translateY(-6px) scale(0.92); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        
        @keyframes shimmer { from { transform: translateX(-100%); } to { transform: translateX(100%); } }
        @keyframes pulse { 0% { filter: brightness(1); } 50% { filter: brightness(1.25); } 100% { filter: brightness(1); } }
        @media (orientation: portrait) {
            .game-container { aspect-ratio: {{ '9 / 16' if is_millionaire else 'unset' }}; max-width: {{ '480px' if is_millionaire else '100%' }}; }
            .game-stats { flex-direction: column; gap: 10px; }
            .options-container { grid-template-columns: 1fr; }
        }
        @media (min-width: 900px) {
            .game-container { max-width: {{ '1100px' if is_millionaire else '1180px' }}; }
        }
        
        @media (max-width: 768px) {
            html, body {
                margin: 0;
                padding: 0;
                min-height: 100%;
            }
            .game-container {
                padding: 14px;
                margin: 8px;
                width: 100%;
                max-width: 100%;
                box-sizing: border-box;
                min-height: 0;
            }
            #game-wrapper {
                width: min(100vw, 100%);
                max-width: 100%;
            }
            .game-title {
                font-size: clamp(1.5rem, 6vw, 1.9rem);
            }
            .game-stats {
                gap: 8px;
            }
            .stat-item {
                flex: 1;
            }
            .question-text {
                font-size: 1.05em;
            }
            .controls {
                flex-direction: column;
                align-items: stretch;
                gap: 10px;
                margin-top: 20px;
            }
            .control-button {
                width: 100%;
                padding: 12px 16px;
                font-size: 1em;
            }
            .lifelines {
                gap: 8px;
            }
            .lifeline-btn {
                flex: 1 1 45%;
                min-width: 0;
                font-size: 0.85em;
                padding: 8px 10px;
            }
            .options-container {
                grid-template-columns: 1fr;
            }
            .option-button {
                padding: 12px;
                font-size: 0.95em;
            }
            #game-content {
                padding: 10px 10px 8px;
            }
            .option-image {
                max-width: 60px;
                max-height: 60px;
                margin-right: 10px;
            }
            .btn-classic { position: relative; display: block; width: 100%; margin: 8px 0; }
            .btn-classic { padding: 14px 16px; background: {{ '#2F3341' if is_millionaire else 'linear-gradient(135deg, #FFFFFF 0%, #F0FDF4 52%, #EFF6FF 100%)' }}; color: {{ '#EDEEF3' if is_millionaire else '#111827' }}; border: 1px solid {{ '#4A4E5A' if is_millionaire else 'rgba(148, 163, 184, 0.28)' }}; border-radius: 14px; box-shadow: {{ '0 2px 6px rgba(0,0,0,0.24)' if is_millionaire else '0 10px 20px rgba(15, 23, 42, 0.10)' }}; }
            .btn-classic:hover { background: {{ '#3A4050' if is_millionaire else 'linear-gradient(135deg, #F8FAFC 0%, #DCFCE7 52%, #DBEAFE 100%)' }}; }
            .voice-toolbar { left: 12px; right: 12px; top: 12px; justify-content: space-between; flex-wrap: wrap; }
            .voice-toolbar select { min-width: 0; flex: 1 1 180px; }
            .intro-card { padding: 24px 20px; width: min(94vw, 560px); }
        }
    </style>
</head>
<body>
    <div id="loading-overlay" class="loading-overlay">
        <div class="loading-card">
            <div class="loading-title">
            <span id="loading-typing">{{ labels.loading }}</span>
            </div>
        </div>
    </div>
    <div id="game-bg" class="bg-layer" style="display:none;"></div>
    <div id="intro-screen" class="intro-screen" style="display:none;">
        <div class="intro-card">
            <h2 class="intro-title">{{ project_name or 'EduPlay Quiz' }}</h2>
            <p class="intro-description">{{ labels.rules or 'Luật chơi: Đọc câu hỏi và chọn đáp án đúng.' }}</p>
            <button id="start-btn" class="start-button" onclick="onStartClick()" title="{{ labels.rules or 'Luật chơi: Đọc câu hỏi và chọn đáp án đúng.' }}">{{ labels.start or 'Bắt đầu' }}</button>
        </div>
    </div>
    <div class="voice-toolbar" id="voice-toolbar" style="display:none;">
        <label for="voice-select">{{ labels.tts_voice }}</label>
        <select id="voice-select"></select>
        <label><input type="checkbox" id="tts-toggle"> {{ labels.tts_toggle }}</label>
    </div>
    <div class="zoom-toolbar" style="display:none;"></div>
    <div id="game-wrapper" class="game-container" style="display:none;">
    <div class="game-header">
            {% if is_millionaire %}<div class="logo-sprite"></div>{% endif %}
            <h1 class="game-title">{{ project_name }}</h1>
        </div>
        
        <div class="lifelines" id="lifelines" style="display: none;">
            <button class="lifeline-btn" id="fifty-btn"><span id="icon-fifty" class="sprite spr-help1"></span> 50:50</button>
            <button class="lifeline-btn" id="phone-btn"><span id="icon-phone" class="sprite spr-help2"></span> 📞 {{ labels.lifeline_phone }}</button>
            <button class="lifeline-btn" id="audience-btn"><span id="icon-audience" class="sprite spr-help3"></span> 👥 {{ labels.lifeline_audience }}</button>
        </div>
        {% if is_millionaire %}<ul id="ladder" class="ladder"></ul><div id="pb" class="pb-panel" style="display:none"></div><div id="lang" class="lang-banner"></div>{% endif %}
        <div class="game-stats" id="game-stats">
            <div class="stat-item">
                <div class="stat-value" id="current-question">1</div>
                <div>{{ labels.question }}</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="correct-count">0</div>
                <div>{{ labels.correct }}</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="score-display">0</div>
                <div>{{ labels.score }}</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="time-left">-</div>
                <div>{{ labels.time }}</div>
            </div>
        </div>
        <div class="time-progress" id="time-progress" style="display: none;"><div id="time-bar" class="time-bar"></div></div>
        
        <div id="game-content">
            <div class="question-container" id="question-container">
                <div class="question-text" id="question-text">{{ labels.loading }}</div>
                <div id="question-image-container" class="image-container"><img class="question-image" id="question-image" style="display: none;"></div>
                <div class="options-container" id="options-container"></div>
                <div class="explanation" id="explanation"></div>
            </div>
            <div class="controls" id="controls-bar">
                <button class="control-button" id="submit-btn" onclick="submitAnswer()">{{ labels.submit }}</button>
                <button class="control-button" id="next-btn" onclick="nextQuestion()" style="display: none;">{{ labels.next }}</button>
            </div>
        </div>
    </div>
    <div class="game-over" id="game-over">
        <div class="game-over-card">
            <h2 id="game-over-title">{{ labels.completed }}</h2>
            <p id="game-over-desc" class="game-over-desc">{{ labels.completed }}</p>
            <div class="result-grid" aria-hidden="true">
                <div class="result-item">
                    <div class="result-label">{{ labels.score }}</div>
                    <div class="result-value"><span id="result-score">0</span></div>
                </div>
                <div class="result-item">
                    <div class="result-label">{{ labels.question }}</div>
                    <div class="result-value" id="result-question-count">0</div>
                </div>
                <div class="result-item">
                    <div class="result-label">{{ labels.time }}</div>
                    <div class="result-value" id="result-time">-</div>
                </div>
            </div>
            <button class="control-button" onclick="restartGame()">{{ labels.play_again }}</button>
        </div>
    </div>
    <div id="popup" class="popup-overlay"><div class="popup-panel" id="popup-panel"></div></div>
    <div id="feedback-popup" class="feedback-popup" aria-hidden="true"><div id="feedback-popup-text" class="feedback-popup-text"></div></div>

    <script>
        const __SPRITE_URL = '{{ sprite_url }}';
        const labels = {{ labels_json }};
        const LOCALE = "{{ 'vi-VN' if lang_attr.startswith('vi') else ('fr-FR' if lang_attr.startswith('fr') else ('de-DE' if lang_attr.startswith('de') else ('es-ES' if lang_attr.startswith('es') else 'en-US'))) }}";
        let __loadingTimer = null;
        function __setLoading(v){
            try{
                const ov = document.getElementById('loading-overlay');
                if (!ov) return;
                ov.style.display = v ? 'flex' : 'none';
                if (v) __startTyping('{{ labels.loading }}'); else __stopTyping();
            }catch(e){}
        }
        function __startTyping(text){
            try{
                const el = document.getElementById('loading-typing');
                let i = 0, dir = 1;
                __stopTyping();
                __loadingTimer = setInterval(()=>{
                    if (!el) return;
                    el.textContent = text.substring(0, i);
                    i += dir;
                    if (i > text.length) dir = -1;
                    if (i <= 0) dir = 1;
                }, 120);
            }catch(e){}
        }
        function __stopTyping(){ try{ if(__loadingTimer){ clearInterval(__loadingTimer); __loadingTimer=null; } }catch(e){} }
        (function(){
            const style = document.createElement('style');
            style.textContent = `
                .option-button.disabled{pointer-events:none;opacity:0.8}
                .shake{animation: eduplayShake 0.32s ease-in-out 1}
                @keyframes eduplayShake{
                    0%{transform:translateX(0)}
                    25%{transform:translateX(-6px)}
                    50%{transform:translateX(6px)}
                    75%{transform:translateX(-4px)}
                    100%{transform:translateX(0)}
                }
            `;
            document.head.appendChild(style);
        })();
        function animateOptionPress(btn){
            try{
                if(!btn) return;
                btn.classList.remove('press-pop');
                void btn.offsetWidth;
                btn.classList.add('press-pop');
                setTimeout(()=>{ try{ btn.classList.remove('press-pop'); }catch(e){} }, 420);
            }catch(e){}
        }
        function setClassicOptionContent(button, prefix, text, hint){
            try{
                if(!button) return;
                const inner = document.createElement('span');
                inner.className = 'option-inner';
                const badge = document.createElement('span');
                badge.className = 'option-prefix';
                badge.textContent = String(prefix || '');
                const copyWrap = document.createElement('span');
                copyWrap.className = 'option-copy-wrap';
                const copy = document.createElement('span');
                copy.className = 'option-copy';
                copy.textContent = String(text || '');
                copyWrap.appendChild(copy);
                if (hint) {
                    const sub = document.createElement('span');
                    sub.className = 'option-hint';
                    sub.textContent = String(hint);
                    copyWrap.appendChild(sub);
                }
                const trail = document.createElement('span');
                trail.className = 'option-trail';
                trail.setAttribute('aria-hidden', 'true');
                trail.textContent = '>';
                button.innerHTML = '';
                inner.appendChild(badge);
                inner.appendChild(copyWrap);
                inner.appendChild(trail);
                button.appendChild(inner);
            }catch(e){}
        }
        // Inline bundled game data to make a single self-contained HTML file
        const gameData = {{ game_data_json }};
        (function(){
            let __manualZoom = false;
            function applyScale(s){
                var wrap=document.getElementById('game-wrapper');
                if(!wrap) return;
                if (!millionaireMode) {
                    try{ wrap.style.zoom = '1'; }catch(e){}
                    try{ wrap.style.transform = 'none'; }catch(e){}
                    try{ wrap.style.transformOrigin = 'top center'; }catch(e){}
                    return;
                }
                try{ wrap.style.zoom = String(s); }catch(e){}
                try{ wrap.style.transform = 'none'; }catch(e){}
                try{ wrap.style.transformOrigin='top center'; }catch(e){}
            }
            function autoScale(){
                if (__manualZoom) return;
                var wrap=document.getElementById('game-wrapper'); if(!wrap) return;
                if (!millionaireMode) {
                    applyScale(1);
                    return;
                }
                var th=0;
                var vtb=document.getElementById('voice-toolbar'); if (vtb && vtb.style && vtb.style.display && vtb.style.display!=='none'){ try{ th += (vtb.offsetHeight||0); }catch(e){} }
                var vw=Math.max(320, window.innerWidth - 24);
                var vh=Math.max(240, window.innerHeight - th - 24);
                var dpr = 1.0;
                try{ dpr = (window.devicePixelRatio || 1.0); }catch(e){ dpr = 1.0; }
                if (!dpr || !isFinite(dpr) || dpr <= 0) dpr = 1.0;
                var cw=(wrap.scrollWidth||wrap.offsetWidth||800) / dpr;
                var ch=(wrap.scrollHeight||wrap.offsetHeight||600) / dpr;
                var mode = (window.__EDUPLAY_SCALE_MODE || '').toString().toLowerCase();
                var sw = (vw/cw);
                var sh = (vh/ch);
                var raw = (mode === 'fitwidth') ? sw : Math.min(sw, sh);
                var maxS = (window.__EDUPLAY_NO_UPSCALE === true) ? 1.0 : 2.0;
                var bias = 1.0;
                try{
                    if (typeof window.__EDUPLAY_SCALE_BIAS === 'number' && isFinite(window.__EDUPLAY_SCALE_BIAS)) bias = window.__EDUPLAY_SCALE_BIAS;
                }catch(e){}
                var s=Math.max(0.5, Math.min(maxS, raw * bias));
                applyScale(s);
            }
            function applySpacing(v){
                try{ var root=document.documentElement; root.style.setProperty('--sp-qmargin', v+'px'); root.style.setProperty('--sp-gap', Math.max(0, v-2)+'px'); }catch(e){}
            }
            try{
                window.applyScale = applyScale;
                window.autoScale = autoScale;
                window.applySpacing = applySpacing;
                window.__setManualZoom = function(v){ __manualZoom = !!v; };
            }catch(e){}
            document.addEventListener('DOMContentLoaded', function(){
                autoScale();
                window.addEventListener('resize', autoScale);
            });
        })();
        let currentQuestionIndex = 0;
        let score = 0; // not displayed
        let correctCount = 0;
        let selectedAnswer = null;
        let selectedAnswerIndex = null;
        let gameState = 'playing'; // 'playing', 'answered', 'finished'
        let currentAudio = null;
        let bgm = null;
        let settings = gameData.game_config || {};
        let pointsPerQuestion = 0;
        try{
            const autoPoints = !!settings.auto_points_enabled;
            let totalPoints = parseInt(settings.total_points || 100);
            if (isNaN(totalPoints) || totalPoints <= 0) totalPoints = 100;
            totalPoints = Math.min(100, totalPoints);
            if (autoPoints) {
                const totalQuestions = (gameData.questions || []).length || 0;
                if (totalQuestions > 0) {
                    pointsPerQuestion = Math.max(1, Math.round(totalPoints / totalQuestions));
                } else {
                    pointsPerQuestion = 0;
                }
            } else {
                const ppq = parseInt(settings.points_per_question || 0);
                if (ppq > 0) {
                    pointsPerQuestion = ppq;
                } else {
                    // fallback: auto-calculate from total_points
                    const totalQuestions = (gameData.questions || []).length || 0;
                    let totalPoints = parseInt(settings.total_points || 100);
                    if (isNaN(totalPoints) || totalPoints <= 0) totalPoints = 100;
                    totalPoints = Math.min(100, totalPoints);
                    pointsPerQuestion = totalQuestions > 0 ? Math.max(1, Math.round(totalPoints / totalQuestions)) : 10;
                }
            }
        }catch(e){
            const totalQuestions = (gameData.questions || []).length || 1;
            pointsPerQuestion = Math.max(1, Math.round(100 / totalQuestions));
        }
        let timeLimitEnabled = (settings.time_limit_enabled !== false);
        let defaultQuestionTime = parseInt(settings.question_time || 30);
        let timerId = null;
        let timeLeft = null;
        let timeTotal = null;
        let ttsEnabled = !!settings.tts_enabled;
        let ttsLang = settings.tts_voice_lang || '{{ lang_attr }}';
        let ttsVoiceName = null;
        const exportMode = String(settings.export_mode || 'student').toLowerCase() === 'teaching' ? 'teaching' : 'student';
        const teachingMode = exportMode === 'teaching';
        const millionaireMode = {{ 'true' if is_millionaire else 'false' }};
        let audioMap = {};
        let feedbackSoundPools = { correct: [], wrong: [] };
        let feedbackSoundLastIndex = { correct: -1, wrong: -1 };
        let feedbackPopupAnim = null;
        let feedbackPopupHideTimer = null;
        let feedbackPopupActiveAudio = null;
        let feedbackPopupAudioEndedHandler = null;
        let feedbackPopupToken = 0;
        let globalMuted = true;
        let matchingCleanup = null;
        let pendingAdvanceAction = 'next';
        const AMTS_ENG = [
            [350000,200000,150000,120000,75000,50000,25000,12500,6000,3000,1500,950,500,200,100],
            [650000,350000,250000,200000,120000,75000,45000,22000,10000,5000,2250,1250,700,350,200],
            [1000000,500000,300000,220000,150000,100000,60000,30000,15000,7500,3500,1500,1000,500,350]
        ];
        const AMTS_HUN = [
            [15000000,8000000,5000000,3500000,2000000,1000000,750000,500000,300000,200000,100000,50000,35000,20000,10000],
            [30000000,15000000,7500000,5000000,3000000,1500000,1000000,750000,500000,300000,150000,100000,70000,40000,20000],
            [50000000,25000000,12500000,8000000,5000000,2500000,1500000,1000000,800000,500000,250000,150000,100000,75000,40000]
        ];
        function getLangCode(){ try{ const la = (gameData.language||'en').toLowerCase(); if (la.startsWith('hu')) return 'hun'; if (la.startsWith('de')) return 'eng'; if (la.startsWith('vi')) return 'eng'; if (la.startsWith('en')) return 'eng'; if (la.startsWith('es')) return 'eng'; if (la.startsWith('fr')) return 'eng'; return 'eng'; }catch(e){ return 'eng'; } }
        function getDiffIndex(){ try{ const d = String((gameData.game_config||{}).difficulty||'Medium').toLowerCase(); if (d.includes('easy')||d.includes('normal')) return 0; if (d.includes('hard')) return 2; return 1; }catch(e){ return 1; } }
        function getAmounts(){ const lang = getLangCode(); const di = getDiffIndex(); const arr = (lang==='hun'? AMTS_HUN : AMTS_ENG); return arr[di]||arr[0]; }
        let MILLION_AMOUNTS = getAmounts();
        const SAFE_INDICES = [4,9,14];
        function renderLadder(){ try{ if(!millionaireMode) return; const ul=document.getElementById('ladder'); if(!ul) return; ul.innerHTML=''; const n = Math.min(15, (gameData.questions||[]).length||15); for(let i=0;i<n;i++){ const amt = MILLION_AMOUNTS[i] || MILLION_AMOUNTS[MILLION_AMOUNTS.length-1]; const li=document.createElement('li'); li.textContent = '$' + amt.toLocaleString(LOCALE); ul.appendChild(li);} updateLadder(); }catch(e){} }
        function updateLadder(){ try{ if(!millionaireMode) return; const items = Array.from((document.getElementById('ladder')||{}).children||[]); items.forEach((li,idx)=>{ li.classList.remove('active','passed','safe'); if(idx === currentQuestionIndex) li.classList.add('active'); if(idx < currentQuestionIndex) li.classList.add('passed'); if (SAFE_INDICES.includes(idx)) li.classList.add('safe'); }); }catch(e){} }
        function renderAmountBars(){ /* removed to avoid overlap */ }
        function renderPB(){ try{ if(!millionaireMode) return; const pb = document.getElementById('pb'); const diff = getDiffIndex(); if (!pb) return; pb.className = 'pb-panel ' + (diff===0? 'spr-pb-normal' : diff===2? 'spr-pb-hard' : 'spr-pb-medium'); }catch(e){} }
        function renderLangBanner(){ try{ if(!millionaireMode) return; const lb = document.getElementById('lang'); if(!lb) return; const lc = getLangCode(); lb.className = 'lang-banner ' + (lc==='hun'? 'spr-hun' : 'spr-eng'); }catch(e){} }
        function shakeElement(el){
            try{
                if(!el) return;
                el.classList.remove('shake');
                void el.offsetWidth;
                el.classList.add('shake');
                setTimeout(()=>{ try{ el.classList.remove('shake'); }catch(e){} }, 360);
            }catch(e){}
        }
        function getCorrectChoiceIndex(question){
            let correctIndex = 0;
            try{
                if (typeof question.correct_answer === 'number') {
                    correctIndex = question.correct_answer;
                } else if (typeof question.correctAnswer === 'number') {
                    correctIndex = question.correctAnswer;
                } else {
                    const letters = ['A','B','C','D'];
                    const raw = (question.correct_answer !== undefined && question.correct_answer !== null) ? question.correct_answer : question.correctAnswer;
                    const upper = String(raw || '').toUpperCase();
                    const letterIndex = letters.indexOf(upper);
                    if (letterIndex >= 0) correctIndex = letterIndex;
                    else {
                        const opts = question.options || question.choices || [];
                        const found = Array.isArray(opts) ? opts.findIndex(o => String(o) === String(raw)) : -1;
                        if (found >= 0) correctIndex = found;
                    }
                }
            }catch(e){}
            return correctIndex;
        }
        function normalizeRuntimeQuestionType(question){
            try{
                const raw = String((question && (question.type || question.question_type || question.q_type || question.kind)) || '').trim().toLowerCase();
                if (raw === 'fillblank' || raw === 'cloze' || raw === 'dien_cho_trong' || raw === 'điền_chỗ_trống') return 'fill_blank';
                if (raw === 'shortanswer' || raw === 'essay' || raw === 'tu_luan' || raw === 'tự_luận') return 'short_answer';
                if (raw === 'truefalse' || raw === 'boolean') return 'true_false';
                if (raw) return raw;
                const hasTextAnswers = !!(question && ((Array.isArray(question.correct_answers) && question.correct_answers.length) || (Array.isArray(question.answers) && question.answers.length) || (question.correct_answer !== undefined && question.correct_answer !== null && String(question.correct_answer).trim() !== '')));
                const hasChoiceOptions = !!(question && ((Array.isArray(question.options) && question.options.length) || (Array.isArray(question.choices) && question.choices.length)));
                return hasTextAnswers && !hasChoiceOptions ? 'fill_blank' : 'multiple_choice';
            }catch(e){
                return 'multiple_choice';
            }
        }
        function getRuntimeQuestionText(question){
            try{
                const raw = question && (question.question !== undefined && question.question !== null ? question.question : question.text);
                return String(raw == null ? '' : raw);
            }catch(e){
                return '';
            }
        }
        function getDisplayQuestionText(question){
            const rawQuestionText = getRuntimeQuestionText(question).trim();
            const displayText = rawQuestionText || '___';
            const alreadyPrefixed = /^\\s*(câu|question|q)\\s*\\d+\\s*[:.-]/i.test(displayText);
            return alreadyPrefixed ? displayText : `${labels.question} ${currentQuestionIndex + 1}: ${displayText}`;
        }
        function renderQuestionPrompt(question, inlineInput = null){
            const questionTextEl = document.getElementById('question-text');
            if (!questionTextEl) return;
            const questionType = normalizeRuntimeQuestionType(question);
            const displayText = getDisplayQuestionText(question);
            questionTextEl.innerHTML = '';
            questionTextEl.classList.remove('fill-blank-inline');
            if (questionType !== 'fill_blank' || !inlineInput) {
                questionTextEl.textContent = displayText;
                return;
            }
            const markerMatch = displayText.match(/_{3,}/);
            const wrap = document.createElement('span');
            wrap.className = 'question-inline-wrap';
            const appendTextPart = (text) => {
                if (!text) return;
                const span = document.createElement('span');
                span.className = 'question-inline-text';
                span.textContent = text;
                wrap.appendChild(span);
            };
            if (markerMatch) {
                appendTextPart(displayText.slice(0, markerMatch.index || 0));
                wrap.appendChild(inlineInput);
                appendTextPart(displayText.slice((markerMatch.index || 0) + markerMatch[0].length));
            } else {
                appendTextPart(displayText);
                wrap.appendChild(inlineInput);
            }
            questionTextEl.classList.add('fill-blank-inline');
            questionTextEl.appendChild(wrap);
        }
        function getRuntimeTextAcceptedAnswers(question){
            try{
                const collected = [];
                const pushValues = (value) => {
                    if (Array.isArray(value)) {
                        value.forEach(item => pushValues(item));
                        return;
                    }
                    const text = String(value == null ? '' : value).trim();
                    if (text) collected.push(text);
                };
                pushValues(question && question.correct_answers);
                pushValues(question && question.answers);
                pushValues(question && question.correct_answer);
                return Array.from(new Set(collected));
            }catch(e){
                return [];
            }
        }
        function getMillionaireResultAmount(stopped){
            try{
                if(!millionaireMode) return score;
                const amounts = Array.isArray(MILLION_AMOUNTS) ? MILLION_AMOUNTS : [];
                if(!amounts.length) return score;
                if(stopped){
                    const prevIndex = Math.max(-1, currentQuestionIndex - 1);
                    return prevIndex >= 0 ? (amounts[prevIndex] || 0) : 0;
                }
                const currentIndex = Math.min(Math.max(0, currentQuestionIndex), amounts.length - 1);
                return amounts[currentIndex] || 0;
            }catch(e){
                return score;
            }
        }
        function handleTeachingChoiceSelection(answer, index){
            try{
                if (!teachingMode || gameState !== 'playing') return;
                const question = gameData.questions[currentQuestionIndex];
                if (!question || !['multiple_choice','true_false'].includes(question.type)) return;
                selectAnswer(answer, index);
                const buttons = Array.from(document.querySelectorAll('.option-button'));
                const correctIndex = question.type === 'true_false'
                    ? (((typeof question.correctAnswer!=='undefined') ? !!question.correctAnswer : !!question.correct_answer) ? 0 : 1)
                    : getCorrectChoiceIndex(question);
                const selectedBtn = buttons[index];
                if (index === correctIndex) {
                    submitAnswer();
                    return;
                }
                try{
                    if (selectedBtn) {
                        selectedBtn.classList.add('incorrect', 'disabled');
                        selectedBtn.style.pointerEvents = 'none';
                        shakeElement(selectedBtn);
                        try {
                            const sp = selectedBtn.parentElement && selectedBtn.parentElement.querySelector('.sprite');
                            if (sp) sp.className = sp.className.replace(/spr-opt-[a-z]+/,'spr-opt-red');
                        } catch(ex){}
                    }
                }catch(e){}
                try{
                    if (audioMap && audioMap.bad && !globalMuted){
                        audioMap.bad.currentTime = 0;
                        audioMap.bad.play().catch(()=>{});
                    }
                }catch(e){}
                selectedAnswer = null;
                selectedAnswerIndex = null;
                const remaining = buttons
                    .map((btn, idx) => ({ btn, idx }))
                    .filter(item => item.btn && !item.btn.classList.contains('disabled'));
                if (remaining.length === 1 && remaining[0].idx === correctIndex) {
                    const nextAnswer = question.type === 'true_false'
                        ? (correctIndex === 0)
                        : ((question.options || [])[correctIndex]);
                    selectAnswer(nextAnswer, correctIndex);
                    requestAnimationFrame(() => {
                        setTimeout(() => { try { submitAnswer(); } catch(e) {} }, 220);
                    });
                }
            }catch(e){}
        }
        function resetTeachingTextInputState() {
            try{
                const input = document.querySelector('#options-container .text-input');
                if (!input) return null;
                input.classList.remove('input-incorrect');
                input.removeAttribute('aria-invalid');
                return input;
            }catch(e){
                return null;
            }
        }
        function getAudio(key){
            try{
                let src = settings[key + '_sound_base64'] || settings[key + '_sound_path'] || '';
                if (!src && key === 'question_bg') {
                    src = settings.question_bg_sound_base64 || settings.bgm_base64 || settings.background_music_base64 || settings.background_music || '';
                }
                if (!src) return null;
                const a = new Audio(src);
                if (key === 'question_bg') { a.loop = true; a.volume = 0.3; }
                try{ a.muted = true; }catch(e){}
                return a;
            }catch(e){ return null; }
        }
        function initAudio(){
            audioMap.new_question = getAudio('new_question');
            audioMap.bg_question = getAudio('question_bg');
            audioMap.hover = getAudio('hover');
            audioMap.click = getAudio('click');
            audioMap.select = getAudio('select');
            audioMap.good = settings.correct_sound_base64 ? new Audio(settings.correct_sound_base64) : getAudio('good');
            audioMap.bad = settings.wrong_sound_base64 ? new Audio(settings.wrong_sound_base64) : getAudio('bad');
            audioMap.error = getAudio('error');
            initFeedbackSoundPools();
        }
        function normalizeFeedbackText(text){
            try{
                return String(text || '').replace(/[_]+/g, ' ').replace(/\s+/g, ' ').trim();
            }catch(e){
                return '';
            }
        }
        function createFeedbackSoundEntry(item){
            try{
                if (!item) return null;
                const src = typeof item === 'string' ? item : (item.src || item.audio || item.url || '');
                if (!src) return null;
                const audio = new Audio(src);
                audio.preload = 'auto';
                try{ audio.muted = true; }catch(e){}
                return {
                    src,
                    text: normalizeFeedbackText(typeof item === 'string' ? '' : (item.text || item.label || item.name || '')),
                    audio,
                };
            }catch(e){
                return null;
            }
        }
        function initFeedbackSoundPools(){
            try{
                const rawPools = (settings && settings.feedback_sound_pools) || {};
                feedbackSoundPools.correct = (Array.isArray(rawPools.correct) ? rawPools.correct : []).map(createFeedbackSoundEntry).filter(Boolean);
                feedbackSoundPools.wrong = (Array.isArray(rawPools.wrong) ? rawPools.wrong : []).map(createFeedbackSoundEntry).filter(Boolean);
            }catch(e){
                feedbackSoundPools.correct = [];
                feedbackSoundPools.wrong = [];
            }
        }
        function setFeedbackSoundPoolsMuted(muted){
            try{
                ['correct', 'wrong'].forEach(kind => {
                    (feedbackSoundPools[kind] || []).forEach(entry => {
                        try{ if (entry && entry.audio) entry.audio.muted = !!muted; }catch(e){}
                    });
                });
            }catch(e){}
        }
        function getAudioDurationMs(audio, fallbackMs){
            try{
                const duration = Number(audio && audio.duration);
                if (isFinite(duration) && duration > 0) return Math.max(450, Math.round(duration * 1000));
            }catch(e){}
            return Math.max(450, parseInt(fallbackMs || 1200, 10) || 1200);
        }
        function playAudioInstance(audio, fallbackMs){
            if (!audio || globalMuted) return getAudioDurationMs(audio, fallbackMs);
            try{ audio.pause(); }catch(e){}
            try{ audio.currentTime = 0; }catch(e){}
            try{ audio.play().catch(()=>{}); }catch(e){}
            return getAudioDurationMs(audio, fallbackMs);
        }
        function pickFeedbackSoundEntry(kind){
            try{
                const pool = feedbackSoundPools[kind] || [];
                if (!pool.length) return null;
                if (pool.length === 1) {
                    feedbackSoundLastIndex[kind] = 0;
                    return pool[0];
                }
                let nextIndex = Math.floor(Math.random() * pool.length);
                if (nextIndex === feedbackSoundLastIndex[kind]) {
                    nextIndex = (nextIndex + 1 + Math.floor(Math.random() * (pool.length - 1))) % pool.length;
                }
                feedbackSoundLastIndex[kind] = nextIndex;
                return pool[nextIndex];
            }catch(e){
                return null;
            }
        }
        function clearFeedbackPopupBindings(){
            try{
                if (feedbackPopupHideTimer) {
                    clearTimeout(feedbackPopupHideTimer);
                    feedbackPopupHideTimer = null;
                }
                if (feedbackPopupActiveAudio && feedbackPopupAudioEndedHandler) {
                    try{ feedbackPopupActiveAudio.removeEventListener('ended', feedbackPopupAudioEndedHandler); }catch(e){}
                }
                feedbackPopupActiveAudio = null;
                feedbackPopupAudioEndedHandler = null;
                if (feedbackPopupAnim) {
                    try{ feedbackPopupAnim.cancel(); }catch(e){}
                    feedbackPopupAnim = null;
                }
            }catch(e){}
        }
        function finalizeFeedbackPopupHide(token){
            try{
                if (token !== feedbackPopupToken) return;
                const popup = document.getElementById('feedback-popup');
                const textEl = document.getElementById('feedback-popup-text');
                clearFeedbackPopupBindings();
                if (!popup || !textEl) return;
                feedbackPopupAnim = textEl.animate([
                    { transform: 'scale(1) rotate(-8deg)', opacity: 1 },
                    { transform: 'scale(0.16) rotate(-12deg)', opacity: 0 },
                ], {
                    duration: 240,
                    easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
                    fill: 'forwards',
                });
                feedbackPopupAnim.onfinish = ()=>{
                    if (token !== feedbackPopupToken) return;
                    try{
                        textEl.textContent = '';
                        textEl.classList.remove('correct', 'wrong');
                        textEl.style.transform = 'scale(0.18) rotate(-10deg)';
                        textEl.style.opacity = '0';
                        popup.style.display = 'none';
                    }catch(e){}
                    feedbackPopupAnim = null;
                };
            }catch(e){}
        }
        function bindFeedbackPopupToAudio(audio, fallbackMs, token){
            try{
                if (token !== feedbackPopupToken) return;
                if (!audio || globalMuted) {
                    feedbackPopupHideTimer = setTimeout(()=>{ finalizeFeedbackPopupHide(token); }, Math.max(650, parseInt(fallbackMs || 1200, 10) || 1200));
                    return;
                }
                feedbackPopupActiveAudio = audio;
                feedbackPopupAudioEndedHandler = ()=>{
                    try{ finalizeFeedbackPopupHide(token); }catch(e){}
                };
                try{ audio.addEventListener('ended', feedbackPopupAudioEndedHandler, { once: true }); }catch(e){}
            }catch(e){
                feedbackPopupHideTimer = setTimeout(()=>{ finalizeFeedbackPopupHide(token); }, Math.max(650, parseInt(fallbackMs || 1200, 10) || 1200));
            }
        }
        function hideFeedbackPopup(){
            try{
                feedbackPopupToken += 1;
                clearFeedbackPopupBindings();
                const popup = document.getElementById('feedback-popup');
                const textEl = document.getElementById('feedback-popup-text');
                if (textEl) {
                    textEl.textContent = '';
                    textEl.classList.remove('correct', 'wrong');
                    textEl.style.transform = 'scale(0.18) rotate(-10deg)';
                    textEl.style.opacity = '0';
                }
                if (popup) popup.style.display = 'none';
            }catch(e){}
        }
        function showFeedbackPopup(text, isCorrect, durationMs){
            try{
                const popup = document.getElementById('feedback-popup');
                const textEl = document.getElementById('feedback-popup-text');
                const content = normalizeFeedbackText(text);
                if (!popup || !textEl || !content) return;
                feedbackPopupToken += 1;
                const token = feedbackPopupToken;
                clearFeedbackPopupBindings();
                textEl.classList.remove('correct', 'wrong');
                textEl.textContent = content;
                textEl.classList.add(isCorrect ? 'correct' : 'wrong');
                popup.style.display = 'flex';
                feedbackPopupAnim = textEl.animate([
                    { transform: 'scale(0.18) rotate(-14deg)', opacity: 0 },
                    { offset: 0.58, transform: 'scale(1.18) rotate(-9deg)', opacity: 1 },
                    { transform: 'scale(1) rotate(-8deg)', opacity: 1 },
                ], {
                    duration: Math.min(520, Math.max(280, Math.round((parseInt(durationMs || 1200, 10) || 1200) * 0.32))),
                    easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
                    fill: 'forwards',
                });
                feedbackPopupAnim.onfinish = ()=>{ if (token === feedbackPopupToken) feedbackPopupAnim = null; };
                return token;
            }catch(e){}
            return null;
        }
        function playFeedbackCue(kind, options = {}){
            try{
                const isCorrect = kind === 'correct';
                const useRandomPool = options.useRandomPool !== false;
                const showPopup = options.showPopup !== false;
                const entry = useRandomPool ? pickFeedbackSoundEntry(kind) : null;
                if (entry && entry.audio) {
                    const durationMs = playAudioInstance(entry.audio, 1400);
                    if (showPopup && entry.text) {
                        const token = showFeedbackPopup(entry.text, isCorrect, durationMs);
                        bindFeedbackPopupToAudio(entry.audio, durationMs, token);
                    }
                    return durationMs;
                }
                const fallbackAudio = isCorrect ? audioMap.good : audioMap.bad;
                const durationMs = playAudioInstance(fallbackAudio, 1200);
                if (showPopup) {
                    const token = showFeedbackPopup(isCorrect ? 'Correct!' : 'Keep trying!', isCorrect, durationMs);
                    bindFeedbackPopupToAudio(fallbackAudio, durationMs, token);
                }
                return durationMs;
            }catch(e){
                return 1200;
            }
        }
        function initVoicesUI(){
            try{
                const tb = document.getElementById('voice-toolbar');
                const sel = document.getElementById('voice-select');
                const toggle = document.getElementById('tts-toggle');
                if (!('speechSynthesis' in window)) return;
                tb.style.display = ttsEnabled ? 'flex' : 'none';
                toggle.checked = !!ttsEnabled;
                toggle.onchange = ()=>{ ttsEnabled = !!toggle.checked; tb.style.display = ttsEnabled ? 'flex':'none'; localStorage.setItem('tts_enabled', String(ttsEnabled)); };
                const fill = ()=>{
                    const voices = window.speechSynthesis.getVoices()||[];
                    sel.innerHTML = '';
                    const pri = voices.filter(v=> String(v.lang||'').toLowerCase().startsWith(String(ttsLang||'').toLowerCase()));
                    const sec = voices.filter(v=> !String(v.lang||'').toLowerCase().startsWith(String(ttsLang||'').toLowerCase()));
                    [...pri, ...sec].forEach(v=>{
                        const opt = document.createElement('option');
                        opt.value = v.name; opt.textContent = `${v.name} (${v.lang})`;
                        sel.appendChild(opt);
                    });
                    let preferred = localStorage.getItem('tts_voice_name');
                    if (!preferred){
                        const match = voices.find(v=> String(v.lang||'').toLowerCase().startsWith(String(ttsLang||'').toLowerCase()));
                        preferred = match ? match.name : (voices[0] ? voices[0].name : null);
                    }
                    if (preferred){ sel.value = preferred; ttsVoiceName = preferred; }
                };
                sel.onchange = ()=>{ ttsVoiceName = sel.value; localStorage.setItem('tts_voice_name', ttsVoiceName||''); };
                window.speechSynthesis.onvoiceschanged = fill;
                fill();
            }catch(e){}
        }
        function speakText(text) {
            try {
                if (!ttsEnabled) return;
                if ('speechSynthesis' in window) {
                    const u = new SpeechSynthesisUtterance(String(text||''));
                    u.lang = ttsLang || '{{ lang_attr }}';
                    try{
                        const voices = window.speechSynthesis.getVoices()||[];
                        if (ttsVoiceName){
                            const v = voices.find(x=> x.name === ttsVoiceName);
                            if (v) u.voice = v;
                        }
                    }catch(e){}
                    try { window.speechSynthesis.cancel(); } catch(e){}
                    window.speechSynthesis.speak(u);
                }
            } catch(e){}
        }
        
        function onStartClick(){
            try{ globalMuted=false; }catch(e){}
            try{ document.getElementById('intro-screen').style.display='none'; document.getElementById('game-wrapper').style.display='flex'; }catch(e){}
            try{ if (window.__setManualZoom) window.__setManualZoom(false); }catch(e){}
            try{
                requestAnimationFrame(()=>{ try{ if(window.autoScale) window.autoScale(); }catch(e){} });
                setTimeout(()=>{ try{ if(window.autoScale) window.autoScale(); }catch(e){} }, 120);
            }catch(e){}
            startGame();
        }
        // Initialize game using inline data
        function startGame() {
            __setLoading(true);
            if (!gameData || !gameData.questions || gameData.questions.length === 0) {
                document.getElementById('question-text').textContent = '{{ labels.no_questions }}';
                __setLoading(false);
                return;
            }
            try{ document.getElementById('intro-screen').style.display = 'none'; }catch(e){}
            try{ document.getElementById('game-wrapper').style.display = 'flex'; }catch(e){}

            // Shuffle questions if enabled
            try{
                if (settings.randomize_questions !== false) {
                    var qs = gameData.questions;
                    for (var _i = qs.length - 1; _i > 0; _i--) {
                        var _j = Math.floor(Math.random() * (_i + 1));
                        var _tmp = qs[_i]; qs[_i] = qs[_j]; qs[_j] = _tmp;
                    }
                    gameData.questions = qs;
                }
            }catch(e){}

            currentQuestionIndex = 0;
            score = 0;
            correctCount = 0;
            gameState = 'playing';
            try{
                initAudio();
                try{ if(!globalMuted){ Object.keys(audioMap).forEach(k=>{ try{ if(audioMap[k]) audioMap[k].muted=false; }catch(e){} }); } }catch(e){}
                try{ setFeedbackSoundPoolsMuted(globalMuted); }catch(e){}
                if (audioMap.bg_question && !globalMuted) { bgm = audioMap.bg_question; bgm.currentTime = 0; bgm.play().catch(()=>{}); }
            } catch(e){}
            

            
            showQuestion();
            updateStats();
            initVoicesUI();
            // No millionaire-specific initialization needed
            __setLoading(false);
            renderLadder();
            renderAmountBars();
            renderPB();
            renderLangBanner();
        }
        
        function showQuestion() {
            if (currentQuestionIndex >= gameData.questions.length) {
                endGame();
                return;
            }
            
            const question = gameData.questions[currentQuestionIndex];
            const questionType = normalizeRuntimeQuestionType(question);
            // Fallback: tự sinh lựa chọn nếu người dùng chỉ thêm câu hỏi trống
            try {
                if (questionType === 'multiple_choice' && (!Array.isArray(question.options) || question.options.length < 2)) {
                    question.options = ['Tuỳ chọn 1','Tuỳ chọn 2','Tuỳ chọn 3','Tuỳ chọn 4'];
                    if (question.correct_answer === undefined || question.correct_answer === null) question.correct_answer = 0;
                }
            } catch(e) {}
            let questionInlineInput = null;
            renderQuestionPrompt(question);
            try{ if (audioMap.new_question && !globalMuted){ audioMap.new_question.currentTime = 0; audioMap.new_question.play().catch(()=>{}); } }catch(e){}

            // Shuffle options for multiple choice while keeping correct answer index in sync
            try {
                if (questionType === 'multiple_choice' &&
                    Array.isArray(question.options) &&
                    question.options.length > 1) {
                    const original = question.options.map((opt, idx) => ({ opt, idx }));
                    for (let i = original.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        const tmp = original[i];
                        original[i] = original[j];
                        original[j] = tmp;
                    }
                    question.options = original.map(o => o.opt);
                    if (typeof question.correct_answer === 'number') {
                        const mappedIndex = original.findIndex(o => o.idx === question.correct_answer);
                        if (mappedIndex >= 0) {
                            question.correct_answer = mappedIndex;
                        }
                    } else if (typeof question.correct_answer === 'string') {
                        const letters = ['A','B','C','D'];
                        const upper = question.correct_answer.toUpperCase();
                        const letterIndex = letters.indexOf(upper);
                        if (letterIndex >= 0) {
                            const mappedIndex = original.findIndex(o => o.idx === letterIndex);
                            if (mappedIndex >= 0) question.correct_answer = mappedIndex;
                        } else {
                            const valIndex = original.findIndex(o => String(o.opt) === String(question.correct_answer));
                            if (valIndex >= 0) question.correct_answer = valIndex;
                        }
                    }
                }
            } catch(e) {}
            
            // Show question image if available with shimmer loader
            const questionImage = document.getElementById('question-image');
            const imageContainer = document.getElementById('question-image-container');
            if (question.image_base64) {
                imageContainer.style.display = 'block';
                imageContainer.classList.add('loading');
                questionImage.onload = ()=>{ try{ imageContainer.classList.remove('loading'); questionImage.style.display='block'; }catch(e){} };
                questionImage.onerror = ()=>{ try{ imageContainer.classList.remove('loading'); questionImage.style.display='none'; }catch(e){} };
                questionImage.src = question.image_base64;
            } else {
                imageContainer.classList.remove('loading');
                questionImage.style.display = 'none';
                imageContainer.style.display = 'none';
            }
            
            const optionsContainer = document.getElementById('options-container');
            optionsContainer.innerHTML = '';
            try{ if(matchingCleanup){ matchingCleanup(); matchingCleanup=null; } }catch(e){ matchingCleanup=null; }
            
            const cfg = gameData.game_config || {};
            const clickSfx = audioMap.click || (cfg.click_sound_base64 ? new Audio(cfg.click_sound_base64) : null);
            const hoverSfx = audioMap.hover || null;
            const selectSfx = audioMap.select || null;
            const correctSfx = audioMap.good || (cfg.correct_sound_base64 ? new Audio(cfg.correct_sound_base64) : null);
            const wrongSfx = audioMap.bad || (cfg.wrong_sound_base64 ? new Audio(cfg.wrong_sound_base64) : null);
            const lifelinesBar = document.getElementById('lifelines');
            lifelinesBar.style.display = millionaireMode ? 'flex' : 'none';

            if (questionType === 'multiple_choice' && question.options) {
                if ({{ 'true' if is_millionaire else 'false' }}) {
                    const spr = ['btn-blue-left','btn-red-right','btn-green-left','btn-yellow-right'];
                    question.options.forEach((option, index) => {
                        const wrap = document.createElement('div');
                        wrap.className = 'option-wrap';
                        const bg = document.createElement('div');
                        const cls = spr[index % spr.length] + ' option-sprite scale-80';
                        bg.className = cls;
                        const button = document.createElement('button');
                        button.className = 'option-button';
                        const label = document.createElement('div');
                        label.className = 'option-label';
                        label.textContent = `${String.fromCharCode(65 + index)}. ${option}`;
                        button.onclick = () => { 
                            try{ if(clickSfx){ clickSfx.currentTime = 0; clickSfx.play().catch(()=>{}); } }catch(e){}
                            try{ if(selectSfx){ selectSfx.currentTime = 0; selectSfx.play().catch(()=>{}); } }catch(e){}
                            if (teachingMode) handleTeachingChoiceSelection(option, index);
                            else selectAnswer(option, index);
                        };
                        button.onmouseenter = () => { try{ if(hoverSfx){ hoverSfx.currentTime = 0; hoverSfx.play().catch(()=>{}); } }catch(e){} };
                        try{
                            const contW = optionsContainer.clientWidth || 800;
                            const target = Math.max(360, Math.min(540, contW - 40));
                            const baseW = (cls.includes('left')? (cls.includes('blue')?463: cls.includes('red')?456: cls.includes('green')?451:454) : (cls.includes('blue')?476: cls.includes('red')?472: cls.includes('green')?473:480));
                            const baseH = (cls.includes('left')? (cls.includes('blue')?146: cls.includes('red')?160: cls.includes('green')?146:144) : (cls.includes('blue')?155: cls.includes('red')?152: cls.includes('green')?145:144));
                            const scale = Math.max(0.5, Math.min(1.25, target / baseW));
                            bg.style.transform = `scale(${scale})`;
                            bg.style.transformOrigin = 'left center';
                            wrap.style.height = `${Math.round(baseH * scale)}px`;
                        }catch(e){}
                        wrap.appendChild(bg);
                        wrap.appendChild(button);
                        wrap.appendChild(label);
                        optionsContainer.appendChild(wrap);
                    });
                } else {
                    // Simple buttons for classic quiz
                    question.options.forEach((option, index) => {
                        const button = document.createElement('button');
                        button.className = 'option-button btn-classic';
                        setClassicOptionContent(button, String.fromCharCode(65 + index), option);
                        button.onclick = () => { 
                            try{ if(clickSfx){ clickSfx.currentTime = 0; clickSfx.play().catch(()=>{}); } }catch(e){}
                            try{ if(selectSfx){ selectSfx.currentTime = 0; selectSfx.play().catch(()=>{}); } }catch(e){}
                            if (teachingMode) handleTeachingChoiceSelection(option, index);
                            else selectAnswer(option, index);
                        };
                        button.onmouseenter = () => { try{ if(hoverSfx){ hoverSfx.currentTime = 0; hoverSfx.play().catch(()=>{}); } }catch(e){} };
                        optionsContainer.appendChild(button);
                    });
                }
            } else if (questionType === 'true_false') {
                [true, false].forEach((tf, index) => {
                    const button = document.createElement('button');
                    button.className = 'option-button btn-classic btn-tf ' + (tf ? 'btn-true' : 'btn-false');
                    setClassicOptionContent(button, String.fromCharCode(65 + index), tf ? labels.true : labels.false);
                    button.onclick = () => {
                        if(clickSfx){ try{ clickSfx.currentTime = 0; clickSfx.play(); }catch(e){} }
                        if(selectSfx){ try{ selectSfx.currentTime = 0; selectSfx.play().catch(()=>{}); }catch(e){} }
                        if (teachingMode) handleTeachingChoiceSelection(tf, index);
                        else selectAnswer(tf, index);
                    };
                    button.onmouseenter = () => { try{ if(hoverSfx){ hoverSfx.currentTime = 0; hoverSfx.play().catch(()=>{}); } }catch(e){} };
                    optionsContainer.appendChild(button);
                });
            } else if (questionType === 'fill_blank') {
                const input = document.createElement('input');
                input.type = 'text';
                input.placeholder = '';
                input.className = 'text-input inline-blank-input';
                questionInlineInput = input;
                try { input.autocomplete = 'off'; input.spellcheck = false; } catch(e) {}
                input.oninput = () => {
                    resetTeachingTextInputState();
                    selectedAnswer = input.value;
                    selectedAnswerIndex = 0;
                };
                input.onkeydown = (e) => { try { if (e.key === 'Enter') { e.preventDefault(); submitAnswer(); } } catch(ex) {} };
            } else if (questionType === 'short_answer') {
                const input = document.createElement('input');
                input.type = 'text';
                input.placeholder = labels.input_placeholder;
                input.className = 'text-input';
                try { input.autocomplete = 'off'; input.spellcheck = false; } catch(e) {}
                input.oninput = () => {
                    resetTeachingTextInputState();
                    selectedAnswer = input.value;
                    selectedAnswerIndex = 0;
                };
                input.onkeydown = (e) => { try { if (e.key === 'Enter') { e.preventDefault(); submitAnswer(); } } catch(ex) {} };
                optionsContainer.appendChild(input);
            } else if (questionType === 'matching' && question.pairs) {
                const wrap = document.createElement('div');
                wrap.className = 'matching-wrap';
                wrap.style.gridColumn = '1 / -1';
                const grid = document.createElement('div');
                grid.className = 'matching-grid';
                const leftCol = document.createElement('div');
                const rightCol = document.createElement('div');
                leftCol.className = 'matching-col';
                rightCol.className = 'matching-col';

                const summary = document.createElement('div');
                summary.className = 'matching-summary';
                if (teachingMode) summary.style.display = 'none';
                summary.style.gridColumn = '1 / -1';

                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.classList.add('matching-lines');
                svg.setAttribute('width', '100%');
                svg.setAttribute('height', '100%');

                const rawPairs = Array.isArray(question.pairs) ? question.pairs : [];
                const validIndices = [];
                rawPairs.forEach((p, idx) => {
                    const l = String((p && p.left) || '').trim();
                    const r = String((p && p.right) || '').trim();
                    if (l || r) validIndices.push(idx);
                });
                question._matching_valid = validIndices.slice();

                const rights = validIndices.map((idx) => ({
                    id: idx,
                    text: String((rawPairs[idx] && rawPairs[idx].right) || '').trim()
                }));
                for (let i = rights.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    const tmp = rights[i];
                    rights[i] = rights[j];
                    rights[j] = tmp;
                }

                const state = { pendingLeft: null, matches: {}, usedRights: {} };
                const leftButtons = {};
                const rightButtons = {};

                const playClick = () => { if (clickSfx) { try { clickSfx.currentTime = 0; clickSfx.play(); } catch(e) {} } };

                const renderLines = () => {
                    try{
                        const w = Math.max(1, wrap.clientWidth || 1);
                        const h = Math.max(1, wrap.clientHeight || 1);
                        svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
                        while (svg.firstChild) svg.removeChild(svg.firstChild);
                        const wrapRect = wrap.getBoundingClientRect();
                        const scaleX = w / Math.max(1, wrapRect.width || w);
                        const scaleY = h / Math.max(1, wrapRect.height || h);
                        const getMatchAnchorX = (rect, side) => {
                            const baseLeft = (rect.left - wrapRect.left) * scaleX;
                            const width = (rect.width || 0) * scaleX;
                            return side === 'left' ? baseLeft : (baseLeft + width);
                        };
                        const getMatchAnchorPoint = (el, side) => {
                            const anchor = el.querySelector(`.matching-anchor-${side}`);
                            const rect = el.getBoundingClientRect();
                            return {
                                x: getMatchAnchorX(rect, side),
                                y: ((rect.top - wrapRect.top) * scaleY) + (((rect.height || 0) * scaleY) * 0.5),
                            };
                        };
                        Object.keys(state.matches).forEach((k) => {
                            const leftIdx = parseInt(k);
                            const rightId = state.matches[leftIdx];
                            const lb = leftButtons[leftIdx];
                            const rb = rightButtons[rightId];
                            if (!lb || !rb) return;
                            const p1 = getMatchAnchorPoint(lb, 'right');
                            const p2 = getMatchAnchorPoint(rb, 'left');
                            const x1 = p1.x;
                            const y1 = p1.y;
                            const x2 = p2.x;
                            const y2 = p2.y;
                            const d = `M ${x1} ${y1} L ${x2} ${y2}`;
                            const shadow = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                            shadow.setAttribute('d', d);
                            shadow.setAttribute('class', 'match-line-shadow');
                            svg.appendChild(shadow);
                            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                            path.setAttribute('d', d);
                            path.setAttribute('class', 'match-line');
                            svg.appendChild(path);
                            const c1 = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                            c1.setAttribute('cx', String(x1));
                            c1.setAttribute('cy', String(y1));
                            c1.setAttribute('r', '5');
                            c1.setAttribute('class', 'match-dot');
                            svg.appendChild(c1);
                            const c2 = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                            c2.setAttribute('cx', String(x2));
                            c2.setAttribute('cy', String(y2));
                            c2.setAttribute('r', '5');
                            c2.setAttribute('class', 'match-dot');
                            svg.appendChild(c2);
                        });
                    }catch(e){}
                };

                const unmatchByLeft = (leftIdx) => {
                    const rid = state.matches[leftIdx];
                    if (rid === undefined || rid === null) return;
                    delete state.matches[leftIdx];
                    delete state.usedRights[rid];
                    try { leftButtons[leftIdx].classList.remove('selected'); leftButtons[leftIdx].classList.remove('pending'); } catch(e) {}
                    try { rightButtons[rid].classList.remove('selected'); } catch(e) {}
                };

                const unmatchByRight = (rightId) => {
                    const leftIdx = Object.keys(state.matches).find(k => String(state.matches[k]) === String(rightId));
                    if (leftIdx === undefined) return;
                    unmatchByLeft(parseInt(leftIdx));
                };

                const updateSelection = () => {
                    if (state.pendingLeft !== null) {
                        Object.keys(leftButtons).forEach(k => {
                            const idx = parseInt(k);
                            if (idx === state.pendingLeft && state.matches[idx] === undefined) leftButtons[idx].classList.add('pending');
                            else leftButtons[idx].classList.remove('pending');
                        });
                    } else {
                        Object.keys(leftButtons).forEach(k => { try { leftButtons[parseInt(k)].classList.remove('pending'); } catch(e) {} });
                    }
                    const matchedCount = Object.keys(state.matches).length;
                    if (matchedCount === validIndices.length && validIndices.length > 0) {
                        selectedAnswer = { matches: Object.assign({}, state.matches) };
                        selectedAnswerIndex = 0;
                    } else {
                        selectedAnswer = null;
                        selectedAnswerIndex = null;
                    }
                    const chips = [];
                    Object.keys(state.matches).sort((a,b)=>parseInt(a)-parseInt(b)).forEach(k => {
                        const li = parseInt(k);
                        const rid = state.matches[li];
                        const lt = String((rawPairs[li] && rawPairs[li].left) || '').trim();
                        const rt = String((rawPairs[rid] && rawPairs[rid].right) || '').trim();
                        if (lt || rt) chips.push(`${lt} → ${rt}`);
                    });
                    summary.innerHTML = chips.map(t => `<span class="matching-chip">${t}</span>`).join('');
                    try{ requestAnimationFrame(renderLines); }catch(e){ try{ renderLines(); }catch(ex){} }
                };

                validIndices.forEach((idx) => {
                    const text = String((rawPairs[idx] && rawPairs[idx].left) || '').trim();
                    const btn = document.createElement('button');
                    btn.className = 'option-button btn-classic';
                    btn.innerHTML = `<span class="matching-anchor matching-anchor-left" aria-hidden="true"></span><span class="matching-anchor matching-anchor-right" aria-hidden="true"></span><span class="matching-label"></span>`;
                    btn.querySelector('.matching-label').textContent = text;
                    btn.onclick = () => {
                        playClick();
                        if (state.matches[idx] !== undefined) {
                            unmatchByLeft(idx);
                            if (state.pendingLeft === idx) state.pendingLeft = null;
                            updateSelection();
                            return;
                        }
                        if (state.pendingLeft === idx) state.pendingLeft = null;
                        else state.pendingLeft = idx;
                        updateSelection();
                    };
                    leftButtons[idx] = btn;
                    leftCol.appendChild(btn);
                });

                rights.forEach((r) => {
                    const btn = document.createElement('button');
                    btn.className = 'option-button btn-classic';
                    btn.innerHTML = `<span class="matching-anchor matching-anchor-left" aria-hidden="true"></span><span class="matching-anchor matching-anchor-right" aria-hidden="true"></span><span class="matching-label"></span>`;
                    btn.querySelector('.matching-label').textContent = r.text;
                    btn.onclick = () => {
                        playClick();
                        if (state.usedRights[r.id]) {
                            unmatchByRight(r.id);
                            updateSelection();
                            return;
                        }
                        if (state.pendingLeft === null || state.pendingLeft === undefined) return;
                        const li = state.pendingLeft;
                        if (teachingMode && Number(li) !== Number(r.id)) {
                            try{
                                if (wrongSfx) {
                                    wrongSfx.currentTime = 0;
                                    wrongSfx.play().catch(()=>{});
                                }
                            }catch(e){}
                            try { shakeElement(leftButtons[li]); } catch(e) {}
                            try { shakeElement(btn); } catch(e) {}
                            state.pendingLeft = null;
                            updateSelection();
                            return;
                        }
                        if (state.matches[li] !== undefined) unmatchByLeft(li);
                        state.matches[li] = r.id;
                        state.usedRights[r.id] = true;
                        if (teachingMode) {
                            try {
                                if (correctSfx) {
                                    correctSfx.currentTime = 0;
                                    correctSfx.play().catch(()=>{});
                                }
                            } catch(e) {}
                        }
                        try { leftButtons[li].classList.add('selected'); leftButtons[li].classList.remove('pending'); } catch(e) {}
                        try { btn.classList.add('selected'); } catch(e) {}
                        state.pendingLeft = null;
                        updateSelection();
                        if (teachingMode && Object.keys(state.matches).length === validIndices.length && validIndices.length > 0) {
                            selectedAnswer = { matches: Object.assign({}, state.matches) };
                            selectedAnswerIndex = 0;
                            submitAnswer();
                        }
                    };
                    rightButtons[r.id] = btn;
                    rightCol.appendChild(btn);
                });

                grid.appendChild(leftCol);
                grid.appendChild(rightCol);
                wrap.appendChild(svg);
                wrap.appendChild(grid);
                optionsContainer.appendChild(wrap);
                optionsContainer.appendChild(summary);
                updateSelection();
                const onLayout = () => { try{ requestAnimationFrame(renderLines); }catch(e){ try{ renderLines(); }catch(ex){} } };
                window.addEventListener('resize', onLayout, { passive: true });
                document.addEventListener('scroll', onLayout, true);
                let ro = null;
                try{
                    ro = new ResizeObserver(onLayout);
                    ro.observe(wrap);
                }catch(e){}
                matchingCleanup = () => {
                    try{ window.removeEventListener('resize', onLayout); }catch(e){}
                    try{ document.removeEventListener('scroll', onLayout, true); }catch(e){}
                    try{ if (ro) ro.disconnect(); }catch(e){}
                };
                onLayout();
            }
            renderQuestionPrompt(question, questionInlineInput);
            try { if (questionInlineInput) questionInlineInput.focus(); } catch(e) {}
            
            // Hide explanation and reset buttons
            const __exEl = document.getElementById('explanation');
            __exEl.classList.remove('show');
            try{ __exEl.innerHTML = ''; }catch(e){}
            const choiceTeachingMode = teachingMode && ['multiple_choice', 'true_false', 'matching'].includes(String(questionType || ''));
            document.getElementById('submit-btn').style.display = choiceTeachingMode ? 'none' : 'inline-block';
            document.getElementById('next-btn').style.display = 'none';
            try{
                requestAnimationFrame(()=>{ try{ if(window.autoScale) window.autoScale(); }catch(e){} });
            }catch(e){}
            
            selectedAnswer = null;
            selectedAnswerIndex = null;
            try{ document.getElementById('fifty-btn').disabled = !!lifelinesUsed.fifty; } catch(e){}
            gameState = 'playing';
            if (timerId) { clearInterval(timerId); timerId = null; }
            if (timeLimitEnabled) {
                let qTime = parseInt((question.time_limit !== undefined ? question.time_limit : defaultQuestionTime));
                timeLeft = isNaN(qTime) ? defaultQuestionTime : qTime;
                timeTotal = timeLeft;
                document.getElementById('time-left').textContent = timeLeft;
                document.getElementById('time-progress').style.display = 'block';
                document.getElementById('time-bar').style.width = '100%';
                timerId = setInterval(() => {
                    timeLeft -= 1;
                    document.getElementById('time-left').textContent = Math.max(0, timeLeft);
                    try {
                        const ratio = Math.max(0, Math.min(1, timeLeft / timeTotal));
                        const tb = document.getElementById('time-bar');
                        tb.style.width = (ratio * 100) + '%';
                        if (ratio <= 0.2) { tb.classList.add('urgent'); } else { tb.classList.remove('urgent'); }
                    } catch(e) {}
                    if (timeLeft <= 0) {
                        clearInterval(timerId);
                        timerId = null;
                        gameState = 'answered';
                        document.getElementById('submit-btn').style.display = 'none';
                        document.getElementById('next-btn').style.display = 'inline-block';
                        document.getElementById('time-progress').style.display = 'none';
                        setTimeout(()=>{ try{ nextQuestion(); }catch(e){} }, 1000);
                    }
                }, 1000);
            } else {
                document.getElementById('time-left').textContent = '-';
                document.getElementById('time-progress').style.display = 'none';
            }
            
            // Play audio if available
            if (question.audio_base64) {
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }
                currentAudio = new Audio(question.audio_base64);
                if (!globalMuted) { try{ currentAudio.play().catch(()=>{}); }catch(e){} }
            } else {
                speakText(getRuntimeQuestionText(question));
            }
            updateLadder();
            renderAmountBars();
            renderPB();
            renderLangBanner();
        }
        
        function selectAnswer(answer, index) {
            if (gameState !== 'playing') return;
            
            selectedAnswer = answer;
            selectedAnswerIndex = index;
            
            // Remove previous selections
            document.querySelectorAll('.option-button').forEach(btn => {
                btn.classList.remove('selected');
                try { btn.parentElement.classList.remove('selected'); } catch(e){}
            });
            
            // Mark selected answer
            const btn = document.querySelectorAll('.option-button')[index];
            btn.classList.add('selected');
            try { btn.parentElement.classList.add('selected'); } catch(e){}
            try { const sp = btn.parentElement.querySelector('.sprite'); if (sp) sp.className = sp.className.replace(/spr-opt-[a-z]+/,'spr-opt-yellow'); } catch(e){}
            animateOptionPress(btn);
        }
        
        function submitAnswer() {
            if (gameState !== 'playing' || selectedAnswer === null) {
                try{ if (audioMap && audioMap.error && !globalMuted){ audioMap.error.currentTime = 0; audioMap.error.play().catch(()=>{}); } }catch(e){}
                alert(labels.select_prompt);
                return;
            }
            const question = gameData.questions[currentQuestionIndex];
            const questionType = normalizeRuntimeQuestionType(question);
            const delayMs = millionaireMode ? parseInt(settings.reveal_delay_ms||1500) : 0;
            document.querySelectorAll('.option-button').forEach(btn=>{ btn.classList.add('disabled'); });
            document.getElementById('submit-btn').style.display = 'none';
            const finalizeSubmission = ()=>{
                let isCorrect = false;
                if (questionType === 'multiple_choice') {
                    const selectedIndex = selectedAnswerIndex;
                    let correctIndex = 0;
                    if (typeof question.correct_answer === 'number') {
                        correctIndex = question.correct_answer;
                    } else {
                        const letters = ['A','B','C','D'];
                        correctIndex = letters.indexOf(String(question.correct_answer).toUpperCase());
                    }
                    isCorrect = selectedIndex === correctIndex;
                } else if (questionType === 'true_false') {
                    let ca = question.correct_answer;
                    if (typeof ca !== 'boolean') {
                        const s = String(ca === undefined || ca === null ? '' : ca).trim().toLowerCase();
                        if (s === 'true' || s === 'đúng' || s === 'dung' || s === 'a' || s === '1' || s === 'yes' || s === 'y') ca = true;
                        else if (s === 'false' || s === 'sai' || s === 'b' || s === '0' || s === 'no' || s === 'n') ca = false;
                        else ca = !!ca;
                    }
                    isCorrect = selectedAnswer === ca;
                } else if (questionType === 'fill_blank' || questionType === 'short_answer') {
                    const ans = (selectedAnswer || '').trim().toLowerCase();
                    const arr = getRuntimeTextAcceptedAnswers(question);
                    const corrects = arr.map(x => String(x).trim().toLowerCase());
                    isCorrect = ans && corrects.includes(ans);
                } else if (questionType === 'matching') {
                    try {
                        const m = selectedAnswer && selectedAnswer.matches ? selectedAnswer.matches : null;
                        const valid = Array.isArray(question._matching_valid) ? question._matching_valid : (Array.isArray(question.pairs) ? question.pairs.map((_, i) => i) : []);
                        if (m && valid.length > 0) {
                            isCorrect = valid.every(i => m[i] !== undefined && Number(m[i]) === Number(i));
                            isCorrect = isCorrect && (Object.keys(m).length === valid.length);
                        } else isCorrect = false;
                    } catch(e) { isCorrect = false; }
                }
                resetTeachingTextInputState();
                if (isCorrect) {
                    correctCount++;
                    try{
                        if (pointsPerQuestion && pointsPerQuestion > 0){
                            score += pointsPerQuestion;
                        }
                    }catch(e){}
                }
                document.querySelectorAll('.option-button').forEach((btn, index) => {
                    try { btn.querySelectorAll('.result-badge').forEach(x => x.remove()); } catch(e){}
                    if (questionType === 'multiple_choice') {
                        let correctIndex = 0;
                        if (typeof question.correct_answer === 'number') {
                            correctIndex = question.correct_answer;
                        } else {
                            const letters = ['A','B','C','D'];
                            correctIndex = letters.indexOf(String(question.correct_answer).toUpperCase());
                        }
                        if (index === correctIndex) {
                            btn.classList.add('correct');
                            const mark = document.createElement('div'); mark.className = 'result-mark spr-green-ok'; btn.appendChild(mark);
                            try { const sp = btn.parentElement.querySelector('.sprite'); if (sp) sp.className = sp.className.replace(/spr-opt-[a-z]+/,'spr-opt-green'); } catch(e){}
                        } else if (btn.classList.contains('selected')) {
                            btn.classList.add('incorrect');
                            const mark = document.createElement('div'); mark.className = 'result-mark spr-red-x'; btn.appendChild(mark);
                            try { const sp = btn.parentElement.querySelector('.sprite'); if (sp) sp.className = sp.className.replace(/spr-opt-[a-z]+/,'spr-opt-red'); } catch(e){}
                        }
                    } else if (questionType === 'true_false') {
                        let ca = question.correct_answer;
                        if (typeof ca !== 'boolean') {
                            const s = String(ca === undefined || ca === null ? '' : ca).trim().toLowerCase();
                            if (s === 'true' || s === 'đúng' || s === 'dung' || s === 'a' || s === '1' || s === 'yes' || s === 'y') ca = true;
                            else if (s === 'false' || s === 'sai' || s === 'b' || s === '0' || s === 'no' || s === 'n') ca = false;
                            else ca = !!ca;
                        }
                        const correctIndex = ca ? 0 : 1;
                        if (index === correctIndex) {
                            btn.classList.add('correct'); const mark = document.createElement('div'); mark.className = 'result-mark spr-green-ok'; btn.appendChild(mark);
                        } else if (btn.classList.contains('selected')) {
                            btn.classList.add('incorrect'); const mark = document.createElement('div'); mark.className = 'result-mark spr-red-x'; btn.appendChild(mark);
                        }
                    }
                });
                try{
                    if (isCorrect) playFeedbackCue('correct');
                    else playFeedbackCue('wrong', { useRandomPool: !teachingMode, showPopup: !teachingMode });
                }catch(e){}
                const showExplanationsEnabled = (settings.show_explanations !== false) && (settings.show_explanation !== false) && (settings.showExplanations !== false);
                const showCorrectEnabled = (settings.show_correct_answer !== false) && (settings.showCorrectAnswer !== false);
                const textStudentFlow = question.type === 'fill_blank' || question.type === 'short_answer';
                const ex = document.getElementById('explanation');
                try{ if (ex){ ex.classList.remove('show'); ex.innerHTML=''; } }catch(e){}
                function appendBlock(title, text, preLine){
                    try{
                        if (!ex) return;
                        const h = document.createElement('h3'); h.textContent = title;
                        const p = document.createElement('p'); p.textContent = String(text || '');
                        if (preLine) p.style.whiteSpace = 'pre-line';
                        ex.appendChild(h); ex.appendChild(p);
                    }catch(e){}
                }
                try{
                    if (!isCorrect && showCorrectEnabled && (!teachingMode || textStudentFlow)) {
                        let ct = '';
                        if (questionType === 'multiple_choice') {
                            let correctIndex = 0;
                            if (typeof question.correct_answer === 'number') correctIndex = question.correct_answer;
                            else { const letters = ['A','B','C','D']; correctIndex = letters.indexOf(String(question.correct_answer).toUpperCase()); }
                            const opts = question.options || question.choices || [];
                            if (Array.isArray(opts) && opts[correctIndex] != null) ct = String(opts[correctIndex]);
                        } else if (questionType === 'true_false') {
                            let ca = question.correct_answer;
                            if (typeof ca !== 'boolean') {
                                const s = String(ca === undefined || ca === null ? '' : ca).trim().toLowerCase();
                                if (s === 'true' || s === 'đúng' || s === 'dung' || s === 'a' || s === '1' || s === 'yes' || s === 'y') ca = true;
                                else if (s === 'false' || s === 'sai' || s === 'b' || s === '0' || s === 'no' || s === 'n') ca = false;
                                else ca = !!ca;
                            }
                            ct = ca ? labels.true : labels.false;
                        } else if (questionType === 'fill_blank' || questionType === 'short_answer') {
                            const arr = getRuntimeTextAcceptedAnswers(question);
                            ct = arr.map(x => String(x)).filter(x => x.trim()).join(', ');
                        } else if (questionType === 'matching') {
                            const pairs = Array.isArray(question.pairs) ? question.pairs : [];
                            ct = pairs.map(p => `${p.left} → ${p.right}`).join('\\n');
                        }
                        if (ct) appendBlock(labels.correct_answer, ct, questionType === 'matching');
                    }
                }catch(e){}
                try{
                    if (question.explanation && showExplanationsEnabled && (!teachingMode || isCorrect || textStudentFlow)) {
                        appendBlock(labels.explain, String(question.explanation), false);
                    }
                }catch(e){}
                try{
                    if (ex && ex.innerText && ex.innerText.trim()) {
                        ex.classList.add('show');
                        try{ ex.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }catch(e){}
                    }
                }catch(e){}
                if (timerId) { clearInterval(timerId); timerId = null; }
                document.getElementById('time-progress').style.display = 'none';
                updateStats();
                gameState = 'answered';
                pendingAdvanceAction = (millionaireMode && !teachingMode && !isCorrect) ? 'end' : 'next';
                const isLast = (currentQuestionIndex >= gameData.questions.length-1);
                if (isLast && isCorrect){
                    document.getElementById('game-content').style.display = 'none';
                    try{ document.getElementById('game-stats').style.display = 'none'; }catch(e){}
                    document.getElementById('game-over').style.display = 'flex';
                    if (millionaireMode) {
                        document.getElementById('game-over-title').textContent = labels.win_title;
                    } else {
                        let msg;
                        if (score < 50) msg = labels.msg_low || 'Cố gắng lên nhé!';
                        else if (score <= 80) msg = labels.msg_mid || 'Gần được rồi!';
                        else msg = labels.msg_high || 'Xuất Sắc!';
                        document.getElementById('game-over-title').textContent = msg;
                    }
                    try{
                        const total = (gameData.questions||[]).length||0;
                        document.getElementById('game-over-desc').textContent = String(labels.result_summary || '').replace('{correct}', String(correctCount)).replace('{total}', String(total));
                        try { document.getElementById('result-score').textContent = String(millionaireMode ? getMillionaireResultAmount(false) : score); } catch(e) {}
                        try { document.getElementById('result-question-count').textContent = String(total); } catch(e) {}
                        try { document.getElementById('result-time').textContent = document.getElementById('time-left').textContent || '-'; } catch(e) {}
                    }catch(e){ document.getElementById('game-over-desc').textContent = labels.completed; }
                } else {
                    document.getElementById('next-btn').style.display = 'inline-block';
                }
            };
            if (delayMs > 0) setTimeout(finalizeSubmission, delayMs);
            else finalizeSubmission();
            updateLadder();
            renderAmountBars();
        }
        
        function nextQuestion() {
            if (pendingAdvanceAction === 'end') {
                pendingAdvanceAction = 'next';
                endGame(true);
                return;
            }
            pendingAdvanceAction = 'next';
            currentQuestionIndex++;
            if (timerId) { clearInterval(timerId); timerId = null; }
            showQuestion();
        }
        
        function updateStats() {
            document.getElementById('current-question').textContent = currentQuestionIndex + 1;
            document.getElementById('correct-count').textContent = correctCount;
            try { document.getElementById('score-display').textContent = score; } catch(e) {}
        }
        
        function endGame(stopped) {
            gameState = 'finished';
            document.getElementById('game-content').style.display = 'none';
            try{ document.getElementById('game-stats').style.display = 'none'; }catch(e){}
            document.getElementById('game-over').style.display = 'flex';
            try{
                const total = (gameData.questions||[]).length||0;
                document.getElementById('game-over-desc').textContent = String(labels.result_summary || '').replace('{correct}', String(correctCount)).replace('{total}', String(total));
                let msg;
                if (millionaireMode && stopped) msg = labels.stopped_title || labels.completed;
                else if (score < 50) msg = labels.msg_low || 'Cố gắng lên nhé!';
                else if (score <= 80) msg = labels.msg_mid || 'Gần được rồi!';
                else msg = labels.msg_high || 'Xuất Sắc!';
                try { document.getElementById('game-over-title').textContent = msg; } catch(e) {}
                try { document.getElementById('result-score').textContent = String(millionaireMode ? getMillionaireResultAmount(!!stopped) : score); } catch(e) {}
                try { document.getElementById('result-question-count').textContent = String(total); } catch(e) {}
                try { document.getElementById('result-time').textContent = document.getElementById('time-left').textContent || '-'; } catch(e) {}
            }catch(e){}
            
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            try { if (bgm) { bgm.pause(); } } catch(e){}
        }
        
        function restartGame() {
            document.getElementById('game-content').style.display = 'block';
            document.getElementById('game-over').style.display = 'none';
            try{ document.getElementById('game-stats').style.display = 'flex'; }catch(e){}
            startGame();
        }
        
        // Initialize game when page loads
        window.addEventListener('load', function(){ try{ document.getElementById('game-wrapper').style.display='none'; document.getElementById('intro-screen').style.display='flex'; }catch(e){} });
        window.addEventListener('load', function(){ try{ document.getElementById('start-btn').addEventListener('click', function(){ onStartClick(); }); }catch(e){} });
        window.addEventListener('resize', function(){ try{ if (gameState==='playing'){ showQuestion(); } }catch(e){} });
        window.addEventListener('load', function(){
            try{
                // Lifelines setup
                window.lifelinesUsed = { fifty:false, phone:false, audience:false };
                const fb = document.getElementById('fifty-btn');
                const pb = document.getElementById('phone-btn');
                const ab = document.getElementById('audience-btn');
                if (fb) fb.onclick = function(){ if (!millionaireMode || lifelinesUsed.fifty || gameState!=='playing') return; try{ fb.disabled=true; }catch(e){} lifelinesUsed.fifty=true; const q = gameData.questions[currentQuestionIndex]; if (q && q.type==='multiple_choice'){ let correctIndex=0; if (typeof q.correct_answer === 'number'){ correctIndex=q.correct_answer; } else { const L=['A','B','C','D']; correctIndex=L.indexOf(String(q.correct_answer).toUpperCase()); } const idxs=[0,1,2,3].filter(i=>i!==correctIndex); // remove 2 random wrongs
                        for (let k=0;k<2 && idxs.length>0;k++){ const r = Math.floor(Math.random()*idxs.length); const removeIndex = idxs.splice(r,1)[0]; const btn = document.querySelectorAll('.option-button')[removeIndex]; if (btn){ btn.classList.add('disabled'); btn.style.opacity='0.4'; try{ btn.parentElement.querySelector('.sprite').className = btn.parentElement.querySelector('.sprite').className.replace(/spr-opt-[a-z]+/,'spr-opt-grey'); }catch(e){} } }
                    }
                };
                if (pb) pb.onclick = function(){ if (!millionaireMode || lifelinesUsed.phone || gameState!=='playing') return; lifelinesUsed.phone=true; try{ pb.disabled=true; document.getElementById('icon-phone').className='sprite spr-help2-x'; }catch(e){} const q = gameData.questions[currentQuestionIndex]; let suggestionIndex = 0; if (q){ if (typeof q.correct_answer === 'number'){ suggestionIndex=q.correct_answer; } else { const L=['A','B','C','D']; suggestionIndex=L.indexOf(String(q.correct_answer).toUpperCase()); } const hint = (settings && settings.lifeline_phone_hint) ? String(settings.lifeline_phone_hint) : null; if (!hint){ if (Math.random()>0.75){ const pool=[0,1,2,3].filter(i=>i!==suggestionIndex); suggestionIndex = pool[Math.floor(Math.random()*pool.length)]; } }
                        const panel = document.getElementById('popup-panel'); const pop = document.getElementById('popup'); if (panel && pop){ panel.innerHTML = `<h3>${labels.lifeline_phone}</h3><p>${hint ? hint : (labels.lifeline_phone_says + ' <b>' + String.fromCharCode(65 + suggestionIndex) + '</b>')}</p>`; pop.style.display='flex'; setTimeout(()=>{ try{ pop.style.display='none'; }catch(e){} }, 2500); }
                    }
                };
                if (ab) ab.onclick = function(){ if (!millionaireMode || lifelinesUsed.audience || gameState!=='playing') return; lifelinesUsed.audience=true; try{ ab.disabled=true; document.getElementById('icon-audience').className='sprite spr-help3-x'; }catch(e){} const q = gameData.questions[currentQuestionIndex]; let correctIndex=0; if (q){ if (typeof q.correct_answer === 'number'){ correctIndex=q.correct_answer; } else { const L=['A','B','C','D']; correctIndex=L.indexOf(String(q.correct_answer).toUpperCase()); } let base=[20,20,20,20]; base[correctIndex] = 50 + Math.floor(Math.random()*30); let rest = 100 - base[correctIndex]; const idxs=[0,1,2,3].filter(i=>i!==correctIndex); let acc=0; idxs.forEach((i,ix)=>{ const v = ix<idxs.length-1 ? Math.floor(rest/(idxs.length-ix)) + Math.floor(Math.random()*10)-5 : (rest-acc); base[i] = Math.max(5, Math.min(40, v)); acc += base[i]; }); const hint = (settings && settings.lifeline_audience_hint) ? String(settings.lifeline_audience_hint) : null; const panel = document.getElementById('popup-panel'); const pop = document.getElementById('popup'); if (panel && pop){ panel.innerHTML = `<h3>${labels.lifeline_audience_result}</h3>${hint ? ('<p>' + hint + '</p>') : ''}<div class='bars'>${base.map((v,i)=>`<div class='bar' style='height:${v*1.4}px'><span>${String.fromCharCode(65+i)} ${v}%</span></div>`).join('')}</div>`; pop.style.display='flex'; setTimeout(()=>{ try{ pop.style.display='none'; }catch(e){} }, 3200); } }
                };
            }catch(e){}
            try{
                const restoreSaved = !!(settings && settings.restore_saved_state);
                if (!restoreSaved) return;
                const raw = localStorage.getItem('eduplay_quiz_state');
                if (!raw) return;
                const st = JSON.parse(raw);
                if (st && Array.isArray(st.questions)) {
                    gameData.questions = st.questions;
                    currentQuestionIndex = Math.min(Math.max(0, parseInt(st.q||0)), gameData.questions.length-1);
                    score = parseInt(st.s||0);
                    correctCount = parseInt(st.c||0);
                    showQuestion();
                    updateStats();
                }
            }catch(e){}
            try{
                // Expose alias functions for tests
                window.useFiftyFifty = function(){ try{ document.getElementById('fifty-btn').click(); }catch(e){} };
                window.usePhoneFriend = function(){ try{ document.getElementById('phone-btn').click(); }catch(e){} };
                window.useAudiencePoll = function(){ try{ document.getElementById('audience-btn').click(); }catch(e){} };
            }catch(e){}
        });
    </script>
</body>
</html>
        """
        
        template = Template(html_template)
        inline_data = {
            "project_name": project_data.get("name", "Game"),
            "questions": [],
            "game_config": project_data.get("game_config", {}),
            "game_type": project_data.get("game_type", "quiz_classic")
        }
        import json as _json
        try:
            gc = project_data.get('game_config', {}) or {}
        except Exception:
            gc = {}
        try:
            gc = dict(gc)
        except Exception:
            gc = {}
        try:
            sound_dir = self.assets_dir / 'sound'
            def _bundle_feedback_pool(entries):
                bundled = []
                for filename, text in entries:
                    fp = sound_dir / filename
                    if not fp.exists():
                        continue
                    try:
                        bundled.append({
                            'src': self._file_to_base64(str(fp)),
                            'text': text,
                        })
                    except Exception:
                        continue
                return bundled

            existing_pools = gc.get('feedback_sound_pools') if isinstance(gc.get('feedback_sound_pools'), dict) else {}
            correct_pool = list(existing_pools.get('correct') or [])
            wrong_pool = list(existing_pools.get('wrong') or [])
            if not correct_pool:
                correct_pool = _bundle_feedback_pool([
                    ('Well_done!.wav', 'Well done!'),
                    ('Correct!.wav', 'Correct!'),
                    ('Good_job!.wav', 'Good job!'),
                    ('Great!.wav', 'Great!'),
                ])
            if not wrong_pool:
                wrong_pool = _bundle_feedback_pool([
                    ('Keep_learning!.wav', 'Keep learning!'),
                    ('Keep_trying!.wav', 'Keep trying!'),
                    ('Keep_going!.wav', 'Keep going!'),
                    ('Good_try!.wav', 'Good try!'),
                ])
            if correct_pool or wrong_pool:
                gc['feedback_sound_pools'] = {
                    'correct': correct_pool,
                    'wrong': wrong_pool,
                }
                if correct_pool and not gc.get('correct_sound_base64'):
                    gc['correct_sound_base64'] = correct_pool[0].get('src')
                if wrong_pool and not gc.get('wrong_sound_base64'):
                    gc['wrong_sound_base64'] = wrong_pool[0].get('src')
        except Exception:
            pass
        # Normalize questions from project_data
        try:
            raw_qs = list(project_data.get('questions', []) or [])
            normalized = []
            for q in raw_qs:
                raw_type = q.get('type') or q.get('question_type') or q.get('q_type') or q.get('kind') or ''
                rt = str(raw_type).strip().lower().replace(' ', '_').replace('-', '_').replace('/', '_')
                if rt in ('multiple_choice', 'multiple', 'mcq', 'choice', 'quiz', 'trac_nghiem', 'trắc_nghiệm'):
                    q_type = 'multiple_choice'
                elif rt in ('true_false', 'truefalse', 'true__false', 'true-false', 'boolean', 'tf', 'dung_sai', 'đúng_sai'):
                    q_type = 'true_false'
                elif rt in ('fill_blank', 'fillblank', 'cloze', 'dien_cho_trong', 'điền_chỗ_trống'):
                    q_type = 'fill_blank'
                elif rt in ('short_answer', 'shortanswer', 'essay', 'tu_luan', 'tự_luận'):
                    q_type = 'short_answer'
                elif rt in ('matching', 'match', 'pairing', 'ghép_đôi', 'ghep_doi'):
                    q_type = 'matching'
                else:
                    if q.get('pairs') or q.get('match_pairs'):
                        q_type = 'matching'
                    elif isinstance(q.get('correct_answer'), bool):
                        q_type = 'true_false'
                    elif (q.get('correct_answers') is not None) and (q.get('options') is None):
                        q_type = 'fill_blank'
                    else:
                        q_type = 'multiple_choice'

                opts = q.get('options') or q.get('answers') or q.get('choices') or []
                try:
                    if q_type == 'multiple_choice' and not opts:
                        candidate_keys = [
                            ('option_a','option_b','option_c','option_d'),
                            ('answerA','answerB','answerC','answerD'),
                            ('A','B','C','D')
                        ]
                        for keys in candidate_keys:
                            arr = [q.get(keys[0]), q.get(keys[1]), q.get(keys[2]), q.get(keys[3])]
                            arr = [x for x in arr if x is not None]
                            if arr and len(arr) >= 2:
                                opts = arr
                                break
                except Exception:
                    pass
                nq = {
                    'question': q.get('question') or q.get('text') or '',
                    'options': opts,
                    'correct_answer': q.get('correct_answer') if q.get('correct_answer') is not None else (q.get('correctAnswer') if q.get('correctAnswer') is not None else None),
                    'explanation': q.get('explanation') or q.get('feedback') or ''
                }
                try:
                    ca = nq['correct_answer']
                    if isinstance(ca, str):
                        letters = ['A','B','C','D']
                        if ca.upper() in letters:
                            nq['correct_answer'] = letters.index(ca.upper())
                        else:
                            try:
                                nq['correct_answer'] = (nq['options'] or []).index(ca)
                            except Exception:
                                pass
                    elif ca is None and q.get('correctIndex') is not None:
                        nq['correct_answer'] = int(q.get('correctIndex'))
                    if (not nq['options']) and (q.get('incorrect_answers') or ca is not None):
                        try:
                            inc = list(q.get('incorrect_answers') or [])
                            base = []
                            if ca is not None:
                                base.append(ca if not isinstance(ca, int) else (opts[ca] if (opts and ca < len(opts)) else ''))
                            base.extend(inc)
                            import random as _r
                            _r.shuffle(base)
                            cand = [str(x) for x in base if str(x).strip()][:4]
                            if len(cand) >= 2:
                                nq['options'] = cand
                                if ca is not None:
                                    try:
                                        val = (ca if not isinstance(ca, int) else (opts[ca] if (opts and ca < len(opts)) else cand[0]))
                                        nq['correct_answer'] = cand.index(str(val))
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    if q_type == 'multiple_choice' and ((not nq['options']) or (isinstance(nq['options'], list) and len(nq['options']) < 2)):
                        nq['options'] = ['Tuỳ chọn 1', 'Tuỳ chọn 2', 'Tuỳ chọn 3', 'Tuỳ chọn 4']
                        if nq['correct_answer'] is None:
                            nq['correct_answer'] = 0
                except Exception:
                    pass
                try:
                    if q_type == 'fill_blank':
                        answers = q.get('correct_answers') or q.get('answers') or []
                        if not answers:
                            single_answer = q.get('correct_answer')
                            if single_answer is None:
                                single_answer = q.get('correctAnswer')
                            if single_answer is not None:
                                answers = [single_answer]
                        if not isinstance(answers, list):
                            answers = [answers]
                        answers = [str(a).strip() for a in answers if str(a).strip()]
                        if answers:
                            nq['correct_answers'] = answers
                    elif q_type == 'true_false':
                        ca = nq.get('correct_answer')
                        if isinstance(ca, bool):
                            nq['correct_answer'] = ca
                        elif isinstance(ca, (int, float)):
                            nq['correct_answer'] = bool(ca)
                        else:
                            s = str(ca if ca is not None else '').strip().lower()
                            if s in ('true', 'đúng', 'dung', 'a', '1', 'yes', 'y'):
                                nq['correct_answer'] = True
                            elif s in ('false', 'sai', 'b', '0', 'no', 'n'):
                                nq['correct_answer'] = False
                            else:
                                nq['correct_answer'] = False
                    elif q_type == 'matching':
                        pairs = q.get('pairs') or q.get('match_pairs') or []
                        if isinstance(pairs, list) and pairs:
                            nq['pairs'] = pairs
                    elif q_type == 'short_answer':
                        answers = []
                        if q.get('expected_answer'):
                            answers.append(q.get('expected_answer'))
                        ra = q.get('answers') or q.get('correct_answers') or []
                        if not ra:
                            single_answer = q.get('correct_answer')
                            if single_answer is None:
                                single_answer = q.get('correctAnswer')
                            if single_answer is not None:
                                ra = [single_answer]
                        if not isinstance(ra, list):
                            ra = [ra]
                        answers.extend(ra)
                        kws = q.get('keywords') or []
                        if isinstance(kws, str):
                            kws = [x.strip() for x in kws.split(',') if x.strip()]
                        answers.extend(kws)
                        norm_answers = []
                        seen = set()
                        for a in answers:
                            s = str(a).strip()
                            if not s:
                                continue
                            key = s.lower()
                            if key in seen:
                                continue
                            seen.add(key)
                            norm_answers.append(s)
                        if norm_answers:
                            nq['correct_answers'] = norm_answers
                except Exception:
                    pass
                nq['type'] = q_type
                normalized.append(nq)
            inline_data['questions'] = normalized
        except Exception:
            inline_data['questions'] = []
        # Attach per-question time limit if provided
        try:
            for idx, q in enumerate(raw_qs):
                if idx < len(inline_data['questions']):
                    tl = q.get('time_limit', q.get('question_time'))
                    if tl is not None:
                        try:
                            inline_data['questions'][idx]['time_limit'] = int(tl)
                        except Exception:
                            inline_data['questions'][idx]['time_limit'] = tl
        except Exception:
            pass
        # Fallback sample only if still empty
        if not inline_data['questions']:
            inline_data['questions'] = [
                {"question": "1 + 1 = ?", "options": ["1","2","3","4"], "correct_answer": 1, "explanation": "1 + 1 = 2", "type":"multiple_choice"},
                {"question": "Thủ đô Việt Nam là?", "options": ["TP.HCM","Hà Nội","Đà Nẵng","Huế"], "correct_answer": 1, "explanation": "Hà Nội", "type":"multiple_choice"}
            ]
        sprite_url = gc.get('millionaire_textures_base64') if is_millionaire else ''
        if is_millionaire:
            try:
                from pathlib import Path
                import base64
                def _data_uri(p: Path, mime: str) -> str:
                    try:
                        with open(p, 'rb') as _f:
                            b = _f.read()
                        return f"data:{mime};base64,{base64.b64encode(b).decode('ascii')}"
                    except Exception:
                        return ''
                assets_base = self.assets_dir / 'Who-wants-to-be-a-millionaire'
                if not sprite_url:
                    tex_assets = assets_base / 'pictures' / 'Textures.png'
                    sprite_url = _data_uri(tex_assets, 'image/png') or 'assets/Who-wants-to-be-a-millionaire/pictures/Textures.png'
            except Exception:
                pass
        # Always reorder question prefixes sequentially regardless of shuffle setting
        try:
            import random as _rnd
            if is_millionaire:
                qs = list(project_data.get('questions', []) or [])
                # Always reorder question prefixes sequentially
                if isinstance(qs, list):
                    if len(qs) > 15:
                        _rnd.shuffle(qs)
                        project_data['questions'] = qs[:15]
                    # Reorder question prefixes sequentially
                    for idx, q in enumerate(project_data['questions']):
                        raw_question = str(q.get('question', '') or '')
                        import re as _re
                        # Remove existing prefix pattern (câu 1, question1, etc.)
                        cleaned = _re.sub(r'^\s*(?:(?:câu|cau|question|q)\s*(?:hỏi|hoi)?(?:\s+số)?\s*\d+\s*[:.\-]?\s*)+', '', raw_question, flags=_re.IGNORECASE)
                        # Add new sequential prefix based on language
                        lang = project_data.get('language', 'vi')  # default to Vietnamese
                        if lang.lower().startswith('en'):
                            q['question'] = f"Question {idx + 1}: {cleaned}"
                        elif lang.lower().startswith('fr'):
                            q['question'] = f"Question {idx + 1}: {cleaned}"
                        elif lang.lower().startswith('de'):
                            q['question'] = f"Frage {idx + 1}: {cleaned}"
                        elif lang.lower().startswith('es'):
                            q['question'] = f"Pregunta {idx + 1}: {cleaned}"
                        else:
                            # Default to Vietnamese
                            q['question'] = f"Câu {idx + 1}: {cleaned}"
        except Exception:
            pass
        inline_data['game_config'] = gc
        # Prepare logo & circle icon
        logo_url = ''
        circle_url = ''
        try:
            if is_millionaire:
                assets_base = self.assets_dir / 'Who-wants-to-be-a-millionaire'
                icon_path = assets_base / 'pictures' / 'icon.png'
                if icon_path.exists():
                    with open(icon_path, 'rb') as _f:
                        b = _f.read()
                    import base64
                    logo_url = f"data:image/png;base64,{base64.b64encode(b).decode('ascii')}"
                circle_path = assets_base / 'pictures' / 'Circle.png'
                if circle_path.exists():
                    with open(circle_path, 'rb') as _f2:
                        cb = _f2.read()
                    import base64
                    circle_url = f"data:image/png;base64,{base64.b64encode(cb).decode('ascii')}"
        except Exception:
            logo_url = ''
            circle_url = ''
        # If millionaire and config requests exam layout, render alternate template
        try:
            use_exam = True if is_millionaire else False
            if use_exam:
                # Render dedicated exam template
                template_path = self.templates_dir / 'millionaire_exam.html'
                if template_path.exists():
                    content = template_path.read_text(encoding='utf-8')
                    from jinja2 import Template as _T
                    _tmpl = _T(content)
                    return _tmpl.render(project_name=project_data.get("name", "EduPlay Game"), language=lang, sprite_url=sprite_url or '', game_json=_json.dumps(inline_data, ensure_ascii=False))
        except Exception:
            pass
        return template.render(project_name=project_data.get("name", "EduPlay Game"), game_data_json=self._safe_json_dumps(inline_data), labels=labels, labels_json=labels_json, lang_attr=lang, bg_start=bg_start, bg_end=bg_end, accent=accent, is_millionaire=is_millionaire, sprite_url=sprite_url or '', font_times_uri='', font_minecraft_uri='', logo_url=logo_url, circle_url=circle_url)
    
    def _generate_fishing_game_html(self, project_data: Dict) -> str:
        """Generate HTML for fishing game using the template"""
        try:
            # Load the fishing game template
            template_path = (self.templates_dir.parent / 'templates_fish' / 'fishing_game.html')
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Prepare game configuration from provided data, with safe defaults
            game_config = dict(project_data.get('game_config', {}) or {})
            # Support nested fishing_settings from editor UI
            fishing_settings = dict(game_config.get('fishing_settings', {}) or {})
            # Map values with fallbacks
            fish_count = int(
                game_config.get('fish_count', fishing_settings.get('fish_count', 10)) or 10
            )
            base_speed = float(
                game_config.get('base_speed', fishing_settings.get('fish_speed', 2.0)) or 2.0
            )
            time_limit = int(game_config.get('time_limit', 60) or 60)
            question_time = int(game_config.get('question_time', game_config.get('question_time_per_question', 30)) or 30)
            # Respect general flags if provided
            show_explanations = bool(
                game_config.get('show_explanations', game_config.get('show_correct_answer', True))
            )
            randomize_questions = bool(game_config.get('randomize_questions', True))

            questions_in = list(project_data.get('questions', []) or [])
            normalized_questions: List[Dict] = []
            for q in questions_in:
                raw_type = q.get('type') or q.get('question_type') or q.get('q_type') or q.get('kind') or ''
                q_type = str(raw_type or '').strip().lower().replace('-', '_').replace(' ', '_').replace('/', '_')
                if q_type in ('multiple', 'mcq', 'choice', 'quiz', 'trac_nghiem', 'trắc_nghiệm'):
                    q_type = 'multiple_choice'
                elif q_type in ('truefalse', 'boolean', 'tf', 'dung_sai', 'đúng_sai'):
                    q_type = 'true_false'
                elif q_type in ('fillblank', 'cloze', 'dien_cho_trong', 'điền_chỗ_trống'):
                    q_type = 'fill_blank'
                elif q_type in ('shortanswer', 'essay', 'tu_luan', 'tự_luận'):
                    q_type = 'short_answer'
                elif q_type in ('match', 'pairing', 'ghep_doi', 'ghép_đôi'):
                    q_type = 'matching'
                elif not q_type:
                    if q.get('pairs') or q.get('match_pairs'):
                        q_type = 'matching'
                    elif isinstance(q.get('correct_answer'), bool) or isinstance(q.get('correctAnswer'), bool):
                        q_type = 'true_false'
                    else:
                        q_type = 'multiple_choice'
                options = q.get('options') or q.get('choices') or q.get('answers') or []
                if not options:
                    variants = [
                        ('option_a', 'option_b', 'option_c', 'option_d'),
                        ('answerA', 'answerB', 'answerC', 'answerD'),
                        ('A', 'B', 'C', 'D'),
                        ('option1', 'option2', 'option3', 'option4'),
                        ('pa', 'pb', 'pc', 'pd'),
                        ('ansA', 'ansB', 'ansC', 'ansD')
                    ]
                    for keys in variants:
                        arr = [q.get(keys[0]), q.get(keys[1]), q.get(keys[2]), q.get(keys[3])]
                        arr = [x for x in arr if x is not None]
                        if arr and len(arr) >= 2:
                            options = arr
                            break
                nq = {
                    'question': q.get('question') or q.get('text') or '',
                    'options': options or [],
                    'correctAnswer': q.get('correctAnswer', q.get('correct_answer')),
                    'explanation': q.get('explanation') or '',
                    'type': q_type,
                    'time_limit': q.get('time_limit', q.get('question_time'))
                }
                try:
                    image_base64 = q.get('image_base64') or ''
                    if (not image_base64) and isinstance(q.get('image'), str) and str(q.get('image')).startswith('data:'):
                        image_base64 = str(q.get('image'))
                    if image_base64:
                        nq['image_base64'] = image_base64
                except Exception:
                    pass
                try:
                    if (not nq['options']) or (isinstance(nq['options'], list) and len(nq['options']) < 2):
                        nq['options'] = ['Tuỳ chọn 1','Tuỳ chọn 2','Tuỳ chọn 3','Tuỳ chọn 4']
                        if nq['correctAnswer'] is None and q_type == 'multiple_choice':
                            nq['correctAnswer'] = 0
                except Exception:
                    pass
                try:
                    if q_type == 'true_false':
                        ca = q.get('correctAnswer', q.get('correct_answer'))
                        if isinstance(ca, bool):
                            nq['correctAnswer'] = ca
                        elif isinstance(ca, (int, float)):
                            nq['correctAnswer'] = bool(ca)
                        else:
                            s = str(ca or '').strip().lower()
                            nq['correctAnswer'] = s in ('true', 'đúng', 'dung', '1', 'yes', 'y')
                        nq['correct_answer'] = nq['correctAnswer']
                        nq['options'] = ['Đúng', 'Sai']
                    else:
                        ca = nq['correctAnswer']
                        if isinstance(ca, str):
                            letters = ['A','B','C','D']
                            if ca in letters:
                                nq['correctAnswer'] = letters.index(ca)
                            else:
                                try:
                                    nq['correctAnswer'] = (nq['options'] or []).index(ca)
                                except Exception:
                                    pass
                except Exception:
                    pass
                if q_type != 'true_false' and not isinstance(nq.get('correctAnswer'), (int, float)):
                    if nq.get('options'):
                        nq['correctAnswer'] = 0
                try:
                    if q_type == 'matching':
                        mp = q.get('match_pairs') or []
                        if (not mp) and isinstance(q.get('options'), list):
                            mp = [p for p in q.get('options') if isinstance(p, dict) and ('left' in p and 'right' in p)]
                        nq['match_pairs'] = mp
                    elif q_type == 'fill_blank' or q_type == 'short_answer':
                        answers = []
                        if q.get('expected_answer'):
                            answers.append(q.get('expected_answer'))
                        ra = q.get('correct_answers') or q.get('answers') or []
                        if not isinstance(ra, list):
                            ra = [ra]
                        answers.extend(ra)
                        kws = q.get('keywords') or []
                        if isinstance(kws, str):
                            kws = [x.strip() for x in kws.split(',') if x.strip()]
                        answers.extend(kws)
                        norm_answers = []
                        seen = set()
                        for a in answers:
                            s = str(a).strip()
                            if not s:
                                continue
                            key = s.lower()
                            if key in seen:
                                continue
                            seen.add(key)
                            norm_answers.append(s)
                        if norm_answers:
                            nq['correctAnswer'] = norm_answers
                except Exception:
                    pass
                normalized_questions.append(nq)

            # Fallback sample questions when none provided
            if not normalized_questions:
                normalized_questions = [
                    {
                        'question': 'What is 2 + 2?',
                        'options': ['3','4','5'],
                        'correctAnswer': 1,
                        'explanation': '2 + 2 = 4'
                    }
                ]

            # Always reorder question prefixes sequentially regardless of shuffle setting
            if isinstance(normalized_questions, list):
                # Randomize and limit
                if randomize_questions:
                    import random as _rnd
                    _rnd.shuffle(normalized_questions)
                normalized_questions = normalized_questions[:fish_count]
                
                # Reorder question prefixes sequentially
                try:
                    for idx, q in enumerate(normalized_questions):
                        raw_question = str(q.get('question', '') or '')
                        import re as _re
                        # Remove existing prefix pattern (câu 1, question1, etc.)
                        cleaned = _re.sub(r'^\s*(?:(?:câu|cau|question|q)\s*(?:hỏi|hoi)?(?:\s+số)?\s*\d+\s*[:.\-]?\s*)+', '', raw_question, flags=_re.IGNORECASE)
                        # Add new sequential prefix
                        q['question'] = f"Câu {idx + 1}: {cleaned}"
                except Exception:
                    pass

            # Use provided fish objects if any; otherwise provide defaults, and encode to base64
            fish_objects_in = list(game_config.get('fish_objects', []) or [])
            if not fish_objects_in:
                fish_types = ['blue', 'green', 'pink', 'orange']
                fish_objects_in = [
                    {
                        'sprite': f'assets/kenney_platformer-kit/PNG/Default/fish_{t}.png',
                        'wrong_sprite': f'assets/kenney_platformer-kit/PNG/Default/fish_{t}_skeleton.png',
                        'sound': 'assets/sound/click.wav'
                    } for t in fish_types
                ]
            # Convert fish sprites to data URIs for preview to avoid file GET errors
            try:
                from pathlib import Path as _P
                import base64, mimetypes
                def _to_uri(path: _P, fallback_mime='image/png'):
                    try:
                        if not path.exists():
                            return ''
                        mime, _ = mimetypes.guess_type(path.name)
                        data = base64.b64encode(path.read_bytes()).decode('ascii')
                        return f'data:{(mime or fallback_mime)};base64,{data}'
                    except Exception:
                        return ''
                base_assets = self.assets_dir / 'kenney_platformer-kit' / 'PNG' / 'Default'
                encoded_fish = []
                for fo in fish_objects_in:
                    s = fo.get('sprite_base64') or fo.get('sprite') or ''
                    w = fo.get('wrong_sprite_base64') or fo.get('wrong_sprite') or ''
                    s_path = _P(s)
                    if not s_path.is_absolute():
                        s_path = base_assets / _P(s).name
                    w_path = _P(w)
                    if not w_path.is_absolute():
                        w_path = base_assets / _P(w).name
                    encoded_fish.append({
                        'sprite_base64': _to_uri(s_path) or '',
                        'wrong_sprite_base64': _to_uri(w_path) or (_to_uri(s_path) or '')
                    })
                fish_objects_in = encoded_fish
            except Exception:
                pass

            # Prepare template context with game type for tests
            context = {
                'project_name': project_data.get('name', 'Fishing Game'),
                'questions': normalized_questions,
                'game_config': {
                    'fish_count': fish_count,
                    'base_speed': base_speed,
                    'time_limit': time_limit,
                    'question_time': question_time,
                    'export_mode': str(game_config.get('export_mode', 'student') or 'student'),
                    'show_explanations': show_explanations,
                    'randomize_questions': randomize_questions,
                    'fish_objects': fish_objects_in,
                    'background_image': game_config.get('background_image', 'background_seaweed_a.png'),
                    'background_music': game_config.get('background_music', 'assets/sound/background.mp3'),
                    'correct_sound': game_config.get('correct_sound', 'assets/sound/correct.wav'),
                    'wrong_sound': game_config.get('wrong_sound', 'assets/sound/wrong.wav'),
                    'click_sound': game_config.get('click_sound', 'assets/sound/click.wav'),
                    'bgm_base64': game_config.get('bgm_base64'),
                    'click_sound_base64': game_config.get('click_sound_base64'),
                    'correct_sound_base64': game_config.get('correct_sound_base64'),
                    'wrong_sound_base64': game_config.get('wrong_sound_base64'),
                    'background_image_base64': game_config.get('background_image_base64'),
                    'backgrounds_base64': game_config.get('backgrounds_base64'),
                    'seaweed_assets_base64': game_config.get('seaweed_assets_base64'),
                    'decor_rocks_base64': game_config.get('decor_rocks_base64'),
                    'terrain_tiles_base64': game_config.get('terrain_tiles_base64'),
                    'tiny_fish_base64': game_config.get('tiny_fish_base64'),
                    'background_terrain_base64': game_config.get('background_terrain_base64'),
                    'background_terrain_top_base64': game_config.get('background_terrain_top_base64'),
                    'rock_assets_base64': game_config.get('rock_assets_base64'),
                    'background_soft_base64': game_config.get('background_soft_base64'),
                    'hud_digits_base64': game_config.get('hud_digits_base64'),
                    'scene_asset_map_base64': game_config.get('scene_asset_map_base64'),
                    # Optional cute effects toggle
                    'cute_effects': bool(game_config.get('cute_effects', False)),
                    # Pass through fish size selection to template
                    'fish_size': fishing_settings.get('fish_size', 'Vừa')
                },
                'language': project_data.get('language', 'vi'),
                'game_type': 'fishing'
            }
            # Populate base64 arrays if missing
            try:
                import base64, mimetypes
                from pathlib import Path as _P
                def _enc(name: str):
                    p = self.assets_dir / 'kenney_platformer-kit' / 'PNG' / 'Default' / name
                    if p.exists():
                        mime, _ = mimetypes.guess_type(p.name)
                        return f"data:{(mime or 'image/png')};base64," + base64.b64encode(p.read_bytes()).decode('ascii')
                    return ''
                gcx = context['game_config']
                if not (gcx.get('seaweed_assets_base64') or []):
                    assets = ['seaweed_grass_a.png','seaweed_grass_b.png','seaweed_green_a.png','seaweed_green_b.png','seaweed_green_c.png','seaweed_green_d.png','seaweed_orange_a.png','seaweed_orange_b.png','seaweed_pink_a.png','seaweed_pink_b.png','seaweed_pink_c.png','seaweed_pink_d.png']
                    gcx['seaweed_assets_base64'] = [a for a in [ _enc(n) for n in assets ] if a]
                if not (gcx.get('decor_rocks_base64') or []):
                    rocks = ['background_rock_a.png','background_rock_b.png']
                    gcx['decor_rocks_base64'] = [a for a in [ _enc(n) for n in rocks ] if a]
                if not (gcx.get('terrain_tiles_base64') or []):
                    tiles = ['terrain_sand_top_a.png','terrain_sand_top_b.png','terrain_sand_top_c.png','terrain_sand_top_d.png','terrain_sand_a.png','terrain_sand_b.png','terrain_sand_c.png','terrain_sand_d.png']
                    gcx['terrain_tiles_base64'] = [a for a in [ _enc(n) for n in tiles ] if a]
                if not (gcx.get('tiny_fish_base64') or []):
                    fish_types = ['blue','green','pink','orange']
                    gcx['tiny_fish_base64'] = [ _enc(f"fish_{t}.png") for t in fish_types if _enc(f"fish_{t}.png") ]
                if not gcx.get('background_image_base64'):
                    enc_bg = _enc('background_seaweed_a.png')
                    if enc_bg:
                        gcx['background_image_base64'] = enc_bg
                # Additional decoration sets
                if not (gcx.get('rock_assets_base64') or []):
                    r2 = ['rock_a.png','rock_b.png']
                    gcx['rock_assets_base64'] = [a for a in [ _enc(n) for n in r2 ] if a]
                if not (gcx.get('background_soft_base64') or []):
                    softs = ['background_rock_a.png','background_rock_b.png','background_seaweed_a.png','background_seaweed_b.png','background_seaweed_c.png','background_seaweed_d.png','background_seaweed_e.png','background_seaweed_f.png','background_seaweed_g.png','background_seaweed_h.png']
                    gcx['background_soft_base64'] = [a for a in [ _enc(n) for n in softs ] if a]
                if not gcx.get('scene_asset_map_base64'):
                    scene_asset_files = [
                        'background_seaweed_a.png','background_seaweed_b.png','background_seaweed_c.png','background_seaweed_d.png',
                        'background_seaweed_e.png','background_seaweed_f.png','background_seaweed_g.png','background_seaweed_h.png',
                        'background_rock_a.png','background_rock_b.png','background_terrain.png','background_terrain_top.png',
                        'fish_blue.png','fish_green.png','fish_pink.png','fish_orange.png','fish_red.png',
                        'fish_grey.png','fish_grey_long_a.png','fish_grey_long_b.png',
                        'fish_blue_skeleton.png','fish_green_skeleton.png','fish_pink_skeleton.png','fish_orange_skeleton.png','fish_red_skeleton.png',
                        'seaweed_grass_a.png','seaweed_grass_b.png',
                        'seaweed_green_a.png','seaweed_green_b.png','seaweed_green_c.png','seaweed_green_d.png',
                        'seaweed_orange_a.png','seaweed_orange_b.png',
                        'seaweed_pink_a.png','seaweed_pink_b.png','seaweed_pink_c.png','seaweed_pink_d.png',
                        'rock_a.png','rock_b.png',
                        'terrain_sand_top_a.png','terrain_sand_top_b.png','terrain_sand_top_c.png','terrain_sand_top_d.png',
                        'terrain_sand_top_e.png','terrain_sand_top_f.png','terrain_sand_top_g.png','terrain_sand_top_h.png',
                        'terrain_sand_a.png','terrain_sand_b.png','terrain_sand_c.png','terrain_sand_d.png',
                        'terrain_dirt_a.png','terrain_dirt_b.png','terrain_dirt_c.png','terrain_dirt_d.png',
                        'terrain_dirt_top_a.png','terrain_dirt_top_b.png','terrain_dirt_top_c.png','terrain_dirt_top_d.png',
                        'terrain_dirt_top_e.png','terrain_dirt_top_f.png','terrain_dirt_top_g.png','terrain_dirt_top_h.png'
                    ]
                    gcx['scene_asset_map_base64'] = {name: data for name, data in ((n, _enc(n)) for n in scene_asset_files) if data}
                if not gcx.get('background_terrain_base64'):
                    gcx['background_terrain_base64'] = _enc('background_terrain.png')
                if not gcx.get('background_terrain_top_base64'):
                    gcx['background_terrain_top_base64'] = _enc('background_terrain_top.png')
                if not gcx.get('hud_digits_base64'):
                    digits = {str(i): _enc(f"hud_number_{i}.png") for i in range(0,10)}
                    digits.update({'percent': _enc('hud_percent.png'), 'plus': _enc('hud_plus.png'), 'colon': _enc('hud_colon.png'), 'dot': _enc('hud_dot.png')})
                    gcx['hud_digits_base64'] = {k:v for k,v in digits.items() if v}
            except Exception:
                pass
            try:
                lang = context['language'] or 'en'
            except Exception:
                lang = 'en'
            try:
                context.update({
                    'i18n_score': I18n.t('quiz.score', lang),
                    'i18n_time': I18n.t('editor.time', lang),
                    'i18n_completed': I18n.t('quiz.completed', lang),
                    'i18n_play_again': I18n.t('quiz.play_again', lang),
                    'i18n_start_title': I18n.t('fishing.start_title', lang),
                    'i18n_start_button': I18n.t('fishing.start_button', lang),
                    'i18n_start_rules': I18n.t('fishing.start_rules', lang),
                    'i18n_audio_not_supported': I18n.t('fishing.audio_not_supported', lang),
                    'i18n_msg_low': I18n.t('quiz.msg_low', lang) or 'Cố gắng lên nhé!',
                    'i18n_msg_mid': I18n.t('quiz.msg_mid', lang) or 'Gần được rồi!',
                    'i18n_msg_high': I18n.t('quiz.msg_high', lang) or 'Xuất Sắc!',
                })
            except Exception:
                context.update({
                    'i18n_score': 'Score',
                    'i18n_time': 'Time',
                    'i18n_completed': 'Completed!',
                    'i18n_play_again': 'Play Again'
                })
            try:
                if not context.get('i18n_start_title'):
                    context['i18n_start_title'] = 'Start Game'
                if not context.get('i18n_start_button'):
                    context['i18n_start_button'] = 'Start'
            except Exception:
                pass
            
            # Add game data as JSON in a script tag
            game_data_script = f'<script id="game-data" type="application/json">{self._safe_json_dumps(context)}</script>'
            
            # Render the template with the context
            from jinja2 import Template
            template = Template(template_content)
            html_content = template.render(**context)
            # Hide global timer (top-left); only per-question timer inside panel
            try:
                html_content = html_content.replace('<div id="timer"', '<div id="timer" style="display:none"')
            except Exception:
                pass
            
            # Insert the game data script before the closing body tag
            html_content = html_content.replace('</body>', f'{game_data_script}\n</body>')
            
            return html_content
            
        except Exception as e:
            import traceback
            error_message = f"Error generating fishing game HTML: {str(e)}\n{traceback.format_exc()}"
            print(error_message)
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>Error</title></head>
            <body>
                <h1>Error Generating Game</h1>
                <p>An error occurred while generating the fishing game.</p>
                <pre>{error_message}</pre>
            </body>
            </html>
            """
    
    def _generate_pygame_script(self, project_data: Dict) -> str:
        """Generate Python/PyGame script"""
        game_type = project_data.get("game_type", "quiz_classic")
        if str(game_type).lower() == "fishing":
            pygame_template = '''
import pygame
import json
import random
import sys
import os
import math
import io
import base64
import tempfile

pygame.init()

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

BACKGROUND_COLOR = (11, 16, 35)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (87, 193, 255)
SUCCESS_COLOR = (18, 183, 106)
WARNING_COLOR = (244, 67, 56)

def _decode_data_url(s):
    try:
        if not s: return None, ''
        s = str(s)
        comma = s.find(',')
        header = s[:comma] if comma != -1 else ''
        data_b64 = s[comma+1:] if comma != -1 else s
        data = base64.b64decode(data_b64)
        mime = ''
        if header.startswith('data:'):
            try:
                mime = header.split(':',1)[1].split(';',1)[0]
                if '/' in mime:
                    mime = mime.split('/',1)[1]
            except:
                mime = ''
        return data, mime
    except:
        return None, ''

def _write_temp_from_data_url(s, prefix='asset'):
    data, ext = _decode_data_url(s)
    if not data: return None
    suffix = ('.' + ext) if ext else '.bin'
    f = tempfile.NamedTemporaryFile(delete=False, prefix=prefix+'_', suffix=suffix)
    try:
        f.write(data)
        f.flush()
    finally:
        f.close()
    return f.name

def _load_image_maybe_base64(src):
    try:
        if src and str(src).startswith('data:'):
            data,_ = _decode_data_url(src)
            if data:
                return pygame.image.load(io.BytesIO(data)).convert_alpha()
        return pygame.image.load(src).convert_alpha()
    except:
        return pygame.Surface((64,32), pygame.SRCALPHA)

 class Fish:
    def __init__(self, img, x, y, speed, direction, tag=None, wrong_img=None, sound=None):
        self.image = _load_image_maybe_base64(img)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.base_y = y
        self.speed = speed
        self.direction = direction
        self.tag = tag or "fish"
        self.wrong_image = _load_image_maybe_base64(wrong_img) if wrong_img else None
        self.sound_path = sound
        self.caught = False
        self.correct = True
        self.t = random.random()*6.28
    def update(self, diff=1.0):
        dx = (self.speed * max(0.5, diff)) * (1 if self.direction == 'R' else -1)
        self.rect.x += dx
        if self.rect.right < -140:
            self.rect.left = SCREEN_WIDTH + 140
        elif self.rect.left > SCREEN_WIDTH + 140:
            self.rect.right = -140
        self.t += 0.06
        amp = min(22, 12*max(0.8, diff))
        self.rect.y = max(120, min(SCREEN_HEIGHT - 160, int(self.base_y + math.sin(self.t)*amp)))
    def draw(self, screen):
        img = self.image if self.correct else (self.wrong_image or self.image)
        screen.blit(img, self.rect)

class Hook:
    def __init__(self):
        self.x = 0
        self.length = 0
        self.active = False
        self.speed = 18
        self.hit_pos = None
    def start(self, x):
        self.x = x
        self.length = 0
        self.active = True
        self.hit_pos = None
    def update(self):
        if not self.active:
            return
        self.length += self.speed
        if 70 + self.length >= SCREEN_HEIGHT - 10:
            self.active = False
    def draw(self, screen):
        if self.active:
            pygame.draw.rect(screen, ACCENT_COLOR, pygame.Rect(self.x-2, 70, 4, self.length))

 class EduPlayFishing:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("{{ project_name }} - Fishing")
        self.clock = pygame.time.Clock()
        self.running = True
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        self.fishes = []
        self.score = 0
        self.correct_count = 0
        self.streak = 0
        self.multiplier = 1
        self.answered_count = 0
        self.game_state = 'playing'
        self.load_game_data()
        self.settings = self.game_data.get('game_config', {})
        try:
            pygame.mixer.init()
        except:
            pass
        self.snd_correct = None
        self.snd_wrong = None
        bgm_path = self.settings.get('background_music')
        bgm_b64 = self.settings.get('background_music_base64')
        if bgm_path:
            try:
                pygame.mixer.music.load(bgm_path)
                pygame.mixer.music.set_volume(0.3)
                pygame.mixer.music.play(-1)
            except:
                pass
        elif bgm_b64:
            try:
                tmp = _write_temp_from_data_url(bgm_b64, 'bgm')
                if tmp:
                    pygame.mixer.music.load(tmp)
                    pygame.mixer.music.set_volume(0.3)
                    pygame.mixer.music.play(-1)
            except:
                pass
        try:
            cs = self.settings.get('correct_sound')
            ws = self.settings.get('wrong_sound')
            csb64 = self.settings.get('correct_sound_base64')
            wsb64 = self.settings.get('wrong_sound_base64')
            if cs:
                self.snd_correct = pygame.mixer.Sound(cs)
            elif csb64:
                try:
                    data,_ = _decode_data_url(csb64)
                    if data:
                        self.snd_correct = pygame.mixer.Sound(io.BytesIO(data))
                except:
                    pass
            if ws:
                self.snd_wrong = pygame.mixer.Sound(ws)
            elif wsb64:
                try:
                    data,_ = _decode_data_url(wsb64)
                    if data:
                        self.snd_wrong = pygame.mixer.Sound(io.BytesIO(data))
                except:
                    pass
        except:
            pass
        self.spawn_fishes()
        self.hook = Hook()
        self.effects = []
    def get_difficulty(self):
        acc = 0.0
        try:
            acc = float(self.correct_count) / float(max(1, self.answered_count))
        except:
            acc = 0.0
        return 1.0 + min(0.8, self.correct_count*0.06 + acc*0.24)
    def load_game_data(self):
        try:
            with open('game_data.json', 'r', encoding='utf-8') as f:
                self.game_data = json.load(f)
        except FileNotFoundError:
            self.game_data = {"project_name": "Fishing", "questions": [], "game_type": "fishing", "game_config": {}}
    def spawn_fishes(self):
        cfg = self.settings or {}
        objs = cfg.get('fish_objects') or []
        speed = int(cfg.get('fish_speed', 5))
        self.fishes.clear()
        for i, fo in enumerate(objs[:8]):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(160, SCREEN_HEIGHT-180)
            direction = random.choice(['L','R'])
            tag = fo.get('tag') or 'fish'
            wrong_img = fo.get('wrong_sprite')
            sound = fo.get('sound')
            f = Fish(fo.get('sprite'), x, y, speed + random.randint(-2,2), direction, tag, wrong_img, sound)
            self.fishes.append(f)
        for i in range(len(self.fishes)):
            if i % 3 == 0:
                self.fishes[i].correct = True
            else:
                self.fishes[i].correct = False
    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit(); sys.exit()
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and self.game_state == 'playing':
                self.hook.start(event.pos[0])
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    def update(self):
        if self.game_state == 'playing':
            for f in self.fishes:
                if not f.caught:
                    f.update(self.get_difficulty())
            self.hook.update()
            if self.hook.active:
                for f in self.fishes:
                    if not f.caught:
                        hx = self.hook.x
                        hy = 70 + self.hook.length
                        if hx>=f.rect.left and hx<=f.rect.right and hy>=f.rect.top and hy<=f.rect.bottom:
                            f.caught = True
                            ok = f.correct
                            if ok:
                                self.streak += 1
                                self.multiplier = min(5, 1 + self.streak//2)
                                self.score += int(self.settings.get('score_per_fish', 10)) * self.multiplier
                                self.correct_count += 1
                                try:
                                    if self.snd_correct: self.snd_correct.play()
                                except:
                                    pass
                            else:
                                self.streak = 0
                                self.multiplier = 1
                                try:
                                    if self.snd_wrong: self.snd_wrong.play()
                                except:
                                    pass
                            self.answered_count += 1
                            self.effects.append({'x': hx, 'y': hy, 'r': 4, 'life': 18, 'color': SUCCESS_COLOR if ok else WARNING_COLOR})
                            self.hook.active = False
        if self.correct_count >= max(1, len(self.fishes)//3):
            self.game_state = 'finished'
    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)
        lake_rect = pygame.Rect(0, 70, SCREEN_WIDTH, SCREEN_HEIGHT-70)
        pygame.draw.rect(self.screen, (16,32,64), lake_rect)
        for f in self.fishes:
            if not f.caught:
                f.draw(self.screen)
        self.hook.draw(self.screen)
        for e in list(self.effects):
            pygame.draw.circle(self.screen, e['color'], (int(e['x']), int(e['y'])), max(1,int(e['r'])))
            e['r'] += 2
            e['life'] -= 1
            if e['life'] <= 0:
                try:
                    self.effects.remove(e)
                except:
                    pass
        hud = self.font_small.render(f"Điểm: {self.score}", True, TEXT_COLOR)
        combo = self.font_small.render(f"Combo x{self.multiplier} • Streak {self.streak}", True, ACCENT_COLOR)
        self.screen.blit(hud, (16, 16))
        self.screen.blit(combo, (16, 42))
        if self.game_state == 'finished':
            t = self.font_large.render("Hoàn thành!", True, ACCENT_COLOR)
            self.screen.blit(t, (SCREEN_WIDTH//2-120, 180))
            s = self.font_medium.render(f"Điểm: {self.score}", True, SUCCESS_COLOR)
            self.screen.blit(s, (SCREEN_WIDTH//2-80, 240))

if __name__ == "__main__":
    game = EduPlayFishing()
    game.run()
            '''
            template = Template(pygame_template)
            return template.render(project_name=project_data.get("name", "EduPlay Fishing"))
        pygame_template = '''
import pygame
import json
import random
import sys
import os
import io
import base64

# Initialize Pygame
pygame.init()

# Game constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors (matching the dark theme)
BACKGROUND_COLOR = (30, 30, 36)
PANEL_COLOR = (45, 47, 58)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (127, 86, 217)
SUCCESS_COLOR = (18, 183, 106)
WARNING_COLOR = (247, 144, 9)

class EduPlayGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("{{ project_name }}")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load game data
        self.load_game_data()
        
        self.settings = self.game_data.get("game_config", {})
        # Always reorder question prefixes sequentially regardless of shuffle setting
        if isinstance(self.game_data.get("questions"), list):
            if self.settings.get("randomize_questions"):
                random.shuffle(self.game_data["questions"])
            # Reorder question prefixes sequentially
            for idx, q in enumerate(self.game_data["questions"]):
                raw_question = str(q.get('question', '') or '')
                import re as _re
                cleaned = _re.sub(r'^\s*(?:(?:câu|cau|question|q)\s*(?:hỏi|hoi)?(?:\s+số)?\s*\d+\s*[:.\-]?\s*)+', '', raw_question, flags=_re.IGNORECASE)
                q['question'] = f"Câu {idx + 1}: {cleaned}"
        
        try:
            auto_points = bool(self.settings.get("auto_points_enabled", False))
        except Exception:
            auto_points = False
        if auto_points:
            try:
                total_questions = len(self.game_data.get("questions") or [])
            except Exception:
                total_questions = 0
            if total_questions > 0:
                try:
                    total_points = int(self.settings.get("total_points", 100))
                    if total_points <= 0:
                        total_points = 100
                    if total_points > 100:
                        total_points = 100
                    per_q = int(round(float(total_points) / float(total_questions)))
                except Exception:
                    per_q = int((100 // total_questions) if total_questions > 0 else 0)
                if per_q <= 0:
                    per_q = 1
                self.points_per_question = per_q
            else:
                self.points_per_question = 0
        else:
            self.points_per_question = int(self.settings.get("points_per_question", 10))
        self.time_limit_enabled = bool(self.settings.get("time_limit_enabled", True))
        self.default_question_time = int(self.settings.get("quiz_time_per_question", self.settings.get("question_time", 30)))
        self.time_left = None
        self.time_total = None
        try:
            pygame.mixer.init()
        except:
            pass
        self.snd_click = None
        self.snd_correct = None
        self.snd_wrong = None
        bgm_path = self.settings.get("background_music")
        bgm_b64 = self.settings.get("background_music_base64")
        for k in ["correct_sound", "wrong_sound", "click_sound"]:
            p = self.settings.get(k)
            if p:
                pp = str(p).replace("\\", "/")
                if pp.startswith("assets/"):
                    p_local = pp
                else:
                    p_local = os.path.join("assets", "media", os.path.basename(pp))
                try:
                    snd = pygame.mixer.Sound(p_local)
                    if k == "click_sound":
                        self.snd_click = snd
                    elif k == "correct_sound":
                        self.snd_correct = snd
                    elif k == "wrong_sound":
                        self.snd_wrong = snd
                except:
                    pass
        # Base64 sounds
        for k in ["click_sound_base64", "correct_sound_base64", "wrong_sound_base64"]:
            s = self.settings.get(k)
            if s:
                try:
                    comma = s.find(','); b64 = s[comma+1:] if comma!=-1 else s
                    data = base64.b64decode(b64)
                    snd = pygame.mixer.Sound(io.BytesIO(data))
                    if k.startswith('click'):
                        self.snd_click = snd
                    elif k.startswith('correct'):
                        self.snd_correct = snd
                    elif k.startswith('wrong'):
                        self.snd_wrong = snd
                except:
                    pass
        if bgm_path:
            pp = str(bgm_path).replace("\\", "/")
            if pp.startswith("assets/"):
                bgm_local = pp
            else:
                bgm_local = os.path.join("assets", "media", os.path.basename(pp))
            try:
                pygame.mixer.music.load(bgm_local)
                pygame.mixer.music.set_volume(0.3)
                pygame.mixer.music.play(-1)
            except:
                pass
        elif bgm_b64:
            try:
                comma = bgm_b64.find(','); b64 = bgm_b64[comma+1:] if comma!=-1 else bgm_b64
                data = base64.b64decode(b64)
                import tempfile
                f = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                try:
                    f.write(data); f.flush()
                finally:
                    f.close()
                pygame.mixer.music.load(f.name)
                pygame.mixer.music.set_volume(0.3)
                pygame.mixer.music.play(-1)
            except:
                pass
        
        # Game state
        self.current_question = 0
        self.score = 0
        self.correct_count = 0
        self.game_state = "playing"
        self.selected_answer = None
        
        # Fonts
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        
        # UI elements
        self.buttons = []
        
    def load_game_data(self):
        """Load game data from JSON file"""
        try:
            with open('game_data.json', 'r', encoding='utf-8') as f:
                self.game_data = json.load(f)
        except FileNotFoundError:
            print("Error: game_data.json not found!")
            self.game_data = {
                "project_name": "EduPlay Game",
                "questions": [],
                "game_type": "quiz_classic"
            }
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()
    
    def handle_events(self):
        """Handle Pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_mouse_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                else:
                    if self.game_state == "playing" and self.current_question < len(self.game_data.get("questions", [])):
                        q = self.game_data["questions"][self.current_question]
                        if q.get("type") == "fill_blank":
                            if not hasattr(self, "input_text"):
                                self.input_text = ""
                            if event.key == pygame.K_BACKSPACE:
                                self.input_text = self.input_text[:-1]
                            elif event.key == pygame.K_RETURN:
                                self.selected_answer = self.input_text
                            else:
                                try:
                                    ch = event.unicode
                                    if ch and len(ch) == 1:
                                        self.input_text += ch
                                except:
                                    pass
                            self.selected_answer = self.input_text
    
    def handle_mouse_click(self, pos):
        """Handle mouse click events"""
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                if button["action"] == "select_answer":
                    self.selected_answer = button["answer"]
                    try:
                        if self.snd_click:
                            self.snd_click.play()
                    except:
                        pass
                elif button["action"] == "select_left":
                    try:
                        self.match_left = button.get("index")
                    except:
                        self.match_left = None
                elif button["action"] == "select_right":
                    try:
                        self.match_right = button.get("index")
                    except:
                        self.match_right = None
                    if self.match_left is not None and self.match_right is not None:
                        self.selected_answer = {"left": self.match_left, "right": self.match_right}
                elif button["action"] == "submit_answer":
                    self.submit_answer()
                elif button["action"] == "next_question":
                    self.next_question()
    
    def update(self):
        """Update game state"""
        self.buttons = []
        
        if self.game_state == "playing":
            if self.time_limit_enabled:
                if self.time_left is None:
                    q = self.game_data["questions"][self.current_question] if self.current_question < len(self.game_data["questions"]) else None
                    if q is not None:
                        t = q.get("time_limit", self.default_question_time)
                        try:
                            self.time_left = float(t)
                            self.time_total = float(t)
                        except:
                            self.time_left = float(self.default_question_time)
                            self.time_total = float(self.default_question_time)
                dt = self.clock.get_time() / 1000.0
                if self.time_left is not None:
                    self.time_left -= dt
                    if self.time_left <= 0:
                        self.time_left = 0
                        self.game_state = "answered"
            self.update_question_buttons()
        elif self.game_state == "answered":
            next_rect = pygame.Rect(500, 600, 200, 60)
            self.buttons.append({
                "rect": next_rect,
                "text": "Tiếp theo",
                "action": "next_question"
            })
    
    def update_question_buttons(self):
        """Update question and answer buttons"""
        if self.current_question >= len(self.game_data["questions"]):
            return
        
        question = self.game_data["questions"][self.current_question]
        
        # Answer buttons
        if question["type"] == "multiple_choice" and "options" in question:
            for i, option in enumerate(question["options"]):
                x = 100 + (i % 2) * 500
                y = 300 + (i // 2) * 120
                rect = pygame.Rect(x, y, 400, 100)
                
                self.buttons.append({
                    "rect": rect,
                    "text": option,
                    "action": "select_answer",
                    "answer": option,
                    "index": i
                })
        elif question.get("type") == "true_false":
            for i, tf in enumerate(["True", "False"]):
                x = 100 + i * 500
                y = 300
                rect = pygame.Rect(x, y, 400, 100)
                self.buttons.append({
                    "rect": rect,
                    "text": tf,
                    "action": "select_answer",
                    "answer": True if tf == "True" else False,
                    "index": i
                })
        elif question.get("type") == "fill_blank":
            try:
                if not hasattr(self, "input_text"):
                    self.input_text = ""
            except:
                self.input_text = ""
            self.input_rect = pygame.Rect(100, 320, 900, 80)
        elif question.get("type") == "matching" and question.get("pairs"):
            self.match_left = None
            self.match_right = None
            lefts = [p.get("left") for p in question.get("pairs")]
            rights = [p.get("right") for p in question.get("pairs")]
            for i, text in enumerate(lefts):
                rect = pygame.Rect(100, 300 + i * 90, 420, 70)
                self.buttons.append({
                    "rect": rect,
                    "text": text,
                    "action": "select_left",
                    "index": i
                })
            for i, text in enumerate(rights):
                rect = pygame.Rect(680, 300 + i * 90, 420, 70)
                self.buttons.append({
                    "rect": rect,
                    "text": text,
                    "action": "select_right",
                    "index": i
                })
        
        # Submit button
        submit_rect = pygame.Rect(500, 600, 200, 60)
        self.buttons.append({
            "rect": submit_rect,
            "text": "Nộp bài",
            "action": "submit_answer"
        })
    
    def draw(self):
        """Draw everything"""
        self.screen.fill(BACKGROUND_COLOR)
        
        if self.current_question < len(self.game_data["questions"]):
            self.draw_question()
        else:
            self.draw_game_over()
        
        pygame.display.flip()
    
    def draw_question(self):
        """Draw current question"""
        question = self.game_data["questions"][self.current_question]
        
        # Question text
        question_text = self.font_medium.render(
            f"Câu {self.current_question + 1}: {question['question']}", 
            True, TEXT_COLOR
        )
        self.screen.blit(question_text, (100, 150))
        
        # Answer buttons
        for button in self.buttons:
            if button["action"] in ("select_answer", "select_left", "select_right"):
                # Draw button
                color = PANEL_COLOR
                if self.game_state == "answered":
                    correct_index = None
                    try:
                        ca = question.get('correct_answer')
                        if isinstance(ca, int):
                            correct_index = ca
                        elif isinstance(ca, str):
                            if ca in ['A', 'B', 'C', 'D']:
                                correct_index = ['A', 'B', 'C', 'D'].index(ca)
                            else:
                                try:
                                    correct_index = question['options'].index(ca)
                                except Exception:
                                    correct_index = None
                    except Exception:
                        correct_index = None
                    sel_idx = None
                    try:
                        sel_idx = question["options"].index(self.selected_answer) if self.selected_answer is not None else None
                    except:
                        sel_idx = None
                    if button["action"] == "select_answer":
                        if question.get("type") == "multiple_choice":
                            if correct_index is not None and button.get("index") == correct_index:
                                color = SUCCESS_COLOR
                            elif sel_idx is not None and button.get("index") == sel_idx:
                                color = WARNING_COLOR
                else:
                    if button.get("action") == "select_answer":
                        if button.get("answer") == self.selected_answer:
                            color = ACCENT_COLOR
                    elif button.get("action") == "select_left":
                        if hasattr(self, "match_left") and self.match_left == button.get("index"):
                            color = ACCENT_COLOR
                    elif button.get("action") == "select_right":
                        if hasattr(self, "match_right") and self.match_right == button.get("index"):
                            color = ACCENT_COLOR
                
                pygame.draw.rect(self.screen, color, button["rect"], border_radius=12)
                pygame.draw.rect(self.screen, ACCENT_COLOR, button["rect"], 2, border_radius=12)
                
                # Draw text
                text = self.font_small.render(button["text"], True, TEXT_COLOR)
                text_rect = text.get_rect(center=button["rect"].center)
                self.screen.blit(text, text_rect)

        if question.get("type") == "fill_blank" and hasattr(self, "input_rect"):
            pygame.draw.rect(self.screen, PANEL_COLOR, self.input_rect, border_radius=10)
            pygame.draw.rect(self.screen, ACCENT_COLOR, self.input_rect, 2, border_radius=10)
            txt = self.font_small.render(self.input_text if hasattr(self, "input_text") else "", True, TEXT_COLOR)
            self.screen.blit(txt, (self.input_rect.x + 12, self.input_rect.y + 24))
        
        # Submit button
        submit_button = next((b for b in self.buttons if b["action"] == "submit_answer"), None)
        if submit_button:
            pygame.draw.rect(self.screen, ACCENT_COLOR, submit_button["rect"], border_radius=12)
            text = self.font_small.render(submit_button["text"], True, TEXT_COLOR)
            text_rect = text.get_rect(center=submit_button["rect"].center)
            self.screen.blit(text, text_rect)
        
        next_button = next((b for b in self.buttons if b["action"] == "next_question"), None)
        if next_button:
            pygame.draw.rect(self.screen, ACCENT_COLOR, next_button["rect"], border_radius=12)
            text = self.font_small.render(next_button["text"], True, TEXT_COLOR)
            text_rect = text.get_rect(center=next_button["rect"].center)
            self.screen.blit(text, text_rect)
        
        if self.game_state == "answered":
            if self.settings.get("show_explanations") and question.get("explanation"):
                expl_text = self.font_small.render(f"Giải thích: {question['explanation']}", True, TEXT_COLOR)
                self.screen.blit(expl_text, (100, 520))

        # Stats
        stats_time = "-"
        if self.time_limit_enabled and self.time_left is not None and self.game_state == "playing":
            try:
                stats_time = str(max(0, int(self.time_left)))
            except:
                stats_time = "-"
        stats_text = self.font_small.render(
            f"Điểm: {self.score} | Đúng: {self.correct_count}/{self.current_question + 1} | Thời gian: {stats_time}", 
            True, TEXT_COLOR
        )
        self.screen.blit(stats_text, (100, 50))
        if self.time_limit_enabled and self.time_left is not None and self.time_total and self.game_state == "playing":
            try:
                ratio = max(0.0, min(1.0, self.time_left / self.time_total))
            except:
                ratio = 0.0
            bar_bg = pygame.Rect(100, 80, 600, 16)
            bar_fg = pygame.Rect(100, 80, int(600 * ratio), 16)
            pygame.draw.rect(self.screen, PANEL_COLOR, bar_bg, border_radius=8)
            pygame.draw.rect(self.screen, ACCENT_COLOR, bar_fg, border_radius=8)
        if self.game_state == "answered":
            try:
                correct_index = ['A', 'B', 'C', 'D'].index(question['correct_answer'])
            except:
                correct_index = None
            sel_idx = None
            try:
                sel_idx = question["options"].index(self.selected_answer) if self.selected_answer is not None else None
            except:
                sel_idx = None
            for button in self.buttons:
                if button.get("index") is None:
                    continue
                label = None
                color = None
                if correct_index is not None and button.get("index") == correct_index:
                    label = "Đúng"
                    color = SUCCESS_COLOR
                elif sel_idx is not None and button.get("index") == sel_idx:
                    label = "Sai"
                    color = WARNING_COLOR
                if label:
                    txt = self.font_small.render(label, True, TEXT_COLOR)
                    r = button["rect"]
                    pygame.draw.rect(self.screen, color, r, 3, border_radius=12)
                    self.screen.blit(txt, (r.x + r.width - 60, r.y + 8))
    
    def draw_game_over(self):
        """Draw game over screen"""
        # Title
        title_text = self.font_large.render("Hoàn thành!", True, ACCENT_COLOR)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(title_text, title_rect)
        
        # Final score
        score_text = self.font_large.render(f"Điểm: {self.score}", True, SUCCESS_COLOR)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 300))
        self.screen.blit(score_text, score_rect)
        
        # Stats
        stats_text = self.font_medium.render(
            f"Trả lời đúng: {self.correct_count}/{len(self.game_data['questions'])}", 
            True, TEXT_COLOR
        )
        stats_rect = stats_text.get_rect(center=(SCREEN_WIDTH // 2, 400))
        self.screen.blit(stats_text, stats_rect)
    
    def submit_answer(self):
        """Submit current answer"""
        if self.selected_answer is None:
            return
        
        question = self.game_data["questions"][self.current_question]
        is_correct = False
        
        if question["type"] == "multiple_choice":
            selected_index = question["options"].index(self.selected_answer)
            correct_index = None
            try:
                ca = question.get('correct_answer')
                if isinstance(ca, int):
                    correct_index = ca
                elif isinstance(ca, str):
                    if ca in ['A', 'B', 'C', 'D']:
                        correct_index = ['A', 'B', 'C', 'D'].index(ca)
                    else:
                        try:
                            correct_index = question['options'].index(ca)
                        except Exception:
                            correct_index = None
            except Exception:
                correct_index = None
            is_correct = (correct_index is not None) and (selected_index == correct_index)
        elif question.get("type") == "true_false":
            try:
                is_correct = bool(self.selected_answer) == bool(question.get("correct_answer", True))
            except:
                is_correct = False
        elif question.get("type") == "fill_blank":
            user = str(self.selected_answer or "").strip()
            answers = question.get("correct_answers") or question.get("answers") or []
            if not isinstance(answers, list):
                answers = [answers]
            try:
                cs = bool(question.get("case_sensitive", False))
            except:
                cs = False
            norm = (lambda s: s if cs else s.lower())
            try:
                is_correct = any(norm(user) == norm(str(a).strip()) for a in answers)
            except:
                is_correct = False
        elif question.get("type") == "matching" and question.get("pairs") and isinstance(self.selected_answer, dict):
            try:
                li = self.selected_answer.get("left")
                ri = self.selected_answer.get("right")
                pr = question.get("pairs")[li]
                is_correct = pr and pr.get("right") == question.get("pairs")[ri].get("right")
            except:
                is_correct = False
        
        if is_correct:
            self.correct_count += 1
            self.score += self.points_per_question
            try:
                if self.snd_correct:
                    self.snd_correct.play()
            except:
                pass
        else:
            try:
                if self.snd_wrong:
                    self.snd_wrong.play()
            except:
                pass
        
        self.game_state = "answered"
        self.time_left = None
        self.time_total = None
    
    def next_question(self):
        """Move to next question"""
        self.current_question += 1
        self.selected_answer = None
        self.game_state = "playing"
        self.time_left = None
        self.time_total = None
    
    def restart_game(self):
        """Restart the game"""
        self.current_question = 0
        self.score = 0
        self.correct_count = 0
        self.selected_answer = None
        self.game_state = "playing"
        self.time_left = None
        self.time_total = None

if __name__ == "__main__":
    game = EduPlayGame()
    game.run()
        '''
        
        template = Template(pygame_template)
        return template.render(project_name=project_data.get("name", "EduPlay Game"))
    
    def _copy_game_assets(self, output_path: Path, project_data: Dict):
        """Copy game assets to output directory"""
        assets_dir = output_path / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        # Copy default assets
        if self.assets_dir.exists():
            for item in self.assets_dir.iterdir():
                if item.is_dir():
                    dest_dir = assets_dir / item.name
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    shutil.copytree(item, dest_dir)
        
        # Copy project media files
        if "media_files" in project_data:
            media_dir = assets_dir / "media"
            media_dir.mkdir(exist_ok=True)
            
            for media_file in project_data["media_files"]:
                src_path = Path(media_file.get("path", ""))
                if src_path.exists():
                    shutil.copy2(src_path, media_dir)
    
    def _create_run_script(self, output_path: Path, command: str = "start \"\" \"index.html\"", shell_script: bool = False):
        """Create run script"""
        if shell_script:
            # Unix/Linux/macOS script
            script_content = f'''#!/bin/bash
{command}
'''
            script_file = output_path / "run.sh"
            script_file.write_text(script_content)
            script_file.chmod(0o755)  # Make executable
        else:
            # Windows batch file
            script_content = f'''@echo off
{command}
pause
'''
            script_file = output_path / "run.bat"
            script_file.write_text(script_content)
    
    def _create_readme(self, output_path: Path, export_type: str):
        try:
            readme_file = output_path / "README.md"
            content = "# EduPlay Game - {} Export\n\nRun using run.bat (Windows) or run.sh (Unix).\n".format(export_type)
            readme_file.write_text(content, encoding='utf-8')
        except Exception:
            pass


"""
Nguyen-Thanh-Tan ¬_¬
"""
