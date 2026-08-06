import os
import json
import time
import hashlib
import base64
import uuid
import platform
import getpass
from typing import Optional, Callable, Any, Dict, List
from pathlib import Path
import sys
from urllib.parse import urlparse

from eduplay.core.path_resolver import PathResolver

import requests


class AIService:
    EMBEDDED_GROQ_KEYS: list[str] = []
    DEFAULT_PROXY_ROOT_URL = ""  # REDACTED — configure via settings
    DEFAULT_PROXY_BASE_URL = DEFAULT_PROXY_ROOT_URL + "/openai/v1"
    LEGACY_PROXY_BASE_URLS: set[str] = set()  # REDACTED
    SERVER_WAKEUP_RETRY_SECONDS = 4
    SERVER_WAKEUP_MAX_ATTEMPTS = 3

    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager
        self.is_ready = False
        self.base_url = self._resolve_base_url()
        self.default_model = self._resolve_default_model()
        self._last_log_text = None
        self._last_log_ts = 0.0
        self._device_id_cache = None
        self._machine_fingerprint_cache = None
        self._device_key_cache = None
        print(f"[AI-INIT] Base URL: {self.base_url}")
        print(f"[AI-INIT] Default Model: {self.default_model}")

    def _get_settings_manager(self):
        if self.settings_manager is not None:
            return self.settings_manager
        try:
            from eduplay.core.settings_manager import SettingsManager
            self.settings_manager = SettingsManager()
            return self.settings_manager
        except Exception:
            return None

    def _resolve_base_url(self) -> str:
        env_url = os.getenv("EDUPLAY_AI_SERVER_URL")
        if env_url and str(env_url).strip():
            return self._normalize_base_url(str(env_url).strip())
        cfg_mgr = self._get_settings_manager()
        if cfg_mgr is not None:
            try:
                cfg_url = cfg_mgr.get("ai_settings.server_base_url", "")
                if cfg_url and str(cfg_url).strip():
                    return self._normalize_base_url(str(cfg_url).strip())
            except Exception:
                pass
        return self._normalize_base_url(self.DEFAULT_PROXY_BASE_URL)

    def _normalize_base_url(self, url: str) -> str:
        try:
            base = str(url or "").strip().rstrip("/")
        except Exception:
            base = ""
        if not base:
            return self.DEFAULT_PROXY_BASE_URL.rstrip("/")
        if base in self.LEGACY_PROXY_BASE_URLS:
            return self.DEFAULT_PROXY_BASE_URL.rstrip("/")
        try:
            parsed = urlparse(base)
            if parsed.scheme in ("http", "https") and (parsed.path or "/") == "/":
                return base + "/openai/v1"
        except Exception:
            pass
        return base

    def _resolve_default_model(self) -> str:
        env_model = os.getenv("GROQ_MODEL")
        if env_model and str(env_model).strip():
            return str(env_model).strip()
        cfg_mgr = self._get_settings_manager()
        if cfg_mgr is not None:
            try:
                cfg = cfg_mgr.get("ai_settings.groq_model", "")
                if cfg and str(cfg).strip():
                    return str(cfg).strip()
            except Exception:
                pass
        return "llama-3.1-8b-instant"

    def _settings_dir(self) -> Path:
        cfg_mgr = self._get_settings_manager()
        if cfg_mgr is not None:
            try:
                existing = Path(getattr(cfg_mgr, "settings_dir"))
                existing.mkdir(parents=True, exist_ok=True)
                return existing
            except Exception:
                pass
        try:
            d = PathResolver.resolve_settings_dir()
        except Exception:
            d = Path.cwd()
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return d

    def _token_cache_path(self) -> Path:
        return self._settings_dir() / "ai_proxy_token.txt"

    def _device_id(self) -> str:
        if self._device_id_cache:
            return self._device_id_cache
        try:
            node = str(platform.node() or "").strip()
        except Exception:
            node = ""
        try:
            user = str(getpass.getuser() or "").strip()
        except Exception:
            user = ""
        try:
            mac = str(uuid.getnode() or "").strip()
        except Exception:
            mac = ""
        raw = (node + "|" + user + "|" + mac).encode("utf-8", errors="ignore")
        did = "dev_" + hashlib.sha256(raw).hexdigest()[:32]
        self._device_id_cache = did
        return did

    def _machine_fingerprint(self) -> str:
        if self._machine_fingerprint_cache:
            return self._machine_fingerprint_cache
        parts = []
        for getter in (
            lambda: platform.node(),
            lambda: platform.machine(),
            lambda: platform.platform(),
            lambda: getpass.getuser(),
            lambda: uuid.getnode(),
        ):
            try:
                parts.append(str(getter() or "").strip())
            except Exception:
                parts.append("")
        raw = "|".join(parts).encode("utf-8", errors="ignore")
        fp = "mfp_" + hashlib.sha256(raw).hexdigest()
        self._machine_fingerprint_cache = fp
        return fp

    def _device_key(self) -> str:
        if self._device_key_cache:
            return self._device_key_cache
        cfg_mgr = self._get_settings_manager()
        current_fp = self._machine_fingerprint()
        if cfg_mgr is not None:
            try:
                saved = str(cfg_mgr.get("device_auth.device_key", "") or "").strip()
            except Exception:
                saved = ""
            try:
                saved_fp = str(cfg_mgr.get("device_auth.machine_fingerprint", "") or "").strip()
            except Exception:
                saved_fp = ""
            if saved and (not saved_fp or saved_fp == current_fp):
                self._device_key_cache = saved
                return saved
        seed = f"{current_fp}|{uuid.uuid4().hex}|{time.time()}"
        device_key = "dkey_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()
        self._device_key_cache = device_key
        if cfg_mgr is not None:
            try:
                cfg_mgr.set("device_auth.device_key", device_key)
            except Exception:
                pass
            try:
                cfg_mgr.set("device_auth.machine_fingerprint", current_fp)
            except Exception:
                pass
        return device_key

    def _load_cached_proxy_token(self) -> str:
        p = self._token_cache_path()
        try:
            if not p.exists():
                return ""
        except Exception:
            return ""
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            return ""
        if not raw:
            return ""
        if raw.startswith("plain:"):
            return str(raw.split("plain:", 1)[1] or "").strip()
        if raw.startswith("enc_v1:"):
            b64 = str(raw.split("enc_v1:", 1)[1] or "").strip()
            if not b64:
                return ""
            try:
                blob = base64.b64decode(b64)
            except Exception:
                return ""
            try:
                from eduplay.core.dpapi import unprotect as _dpapi_unprotect
            except Exception:
                _dpapi_unprotect = None  # type: ignore
            if _dpapi_unprotect is None:
                return ""
            try:
                plain = _dpapi_unprotect(blob).decode("utf-8", errors="ignore")
            except Exception:
                return ""
            return str(plain or "").strip()
        return ""

    def _save_cached_proxy_token(self, token: str) -> None:
        t = str(token or "").strip()
        if not t:
            return
        p = self._token_cache_path()
        try:
            from eduplay.core.dpapi import protect as _dpapi_protect
        except Exception:
            _dpapi_protect = None  # type: ignore
        if _dpapi_protect is None or sys.platform != "win32":
            try:
                p.write_text("plain: " + t, encoding="utf-8")
            except Exception:
                pass
            return
        try:
            blob = _dpapi_protect(t.encode("utf-8"))
            b64 = base64.b64encode(blob).decode("ascii")
            p.write_text("enc_v1: " + b64, encoding="utf-8")
        except Exception:
            try:
                p.write_text("plain: " + t, encoding="utf-8")
            except Exception:
                pass

    def _clear_cached_proxy_token(self) -> None:
        p = self._token_cache_path()
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass

    def _proxy_root_url(self) -> str:
        try:
            base = str(self.base_url or "").strip().rstrip("/")
        except Exception:
            base = ""
        if base.endswith("/openai/v1"):
            return base[: -len("/openai/v1")].rstrip("/")
        if "/openai/v1" in base:
            try:
                return base.rsplit("/openai/v1", 1)[0].rstrip("/")
            except Exception:
                return base
        return base

    def _notify_progress(self, progress_cb: Optional[Callable], message: str) -> None:
        if not progress_cb:
            return
        try:
            progress_cb(str(message))
        except TypeError:
            try:
                progress_cb(str(message), None)
            except Exception:
                pass
        except Exception:
            pass

    def _server_wakeup_message(self) -> str:
        return "Đang gọi AI, server đang khởi động..."

    def _response_indicates_wakeup(self, status_code: int, detail: str) -> bool:
        text = str(detail or "").strip().lower()
        if status_code in (502, 503, 504):
            if not text:
                return True
            return any(
                marker in text
                for marker in (
                    "server_starting",
                    "starting",
                    "warming",
                    "cold start",
                    "booting",
                    "temporarily unavailable",
                    "upstream request timeout",
                )
            )
        return any(
            marker in text
            for marker in ("server_starting", "warming", "cold start", "booting")
        )

    def _register_proxy_token(self, progress_cb: Optional[Callable] = None) -> str:
        device_id = self._device_id()
        payload = {
            "device_id": device_id,
            "device_key": self._device_key(),
            "machine_fingerprint": self._machine_fingerprint(),
            "platform": str(platform.platform() or ""),
            "app_id": "eduplay-studio",
        }
        endpoints = []
        try:
            root = self._proxy_root_url().rstrip("/")
        except Exception:
            root = ""
        if not root:
            return ""
        endpoints.append((root + "/device/register", payload))
        endpoints.append((root + "/register", {"device_id": device_id}))

        for index, (url, body) in enumerate(endpoints):
            for attempt in range(self.SERVER_WAKEUP_MAX_ATTEMPTS):
                try:
                    resp = requests.post(url, json=body, timeout=(5, 25))
                except requests.exceptions.RequestException:
                    resp = None
                if resp is None:
                    if attempt < (self.SERVER_WAKEUP_MAX_ATTEMPTS - 1):
                        self._notify_progress(progress_cb, self._server_wakeup_message())
                        time.sleep(self.SERVER_WAKEUP_RETRY_SECONDS)
                        continue
                    break
                if resp.status_code == 404 and index == 0:
                    break
                if resp.status_code != 200:
                    try:
                        detail = resp.text or ""
                    except Exception:
                        detail = ""
                    if self._response_indicates_wakeup(resp.status_code, detail) and attempt < (self.SERVER_WAKEUP_MAX_ATTEMPTS - 1):
                        self._notify_progress(progress_cb, self._server_wakeup_message())
                        time.sleep(self.SERVER_WAKEUP_RETRY_SECONDS)
                        continue
                    break
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                token = ""
                try:
                    token = str((data or {}).get("access_token") or (data or {}).get("token") or "").strip()
                except Exception:
                    token = ""
                if token:
                    self._save_cached_proxy_token(token)
                    return token
                break
        return ""

    def _normalize_lang_code(self, language: str) -> str:
        try:
            s = str(language or "").strip().lower()
        except Exception:
            s = ""
        if "_" in s:
            s = s.split("_", 1)[0]
        if "-" in s:
            s = s.split("-", 1)[0]
        if s in ("vi", "en", "fr", "es", "de"):
            return s
        return "en"

    def _system_prompt_for_lang(self, lang: str) -> str:
        base_tool_rules = (
            "Tool-output rules:\n"
            "- If the user requests an in-app action (create/open project, add/update/delete question, update config, set image, web search): output ONLY tool commands.\n"
            "- Each command MUST be exactly 1 line, format: COMMAND: {\"key\":\"value\"}\n"
            "- JSON MUST be valid one-line JSON using double quotes only.\n"
            "- Do NOT output <think>...</think>.\n"
            "- Never mention internal IDs (project_id, question_id, request_id). Use names or question numbers only.\n"
            "- If the request cannot be done with the allowed commands: output exactly 1 line: ko có trong danh sách lệnh\n"
            "- CREATE_PROJECT: \"name\" MUST be the short project title only (e.g. \"Toán lớp 4\"). Do NOT include phrases like 'tạo dự án', 'về', 'game', 'loại' in the name field.\n"
            "\n"
            "Allowed commands (use ONLY these):\n"
            "- CREATE_PROJECT, OPEN_PROJECT, ADD_QUESTION, UPDATE_QUESTION, DELETE_QUESTION\n"
            "- SET_QUESTION_IMAGE, SET_QUESTION_IMAGE_URL, SEARCH_IMAGE\n"
            "- UPDATE_GAME_CONFIG, READ_PROJECT_DETAILS, WEB_SEARCH, WEB_FETCH\n"
            "\n"
            "UPDATE_GAME_CONFIG examples:\n"
            "- Bật trộn câu hỏi: UPDATE_GAME_CONFIG: {\"randomize_questions\":true}\n"
            "- Tắt trộn câu hỏi: UPDATE_GAME_CONFIG: {\"randomize_questions\":false}\n"
            "- Đổi thời gian: UPDATE_GAME_CONFIG: {\"question_time\":45}\n"
        )
        question_rules = (
            "\n"
            "Question-generation rules:\n"
            "- If the user asks for N questions, output exactly N ADD_QUESTION lines (no more, no less) and NOTHING else.\n"
            "- Valid types: multiple_choice, true_false, fill_blank, matching, short_answer.\n"
            "- IMPORTANT: 'Ai là triệu phú' (Who Wants to Be a Millionaire) ONLY supports 'multiple_choice' questions with exactly 4 options.\n"
            "  If the current project is 'Ai là triệu phú' and the user asks for multiple question types, politely explain that this game only supports multiple_choice and generate ONLY multiple_choice questions.\n"
            "  Never add true_false, fill_blank, matching, or short_answer to a 'Ai là triệu phú' project.\n"
            "- multiple_choice schema: {\"type\":\"multiple_choice\",\"question\":\"...\",\"options\":[\"...\",\"...\",\"...\",\"...\"],\"correct_answer\":0,\"explanation\":\"...\"}\n"
            "- true_false schema: {\"type\":\"true_false\",\"question\":\"...\",\"correct_answer\":true,\"explanation\":\"...\"}\n"
            "- fill_blank schema: {\"type\":\"fill_blank\",\"question\":\"... ____ ...\",\"answers\":[\"...\"],\"case_sensitive\":false,\"explanation\":\"...\"}\n"
            "- matching schema: {\"type\":\"matching\",\"question\":\"...\",\"pairs\":[{\"left\":\"...\",\"right\":\"...\"}],\"explanation\":\"...\"}\n"
            "- short_answer schema: {\"type\":\"short_answer\",\"question\":\"...\",\"answers\":[\"...\"],\"explanation\":\"...\"}\n"
        )
        attachment_rules_vi = (
            "\n"
            "Nếu có tài liệu đính kèm: chỉ dùng nội dung trong tài liệu để tạo câu hỏi. KHÔNG bịa thêm kiến thức ngoài tài liệu.\n"
            "Khi viết explanation: KHÔNG dùng từ 'tài liệu' hoặc các cụm như 'theo/dựa trên...'.\n"
            "Nếu tài liệu là giáo án: chỉ tạo câu hỏi dựa trên PHẦN GIÁO VIÊN ĐÃ DẠY.\n"
        )
        if lang == "vi":
            return (
                "Tôi là Edubot trong ứng dụng EduPlay Studio.\n"
                "Vai trò: TRỢ LÝ GIÁO VIÊN.\n"
                "Mục tiêu: giúp giáo viên tạo câu hỏi/bài luyện tập nhanh, đúng trọng tâm, đúng số lượng.\n"
                "\n"
                "Cách trả lời:\n"
                "- Tôi xưng 'Tôi' và gọi người dùng là 'bạn'.\n"
                "- Nếu chỉ hỏi/trao đổi: trả lời tự nhiên, rõ ràng, đúng trọng tâm. Không lan man.\n"
                "\n"
                "QUAN TRỌNG — Phân tích ý nghĩa trước khi hành động:\n"
                "- Trước khi output tool command, hãy hiểu ý nghĩa thực sự của yêu cầu.\n"
                "- Ví dụ: 'xoá 4 câu cuối' nghĩa là xoá 4 câu hỏi ở cuối danh sách (câu cuối cùng, câu áp chót, ...). KHÔNG phải 'xoá câu số 4'.\n"
                "- Ví dụ: 'xoá câu thứ 4' hoặc 'xoá câu số 4' mới là xoá câu có số thứ tự 4.\n"
                "- Khi 'xoá N câu cuối': output đúng N dòng DELETE_QUESTION, mỗi dòng dùng question_number của từng câu cần xoá (đếm từ cuối lên).\n"
                "- Tương tự với 'xoá câu đầu', 'xoá N câu đầu', v.v.\n"
                "\n"
                + attachment_rules_vi
                + "\n"
                + base_tool_rules
                + question_rules
                + "\n"
                "Web & images:\n"
                "- WEB_SEARCH: <query>\n"
                "- WEB_FETCH: <URL>\n"
                "- SEARCH_IMAGE: {\"question_number\":1,\"query\":\"...\"} or {\"question_id\":\"q_...\",\"query\":\"...\"}\n"
                "- SET_QUESTION_IMAGE_URL: {\"question_number\":1,\"url\":\"https://...\"} or {\"question_id\":\"q_...\",\"url\":\"https://...\"}\n"
            )
        if lang == "fr":
            return (
                "Tu es Edubot dans EduPlay Studio.\n"
                "Réponds en français, de façon concise et pertinente.\n"
                + "\n"
                + base_tool_rules
                + question_rules
            )
        if lang == "es":
            return (
                "Eres Edubot en EduPlay Studio.\n"
                "Responde en español, de forma concisa y pertinente.\n"
                + "\n"
                + base_tool_rules
                + question_rules
            )
        if lang == "de":
            return (
                "Du bist Edubot in EduPlay Studio.\n"
                "Antworte auf Deutsch, kurz und relevant.\n"
                + "\n"
                + base_tool_rules
                + question_rules
            )
        return (
            "You are Edubot in EduPlay Studio.\n"
            "Answer in English, concise and relevant.\n"
            + "\n"
            + base_tool_rules
            + question_rules
        )

    def _get_proxy_token(self) -> str:
        try:
            cached = self._load_cached_proxy_token()
            if cached and str(cached).strip():
                return str(cached).strip()
        except Exception:
            pass
        return ""

    def _should_use_proxy(self) -> bool:
        try:
            base = str(self.base_url or "").strip().rstrip("/")
        except Exception:
            base = ""
        return bool(base)

    def check_ready_fast(self) -> bool:
        try:
            return bool(self._should_use_proxy() and self._device_key())
        except Exception:
            return False

    def setup_ai(self, progress_cb: Optional[Callable] = None) -> bool:
        def show_progress(message: str, value: Optional[int] = None):
            if progress_cb:
                progress_cb(message, value)
            try:
                now = time.monotonic()
            except Exception:
                now = 0.0
            try:
                msg = str(message)
            except Exception:
                msg = ""
            if msg == getattr(self, "_last_log_text", None):
                if now and (now - float(getattr(self, "_last_log_ts", 0.0)) < 0.75):
                    return
            self._last_log_text = msg
            self._last_log_ts = now
            print(f"[AI] {msg}")

        if not self._should_use_proxy():
            show_progress("Thiếu cấu hình AI server", 100)
            self.is_ready = False
            return False
        show_progress("Đang chuẩn bị kết nối AI server...", 20)
        if not self._device_key():
            show_progress("Không tạo được device key", 100)
            self.is_ready = False
            return False
        self.is_ready = True
        show_progress("AI server sẵn sàng", 100)
        return True

    def chat_with_ai(
        self,
        prompt: str,
        language: str = "vi",
        app_context: Optional[str | dict | list] = None,
        model: Optional[str] = None,
        progress_cb: Optional[Callable] = None,
    ) -> str:
        try:
            prompt_s = str(prompt or "")
        except Exception:
            prompt_s = ""

        chat_history = []
        ctx_obj = app_context
        try:
            if isinstance(app_context, dict):
                chat_history = list(app_context.get("chat_history", []) or [])
                if "chat_history" in app_context:
                    ctx_obj = dict(app_context)
                    try:
                        ctx_obj.pop("chat_history", None)
                    except Exception:
                        pass
        except Exception:
            chat_history = []
            ctx_obj = app_context

        try:
            if isinstance(ctx_obj, (dict, list)):
                ctx_s = json.dumps(ctx_obj, ensure_ascii=False, indent=2)
            else:
                ctx_s = str(ctx_obj or "").strip()
        except Exception:
            ctx_s = ""

        lang = self._normalize_lang_code(language)

        if ctx_s:
            if lang == "vi":
                prompt_s = f"Ngữ cảnh ứng dụng:\n{ctx_s}\n\nYêu cầu:\n{prompt_s}"
            elif lang == "fr":
                prompt_s = f"Contexte de l’application:\n{ctx_s}\n\nDemande:\n{prompt_s}"
            elif lang == "es":
                prompt_s = f"Contexto de la aplicación:\n{ctx_s}\n\nSolicitud:\n{prompt_s}"
            elif lang == "de":
                prompt_s = f"App-Kontext:\n{ctx_s}\n\nAnfrage:\n{prompt_s}"
            else:
                prompt_s = f"App context:\n{ctx_s}\n\nRequest:\n{prompt_s}"

        used_model = model or self.default_model
        messages = [{"role": "system", "content": self._system_prompt_for_lang(lang)}]
        try:
            for m in chat_history[-3:]:
                try:
                    role = str((m or {}).get("role") or "").strip().lower()
                except Exception:
                    role = ""
                try:
                    content = str((m or {}).get("content") or "").strip()
                except Exception:
                    content = ""
                if role not in ("user", "assistant"):
                    continue
                if not content:
                    continue
                messages.append({"role": role, "content": content})
        except Exception:
            pass
        messages.append({"role": "user", "content": prompt_s})
        return self.chat_messages(messages, model=used_model, progress_cb=progress_cb)

    def chat_messages(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        progress_cb: Optional[Callable] = None,
    ) -> str:
        if not self.is_ready:
            return "AI service not ready"

        if self._should_use_proxy():
            token = self._get_proxy_token()
            if not token:
                self._notify_progress(progress_cb, "Đang gọi AI, xác thực thiết bị...")
                token = self._register_proxy_token(progress_cb=progress_cb)
            if not token:
                return "Không thể xác thực thiết bị với AI server. Hãy kiểm tra server và thử lại."
            try:
                from eduplay.core.settings_manager import SettingsManager
                timeout_sec = int(SettingsManager().get("ai_settings.request_timeout_sec", 180) or 180)
            except Exception:
                timeout_sec = 180
            if timeout_sec < 30:
                timeout_sec = 30
            try:
                from eduplay.core.settings_manager import SettingsManager
                ai_settings = SettingsManager().get_ai_settings() or {}
            except Exception:
                ai_settings = {}
            try:
                t_raw = ai_settings.get("temperature", None)
                temperature = float(t_raw) if t_raw is not None else 0.2
            except Exception:
                temperature = 0.2
            try:
                max_tokens = int(ai_settings.get("max_tokens", 1024) or 1024)
            except Exception:
                max_tokens = 1024
            used_model = model or self._resolve_default_model()
            try:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Device-Id": self._device_id(),
                    "X-Device-Key": self._device_key(),
                    "X-Machine-Fingerprint": self._machine_fingerprint(),
                }
                api_url = f"{self.base_url}/chat/completions"
                for attempt in range(self.SERVER_WAKEUP_MAX_ATTEMPTS):
                    if attempt > 0:
                        self._notify_progress(progress_cb, self._server_wakeup_message())
                    try:
                        resp = requests.post(
                            api_url,
                            headers=headers,
                            json={
                                "model": used_model,
                                "messages": messages,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "stream": False,
                            },
                            timeout=(10, timeout_sec),
                        )
                    except requests.exceptions.RequestException as e:
                        if attempt < (self.SERVER_WAKEUP_MAX_ATTEMPTS - 1):
                            self._notify_progress(progress_cb, self._server_wakeup_message())
                            time.sleep(self.SERVER_WAKEUP_RETRY_SECONDS)
                            continue
                        return f"Không kết nối được AI server: {str(e)}"
                    if resp.status_code == 200:
                        data = resp.json()
                        try:
                            content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
                        except Exception:
                            content = ""
                        if str(content or "").strip():
                            return str(content)
                        return "AI server trả về kết quả rỗng. Bạn thử lại hoặc đổi model."
                    try:
                        detail = (resp.text or "").strip()
                    except Exception:
                        detail = ""
                    if resp.status_code in (401, 403):
                        self._clear_cached_proxy_token()
                        if attempt == 0:
                            token = self._register_proxy_token(progress_cb=progress_cb)
                            if token:
                                headers["Authorization"] = f"Bearer {token}"
                                continue
                        if "missing_device_id" in detail:
                            return "AI server lỗi: thiếu device ID. Liên hệ support."
                        if "unauthorized" in detail:
                            return "Thiết bị này không có quyền truy cập AI server."
                        return f"AI server từ chối xác thực thiết bị. {detail}"
                    if self._response_indicates_wakeup(resp.status_code, detail):
                        if attempt < (self.SERVER_WAKEUP_MAX_ATTEMPTS - 1):
                            self._notify_progress(progress_cb, self._server_wakeup_message())
                            time.sleep(self.SERVER_WAKEUP_RETRY_SECONDS)
                            continue
                        return "AI server vẫn đang khởi động. Bạn thử gửi lại sau vài giây."
                    if resp.status_code == 429:
                        return "AI server đang bị giới hạn tốc độ (429). Bạn thử lại sau."
                    if resp.status_code == 500:
                        if "missing_groq_key" in detail:
                            return "AI server chưa cấu hình Groq API key. Hãy kiểm tra biến môi trường trên server."
                        if "missing_token_secret" in detail:
                            return "AI server chưa cấu hình APP_TOKEN_SECRET trên server."
                    preview = (detail[:200] + "...") if len(detail) > 200 else detail
                    return f"AI server lỗi (status {resp.status_code}). {preview}"
            except Exception as e:
                return f"Không kết nối được AI server: {str(e)}"

        return "AI server chưa được cấu hình hoặc không khả dụng. Hãy kiểm tra server và thử lại."
