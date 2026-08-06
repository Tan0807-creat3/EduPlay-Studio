"""
Browser Screen - Screen for browsing and managing projects
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QPushButton, QLabel, QFrame, QScrollArea,
                               QMessageBox, QFileDialog, QLineEdit, QSizePolicy, QMenu, QGraphicsDropShadowEffect, QListView)
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap
from pathlib import Path
from datetime import datetime
import os
import json

from eduplay.ui.icon_factory import build_app_action_icon, build_line_icon, strip_icon_text
from eduplay.core.path_resolver import PathResolver

class ProjectCard(QFrame):
    """Custom widget for project cards"""
    clicked = Signal(dict)
    rename = Signal(dict)
    duplicate = Signal(dict)
    edit_tags = Signal(dict)
    delete = Signal(dict)
    
    def __init__(self, project_data, parent=None):
        super().__init__(parent)
        self.project_data = project_data
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()
    
    def init_ui(self):
        """Initialize the card UI"""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setMinimumSize(240, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("project-card")
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # Project name
        name = self.project_data.get("name", "")
        if not name:
            try:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or 'en'
                name = I18n.t('browser.untitled', lang) if I18n else "Untitled"
            except Exception:
                name = "Untitled"
                
        self.name_label = QLabel(name)
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)
        
        # Project description
        desc = self.project_data.get("description", "")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        
        self.desc_label = QLabel(desc)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        tags = [str(tag).strip() for tag in (self.project_data.get("tags") or []) if str(tag or "").strip()]
        self.tags_label = QLabel("  ".join(f"#{tag}" for tag in tags[:4]))
        self.tags_label.setWordWrap(True)
        self.tags_label.setVisible(bool(tags))
        layout.addWidget(self.tags_label)
        
        layout.addStretch()
        
        # Project info
        info_layout = QHBoxLayout()
        
        # Game type
        game_type = self.project_data.get("game_type", "quiz_classic")
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            lang = SettingsManager().get_language() or 'en'
            mapping = {
                "quiz_classic": "new.type_quiz",
                "quiz_fishing": "new.type_fishing",
                "fishing": "new.type_fishing",
                "quiz_millionaire": "new.type_millionaire",
                "quiz_adventure": "new.type_adventure",
                "quiz_platformer": "new.type_platformer",
            }
            key = mapping.get(game_type, "")
            game_type_text = I18n.t(key, lang) if (I18n and key) else game_type.replace("_", " ").title()
        except Exception:
            game_type_text = game_type.replace("_", " ").title()
            
        self.game_type_label = QLabel(f"🎮 {game_type_text}")
        info_layout.addWidget(self.game_type_label)
        
        info_layout.addStretch()
        
        # Modified date
        modified = self.project_data.get("modified_at", "")
        if modified:
            try:
                mod_date = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                date_str = mod_date.strftime("%d/%m/%Y")
            except:
                date_str = modified[:10]
        else:
            try:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or 'en'
                date_str = I18n.t('browser.date_unknown', lang)
            except Exception:
                date_str = "Unknown"
        
        self.date_label = QLabel(f"📅 {date_str}")
        info_layout.addWidget(self.date_label)
        
        layout.addLayout(info_layout)

        # Open button
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            lang = SettingsManager().get_language() or 'en'
            btn_text = I18n.t('browser.open', lang) if I18n else "Open"
        except Exception:
            btn_text = "Open"
            
        self.open_btn = QPushButton(btn_text)
        self.open_btn.clicked.connect(lambda: self.clicked.emit(self.project_data))
        try:
            self.open_btn.setProperty("primary", True)
        except Exception:
            pass
            
        # Actions row
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.open_btn)
        
        try:
            rename_text = I18n.t('browser.rename', lang) if I18n else "Rename"
            delete_text = I18n.t('browser.delete', lang) if I18n else "Delete"
        except Exception:
            rename_text = "Rename"
            delete_text = "Delete"
            
        self.rename_btn = QPushButton(rename_text)
        self.rename_btn.clicked.connect(lambda: self.rename.emit(self.project_data))
        actions.addWidget(self.rename_btn)
        
        self.del_btn = QPushButton(delete_text)
        self.del_btn.clicked.connect(lambda: self.delete.emit(self.project_data))
        actions.addWidget(self.del_btn)
        
        self.menu_btn = QPushButton("⋯")
        self.menu_btn.setVisible(False)
        
        self.menu = QMenu(self)
        act_rename = QAction(rename_text, self)
        try:
            duplicate_text = I18n.t('browser.duplicate', lang) if I18n else "Duplicate"
            edit_tags_text = I18n.t('browser.edit_tags', lang) if I18n else "Tags"
        except Exception:
            duplicate_text = "Duplicate"
            edit_tags_text = "Tags"
        act_duplicate = QAction(duplicate_text, self)
        act_tags = QAction(edit_tags_text, self)
        act_delete = QAction(delete_text, self)
        act_rename.triggered.connect(lambda: self.rename.emit(self.project_data))
        act_duplicate.triggered.connect(lambda: self.duplicate.emit(self.project_data))
        act_tags.triggered.connect(lambda: self.edit_tags.emit(self.project_data))
        act_delete.triggered.connect(lambda: self.delete.emit(self.project_data))
        self.menu.addAction(act_rename)
        self.menu.addAction(act_duplicate)
        self.menu.addAction(act_tags)
        self.menu.addAction(act_delete)
        self.menu_btn.setMenu(self.menu)
        actions.addWidget(self.menu_btn)
        
        layout.addLayout(actions)
        
        # Apply initial theme
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or 'dark'
            self.apply_theme(theme)
        except Exception:
            self.apply_theme('dark')

    def apply_theme(self, theme: str):
        """Apply theme to project card"""
        if theme == 'dark':
            card_bg = "#2D2F3A"
            card_border = "#4A4E5A"
            card_hover_bg = "#3A3C47"
            card_hover_border = "#7F56D9"
            name_color = "#FFFFFF"
            desc_color = "#A0AEC0"
            meta_color = "#A0AEC0"
            rename_bg = "#3A3A40"
            rename_fg = "#FFFFFF"
            rename_hover_bg = "#4A4A50"
            menu_bg = "#111827"
            menu_border = "#4A4E5A"
            menu_fg = "#E5E7EB"
        else:
            card_bg = "#FFFFFF"
            card_border = "#E2E8F0"
            card_hover_bg = "#F8FAFC"
            card_hover_border = "#7F56D9"
            name_color = "#0F1728"
            desc_color = "#4B5563"
            meta_color = "#667085"
            rename_bg = "#E5E7EB"
            rename_fg = "#111827"
            rename_hover_bg = "#D4D4D8"
            menu_bg = "#FFFFFF"
            menu_border = "#E2E8F0"
            menu_fg = "#111827"
            
        self.setStyleSheet(f"""
            #project-card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 12px;
            }}
            #project-card:hover {{
                background-color: {card_hover_bg};
                border-color: {card_hover_border};
            }}
        """)
        
        if hasattr(self, 'name_label'):
            self.name_label.setStyleSheet(f"QLabel {{ color: {name_color}; font-size: 18px; font-weight: 700; }}")
        
        if hasattr(self, 'desc_label'):
            self.desc_label.setStyleSheet(f"QLabel {{ color: {desc_color}; font-size: 14px; }}")

        if hasattr(self, 'tags_label'):
            self.tags_label.setStyleSheet(f"QLabel {{ color: {meta_color}; font-size: 12px; font-weight: 600; }}")
            
        if hasattr(self, 'game_type_label'):
            self.game_type_label.setStyleSheet("QLabel { color: #7F56D9; font-size: 12px; font-weight: 600; }")
            
        if hasattr(self, 'date_label'):
            self.date_label.setStyleSheet(f"QLabel {{ color: {meta_color}; font-size: 12px; }}")
            
        if hasattr(self, 'open_btn'):
            self.open_btn.setStyleSheet("""
                QPushButton {
                    background-color: #7F56D9;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 14px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #6941C6;
                }
            """)
            
        for btn in [getattr(self, 'rename_btn', None), getattr(self, 'del_btn', None), getattr(self, 'menu_btn', None)]:
            if btn:
                if btn == getattr(self, 'del_btn', None):
                     btn.setStyleSheet("QPushButton{background:#F44336;color:#fff;border:none;border-radius:10px;padding:8px 12px;font-size:12px;} QPushButton:hover{background:#D32F2F}")
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {rename_bg};
                            color: {rename_fg};
                            border: none;
                            border-radius: 10px;
                            padding: 8px 12px;
                            font-size: 12px;
                        }}
                        QPushButton:hover {{
                            background-color: {rename_hover_bg};
                        }}
                    """)
                    
        if hasattr(self, 'menu'):
            if theme == 'dark':
                 self.menu.setStyleSheet("""
                    QMenu {
                        background-color: #111827;
                        color: #E5E7EB;
                        border: 1px solid #4A4E5A;
                        padding: 4px 0;
                    }
                    QMenu::item {
                        padding: 6px 20px;
                        background-color: transparent;
                    }
                    QMenu::item:selected {
                        background-color: #7F56D9;
                        color: #FFFFFF;
                    }
                """)
            else:
                self.menu.setStyleSheet("""
                    QMenu {
                        background-color: #FFFFFF;
                        color: #0F1728;
                        border: 1px solid #E2E8F0;
                        padding: 4px 0;
                    }
                    QMenu::item {
                        padding: 6px 20px;
                        background-color: transparent;
                    }
                    QMenu::item:selected {
                        background-color: #7F56D9;
                        color: #FFFFFF;
                    }
                    QMenu::item:disabled {
                        color: #9CA3AF;
                    }
                """)

    def set_scale(self, scale: float):
        try:
            nm = self.findChild(QLabel)
            fsize = max(16, int(18 * scale))
            dsize = max(12, int(14 * scale))
            for w in self.findChildren(QLabel):
                st = w.styleSheet()
                if 'font-size' in st:
                    import re
                    st = re.sub(r"font-size:\s*\d+px;", f"font-size: {dsize}px;", st)
                    w.setStyleSheet(st)
            try:
                self.setMinimumSize(int(240 * scale), int(180 * scale))
            except Exception:
                pass
        except Exception:
            pass

    def enterEvent(self, event):
        super().enterEvent(event)

    def set_compact(self, compact: bool):
        try:
            self.rename_btn.setVisible(not compact)
            self.del_btn.setVisible(not compact)
            self.menu_btn.setVisible(compact)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            small = self.width() < 720
            if hasattr(self, 'rename_btn') and hasattr(self, 'del_btn') and hasattr(self, 'menu_btn'):
                self.rename_btn.setVisible(not small)
                self.del_btn.setVisible(not small)
                self.menu_btn.setVisible(small)
        except Exception:
            pass
    
    def load_thumbnail(self):
        """Load project thumbnail or show default icon"""
        # Try to find project thumbnail
        project_id = self.project_data.get("id", "")
        if project_id:
            # Look for thumbnail in project directory
            project_dir = PathResolver.resolve_projects_dir() / project_id
            thumbnail_path = project_dir / "thumbnail.png"
            
            if thumbnail_path.exists():
                pixmap = QPixmap(str(thumbnail_path))
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(280, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    thumbnail_label = QLabel()
                    thumbnail_label.setPixmap(scaled_pixmap)
                    thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    return thumbnail_label
        
        # Default icon based on game type
        game_type = self.project_data.get("game_type", "quiz_classic")
        default_icons = {
            "quiz_classic": "📝",
            "quiz_fishing": "🎣",
            "fishing": "🎣",
            "quiz_adventure": "🗡️",
            "quiz_platformer": "🏃"
        }
        
        icon_text = default_icons.get(game_type, "🎮")
        default_label = QLabel(icon_text)
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            theme = 'dark'
        icon_color = "#4A4E5A" if theme == "dark" else "#94A3B8"
        default_label.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                color: {icon_color};
            }}
        """)
        default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return default_label
    
    def mouseReleaseEvent(self, event):
        """Emit clicked when released inside card"""
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                self.clicked.emit(self.project_data)
        except Exception:
            pass

class BrowserScreen(QWidget):
    """Screen for browsing and managing projects"""
    
    # Signals
    project_selected = Signal(dict)
    back_clicked = Signal()
    create_new_clicked = Signal()
    
    def __init__(self):
        super().__init__()
        self.project_manager = None  # Will be set when screen is shown
        self.all_projects = []  # Store all projects for filtering
        self._filtered_projects = []  # cache current filtered list
        self._recent_project_ids = []
        self._last_cols = 0
        self._stable_scale = None
        self._requested_scale = 1.0
        self._current_theme = "dark"
        self.init_ui()
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or "dark"
        except Exception:
            theme = "dark"
        try:
            self.apply_theme(theme)
        except Exception:
            pass

    def _show_message(self, title: str, message: str, level: str = "info"):
        try:
            win = self.window()
            if win and hasattr(win, "_show_message"):
                win._show_message(title, message, level)
                return
        except Exception:
            pass

        from PySide6.QtCore import QTimer
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or "dark"
        except Exception:
            theme = "dark"

        box = QMessageBox(self)
        if str(theme).lower() == "dark":
            box.setStyleSheet(
                """
                QMessageBox { background-color: #0F172A; color: #E5E7EB; }
                QMessageBox QLabel { color: #E5E7EB; background: transparent; }
                QMessageBox QPushButton {
                    background-color: #111827;
                    color: #E5E7EB;
                    border: 1px solid #374151;
                    border-radius: 10px;
                    padding: 8px 14px;
                    min-width: 96px;
                }
                QMessageBox QPushButton:hover { background-color: #1F2937; color: #FFFFFF; border-color: #4B5563; }
                QMessageBox QPushButton:default { background-color: #7F56D9; border-color: #7F56D9; color: #FFFFFF; }
                """
            )
        else:
            box.setStyleSheet(
                """
                QMessageBox { background-color: #FFFFFF; color: #111827; }
                QMessageBox QLabel { color: #1F2937; background: transparent; }
                QMessageBox QPushButton {
                    background-color: #F3F4F6;
                    color: #111827;
                    border: 1px solid #D0D5DD;
                    border-radius: 10px;
                    padding: 8px 14px;
                    min-width: 96px;
                }
                QMessageBox QPushButton:hover { background-color: #E5E7EB; color: #111827; border-color: #9CA3AF; }
                QMessageBox QPushButton:default { background-color: #7F56D9; border-color: #7F56D9; color: #FFFFFF; }
                """
            )
        box.setWindowTitle(title)
        box.setText(message)
        severity = (level or "").lower()
        if severity == "error":
            box.setIcon(QMessageBox.Critical)
        elif severity == "warning":
            box.setIcon(QMessageBox.Warning)
        elif severity == "success":
            box.setIcon(QMessageBox.Information)
        else:
            box.setIcon(QMessageBox.Information)
        try:
            box.setWindowModality(Qt.NonModal)
            box.show()
            if severity in ("success", "info", ""):
                QTimer.singleShot(2500, box.close)
        except Exception:
            try:
                box.exec()
            except Exception:
                pass

    def _set_button_icon(self, btn: QPushButton, kind: str, color_hex: str, size: int = 16):
        try:
            if kind == "import":
                btn.setIcon(build_app_action_icon("import", btn.style(), size=size))
                btn.setIconSize(QSize(size, size))
                return
            stroke = 1.5 if kind == "import" else 2
            btn.setIcon(build_line_icon(kind, color_hex, size, stroke_width=stroke))
            btn.setIconSize(QSize(size, size))
        except Exception:
            pass

    def _effective_scale(self) -> float:
        try:
            if self._stable_scale is not None:
                return float(self._stable_scale)
        except Exception:
            pass
        try:
            return float(self._requested_scale)
        except Exception:
            return 1.0

    def _title_color(self) -> str:
        return "#E2E8F0" if str(getattr(self, "_current_theme", "dark")).lower() == "dark" else "#0F1728"

    def _apply_title_style(self, scale: float | None = None):
        if not hasattr(self, "title_label"):
            return
        effective_scale = scale if scale is not None else self._effective_scale()
        title_size = max(20, int(round(24 * float(effective_scale))))
        self.title_label.setStyleSheet(
            f"""
            QLabel {{
                color: {self._title_color()};
                font-size: {title_size}px;
                font-weight: 700;
                background: transparent;
            }}
            """
        )

    def _apply_header_scale(self, scale: float | None = None):
        effective_scale = scale if scale is not None else self._effective_scale()
        self._apply_title_style(effective_scale)
        button_height = max(40, int(round(48 * float(effective_scale))))
        button_font_size = max(11, int(round(button_height * 0.36)))
        for btn in [getattr(self, "back_btn", None), getattr(self, "import_btn", None), getattr(self, "refresh_btn", None)]:
            if not btn:
                continue
            btn.setFixedHeight(button_height)
            font = btn.font()
            font.setPointSize(button_font_size)
            btn.setFont(font)
        if hasattr(self, "search_input"):
            self.search_input.setFixedHeight(button_height)
        for combo_name in ("recent_combo", "filter_combo"):
            combo = getattr(self, combo_name, None)
            try:
                if combo and hasattr(combo, "button"):
                    combo.button.setFixedHeight(button_height)
            except Exception:
                pass

    def apply_theme(self, theme: str | None = None):
        try:
            from eduplay.core.settings_manager import SettingsManager
            current_theme = theme or (SettingsManager().get_theme() or "dark")
        except Exception:
            current_theme = "dark"
        self._current_theme = current_theme
        try:
            for combo_name in ("recent_combo", "filter_combo"):
                combo = getattr(self, combo_name, None)
                if not combo:
                    continue
                if current_theme == "dark":
                    combo.button.setStyleSheet(
                        """
                        QToolButton {
                            background-color: #111827;
                            color: #E5E7EB;
                            border: 1px solid #4A4E5A;
                            border-radius: 8px;
                            padding: 8px 12px;
                            min-width: 160px;
                            text-align: left;
                        }
                        QToolButton::menu-indicator {
                            image: none;
                        }
                        """
                    )
                    combo.popup.setStyleSheet(
                        """
                        QFrame#FlatDropdownPopup {
                            background-color: #111827;
                            border: 1px solid #4A4E5A;
                            border-radius: 0px 0px 8px 8px;
                        }
                        QListView {
                            background-color: transparent;
                            color: #E5E7EB;
                            border: none;
                            padding: 0px;
                        }
                        QListView::item {
                            padding: 6px 12px;
                            margin: 0px;
                        }
                        QListView::item:selected {
                            background-color: #7F56D9;
                            color: #FFFFFF;
                        }
                        QListView::item:hover:!selected {
                            background-color: #1F2933;
                        }
                        """
                    )
                else:
                    combo.button.setStyleSheet(
                        """
                        QToolButton {
                            background-color: #FFFFFF;
                            color: #0F1728;
                            border: 1px solid #D0D5DD;
                            border-radius: 10px;
                            padding: 8px 12px;
                            min-width: 160px;
                            text-align: left;
                        }
                        QToolButton::menu-indicator {
                            image: none;
                        }
                        """
                    )
                    combo.popup.setStyleSheet(
                        """
                        QFrame#FlatDropdownPopup {
                            background-color: #F9FAFF;
                            border: 1px solid #D0D5DD;
                            border-radius: 0px 0px 10px 10px;
                        }
                        QListView {
                            background-color: transparent;
                            color: #0F1728;
                            border: none;
                            padding: 0px;
                        }
                        QListView::item {
                            padding: 6px 12px;
                            margin: 0px;
                        }
                        QListView::item:selected {
                            background-color: #7F56D9;
                            color: #FFFFFF;
                        }
                        QListView::item:hover:!selected {
                            background-color: #E0EAFF;
                        }
                        """
                    )
        except Exception:
            pass

        # Update other components
        try:
            if hasattr(self, 'back_btn'):
                if current_theme == 'dark':
                    self.back_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            color: #A0AEC0;
                            border: 1px solid #4A4E5A;
                            border-radius: 8px;
                            padding: 10px 20px;
                            font-size: 14px;
                            font-weight: 600;
                        }
                        QPushButton:hover {
                            background-color: #3A3C47;
                            color: #FFFFFF;
                            border-color: #5A5E6A;
                        }
                    """)
                else:
                    self.back_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            color: #4B5563;
                            border: 1px solid #D0D5DD;
                            border-radius: 8px;
                            padding: 10px 20px;
                            font-size: 14px;
                            font-weight: 600;
                        }
                        QPushButton:hover {
                            background-color: #F3F4F6;
                            color: #111827;
                            border-color: #9CA3AF;
                        }
                    """)
            
            if hasattr(self, 'search_label'):
                color = "#A0AEC0" if current_theme == 'dark' else "#64748B"
                self.search_label.setStyleSheet(f"""
                    QLabel {{
                        color: {color};
                        font-size: 16px;
                    }}
                """)

            if hasattr(self, 'title_label'):
                self._apply_title_style()
                
            if hasattr(self, 'projects_grid'):
                for i in range(self.projects_grid.count()):
                    item = self.projects_grid.itemAt(i)
                    if item and item.widget() and hasattr(item.widget(), 'apply_theme'):
                        item.widget().apply_theme(current_theme)
        except Exception:
            pass
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create header
        self.create_header(layout)
        
        # Create content area
        self.create_content_area(layout)
        
        self.setLayout(layout)
        
        # Styling handled by global theme QSS
    
    def create_header(self, layout):
        """Create header with navigation and actions"""
        header = QFrame()
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 10, 24, 10)
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            lang = SettingsManager().get_language() or 'en'
        except Exception:
            I18n = None
            lang = 'en'
        
        # Back button
        try:
            if I18n:
                back_text = I18n.t('browser.back', lang)
            else:
                back_text = "← Back"
        except Exception:
            back_text = "← Back"
        self.back_btn = QPushButton(strip_icon_text(back_text))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #A0AEC0;
                border: 1px solid #4A4E5A;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3A3C47;
                color: #FFFFFF;
                border-color: #5A5E6A;
            }
        """)
        try:
            self.back_btn.setProperty("secondary", True)
        except Exception:
            pass
        self._set_button_icon(self.back_btn, "back", "#A0AEC0", 16)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(self.back_btn, 0)  # fixed, no stretch

        header_layout.addStretch(1)

        # Center: title + search/filter stacked vertically
        center_layout = QVBoxLayout()
        center_layout.setSpacing(6)
        center_layout.setContentsMargins(0, 0, 0, 0)

        # Title centered
        try:
            if I18n:
                title_text = I18n.t('browser.my_projects', lang)
            else:
                title_text = "My Projects"
        except Exception:
            title_text = "My Projects"
        self.title_label = QLabel(title_text)
        self.title_label.setAlignment(Qt.AlignCenter)
        self._apply_title_style()
        center_layout.addWidget(self.title_label)

        # Search + filter row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        search_layout.setContentsMargins(0, 0, 0, 0)

        self.search_label = QLabel("🔍")
        self.search_label.setStyleSheet("QLabel { color: #A0AEC0; font-size: 16px; }")
        search_layout.addWidget(self.search_label)

        self.search_input = QLineEdit()
        try:
            if I18n:
                self.search_input.setPlaceholderText(I18n.t('browser.search_placeholder', lang))
            else:
                self.search_input.setPlaceholderText("Search projects...")
        except Exception:
            self.search_input.setPlaceholderText("Search projects...")
        self.search_input.setStyleSheet("")
        self.search_input.setMinimumWidth(160)
        self.search_input.setMaximumWidth(280)
        self.search_input.textChanged.connect(self.filter_projects)
        search_layout.addWidget(self.search_input)

        from eduplay.ui.widgets.custom_dropdown import FlatDropdown
        self.recent_combo = FlatDropdown()
        self.filter_combo = FlatDropdown()
        self._populate_filter_controls(lang)
        self.recent_combo.currentTextChanged.connect(self.filter_projects)
        self.filter_combo.currentTextChanged.connect(self.filter_projects)
        search_layout.addWidget(self.recent_combo)
        search_layout.addWidget(self.filter_combo)

        center_layout.addLayout(search_layout)
        header_layout.addLayout(center_layout)

        header_layout.addStretch(1)
        
        # Action buttons
        try:
            if I18n:
                import_text = I18n.t('browser.import', lang)
            else:
                import_text = "📁 Import"
        except Exception:
            import_text = "📁 Import"
        self.import_btn = QPushButton(strip_icon_text(import_text))
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                margin-right: 10px;
            }
            QPushButton:hover {
                background-color: #8B66E9;
            }
        """)
        try:
            self.import_btn.setProperty("primary", True)
        except Exception:
            pass
        self._set_button_icon(self.import_btn, "import", "#FFFFFF", 16)
        self.import_btn.clicked.connect(self.import_project)
        header_layout.addWidget(self.import_btn)
        
        try:
            if I18n:
                refresh_text = I18n.t('browser.refresh', lang)
            else:
                refresh_text = "🔄 Refresh"
        except Exception:
            refresh_text = "🔄 Refresh"
        self.refresh_btn = QPushButton(strip_icon_text(refresh_text))
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #12B76A;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #22C77A;
            }
        """)
        try:
            self.refresh_btn.setProperty("success", True)
        except Exception:
            pass
        self._set_button_icon(self.refresh_btn, "refresh", "#FFFFFF", 16)
        self.refresh_btn.clicked.connect(self.refresh_projects)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(header)
        self._apply_header_scale()
    
    def create_content_area(self, layout):
        """Create content area with project grid"""
        # Scroll area for projects
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea{background:transparent;} QScrollArea > QWidget > QWidget{background:transparent;} QScrollArea > QWidget{background:transparent;}")
        
        # Container for scroll area
        container = QWidget()
        try:
            container.setStyleSheet("background:transparent;")
        except Exception:
            pass
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(40, 40, 40, 40)
        self.content_layout.setSpacing(30)
        
        # Projects grid
        self.projects_grid = QGridLayout()
        self.projects_grid.setSpacing(20)
        self.content_layout.addLayout(self.projects_grid)
        
        # Add stretch to push content to top
        self.content_layout.addStretch()
        
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)
        
        # Load projects
        self.load_projects()
    
    def load_projects(self):
        """Load and display projects"""
        # Clear existing projects
        self.clear_projects_grid()
        
        # Import project manager here to avoid circular imports
        from eduplay.core.project_manager import ProjectManager
        
        if not self.project_manager:
            self.project_manager = ProjectManager()
        
        # Get all projects
        self.all_projects = self.project_manager.get_all_projects()
        try:
            from eduplay.core.settings_manager import SettingsManager
            recent = SettingsManager().get_recent_projects() or []
            self._recent_project_ids = [
                str(item.get("id") or "").strip()
                for item in recent
                if isinstance(item, dict) and str(item.get("id") or "").strip()
            ]
        except Exception:
            self._recent_project_ids = []
        self._populate_filter_controls(self._current_lang())
        
        # Apply filters
        self.filter_projects()

    def _current_lang(self) -> str:
        try:
            from eduplay.core.settings_manager import SettingsManager
            return SettingsManager().get_language() or "en"
        except Exception:
            return "en"

    def _populate_filter_controls(self, lang: str | None = None):
        l = lang or self._current_lang()
        try:
            from eduplay.core.i18n import I18n
        except Exception:
            I18n = None

        recent_value = self.recent_combo.currentData() if hasattr(self, "recent_combo") else "all"
        template_value = self.filter_combo.currentData() if hasattr(self, "filter_combo") else "all"

        recent_items = [
            (I18n.t("browser.scope_all", l) if I18n else "All projects", "all"),
            (I18n.t("browser.scope_recent", l) if I18n else "Recent", "recent"),
        ]
        template_items = [
            (I18n.t("browser.filter_all", l) if I18n else "All", "all"),
            (I18n.t("browser.filter_quiz", l) if I18n else "Quiz", "quiz_classic"),
            (I18n.t("browser.filter_millionaire", l) if I18n else "Millionaire", "quiz_millionaire"),
            (I18n.t("browser.filter_fishing", l) if I18n else "Fishing", "fishing"),
        ]

        for combo, items, current in (
            (getattr(self, "recent_combo", None), recent_items, recent_value),
            (getattr(self, "filter_combo", None), template_items, template_value),
        ):
            if not combo:
                continue
            combo.clear()
            selected_index = 0
            for idx, (label, data) in enumerate(items):
                combo.addItem(label, data)
                if str(data or "") == str(current or ""):
                    selected_index = idx
            combo.setCurrentIndex(selected_index)
    
    def filter_projects(self):
        """Filter projects based on search and game type"""
        overlay_owner = None
        try:
            from PySide6.QtWidgets import QApplication
            win = QApplication.activeWindow()
            if win and hasattr(win, "_show_loading"):
                overlay_owner = win
                try:
                    from eduplay.core.i18n import I18n
                    from eduplay.core.settings_manager import SettingsManager
                    lang = SettingsManager().get_language() or 'en'
                except Exception:
                    lang = 'en'
                try:
                    msg = I18n.t('browser.search_loading', lang)
                except Exception:
                    msg = "Đang lọc dự án..." if lang == 'vi' else "Filtering projects..."
                try:
                    win._show_loading(msg, "search")
                except Exception:
                    overlay_owner = None
        except Exception:
            overlay_owner = None
        try:
            # Clear existing projects
            self.clear_projects_grid()
            
            # Get filter criteria
            search_text = self.search_input.text().lower() if hasattr(self, 'search_input') else ""
            template_filter = self.filter_combo.currentData() if hasattr(self, "filter_combo") else "all"
            recent_only = (self.recent_combo.currentData() if hasattr(self, "recent_combo") else "all") == "recent"

            filtered_projects = self.project_manager.filter_projects(
                self.all_projects,
                search_text=search_text,
                template_filter=str(template_filter or "all"),
                tag_filter="all",
                recent_only=bool(recent_only),
                recent_project_ids=self._recent_project_ids,
            )
            
            if not filtered_projects:
                self._filtered_projects = []
                self.render_project_cards()
                return
            self._filtered_projects = filtered_projects
            self.render_project_cards()
        finally:
            if overlay_owner:
                try:
                    overlay_owner._hide_loading()
                except Exception:
                    pass

    def get_max_columns(self) -> int:
        try:
            w = self.width()
        except Exception:
            w = 1200
        if w < 720:
            return 1
        if w < 1024:
            return 2
        if w < 1366:
            return 3
        return 4

    def render_project_cards(self):
        self.clear_projects_grid()
        max_cols = self.get_max_columns()
        self._last_cols = max_cols
        if not self._filtered_projects:
            self.show_empty_state()
            return
        row = 0
        col = 0
        for project in self._filtered_projects:
            card = ProjectCard(project, self)
            try:
                card.clicked.connect(self.on_project_clicked)
                card.rename.connect(self.on_project_rename)
                card.duplicate.connect(self.on_project_duplicate)
                card.edit_tags.connect(self.on_project_edit_tags)
                card.delete.connect(self.on_project_delete)
                card.set_compact(self.width() < 720)
            except Exception:
                pass
            self.projects_grid.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def show_empty_state(self):
        """Show empty state when no projects exist"""
        self.clear_projects_grid()
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(20)
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 64px;
                color: #4A4E5A;
            }
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon_label)
        try:
            from eduplay.core.i18n import I18n
            lang = self._current_lang()
            empty_title = I18n.t("browser.empty_title", lang)
            empty_desc = I18n.t("browser.empty_desc", lang)
            empty_cta = I18n.t("browser.empty_cta", lang)
        except Exception:
            empty_title = "No projects yet"
            empty_desc = "Create your first project to get started"
            empty_cta = "Create new project"
        message_label = QLabel(empty_title)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 700;
                color: #A0AEC0;
            }
        """)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(message_label)
        submessage_label = QLabel(empty_desc)
        submessage_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #A0AEC0;
            }
        """)
        submessage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(submessage_label)
        create_btn = QPushButton(empty_cta)
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: 600;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #8B66E9;
            }
        """)
        try:
            create_btn.setProperty("primary", True)
        except Exception:
            pass
        create_btn.clicked.connect(self.create_new_project)
        empty_layout.addWidget(create_btn)
        self._empty_message_label = message_label
        self._empty_submessage_label = submessage_label
        self._empty_create_btn = create_btn
        span = self.get_max_columns()
        self.projects_grid.addWidget(empty_widget, 0, 0, 1, span, Qt.AlignmentFlag.AlignCenter)
    
    def clear_projects_grid(self):
        """Clear all projects from the grid"""
        while self.projects_grid.count():
            item = self.projects_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def on_project_clicked(self, project_data):
        """Handle project card click"""
        self.project_selected.emit(project_data)
    
    def create_new_project(self):
        """Create new project"""
        self.create_new_clicked.emit()
    
    def refresh_projects(self):
        """Refresh projects list"""
        self.load_projects()

    def on_project_rename(self, project_data: dict):
        try:
            try:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or 'en'
                title = I18n.t('browser.rename_project_title', lang)
                label = I18n.t('browser.rename_project_prompt', lang)
                success_title = I18n.t('browser.success_title', lang)
                success_msg = I18n.t('browser.rename_project_success', lang)
                error_title = I18n.t('browser.error', lang)
                error_msg = I18n.t('browser.rename_project_failed', lang)
            except Exception:
                title = "Rename Project"
                label = "New name:"
                success_title = "Success"
                success_msg = "Project renamed successfully."
                error_title = "Error"
                error_msg = "Failed to rename project"
            try:
                from eduplay.core.settings_manager import SettingsManager
                theme = SettingsManager().get_theme() or 'dark'
            except Exception:
                theme = 'dark'
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit
            from PySide6.QtCore import Qt
            t = 'dark' if str(theme).lower() == 'dark' else 'light'
            if t == 'dark':
                dlg_bg = "#0B0E14"
                dlg_border = "#2A2F3A"
                text_color = "#EDEEF3"
                subtle = "rgba(148,163,184,0.14)"
                input_bg = "#111827"
                input_border = "#374151"
                btn_bg = "#1B1F2A"
                btn_border = "#2A2F3A"
                btn_fg = "#EDEEF3"
                btn_hover = "#222739"
                brand = "#7F56D9"
                brand_hover = "#8B66E9"
            else:
                dlg_bg = "#FFFFFF"
                dlg_border = "#D0D5DD"
                text_color = "#0F1728"
                subtle = "rgba(148,163,184,0.18)"
                input_bg = "#FFFFFF"
                input_border = "#D0D5DD"
                btn_bg = "#F3F4F6"
                btn_border = "#D0D5DD"
                btn_fg = "#111827"
                btn_hover = "#E5E7EB"
                brand = "#7F56D9"
                brand_hover = "#8B66E9"

            dlg = QDialog(self)
            try:
                dlg.setWindowTitle(title)
            except Exception:
                pass
            try:
                dlg.setModal(True)
            except Exception:
                pass
            try:
                dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            except Exception:
                pass
            try:
                dlg.setAttribute(Qt.WA_TranslucentBackground, True)
            except Exception:
                pass

            outer = QVBoxLayout(dlg)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            card = QFrame(dlg)
            card.setObjectName("renameDialogCard")
            outer.addWidget(card)

            dlg.setStyleSheet(
                f"""
                QFrame#renameDialogCard {{
                    background-color: {dlg_bg};
                    color: {text_color};
                    border-radius: 16px;
                    border: 1px solid {dlg_border};
                }}
                QLabel#dlgTitle {{
                    color: {text_color};
                    background: transparent;
                    font-size: 16px;
                    font-weight: 800;
                }}
                QLabel#msg {{
                    color: {text_color};
                    background: transparent;
                    font-size: 13px;
                }}
                QLineEdit {{
                    background-color: {input_bg};
                    color: {text_color};
                    border: 1px solid {input_border};
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 14px;
                }}
                QPushButton {{
                    min-width: 96px;
                    padding: 8px 16px;
                    border-radius: 999px;
                    border: 1px solid {btn_border};
                    background-color: {btn_bg};
                    color: {btn_fg};
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                }}
                QPushButton#primary {{
                    background-color: {brand};
                    border-color: {brand};
                    color: #FFFFFF;
                }}
                QPushButton#primary:hover {{
                    background-color: {brand_hover};
                    border-color: {brand_hover};
                }}
                QFrame#sep {{
                    background-color: {subtle};
                }}
                """
            )

            lay = QVBoxLayout(card)
            lay.setContentsMargins(18, 14, 18, 14)
            lay.setSpacing(12)
            title_lbl = QLabel(title, card)
            title_lbl.setObjectName("dlgTitle")
            lay.addWidget(title_lbl)

            msg = QLabel(label, card)
            msg.setObjectName("msg")
            msg.setWordWrap(True)
            lay.addWidget(msg)

            name_input = QLineEdit(project_data.get("name", ""), card)
            lay.addWidget(name_input)

            try:
                sep = QFrame(dlg)
                sep.setObjectName("sep")
                sep.setFixedHeight(1)
                lay.addWidget(sep)
            except Exception:
                pass

            btn_row = QHBoxLayout()
            btn_row.addStretch()
            cancel_btn = QPushButton(I18n.t("common.cancel", lang) if I18n else "Cancel", dlg)
            ok_btn = QPushButton(I18n.t("common.ok", lang) if I18n else "OK", dlg)
            ok_btn.setObjectName("primary")
            cancel_btn.clicked.connect(dlg.reject)
            ok_btn.clicked.connect(dlg.accept)
            btn_row.addWidget(cancel_btn)
            btn_row.addWidget(ok_btn)
            lay.addLayout(btn_row)

            try:
                dlg.setFixedWidth(420)
            except Exception:
                pass

            name_input.setFocus()
            name_input.selectAll()
            ret = dlg.exec()
            if ret != QDialog.Accepted:
                return
            new_name = name_input.text().strip()
            if not new_name:
                return
            from eduplay.core.project_manager import ProjectManager
            pm = self.project_manager or ProjectManager()
            project_data["name"] = new_name
            pm.save_project(project_data)
            self._show_message(success_title, success_msg, "success")
            try:
                win = self.window()
                if win and hasattr(win, "show_system_notification"):
                    win.show_system_notification(success_title, success_msg, "success")
            except Exception:
                pass
            self.refresh_projects()
        except Exception as e:
            try:
                self._show_message(error_title, f"{error_msg}: {str(e)}", "error")
            except Exception:
                self._show_message("Error", f"Failed to rename: {str(e)}", "error")
            try:
                win = self.window()
                if win and hasattr(win, "show_system_notification"):
                    win.show_system_notification(error_title, f"{error_msg}: {str(e)}", "error")
            except Exception:
                pass

    def on_project_delete(self, project_data: dict):
        try:
            try:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or 'en'
                theme = SettingsManager().get_theme() or 'dark'
                title = I18n.t('browser.delete_project_title', lang)
                confirm = I18n.t('browser.delete_project_confirm', lang).format(name=project_data.get("name",""))
                success_title = I18n.t('browser.success_title', lang)
                success_msg = I18n.t('browser.delete_project_success', lang)
                error_title = I18n.t('browser.error', lang)
                error_msg = I18n.t('browser.delete_project_failed', lang)
            except Exception:
                title = "Delete Project"
                confirm = f"Delete '{project_data.get('name','')}'?"
                success_title = "Success"
                success_msg = "Project deleted successfully."
                error_title = "Error"
                error_msg = "Failed to delete project"
                try:
                    from eduplay.core.settings_manager import SettingsManager
                    theme = SettingsManager().get_theme() or 'dark'
                except Exception:
                    theme = 'dark'

            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
            from PySide6.QtCore import Qt
            t = 'dark' if str(theme).lower() == 'dark' else 'light'
            if t == 'dark':
                dlg_bg = "#0B0E14"
                dlg_border = "#2A2F3A"
                text_color = "#EDEEF3"
                subtle = "rgba(148,163,184,0.14)"
                btn_bg = "#1B1F2A"
                btn_border = "#2A2F3A"
                btn_fg = "#EDEEF3"
                btn_hover = "#222739"
                brand = "#7F56D9"
                brand_hover = "#8B66E9"
            else:
                dlg_bg = "#FFFFFF"
                dlg_border = "#D0D5DD"
                text_color = "#0F1728"
                subtle = "rgba(148,163,184,0.18)"
                btn_bg = "#F3F4F6"
                btn_border = "#D0D5DD"
                btn_fg = "#111827"
                btn_hover = "#E5E7EB"
                brand = "#7F56D9"
                brand_hover = "#8B66E9"

            dlg = QDialog(self)
            try:
                dlg.setWindowTitle("")
            except Exception:
                pass
            try:
                dlg.setModal(True)
            except Exception:
                pass
            try:
                dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            except Exception:
                pass
            try:
                dlg.setAttribute(Qt.WA_TranslucentBackground, True)
            except Exception:
                pass

            outer = QVBoxLayout(dlg)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            card = QFrame(dlg)
            card.setObjectName("deleteDialogCard")
            outer.addWidget(card)

            dlg.setStyleSheet(
                f"""
                QFrame#deleteDialogCard {{
                    background-color: {dlg_bg};
                    color: {text_color};
                    border-radius: 16px;
                    border: 1px solid {dlg_border};
                }}
                QLabel#dlgTitle {{
                    color: {text_color};
                    background: transparent;
                    font-size: 16px;
                    font-weight: 800;
                }}
                QLabel#msg {{
                    color: {text_color};
                    background: transparent;
                    font-size: 13px;
                }}
                QPushButton {{
                    min-width: 96px;
                    padding: 8px 16px;
                    border-radius: 999px;
                    border: 1px solid {btn_border};
                    background-color: {btn_bg};
                    color: {btn_fg};
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                }}
                QPushButton#primary {{
                    background-color: {brand};
                    border-color: {brand};
                    color: #FFFFFF;
                }}
                QPushButton#primary:hover {{
                    background-color: {brand_hover};
                    border-color: {brand_hover};
                }}
                QPushButton#close {{
                    min-width: 34px;
                    max-width: 34px;
                    min-height: 34px;
                    max-height: 34px;
                    padding: 0px;
                    border-radius: 17px;
                }}
                QFrame#sep {{
                    background-color: {subtle};
                }}
                """
            )

            lay = QVBoxLayout(card)
            lay.setContentsMargins(18, 14, 18, 14)
            lay.setSpacing(12)
            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            title_lbl = QLabel(title, card)
            title_lbl.setObjectName("dlgTitle")
            header_row.addWidget(title_lbl)
            header_row.addStretch()
            close_btn = QPushButton("×", card)
            close_btn.setObjectName("close")
            try:
                close_btn.clicked.connect(dlg.reject)
            except Exception:
                pass
            header_row.addWidget(close_btn)
            lay.addLayout(header_row)

            msg = QLabel(confirm, card)
            msg.setObjectName("msg")
            msg.setWordWrap(True)
            msg.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lay.addWidget(msg)
            try:
                sep = QFrame(dlg)
                sep.setObjectName("sep")
                sep.setFixedHeight(1)
                lay.addWidget(sep)
            except Exception:
                pass
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            no_btn = QPushButton(I18n.t("common.cancel", lang), dlg)
            yes_btn = QPushButton(I18n.t("browser.delete", lang), dlg)
            yes_btn.setObjectName("primary")
            try:
                no_btn.clicked.connect(dlg.reject)
                yes_btn.clicked.connect(dlg.accept)
            except Exception:
                pass
            btn_row.addWidget(no_btn)
            btn_row.addWidget(yes_btn)
            lay.addLayout(btn_row)
            try:
                dlg.setFixedWidth(420)
            except Exception:
                pass
            ret = dlg.exec()
            if ret != QDialog.Accepted:
                return
            from eduplay.core.project_manager import ProjectManager
            pm = self.project_manager or ProjectManager()
            pm.delete_project(project_data.get("id",""))
            try:
                win = self.window()
                if win and hasattr(win, "show_system_notification"):
                    win.show_system_notification(success_title, success_msg, "success")
                else:
                    self._show_message(success_title, success_msg, "success")
            except Exception:
                try:
                    self._show_message(success_title, success_msg, "success")
                except Exception:
                    pass
            self.refresh_projects()
        except Exception as e:
            try:
                self._show_message(error_title, f"{error_msg}: {str(e)}", "error")
            except Exception:
                self._show_message("Error", f"Failed to delete: {str(e)}", "error")
            try:
                win = self.window()
                if win and hasattr(win, "show_system_notification"):
                    win.show_system_notification(error_title, f"{error_msg}: {str(e)}", "error")
            except Exception:
                pass

    def on_project_duplicate(self, project_data: dict):
        try:
            try:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or "en"
                success_title = I18n.t("browser.success_title", lang)
                success_msg = I18n.t("browser.duplicate_project_success", lang)
                error_title = I18n.t("browser.error", lang)
                error_msg = I18n.t("browser.duplicate_project_failed", lang)
            except Exception:
                success_title = "Success"
                success_msg = "Project duplicated successfully."
                error_title = "Error"
                error_msg = "Failed to duplicate project."
            pm = self.project_manager
            duplicated = pm.duplicate_project(str(project_data.get("id") or ""))
            if not duplicated:
                self._show_message(error_title, error_msg, "error")
                return
            self._show_message(success_title, success_msg, "success")
            self.refresh_projects()
        except Exception as e:
            self._show_message("Error", str(e), "error")

    def on_project_edit_tags(self, project_data: dict):
        try:
            try:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or "en"
                title = I18n.t("browser.edit_tags_title", lang)
                label = I18n.t("browser.edit_tags_prompt", lang)
                error_msg = I18n.t("browser.error", lang)
            except Exception:
                title = "Edit Tags"
                label = "Tags (comma separated):"
                error_msg = "Error"
            existing_tags = ", ".join(project_data.get("tags") or [])
            try:
                from eduplay.core.settings_manager import SettingsManager
                theme = SettingsManager().get_theme() or 'dark'
            except Exception:
                theme = 'dark'
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit
            from PySide6.QtCore import Qt
            t = 'dark' if str(theme).lower() == 'dark' else 'light'
            if t == 'dark':
                dlg_bg = "#0B0E14"
                dlg_border = "#2A2F3A"
                text_color = "#EDEEF3"
                subtle = "rgba(148,163,184,0.14)"
                input_bg = "#111827"
                input_border = "#374151"
                btn_bg = "#1B1F2A"
                btn_border = "#2A2F3A"
                btn_fg = "#EDEEF3"
                btn_hover = "#222739"
                brand = "#7F56D9"
                brand_hover = "#8B66E9"
            else:
                dlg_bg = "#FFFFFF"
                dlg_border = "#D0D5DD"
                text_color = "#0F1728"
                subtle = "rgba(148,163,184,0.18)"
                input_bg = "#FFFFFF"
                input_border = "#D0D5DD"
                btn_bg = "#F3F4F6"
                btn_border = "#D0D5DD"
                btn_fg = "#111827"
                btn_hover = "#E5E7EB"
                brand = "#7F56D9"
                brand_hover = "#8B66E9"

            dlg = QDialog(self)
            try:
                dlg.setWindowTitle(title)
            except Exception:
                pass
            try:
                dlg.setModal(True)
            except Exception:
                pass
            try:
                dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            except Exception:
                pass
            try:
                dlg.setAttribute(Qt.WA_TranslucentBackground, True)
            except Exception:
                pass

            outer = QVBoxLayout(dlg)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            card = QFrame(dlg)
            card.setObjectName("tagsDialogCard")
            outer.addWidget(card)

            dlg.setStyleSheet(
                f"""
                QFrame#tagsDialogCard {{
                    background-color: {dlg_bg};
                    color: {text_color};
                    border-radius: 16px;
                    border: 1px solid {dlg_border};
                }}
                QLabel#dlgTitle {{
                    color: {text_color};
                    background: transparent;
                    font-size: 16px;
                    font-weight: 800;
                }}
                QLabel#msg {{
                    color: {text_color};
                    background: transparent;
                    font-size: 13px;
                }}
                QLineEdit {{
                    background-color: {input_bg};
                    color: {text_color};
                    border: 1px solid {input_border};
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: 14px;
                }}
                QPushButton {{
                    min-width: 96px;
                    padding: 8px 16px;
                    border-radius: 999px;
                    border: 1px solid {btn_border};
                    background-color: {btn_bg};
                    color: {btn_fg};
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                }}
                QPushButton#primary {{
                    background-color: {brand};
                    border-color: {brand};
                    color: #FFFFFF;
                }}
                QPushButton#primary:hover {{
                    background-color: {brand_hover};
                    border-color: {brand_hover};
                }}
                QFrame#sep {{
                    background-color: {subtle};
                }}
                """
            )

            lay = QVBoxLayout(card)
            lay.setContentsMargins(18, 14, 18, 14)
            lay.setSpacing(12)
            title_lbl = QLabel(title, card)
            title_lbl.setObjectName("dlgTitle")
            lay.addWidget(title_lbl)

            msg = QLabel(label, card)
            msg.setObjectName("msg")
            msg.setWordWrap(True)
            lay.addWidget(msg)

            tags_input = QLineEdit(existing_tags, card)
            lay.addWidget(tags_input)

            try:
                sep = QFrame(dlg)
                sep.setObjectName("sep")
                sep.setFixedHeight(1)
                lay.addWidget(sep)
            except Exception:
                pass

            btn_row = QHBoxLayout()
            btn_row.addStretch()
            cancel_btn = QPushButton(I18n.t("common.cancel", lang) if I18n else "Cancel", dlg)
            ok_btn = QPushButton(I18n.t("common.ok", lang) if I18n else "OK", dlg)
            ok_btn.setObjectName("primary")
            cancel_btn.clicked.connect(dlg.reject)
            ok_btn.clicked.connect(dlg.accept)
            btn_row.addWidget(cancel_btn)
            btn_row.addWidget(ok_btn)
            lay.addLayout(btn_row)

            try:
                dlg.setFixedWidth(420)
            except Exception:
                pass

            tags_input.setFocus()
            tags_input.selectAll()
            ret = dlg.exec()
            if ret != QDialog.Accepted:
                return
            raw_tags = tags_input.text()
            tags = [part.strip() for part in str(raw_tags or "").split(",")]
            updated = self.project_manager.update_project_tags(str(project_data.get("id") or ""), tags)
            if not updated:
                self._show_message(error_msg, "Failed to update tags.", "error")
                return
            self.refresh_projects()
        except Exception as e:
            self._show_message("Error", str(e), "error")
    
    def import_project(self):
        """Import project from file"""
        try:
            from eduplay.core.i18n import I18n
            lang = getattr(self.project_manager, 'language', None)
            l = lang or 'en'
            file_path, _ = QFileDialog.getOpenFileName(self, I18n.t('browser.choose_project_file', l), "", I18n.t('browser.file_filters', l))
            if not file_path:
                return
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            from eduplay.core.project_manager import ProjectManager
            pm = self.project_manager or ProjectManager()
            name = data.get('name', I18n.t('browser.imported_project', l))
            desc = data.get('description', '')
            game_type = data.get('game_type', 'quiz_classic')
            new_proj = pm.create_project(name, desc, game_type)
            # Copy questions and config
            new_proj['questions'] = data.get('questions', [])
            new_proj['game_config'] = data.get('game_config', new_proj.get('game_config', {}))
            pm.save_project(new_proj)
            QMessageBox.information(self, I18n.t('browser.import_title', l), I18n.t('browser.import_success', l))
            try:
                win = self.window()
                if win and hasattr(win, "show_system_notification"):
                    win.show_system_notification(I18n.t('browser.import_title', l), I18n.t('browser.import_success', l), "success")
            except Exception:
                pass
            self.refresh_projects()
        except Exception as e:
            QMessageBox.critical(self, I18n.t('browser.error', l), f"{I18n.t('browser.import_failed', l)}: {str(e)}")
            try:
                win = self.window()
                if win and hasattr(win, "show_system_notification"):
                    win.show_system_notification(I18n.t('browser.error', l), f"{I18n.t('browser.import_failed', l)}: {str(e)}", "error")
            except Exception:
                pass
    
    def showEvent(self, event):
        """Handle show event - refresh projects when screen is shown"""
        super().showEvent(event)
        self.load_projects()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            m = 20 if self.width() < 900 else 40
            if hasattr(self, 'content_layout') and self.content_layout:
                self.content_layout.setContentsMargins(m, m, m, m)
            self._apply_header_scale()
            cols = self.get_max_columns()
            if cols != getattr(self, '_last_cols', 0):
                self.render_project_cards()
            try:
                compact = self.width() < 720
                for i in range(self.projects_grid.count()):
                    w = self.projects_grid.itemAt(i).widget()
                    if hasattr(w, 'set_compact'):
                        w.set_compact(compact)
            except Exception:
                pass
        except Exception:
            pass

    def set_language(self, lang: str):
        from eduplay.core.i18n import I18n
        l = lang or 'en'
        try:
            self.back_btn.setText(strip_icon_text(I18n.t('browser.back', l)))
            self.search_input.setPlaceholderText(I18n.t('browser.search_placeholder', l))
            self._populate_filter_controls(l)
            self.title_label.setText(I18n.t('browser.my_projects', l))
            self.import_btn.setText(strip_icon_text(I18n.t('browser.import', l)))
            self.refresh_btn.setText(strip_icon_text(I18n.t('browser.refresh', l)))
            if hasattr(self, "_empty_message_label"):
                self._empty_message_label.setText(I18n.t("browser.empty_title", l))
            if hasattr(self, "_empty_submessage_label"):
                self._empty_submessage_label.setText(I18n.t("browser.empty_desc", l))
            if hasattr(self, "_empty_create_btn"):
                self._empty_create_btn.setText(I18n.t("browser.empty_cta", l))
        except Exception:
            pass

    def set_scale(self, scale: float):
        try:
            normalized_scale = max(0.85, min(1.5, float(scale)))
            self._requested_scale = normalized_scale
            if self._stable_scale is None:
                self._stable_scale = normalized_scale
            effective_scale = self._effective_scale()
            self._apply_header_scale(effective_scale)
            for i in range(self.projects_grid.count()):
                w = self.projects_grid.itemAt(i).widget()
                if hasattr(w, 'set_scale'):
                    w.set_scale(effective_scale)
        except Exception:
            pass
