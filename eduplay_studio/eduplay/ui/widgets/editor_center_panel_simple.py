from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QSplitter, QPushButton, QFrame, QTextEdit, QLineEdit,
                                QComboBox, QCheckBox, QSpinBox, QSlider, QSizePolicy, QFileDialog,
                                QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import os
import sys

from eduplay.ui.widgets.custom_dropdown import FlatDropdown

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

class IndentTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.setAcceptRichText(False)
        except Exception:
            pass
    def keyPressEvent(self, e):
        try:
            from PySide6.QtCore import Qt
            if e.key() == Qt.Key_Tab and not (e.modifiers() & Qt.ShiftModifier):
                self.insertPlainText("    ")
                return
            if e.key() == Qt.Key_Backtab or (e.key() == Qt.Key_Tab and (e.modifiers() & Qt.ShiftModifier)):
                c = self.textCursor()
                c.movePosition(c.StartOfLine, c.MoveAnchor)
                c.movePosition(c.NextCharacter, c.KeepAnchor, 4)
                if c.selectedText() == "    ":
                    c.removeSelectedText()
                    return
        except Exception:
            pass
        super().keyPressEvent(e)


class EditorCenterPanel(QWidget):
    question_updated = Signal(dict)
    
    def __init__(self, parent=None, theme=None):
        super().__init__(parent)
        self.current_question = None
        self._is_loading_question = False
        try:
            from eduplay.core.settings_manager import SettingsManager
            self.language = SettingsManager().get_language()
            t = theme or (SettingsManager().get_theme() or 'dark')
        except Exception:
            self.language = 'en'
            t = theme or 'dark'
        self.theme = 'dark' if str(t).lower() == 'dark' else 'light'
        self.setup_ui()
        try:
            self.set_language(self.language)
        except Exception:
            pass

    def _t(self, key: str, fallback: str, **kwargs) -> str:
        try:
            from eduplay.core.i18n import I18n
            value = I18n.t(key, getattr(self, "language", "en") or "en", **kwargs)
            if isinstance(value, str) and value != key:
                return value
        except Exception:
            pass
        return fallback.format(**kwargs) if kwargs else fallback

    def _set_correct_preview(self, text: str) -> None:
        try:
            label = self._t("editor.center.correct_answer_preview", "Correct answer: {text}", text=text)
            self.correct_preview_label.setText(label if text else "")
        except Exception:
            self.correct_preview_label.setText("")
        
    def apply_theme(self, theme: str):
        """Apply theme to the panel"""
        self.theme = 'dark' if str(theme).lower() == 'dark' else 'light'
        t = self.theme
        
        # Header
        if t == 'dark':
            header_bg = "#25252B"
            header_border = "#3A3A40"
            title_color = "#E0E0E0"
        else:
            header_bg = "#F8FAFC"
            header_border = "#CBD5E1"
            title_color = "#1A1A1A"
            
        try:
            layout = self.layout()
            if layout and layout.count() > 0:
                header = layout.itemAt(0).widget()
                if header:
                    header.setStyleSheet(f"""
                        QWidget {{ background-color: {header_bg}; border-bottom: 1px solid {header_border}; padding: 10px; }}
                    """)
        except Exception:
            pass
            
        if hasattr(self, 'question_title'):
            self.question_title.setStyleSheet(f"""
                QLabel {{ color: {title_color}; font-size: 18px; font-weight: bold; }}
            """)

        # Content area background
        if hasattr(self, 'content_area'):
            try:
                content_widget = self.content_area.widget()
                if content_widget:
                    bg = '#1E1E24' if t == 'dark' else '#F9FAFF'
                    content_widget.setStyleSheet(f"QWidget {{ background-color: {bg}; }}")
            except Exception:
                pass

        # Group Frames
        if t == 'dark':
            group_style = """
                QFrame { color: #E0E0E0; border: 1px solid #3A3A40; border-radius: 6px; margin-top: 10px; padding: 10px; }
            """
            text_edit_style = """
                QTextEdit { background-color: #25252B; color: #E0E0E0; border: 1px solid #3A3A40; border-radius: 4px; padding: 10px; font-size: 14px; min-height: 80px; }
            """
            spin_style = """
                QSpinBox { background-color: #25252B; color: #E0E0E0; border: 1px solid #3A3A40; border-radius: 4px; padding: 6px 30px 6px 6px; min-width: 60px; }
                QSpinBox::up-button, QSpinBox::down-button { background-color: #1E1E24; border-left: 1px solid #3A3A40; width: 20px; subcontrol-origin: border; }
                QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 3px; }
                QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 3px; }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #2A2A30; }
                QSpinBox::up-arrow { image: none; width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 6px solid #E0E0E0; }
                QSpinBox::down-arrow { image: none; width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #E0E0E0; }
            """
        else:
            group_style = """
                QFrame { color: #1A1A1A; border: 1px solid #CBD5E1; border-radius: 6px; margin-top: 10px; padding: 10px; }
            """
            text_edit_style = """
                QTextEdit { background-color: #F8FAFC; color: #1A1A1A; border: 1px solid #CBD5E1; border-radius: 4px; padding: 10px; font-size: 14px; min-height: 80px; }
            """
            spin_style = """
                QSpinBox { background-color: #FFFFFF; color: #1A1A1A; border: 1px solid #CBD5E1; border-radius: 4px; padding: 6px 30px 6px 6px; min-width: 60px; }
                QSpinBox::up-button, QSpinBox::down-button { background-color: #EEF2FF; border-left: 1px solid #CBD5E1; width: 20px; subcontrol-origin: border; }
                QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 3px; }
                QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 3px; }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #E0EAFF; }
                QSpinBox::up-arrow { image: none; width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 6px solid #1A1A1A; }
                QSpinBox::down-arrow { image: none; width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #1A1A1A; }
            """

        for attr in ['question_group', 'settings_group', 'explanation_group', 'media_group', 'multiple_choice_ui', 'true_false_ui', 'fill_blank_ui', 'matching_ui', 'short_answer_ui', 'essay_ui']:
            if hasattr(self, attr) and getattr(self, attr):
                getattr(self, attr).setStyleSheet(group_style)
                
        for attr in ['question_text', 'explanation_text', 'options_text', 'fill_blank_answers']:
            if hasattr(self, attr) and getattr(self, attr):
                getattr(self, attr).setStyleSheet(text_edit_style)

        if hasattr(self, 'question_time_spin'):
            self.question_time_spin.setStyleSheet(spin_style)
        if hasattr(self, 'correct_answer'):
            self.correct_answer.setStyleSheet(spin_style)

        # Checkbox
        if hasattr(self, 'case_sensitive'):
            if t == 'dark':
                cb_color = "#E0E0E0"
                cb_bg = "#25252B"
                cb_border = "#3A3A40"
            else:
                cb_color = "#1A1A1A"
                cb_bg = "#FFFFFF"
                cb_border = "#CBD5E1"
            
            self.case_sensitive.setStyleSheet(f"""
                QCheckBox {{
                    color: {cb_color};
                    font-weight: bold;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    background-color: {cb_bg};
                    border: 1px solid {cb_border};
                    border-radius: 3px;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #7F56D9;
                }}
            """)

        # Empty placeholder
        if hasattr(self, 'empty_placeholder'):
            if t == 'dark':
                ph_border = "#3A3A40"
                ph_bg = "rgba(30,30,36,0.45)"
                ph_text = "#E0E0E0"
            else:
                ph_border = "#BBDEFB"
                ph_bg = "#E3F2FD"
                ph_text = "#000000"
            self.empty_placeholder.setStyleSheet(
                f"QFrame {{ border: 1px dashed {ph_border}; border-radius: 8px; padding: 24px; background: {ph_bg}; }} "
                f"QLabel {{ color: {ph_text}; font-weight: 800; font-size: 22px; }}"
            )

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Main content area
        self.content_area = self.create_content_area()
        layout.addWidget(self.content_area, 1)  # Add stretch factor 1 to take available space
        
        # Action buttons
        actions = self.create_action_buttons()
        layout.addWidget(actions, 0)  # Add stretch factor 0 to keep fixed size
        
        try:
            self._force_hide_question_type_if_millionaire()
        except Exception:
            pass
        
    def create_header(self):
        header = QWidget()
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            header.setStyleSheet("""
                QWidget { background-color: #25252B; border-bottom: 1px solid #3A3A40; padding: 10px; }
            """)
        else:
            header.setStyleSheet("""
                QWidget { background-color: #F8FAFC; border-bottom: 1px solid #CBD5E1; padding: 10px; }
            """)
        
        layout = QHBoxLayout(header)
        
        self.question_title = QLabel("")
        self.question_title.setStyleSheet("""
            QLabel { color: %s; font-size: 18px; font-weight: bold; }
        """ % ('#E0E0E0' if theme == 'dark' else '#1A1A1A'))
        layout.addWidget(self.question_title)
        
        layout.addStretch()
        
        # Question type selector
        self.question_type_combo = FlatDropdown()
        self.question_type_combo.currentIndexChanged.connect(self.on_question_type_changed)
        layout.addWidget(self.question_type_combo)
        
        return header
        
    def create_content_area(self):
        theme = getattr(self, 'theme', 'dark')
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content = QWidget()
        content.setStyleSheet("""
            QWidget { background-color: %s; }
        """ % ('#1E1E24' if theme == 'dark' else '#F9FAFF'))
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Question text - always visible
        question_group = QFrame()
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            question_group.setStyleSheet("""
                QFrame { color: #E0E0E0; border: 1px solid #3A3A40; border-radius: 6px; margin-top: 10px; padding: 10px; }
            """)
        else:
            question_group.setStyleSheet("""
                QFrame { color: #1A1A1A; border: 1px solid #CBD5E1; border-radius: 6px; margin-top: 10px; padding: 10px; }
            """)
        question_layout = QVBoxLayout(question_group)
        
        self.question_label = QLabel("")
        self.question_label.setStyleSheet("font-weight: bold;")
        question_layout.addWidget(self.question_label)
        
        class IndentTextEdit(QTextEdit):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                try:
                    self.setAcceptRichText(False)
                except Exception:
                    pass
            def keyPressEvent(self, e):
                try:
                    from PySide6.QtCore import Qt
                    if e.key() == Qt.Key_Tab and not (e.modifiers() & Qt.ShiftModifier):
                        self.insertPlainText("    ")
                        return
                    if e.key() == Qt.Key_Backtab or (e.key() == Qt.Key_Tab and (e.modifiers() & Qt.ShiftModifier)):
                        c = self.textCursor()
                        c.movePosition(c.StartOfLine, c.MoveAnchor)
                        c.movePosition(c.NextCharacter, c.KeepAnchor, 4)
                        if c.selectedText() == "    ":
                            c.removeSelectedText()
                            return
                except Exception:
                    pass
                super().keyPressEvent(e)
        self.question_text = IndentTextEdit()
        self.question_text.setStyleSheet("""
            QTextEdit { background-color: %s; color: %s; border: 1px solid %s; border-radius: 4px; padding: 10px; font-size: 14px; min-height: 80px; }
        """ % ('#25252B' if theme == 'dark' else '#F8FAFC', '#E0E0E0' if theme == 'dark' else '#1A1A1A', '#3A3A40' if theme == 'dark' else '#CBD5E1'))
        # Connect text change for hot reload
        self.question_text.textChanged.connect(self.on_text_changed)
        try:
            self.question_text.setTabChangesFocus(False)
            self.explanation_text.setTabChangesFocus(False)
        except Exception:
            pass
        try:
            self.question_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        question_layout.addWidget(self.question_text)
        layout.addWidget(question_group)
        self.question_group = question_group

        settings_group = QFrame()
        settings_group.setStyleSheet(question_group.styleSheet())
        settings_layout = QHBoxLayout(settings_group)
        self.time_limit_label = QLabel("")
        self.time_limit_label.setStyleSheet("font-weight: bold;")
        try:
            self.time_limit_label.setToolTip('Thời gian tối đa cho mỗi câu hỏi')
        except Exception:
            pass
        settings_layout.addWidget(self.time_limit_label)
        self.question_time_slider = QSlider(Qt.Horizontal)
        self.question_time_slider.setRange(5, 180)
        self.question_time_slider.setSingleStep(5)
        try:
            from eduplay.core.settings_manager import SettingsManager
            _default_time = int(SettingsManager().get('game_defaults.quiz_time_per_question', 30))
        except Exception:
            _default_time = 30
        self.question_time_slider.setValue(_default_time)
        self.question_time_slider.setStyleSheet("QSlider{min-width:200px;}")
        settings_layout.addWidget(self.question_time_slider)
        self.question_time_spin = QSpinBox()
        self.question_time_spin.setRange(5, 180)
        self.question_time_spin.setValue(_default_time)
        if theme == 'dark':
            self.question_time_spin.setStyleSheet(
                """
                QSpinBox { background-color: #25252B; color: #E0E0E0; border: 1px solid #3A3A40; border-radius: 4px; padding: 6px; min-width: 60px; }
                QSpinBox::up-button, QSpinBox::down-button { background-color: #1E1E24; border-left: 1px solid #3A3A40; width: 20px; subcontrol-origin: border; }
                QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 3px; }
                QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 3px; }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #2A2A30; }
                """
            )
        else:
            self.question_time_spin.setStyleSheet(
                """
                QSpinBox { background-color: #FFFFFF; color: #1A1A1A; border: 1px solid #CBD5E1; border-radius: 4px; padding: 6px; min-width: 60px; }
                QSpinBox::up-button, QSpinBox::down-button { background-color: #EEF2FF; border-left: 1px solid #CBD5E1; width: 20px; subcontrol-origin: border; }
                QSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 3px; }
                QSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 3px; }
                QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #E0EAFF; }
                """
            )
        settings_layout.addWidget(self.question_time_spin)
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        self.settings_group = settings_group
        self.question_time_slider.valueChanged.connect(self.question_time_spin.setValue)
        self.question_time_slider.valueChanged.connect(self.on_text_changed)
        self.question_time_spin.valueChanged.connect(self.question_time_slider.setValue)
        self.question_time_spin.valueChanged.connect(self.on_text_changed)
        
        # Dynamic content area for different question types
        self.dynamic_content = QWidget()
        self.dynamic_layout = QVBoxLayout(self.dynamic_content)
        self.dynamic_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.dynamic_content)

        self.empty_placeholder = QFrame()
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            ph_border = "#3A3A40"
            ph_bg = "rgba(30,30,36,0.45)"
            ph_text = "#E0E0E0"
        else:
            ph_border = "#BBDEFB"
            ph_bg = "#E3F2FD"
            ph_text = "#000000"
        self.empty_placeholder.setStyleSheet(
            f"QFrame {{ border: 1px dashed {ph_border}; border-radius: 8px; padding: 24px; background: {ph_bg}; }} "
            f"QLabel {{ color: {ph_text}; font-weight: 800; font-size: 22px; }}"
        )
        ph_lay = QVBoxLayout(self.empty_placeholder)
        self.welcome_label = QLabel(self._t("editor.center.welcome", "Welcome to the editor"))
        self.welcome_label.setAlignment(Qt.AlignCenter)
        ph_lay.addWidget(self.welcome_label)
        self.dynamic_layout.addWidget(self.empty_placeholder)
        
        # Build all type UIs but keep hidden by default until a question is selected
        self.create_multiple_choice_ui(); self.multiple_choice_ui.hide()
        self.create_true_false_ui(); self.true_false_ui.hide()
        self.create_fill_blank_ui(); self.fill_blank_ui.hide()
        self.create_matching_ui(); self.matching_ui.hide()
        self.create_short_answer_ui(); self.short_answer_ui.hide()
        self.create_essay_ui(); self.essay_ui.hide()

        # Explanation - always visible
        explanation_group = QFrame()
        explanation_group.setStyleSheet(question_group.styleSheet())
        explanation_layout = QVBoxLayout(explanation_group)
        
        self.explanation_label = QLabel("")
        self.explanation_label.setStyleSheet("font-weight: bold;")
        explanation_layout.addWidget(self.explanation_label)
        
        self.explanation_text = IndentTextEdit()
        self.explanation_text.setStyleSheet(self.question_text.styleSheet())
        self.explanation_text.setMaximumHeight(100)
        explanation_layout.addWidget(self.explanation_text)
        layout.addWidget(explanation_group)
        self.explanation_group = explanation_group
        media_group = QFrame()
        media_group.setStyleSheet(question_group.styleSheet())
        media_layout = QVBoxLayout(media_group)
        self.media_label = QLabel(self._t("editor.center.media_files", "Media Files"))
        self.media_label.setStyleSheet("font-weight: bold;")
        media_layout.addWidget(self.media_label)
        row_img = QHBoxLayout()
        self.image_path = QLineEdit()
        self.image_path.setPlaceholderText(self._t("editor.center.image_path_placeholder", "Image path..."))
        row_img.addWidget(self.image_path)
        self.browse_image_btn = QPushButton(self._t("editor.center.choose_image", "Choose Image"))
        self.browse_image_btn.clicked.connect(self.browse_image_file)
        row_img.addWidget(self.browse_image_btn)
        media_layout.addLayout(row_img)
        row_audio = QHBoxLayout()
        self.audio_path = QLineEdit()
        self.audio_path.setPlaceholderText(self._t("editor.center.audio_path_placeholder", "Audio path..."))
        row_audio.addWidget(self.audio_path)
        self.browse_audio_btn = QPushButton(self._t("editor.center.choose_audio", "Choose Audio"))
        self.browse_audio_btn.clicked.connect(self.browse_audio_file)
        row_audio.addWidget(self.browse_audio_btn)
        media_layout.addLayout(row_audio)
        layout.addWidget(media_group)
        self.media_group = media_group
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _force_hide_question_type_if_millionaire(self):
        try:
            proj = getattr(self, "current_project", {}) or {}
            gt = str(proj.get("game_type", "") or "").lower()
            cfg = proj.get("game_config", {}) or {}
            if not gt:
                gt = str(cfg.get("game_type", "") or "").lower()
            is_m = ("triệu phú" in gt) or ("trieu phu" in gt) or ("millionaire" in gt) or ("quiz_millionaire" in gt) or ("altp" in gt)
            if is_m and hasattr(self, "question_type_combo") and self.question_type_combo:
                try:
                    self.question_type_combo.hide()
                    self.question_type_combo.setEnabled(False)
                except Exception:
                    pass
        except Exception:
            pass
        
    def create_multiple_choice_ui(self):
        """Create UI for multiple choice questions"""
        group = QFrame()
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            group.setStyleSheet("""
                QFrame { color: #E0E0E0; border: 1px solid #3A3A40; border-radius: 6px; margin-top: 10px; padding: 10px; }
            """)
        else:
            group.setStyleSheet("""
                QFrame { color: #1A1A1A; border: 1px solid #CBD5E1; border-radius: 6px; margin-top: 10px; padding: 10px; }
            """)
        layout = QVBoxLayout(group)
        
        self.options_label = QLabel("")
        self.options_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.options_label)
        
        self.options_text = IndentTextEdit()
        self.options_text.setStyleSheet("""
            QTextEdit { background-color: %s; color: %s; border: 1px solid %s; border-radius: 4px; padding: 10px; font-size: 14px; min-height: 100px; }
        """ % ('#25252B' if theme == 'dark' else '#F8FAFC', '#E0E0E0' if theme == 'dark' else '#1A1A1A', '#3A3A40' if theme == 'dark' else '#CBD5E1'))
        try:
            self.options_text.setTabChangesFocus(False)
        except Exception:
            pass
        try:
            self.options_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        layout.addWidget(self.options_text)
        
        correct_layout = QHBoxLayout()
        self.correct_index_label = QLabel("")
        self.correct_index_label.setStyleSheet("font-weight: bold;")
        correct_layout.addWidget(self.correct_index_label)
        
        self.correct_answer = QSpinBox()
        self.correct_answer.setRange(0, 9)
        self.correct_answer.setStyleSheet("""
            QSpinBox { background-color: %s; color: %s; border: 1px solid %s; border-radius: 4px; padding: 6px; min-width: 60px; }
        """ % ('#25252B' if theme == 'dark' else '#FFFFFF', '#E0E0E0' if theme == 'dark' else '#1A1A1A', '#3A3A40' if theme == 'dark' else '#CBD5E1'))
        # Connect value change for hot reload
        self.correct_answer.valueChanged.connect(self.on_text_changed)
        correct_layout.addWidget(self.correct_answer)
        correct_layout.addStretch()
        
        layout.addLayout(correct_layout)
        
        self.correct_preview_label = QLabel("")
        self.correct_preview_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.correct_preview_label)
        
        self.multiple_choice_ui = group
        self.dynamic_layout.addWidget(group)
        
    def create_true_false_ui(self):
        """Create UI for true/false questions"""
        group = QFrame()
        group.setStyleSheet(self.multiple_choice_ui.styleSheet())
        layout = QVBoxLayout(group)
        
        self.correct_label = QLabel("")
        self.correct_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.correct_label)
        
        self.true_false_correct = FlatDropdown()
        # Connect current index change for hot reload
        self.true_false_correct.currentIndexChanged.connect(self.on_text_changed)
        layout.addWidget(self.true_false_correct)
        layout.addStretch()
        
        self.true_false_ui = group
        self.dynamic_layout.addWidget(group)
        
    def create_fill_blank_ui(self):
        """Create UI for fill in the blank questions"""
        group = QFrame()
        group.setStyleSheet(self.multiple_choice_ui.styleSheet())
        layout = QVBoxLayout(group)
        
        self.answers_label = QLabel("")
        self.answers_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.answers_label)
        
        self.fill_blank_answers = QTextEdit()
        self.fill_blank_answers.setStyleSheet(self.options_text.styleSheet())
        try:
            self.fill_blank_answers.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        self.fill_blank_answers.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.fill_blank_answers)
        
        self.case_sensitive = QCheckBox("")
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            checkbox_color = "#E0E0E0"
            indicator_bg = "#25252B"
            indicator_border = "#3A3A40"
        else:
            checkbox_color = "#1A1A1A"
            indicator_bg = "#FFFFFF"
            indicator_border = "#CBD5E1"
        self.case_sensitive.setStyleSheet(
            f"""
            QCheckBox {{
                color: {checkbox_color};
                font-weight: bold;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                background-color: {indicator_bg};
                border: 1px solid {indicator_border};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: #7F56D9;
            }}
        """
        )
        self.case_sensitive.stateChanged.connect(self.on_text_changed)
        layout.addWidget(self.case_sensitive)
        layout.addStretch()
        
        self.fill_blank_ui = group
        self.dynamic_layout.addWidget(group)
        
    def create_matching_ui(self):
        """Create UI for matching questions"""
        group = QFrame()
        group.setStyleSheet(self.multiple_choice_ui.styleSheet())
        layout = QVBoxLayout(group)
        
        self.pairs_label = QLabel("")
        self.pairs_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.pairs_label)
        
        self.matching_pairs = QTextEdit()
        self.matching_pairs.setStyleSheet(self.options_text.styleSheet())
        try:
            self.matching_pairs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        self.matching_pairs.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.matching_pairs)
        layout.addStretch()
        
        self.matching_ui = group
        self.dynamic_layout.addWidget(group)
        
    def create_short_answer_ui(self):
        """Create UI for short answer questions"""
        group = QFrame()
        group.setStyleSheet(self.multiple_choice_ui.styleSheet())
        layout = QVBoxLayout(group)
        
        self.expected_label = QLabel("")
        self.expected_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.expected_label)
        
        self.short_answer_expected = QLineEdit()
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            sa_bg = "#25252B"
            sa_fg = "#E0E0E0"
            sa_border = "#3A3A40"
        else:
            sa_bg = "#FFFFFF"
            sa_fg = "#1A1A1A"
            sa_border = "#CBD5E1"
        self.short_answer_expected.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {sa_bg};
                color: {sa_fg};
                border: 1px solid {sa_border};
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }}
        """
        )
        self.short_answer_expected.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.short_answer_expected)
        
        self.keywords_label = QLabel("")
        self.keywords_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.keywords_label)
        
        self.short_answer_keywords = QLineEdit()
        self.short_answer_keywords.setStyleSheet(self.short_answer_expected.styleSheet())
        self.short_answer_keywords.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.short_answer_keywords)
        layout.addStretch()
        
        self.short_answer_ui = group
        self.dynamic_layout.addWidget(group)
        
    def create_essay_ui(self):
        """Create UI for essay questions"""
        group = QFrame()
        group.setStyleSheet(self.multiple_choice_ui.styleSheet())
        layout = QVBoxLayout(group)
        
        self.max_points_label = QLabel("")
        self.max_points_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.max_points_label)
        
        self.essay_max_points = QSpinBox()
        self.essay_max_points.setRange(1, 100)
        self.essay_max_points.setValue(10)
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            es_bg = "#25252B"
            es_fg = "#E0E0E0"
            es_border = "#3A3A40"
        else:
            es_bg = "#FFFFFF"
            es_fg = "#1A1A1A"
            es_border = "#CBD5E1"
        self.essay_max_points.setStyleSheet(
            f"""
            QSpinBox {{
                background-color: {es_bg};
                color: {es_fg};
                border: 1px solid {es_border};
                border-radius: 4px;
                padding: 6px;
                min-width: 80px;
            }}
        """
        )
        self.essay_max_points.valueChanged.connect(self.on_text_changed)
        layout.addWidget(self.essay_max_points)
        
        self.rubric_label = QLabel("")
        self.rubric_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.rubric_label)
        
        self.essay_rubric = QTextEdit()
        self.essay_rubric.setStyleSheet(self.options_text.styleSheet())
        try:
            self.essay_rubric.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except Exception:
            pass
        self.essay_rubric.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.essay_rubric)
        layout.addStretch()
        
        self.essay_ui = group
        self.dynamic_layout.addWidget(group)
        
    def create_action_buttons(self):
        buttons = QWidget()
        theme = getattr(self, 'theme', 'dark')
        buttons.setStyleSheet("""
            QWidget { background-color: %s; border-top: 1px solid %s; padding: 10px; }
        """ % ('#25252B' if theme == 'dark' else '#F8FAFC', '#3A3A40' if theme == 'dark' else '#CBD5E1'))
        
        layout = QHBoxLayout(buttons)
        
        # Delete button
        self.delete_btn = QPushButton("")
        self.delete_btn.setStyleSheet("""
            QPushButton { background-color: %s; color: #FFFFFF; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: %s; }
        """ % ('#F44336' if theme == 'dark' else '#EF4444', '#D32F2F' if theme == 'dark' else '#DC2626'))
        self.delete_btn.clicked.connect(self.delete_current_question)
        layout.addWidget(self.delete_btn)
        
        layout.addStretch()
        
        # Duplicate button
        self.duplicate_btn = QPushButton("")
        self.duplicate_btn.setStyleSheet("""
            QPushButton { background-color: %s; color: #FFFFFF; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: %s; }
        """ % ('#F79009' if theme == 'dark' else '#F59E0B', '#E68008' if theme == 'dark' else '#D97706'))
        self.duplicate_btn.clicked.connect(self.duplicate_current_question)
        layout.addWidget(self.duplicate_btn)
        
        # Save button
        self.save_btn = QPushButton("")
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: %s; color: #FFFFFF; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: %s; }
        """ % ('#7F56D9' if theme == 'dark' else '#10B981', '#6A48C0' if theme == 'dark' else '#059669'))
        self.save_btn.clicked.connect(self.save_current_question)
        layout.addWidget(self.save_btn)
        
        return buttons

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            base_h = max(28, min(48, int(self.height() * 0.045)))
            for btn in [getattr(self, 'delete_btn', None), getattr(self, 'duplicate_btn', None), getattr(self, 'save_btn', None)]:
                if btn:
                    btn.setFixedHeight(base_h)
                    fs = max(11, min(16, int(base_h * 0.4)))
                    f = btn.font()
                    f.setPointSize(fs)
                    btn.setFont(f)
        except Exception:
            pass
        try:
            h = max(self.height(), 400)
            qh = max(120, int(h * 0.26))
            eh = max(100, int(h * 0.22))
            oh = max(110, int(h * 0.22))
            mh = max(110, int(h * 0.22))
            rh = max(100, int(h * 0.18))
            if hasattr(self, 'question_text'):
                self.question_text.setMinimumHeight(qh)
            if hasattr(self, 'explanation_text'):
                self.explanation_text.setMinimumHeight(eh)
            if hasattr(self, 'options_text'):
                self.options_text.setMinimumHeight(oh)
            if hasattr(self, 'fill_blank_answers'):
                self.fill_blank_answers.setMinimumHeight(oh)
            if hasattr(self, 'matching_pairs'):
                self.matching_pairs.setMinimumHeight(mh)
            if hasattr(self, 'essay_rubric'):
                self.essay_rubric.setMinimumHeight(rh)
        except Exception:
            pass
        
    def set_question(self, question_data, index=-1):
        """Load a question for editing"""
        self._is_loading_question = True
        self.current_question = question_data
        self.current_index = index
        
        # Hide all UI groups first
        self.hide_all_ui_groups()
        
        try:
            if question_data:
                try:
                    from eduplay.core.i18n import I18n
                    lang = getattr(self, 'language', 'en')
                    prefix = I18n.t('editor.question_prefix', lang)
                    self.question_title.setText(f"{prefix} {index + 1}" if index >= 0 else prefix)
                except Exception:
                    self.question_title.setText(f"Question {index + 1}" if index >= 0 else "Question")
                self.question_text.setPlainText(question_data.get('question', ''))
                self.explanation_text.setPlainText(question_data.get('explanation', ''))
                try:
                    self.image_path.setText(question_data.get('image','') or '')
                    self.audio_path.setText(question_data.get('audio','') or '')
                except Exception:
                    pass
                
                q_type = (question_data.get('type') or 'multiple_choice')
                self.show_question_type_ui(q_type, question_data)
                try:
                    self.question_type_combo.setEnabled(True)
                    self.question_type_combo.setCurrentData(q_type)
                except Exception:
                    pass
                try:
                    from eduplay.core.settings_manager import SettingsManager
                    default_time = int(SettingsManager().get('game_defaults.quiz_time_per_question', 30))
                except Exception:
                    default_time = 30
                try:
                    tl = int(question_data.get('time_limit', default_time))
                except Exception:
                    tl = default_time
                self.question_time_slider.setValue(tl)
                self.question_time_spin.setValue(tl)
                try:
                    self.empty_placeholder.hide()
                except Exception:
                    pass
                try:
                    self.question_group.show(); self.settings_group.show(); self.explanation_group.show(); self.media_group.show();
                    self.question_type_combo.show()
                    for btn in [getattr(self, 'delete_btn', None), getattr(self, 'duplicate_btn', None), getattr(self, 'save_btn', None)]:
                        if btn: btn.show()
                except Exception:
                    pass
                
            else:
                try:
                    from eduplay.core.i18n import I18n
                    lang = getattr(self, 'language', 'en')
                    self.question_title.setText(I18n.t('editor.center.no_question', lang))
                    self.welcome_label.setText(I18n.t('editor.center.welcome', lang))
                except Exception:
                    self.question_title.setText("No Question Selected")
                self.question_text.clear()
                self.explanation_text.clear()
                try:
                    self.image_path.clear()
                    self.audio_path.clear()
                except Exception:
                    pass
                self.question_type_combo.setCurrentIndex(0)  # Default to Multiple Choice
                try:
                    from eduplay.core.settings_manager import SettingsManager
                    default_time = int(SettingsManager().get('game_defaults.quiz_time_per_question', 30))
                except Exception:
                    default_time = 30
                self.question_time_slider.setValue(default_time)
                self.question_time_spin.setValue(default_time)
                try:
                    self.hide_all_ui_groups()
                    self.empty_placeholder.show()
                    self.question_group.hide(); self.settings_group.hide(); self.explanation_group.hide(); self.media_group.hide();
                    self.question_type_combo.hide()
                    for btn in [getattr(self, 'delete_btn', None), getattr(self, 'duplicate_btn', None), getattr(self, 'save_btn', None)]:
                        if btn: btn.hide()
                except Exception:
                    pass
        finally:
            self._is_loading_question = False
            
    def hide_all_ui_groups(self):
        """Hide all question type UI groups"""
        self.multiple_choice_ui.hide()
        self.true_false_ui.hide()
        self.fill_blank_ui.hide()
        self.matching_ui.hide()
        self.short_answer_ui.hide()
        self.essay_ui.hide()
        
    def show_question_type_ui(self, q_type, question_data):
        """Show the appropriate UI for the question type and load data"""
        if q_type == 'multiple_choice':
            self.multiple_choice_ui.show()
            options = question_data.get('options', [])
            try:
                mx = max(0, (len(options) if options else 0) - 1)
                self.correct_answer.setRange(0, mx)
            except Exception:
                pass
            # Extract text from options dictionary
            options_text = [opt.get('text', '') if isinstance(opt, dict) else str(opt) for opt in options]
            self.options_text.setPlainText('\n'.join(options_text))
            correct = question_data.get('correct_answer', 0)
            try:
                if isinstance(correct, str):
                    try:
                        letters = [chr(65 + i) for i in range(max(2, len(options or [])))]
                    except Exception:
                        letters = ['A', 'B', 'C', 'D']
                    uc = correct.strip().upper()
                    if uc in letters:
                        idx = letters.index(uc)
                    else:
                        try:
                            idx = (options or []).index(correct)
                        except Exception:
                            idx = 0
                else:
                    try:
                        idx = int(correct)
                    except Exception:
                        idx = 0
                try:
                    mx = self.correct_answer.maximum()
                    if isinstance(mx, int) and idx > mx:
                        idx = mx
                    if idx < 0:
                        idx = 0
                except Exception:
                    pass
                self.correct_answer.setValue(idx)
            except Exception:
                self.correct_answer.setValue(0)
            try:
                ci = self.correct_answer.value()
                txt = (options[ci] if options and ci < len(options) else "")
                self._set_correct_preview(txt)
            except Exception:
                self.correct_preview_label.setText("")
            
        elif q_type == 'true_false':
            self.true_false_ui.show()
            correct = question_data.get('correct_answer', True)
            self.true_false_correct.setCurrentData(bool(correct))
            
        elif q_type == 'fill_blank':
            self.fill_blank_ui.show()
            answers = question_data.get('correct_answers', [])
            self.fill_blank_answers.setPlainText('\n'.join(answers))
            case_sensitive = question_data.get('case_sensitive', False)
            self.case_sensitive.setChecked(case_sensitive)
            
        elif q_type == 'matching':
            self.matching_ui.show()
            pairs = question_data.get('pairs', [])
            pairs_text = []
            for pair in pairs:
                pairs_text.append(f"{pair.get('left', '')}={pair.get('right', '')}")
            self.matching_pairs.setPlainText('\n'.join(pairs_text))
            
        elif q_type == 'short_answer':
            self.short_answer_ui.show()
            expected = question_data.get('expected_answer', '')
            self.short_answer_expected.setText(expected)
            keywords = question_data.get('keywords', [])
            self.short_answer_keywords.setText(', '.join(keywords))
            
        elif q_type == 'essay':
            self.essay_ui.show()
            max_points = question_data.get('max_points', 10)
            self.essay_max_points.setValue(max_points)
            rubric = question_data.get('rubric', '')
            self.essay_rubric.setPlainText(rubric)
        
    def on_question_type_changed(self, index):
        # Use user data from FlatDropdown
        internal_type = self.question_type_combo.currentData() or 'multiple_choice'
        
        self.hide_all_ui_groups()
        if self.current_question:
            self.current_question['type'] = internal_type
            self.show_question_type_ui(internal_type, self.current_question)
            self.on_text_changed()
        else:
            self.show_question_type_ui(internal_type, {})
        
    def on_text_changed(self):
        """Live-update current question and trigger hot preview without pressing Save"""
        if getattr(self, "_is_loading_question", False):
            return
        if not self.current_question:
            return
        # Update basic fields
        self.current_question['question'] = self.question_text.toPlainText()
        self.current_question['explanation'] = self.explanation_text.toPlainText()
        try:
            self.current_question['image'] = self.image_path.text().strip()
            self.current_question['audio'] = self.audio_path.text().strip()
        except Exception:
            pass
        # Update type-specific fields
        q_type = self.current_question.get('type', 'multiple_choice')
        if q_type == 'multiple_choice':
            options_text = self.options_text.toPlainText().strip()
            options_lines = [line.strip() for line in options_text.split('\n') if line.strip()] if options_text else []
            # Convert to dictionary format for consistency
            options = [{"text": line, "correct": False} for line in options_lines]
            if options:
                self.current_question['options'] = options
            try:
                mx = max(0, len(options) - 1) if options else 0
                self.correct_answer.blockSignals(True)
                self.correct_answer.setRange(0, mx)
                v = self.correct_answer.value()
                if v > mx:
                    self.correct_answer.setValue(mx)
                self.correct_answer.blockSignals(False)
            except Exception:
                try:
                    self.correct_answer.blockSignals(False)
                except Exception:
                    pass
            self.current_question['correct_answer'] = self.correct_answer.value()
            try:
                ci = self.correct_answer.value()
                txt = (options[ci] if options and ci < len(options) else "")
                self._set_correct_preview(txt)
            except Exception:
                self.correct_preview_label.setText("")
        elif q_type == 'true_false':
            try:
                self.current_question['correct_answer'] = bool(self.true_false_correct.currentData())
            except Exception:
                self.current_question['correct_answer'] = True
        elif q_type == 'fill_blank':
            answers_text = self.fill_blank_answers.toPlainText().strip()
            answers = [line.strip() for line in answers_text.split('\n') if line.strip()] if answers_text else []
            self.current_question['correct_answers'] = answers
            self.current_question['case_sensitive'] = self.case_sensitive.isChecked()
        elif q_type == 'matching':
            pairs_text = self.matching_pairs.toPlainText().strip()
            pairs = []
            if pairs_text:
                for line in pairs_text.split('\n'):
                    if '=' in line:
                        left, right = line.split('=', 1)
                        pairs.append({'left': left.strip(), 'right': right.strip()})
            self.current_question['pairs'] = pairs
        elif q_type == 'short_answer':
            self.current_question['expected_answer'] = self.short_answer_expected.text().strip()
            keywords_text = self.short_answer_keywords.text().strip()
            self.current_question['keywords'] = [kw.strip() for kw in keywords_text.split(',') if kw.strip()] if keywords_text else []
        elif q_type == 'essay':
            self.current_question['max_points'] = self.essay_max_points.value()
            self.current_question['rubric'] = self.essay_rubric.toPlainText().strip()
        # Emit update for right panel hot reload
        self.current_question['time_limit'] = int(self.question_time_slider.value())
        self.question_updated.emit({'action': 'save', 'question': self.current_question})
            
    def delete_current_question(self):
        """Delete the current question"""
        if self.current_question:
            payload = {
                'action': 'delete',
                'question': self.current_question,
                'index': getattr(self, 'current_index', -1)
            }
            try:
                qid = self.current_question.get('id')
            except Exception:
                qid = None
            if qid:
                payload['question_id'] = qid
            self.question_updated.emit(payload)
            
    def duplicate_current_question(self):
        """Duplicate the current question"""
        if self.current_question:
            self.question_updated.emit({'action': 'duplicate', 'question': self.current_question})
            
    def save_current_question(self):
        """Save the current question"""
        if self.current_question:
            # Update basic fields
            self.current_question['question'] = self.question_text.toPlainText()
            self.current_question['explanation'] = self.explanation_text.toPlainText()
            try:
                self.current_question['image'] = self.image_path.text().strip()
                self.current_question['audio'] = self.audio_path.text().strip()
            except Exception:
                pass
            
            # Save data based on question type
            q_type = self.current_question.get('type', 'multiple_choice')
            
            if q_type == 'multiple_choice':
                # Parse options
                options_text = self.options_text.toPlainText().strip()
                if options_text:
                    options_lines = [line.strip() for line in options_text.split('\n') if line.strip()]
                    # Convert to dictionary format for consistency
                    options = [{"text": line, "correct": False} for line in options_lines]
                    self.current_question['options'] = options
                
                # Parse correct answer
                correct = self.correct_answer.value()
                self.current_question['correct_answer'] = correct
                
            elif q_type == 'true_false':
                try:
                    from eduplay.core.i18n import I18n
                    l = getattr(self, 'language', 'en')
                    correct = self.true_false_correct.currentText() == I18n.t('editor.center.true', l)
                except Exception:
                    correct = self.true_false_correct.currentText() == "True"
                self.current_question['correct_answer'] = correct
                
            elif q_type == 'fill_blank':
                # Parse acceptable answers
                answers_text = self.fill_blank_answers.toPlainText().strip()
                if answers_text:
                    answers = [line.strip() for line in answers_text.split('\n') if line.strip()]
                    self.current_question['correct_answers'] = answers
                
                self.current_question['case_sensitive'] = self.case_sensitive.isChecked()
                
            elif q_type == 'matching':
                # Parse matching pairs
                pairs_text = self.matching_pairs.toPlainText().strip()
                pairs = []
                if pairs_text:
                    for line in pairs_text.split('\n'):
                        if '=' in line:
                            left, right = line.split('=', 1)
                            pairs.append({
                                'left': left.strip(),
                                'right': right.strip()
                            })
                self.current_question['pairs'] = pairs
                
            elif q_type == 'short_answer':
                self.current_question['expected_answer'] = self.short_answer_expected.text().strip()
                keywords_text = self.short_answer_keywords.text().strip()
                if keywords_text:
                    keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
                    self.current_question['keywords'] = keywords
                else:
                    self.current_question['keywords'] = []
                    
            elif q_type == 'essay':
                self.current_question['max_points'] = self.essay_max_points.value()
                self.current_question['rubric'] = self.essay_rubric.toPlainText().strip()
            
            self.question_updated.emit({'action': 'save', 'question': self.current_question})

    def browse_image_file(self):
        try:
            fp, _ = QFileDialog.getOpenFileName(
                self,
                self._t("editor.center.image_dialog_title", "Select Image"),
                "",
                self._t("editor.center.image_file_filter", "Images (*.png *.jpg *.jpeg *.gif)")
            )
            if fp:
                self.image_path.setText(fp)
                self.on_text_changed()
        except Exception:
            pass

    def browse_audio_file(self):
        try:
            fp, _ = QFileDialog.getOpenFileName(
                self,
                self._t("editor.center.audio_dialog_title", "Select Audio"),
                "",
                self._t("editor.center.audio_file_filter", "Audio Files (*.wav *.mp3 *.ogg)")
            )
            if fp:
                self.audio_path.setText(fp)
                self.on_text_changed()
        except Exception:
            pass

    def set_language(self, lang: str):
        self.language = lang or 'en'
        try:
            from eduplay.core.i18n import I18n
            l = self.language
            self.question_label.setText(I18n.t('editor.center.question_text', l))
            self.question_text.setPlaceholderText(I18n.t('editor.center.question_placeholder', l))
            self.explanation_label.setText(I18n.t('editor.center.explanation', l))
            self.explanation_text.setPlaceholderText(I18n.t('editor.center.explanation_placeholder', l))
            try:
                self.time_limit_label.setText(I18n.t('editor.center.time_limit', l))
            except Exception:
                self.time_limit_label.setText('Thời gian câu hỏi (giây)' if l == 'vi' else 'Question time (seconds)')
            self.options_label.setText(I18n.t('editor.center.answer_options', l))
            self.options_text.setPlaceholderText(I18n.t('editor.center.options_placeholder', l))
            self.correct_index_label.setText(I18n.t('editor.center.correct_index', l))
            self.correct_label.setText(I18n.t('editor.center.correct_label', l))
            self.true_false_correct.clear()
            self.true_false_correct.addItem(I18n.t('editor.center.true', l), True)
            self.true_false_correct.addItem(I18n.t('editor.center.false', l), False)
            self.answers_label.setText(I18n.t('editor.center.acceptable_answers', l))
            self.fill_blank_answers.setPlaceholderText(I18n.t('editor.center.acceptable_placeholder', l))
            self.case_sensitive.setText(I18n.t('editor.center.case_sensitive', l))
            self.pairs_label.setText(I18n.t('editor.center.matching_pairs', l))
            self.matching_pairs.setPlaceholderText(I18n.t('editor.center.matching_placeholder', l))
            self.expected_label.setText(I18n.t('editor.center.expected', l))
            self.short_answer_expected.setPlaceholderText(I18n.t('editor.center.expected_placeholder', l))
            self.keywords_label.setText(I18n.t('editor.center.keywords_label', l))
            self.short_answer_keywords.setPlaceholderText(I18n.t('editor.center.keywords_placeholder', l))
            self.max_points_label.setText(I18n.t('editor.center.max_points', l))
            self.rubric_label.setText(I18n.t('editor.center.rubric_label', l))
            self.essay_rubric.setPlaceholderText(I18n.t('editor.center.rubric_placeholder', l))
            self.delete_btn.setText(I18n.t('editor.center.delete', l))
            self.duplicate_btn.setText(I18n.t('editor.center.duplicate', l))
            self.save_btn.setText(I18n.t('editor.center.save', l))
            self.media_label.setText(I18n.t('editor.center.media_files', l))
            self.image_path.setPlaceholderText(I18n.t('editor.center.image_path_placeholder', l))
            self.browse_image_btn.setText(I18n.t('editor.center.choose_image', l))
            self.audio_path.setPlaceholderText(I18n.t('editor.center.audio_path_placeholder', l))
            self.browse_audio_btn.setText(I18n.t('editor.center.choose_audio', l))
            self.question_type_combo.clear()
            self.question_type_combo.addItem(I18n.t('editor.type.multiple_choice', l), 'multiple_choice')
            self.question_type_combo.addItem(I18n.t('editor.type.true_false', l), 'true_false')
            self.question_type_combo.addItem(I18n.t('editor.type.fill_blank', l), 'fill_blank')
            self.question_type_combo.addItem(I18n.t('editor.type.matching', l), 'matching')
            self.question_type_combo.addItem(I18n.t('editor.type.short_answer', l), 'short_answer')
            self.question_type_combo.addItem(I18n.t('editor.type.essay', l), 'essay')

            try:
                self.question_type_combo.setEnabled(True)
            except Exception:
                pass
            try:
                # Welcome placeholder i18n
                self.welcome_label.setText(I18n.t('editor.center.welcome', l))
            except Exception:
                pass
            if self.current_question:
                try:
                    prefix = I18n.t('editor.question_prefix', l)
                    idx = getattr(self, 'current_index', -1)
                    if idx is not None and idx >= 0:
                        self.question_title.setText(f"{prefix} {idx + 1}")
                    else:
                        self.question_title.setText(prefix)
                except Exception:
                    pass
            try:
                q_type = (self.current_question or {}).get('type', '')
                if q_type == 'multiple_choice':
                    options = (self.current_question or {}).get('options', [])
                    idx = self.correct_answer.value()
                    txt = (options[idx] if options and idx < len(options) else "")
                    if isinstance(txt, dict):
                        txt = txt.get("text", "")
                    self._set_correct_preview(str(txt or ""))
            except Exception:
                pass
        except Exception:
            pass

    def hide_preview_buttons(self):
        """Hide preview buttons for millionaire game - dummy implementation"""
        # This class doesn't have preview buttons, but we provide the method for compatibility
        pass

