from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QSplitter, QPushButton, QFrame, QTextEdit, QLineEdit,
                                QListWidget, QListWidgetItem, QScrollArea, QComboBox, QSlider)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class EditorLeftPanel(QWidget):
    question_selected = Signal(dict)
    game_config_changed = Signal(dict)
    asset_selected = Signal(str)
    
    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.current_project = None
        try:
            from eduplay.core.settings_manager import SettingsManager
            t = theme or (SettingsManager().get_theme() or 'dark')
        except Exception:
            t = theme or 'dark'
        self.theme = 'dark' if str(t).lower() == 'dark' else 'light'
        self.setup_ui()

    def _lang(self) -> str:
        try:
            from eduplay.core.settings_manager import SettingsManager
            return SettingsManager().get_language() or "en"
        except Exception:
            return "en"

    def _t(self, key: str, fallback: str, **kwargs) -> str:
        try:
            from eduplay.core.i18n import I18n
            value = I18n.t(key, self._lang(), **kwargs)
            if isinstance(value, str) and value != key:
                return value
        except Exception:
            pass
        return fallback.format(**kwargs) if kwargs else fallback
        
    def apply_theme(self, theme: str):
        """Apply theme to the panel"""
        self.theme = 'dark' if str(theme).lower() == 'dark' else 'light'
        t = self.theme
        
        # Colors
        if t == 'dark':
            frame_border = "#3A3A40"
            frame_bg = "#25252B"
            section_border = "#3A3A40"
            section_bg = "#1E1E24"
            text_color = "#E0E0E0"
            list_bg = "#1E1E24"
            list_fg = "#E0E0E0"
            list_divider = "#3A3A40"
            list_hover = "#2A2A30"
            check_fg = "#E5E7EB"
            check_box_bg = "#020617"
            check_box_border = "#3A3A40"
            check_box_checked = "#7F56D9"
            btn_bg = "#3A3A40"
            btn_fg = "#E0E0E0"
            btn_hover = "#4A4A50"
        else:
            frame_border = "#CBD5E1"
            frame_bg = "#F8FAFC"
            section_border = "#E2E8F0"
            section_bg = "#FFFFFF"
            text_color = "#0F172A"
            list_bg = "#FFFFFF"
            list_fg = "#0F172A"
            list_divider = "#E2E8F0"
            list_hover = "#F1F5F9"
            check_fg = "#0F172A"
            check_box_bg = "#FFFFFF"
            check_box_border = "#CBD5E1"
            check_box_checked = "#7F56D9"
            btn_bg = "#E0EAFF"
            btn_fg = "#111827"
            btn_border = "#A5B4FC"
            btn_hover = "#CBD5FF"

        # Update main frame
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setStyleSheet(
                f"""
                QFrame {{
                    border: 1px solid {frame_border};
                    background-color: {frame_bg};
                    border-radius: 4px;
                }}
            """
            )

        # Update questions section
        if hasattr(self, 'questions_section'):
            self.questions_section.setStyleSheet(
                f"""
                QFrame {{
                    color: {text_color};
                    border: 1px solid {section_border};
                    border-radius: 4px;
                    margin: 5px;
                    padding: 10px;
                    background-color: {section_bg};
                }}
            """
            )
        
        if hasattr(self, 'questions_list'):
            self.questions_list.setStyleSheet(
                f"""
                QListWidget {{
                    background-color: {list_bg};
                    border: none;
                    color: {list_fg};
                    font-size: 12px;
                    outline: none;
                }}
                QListWidget::item {{
                    padding: 8px;
                    border-bottom: 1px solid {list_divider};
                }}
                QListWidget::item:hover {{
                    background-color: {list_hover};
                }}
                QListWidget::item:selected {{
                    background-color: #7F56D9;
                    color: white;
                }}
            """
            )

        # Update game config section
        if hasattr(self, 'config_section'):
            # Re-determine config section colors as they might differ in original code (simplified here to match logic)
            if t == 'dark':
                cfg_section_bg = "#111827"
                cfg_section_border = "#3A3A40"
            else:
                cfg_section_bg = "#EFF6FF"
                cfg_section_border = "#BFDBFE"
                
            self.config_section.setStyleSheet(
                f"""
                QFrame {{
                    color: {text_color};
                    border: 1px solid {cfg_section_border};
                    border-radius: 4px;
                    margin: 5px;
                    padding: 10px;
                    background-color: {cfg_section_bg};
                }}
            """
            )

        # Update checkboxes
        check_style = f"""
            QCheckBox {{ color: {check_fg}; }}
            QCheckBox::indicator {{
                width:16px;
                height:16px;
                background-color:{check_box_bg};
                border:1px solid {check_box_border};
                border-radius:3px;
            }}
            QCheckBox::indicator:checked {{
                background-color:{check_box_checked};
            }}
        """
        for attr in ['show_explanations_check', 'randomize_questions_check', 
                     'auto_points_check', 'time_limit_enabled_check', 'music_toggle']:
            if hasattr(self, attr) and getattr(self, attr):
                getattr(self, attr).setStyleSheet(check_style)
        
        # Update fishing sound buttons
        if t == 'dark':
            sound_btn_style = """
                QPushButton { background-color: #3A3A40; color: #E0E0E0; border: none; padding: 6px 10px; border-radius: 4px; }
                QPushButton:hover { background-color: #4A4A50; }
            """
        else:
            sound_btn_style = """
                QPushButton { background-color: #E0EAFF; color: #111827; border: 1px solid #A5B4FC; padding: 6px 10px; border-radius: 4px; }
                QPushButton:hover { background-color: #CBD5FF; }
            """
        for attr in ['select_bgm_btn', 'select_correct_btn', 'select_wrong_btn']:
            if hasattr(self, attr) and getattr(self, attr):
                getattr(self, attr).setStyleSheet(sound_btn_style)
        
        # Update fish list
        if hasattr(self, 'fish_list'):
            self.fish_list.setStyleSheet(self.questions_list.styleSheet())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            frame_border = "#3A3A40"
            frame_bg = "#25252B"
        else:
            frame_border = "#CBD5E1"
            frame_bg = "#F8FAFC"
        self.tab_widget = QFrame()
        self.tab_widget.setStyleSheet(
            f"""
            QFrame {{
                border: 1px solid {frame_border};
                background-color: {frame_bg};
                border-radius: 4px;
            }}
        """
        )
        
        tab_layout = QVBoxLayout(self.tab_widget)
        
        questions_section = self.create_questions_section()
        self.questions_section = questions_section
        tab_layout.addWidget(questions_section)
        
        config_section = self.create_game_config_section()
        self.config_section = config_section
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        config_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        config_scroll.setFrameShape(QFrame.NoFrame)
        config_scroll.setWidget(config_section)
        tab_layout.addWidget(config_scroll)
        
        layout.addWidget(self.tab_widget)
        
    def create_questions_section(self):
        section = QFrame()
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            section_border = "#3A3A40"
            section_bg = "#1E1E24"
            text_color = "#E0E0E0"
            list_bg = "#1E1E24"
            list_fg = "#E0E0E0"
            list_divider = "#3A3A40"
            list_hover = "#2A2A30"
        else:
            section_border = "#FFE0B2"
            section_bg = "#FFF3E0"
            text_color = "#000000"
            list_bg = "#FFFBEB"
            list_fg = "#000000"
            list_divider = "#FFCC80"
            list_hover = "#FFE0B2"
        section.setStyleSheet(
            f"""
            QFrame {{
                color: {text_color};
                border: 1px solid {section_border};
                border-radius: 4px;
                margin: 5px;
                padding: 10px;
                background-color: {section_bg};
            }}
        """
        )
        
        layout = QVBoxLayout(section)
        
        title_layout = QHBoxLayout()
        
        try:
            from eduplay.core.settings_manager import SettingsManager
            from eduplay.core.i18n import I18n
            _lang_q = SettingsManager().get_language() or 'vi'
            title_text = I18n.t('editor.questions_title', _lang_q)
            add_text = I18n.t('editor.add_question', _lang_q)
        except Exception:
            title_text = "Questions"
            add_text = "+ Add"
        title = QLabel(title_text)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        add_btn = QPushButton(add_text)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #12B76A;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0F9C5A;
            }
        """)
        add_btn.clicked.connect(self.add_question)
        title_layout.addWidget(add_btn)
        
        layout.addLayout(title_layout)
        
        self.questions_list = QListWidget()
        self.questions_list.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {list_bg};
                border: none;
                color: {list_fg};
                font-size: 12px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {list_divider};
            }}
            QListWidget::item:hover {{
                background-color: {list_hover};
            }}
            QListWidget::item:selected {{
                background-color: #7F56D9;
                color: white;
            }}
        """
        )
        self.questions_list.itemClicked.connect(self.on_question_item_clicked)
        self.questions_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.questions_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.questions_list.setMinimumHeight(220)
        layout.addWidget(self.questions_list)
        
        return section
        
    def create_game_config_section(self):
        section = QFrame()
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            section_border = "#3A3A40"
            section_bg = "#111827"
            text_color = "#E5E7EB"
            check_fg = "#E5E7EB"
            check_box_bg = "#020617"
            check_box_border = "#3A3A40"
            check_box_checked = "#7F56D9"
        else:
            section_border = "#BFDBFE"
            section_bg = "#EFF6FF"
            text_color = "#000000"
            check_fg = "#000000"
            check_box_bg = "#FFFFFF"
            check_box_border = "#BFDBFE"
            check_box_checked = "#7F56D9"
        section.setStyleSheet(
            f"""
            QFrame {{
                color: {text_color};
                border: 1px solid {section_border};
                border-radius: 4px;
                margin: 5px;
                padding: 10px;
                background-color: {section_bg};
            }}
        """
        )
        
        layout = QVBoxLayout(section)
        
        # Title
        title = QLabel(self._t("editor.left.game_config_title", "Game Configuration"))
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # Simplified game config: remove Game Type/Difficulty per requirements
        self.game_type_combo = QComboBox(); self.game_type_combo.hide()
        self.difficulty_combo = QComboBox(); self.difficulty_combo.hide()
        
        # Per-question time is controlled in the center panel; hide global time control
        self.question_time_slider = QSlider(Qt.Horizontal); self.question_time_slider.hide()
        self.question_time = QLineEdit(); self.question_time.hide()

        from PySide6.QtWidgets import QCheckBox
        try:
            from eduplay.core.settings_manager import SettingsManager
            from eduplay.core.i18n import I18n
            _lang = SettingsManager().get_language() or 'vi'
            _defaults = SettingsManager().get_game_defaults()
            _show_expl = bool(_defaults.get('show_explanations', True))
            _randomize = bool(_defaults.get('randomize_questions', True))
            _auto_points = bool(_defaults.get('auto_points_enabled', False))
        except Exception:
            _lang = 'vi'
            _show_expl, _randomize, _auto_points = True, True, False
        self.show_explanations_check = QCheckBox(I18n.t('settings.show_explanations', _lang))
        self.show_explanations_check.setChecked(_show_expl)
        self.show_explanations_check.setStyleSheet(
            f"""
            QCheckBox {{ color: {check_fg}; }}
            QCheckBox::indicator {{
                width:16px;
                height:16px;
                background-color:{check_box_bg};
                border:1px solid {check_box_border};
                border-radius:3px;
            }}
            QCheckBox::indicator:checked {{
                background-color:{check_box_checked};
            }}
        """
        )
        layout.addWidget(self.show_explanations_check)
        self.randomize_questions_check = QCheckBox(I18n.t('settings.randomize_questions', _lang))
        self.randomize_questions_check.setChecked(_randomize)
        self.randomize_questions_check.setStyleSheet(self.show_explanations_check.styleSheet())
        layout.addWidget(self.randomize_questions_check)
        try:
            self.show_explanations_check.toggled.connect(self.emit_game_config_change)
            self.randomize_questions_check.toggled.connect(self.emit_game_config_change)
        except Exception:
            pass

        from PySide6.QtWidgets import QSpinBox
        points_row = QHBoxLayout()
        points_row.addWidget(QLabel(I18n.t('settings.points_per_question', _lang)))
        self.points_spin = QSpinBox()
        self.points_spin.setRange(1, 100)
        try:
            self.points_spin.setValue(int(_defaults.get('points_per_question', 10)))
        except Exception:
            self.points_spin.setValue(10)
        points_row.addWidget(self.points_spin)
        try:
            self.auto_points_check = QCheckBox(I18n.t('settings.auto_points_enabled', _lang))
            self.auto_points_check.setChecked(_auto_points)
            self.auto_points_check.setStyleSheet(self.show_explanations_check.styleSheet())
            points_row.addWidget(self.auto_points_check)
            def _sync_points_enabled():
                try:
                    self.points_spin.setEnabled(not self.auto_points_check.isChecked())
                except Exception:
                    pass
            self.auto_points_check.toggled.connect(self.emit_game_config_change)
            self.auto_points_check.toggled.connect(_sync_points_enabled)
            _sync_points_enabled()
        except Exception:
            self.auto_points_check = None
        layout.addLayout(points_row)
        self.points_spin.valueChanged.connect(self.emit_game_config_change)

        self.time_limit_enabled_check = QCheckBox(I18n.t('settings.time_limit_enabled', _lang))
        try:
            self.time_limit_enabled_check.setChecked(bool(_defaults.get('time_limit_enabled', True)))
        except Exception:
            self.time_limit_enabled_check.setChecked(True)
        self.time_limit_enabled_check.setStyleSheet(self.show_explanations_check.styleSheet())
        layout.addWidget(self.time_limit_enabled_check)
        self.time_limit_enabled_check.toggled.connect(self.emit_game_config_change)

        # Lifeline hints
        self.hint_title = QLabel(I18n.t('lifeline.hints_title', _lang))
        self.hint_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.hint_title)
        from PySide6.QtWidgets import QTextEdit
        self.phone_hint_edit = QTextEdit()
        self.phone_hint_edit.setPlaceholderText(I18n.t('lifeline.phone_hint_placeholder', _lang))
        self.phone_hint_edit.setFixedHeight(60)
        self.phone_hint_edit.textChanged.connect(self.emit_game_config_change)
        layout.addWidget(self.phone_hint_edit)
        self.audience_hint_edit = QTextEdit()
        self.audience_hint_edit.setPlaceholderText(I18n.t('lifeline.audience_hint_placeholder', _lang))
        self.audience_hint_edit.setFixedHeight(60)
        self.audience_hint_edit.textChanged.connect(self.emit_game_config_change)
        layout.addWidget(self.audience_hint_edit)

        self.fishing_title = QLabel(I18n.t('fishing.settings_title', _lang))
        self.fishing_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.fishing_title)

        count_row = QHBoxLayout()
        count_row.addWidget(QLabel(I18n.t('fishing.count', _lang)))
        from PySide6.QtWidgets import QSpinBox, QDoubleSpinBox
        self.fish_count_spin = QSpinBox()
        self.fish_count_spin.setRange(5, 20)
        self.fish_count_spin.setValue(10)
        count_row.addWidget(self.fish_count_spin)
        count_row.addStretch()
        layout.addLayout(count_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel(I18n.t('fishing.base_speed', _lang)))
        self.base_speed_spin = QDoubleSpinBox()
        self.base_speed_spin.setRange(1.0, 5.0)
        self.base_speed_spin.setSingleStep(0.1)
        self.base_speed_spin.setValue(2.5)
        speed_row.addWidget(self.base_speed_spin)
        speed_row.addStretch()
        layout.addLayout(speed_row)

        sounds_row = QHBoxLayout()
        self.select_bgm_btn = QPushButton(I18n.t('fishing.select_bgm', _lang))
        self.select_correct_btn = QPushButton(I18n.t('fishing.select_correct', _lang))
        self.select_wrong_btn = QPushButton(I18n.t('fishing.select_wrong', _lang))
        if theme == 'dark':
            btn_style = """
                QPushButton { background-color: #3A3A40; color: #E0E0E0; border: none; padding: 6px 10px; border-radius: 4px; }
                QPushButton:hover { background-color: #4A4A50; }
            """
        else:
            btn_style = """
                QPushButton { background-color: #E0EAFF; color: #111827; border: 1px solid #A5B4FC; padding: 6px 10px; border-radius: 4px; }
                QPushButton:hover { background-color: #CBD5FF; }
            """
        for b in [self.select_bgm_btn, self.select_correct_btn, self.select_wrong_btn]:
            b.setStyleSheet(btn_style)
        sounds_row.addWidget(self.select_bgm_btn)
        sounds_row.addWidget(self.select_correct_btn)
        sounds_row.addWidget(self.select_wrong_btn)
        layout.addLayout(sounds_row)

        from PySide6.QtWidgets import QCheckBox
        self.music_toggle = QCheckBox(I18n.t('fishing.music_toggle', _lang))
        self.music_toggle.setChecked(True)
        self.music_toggle.setStyleSheet(f"QCheckBox {{ color: {check_fg}; }}")
        layout.addWidget(self.music_toggle)

        self.fish_list_label = QLabel(I18n.t('fishing.list_label', _lang))
        layout.addWidget(self.fish_list_label)
        from PySide6.QtWidgets import QListWidget, QListWidgetItem
        self.fish_list = QListWidget()
        try:
            from PySide6.QtWidgets import QSizePolicy as QSP
            self.fish_list.setSizePolicy(QSP.Expanding, QSP.Expanding)
            self.fish_list.setMinimumHeight(120)
        except Exception:
            pass
        self.fish_list.setStyleSheet(self.questions_list.styleSheet())
        layout.addWidget(self.fish_list)

        fish_btn_row = QHBoxLayout()
        self.add_fish_btn = QPushButton(I18n.t('fishing.add', _lang))
        self.add_fish_bundle_btn = QPushButton(I18n.t('fishing.add_bundle', _lang))
        self.remove_fish_btn = QPushButton(I18n.t('fishing.remove', _lang))
        for b in [self.add_fish_btn, self.remove_fish_btn]:
            b.setStyleSheet("""
                QPushButton { background-color: #7F56D9; color: #fff; border: none; padding: 6px 10px; border-radius: 4px; }
                QPushButton:hover { background-color: #6A48C0; }
            """)
        fish_btn_row.addWidget(self.add_fish_btn)
        fish_btn_row.addWidget(self.add_fish_bundle_btn)
        fish_btn_row.addWidget(self.remove_fish_btn)
        layout.addLayout(fish_btn_row)

        self.select_bgm_btn.clicked.connect(lambda: self._pick_sound('background_music'))
        self.select_correct_btn.clicked.connect(lambda: self._pick_sound('correct_sound'))
        self.select_wrong_btn.clicked.connect(lambda: self._pick_sound('wrong_sound'))
        self.add_fish_btn.clicked.connect(self._add_fish_dialog)
        self.remove_fish_btn.clicked.connect(self._remove_selected_fish)
        self.add_fish_bundle_btn.clicked.connect(self._add_fish_from_bundle)

        # Simplified signals
        self.game_type_combo.currentTextChanged.connect(self.emit_game_config_change)
        self.base_speed_spin.valueChanged.connect(self.emit_game_config_change)
        self.fish_count_spin.valueChanged.connect(self.emit_game_config_change)
        self.music_toggle.toggled.connect(self.emit_game_config_change)
        
        layout.addStretch()
        return section
        
    def set_project(self, project):
        """Load project data into the panel"""
        self.current_project = project
        self.load_questions()
        self.load_game_config()
        try:
            gt_text = self._current_game_type_text()
            self._apply_visibility_by_type(gt_text)
        except Exception:
            pass
        
    def load_questions(self):
        """Load questions from current project"""
        self.questions_list.clear()
        
        if self.current_project and 'questions' in self.current_project:
            for i, question in enumerate(self.current_project['questions']):
                q_text = question.get('question', self._t('editor.left.untitled_question', 'Untitled Question'))
                q_type = question.get('type', 'multiple_choice')
                
                # Create display text
                display_text = f"Q{i+1}: {q_text[:50]}"
                if len(q_text) > 50:
                    display_text += "..."
                
                # Add type indicator
                type_icons = {
                    'multiple_choice': "📝",
                    'true_false': "✅",
                    'fill_blank': "📝",
                    'matching': "🔗",
                    'short_answer': "💬",
                    'essay': "📄"
                }
                icon = type_icons.get(q_type, "❓")
                extra = ""
                try:
                    if q_type == 'multiple_choice':
                        opts = question.get('options') or []
                        ca = question.get('correct_answer', 0)
                        def _opt_text_by_index(k):
                            try:
                                if isinstance(k, int) and 0 <= k < len(opts):
                                    return opts[k]
                            except Exception:
                                pass
                            return ""
                        if isinstance(ca, str):
                            try:
                                letters = [chr(65 + j) for j in range(max(2, len(opts)))]
                            except Exception:
                                letters = ['A','B','C','D']
                            uc = ca.strip().upper()
                            if uc in letters:
                                idx = letters.index(uc)
                                txt = _opt_text_by_index(idx)
                                extra = f" ✓ {uc}" + (f" – {txt}" if txt else "")
                            else:
                                try:
                                    idx = opts.index(ca)
                                    txt = _opt_text_by_index(idx)
                                    extra = f" ✓ {chr(65 + idx)}" + (f" – {txt}" if txt else "")
                                except Exception:
                                    extra = ""
                        else:
                            try:
                                idx = int(ca)
                                if idx >= 0:
                                    txt = _opt_text_by_index(idx)
                                    extra = f" ✓ {chr(65 + idx)}" + (f" – {txt}" if txt else "")
                            except Exception:
                                extra = ""
                except Exception:
                    extra = ""
                display_text = f"{icon} {display_text}{extra}"
                
                # Create list item
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, question)  # Store question data
                self.questions_list.addItem(item)
        
        # Select first item if available
        if self.questions_list.count() > 0:
            self.questions_list.setCurrentRow(0)
            first_item = self.questions_list.item(0)
            if first_item:
                question_data = first_item.data(Qt.UserRole)
                self.question_selected.emit(question_data)

    def load_questions_silent(self):
        """Reload questions without emitting selection to avoid recursion"""
        try:
            row = self.questions_list.currentRow()
        except Exception:
            row = -1
        self.questions_list.clear()
        if self.current_project and 'questions' in self.current_project:
            for i, question in enumerate(self.current_project['questions']):
                q_text = question.get('question', self._t('editor.left.untitled_question', 'Untitled Question'))
                q_type = question.get('type', 'multiple_choice')
                display_text = f"Q{i+1}: {q_text[:50]}" + ("..." if len(q_text) > 50 else "")
                type_icons = {
                    'multiple_choice': "📝",
                    'true_false': "✅",
                    'fill_blank': "📝",
                    'matching': "🔗",
                    'short_answer': "💬",
                    'essay': "📄"
                }
                icon = type_icons.get(q_type, "❓")
                extra = ""
                try:
                    if q_type == 'multiple_choice':
                        opts = question.get('options') or []
                        ca = question.get('correct_answer', 0)
                        def _opt_text_by_index(k):
                            try:
                                if isinstance(k, int) and 0 <= k < len(opts):
                                    return opts[k]
                            except Exception:
                                pass
                            return ""
                        if isinstance(ca, str):
                            try:
                                letters = [chr(65 + j) for j in range(max(2, len(opts)))]
                            except Exception:
                                letters = ['A','B','C','D']
                            uc = ca.strip().upper()
                            if uc in letters:
                                idx = letters.index(uc)
                                txt = _opt_text_by_index(idx)
                                extra = f" ✓ {uc}" + (f" – {txt}" if txt else "")
                            else:
                                try:
                                    idx = opts.index(ca)
                                    txt = _opt_text_by_index(idx)
                                    extra = f" ✓ {chr(65 + idx)}" + (f" – {txt}" if txt else "")
                                except Exception:
                                    extra = ""
                        else:
                            try:
                                idx = int(ca)
                                if idx >= 0:
                                    txt = _opt_text_by_index(idx)
                                    extra = f" ✓ {chr(65 + idx)}" + (f" – {txt}" if txt else "")
                            except Exception:
                                extra = ""
                except Exception:
                    extra = ""
                display_text = f"{icon} {display_text}{extra}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, question)
                self.questions_list.addItem(item)
        try:
            if row >= 0 and row < self.questions_list.count():
                self.questions_list.setCurrentRow(row)
        except Exception:
            pass
            
    def load_game_config(self):
        """Load game configuration"""
        if self.current_project and 'game_config' in self.current_project:
            config = self.current_project['game_config']
            if config:  # Check if config is not None
                # Set game type
                game_type = config.get('game_type', 'Quiz Classic')
                # hidden control; keep value only in cfg
                
                # difficulty hidden
                
                # global time hidden
                try:
                    if hasattr(self, 'fish_speed_spin'):
                        self.fish_speed_spin.setValue(int(config.get('speed', 5)))
                    self.fish_list.clear()
                    fishes = config.get('fish_objects') or []
                    self._fish_objects = list(fishes)
                    for f in fishes:
                        from PySide6.QtWidgets import QListWidgetItem
                        item = QListWidgetItem(os.path.basename(f.get('sprite','')) or 'Fish')
                        item.setData(Qt.UserRole, f)
                        self.fish_list.addItem(item)
                    self._sounds = {}
                    for k in ['background_music','correct_sound','wrong_sound']:
                        if config.get(k):
                            self._sounds[k] = config.get(k)
                    try:
                        if hasattr(self, 'points_spin') and 'points_per_question' in config:
                            self.points_spin.setValue(int(config.get('points_per_question', self.points_spin.value())))
                        if hasattr(self, 'auto_points_check') and self.auto_points_check is not None:
                            self.auto_points_check.setChecked(bool(config.get('auto_points_enabled', self.auto_points_check.isChecked())))
                            try:
                                self.points_spin.setEnabled(not self.auto_points_check.isChecked())
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
            else:
                # Set default values if config is None
                self.game_type_combo.setCurrentIndex(0)  # Quiz Classic
                self.difficulty_combo.setCurrentIndex(1)  # Medium
                self.question_time.setText('30')
        else:
            # Set default values if no game_config exists
            self.game_type_combo.setCurrentIndex(0)  # Quiz Classic
            self.difficulty_combo.setCurrentIndex(1)  # Medium
            self.question_time.setText('30')
            
    def add_question(self):
        """Add a new question"""
        if self.current_project:
            # Get current game config to set default values
            game_config = self.get_game_config()
            game_type = game_config.get('game_type', 'Quiz Classic')
            try:
                from eduplay.core.settings_manager import SettingsManager
                default_time = int(SettingsManager().get('game_defaults.quiz_time_per_question', 30))
            except Exception:
                default_time = 30
            
            # Create appropriate question based on game type
            if game_type == "Fishing Game":
                new_question = {
                    'question': 'Catch the fish with the correct answer',
                    'type': 'multiple_choice',
                    'options': ['Answer A', 'Answer B', 'Answer C', 'Answer D'],
                    'correct_answer': 0,
                    'explanation': 'This is a fishing game question. The correct answer fish should be caught.',
                    'time_limit': int(game_config.get('question_time', default_time)),
                    'fish_config': {
                        'speed': 2,
                        'size': 'medium',
                        'color': 'blue'
                    }
                }
            else:
                # Default quiz question
                new_question = {
                    'question': 'New Question',
                    'type': 'multiple_choice',
                    'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                    'correct_answer': 0,
                    'explanation': '',
                    'time_limit': int(game_config.get('question_time', default_time))
                }
            try:
                import uuid
                new_question["id"] = f"q_{uuid.uuid4().hex[:10]}"
            except Exception:
                pass
            
            if 'questions' not in self.current_project:
                self.current_project['questions'] = []
            self.current_project['questions'].append(new_question)
            
            self.load_questions()
            
            # Select the newly added question
            if self.questions_list.count() > 0:
                self.questions_list.setCurrentRow(self.questions_list.count() - 1)
                last_item = self.questions_list.item(self.questions_list.count() - 1)
                if last_item:
                    question_data = last_item.data(Qt.UserRole)
                    self.question_selected.emit(question_data)
            
    def on_question_item_clicked(self, item):
        """Handle question item click"""
        question_data = item.data(Qt.UserRole)
        if question_data:
            self.question_selected.emit(question_data)
            
    def get_game_config(self):
        """Get current game configuration"""
        # Use existing project config values for hidden controls
        existing_cfg = {}
        try:
            if self.current_project and isinstance(self.current_project.get('game_config'), dict):
                existing_cfg = dict(self.current_project.get('game_config') or {})
        except Exception:
            existing_cfg = {}
        cfg = {
            'game_type': existing_cfg.get('game_type', self.game_type_combo.currentText() or 'Quiz Classic'),
            'difficulty': existing_cfg.get('difficulty', 'Medium'),
            'question_time': int(existing_cfg.get('question_time', 30)),
            'show_explanations': bool(self.show_explanations_check.isChecked()) if hasattr(self, 'show_explanations_check') else True,
            'randomize_questions': bool(self.randomize_questions_check.isChecked()) if hasattr(self, 'randomize_questions_check') else True,
            'points_per_question': int(self.points_spin.value()) if hasattr(self, 'points_spin') else 10,
            'auto_points_enabled': bool(self.auto_points_check.isChecked()) if hasattr(self, 'auto_points_check') and self.auto_points_check is not None else False,
            'time_limit_enabled': bool(self.time_limit_enabled_check.isChecked()) if hasattr(self, 'time_limit_enabled_check') else True,
            'cute_effects': True
        }
        # Lifeline hints for Millionaire only
        try:
            gt_text = self._current_game_type_text().lower()
            is_millionaire = (gt_text in ('quiz_millionaire','millionaire')) or ('triệu phú' in gt_text) or ('ai la trieu phu' in gt_text)
            if is_millionaire:
                cfg['lifeline_phone_hint'] = (self.phone_hint_edit.toPlainText() or '').strip()
                cfg['lifeline_audience_hint'] = (self.audience_hint_edit.toPlainText() or '').strip()
        except Exception:
            pass
        # Fishing settings only for fishing
        gt_lower = str(cfg.get('game_type') or '').lower()
        
        # Use the same fishing detection logic as export_service.py
        def _looks_like_fishing_config(cfg_dict: dict) -> bool:
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
        
        # Get game config to check for fishing keys
        try:
            from eduplay.core.project_manager import ProjectManager
            pm = ProjectManager()
            current_project = pm.get_current_project()
            cfg_full = (current_project.get('game_config', {}) or {}) if current_project else {}
        except Exception:
            cfg_full = {}
        
        has_fishing_keys = _looks_like_fishing_config(cfg_full)
        is_fishing = (
            gt_lower == 'fishing'
            or 'fishing' in gt_lower
            or 'fish' in gt_lower
            or gt_lower in ('bat_ca', 'bắt cá', 'tro_choi_cau_ca', 'trò_chơi_câu_cá')
            or gt_lower in ('fishing game', 'tro choi cau ca', 'trò chơi câu cá')
            or has_fishing_keys
        )
        
        if is_fishing:
            cfg['fish_count'] = int(self.fish_count_spin.value()) if hasattr(self, 'fish_count_spin') else 10
            cfg['base_speed'] = float(self.base_speed_spin.value()) if hasattr(self, 'base_speed_spin') else 2.5
            cfg['fish_objects'] = getattr(self, '_fish_objects', []) if hasattr(self, '_fish_objects') else []
            if hasattr(self, '_sounds'):
                cfg.update(self._sounds)
            if getattr(self, '_bg_selected', ''):
                rel = 'assets/kenney_platformer-kit/PNG/Default/' + os.path.basename(self._bg_selected)
                cfg['background_image'] = rel
            cfg['music_volume'] = 0.5
            cfg['click_sound'] = cfg.get('click_sound') or 'assets/sound/click.wav'
            cfg.setdefault('fish_size', 'Vừa')
        return cfg

    def emit_game_config_change(self):
        config = self.get_game_config()
        self.game_config_changed.emit(config)

    def _on_game_type_changed(self, text: str):
        if text == 'Fishing Game':
            self._ensure_fishing_defaults()
        try:
            self._apply_visibility_by_type(text)
        except Exception:
            pass
        self.emit_game_config_change()

    def _ensure_fishing_defaults(self):
        try:
            if not hasattr(self, '_fish_objects') or not self._fish_objects:
                base = 'assets/kenney_platformer-kit/PNG/Default'
                fishes = [
                    {'sprite': f'{base}/fish_blue.png', 'wrong_sprite': f'{base}/fish_blue_skeleton.png', 'sound': ''},
                    {'sprite': f'{base}/fish_green.png', 'wrong_sprite': f'{base}/fish_green_skeleton.png', 'sound': ''},
                    {'sprite': f'{base}/fish_orange.png', 'wrong_sprite': f'{base}/fish_orange_skeleton.png', 'sound': ''},
                    {'sprite': f'{base}/fish_pink.png', 'wrong_sprite': f'{base}/fish_pink_skeleton.png', 'sound': ''},
                    {'sprite': f'{base}/fish_red.png', 'wrong_sprite': f'{base}/fish_red_skeleton.png', 'sound': ''},
                ]
                self._fish_objects = fishes
                self.fish_list.clear()
                for f in fishes:
                    item = QListWidgetItem(os.path.basename(f['sprite']))
                    item.setData(Qt.UserRole, f)
                    self.fish_list.addItem(item)
            if not hasattr(self, '_sounds'):
                self._sounds = {}
            self._sounds.setdefault('background_music', 'assets/sound/background.mp3')
            self._sounds.setdefault('correct_sound', 'assets/sound/correct.wav')
            self._sounds.setdefault('wrong_sound', 'assets/sound/wrong.wav')
            self._sounds.setdefault('click_sound', 'assets/sound/click.wav')
        except Exception:
            pass

    def _current_game_type_text(self) -> str:
        try:
            top_gt = str((self.current_project or {}).get('game_type') or '').strip()
        except Exception:
            top_gt = ''
        try:
            cfg_gt = str(((self.current_project or {}).get('game_config') or {}).get('game_type') or '').strip()
        except Exception:
            cfg_gt = ''
        return top_gt or cfg_gt or self.game_type_combo.currentText() or ''

    def _apply_visibility_by_type(self, gt_text: str):
        s = str(gt_text or '').lower()
        is_millionaire = (s in ('quiz_millionaire','millionaire')) or ('triệu phú' in s) or ('ai là triệu phú' in s) or ('ai la trieu phu' in s)
        
        # Use the same fishing detection logic as export_service.py
        def _looks_like_fishing_config(cfg_dict: dict) -> bool:
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
        
        # Get game config to check for fishing keys
        try:
            from eduplay.core.project_manager import ProjectManager
            pm = ProjectManager()
            current_project = pm.get_current_project()
            cfg_full = (current_project.get('game_config', {}) or {}) if current_project else {}
        except Exception:
            cfg_full = {}
        
        has_fishing_keys = _looks_like_fishing_config(cfg_full)
        is_fishing = (
            s == 'fishing'
            or 'fishing' in s
            or 'fish' in s
            or s in ('bat_ca', 'bắt cá', 'tro_choi_cau_ca', 'trò_chơi_câu_cá')
            or s in ('fishing game', 'tro choi cau ca', 'trò chơi câu cá')
            or has_fishing_keys
        )
        try:
            # Lifeline hints visible only for Millionaire
            self.hint_title.setVisible(is_millionaire)
            self.phone_hint_edit.setVisible(is_millionaire)
            self.audience_hint_edit.setVisible(is_millionaire)
        except Exception:
            pass
        try:
            # Fishing settings visible only for Fishing
            self.fishing_title.setVisible(is_fishing)
            self.fish_count_spin.setVisible(is_fishing)
            self.base_speed_spin.setVisible(is_fishing)
            self.select_bgm_btn.setVisible(is_fishing)
            self.select_correct_btn.setVisible(is_fishing)
            self.select_wrong_btn.setVisible(is_fishing)
            self.music_toggle.setVisible(is_fishing)
            self.fish_list_label.setVisible(is_fishing)
            self.fish_list.setVisible(is_fishing)
            self.add_fish_btn.setVisible(is_fishing)
            self.add_fish_bundle_btn.setVisible(is_fishing)
            self.remove_fish_btn.setVisible(is_fishing)
        except Exception:
            pass
    def _pick_sound(self, key: str):
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("editor.left.select_sound_title", "Select Sound"),
            os.path.expanduser("~"),
            self._t("editor.left.audio_files_filter", "Audio Files (*.mp3 *.wav)")
        )
        if file_path:
            if not hasattr(self, '_sounds'):
                self._sounds = {}
            self._sounds[key] = file_path
            self.emit_game_config_change()

    def _add_fish_dialog(self):
        from PySide6.QtWidgets import QFileDialog
        sprite_path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("editor.left.select_fish_sprite_title", "Select Fish Sprite"),
            os.path.expanduser("~"),
            self._t("editor.left.image_files_filter", "Images (*.png *.jpg *.jpeg)")
        )
        if not sprite_path:
            return
        wrong_path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("editor.left.select_wrong_sprite_title", "Select Wrong Sprite (Skeleton)"),
            os.path.expanduser("~"),
            self._t("editor.left.image_files_filter", "Images (*.png *.jpg *.jpeg)")
        )
        sound_path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("editor.left.select_fish_sound_title", "Select Fish Sound (optional)"),
            os.path.expanduser("~"),
            self._t("editor.left.audio_files_filter", "Audio Files (*.mp3 *.wav)")
        )
        fish = {'sprite': sprite_path, 'wrong_sprite': wrong_path or '', 'sound': sound_path or ''}
        if not hasattr(self, '_fish_objects'):
            self._fish_objects = []
        self._fish_objects.append(fish)
        item = QListWidgetItem(os.path.basename(sprite_path))
        item.setData(Qt.UserRole, fish)
        self.fish_list.addItem(item)
        self.emit_game_config_change()

    def _add_fish_from_bundle(self):
        from PySide6.QtWidgets import QFileDialog
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../assets_bundle/kenney_platformer-kit/PNG"))
        sprite_path, _ = QFileDialog.getOpenFileName(
            self,
            self._t("editor.left.select_bundle_fish_sprite_title", "Choose fish sprite from bundle"),
            base,
            self._t("editor.left.bundle_image_filter", "Images (*.png)")
        )
        if not sprite_path:
            return
        name = os.path.basename(sprite_path)
        root, ext = os.path.splitext(sprite_path)
        if "_skeleton" in name:
            wrong_path = sprite_path
            main_guess = sprite_path.replace("_skeleton", "")
            sprite_candidate = main_guess if os.path.exists(main_guess) else sprite_path
            sprite_path = sprite_candidate
        else:
            wrong_guess = root + "_skeleton" + ext
            wrong_path = wrong_guess if os.path.exists(wrong_guess) else ''
        fish = {'sprite': sprite_path, 'wrong_sprite': wrong_path, 'sound': ''}
        if not hasattr(self, '_fish_objects'):
            self._fish_objects = []
        self._fish_objects.append(fish)
        item = QListWidgetItem(os.path.basename(sprite_path))
        item.setData(Qt.UserRole, fish)
        self.fish_list.addItem(item)
        self.emit_game_config_change()

    def _remove_selected_fish(self):
        row = self.fish_list.currentRow()
        if row >= 0:
            self.fish_list.takeItem(row)
            if hasattr(self, '_fish_objects') and row < len(self._fish_objects):
                self._fish_objects.pop(row)
            self.emit_game_config_change()
        # Removed invalid layout reference to avoid runtime errors

