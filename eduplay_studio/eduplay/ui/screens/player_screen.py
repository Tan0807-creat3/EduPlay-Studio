"""
Player Screen - Screen for playing games
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QFileDialog, QMessageBox, QSizePolicy,
                               QScrollArea, QGridLayout)
from PySide6.QtCore import Signal, Qt, QUrl, QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from pathlib import Path
from datetime import datetime
import json
import os
from eduplay.core.path_resolver import PathResolver
from eduplay.ui.widgets.custom_dropdown import FlatDropdown
from eduplay.ui.icon_factory import build_line_icon, strip_icon_text

class PlayerScreen(QWidget):
    """Screen for playing exported games"""
    
    # Signals
    back_clicked = Signal()
    
    def __init__(self):
        super().__init__()
        self.current_game_path = None
        self.project_manager = None
        self._project_preview_map = {}
        self._project_meta_map = {}
        self._project_cards = []
        self._project_rows = []
        self._selected_project_meta = {}
        self._last_card_cols = 0
        try:
            from eduplay.core.settings_manager import SettingsManager
            self.language = SettingsManager().get_language() or 'en'
            self.theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            self.language = 'en'
            self.theme = 'dark'
        self.init_ui()

    def _t(self, key: str, fallback: str) -> str:
        try:
            from eduplay.core.i18n import I18n
            l = getattr(self, "language", "en")
            val = I18n.t(key, l)
            if isinstance(val, str) and val.strip() and val != key:
                return val
        except Exception:
            pass
        return fallback
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create header
        self.create_header(layout)
        
        # Create content area
        self.create_content_area(layout)
        
        # Stretch: header minimal height, content takes space
        layout.setStretch(0, 0)
        layout.setStretch(1, 1)
        
        self.setLayout(layout)
        
        # Styling handled by global theme QSS
    
    def create_header(self, layout):
        """Create header with navigation and controls"""
        header = QFrame()
        header.setObjectName("header")
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            header_style = "QFrame#header{ background-color: rgba(27,31,42,0.65); border-bottom: 1px solid #2A2F3A; }"
        else:
            header_style = "QFrame#header{ background-color: #E6F7FF; border-bottom: 1px solid #93C5FD; }"
        header.setStyleSheet(header_style)
        try:
            from PySide6.QtWidgets import QGraphicsDropShadowEffect
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(24)
            shadow.setOffset(0, 4)
            header.setGraphicsEffect(shadow)
        except Exception:
            pass
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 8, 20, 8)
        header_layout.setAlignment(Qt.AlignVCenter)
        
        # Back button
        try:
            from eduplay.core.i18n import I18n
            l = getattr(self, 'language', 'en')
            back_text = I18n.t('player.back', l)
        except Exception:
            back_text = "← Back"
        back_btn = QPushButton(strip_icon_text(back_text))
        back_btn.setObjectName("secondary-button")
        try:
            back_btn.setIcon(build_line_icon("back", "#FFFFFF" if theme == "dark" else "#0F1728", 16))
        except Exception:
            pass
        try:
            back_btn.setProperty("secondary", True)
        except Exception:
            pass
        try:
            if theme != "dark":
                back_btn.setStyleSheet(
                    "QPushButton{color:#0F1728;font-weight:700;background:#E6F7FF;border:1px solid #BFDBFE;border-radius:14px;padding:0 14px;}"
                    "QPushButton:hover{background:#DFF1FF;border-color:#93C5FD;}"
                    "QPushButton:pressed{background:#CFE8FF;}"
                )
        except Exception:
            pass
        back_btn.clicked.connect(self._on_back_pressed)
        back_btn.setMinimumWidth(120)
        back_btn.setMinimumHeight(36)
        back_btn.setMaximumHeight(44)
        header_layout.addWidget(back_btn)
        self.back_btn = back_btn
        
        header_layout.addStretch()
        
        # Title
        try:
            from eduplay.core.i18n import I18n
            l = getattr(self, 'language', 'en')
            title_text = I18n.t('player.title', l)
        except Exception:
            title_text = "Play Game"
        title_label = QLabel(title_text)
        title_label.setStyleSheet("""
            QLabel {
                color: %s;
                font-size: 20px;
                font-weight: 700;
                background: transparent;
                border: none;
                padding: 0;
            }
        """ % ('#FFFFFF' if theme == 'dark' else '#1A1A1A'))
        header_layout.addWidget(title_label)
        self.header_title = title_label
        
        header_layout.addStretch()
        
        # Keep right side empty on player list for cleaner UI
        self.open_file_btn = None
        self.open_btn = None
        self.reload_btn = None
        header_layout.addSpacing(8)
        
        layout.addWidget(header)
    
    def create_content_area(self, layout):
        """Create content area for game display"""
        self.content_area = QFrame()
        self.content_area.setObjectName("content-area")
        
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Project list panel (shown when no game is loaded)
        self.welcome_panel = self.create_welcome_panel()
        self.welcome_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self.welcome_panel)
        
        # Web view (for HTML games)
        self.web_view = QWebEngineView()
        self.web_view.setVisible(False)
        try:
            self._web_zoom_timer = QTimer(self)
            self._web_zoom_timer.setSingleShot(True)
            self._web_zoom_timer.timeout.connect(self._update_web_zoom)
        except Exception:
            self._web_zoom_timer = None
        try:
            from PySide6.QtGui import QColor
            theme = getattr(self, "theme", "dark")
            bg = QColor(2, 6, 23) if theme == "dark" else QColor(230, 247, 255)
            try:
                self.web_view.setStyleSheet(f"background-color: {bg.name()};")
            except Exception:
                pass
            try:
                self.web_view.page().setBackgroundColor(bg)
            except Exception:
                pass
        except Exception:
            pass
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineSettings
            s = self.web_view.settings()
            try:
                s.setAttribute(QWebEngineSettings.ShowScrollBars, True)
            except Exception:
                try:
                    s.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, True)
                except Exception:
                    pass
            try:
                s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
                s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
                s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
                s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
                s.setAttribute(QWebEngineSettings.WebGLEnabled, True)
                s.setAttribute(QWebEngineSettings.Accelerated2DCanvasEnabled, True)
                try:
                    self.web_view.page().setAudioMuted(False)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass
        try:
            def _on_load_finished(ok):
                if not ok:
                    return
                try:
                    self.web_view.setZoomFactor(1.0)
                except Exception:
                    pass
                try:
                    js = """
                        (function(){
                            try{
                                if (window.__setManualZoom){
                                    var orig = window.__setManualZoom;
                                    window.__setManualZoom = function(v){ try{ orig(true); }catch(e){} };
                                    try{ orig(true); }catch(e){}
                                }
                                if (window.autoScale){
                                    window.autoScale = function(){ try{ if(window.applyScale) window.applyScale(1.0); }catch(e){} };
                                }
                                if (window.applyScale){ window.applyScale(1.0); }
                            }catch(e){}
                        })();
                    """
                    self.web_view.page().runJavaScript(js)
                except Exception:
                    pass
            self.web_view.loadFinished.connect(_on_load_finished)
        except Exception:
            pass
        content_layout.addWidget(self.web_view, 1)
        
        layout.addWidget(self.content_area)
    
    def create_welcome_panel(self):
        """Create project browsing panel"""
        panel = QFrame()
        panel.setObjectName("welcome-panel")
        
        panel_layout = QVBoxLayout(panel)
        panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        panel_layout.setSpacing(10)
        panel_layout.setContentsMargins(36, 18, 36, 20)

        section_title = QLabel(self._t("browser.my_projects", "Dự án của tôi"))
        section_title.setObjectName("player-section-title")
        _theme_st = getattr(self, "theme", "dark")
        _title_color = "#E2E8F0" if _theme_st == "dark" else "#0F1728"
        section_title.setStyleSheet(
            f"QLabel#player-section-title{{color:{_title_color};font-size:42px;font-weight:700;padding:4px 2px;background:transparent;border:none;}}"
        )
        panel_layout.addWidget(section_title, 0, Qt.AlignmentFlag.AlignLeft)
        self.section_title = section_title
        
        # Keep old dropdown for data compatibility (hidden in new UI)
        self.project_combo = FlatDropdown()
        self.project_combo.setVisible(False)
        self.project_combo.currentIndexChanged.connect(self._update_project_selection_state)
        panel_layout.addWidget(self.project_combo)

        # Project cards list (similar style with Browser screen)
        self.project_scroll = QScrollArea()
        self.project_scroll.setWidgetResizable(True)
        self.project_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.project_scroll.setMinimumHeight(420)
        self.project_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        self.project_cards_container = QWidget()
        self.project_cards_layout = QGridLayout(self.project_cards_container)
        self.project_cards_layout.setContentsMargins(2, 8, 2, 8)
        self.project_cards_layout.setHorizontalSpacing(20)
        self.project_cards_layout.setVerticalSpacing(20)
        self.project_scroll.setWidget(self.project_cards_container)
        panel_layout.addWidget(self.project_scroll, 1)

        self.choose_btn = None
        self.project_status_label = None
        self.instructions_label = None
        self.icon_label = None
        self.welcome_title = None
        self.welcome_desc = None
        self._apply_project_selector_theme(getattr(self, "theme", "dark"))
        try:
            self.refresh_project_previews()
        except Exception:
            pass
        
        return panel

    def _on_back_pressed(self):
        """If preview is open, return to list. Otherwise, leave player screen."""
        try:
            if hasattr(self, "web_view") and self.web_view and self.web_view.isVisible():
                # Stop all audio/video and JS timers before hiding
                try:
                    self.web_view.page().runJavaScript(
                        "try{"
                        "  document.querySelectorAll('audio,video').forEach(function(m){"
                        "    try{m.pause();m.currentTime=0;}catch(e){}"
                        "  });"
                        "  if(typeof timerInterval!=='undefined')clearInterval(timerInterval);"
                        "  if(typeof gameTimer!=='undefined')clearInterval(gameTimer);"
                        "  if(typeof countdownTimer!=='undefined')clearInterval(countdownTimer);"
                        "}catch(e){}"
                    )
                except Exception:
                    pass
                # Load blank page to fully terminate WebEngine content
                try:
                    from PySide6.QtCore import QUrl
                    self.web_view.load(QUrl("about:blank"))
                except Exception:
                    pass
                self.show_welcome_panel()
                self.refresh_project_previews()
                return
        except Exception:
            pass
        self.back_clicked.emit()

    def _projects_root_dir(self) -> Path:
        try:
            from eduplay.core.project_manager import ProjectManager
            pm = self.project_manager or ProjectManager()
            return Path(pm.projects_dir)
        except Exception:
            return PathResolver.resolve_projects_dir()

    def _find_preview_file(self, proj_dir: Path, pid: str) -> Path | None:
        try:
            direct = proj_dir / f"{pid}_preview.html"
            if direct.exists():
                return direct
            candidates = sorted(
                proj_dir.glob("*_preview.html"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                return candidates[0]
            index_file = proj_dir / "index.html"
            if index_file.exists():
                return index_file
        except Exception:
            pass
        return None

    def _format_date(self, raw):
        try:
            if isinstance(raw, (int, float)) and raw > 0:
                return datetime.fromtimestamp(raw).strftime("%d/%m/%Y")
            if isinstance(raw, str) and raw.strip():
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
        return self._t("browser.date_unknown", "Không rõ")

    def _game_type_label(self, game_type: str) -> str:
        g = str(game_type or "").strip().lower()
        if g == "quiz_millionaire":
            return self._t("new.type_millionaire", "Ai là triệu phú")
        if g in ("quiz_fishing", "fishing"):
            return self._t("new.type_fishing", "Game Bắt Cá")
        if g == "quiz_adventure":
            return self._t("new.type_adventure", "Phiêu lưu")
        if g == "quiz_platformer":
            return self._t("new.type_platformer", "Vượt chướng ngại vật")
        return self._t("new.type_quiz", "Quiz Cổ Điển")

    def refresh_project_previews(self):
        """Refresh project list from Documents/EduPlay/Projects."""
        try:
            root = self._projects_root_dir()
            self._project_preview_map = {}
            self._project_meta_map = {}
            previous_id = str((self._selected_project_meta or {}).get("id") or "").strip()
            if hasattr(self, "project_combo"):
                self.project_combo.clear()
            self._project_rows = []
            if not root.exists():
                self._render_project_cards([])
                return
            rows = []
            try:
                from eduplay.core.project_manager import ProjectManager
                pm = self.project_manager or ProjectManager()
                self.project_manager = pm
                projects = pm.get_all_projects()
            except Exception:
                projects = []
            if projects:
                for p in projects:
                    try:
                        pid = str(p.get("id") or "").strip()
                        if not pid:
                            continue
                        name = str(p.get("name") or pid).strip()
                        desc = str(p.get("description") or "").strip()
                        game_type = str(p.get("game_type") or "quiz_classic").strip()
                        modified_at = str(p.get("modified_at") or "").strip()
                        proj_dir = root / pid
                        preview = self._find_preview_file(proj_dir, pid)
                        exists = bool(preview and preview.exists())
                        if modified_at:
                            try:
                                mtime = datetime.fromisoformat(modified_at.replace("Z", "+00:00")).timestamp()
                            except Exception:
                                mtime = preview.stat().st_mtime if exists else 0
                        else:
                            mtime = preview.stat().st_mtime if exists else 0
                        rows.append((mtime, name, pid, preview, exists, desc, game_type, modified_at))
                    except Exception:
                        continue
            else:
                for proj_dir in root.iterdir():
                    try:
                        if not proj_dir.is_dir():
                            continue
                        pid = proj_dir.name
                        preview = self._find_preview_file(proj_dir, pid)
                        exists = bool(preview and preview.exists())
                        name = pid
                        desc = ""
                        game_type = "quiz_classic"
                        modified_at = ""
                        project_file = proj_dir / f"{pid}.eduplay"
                        if project_file.exists():
                            try:
                                data = json.loads(project_file.read_text(encoding="utf-8"))
                                name = str(data.get("name") or pid)
                                desc = str(data.get("description") or "")
                                game_type = str(data.get("game_type") or "quiz_classic")
                                modified_at = str(data.get("modified_at") or "")
                            except Exception:
                                name = pid
                        if modified_at:
                            try:
                                mtime = datetime.fromisoformat(modified_at.replace("Z", "+00:00")).timestamp()
                            except Exception:
                                mtime = preview.stat().st_mtime if exists else 0
                        else:
                            mtime = preview.stat().st_mtime if exists else 0
                        rows.append((mtime, name, pid, preview, exists, desc, game_type, modified_at))
                    except Exception:
                        continue
            rows.sort(key=lambda x: x[0], reverse=True)
            for item in rows:
                mtime, name, pid, preview, exists = item[0], item[1], item[2], item[3], item[4]
                desc = ""
                game_type = "quiz_classic"
                modified_at = ""
                if len(item) >= 8:
                    desc = item[5]
                    game_type = item[6]
                    modified_at = item[7]
                status = "Da xuat" if exists else "Chua xuat"
                label = f"{name} ({pid}) - {status}"
                preview_path = str(preview) if preview else ""
                self._project_preview_map[label] = preview_path
                self._project_meta_map[label] = {
                    "id": pid,
                    "name": name,
                    "description": desc,
                    "game_type": game_type,
                    "preview": preview_path,
                    "preview_exists": bool(exists),
                    "project_dir": str(root / pid),
                    "modified_at": float(mtime),
                    "modified_at_raw": modified_at,
                }
                if hasattr(self, "project_combo"):
                    self.project_combo.addItem(label, self._project_meta_map[label])
                self._project_rows.append(self._project_meta_map[label])
            if not rows and hasattr(self, "project_combo"):
                self.project_combo.addItem(self._t("player.no_projects", "Chưa có dự án nào"), {})
            self._render_project_cards(self._project_rows)
            selected = {}
            if previous_id:
                for meta in self._project_rows:
                    if str(meta.get("id") or "") == previous_id:
                        selected = meta
                        break
            if not selected and self._project_rows:
                selected = self._project_rows[0]
            self._set_selected_project(selected)
            self._update_project_selection_state()
        except Exception:
            pass

    def _clear_project_cards(self):
        try:
            while self.project_cards_layout.count():
                item = self.project_cards_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
        except Exception:
            pass
        self._project_cards = []

    def _card_columns(self) -> int:
        try:
            w = self.width()
        except Exception:
            w = 1200
        if w < 820:
            return 1
        if w < 1240:
            return 2
        return 3

    def _render_project_cards(self, rows: list[dict]):
        self._clear_project_cards()
        self._last_card_cols = self._card_columns()
        if not rows:
            empty = QLabel(self._t("player.no_projects", "Chưa có dự án nào"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("QLabel{color:#98A2B3;font-size:14px;font-weight:600;padding:20px;}")
            self.project_cards_layout.addWidget(empty, 0, 0)
            return
        cols = self._last_card_cols
        row = 0
        col = 0
        for meta in rows:
            card = self._build_project_card(meta)
            self.project_cards_layout.addWidget(card, row, col)
            self._project_cards.append((card, meta))
            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _build_project_card(self, meta: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("player-project-card")
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumHeight(180)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        name = str(meta.get("name") or meta.get("id") or "Dự án")
        desc = str(meta.get("description") or "").strip() or self._t("player.project_desc_empty", "Không có mô tả")
        exists = bool(meta.get("preview_exists"))
        status = self._t("player.status_exported", "Đã có preview") if exists else self._t("player.status_not_exported", "Chưa xuất preview")
        game_type_text = self._game_type_label(str(meta.get("game_type") or "quiz_classic"))
        date_text = self._format_date(meta.get("modified_at_raw") or meta.get("modified_at"))

        name_label = QLabel(name)
        name_label.setTextFormat(Qt.TextFormat.PlainText)
        name_label.setObjectName("card-name")
        name_label.setStyleSheet("QLabel#card-name{font-size:18px;font-weight:700;background:transparent;border:none;padding:0;margin:0;}")
        name_label.setWordWrap(True)
        desc_label = QLabel(desc)
        desc_label.setTextFormat(Qt.TextFormat.PlainText)
        desc_label.setObjectName("card-desc")
        desc_label.setStyleSheet("QLabel#card-desc{font-size:14px;background:transparent;border:none;padding:0;margin:0;}")
        desc_label.setWordWrap(True)
        status_label = QLabel(status)
        status_label.setTextFormat(Qt.TextFormat.PlainText)
        status_label.setObjectName("card-status")
        status_label.setStyleSheet("QLabel#card-status{font-size:12px;font-weight:600;background:transparent;border:none;padding:0;margin:0;}")

        layout.addWidget(name_label)
        layout.addWidget(desc_label)
        info_layout = QHBoxLayout()
        game_type_label = QLabel(f"🎮 {game_type_text}")
        game_type_label.setTextFormat(Qt.TextFormat.PlainText)
        game_type_label.setObjectName("card-meta")
        game_type_label.setStyleSheet("QLabel#card-meta{font-size:12px;font-weight:600;color:#7F56D9;background:transparent;border:none;}")
        date_label = QLabel(f"📅 {date_text}")
        date_label.setTextFormat(Qt.TextFormat.PlainText)
        date_label.setObjectName("card-meta-date")
        date_label.setStyleSheet("QLabel#card-meta-date{font-size:12px;background:transparent;border:none;}")
        info_layout.addWidget(game_type_label)
        info_layout.addStretch()
        info_layout.addWidget(date_label)
        layout.addLayout(info_layout)
        layout.addWidget(status_label)
        layout.addStretch()

        actions = QHBoxLayout()
        open_btn = QPushButton(self._t("browser.open", "Mở"))
        open_btn.setProperty("primary", True)
        open_btn.setMinimumHeight(34)
        open_btn.setEnabled(exists)
        open_btn.setStyleSheet(
            "QPushButton{background:#7F56D9;color:#FFFFFF;border:1px solid #7F56D9;border-radius:10px;font-weight:700;padding:6px 12px;}"
            "QPushButton:hover{background:#8B66E9;border-color:#8B66E9;}"
            "QPushButton:pressed{background:#6B46C1;border-color:#6B46C1;}"
            "QPushButton:disabled{background:#E5E7EB;color:#667085;border:1px solid #D0D5DD;}"
        )
        open_btn.clicked.connect(lambda _=False, m=meta: self._open_project_preview_meta(m))
        actions.addWidget(open_btn)
        layout.addLayout(actions)

        def _card_mouse_release(event, c=card, b=open_btn, m=meta):
            try:
                if event.button() == Qt.MouseButton.LeftButton:
                    p = event.position().toPoint() if hasattr(event, "position") else event.pos()
                    child = c.childAt(p)
                    on_button = (child is b) or (child is not None and b.isAncestorOf(child))
                    self._set_selected_project(m)
                    if not on_button and bool(m.get("preview_exists")):
                        self._open_project_preview_meta(m)
            except Exception:
                pass
            try:
                QFrame.mouseReleaseEvent(c, event)
            except Exception:
                pass
        card.mouseReleaseEvent = _card_mouse_release
        self._apply_single_card_theme(card, exists, False)
        return card

    def _apply_single_card_theme(self, card: QFrame, has_preview: bool, selected: bool):
        theme = getattr(self, "theme", "dark")
        if theme == "dark":
            bg = "#2D2F3A"
            border = "#4A4E5A" if not selected else "#7F56D9"
            name_color = "#FFFFFF"
            text_color = "#A0AEC0"
            status_ok = "#34D399"
            status_no = "#F59E0B"
            date_color = "#94A3B8"
        else:
            bg = "#FFFFFF" if not selected else "#F8FAFC"
            border = "#E2E8F0" if not selected else "#7F56D9"
            name_color = "#0F1728"
            text_color = "#4B5563"
            status_ok = "#12B76A"
            status_no = "#C2410C"
            date_color = "#667085"
        status_color = status_ok if has_preview else status_no
        card.setStyleSheet(
            f"""
            QFrame#player-project-card {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QFrame#player-project-card:hover {{
                border-color: #7F56D9;
            }}
            QFrame#player-project-card QLabel#card-name {{
                color: {name_color};
                background: transparent;
                border: none;
            }}
            QFrame#player-project-card QLabel#card-desc {{
                color: {text_color};
                background: transparent;
                border: none;
            }}
            QFrame#player-project-card QLabel#card-status {{
                color: {status_color};
                background: transparent;
                border: none;
            }}
            QFrame#player-project-card QLabel#card-meta-date {{
                color: {date_color};
                background: transparent;
                border: none;
            }}
            """
        )

    def _set_selected_project(self, meta: dict):
        if not isinstance(meta, dict):
            meta = {}
        self._selected_project_meta = meta
        selected_id = str(meta.get("id") or "").strip()
        for card, card_meta in self._project_cards:
            has_preview = bool(card_meta.get("preview_exists"))
            is_selected = str(card_meta.get("id") or "").strip() == selected_id and bool(selected_id)
            self._apply_single_card_theme(card, has_preview, is_selected)
        try:
            if selected_id and hasattr(self, "project_combo"):
                for i in range(self.project_combo.count()):
                    data = self.project_combo.itemData(i)
                    if isinstance(data, dict) and str(data.get("id") or "").strip() == selected_id:
                        self.project_combo.setCurrentIndex(i)
                        break
        except Exception:
            pass
        self._update_project_selection_state()

    def _current_project_meta(self) -> dict:
        if isinstance(self._selected_project_meta, dict) and self._selected_project_meta:
            return self._selected_project_meta
        try:
            meta = self.project_combo.currentData() if hasattr(self, "project_combo") else {}
            return meta if isinstance(meta, dict) else {}
        except Exception:
            return {}

    def _open_project_preview_meta(self, meta: dict):
        self._set_selected_project(meta)
        self.load_selected_project_preview()

    def _open_project_dir_meta(self, meta: dict):
        self._set_selected_project(meta)
        try:
            proj_dir = Path(str((meta or {}).get("project_dir", "")))
            if proj_dir and str(proj_dir) and proj_dir.exists():
                os.startfile(str(proj_dir))
        except Exception:
            pass

    def load_selected_project_preview(self):
        """Load selected [project]_preview.html."""
        try:
            if not hasattr(self, "project_combo"):
                return
            meta = {}
            meta = self._current_project_meta()
            path = str(meta.get("preview") or "")
            if not path:
                QMessageBox.information(
                    self,
                    self._t("common.ok", "Thông báo"),
                    self._t("player.project_select_required", "Vui lòng chọn dự án."),
                )
                return
            fp = Path(path)
            if not fp.exists():
                QMessageBox.warning(
                    self,
                    self._t("player.preview_missing_title", "Chưa có preview"),
                    self._t(
                        "player.preview_missing_desc",
                        "Dự án này chưa có file preview.\nHãy xuất game để tạo file *_preview.html.",
                    ),
                )
                self.refresh_project_previews()
                return
            self.load_html_game(str(fp))
        except Exception:
            pass

    def _update_project_selection_state(self):
        try:
            meta = {}
            meta = self._current_project_meta()
            has_preview = bool(meta.get("preview_exists"))
            if self.choose_btn:
                self.choose_btn.setEnabled(bool(meta) and has_preview)
            if self.project_status_label:
                if not meta:
                    self.project_status_label.setText(self._t("player.no_projects", "Chưa có dự án nào."))
                elif has_preview:
                    self.project_status_label.setText(self._t("player.status_ready", "Dự án đã có preview. Bạn có thể mở ngay."))
                else:
                    self.project_status_label.setText(self._t("player.status_need_export", "Dự án chưa xuất preview. Hãy xuất game trước."))
        except Exception:
            pass

    def _apply_project_selector_theme(self, theme: str):
        try:
            if theme == "dark":
                status_color = "#CBD5E1"
                combo_bg = "#111827"
                combo_text = "#E5E7EB"
                combo_border = "#374151"
            else:
                status_color = "#475467"
                combo_bg = "#FFFFFF"
                combo_text = "#0F1728"
                combo_border = "#D0D5DD"
            if hasattr(self, "project_combo"):
                self.project_combo.setStyleSheet(
                    f"""
                    QToolButton {{
                        background-color: {combo_bg};
                        color: {combo_text};
                        border: 1px solid {combo_border};
                        border-radius: 10px;
                        text-align: left;
                        padding: 8px 12px;
                        min-height: 40px;
                        font-size: 14px;
                        font-weight: 600;
                    }}
                    QToolButton:hover {{
                        border-color: #7F56D9;
                    }}
                    QFrame#FlatDropdownPopup {{
                        background-color: {combo_bg};
                        border: 1px solid {combo_border};
                        border-radius: 10px;
                    }}
                    QListView {{
                        background-color: {combo_bg};
                        color: {combo_text};
                        border: none;
                        outline: none;
                        padding: 4px;
                    }}
                    QListView::item {{
                        padding: 8px 10px;
                        border-radius: 8px;
                    }}
                    QListView::item:selected {{
                        background-color: #7F56D9;
                        color: #FFFFFF;
                    }}
                    QListView::item:hover {{
                        background-color: #E0EAFF;
                        color: #0F1728;
                    }}
                    """
                )
            if self.project_status_label:
                self.project_status_label.setStyleSheet(
                    f"QLabel{{color:{status_color};font-size:14px;font-weight:600;}}"
                )
            for card, meta in self._project_cards:
                self._apply_single_card_theme(
                    card,
                    bool(meta.get("preview_exists")),
                    str(meta.get("id") or "") == str((self._selected_project_meta or {}).get("id") or ""),
                )
        except Exception:
            pass
    
    def choose_game_folder(self):
        """Let user choose a game folder"""
        from eduplay.core.i18n import I18n
        from eduplay.core.settings_manager import SettingsManager
        l = SettingsManager().get_language() or 'en'
        folder_path = QFileDialog.getExistingDirectory(
            self,
            I18n.t('player.choose_dialog_title', l),
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            self.load_game_from_folder(folder_path)
    
    def choose_html_file(self):
        """Let user choose a single HTML file"""
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or 'en'
            title = getattr(I18n, 't', lambda k, _l: 'Choose HTML file')( 'player.choose_file_dialog_title', l )
        except Exception:
            title = "Choose HTML file"
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", "HTML Files (*.html)")
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                markers = [
                    "const gameData",
                    "id=\"game-data\"",
                    '"game_type": "fishing"',
                    "quiz-root"
                ]
                if not any(m in content for m in markers):
                    try:
                        from eduplay.core.i18n import I18n
                        from eduplay.core.settings_manager import SettingsManager
                        l = getattr(self, 'language', None) or SettingsManager().get_language() or 'en'
                        QMessageBox.warning(self, getattr(I18n, 't', lambda k, _l: 'Invalid')( 'player.invalid_html_title', l ), getattr(I18n, 't', lambda k, _l: 'Folder does not contain EduPlay exported HTML game.')( 'player.invalid_html_desc', l ))
                    except Exception:
                        QMessageBox.warning(self, self._t("player.invalid_html_title", "Invalid"), self._t("player.invalid_html_file_desc", "Selected file is not an EduPlay HTML game"))
                    return
            except Exception:
                pass
            self.load_html_game(file_path)
    
    def open_game_folder(self):
        """Open current game folder in file explorer"""
        if self.current_game_path:
            folder_path = Path(self.current_game_path).parent
            if folder_path.exists():
                os.startfile(str(folder_path))
            else:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                l = getattr(self, 'language', None) or SettingsManager().get_language() or 'en'
                QMessageBox.warning(self, self._t("player.warning_title", "Warning"), I18n.t('player.folder_not_exist', l))
        else:
            meta = self._current_project_meta()
            try:
                proj_dir = Path(str((meta or {}).get("project_dir", "")))
            except Exception:
                proj_dir = Path("")
            if proj_dir and str(proj_dir) and proj_dir.exists():
                os.startfile(str(proj_dir))
            else:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                l = getattr(self, 'language', None) or SettingsManager().get_language() or 'en'
                QMessageBox.information(self, self._t("common.ok", "Thông báo"), I18n.t('player.no_game_loaded', l))
    
    def load_game_from_folder(self, folder_path):
        """Load game from selected folder"""
        folder = Path(folder_path)
        from eduplay.core.i18n import I18n
        from eduplay.core.settings_manager import SettingsManager
        l = getattr(self, 'language', None) or SettingsManager().get_language() or 'en'
        
        # Look for game files in priority order
        game_files = [
            ("index.html", "html"),
            ("game.py", "python"),
            ("main.py", "python")
        ]
        
        game_file = None
        game_type = None
        
        for filename, file_type in game_files:
            file_path = folder / filename
            if file_path.exists():
                game_file = file_path
                game_type = file_type
                break
        
        if not game_file:
            html_candidates = list(folder.glob("*.html"))
            chosen_html = None
            for fp in html_candidates:
                try:
                    content = fp.read_text(encoding="utf-8", errors="ignore")
                    markers = [
                        "const gameData",
                        "id=\"game-data\"",
                        '"game_type": "fishing"',
                        "quiz-root"
                    ]
                    if any(m in content for m in markers):
                        chosen_html = fp
                        break
                except Exception:
                    continue
            if chosen_html:
                game_file = chosen_html
                game_type = "html"
            else:
                QMessageBox.warning(
                    self,
                    I18n.t('player.not_found_title', l),
                    I18n.t('player.not_found_desc', l)
                )
                return
        
        # Validate and load the game
        if game_type == "html":
            try:
                content_path = game_file if game_file else (folder / "index.html")
                content = Path(content_path).read_text(encoding="utf-8", errors="ignore")
                markers = [
                    "const gameData",
                    "<div id=\"qtext\"",
                    "<div id=\"lake\"",
                    "id=\"game-data\"",
                    '"game_type": "fishing"'
                ]
                if not any(m in content for m in markers):
                    QMessageBox.warning(self, I18n.t('player.invalid_html_title', l), I18n.t('player.invalid_html_desc', l))
                    return
            except Exception:
                pass
            self.load_html_game(str(game_file))
        elif game_type == "python":
            data_file = folder / "game_data.json"
            if not data_file.exists():
                try:
                    from eduplay.core.i18n import I18n
                    from eduplay.core.settings_manager import SettingsManager
                    l = getattr(self, 'language', None) or SettingsManager().get_language() or 'en'
                    title = I18n.t('player.python_missing_data_title', l)
                    desc = I18n.t('player.python_missing_data_desc', l)
                except Exception:
                    title = "Missing data"
                    desc = "game_data.json not found for the Python game."
                QMessageBox.warning(self, title, desc)
                return
            self.load_python_game(str(game_file))
        
        self.current_game_path = str(game_file)
    
    def load_html_game(self, html_file):
        """Load HTML game in web view"""
        try:
            # Convert to file URL
            file_url = QUrl.fromLocalFile(html_file)
            
            # Hide welcome panel and show web view
            self.welcome_panel.setVisible(False)
            self.web_view.setVisible(True)
            
            # Load the game
            self.web_view.load(file_url)
            
            # Set window title
            p = Path(html_file)
            game_name = p.stem if p.name.lower().endswith('.html') and p.name.lower() != 'index.html' else p.parent.name
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = getattr(self, 'language', None) or SettingsManager().get_language() or 'en'
            self.setWindowTitle(f"{I18n.t('player.title', l)} - {game_name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                self._t("browser.error", "Error"),
                f"{str(e)}"
            )
            self.show_welcome_panel()
    
    def load_python_game(self, python_file):
        """Load and run Python game"""
        try:
            # For now, we'll show instructions on how to run Python games
            # In a full implementation, this would integrate with the Python runtime
            try:
                from eduplay.core.settings_manager import SettingsManager
                editor = SettingsManager().get_editor_settings() or {}
                font_family = str(editor.get("font_family") or "Segoe UI").replace('"', "")
            except Exception:
                font_family = "Segoe UI"

            instructions = f"""
            <html>
            <head>
                <style>
                    body {{
                        background-color: #1E1E24;
                        color: #FFFFFF;
                        font-family: "{font_family}", 'Segoe UI', sans-serif;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                        padding: 20px;
                    }}
                    .container {{
                        background-color: #2D2F3A;
                        border-radius: 16px;
                        padding: 40px;
                        max-width: 600px;
                        text-align: center;
                    }}
                    h1 {{
                        color: #F79009;
                        font-size: 28px;
                        margin-bottom: 20px;
                    }}
                    .instructions {{
                        background-color: rgba(30, 30, 36, 0.8);
                        border-radius: 12px;
                        padding: 20px;
                        margin: 20px 0;
                        text-align: left;
                    }}
                    code {{
                        background-color: #1E1E24;
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-family: 'Courier New', monospace;
                    }}
                    .run-button {{
                        background-color: #F79009;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 8px;
                        padding: 12px 24px;
                        font-size: 16px;
                        font-weight: 600;
                        text-decoration: none;
                        display: inline-block;
                        margin-top: 20px;
                    }}
                    .run-button:hover {{
                        background-color: #FFA019;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>{self._t("player.python_game_title", "Python Game")}</h1>
                    <p>{self._t("player.python_game_desc", "This is a Python game that needs to be run separately.")}</p>
                    
                    <div class="instructions">
                        <h3>{self._t("player.python_instructions_header", "How to run the game:")}</h3>
                        <ol>
                            <li>{self._t("player.python_step_open_terminal", "Open Command Prompt or Terminal")}</li>
                            <li>{self._t("player.python_step_change_dir", "Go to the game folder:")} <code>cd "{os.path.dirname(python_file)}"</code></li>
                            <li>{self._t("player.python_step_run_command", "Run the command:")} <code>python game.py</code></li>
                            <li>{self._t("player.python_step_manual", "Or use the button below to open the folder and run it manually")}</li>
                        </ol>
                    </div>
                    
                    <p><strong>{self._t("player.note_label", "Note:")}</strong> {self._t("player.python_note", "Python and Pygame are required to run this game.")}</p>
                    
                    <a href="#" class="run-button" onclick="window.openFolder()">{self._t("player.python_run_folder", "Open game folder")}</a>
                </div>
                
                <script>
                    window.openFolder = function() {{
                        // This will be handled by the Qt application
                        window.qt.openFolder(""" + os.path.dirname(python_file) + """);
                    }};
                </script>
            </body>
            </html>
            """
            
            # Hide welcome panel and show web view with instructions
            self.welcome_panel.setVisible(False)
            self.web_view.setVisible(True)
            self.web_view.setHtml(instructions)
            
            # Set window title
            game_name = Path(python_file).parent.name
            self.setWindowTitle(f"{self._t('player.title', 'Play Game')} - {game_name}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                self._t("browser.error", "Error"),
                f"{str(e)}"
            )
            self.show_welcome_panel()
    
    def reload_game(self):
        """Reload current game"""
        if self.current_game_path:
            self.load_game_from_folder(str(Path(self.current_game_path).parent))
        else:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or 'en'
            QMessageBox.information(self, self._t("player.info_title", "Info"), I18n.t('player.no_game_loaded', l))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            w_scale = self.width()/1200.0 if self.width() else 1.0
            h_scale = self.height()/800.0 if self.height() else 1.0
            scale = max(0.55, min(1.75, min(w_scale, h_scale)))
            self.set_scale(scale)
        except Exception:
            pass
    
    def _schedule_web_zoom_update(self):
        try:
            t = getattr(self, "_web_zoom_timer", None)
            if not t:
                self._update_web_zoom()
                return
            t.start(120)
        except Exception:
            pass

    def _update_web_zoom(self):
        try:
            if not hasattr(self, "web_view") or not self.web_view or not self.web_view.isVisible():
                return
            self.web_view.setZoomFactor(1.0)
        except Exception:
            pass

    def _apply_web_zoom_result(self, res, view_w, view_h, fallback):
        try:
            if bool((res or {}).get('didAuto')):
                try:
                    self.web_view.setZoomFactor(1.0)
                except Exception:
                    pass
                return
            cw = int((res or {}).get('w') or 0)
            ch = int((res or {}).get('h') or 0)
            if cw <= 0 or ch <= 0:
                fallback()
                return
            fw = view_w / float(cw)
            fh = view_h / float(ch)
            factor = max(0.5, min(2.5, min(fw, fh)))
            factor = factor * 0.92
            factor = min(1.0, factor)
            self.web_view.setZoomFactor(factor)
        except Exception:
            fallback()

    def set_scale(self, scale: float):
        try:
            if hasattr(self, 'header_title') and self.header_title:
                fs = max(20, int(24 * scale))
                theme = getattr(self, 'theme', 'dark')
                self.header_title.setStyleSheet(
                    f"QLabel{{color:{'#FFFFFF' if theme=='dark' else '#1A1A1A'};font-size:{fs}px;font-weight:700;background:transparent;border:none;padding:0;}}"
                )
            h = max(34, int(42 * scale))
            for btn in [getattr(self, 'back_btn', None), getattr(self, 'open_btn', None), getattr(self, 'reload_btn', None), getattr(self, 'choose_btn', None)]:
                if btn:
                    btn.setFixedHeight(h)
                    bf = btn.font()
                    bf.setPointSize(max(12, int(h*0.36)))
                    btn.setFont(bf)
            if hasattr(self, 'icon_label') and self.icon_label:
                isz = max(48, int(64 * scale))
                self.icon_label.setStyleSheet(f"QLabel{{font-size:{isz}px;margin-bottom:{int(18*scale)}px;}}")
            if hasattr(self, 'welcome_title') and self.welcome_title:
                tsz = max(24, int(32 * scale))
                theme = getattr(self, 'theme', 'dark')
                self.welcome_title.setStyleSheet(f"QLabel{{color:{'#FFFFFF' if theme=='dark' else '#1A1A1A'};font-size:{tsz}px;font-weight:700;margin-bottom:{int(10*scale)}px;}}")
            if hasattr(self, 'welcome_desc') and self.welcome_desc:
                dsz = max(14, int(16 * scale))
                dcolor = "#A0AEC0" if getattr(self, "theme", "dark") == "dark" else "#475467"
                self.welcome_desc.setStyleSheet(f"QLabel{{color:{dcolor};font-size:{dsz}px;margin-bottom:{int(20*scale)}px;}}")
            if hasattr(self, 'instructions_label') and self.instructions_label:
                isz = max(12, int(14 * scale))
                icolor = "#A0AEC0" if getattr(self, "theme", "dark") == "dark" else "#475467"
                self.instructions_label.setStyleSheet(f"QLabel{{color:{icolor};font-size:{isz}px;margin-top:{int(20*scale)}px;}}")
            if hasattr(self, "project_combo") and self.project_combo:
                self.project_combo.setFixedHeight(max(40, int(46 * scale)))
            if hasattr(self, "section_title") and self.section_title:
                tf = self.section_title.font()
                tf.setPointSize(max(16, int(22 * scale)))
                self.section_title.setFont(tf)
                _sc = "#E2E8F0" if getattr(self, "theme", "dark") == "dark" else "#0F1728"
                self.section_title.setStyleSheet(
                    f"QLabel#player-section-title{{color:{_sc};font-size:{max(20, int(28 * scale))}px;font-weight:700;padding:4px 2px;background:transparent;border:none;}}"
                )
            if hasattr(self, "project_scroll") and self.project_scroll:
                self.project_scroll.setMinimumHeight(max(340, int(420 * scale)))
            cols = self._card_columns()
            if cols != self._last_card_cols:
                self._render_project_cards(self._project_rows)
                self._set_selected_project(self._selected_project_meta)
        except Exception:
            pass
    
    def load_project_game(self, project_data):
        """Load game from project data"""
        try:
            # Import project manager
            from eduplay.core.project_manager import ProjectManager
            
            if not self.project_manager:
                self.project_manager = ProjectManager()
            
            # Get project path
            project_id = project_data.get("id", "")
            project_dir = PathResolver.resolve_projects_dir() / project_id
            
            # Look for exported game files
            export_dir = project_dir / "export"
            if export_dir.exists():
                # Check for HTML export first
                html_export = export_dir / "html"
                if html_export.exists():
                    index_file = html_export / "index.html"
                    if index_file.exists():
                        self.load_html_game(str(index_file))
                        return
                # Support single-file HTML exports directly under export dir
                try:
                    single_files = sorted(export_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
                except Exception:
                    single_files = []
                for sf in single_files:
                    try:
                        content = sf.read_text(encoding="utf-8", errors="ignore")
                        if any(m in content for m in ["const gameData", '"game_type": "fishing"', "quiz-root"]):
                            self.load_html_game(str(sf))
                            return
                    except Exception:
                        continue
                
                # Check for Python export
                python_export = export_dir / "python"
                if python_export.exists():
                    game_file = python_export / "game.py"
                    if game_file.exists():
                        self.load_python_game(str(game_file))
                        return
            
            # If no export found, show message
            QMessageBox.information(
                self,
                "Chưa xuất bản",
                "Dự án này chưa được xuất bản. Vui lòng xuất bản dự án trước khi chơi."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi tải game",
                f"Không thể tải game từ dự án:\n{str(e)}"
            )
    
    def load_from_project(self):
        """Load game from existing project"""
        try:
            # Import project manager
            from eduplay.core.project_manager import ProjectManager
            
            if not self.project_manager:
                self.project_manager = ProjectManager()
            
            # Get all projects
            projects = self.project_manager.get_all_projects()
            
            if not projects:
                QMessageBox.information(
                    self,
                    "Không có dự án",
                    "Chưa có dự án nào được tạo. Vui lòng tạo dự án trước."
                )
                return
            
            # For now, load the most recent project
            # In a full implementation, this would show a project selection dialog
            latest_project = max(projects, key=lambda p: p.get("modified_at", ""))
            self.load_project_game(latest_project)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Lỗi tải dự án",
                f"Không thể tải dự án:\n{str(e)}"
            )
    
    def apply_theme(self, theme: str | None = None):
        """Apply theme to player screen"""
        try:
            from eduplay.core.settings_manager import SettingsManager
            current_theme = theme or (SettingsManager().get_theme() or "dark")
        except Exception:
            current_theme = "dark"
            
        if current_theme == "dark":
            text_color = "#A0AEC0"
            title_color = "#FFFFFF"
            header_bg = "rgba(27,31,42,0.65)"
            header_border = "#2A2F3A"
        else:
            text_color = "#475467"
            title_color = "#1A1A1A"
            header_bg = "#E6F7FF"
            header_border = "#93C5FD"
            
        try:
            # Update header
            header = self.findChild(QFrame, "header")
            if header:
                header.setStyleSheet(f"QFrame#header{{ background-color: {header_bg}; border-bottom: 1px solid {header_border}; }}")
                
            # Update header title
            if hasattr(self, 'header_title'):
                current_font_size = self.header_title.font().pointSize()
                if current_font_size < 1: current_font_size = 24
                # Use current font size if possible or default
                # But QSS might override font size if we set it.
                # Let's try to keep font size dynamic or just set color if possible?
                # QSS: "color: ..."
                # If we re-set the whole sheet we might lose scale.
                # But set_scale also sets stylesheet.
                # Let's just set color and font size (assuming standard or scaled).
                # To be safe, let's just re-call set_scale if we can, or just set color.
                # But set_scale uses self.theme. We should update self.theme first.
                pass

            self.theme = current_theme
            
            if hasattr(self, 'header_title'):
                # We can rely on set_scale to update the style if we call it, 
                # or we can manually update here.
                # Let's manually update to be sure.
                # We need to respect the current scale if possible.
                # But we don't know the current scale easily without storing it.
                # However, set_scale reads self.theme.
                # So if we updated self.theme, maybe we can just trigger a resize or re-apply style.
                # Let's just update the color for now.
                self.header_title.setStyleSheet(f"""
                    QLabel {{
                        color: {title_color};
                        font-size: 24px;
                        font-weight: 700;
                    }}
                """)

            if hasattr(self, 'welcome_title') and self.welcome_title:
                 self.welcome_title.setStyleSheet(f"""
                    QLabel {{
                        color: {title_color};
                        font-size: 32px;
                        font-weight: 700;
                        margin-bottom: 10px;
                    }}
                """)

            if hasattr(self, 'welcome_desc') and self.welcome_desc:
                self.welcome_desc.setStyleSheet(f"""
                    QLabel {{
                        color: {text_color};
                        font-size: 16px;
                        margin-bottom: 30px;
                    }}
                """)
                
            if hasattr(self, 'instructions_label') and self.instructions_label:
                self.instructions_label.setStyleSheet(f"""
                    QLabel {{
                        color: {text_color};
                        font-size: 14px;
                        margin-top: 20px;
                    }}
                """)
            self._apply_project_selector_theme(current_theme)
            if hasattr(self, "section_title") and self.section_title:
                sec = "#E5E7EB" if current_theme == "dark" else "#0F1728"
                self.section_title.setStyleSheet(
                    f"QLabel#player-section-title{{color:{sec};font-size:42px;font-weight:700;padding:4px 2px;background:transparent;border:none;}}"
                )
            self._update_project_selection_state()
                
            # Re-apply scale if possible to fix sizes
            try:
                w_scale = self.width()/1200.0 if self.width() else 1.0
                h_scale = self.height()/800.0 if self.height() else 1.0
                scale = max(0.55, min(1.75, min(w_scale, h_scale)))
                self.set_scale(scale)
            except Exception:
                pass
                
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self.refresh_project_previews()
            self._apply_project_selector_theme(getattr(self, "theme", "dark"))
        except Exception:
            pass

    def show_welcome_panel(self):
        """Show welcome panel and hide game"""
        self.welcome_panel.setVisible(True)
        self.web_view.setVisible(False)
        self.current_game_path = None
        self.setWindowTitle(self._t("title.player", "EduPlay Studio - Chơi game"))

    def set_language(self, lang: str):
        try:
            self.language = lang or "en"
            if hasattr(self, "back_btn"):
                self.back_btn.setText(strip_icon_text(self._t("player.back", "← Quay lại")))
            if hasattr(self, "header_title"):
                self.header_title.setText(self._t("player.title", "Chơi Game"))
            if self.open_file_btn:
                self.open_file_btn.setText(self._t("player.project_list_btn", "Danh sách dự án"))
            if hasattr(self, "welcome_title") and self.welcome_title:
                self.welcome_title.setText(self._t("player.ready_title", "Sẵn sàng chơi game!"))
            if hasattr(self, "welcome_desc") and self.welcome_desc:
                self.welcome_desc.setText(
                    self._t("player.ready_desc_project_list", "Chọn dự án trong danh sách để mở preview tự động.")
                )
            if self.instructions_label:
                self.instructions_label.setText(
                    self._t(
                        "player.instructions_project_list",
                        "Chọn dự án, hệ thống tự dùng file *_preview.html trong thư mục dự án.",
                    )
                )
            if hasattr(self, "section_title") and self.section_title:
                self.section_title.setText(self._t("browser.my_projects", "Dự án của tôi"))
            self._render_project_cards(self._project_rows)
            self._set_selected_project(self._selected_project_meta)
            self._update_project_selection_state()
        except Exception:
            pass

