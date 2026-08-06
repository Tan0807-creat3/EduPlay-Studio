"""
Editor Right Panel - Real-time preview of questions and games
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QPushButton, QLabel, QStackedWidget, QTextBrowser,
                               QListWidget, QListWidgetItem)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QFont, QPixmap
import os
import re
import tempfile

class EditorRightPanel(QWidget):
    """Right panel for real-time preview of questions and games"""
    
    # Signals
    preview_action = Signal(str)  # Emits preview action (reload, fullscreen, etc.)
    
    def __init__(self):
        super().__init__()
        self.current_project = None
        self.current_question = None
        self.current_mode = "question"  # "question" or "game"
        self.preview_html = None
        self.init_ui()
        try:
            # Default language-aware title
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or 'en'
            self.preview_title.setText(I18n.t('editor.live_preview', l))
        except Exception:
            pass

    def _lang(self) -> str:
        try:
            from eduplay.core.i18n import I18n
            locale = getattr(I18n, "locale", None)
            if locale:
                return locale
            from eduplay.core.settings_manager import SettingsManager
            return SettingsManager().get_language() or "en"
        except Exception:
            return "en"

    # Public API consumed by EditorScreen
    def set_project(self, project: dict):
        """Assign current project and decide initial preview target"""
        try:
            self.current_project = project or {}
            qs = self.current_project.get('questions', [])
            if qs:
                try:
                    self.preview_question(qs[0])
                except Exception:
                    self.preview_game(self.current_project)
            else:
                self.preview_game(self.current_project)
        except Exception:
            self.preview_game(project or {})

    def set_question(self, question: dict, index: int | None = None):
        """Assign current question and refresh preview"""
        try:
            if question:
                self.preview_question(question)
            else:
                # If question absent switch to game preview
                self.preview_game(self.current_project or {})
        except Exception:
            pass

    def refresh_preview(self):
        """Force refresh based on current mode and state"""
        try:
            self.update_preview()
        except Exception:
            pass

    def _looks_like_fishing_config(self, cfg_dict: dict) -> bool:
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
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create header
        self.create_header(layout)
        
        # Create preview area
        self.create_preview_area(layout)
        
        # Create info panel
        self.create_info_panel(layout)
        
        self.setLayout(layout)
        
        # Apply styling
        self.setStyleSheet("""
            EditorRightPanel {
                background-color: #2D2F3A;
                border-left: 1px solid #4A4E5A;
            }
            
            .preview-header {
                background-color: #1E1E24;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                padding: 12px 15px;
                border-bottom: 1px solid #4A4E5A;
            }
            
            .preview-button {
                background-color: #3A3C47;
                color: #E2E8F0;
                border: 1px solid #4A4E5A;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 5px;
            }
            
            .preview-button:hover {
                background-color: #4A4E5A;
                color: #FFFFFF;
            }
            
            .preview-content {
                background-color: #1E1E24;
                border: none;
            }
            
            .info-panel {
                background-color: #1E1E24;
                border-top: 1px solid #4A4E5A;
                padding: 15px;
            }
            
            .info-title {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 10px;
            }
            
            .info-item {
                color: #A0AEC0;
                font-size: 12px;
                margin-bottom: 5px;
            }
            
            .info-value {
                color: #E2E8F0;
                font-weight: 600;
            }
            
            QTextBrowser {
                background-color: #1E1E24;
                color: #E2E8F0;
                border: none;
                font-size: 14px;
                line-height: 1.6;
            }
            
            QTextBrowser p {
                margin: 10px 0;
            }
            
            QTextBrowser .question-text {
                font-size: 16px;
                font-weight: 600;
                color: #FFFFFF;
                margin-bottom: 15px;
            }
            
            QTextBrowser .option {
                background-color: #2D2F3A;
                border: 1px solid #4A4E5A;
                border-radius: 6px;
                padding: 10px;
                margin: 5px 0;
            }
            
            QTextBrowser .option:hover {
                background-color: #3A3C47;
                border-color: #5A5E6A;
            }
            
            QTextBrowser .option.correct {
                background-color: rgba(18, 183, 106, 0.2);
                border-color: #12B76A;
            }
            
            QTextBrowser .option.incorrect {
                background-color: rgba(244, 67, 54, 0.2);
                border-color: #F44336;
            }
            
            QTextBrowser .explanation {
                background-color: rgba(127, 86, 217, 0.1);
                border-left: 3px solid #7F56D9;
                padding: 10px;
                margin-top: 15px;
                font-size: 13px;
                color: #A0AEC0;
            }
        """)
    
    def apply_theme(self, theme: str):
        t = 'dark' if str(theme).lower() == 'dark' else 'light'
        if t == 'dark':
            bg = "#2D2F3A"
            border = "#4A4E5A"
            header_bg = "#1E1E24"
            header_text = "#FFFFFF"
            btn_bg = "#3A3C47"
            btn_fg = "#E2E8F0"
            btn_hover = "#4A4E5A"
            content_bg = "#1E1E24"
            info_bg = "#1E1E24"
            info_title = "#FFFFFF"
            info_item = "#A0AEC0"
            info_value = "#E2E8F0"
            textbrowser_bg = "#1E1E24"
            textbrowser_fg = "#E2E8F0"
            option_bg = "#2D2F3A"
            option_border = "#4A4E5A"
            option_hover = "#3A3C47"
            option_hover_border = "#5A5E6A"
        else:
            bg = "#FFFFFF"
            border = "#E2E8F0"
            header_bg = "#F8FAFC"
            header_text = "#1A1A1A"
            btn_bg = "#FFFFFF"
            btn_fg = "#1A1A1A"
            btn_hover = "#F1F5F9"
            content_bg = "#F9FAFF"
            info_bg = "#FFFFFF"
            info_title = "#1A1A1A"
            info_item = "#667085"
            info_value = "#111827"
            textbrowser_bg = "#FFFFFF"
            textbrowser_fg = "#1A1A1A"
            option_bg = "#FFFFFF"
            option_border = "#CBD5E1"
            option_hover = "#F1F5F9"
            option_hover_border = "#94A3B8"
        qss = f"""
            EditorRightPanel {{
                background-color: {bg};
                border-left: 1px solid {border};
            }}
            .preview-header {{
                background-color: {header_bg};
                color: {header_text};
                font-size: 14px;
                font-weight: 700;
                padding: 12px 15px;
                border-bottom: 1px solid {border};
            }}
            .preview-button {{
                background-color: {btn_bg};
                color: {btn_fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 5px;
            }}
            .preview-button:hover {{
                background-color: {btn_hover};
                color: {header_text};
            }}
            .preview-content {{
                background-color: {content_bg};
                border: none;
            }}
            .info-panel {{
                background-color: {info_bg};
                border-top: 1px solid {border};
                padding: 15px;
            }}
            .info-title {{
                color: {info_title};
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            .info-item {{
                color: {info_item};
                font-size: 12px;
                margin-bottom: 5px;
            }}
            .info-value {{
                color: {info_value};
                font-weight: 600;
            }}
            QTextBrowser {{
                background-color: {textbrowser_bg};
                color: {textbrowser_fg};
                border: none;
                font-size: 14px;
                line-height: 1.6;
            }}
            QTextBrowser .question-text {{
                font-size: 16px;
                font-weight: 600;
                color: {header_text};
                margin-bottom: 15px;
            }}
            QTextBrowser .option {{
                background-color: {option_bg};
                border: 1px solid {option_border};
                border-radius: 6px;
                padding: 10px;
                margin: 5px 0;
            }}
            QTextBrowser .option:hover {{
                background-color: {option_hover};
                border-color: {option_hover_border};
            }}
            QTextBrowser .option.correct {{
                background-color: rgba(18, 183, 106, 0.15);
                border-color: #12B76A;
            }}
            QTextBrowser .option.incorrect {{
                background-color: rgba(244, 67, 54, 0.15);
                border-color: #F44336;
            }}
            QTextBrowser .explanation {{
                background-color: rgba(127, 86, 217, 0.08);
                border-left: 3px solid #7F56D9;
                padding: 10px;
                margin-top: 15px;
                font-size: 13px;
                color: {info_item};
            }}
        """
        try:
            self.setStyleSheet(qss)
        except Exception:
            pass
    
    def create_header(self, layout):
        """Create preview header"""
        header = QFrame()
        header.setObjectName("preview-header")
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or 'en'
            title_text = I18n.t('editor.live_preview', l)
        except Exception:
            title_text = "Live Preview"
        self.preview_title = QLabel(title_text)
        header_layout.addWidget(self.preview_title)
        header_layout.addStretch()
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or 'en'
            btn_text = I18n.t('editor.preview_title', l)
        except Exception:
            btn_text = "Preview"
        self.open_preview_btn = QPushButton(btn_text)
        self.open_preview_btn.setObjectName("preview-button")
        self.open_preview_btn.clicked.connect(self._open_external_preview)
        header_layout.addWidget(self.open_preview_btn)
        
        layout.addWidget(header)
    
    def _open_external_preview(self):
        try:
            w = self
            while w is not None:
                if hasattr(w, "open_preview_window"):
                    try:
                        w.open_preview_window()
                    except Exception:
                        pass
                    return
                w = w.parent()
        except Exception:
            try:
                self.preview_stack.setCurrentIndex(1)
            except Exception:
                pass
    
    def create_preview_area(self, layout):
        """Create preview area"""
        # Create stacked widget for different preview types
        self.preview_stack = QStackedWidget()
        
        # Question preview (HTML-based)
        self.question_preview = QTextBrowser()
        self.question_preview.setObjectName("preview-content")
        self.preview_stack.addWidget(self.question_preview)

        self.game_placeholder = QFrame()
        self.game_placeholder.setObjectName("preview-content")
        ph_layout = QVBoxLayout(self.game_placeholder)
        ph_layout.setContentsMargins(18, 18, 18, 18)
        ph_layout.setSpacing(10)
        self.game_placeholder_title = QLabel("")
        self.game_placeholder_title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.game_placeholder_desc = QLabel("")
        self.game_placeholder_desc.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.game_placeholder_desc.setWordWrap(True)
        self.game_placeholder_btn = QPushButton("")
        self.game_placeholder_btn.setObjectName("preview-button")
        self.game_placeholder_btn.clicked.connect(self._open_external_preview)
        ph_layout.addStretch()
        ph_layout.addWidget(self.game_placeholder_title)
        ph_layout.addWidget(self.game_placeholder_desc)
        ph_layout.addWidget(self.game_placeholder_btn, alignment=Qt.AlignHCenter)
        ph_layout.addStretch()
        self.preview_stack.addWidget(self.game_placeholder)
        
        layout.addWidget(self.preview_stack, stretch=3)
    
    def create_info_panel(self, layout):
        """Create info panel"""
        info_panel = QFrame()
        info_panel.setObjectName("info-panel")
        
        info_layout = QVBoxLayout(info_panel)
        info_layout.setSpacing(10)
        
        # Title
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or 'en'
            info_text = I18n.t('editor.info', l)
        except Exception:
            info_text = "Information"
        info_title = QLabel(info_text)
        info_title.setObjectName("info-title")
        info_layout.addWidget(info_title)
        
        # Info items
        self.info_items = {}
        try:
            info_labels = [
                ("type", I18n.t('editor.type_label', l)),
                ("difficulty", I18n.t('editor.difficulty', l)),
                ("time", I18n.t('editor.time', l)),
                ("points", I18n.t('editor.points', l)),
                ("tags", I18n.t('editor.tags', l))
            ]
        except Exception:
            info_labels = [
                ("type", "Type:"),
                ("difficulty", "Difficulty:"),
                ("time", "Time:"),
                ("points", "Points:"),
                ("tags", "Tags:")
            ]
        
        for key, label in info_labels:
            item_layout = QHBoxLayout()
            item_layout.addWidget(QLabel(label), stretch=1)
            self.info_items[key] = QLabel("-")
            self.info_items[key].setObjectName("info-value")
            item_layout.addWidget(self.info_items[key], stretch=2)
            info_layout.addLayout(item_layout)
        
        info_layout.addStretch()
        layout.addWidget(info_panel, stretch=1)
    
    def update_preview(self):
        """Update the preview based on current content"""
        if self.current_mode == "question" and self.current_question:
            self.preview_question(self.current_question)
        elif self.current_mode == "game" and self.current_project:
            self.preview_game(self.current_project)
    
    def preview_question(self, question_data: dict):
        """Preview a question"""
        self.current_question = question_data
        self.current_mode = "question"
        self.preview_stack.setCurrentIndex(0)
        
        # Generate HTML preview
        html_content = self.generate_question_html(question_data)
        self.question_preview.setHtml(html_content)
        
        # Update info panel
        self.update_info_panel(question_data)
        
        # Update title
        question_text = question_data.get("question", "Câu hỏi")
        if len(question_text) > 30:
            question_text = question_text[:27] + "..."
        self.preview_title.setText(f"Xem trước: {question_text}")
    
    def preview_game(self, project_data: dict):
        """Preview a game"""
        self.current_project = project_data
        self.current_mode = "game"
        try:
            self.preview_stack.setCurrentIndex(1)
        except Exception:
            pass
        
        project_name = project_data.get("name", "Trò chơi") if isinstance(project_data, dict) else "Trò chơi"
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or 'en'
            title_txt = I18n.t('editor.preview_title', l)
            desc_txt = I18n.t('editor.loading_preview', l)
            btn_txt = I18n.t('editor.preview_title', l)
        except Exception:
            title_txt = "Preview"
            desc_txt = "Open preview window"
            btn_txt = "Preview"
        try:
            self.preview_title.setText(f"{title_txt}: {project_name}")
        except Exception:
            pass
        try:
            self.game_placeholder_title.setText(project_name)
            self.game_placeholder_desc.setText(desc_txt)
            self.game_placeholder_btn.setText(btn_txt)
        except Exception:
            pass
    
    def generate_question_html(self, question_data: dict) -> str:
        """Generate HTML for question preview"""
        question_type = question_data.get("type", "multiple_choice")
        question_text = question_data.get("question", "")
        explanation = question_data.get("explanation", "")
        
        html_parts = []
        html_parts.append("<html><head><style>")
        html_parts.append(self.get_question_preview_css())
        html_parts.append("</style></head><body>")
        
        # Question text
        if question_type != "fill_blank":
            html_parts.append(f'<div class="question-text">{self.escape_html(question_text)}</div>')
        
        # Type-specific content
        if question_type == "multiple_choice":
            html_parts.extend(self.generate_multiple_choice_html(question_data))
        elif question_type == "true_false":
            html_parts.extend(self.generate_true_false_html(question_data))
        elif question_type == "fill_blank":
            html_parts.extend(self.generate_fill_blank_html(question_data))
        elif question_type == "matching":
            html_parts.extend(self.generate_matching_html(question_data))
        elif question_type == "short_answer":
            html_parts.extend(self.generate_short_answer_html(question_data))
        
        # Explanation
        if explanation:
            html_parts.append(f'<div class="explanation">{self.escape_html(explanation)}</div>')
        
        html_parts.append("</body></html>")
        return "".join(html_parts)
    
    def generate_multiple_choice_html(self, question_data: dict) -> list:
        """Generate HTML for multiple choice question"""
        html_parts = []
        options = question_data.get("options", [])
        
        for i, option in enumerate(options):
            option_text = option.get("text")
            if not option_text:
                try:
                    from eduplay.core.i18n import I18n
                    option_text = I18n.t("quiz.answer_option_label", self._lang(), n=i + 1)
                except Exception:
                    option_text = f"Answer {i + 1}"
            is_correct = option.get("correct", False)
            
            css_class = "option correct" if is_correct else "option"
            html_parts.append(f'<div class="{css_class}">{self.escape_html(option_text)}</div>')
        
        return html_parts
    
    def generate_true_false_html(self, question_data: dict) -> list:
        """Generate HTML for true/false question"""
        html_parts = []
        correct_answer = question_data.get("correct_answer", False)
        
        true_class = "option correct" if correct_answer else "option"
        false_class = "option correct" if not correct_answer else "option"
        
        try:
            from eduplay.core.i18n import I18n
            true_text = I18n.t("quiz.true", self._lang())
            false_text = I18n.t("quiz.false", self._lang())
        except Exception:
            true_text = "True"
            false_text = "False"
        
        html_parts.append(f'<div class="{true_class}">{true_text}</div>')
        html_parts.append(f'<div class="{false_class}">{false_text}</div>')
        
        return html_parts
    
    def generate_fill_blank_html(self, question_data: dict) -> list:
        """Generate HTML for fill-in-the-blank question"""
        html_parts = []
        answers = question_data.get("answers", [])
        question_text = self.escape_html(question_data.get("question", "") or "___")

        html_parts.append('<div class="question-text fill-blank-inline">')
        html_parts.append('<span class="question-inline-wrap">')

        marker = re.search(r'_{3,}', question_text)
        if marker:
            before = question_text[:marker.start()]
            after = question_text[marker.end():]
            if before:
                html_parts.append(f'<span class="question-inline-text">{before}</span>')
            html_parts.append('<input type="text" class="text-input inline-blank-input" value="" />')
            if after:
                html_parts.append(f'<span class="question-inline-text">{after}</span>')
        else:
            if question_text:
                html_parts.append(f'<span class="question-inline-text">{question_text}</span>')
            html_parts.append('<input type="text" class="text-input inline-blank-input" value="" />')

        html_parts.append('</span>')
        html_parts.append('</div>')

        if answers:
            answer_text = ", ".join(self.escape_html(str(answer)) for answer in answers if str(answer).strip())
            if answer_text:
                try:
                    from eduplay.core.i18n import I18n
                    note = I18n.t("quiz.accepted_answers", self._lang())
                except Exception:
                    note = "Accepted answers:"
                html_parts.append(f'<div class="answer-note">{note} {answer_text}</div>')
        
        return html_parts
    
    def generate_matching_html(self, question_data: dict) -> list:
        """Generate HTML for matching question"""
        html_parts = []
        pairs = question_data.get("pairs", [])
        
        html_parts.append('<div style="display: flex; justify-content: space-between;">')
        try:
            from eduplay.core.i18n import I18n
            left_header = I18n.t("quiz.matching_left", self._lang())
            right_header = I18n.t("quiz.matching_right", self._lang())
        except Exception:
            left_header = "Left:"
            right_header = "Right:"
        html_parts.append(f"<strong>{left_header}</strong><br>")
        for pair in pairs:
            left = pair.get("left", "")
            html_parts.append(f'<div class="option">{self.escape_html(left)}</div>')
        html_parts.append("</div>")
        
        html_parts.append('<div style="width: 45%;">')
        html_parts.append(f"<strong>{right_header}</strong><br>")
        for pair in pairs:
            right = pair.get("right", "")
            html_parts.append(f'<div class="option">{self.escape_html(right)}</div>')
        html_parts.append("</div>")
        html_parts.append("</div>")
        
        return html_parts
    
    def generate_short_answer_html(self, question_data: dict) -> list:
        """Generate HTML for short answer question"""
        html_parts = []
        answers = question_data.get("answers", [])
        max_length = question_data.get("max_length", 100)
        
        try:
            from eduplay.core.i18n import I18n
            label = I18n.t("quiz.short_answer_label", self._lang())
            limit = I18n.t("quiz.limit_chars", self._lang(), max_length=max_length)
        except Exception:
            label = "Short answer:"
            limit = f"Limit: {max_length} characters"
        
        html_parts.append(f'<div class="option">{label}</div>')
        
        for answer in answers:
            html_parts.append(f'<div class="option correct">{self.escape_html(answer)}</div>')
        
        html_parts.append(f'<div style="color: #A0AEC0; font-size: 12px; margin-top: 10px;">{limit}</div>')
        
        return html_parts
    
    def generate_game_html(self, project_data: dict) -> str:
        """Generate HTML for game preview"""
        # Use the same fishing detection logic as export_service.py
        game_type_from_config = project_data.get("game_config", {}).get("game_type", "")
        game_type_top_level = project_data.get("game_type", "")
        force_variant = str(project_data.get("force_variant") or "").lower()
        cfg_full = (project_data.get('game_config', {}) or {})
        cfg_gt = str(cfg_full.get('game_type') or '').lower()
        
        def _looks_like_fishing_config(cfg: dict) -> bool:
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
        
        marker = str(project_data.get('variant_marker') or '').lower()
        cfg_marker = str((project_data.get('game_config', {}) or {}).get('variant_marker') or '').lower()
        name_str = str(project_data.get('name') or '')
        is_fishing = (
            str(game_type_top_level).lower() == 'fishing'
            or 'fishing' in str(game_type_top_level).lower()
            or 'fish' in str(game_type_top_level).lower()
            or ('bắt cá' in str(game_type_top_level).lower()) or ('bat ca' in str(game_type_top_level).lower()) or ('câu cá' in str(game_type_top_level).lower()) or ('cau ca' in str(game_type_top_level).lower())
            or str(game_type_top_level).lower() in ('bat_ca', 'bắt cá', 'tro_choi_cau_ca', 'trò_chơi_câu_cá')
            or str(game_type_top_level).lower() in ('fishing game', 'tro choi cau ca', 'trò chơi câu cá')
            or force_variant == 'fishing'
            or ('fishing' in cfg_gt) or ('fish' in cfg_gt) or ('bắt cá' in cfg_gt) or ('bat ca' in cfg_gt) or ('câu cá' in cfg_gt) or ('cau ca' in cfg_gt)
            or marker == 'fishing'
            or cfg_marker == 'fishing'
            or ('🎣' in name_str)
        )
        
        if is_fishing:
            game_type = "Fishing Game"
        else:
            # Check for other game types
            gt = game_type_from_config or "Trắc nghiệm cổ điển"
            game_type = gt if isinstance(gt, str) else "Trắc nghiệm cổ điển"
            if str(game_type).lower() in ["quiz", "quiz_classic"]:
                game_type = "Quiz Classic"
            elif str(game_type).lower() in ["ai là triệu phú", "millionaire", "quiz_millionaire"]:
                game_type = "Millionaire"
        questions = project_data.get("questions", [])
        
        html_parts = []
        html_parts.append("<html><head><style>")
        html_parts.append(self.get_game_preview_css())
        html_parts.append("</style></head><body>")
        
        html_parts.append('<div class="game-preview">')
        html_parts.append(f'<h2>{self.escape_html(game_type)}</h2>')
        html_parts.append(f'<p>Số câu hỏi: {len(questions)}</p>')
        
        if questions:
            html_parts.append('<h3>Câu hỏi mẫu:</h3>')
            # Show first question as preview
            first_question = questions[0]
            html_parts.extend(self.generate_question_html_parts(first_question))
        
        if game_type == "Millionaire":
            try:
                from eduplay.core.i18n import I18n
                from eduplay.core.settings_manager import SettingsManager
                l = SettingsManager().get_language() or 'vi'
                fifty = I18n.t('lifeline.fifty', l)
                phone = I18n.t('lifeline.phone', l)
                audience = I18n.t('lifeline.audience_result', l)
            except Exception:
                fifty, phone, audience = '50:50', 'Phone', 'Audience'
            html_parts.append('<div class="lifelines" style="margin-top:12px; display:flex; gap:8px;">')
            html_parts.append(f'<button style="padding:6px 10px; border-radius:8px;">{self.escape_html(fifty)}</button>')
            html_parts.append(f'<button style="padding:6px 10px; border-radius:8px;">{self.escape_html(phone)}</button>')
            html_parts.append(f'<button style="padding:6px 10px; border-radius:8px;">{self.escape_html(audience)}</button>')
            html_parts.append('</div>')
        html_parts.append('</div>')
        html_parts.append("</body></html>")
        
        return "".join(html_parts)
    
    def generate_question_html_parts(self, question_data: dict) -> list:
        """Generate basic HTML parts for a question"""
        html_parts = []
        question_text = question_data.get("question", "")
        
        html_parts.append(f'<div class="question-preview">')
        html_parts.append(f'<div class="question-text">{self.escape_html(question_text)}</div>')
        
        # Add basic options preview
        if question_data.get("type") == "multiple_choice":
            options = question_data.get("options", [])
            for option in options[:2]:  # Show first 2 options
                option_text = option.get("text", "")
                html_parts.append(f'<div class="option">{self.escape_html(option_text)}</div>')
            if len(options) > 2:
                html_parts.append('<div style="color: #A0AEC0; font-size: 12px;">...</div>')
        
        html_parts.append('</div>')
        return html_parts
    
    def get_question_preview_css(self) -> str:
        """Get CSS for question preview"""
        try:
            from eduplay.core.settings_manager import SettingsManager
            sm = SettingsManager()
            theme = sm.get_theme() or 'dark'
            editor = sm.get_editor_settings() or {}
            family = str(editor.get("font_family") or "Segoe UI").replace('"', "")
        except Exception:
            theme = 'dark'
            family = "Segoe UI"
        bg = '#1E1E24' if theme == 'dark' else '#FFFFFF'
        text = '#FFFFFF' if theme == 'dark' else '#1A1A1A'
        card = '#2D2F3A' if theme == 'dark' else '#FFFFFF'
        border = '#4A4E5A' if theme == 'dark' else '#D0D5DD'
        hover = '#3A3C47' if theme == 'dark' else '#F5F6FA'
        return f"""
            body {{
                font-family: "{family}", -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: {bg};
            }}
            .question-text {{
                font-size: 18px;
                font-weight: 600;
                color: {text};
                margin-bottom: 20px;
                line-height: 1.4;
            }}
            .question-text.fill-blank-inline {{
                display: block;
                text-align: center;
                margin-bottom: 16px;
            }}
            .question-inline-wrap {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                flex-wrap: wrap;
                line-height: 1.6;
            }}
            .question-inline-text {{
                color: {text};
            }}
            .text-input {{
                width: min(92%, 560px);
                min-width: 180px;
                max-width: 100%;
                padding: 10px 14px;
                border-radius: 12px;
                border: 2px solid {border};
                background-color: {card};
                color: {text};
                font-size: 16px;
                font-weight: 600;
                outline: none;
                text-align: center;
                box-sizing: border-box;
                margin: 0 auto;
            }}
            .inline-blank-input {{
                width: clamp(140px, 24vw, 240px);
                min-width: 140px;
                max-width: 100%;
                margin: 4px 0;
                display: inline-block;
            }}
            .option {{
                background-color: {card};
                border: 2px solid {border};
                border-radius: 8px;
                padding: 12px 16px;
                margin: 8px 0;
                color: {('#E2E8F0' if theme == 'dark' else '#1A1A1A')};
                font-size: 15px;
            }}
            .option:hover {{
                background-color: {hover};
                border-color: {border};
            }}
            .option.correct {{
                background-color: rgba(18, 183, 106, 0.1);
                border-color: #12B76A;
                color: #12B76A;
            }}
            .option.incorrect {{
                background-color: rgba(244, 67, 54, 0.1);
                border-color: #F44336;
                color: #F44336;
            }}
            .explanation {{
                background-color: rgba(127, 86, 217, 0.1);
                border-left: 4px solid #7F56D9;
                padding: 12px;
                margin-top: 20px;
                border-radius: 0 6px 6px 0;
                color: {('#A0AEC0' if theme == 'dark' else '#667085')};
                font-size: 14px;
                line-height: 1.5;
            }}
            .answer-note {{
                margin-top: 12px;
                color: #12B76A;
                font-size: 13px;
                text-align: center;
            }}
        """
    
    def get_game_preview_css(self) -> str:
        """Get CSS for game preview"""
        try:
            from eduplay.core.settings_manager import SettingsManager
            sm = SettingsManager()
            theme = sm.get_theme() or 'dark'
            editor = sm.get_editor_settings() or {}
            family = str(editor.get("font_family") or "Segoe UI").replace('"', "")
        except Exception:
            theme = 'dark'
            family = "Segoe UI"
        bg = '#1E1E24' if theme == 'dark' else '#FFFFFF'
        text = '#E2E8F0' if theme == 'dark' else '#1A1A1A'
        head = '#FFFFFF' if theme == 'dark' else '#1A1A1A'
        card = '#2D2F3A' if theme == 'dark' else '#FFFFFF'
        border = '#4A4E5A' if theme == 'dark' else '#D0D5DD'
        sub = '#A0AEC0' if theme == 'dark' else '#667085'
        return f"""
            body {{
                font-family: "{family}", -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: {bg};
                color: {text};
            }}
            .game-preview {{
                text-align: center;
                max-width: 600px;
                margin: 0 auto;
            }}
            .game-preview h2 {{
                color: {head};
                font-size: 24px;
                margin-bottom: 10px;
            }}
            .game-preview h3 {{
                color: {sub};
                font-size: 16px;
                margin-top: 20px;
                margin-bottom: 10px;
            }}
            .question-preview {{
                background-color: {card};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 15px;
                margin: 15px 0;
                text-align: left;
            }}
            .question-text {{
                font-size: 16px;
                font-weight: 600;
                color: {head};
                margin-bottom: 10px;
            }}
        """
    
    def update_info_panel(self, question_data: dict):
        """Update info panel with question information"""
        try:
            from eduplay.core.i18n import I18n
            lang = self._lang()
            type_names = {
                "multiple_choice": I18n.t("quiz.type_multiple_choice", lang),
                "true_false": I18n.t("quiz.type_true_false", lang),
                "fill_blank": I18n.t("quiz.type_fill_blank", lang),
                "matching": I18n.t("quiz.type_matching", lang),
                "short_answer": I18n.t("quiz.type_short_answer", lang),
            }
        except Exception:
            type_names = {
                "multiple_choice": "Multiple choice",
                "true_false": "True/False",
                "fill_blank": "Fill in the blank",
                "matching": "Matching",
                "short_answer": "Short answer",
            }
        question_type = question_data.get("type", "multiple_choice")
        self.info_items["type"].setText(type_names.get(question_type, question_type))
        
        # Difficulty
        difficulty = question_data.get("difficulty", "Trung bình")
        self.info_items["difficulty"].setText(difficulty)
        
        # Time limit
        time_limit = question_data.get("time_limit", 30)
        self.info_items["time"].setText(f"{time_limit} giây")
        
        # Points
        points = question_data.get("points", 10)
        self.info_items["points"].setText(f"{points} điểm")
        
        # Tags
        tags = question_data.get("tags", [])
        tags_text = ", ".join(tags) if tags else "Không có"
        self.info_items["tags"].setText(tags_text)
    
    def escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace("\"", "&quot;")
                   .replace("'", "&#39;"))
    
    def load_project(self, project_data: dict):
        """Load project data"""
        self.current_project = project_data
        
        # Preview first question if available
        questions = project_data.get("questions", [])
        if questions:
            self.preview_question(questions[0])
        else:
            # Preview game configuration
            self.preview_game(project_data)

