"""
New Project Screen - Screen for creating new projects
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QPushButton,
                               QLabel, QFrame, QSpacerItem, QSizePolicy,
                               QToolButton)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QPalette, QColor
from eduplay.core.i18n import I18n
from eduplay.core.settings_manager import SettingsManager
from eduplay.ui.icon_factory import build_line_icon, build_standard_ui_icon, strip_icon_text
from eduplay.ui.widgets.custom_dropdown import FlatDropdown

class NewProjectScreen(QWidget):
    """Screen for creating new projects"""
    
    # Signals
    project_created = Signal(dict)
    back_clicked = Signal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        self._settings = SettingsManager()
        self._lang = self._settings.get_language() or 'vi'
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create header
        self.create_header(layout)
        
        # Create form area
        self.create_form_area(layout)
        
        self.setLayout(layout)
        self.apply_theme()
    
    def create_header(self, layout):
        """Create header with back button and title"""
        header = QFrame()
        header.setObjectName("header")
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 14, 24, 14)
        header_layout.setSpacing(12)
        
        # Back button
        self.back_btn = QPushButton(strip_icon_text(I18n.t('new.back', self._lang)))
        self.back_btn.setObjectName("secondary-button")
        try:
            self.back_btn.setIcon(build_line_icon("back", "#7F56D9", 16))
        except Exception:
            pass
        self.back_btn.clicked.connect(self.back_clicked.emit)
        header_layout.addWidget(self.back_btn)
        
        header_layout.addStretch()
        
        # Title
        self.title_label = QLabel(I18n.t('new.title', self._lang))
        self.title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        layout.addWidget(header)
    
    def create_form_area(self, layout):
        """Create form area"""
        # Center container
        center_container = QWidget()
        center_layout = QHBoxLayout(center_container)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setContentsMargins(32, 28, 32, 28)
        
        # Form container
        self.form_container = QFrame()
        self.form_container.setObjectName("form-container")
        self.form_container.setMaximumWidth(920)
        
        form_layout = QVBoxLayout(self.form_container)
        form_layout.setContentsMargins(32, 30, 32, 26)
        form_layout.setSpacing(18)
        
        self.form_title = QLabel(I18n.t('new.form_title', self._lang))
        try:
            theme = self._settings.get_theme() or 'dark'
        except Exception:
            theme = 'dark'
        if theme == 'dark':
            form_title_color = "#FFFFFF"
            form_subtitle_color = "#A0AEC0"
        else:
            form_title_color = "#7F56D9"
            form_subtitle_color = "#475467"
        self.form_title.setStyleSheet(
            f"""
            QLabel {{
                color: {form_title_color};
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 10px;
            }}
        """
        )
        form_layout.addWidget(self.form_title)
        
        self.form_subtitle = QLabel(I18n.t('new.form_subtitle', self._lang))
        self.form_subtitle.setStyleSheet(
            f"""
            QLabel {{
                color: {form_subtitle_color};
                font-size: 16px;
                margin-bottom: 30px;
            }}
        """
        )
        form_layout.addWidget(self.form_subtitle)
        
        # Form fields
        form = QFormLayout()
        form.setSpacing(20)
        form.setLabelAlignment(Qt.AlignTop | Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18)
        
        # Project name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(I18n.t('new.name_placeholder', self._lang))
        self.name_input.textChanged.connect(self.validate_form)
        form.addRow(I18n.t('new.name_label', self._lang), self.name_input)
        
        # Project description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText(I18n.t('new.desc_placeholder', self._lang))
        self.description_input.setMaximumHeight(100)
        self.description_input.textChanged.connect(self.validate_form)
        form.addRow(I18n.t('new.desc_label', self._lang), self.description_input)
        
        # Game type dropdown styled like the new mockup
        self.game_type_dropdown = FlatDropdown()
        self.game_type_dropdown.setObjectName("game-type-dropdown")
        self.game_type_dropdown.max_visible_items = 4
        self.game_type_dropdown.currentTextChanged.connect(self.validate_form)
        self._populate_game_type_dropdown()
        form.addRow(I18n.t('new.type_label', self._lang), self.game_type_dropdown)
        
        form_layout.addLayout(form)
        
        # Spacer
        form_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # Cancel button
        self.cancel_btn = QPushButton(I18n.t('new.cancel', self._lang))
        self.cancel_btn.setObjectName("secondary-button")
        self.cancel_btn.clicked.connect(self.back_clicked.emit)
        button_layout.addWidget(self.cancel_btn)
        
        # Create button
        self.create_btn = QPushButton(I18n.t('new.create', self._lang))
        self.create_btn.setObjectName("primary-button")
        self.create_btn.clicked.connect(self.create_project)
        self.create_btn.setEnabled(False)
        button_layout.addWidget(self.create_btn)
        
        form_layout.addLayout(button_layout)
        
        center_layout.addWidget(self.form_container)
        layout.addWidget(center_container, 1)  # Take remaining space

    def apply_theme(self, theme: str | None = None):
        """Apply theme-specific styling for this screen and its widgets."""
        try:
            current_theme = theme or (self._settings.get_theme() or 'dark')
        except Exception:
            current_theme = 'dark'
        
        if current_theme == 'dark':
            root_bg = '#161925'
            header_bg = '#161925'
            header_border = '#2A3142'
            form_bg = '#202638'
            header_title_color = "#FFFFFF"
            form_title_color = "#FFFFFF"
            form_subtitle_color = "#A0AEC0"
            form_border = "#2A3142"
            icon_btn_bg = "#1F2937"
            icon_btn_hover = "#2B3548"
            icon_btn_border = "#344054"
        else:
            root_bg = '#F5F7FB'
            header_bg = '#FFFFFF'
            header_border = '#E2E8F0'
            form_bg = '#FFFFFF'
            header_title_color = "#1A1A1A"
            form_title_color = "#7F56D9"
            form_subtitle_color = "#475467"
            form_border = '#E4E7EC'
            icon_btn_bg = '#FFFFFF'
            icon_btn_hover = '#F9FAFB'
            icon_btn_border = '#D0D5DD'
        
        self.setStyleSheet(
            f"""
            NewProjectScreen {{
                background-color: {root_bg};
            }}
            QFrame#header {{
                background-color: {header_bg};
                border-bottom: 1px solid {header_border};
            }}
            QFrame#form-container {{
                background-color: {form_bg};
                border: 1px solid {form_border};
                border-radius: 18px;
            }}
            QToolButton#header-icon-btn {{
                background-color: {icon_btn_bg};
                border: 1px solid {icon_btn_border};
                border-radius: 10px;
                padding: 0px;
            }}
            QToolButton#header-icon-btn:hover {{
                background-color: {icon_btn_hover};
            }}
        """
        )
        
        try:
            self.title_label.setStyleSheet(
                f"QLabel{{color:{header_title_color};font-size:24px;font-weight:700;}}"
            )
            self.form_title.setStyleSheet(
                f"QLabel{{color:{form_title_color};font-size:28px;font-weight:700;margin-bottom:10px;}}"
            )
            self.form_subtitle.setStyleSheet(
                f"QLabel{{color:{form_subtitle_color};font-size:16px;margin-bottom:20px;}}"
            )
            
            # Input fields styling
            input_bg = "rgba(30, 30, 40, 0.8)" if current_theme == 'dark' else "#FFFFFF"
            input_color = "#FFFFFF" if current_theme == 'dark' else "#1A1A1A"
            input_border = "1px solid #4A5568" if current_theme == 'dark' else "1px solid #D0D5DD"
            placeholder_color = "#A0AEC0" if current_theme == 'dark' else "#98A2B3"
            
            input_style = f"""
                background-color: {input_bg};
                color: {input_color};
                border: {input_border};
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            """
            
            if hasattr(self, 'name_input'):
                self.name_input.setStyleSheet(f"QLineEdit {{ {input_style} }} QLineEdit::placeholder {{ color: {placeholder_color}; }}")
                
            if hasattr(self, 'description_input'):
                self.description_input.setStyleSheet(f"QTextEdit {{ {input_style} }} QTextEdit::placeholder {{ color: {placeholder_color}; }}")
            if hasattr(self, 'game_type_dropdown'):
                self.game_type_dropdown.button.setMinimumHeight(48)
                self.game_type_dropdown.button.setStyleSheet(
                    f"""
                    QToolButton {{
                        background-color: {input_bg};
                        color: {input_color};
                        border: {input_border};
                        border-radius: 10px;
                        padding: 0px 14px;
                        font-size: 14px;
                        font-weight: 600;
                        text-align: left;
                    }}
                    QToolButton:hover {{
                        border: 1px solid #7F56D9;
                    }}
                    """
                )
                self.game_type_dropdown.popup.setStyleSheet(
                    f"""
                    QFrame#FlatDropdownPopup {{
                        background-color: {form_bg};
                        border: 1px solid {form_border};
                        border-radius: 10px;
                    }}
                    QListView {{
                        background-color: transparent;
                        color: {input_color};
                        border: none;
                        outline: none;
                    }}
                    QListView::item {{
                        min-height: 40px;
                        padding: 8px 12px;
                    }}
                    QListView::item:selected {{
                        background-color: #5B2BE1;
                        color: #FFFFFF;
                    }}
                    QListView::item:hover:!selected {{
                        background-color: {icon_btn_hover};
                    }}
                    """
                )
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            w = self.width()
            # Responsive margins/padding
            w_scale = w/1200.0 if w else 1.0
            h_scale = self.height()/800.0 if self.height() else 1.0
            scale = max(0.82, min(1.28, min(w_scale, h_scale)))
            available_width = max(360, w - 96)
            maxw = int(min(920, max(560, min(available_width, w * 0.72))))
            theme = self._settings.get_theme() or 'dark'
            form_bg = '#202638' if theme == 'dark' else '#FFFFFF'
            form_border = '#2A3142' if theme == 'dark' else '#E4E7EC'
            self.form_container.setStyleSheet(f"""
                QFrame#form-container {{
                    background-color: {form_bg};
                    border: 1px solid {form_border};
                    border-radius: 18px;
                }}
            """)
            self.form_container.setMaximumWidth(maxw)
            self.form_container.setMinimumWidth(min(maxw, 720))
            self.set_scale(scale)
        except Exception:
            pass

    def set_scale(self, scale: float):
        try:
            theme = self._settings.get_theme() or 'dark'
            if theme == 'dark':
                header_title_color = "#FFFFFF"
                form_title_color = "#FFFFFF"
                form_subtitle_color = "#A0AEC0"
            else:
                header_title_color = "#1A1A1A"
                form_title_color = "#7F56D9"
                form_subtitle_color = "#475467"
            tsize = max(20, int(24 * scale))
            self.title_label.setStyleSheet(
                f"QLabel{{color:{header_title_color};font-size:{tsize}px;font-weight:700;}}"
            )
            fts = max(24, int(28 * scale))
            self.form_title.setStyleSheet(
                f"QLabel{{color:{form_title_color};font-size:{fts}px;font-weight:700;margin-bottom:{int(10*scale)}px;}}"
            )
            fss = max(14, int(16 * scale))
            self.form_subtitle.setStyleSheet(
                f"QLabel{{color:{form_subtitle_color};font-size:{fss}px;margin-bottom:{int(20*scale)}px;}}"
            )
            h = max(40, int(48 * scale))
            for btn in [self.back_btn, self.cancel_btn, self.create_btn]:
                if btn:
                    btn.setFixedHeight(h)
                    bf = btn.font()
                    bf.setPointSize(max(12, int(h*0.36)))
                    btn.setFont(bf)
            if hasattr(self, "game_type_dropdown") and self.game_type_dropdown:
                self.game_type_dropdown.button.setFixedHeight(h)
        except Exception:
            pass
    
    def validate_form(self):
        """Validate form inputs"""
        name = self.name_input.text().strip()
        is_valid = bool(name) and bool(self._selected_game_type_text())
        if hasattr(self, "create_btn") and self.create_btn:
            self.create_btn.setEnabled(is_valid)
        
        return is_valid
    
    def create_project(self):
        """Create new project"""
        if not self.validate_form():
            return
        
        name = self.name_input.text().strip()
        description = self.description_input.toPlainText().strip()
        game_type = self._selected_game_type_text()
        
        # Convert game type to internal format
        gt_lower = game_type.lower()
        if ('bắt cá' in gt_lower) or ('bat ca' in gt_lower) or ('câu cá' in gt_lower) or ('cau ca' in gt_lower) or ('fishing' in gt_lower):
            game_type_internal = 'fishing'
        elif ('phiêu lưu' in gt_lower) or ('adventure' in gt_lower):
            game_type_internal = 'quiz_adventure'
        elif ('vượt chướng ngại vật' in gt_lower) or ('platformer' in gt_lower):
            game_type_internal = 'quiz_platformer'
        elif ('triệu phú' in gt_lower) or ('millionaire' in gt_lower) or ('ai là triệu phú' in gt_lower):
            game_type_internal = 'quiz_millionaire'

        else:
            game_type_internal = 'quiz_classic'
        
        project_data = {
            "name": name,
            "description": description,
            "game_type": game_type_internal,
            "created_at": None,  # Will be set by project manager
            "questions": [],
            "game_config": {
                "game_type": (
                    'Ai là triệu phú' if game_type_internal == 'quiz_millionaire'
                    else ('Fishing Game' if game_type_internal == 'fishing' else game_type_internal)
                ),
                "difficulty": "Medium",
                "question_time": 30
            }
        }
        if game_type_internal == 'fishing':
            project_data['force_variant'] = 'fishing'
            project_data['variant_marker'] = 'fishing'
            project_data['game_config']['variant_marker'] = 'fishing'
            try:
                if name and '🎣' not in name:
                    project_data['name'] = f"{name} 🎣"
            except Exception:
                pass
            project_data['game_config'].update(self._default_fishing_config())
        elif game_type_internal == 'quiz_millionaire':
            project_data['game_config'].update(self._default_millionaire_config())
        else:
            project_data['game_config'].update(self._default_quiz_config())
        
        self.project_created.emit(project_data)

    def _default_fishing_config(self) -> dict:
        base = 'assets/kenney_platformer-kit/PNG/Default'
        fishes = [
            {'sprite': f'{base}/fish_blue.png', 'wrong_sprite': f'{base}/fish_blue_skeleton.png', 'sound': ''},
            {'sprite': f'{base}/fish_green.png', 'wrong_sprite': f'{base}/fish_green_skeleton.png', 'sound': ''},
            {'sprite': f'{base}/fish_orange.png', 'wrong_sprite': f'{base}/fish_orange_skeleton.png', 'sound': ''},
            {'sprite': f'{base}/fish_pink.png', 'wrong_sprite': f'{base}/fish_pink_skeleton.png', 'sound': ''},
            {'sprite': f'{base}/fish_red.png', 'wrong_sprite': f'{base}/fish_red_skeleton.png', 'sound': ''},
        ]
        return {
            'fish_speed': 5,
            'fish_objects': fishes,
            # Use bundled fishing-friendly sounds
            'background_music': 'assets/kenney_platformer-kit/sound/water_loop.mp3',
            'correct_sound': 'assets/sound/correct.wav',
            'wrong_sound': 'assets/sound/wrong.wav',
            'click_sound': 'assets/kenney_platformer-kit/sound/click.mp3'
        }

    def _default_quiz_config(self) -> dict:
        return {
            'question_time': 30,
            'background_music': 'assets/sound/background.mp3',
            'correct_sound': 'assets/sound/correct.wav',
            'wrong_sound': 'assets/sound/wrong.wav',
            'click_sound': 'assets/sound/click.wav'
        }

    def _default_millionaire_config(self) -> dict:
        return {
            'question_time': 45,
            'lifelines_enabled': True,
            'enable_fifty': True,
            'enable_phone': True,
            'enable_audience': True,
            'safe_milestones': [4, 9, 14],
            # Map to existing bundled millionaire assets
            'background_music': 'assets/millionaire/sounds/Music/0_to_1000.mp3',
            'correct_sound': 'assets/millionaire/sounds/Effects/correct answer.mp3',
            'wrong_sound': 'assets/millionaire/sounds/Effects/wrong answer.mp3',
            # Use global click for consistent UX
            'click_sound': 'assets/sound/click.wav'
        }



    def set_language(self, lang: str):
        self._lang = lang or 'en'
        try:
            self.back_btn.setText(strip_icon_text(I18n.t('new.back', self._lang)))
            self.title_label.setText(I18n.t('new.title', self._lang))
            self.form_title.setText(I18n.t('new.form_title', self._lang))
            self.form_subtitle.setText(I18n.t('new.form_subtitle', self._lang))
            self.name_input.setPlaceholderText(I18n.t('new.name_placeholder', self._lang))
            self.description_input.setPlaceholderText(I18n.t('new.desc_placeholder', self._lang))
            self._populate_game_type_dropdown()
            # Update form labels is handled when building; optional
            self.cancel_btn.setText(I18n.t('new.cancel', self._lang))
            self.create_btn.setText(I18n.t('new.create', self._lang))
        except Exception:
            pass

    def _build_header_icon_button(self, kind: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setObjectName("header-icon-btn")
        btn.setAutoRaise(False)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(40, 40)
        try:
            btn.setIcon(build_standard_ui_icon(kind, self.style(), color_hex="#475467", size=18))
            btn.setIconSize(QSize(18, 18))
        except Exception:
            pass
        return btn

    def _game_type_items(self) -> list[tuple[str, str]]:
        quiz = I18n.t('new.type_quiz', self._lang)
        fish = I18n.t('new.type_fishing', self._lang)
        try:
            millionaire = I18n.t('new.type_millionaire', self._lang)
        except Exception:
            millionaire = 'Ai là triệu phú'
        return [
            (quiz, '#4F46E5'),
            (fish, '#10B981'),
            (millionaire, '#8B5CF6'),
        ]

    def _populate_game_type_dropdown(self):
        current_text = self._selected_game_type_text()
        self.game_type_dropdown.clear()
        target_row = 0
        for row, (text, color) in enumerate(self._game_type_items()):
            self.game_type_dropdown.addItem(text, color)
            if current_text and text == current_text:
                target_row = row
        if self.game_type_dropdown.count():
            self.game_type_dropdown.setCurrentIndex(target_row)

    def _selected_game_type_text(self) -> str:
        try:
            if hasattr(self, "game_type_dropdown") and self.game_type_dropdown:
                return self.game_type_dropdown.currentText().strip()
        except Exception:
            pass
        return ""

"""
Nguyen-Thanh-Tan ¬_¬
"""
