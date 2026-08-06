"""
Editor Center Panel - Question editor and game configuration editor
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
                               QTextEdit, QLineEdit, QSpinBox, QCheckBox,
                               QPushButton, QLabel, QGroupBox, QFrame, QScrollArea,
                               QListWidget, QListWidgetItem, QRadioButton, QButtonGroup,
                               QSizePolicy, QAbstractItemView, QStyle)
from PySide6.QtCore import Signal, Qt, Slot, QSignalBlocker, QEvent
import re
from PySide6.QtGui import QFont, QIcon, QTextOption, QPixmap
from eduplay.core.import_service import ImportService
from eduplay.core.asset_loader import materialize_asset_file
from eduplay.ui.widgets.custom_dropdown import FlatDropdown
from eduplay.core.i18n import I18n
from eduplay.core.settings_manager import SettingsManager


class _BaseInlineAnswerRow(QWidget):
    activated = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._focus_widgets = []
        self._delete_button = QPushButton(self)
        self._delete_button.setObjectName("answerDeleteButton")
        self._delete_button.setCursor(Qt.PointingHandCursor)
        self._delete_button.setFlat(True)
        self._delete_button.setFixedSize(20, 20)
        self._delete_button.setToolTip(I18n.t("editor.center.remove_btn"))
        try:
            self._delete_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
            self._delete_button.setIconSize(self._delete_button.size() * 0.58)
        except Exception:
            self._delete_button.setText("x")
        self._delete_button.clicked.connect(self.delete_requested.emit)
        self._delete_button.hide()
        self.setMouseTracking(True)

    def _register_focus_widget(self, widget: QWidget):
        if widget and widget not in self._focus_widgets:
            self._focus_widgets.append(widget)
            widget.installEventFilter(self)

    def _has_focus_inside(self) -> bool:
        return any(widget.hasFocus() for widget in self._focus_widgets)

    def _update_delete_visibility(self, visible: bool):
        try:
            self._delete_button.setVisible(bool(visible))
        except Exception:
            pass

    def eventFilter(self, watched, event):
        if watched in self._focus_widgets:
            if event.type() == QEvent.Type.FocusIn:
                self._update_delete_visibility(True)
                self.activated.emit()
            elif event.type() == QEvent.Type.FocusOut and not self._has_focus_inside():
                self._update_delete_visibility(False)
        return super().eventFilter(watched, event)

    def enterEvent(self, event):
        self._update_delete_visibility(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._has_focus_inside():
            self._update_delete_visibility(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.activated.emit()
        super().mousePressEvent(event)


class _MultipleChoiceOptionRow(_BaseInlineAnswerRow):
    text_changed = Signal(str)
    correct_requested = Signal()

    def __init__(self, text: str = "", is_correct: bool = False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(5)

        self.correct_button = QPushButton(self)
        self.correct_button.setObjectName("optionCorrectButton")
        self.correct_button.setCursor(Qt.PointingHandCursor)
        self.correct_button.setCheckable(True)
        self.correct_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.correct_button.setFixedSize(24, 24)
        self.correct_button.clicked.connect(lambda _checked=False: self.correct_requested.emit())
        layout.addWidget(self.correct_button)

        self.editor = QLineEdit(self)
        self.editor.setObjectName("optionEditor")
        self.editor.setPlaceholderText(I18n.t("editor.center.option_placeholder"))
        self.editor.setMinimumHeight(24)
        self.editor.textChanged.connect(self.text_changed.emit)
        layout.addWidget(self.editor, 1)

        layout.addWidget(self._delete_button)
        self._register_focus_widget(self.editor)
        self.update_state(text, is_correct)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 8px;
            }
            QLineEdit#optionEditor {
                padding: 7px 10px;
            }
            QPushButton#answerDeleteButton {
                border: none;
                background: transparent;
                padding: 0;
            }
            QPushButton#answerDeleteButton:hover {
                background-color: rgba(239, 68, 68, 0.12);
                border-radius: 14px;
            }
        """)
        self.setFixedHeight(36)

    def update_state(self, text: str, is_correct: bool):
        blocker = QSignalBlocker(self.editor)
        self.editor.setText(str(text or ""))
        del blocker
        btn_blocker = QSignalBlocker(self.correct_button)
        self.correct_button.setChecked(bool(is_correct))
        self.correct_button.setText("✓" if is_correct else "")
        del btn_blocker
        self.correct_button.setStyleSheet(
            "QPushButton { border: 1px solid #CBD5E1; border-radius: 12px; font-size: 15px; font-weight: 700; "
            "background-color: #FFFFFF; color: transparent; padding: 0; }"
            "QPushButton:hover { border-color: #10B981; background-color: #FFFFFF; }"
            "QPushButton:checked { border: 1px solid #10B981; background-color: #ECFDF3; color: #10B981; }"
        )

    def focus_editor(self):
        self.editor.setFocus()
        self.editor.selectAll()


class _MatchingPairRow(_BaseInlineAnswerRow):
    values_changed = Signal(str, str)

    def __init__(self, left: str = "", right: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(5)

        self.left_editor = QLineEdit(self)
        self.left_editor.setObjectName("matchingLeftEditor")
        self.left_editor.setPlaceholderText(I18n.t("editor.center.left_column"))
        self.left_editor.setMinimumHeight(26)
        layout.addWidget(self.left_editor, 1)

        self.right_editor = QLineEdit(self)
        self.right_editor.setObjectName("matchingRightEditor")
        self.right_editor.setPlaceholderText(I18n.t("editor.center.right_column"))
        self.right_editor.setMinimumHeight(26)
        layout.addWidget(self.right_editor, 1)

        layout.addWidget(self._delete_button)
        self.left_editor.textChanged.connect(self._emit_values_changed)
        self.right_editor.textChanged.connect(self._emit_values_changed)
        self._register_focus_widget(self.left_editor)
        self._register_focus_widget(self.right_editor)
        self.update_values(left, right)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 8px;
            }
            QLineEdit#matchingLeftEditor,
            QLineEdit#matchingRightEditor {
                padding: 7px 10px;
            }
            QPushButton#answerDeleteButton {
                border: none;
                background: transparent;
                padding: 0;
            }
            QPushButton#answerDeleteButton:hover {
                background-color: rgba(239, 68, 68, 0.12);
                border-radius: 14px;
            }
        """)
        self.setFixedHeight(38)

    def _emit_values_changed(self):
        self.values_changed.emit(self.left_editor.text(), self.right_editor.text())

    def update_values(self, left: str, right: str):
        left_blocker = QSignalBlocker(self.left_editor)
        right_blocker = QSignalBlocker(self.right_editor)
        self.left_editor.setText(str(left or ""))
        self.right_editor.setText(str(right or ""))
        del left_blocker
        del right_blocker

    def focus_left(self):
        self.left_editor.setFocus()
        self.left_editor.selectAll()

class EditorCenterPanel(QWidget):
    """Center panel for editing questions and game configuration"""
    
    # Signals
    question_updated = Signal(dict)  # Emits updated question data
    preview_requested = Signal()  # Request to update preview
    quick_preview_requested = Signal()  # Request quick preview for current question (single-question)
    unsaved_changed = Signal(bool)  # Notify when content becomes dirty
    game_config_updated = Signal(dict)  # Emits updated game config
    
    def __init__(self):
        super().__init__()
        self.current_project = None
        self.current_question = None
        self.current_mode = "question"  # "question" or "game_config"
        self.import_service = ImportService()
        self.is_processing_paste = False
        self._is_adjusting_points = False
        self._is_syncing_option_item = False
        self.init_ui()

    def _lang(self) -> str:
        try:
            return SettingsManager().get_language() or I18n.locale or "en"
        except Exception:
            return getattr(I18n, "locale", "en") or "en"

    def _t(self, key: str, fallback: str) -> str:
        try:
            return I18n.t(key, self._lang())
        except Exception:
            return fallback

    def _icon_text(self, icon: str, key: str, fallback: str) -> str:
        return f"{icon} {self._t(key, fallback)}"
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create stacked widget for different editing modes
        self.stacked_widget = QStackedWidget()
        self._empty_state_index = -1
        
        # Create question editor
        self.create_question_editor()
        
        # Create game config editor
        self.create_game_config_editor()

        self.create_empty_state()
        
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)
        
        # Apply theme-aware styling for container elements; let common widgets use global QSS
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            theme = 'dark'
        bg = '#1E1E24' if theme == 'dark' else '#FFFFFF'
        panel = '#2D2F3A' if theme == 'dark' else '#FFFFFF'
        border = '#4A4E5A' if theme == 'dark' else '#D0D5DD'
        text_primary = '#FFFFFF' if theme == 'dark' else '#1A1A1A'
        alt = '#3A3C47' if theme == 'dark' else '#F5F6FA'
        style = f"""
            EditorCenterPanel {{
                background-color: {bg};
                border: 1px solid {border};
            }}
            .editor-header {{
                background-color: {panel};
                color: {text_primary};
                font-size: 16px;
                font-weight: 700;
                padding: 15px 20px;
                border-bottom: 1px solid {border};
            }}
            .editor-content {{
                padding: 20px;
            }}
            .question-type-selector {{
                background-color: {panel};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 20px;
            }}
            QListWidget {{
                background-color: {panel};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 6px;
                outline: none;
                alternate-background-color: {alt};
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border: none;
            }}
            QListWidget::item:selected {{
                background-color: #10B981;
                color: #FFFFFF;
            }}
            QListWidget::item:hover {{
                background-color: {alt};
                color: {text_primary};
            }}
        """
        self.setStyleSheet(style)
        try:
            self.stacked_widget.setCurrentIndex(self._empty_state_index if self._empty_state_index >= 0 else 0)
        except Exception:
            pass

    def create_empty_state(self):
        widget = QWidget()
        widget.setObjectName("editorCenterEmptyState")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(42, 34, 42, 34)
        layout.setSpacing(16)
        layout.addStretch()
        try:
            lang = SettingsManager().get_language() or "vi"
        except Exception:
            lang = "vi"

        self.empty_state_art = QLabel()
        self.empty_state_art.setAlignment(Qt.AlignCenter)
        self.empty_state_art.setMinimumHeight(260)
        self.empty_state_art.setObjectName("editorCenterEmptyArt")
        self._empty_state_art_loaded = False
        try:
            art_path = materialize_asset_file("eduplay/resources/icons/editing_frame.png")
            pixmap = QPixmap(str(art_path))
            if not pixmap.isNull():
                self.empty_state_art.setPixmap(
                    pixmap.scaled(460, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self._empty_state_art_loaded = True
        except Exception:
            pass
        if not self._empty_state_art_loaded:
            self.empty_state_art.setText("✏️")
            self.empty_state_art.setStyleSheet("font-size:120px;background:transparent;")
        layout.addWidget(self.empty_state_art, 0, Qt.AlignCenter)

        self.empty_state_title = QLabel(I18n.t("editor.center.welcome", lang))
        self.empty_state_title.setObjectName("editorCenterEmptyTitle")
        self.empty_state_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_state_title)

        self.empty_state_subtitle = QLabel(I18n.t("editor.center.no_question", lang))
        self.empty_state_subtitle.setObjectName("editorCenterEmptySubtitle")
        self.empty_state_subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_state_subtitle)
        layout.addStretch()
        self._empty_state_index = self.stacked_widget.addWidget(widget)
    
    def apply_theme(self, theme: str):
        t = 'dark' if str(theme).lower() == 'dark' else 'light'
        bg = '#1E1E24' if t == 'dark' else '#FFFDF8'
        panel = '#2D2F3A' if t == 'dark' else '#FFFFFF'
        border = '#4A4E5A' if t == 'dark' else '#E4E7EC'
        text_primary = '#FFFFFF' if t == 'dark' else '#1A1A1A'
        alt = '#3A3C47' if t == 'dark' else '#F5F6FA'
        empty_title = '#F8FAFC' if t == 'dark' else '#111827'
        empty_subtitle = '#98A2B3' if t == 'dark' else '#667085'
        style = f"""
            EditorCenterPanel {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 18px;
            }}
            .editor-header {{
                background-color: {panel};
                color: {text_primary};
                font-size: 16px;
                font-weight: 700;
                padding: 15px 20px;
                border-bottom: 1px solid {border};
            }}
            .editor-content {{
                padding: 20px;
            }}
            .question-type-selector {{
                background-color: {panel};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px;
                margin-bottom: 20px;
            }}
            QListWidget {{
                background-color: {panel};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 6px;
                outline: none;
                alternate-background-color: {alt};
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border: none;
            }}
            QListWidget::item:selected {{
                background-color: #10B981;
                color: #FFFFFF;
            }}
            QListWidget::item:hover {{
                background-color: {alt};
                color: {text_primary};
            }}
        """
        try:
            self.setStyleSheet(style)
        except Exception:
            pass
        try:
            if hasattr(self, "empty_state_title") and self.empty_state_title:
                self.empty_state_title.setStyleSheet(
                    f"QLabel#editorCenterEmptyTitle{{color:{empty_title};font-size:28px;font-weight:800;background:transparent;}}"
                )
            if hasattr(self, "empty_state_subtitle") and self.empty_state_subtitle:
                self.empty_state_subtitle.setStyleSheet(
                    f"QLabel#editorCenterEmptySubtitle{{color:{empty_subtitle};font-size:14px;font-weight:500;background:transparent;}}"
                )
            if hasattr(self, "empty_state_art") and self.empty_state_art and not getattr(self, "_empty_state_art_loaded", False):
                art_color = '#7F56D9' if t == 'dark' else '#7F56D9'
                self.empty_state_art.setStyleSheet(
                    f"font-size:120px;color:{art_color};background:transparent;"
                )
        except Exception:
            pass
    
    def _minimize_widget(self, w):
        try:
            w.setEnabled(False)
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QSizePolicy
            w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass
        try:
            w.setMinimumSize(0, 0)
            w.setMaximumSize(0, 0)
        except Exception:
            pass
    
    def _restore_widget(self, w):
        try:
            w.setEnabled(True)
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QSizePolicy
            w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        except Exception:
            pass
        try:
            w.setMinimumSize(0, 0)
            w.setMaximumSize(16777215, 16777215)
        except Exception:
            pass
    
    def create_question_editor(self):
        """Create question editor widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel(self._t("editor.center.question_editor_header", "Edit Question"))
        header.setObjectName("editor-header")
        layout.addWidget(header)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        
        # Question type selector
        type_group = self.create_question_type_selector()
        content_layout.addWidget(type_group)
        
        # Question content
        question_group = self.create_question_content_group()
        content_layout.addWidget(question_group)
        
        # Options/answers section (varies by question type)
        self.options_group = self.create_options_group()
        content_layout.addWidget(self.options_group)
        
        # Question settings
        settings_group = self.create_question_settings_group()
        content_layout.addWidget(settings_group)
        try:
            self._force_hide_question_type_if_millionaire()
        except Exception:
            pass
        
        explanation_group = self.create_explanation_group()
        content_layout.addWidget(explanation_group)
        content_layout.addStretch()
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        action_bar = QFrame()
        try:
            action_bar.setFrameShape(QFrame.NoFrame)
        except Exception:
            pass
        try:
            action_bar.setStyleSheet("QFrame { background: transparent; }")
        except Exception:
            pass
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(20, 10, 20, 10)
        action_layout.addStretch()

        self.duplicate_question_btn = QPushButton(self._icon_text("⧉", "editor.center.duplicate", "Duplicate"))
        self.duplicate_question_btn.setObjectName("action-button warning")
        try:
            self.duplicate_question_btn.setStyleSheet("QPushButton { background-color:#F59E0B; color:#fff; border:none; padding:8px 16px; border-radius:6px; font-weight:bold; } QPushButton:hover { background-color:#D97706; }")
        except Exception:
            pass
        self.duplicate_question_btn.clicked.connect(self.duplicate_current_question)
        action_layout.addWidget(self.duplicate_question_btn)

        self.save_question_btn = QPushButton(self._icon_text("💾", "editor.center.save_question", "Save Question"))
        self.save_question_btn.setObjectName("action-button success")
        self.save_question_btn.clicked.connect(self.save_question)
        action_layout.addWidget(self.save_question_btn)

        self.quick_preview_question_btn = QPushButton(self._icon_text("👁", "editor.center.quick_preview", "Preview Question"))
        self.quick_preview_question_btn.setObjectName("action-button info")
        try:
            self.quick_preview_question_btn.setStyleSheet("QPushButton { background-color:#3B82F6; color:#fff; border:none; padding:8px 16px; border-radius:6px; font-weight:bold; } QPushButton:hover { background-color:#2563EB; }")
        except Exception:
            pass
        self.quick_preview_question_btn.clicked.connect(self.request_quick_preview_current_question)
        action_layout.addWidget(self.quick_preview_question_btn)

        self.delete_question_btn = QPushButton(self._icon_text("🗑", "editor.center.delete", "Delete Question"))
        self.delete_question_btn.setObjectName("action-button danger")
        try:
            self.delete_question_btn.setStyleSheet("QPushButton { background-color:#EF4444; color:#fff; border:none; padding:8px 16px; border-radius:6px; font-weight:bold; } QPushButton:hover { background-color:#DC2626; }")
        except Exception:
            pass
        self.delete_question_btn.clicked.connect(self.delete_current_question)
        action_layout.addWidget(self.delete_question_btn)

        layout.addWidget(action_bar)
        
        widget.setLayout(layout)
        self.stacked_widget.addWidget(widget)
        try:
            self.on_game_type_changed(self.game_type_combo.currentText())
        except Exception:
            pass
        try:
            self._force_hide_question_type_if_millionaire()
        except Exception:
            pass
        try:
            self._force_hide_question_type_if_millionaire()
        except Exception:
            pass

    def request_quick_preview_current_question(self):
        try:
            self.quick_preview_requested.emit()
        except Exception:
            pass
    
    def create_game_config_editor(self):
        """Create game configuration editor widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QLabel(self._t("editor.center.game_config_header", "Edit Game Configuration"))
        header.setObjectName("editor-header")
        layout.addWidget(header)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        
        # Game type selection
        game_type_group = QGroupBox(self._t("editor.center.game_type_group", "Game Type"))
        game_type_layout = QVBoxLayout()
        
        self.game_type_combo = FlatDropdown()
        self.game_type_combo.addItems([
            self._t("editor.left.game_type_quiz", "Quiz Classic"),
            self._t("editor.left.game_type_fishing", "Fishing Game"),
            self._t("editor.left.game_type_millionaire", "Who Wants to Be a Millionaire"),
        ])
        self.game_type_combo.currentTextChanged.connect(self.on_game_type_changed)
        game_type_layout.addWidget(self.game_type_combo)
        
        game_type_group.setLayout(game_type_layout)
        content_layout.addWidget(game_type_group)
        
        # General settings
        general_group = QGroupBox(self._t("editor.center.general_settings_group", "General Settings"))
        general_layout = QVBoxLayout()
        general_layout.setSpacing(15)
        
        # Time limit
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel(self._t("editor.center.default_question_time", "Default time per question:")))
        self.time_limit_spin = QSpinBox()
        self.time_limit_spin.setRange(0, 300)
        self.time_limit_spin.setSuffix(self._t("editor.center.seconds_suffix", " sec"))
        self.time_limit_spin.setValue(30)
        time_layout.addWidget(self.time_limit_spin)
        time_layout.addStretch()
        general_layout.addLayout(time_layout)
        
        # Points controls
        points_layout = QVBoxLayout()
        # Auto distribute toggle
        auto_row = QHBoxLayout()
        self.auto_points_check = QCheckBox(self._t("editor.center.auto_points", "Auto-distribute points"))
        self.auto_points_check.setChecked(True)
        auto_row.addWidget(self.auto_points_check)
        auto_row.addStretch()
        points_layout.addLayout(auto_row)
        # Total points
        total_row = QHBoxLayout()
        total_row.addWidget(QLabel(self._t("editor.center.default_points_total", "Total points (quiz and fishing):")))
        self.total_points_spin = QSpinBox()
        self.total_points_spin.setRange(1, 100)
        self.total_points_spin.setValue(100)
        total_row.addWidget(self.total_points_spin)
        total_row.addStretch()
        points_layout.addLayout(total_row)
        # Manual points per question (used khi tắt tự động)
        per_row = QHBoxLayout()
        per_row.addWidget(QLabel(self._t("editor.center.manual_points_per_question", "Points per question (when auto is off):")))
        self.points_spin = QSpinBox()
        self.points_spin.setRange(1, 100)
        self.points_spin.setValue(10)
        per_row.addWidget(self.points_spin)
        per_row.addStretch()
        points_layout.addLayout(per_row)
        general_layout.addLayout(points_layout)
        
        # Tie auto-points to control availability and distribution
        try:
            self.auto_points_check.toggled.connect(self.on_auto_points_toggled)
            self.total_points_spin.valueChanged.connect(self.on_total_points_changed)
        except Exception:
            pass
        try:
            # Moved primary toggle to the left settings tab; keep this one hidden for compatibility.
            self.auto_points_check.setVisible(False)
        except Exception:
            pass
        
        # Show correct answer
        self.show_correct_check = QCheckBox(self._t("editor.center.show_correct_answer", "Show correct answer after each question"))
        self.show_correct_check.setChecked(True)
        self.show_correct_check.toggled.connect(self.save_game_config)
        general_layout.addWidget(self.show_correct_check)
        
        # Randomize questions
        self.randomize_check = QCheckBox(self._t("editor.left.randomize_questions", "Shuffle question order"))
        self.randomize_check.setChecked(True)
        self.randomize_check.toggled.connect(self.save_game_config)
        general_layout.addWidget(self.randomize_check)
        
        general_group.setLayout(general_layout)
        content_layout.addWidget(general_group)
        
        # Quiz-specific settings
        self.quiz_settings_group = QGroupBox(self._t("editor.center.quiz_settings_group", "Quiz Settings"))
        quiz_layout = QVBoxLayout()
        quiz_layout.setSpacing(15)
        
        # Number of options
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel(self._t("editor.center.options_per_question", "Options per question:")))
        self.num_options_spin = QSpinBox()
        self.num_options_spin.setRange(2, 6)
        self.num_options_spin.setValue(4)
        options_layout.addWidget(self.num_options_spin)
        options_layout.addStretch()
        quiz_layout.addLayout(options_layout)
        
        # Allow multiple answers
        self.multiple_answers_check = QCheckBox(self._t("editor.center.allow_multiple_answers", "Allow multiple answers"))
        quiz_layout.addWidget(self.multiple_answers_check)
        
        # Show progress bar
        self.show_progress_check = QCheckBox(self._t("editor.center.show_progress", "Show progress bar"))
        self.show_progress_check.setChecked(True)
        quiz_layout.addWidget(self.show_progress_check)
        
        self.quiz_settings_group.setLayout(quiz_layout)
        content_layout.addWidget(self.quiz_settings_group)
        
        # Fishing game settings
        self.fishing_settings_group = QGroupBox(self._t("fishing.settings_title", "Fishing Settings"))
        fishing_layout = QVBoxLayout()
        fishing_layout.setSpacing(15)
        
        # Fish speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel(self._t("editor.center.fish_swim_speed", "Fish swim speed:")))
        self.fish_speed_spin = QSpinBox()
        self.fish_speed_spin.setRange(1, 10)
        self.fish_speed_spin.setValue(5)
        speed_layout.addWidget(self.fish_speed_spin)
        speed_layout.addStretch()
        fishing_layout.addLayout(speed_layout)
        
        # Number of fish
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel(self._t("fishing.count", "Fish count:")))
        self.fish_count_spin = QSpinBox()
        self.fish_count_spin.setRange(5, 20)
        self.fish_count_spin.setValue(10)
        count_layout.addWidget(self.fish_count_spin)
        count_layout.addStretch()
        fishing_layout.addLayout(count_layout)
        
        # Fish size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel(self._t("editor.center.fish_size", "Fish size:")))
        self.fish_size_combo = FlatDropdown()
        self.fish_size_combo.addItems([
            self._t("editor.center.fish_size_small", "Small"),
            self._t("editor.center.fish_size_medium", "Medium"),
            self._t("editor.center.fish_size_large", "Large"),
        ])
        try:
            self.fish_size_combo.setCurrentIndex(1)
        except Exception:
            pass
        size_layout.addWidget(self.fish_size_combo)
        size_layout.addStretch()
        fishing_layout.addLayout(size_layout)

        # Cute effects toggle
        self.cute_effects_check = QCheckBox(self._t("editor.center.cute_effects", "Cute effects (hearts/sparkles)"))
        self.cute_effects_check.setChecked(False)
        fishing_layout.addWidget(self.cute_effects_check)
        
        self.fishing_settings_group.setLayout(fishing_layout)
        content_layout.addWidget(self.fishing_settings_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.preview_config_btn = QPushButton(self._icon_text("👁️", "editor.center.preview_config", "Preview"))
        self.preview_config_btn.setObjectName("action-button secondary")
        self.preview_config_btn.clicked.connect(self.preview_game_config)
        button_layout.addWidget(self.preview_config_btn)
        
        self.save_config_btn = QPushButton(self._icon_text("💾", "editor.center.save_config", "Save Configuration"))
        self.save_config_btn.setObjectName("action-button success")
        self.save_config_btn.clicked.connect(self.save_game_config)
        button_layout.addWidget(self.save_config_btn)
        
        content_layout.addLayout(button_layout)
        content_layout.addStretch()
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        try:
            self.on_game_type_changed(self.game_type_combo.currentText())
        except Exception:
            pass
        
        widget.setLayout(layout)
        self.stacked_widget.addWidget(widget)
        
        # Initially hide fishing settings
        self.fishing_settings_group.setVisible(False)
    
    def create_question_type_selector(self):
        """Create question type selector"""
        group = QGroupBox(self._t("editor.center.question_type_label", "Question Type"))
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        self.question_type_group = QButtonGroup()
        self._question_type_buttons = {}
        question_types = [
            ("multiple_choice", self._t("editor.type.multiple_choice", "Multiple Choice")),
            ("true_false", self._t("editor.type.true_false", "True/False")),
            ("fill_blank", self._t("editor.type.fill_blank", "Fill in the Blank")),
            ("matching", self._t("editor.type.matching", "Matching")),
            ("short_answer", self._t("editor.type.short_answer", "Short Answer")),
        ]
        
        for type_id, type_name in question_types:
            btn = QRadioButton(type_name)
            btn.setChecked(type_id == "multiple_choice")
            self.question_type_group.addButton(btn)
            self.question_type_group.setId(btn, len(self.question_type_group.buttons()) - 1)
            layout.addWidget(btn)
            self._question_type_buttons[type_id] = btn
        
        self.question_type_group.buttonClicked.connect(self.on_question_type_changed)
        
        group.setLayout(layout)
        # keep reference to toggle visibility when game type is Millionaire
        self.question_type_group_box = group
        try:
            self._force_hide_question_type_if_millionaire()
        except Exception:
            pass
        return group
    
    def on_auto_points_toggled(self, checked: bool):
        try:
            if hasattr(self, "question_auto_points_check"):
                blocker = QSignalBlocker(self.question_auto_points_check)
                self.question_auto_points_check.setChecked(bool(checked))
                del blocker
        except Exception:
            pass
        try:
            # Disable manual per-question (global default) when auto is on
            if hasattr(self, 'points_spin'):
                self.points_spin.setEnabled(not checked)
            if hasattr(self, 'question_points_spin'):
                self.question_points_spin.setEnabled(not checked)
            # Always allow total points editing
            if hasattr(self, 'total_points_spin'):
                self.total_points_spin.setEnabled(True)
        except Exception:
            pass
        try:
            self._is_adjusting_points = True
            self._distribute_points_across_questions()
            current_question = self._get_current_project_question()
            shared_value = self._auto_points_value()
            if hasattr(self, "points_spin"):
                self.points_spin.setValue(shared_value)
            if hasattr(self, 'question_points_spin'):
                if isinstance(current_question, dict):
                    self.question_points_spin.setValue(int(current_question.get("points", shared_value)))
                else:
                    self.question_points_spin.setValue(shared_value)
        except Exception:
            pass
        finally:
            try:
                self._is_adjusting_points = False
            except Exception:
                pass
    
    def on_total_points_changed(self, _v: int):
        try:
            if hasattr(self, "points_spin"):
                self.points_spin.setValue(self._auto_points_value())
            if hasattr(self, 'auto_points_check') and self.auto_points_check.isChecked():
                try:
                    self._is_adjusting_points = True
                    self._distribute_points_across_questions()
                    current_question = self._get_current_project_question()
                    if hasattr(self, 'question_points_spin'):
                        if isinstance(current_question, dict):
                            self.question_points_spin.setValue(int(current_question.get("points", self._auto_points_value())))
                        else:
                            self.question_points_spin.setValue(self._auto_points_value())
                finally:
                    self._is_adjusting_points = False
        except Exception:
            pass
    
    def _auto_points_value(self) -> int:
        try:
            total = int(self.total_points_spin.value())
            n = len((self.current_project or {}).get('questions') or []) or 1
            return max(1, total // max(1, n))
        except Exception:
            return 1

    def _get_project_questions(self) -> list:
        try:
            qs = (self.current_project or {}).get("questions") or []
            return qs if isinstance(qs, list) else []
        except Exception:
            return []

    def _get_current_project_question(self):
        qs = self._get_project_questions()
        try:
            idx = int(getattr(self, "current_index", -1))
        except Exception:
            idx = -1
        if 0 <= idx < len(qs) and isinstance(qs[idx], dict):
            self.current_question = qs[idx]
            return qs[idx]
        try:
            current = self.current_question if isinstance(self.current_question, dict) else None
            cid = current.get("id") if current else None
        except Exception:
            cid = None
        if cid is not None:
            for q in qs:
                if isinstance(q, dict) and q.get("id") == cid:
                    self.current_question = q
                    return q
        if isinstance(self.current_question, dict):
            return self.current_question
        return None
    
    def _distribute_points_across_questions(self):
        try:
            if not self.current_project:
                return
            qs = self.current_project.get('questions') or []
            if not qs:
                return
            total = int(self.total_points_spin.value()) if hasattr(self, "total_points_spin") else 100
            n = len(qs) or 1
            base = max(1, total // n)
            rem = max(0, total - (base * n))
            for i, q in enumerate(qs):
                try:
                    v = base + (1 if i < rem else 0)
                    q["points"] = int(v)
                except Exception:
                    pass
        except Exception:
            pass
    
    def create_question_content_group(self):
        """Create question content group"""
        group = QGroupBox(self._t("editor.center.question_content_group", "Question Content"))
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Question text
        layout.addWidget(QLabel(self._t("editor.center.question_label", "Question:")))
        self.question_text = QTextEdit()
        self._question_placeholder_default = self._t("editor.center.question_placeholder", "Enter your question here...")
        if not self._question_placeholder_default or self._question_placeholder_default == "editor.center.question_placeholder":
            self._question_placeholder_default = "Enter your question here..."
        self._question_placeholder_fill_blank = self._t(
            "editor.center.question_placeholder_fill_blank",
            "Enter your question here... Use ___ where students should fill in the blank."
        )
        if (
            not self._question_placeholder_fill_blank
            or self._question_placeholder_fill_blank == "editor.center.question_placeholder_fill_blank"
        ):
            self._question_placeholder_fill_blank = "Enter your question here... Use ___ where students should fill in the blank."
        self.question_text.setPlaceholderText(self._question_placeholder_default)
        # Let height be responsive instead of fixed small maximum
        self.question_text.setMinimumHeight(120)
        self.question_text.setLineWrapMode(QTextEdit.WidgetWidth)
        try:
            self.question_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        except Exception:
            pass
        try:
            self.question_text.setTabChangesFocus(False)
        except Exception:
            pass
        try:
            self.question_text.setAcceptRichText(False)
        except Exception:
            pass
        self.question_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.question_text.textChanged.connect(self.on_content_changed)
        layout.addWidget(self.question_text)
        fill_blank_hint_text = self._t(
            "editor.center.fill_blank_hint",
            "Luu y: voi cau hoi dien vao cho trong, hay dung ___ (3 dau _) de app nhan dien dung vi tri can dien."
        )
        if not fill_blank_hint_text or fill_blank_hint_text == "editor.center.fill_blank_hint":
            fill_blank_hint_text = "Luu y: voi cau hoi dien vao cho trong, hay dung ___ (3 dau _) de app nhan dien dung vi tri can dien."
        self.fill_blank_question_hint = QLabel(fill_blank_hint_text)
        self.fill_blank_question_hint.setWordWrap(True)
        self.fill_blank_question_hint.setVisible(False)
        try:
            self.fill_blank_question_hint.setStyleSheet("QLabel { color: #667085; font-size: 12px; }")
        except Exception:
            pass
        layout.addWidget(self.fill_blank_question_hint)

        # Question image (optional)
        image_layout = QHBoxLayout()
        layout.addWidget(QLabel(self._t("editor.center.image_optional", "Image (optional):")))
        
        self.question_image_path = QLineEdit()
        self.question_image_path.setPlaceholderText(self._t("editor.center.image_path_placeholder", "Image path..."))
        image_layout.addWidget(self.question_image_path)
        
        self.browse_image_btn = QPushButton(self._t("editor.center.choose_image", "Choose Image"))
        self.browse_image_btn.setObjectName("action-button secondary")
        self.browse_image_btn.clicked.connect(self.browse_image)
        image_layout.addWidget(self.browse_image_btn)
        
        layout.addLayout(image_layout)
        
        
        
        group.setLayout(layout)
        return group

    def create_explanation_group(self):
        """Create explanation editor group and keep it at the bottom"""
        group = QGroupBox(self._t("editor.center.explanation", "Explanation (optional):"))
        layout = QVBoxLayout()
        self.explanation_text = QTextEdit()
        self.explanation_text.setPlaceholderText(self._t("editor.center.explanation_placeholder", "Provide explanation or feedback for this question..."))
        self.explanation_text.setMinimumHeight(100)
        self.explanation_text.setLineWrapMode(QTextEdit.WidgetWidth)
        try:
            self.explanation_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        except Exception:
            pass
        try:
            self.explanation_text.setTabChangesFocus(False)
        except Exception:
            pass
        try:
            self.explanation_text.setAcceptRichText(False)
        except Exception:
            pass
        self.explanation_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.explanation_text.textChanged.connect(self.on_content_changed)
        layout.addWidget(self.explanation_text)
        group.setLayout(layout)
        return group
    
    def create_options_group(self):
        """Create options/answers group (content varies by question type)"""
        group = QGroupBox(self._t("editor.center.answers_group", "Answers"))
        self.options_layout = QVBoxLayout()
        self.options_layout.setSpacing(10)
        
        # Create stacked widget for different option types
        self.options_stacked = QStackedWidget()
        
        # Multiple choice options
        self.create_multiple_choice_options()
        
        # True/False options
        self.create_true_false_options()
        
        # Fill blank options
        self.create_fill_blank_options()
        
        # Matching options
        self.create_matching_options()
        
        # Short answer options
        self.create_short_answer_options()
        
        self.options_layout.addWidget(self.options_stacked)
        self.options_stacked.setMinimumHeight(230)
        
        # Add option button (for types that support it)
        btn_row = QHBoxLayout()
        self.add_option_btn = QPushButton(f"+ {self._t('editor.center.add_option_btn', 'Add Option')}")
        self.add_option_btn.setObjectName("action-button secondary")
        self.add_option_btn.clicked.connect(self.add_option)
        btn_row.addWidget(self.add_option_btn)
        self.bulk_options_btn = QPushButton(self._t("editor.center.bulk_options", "Bulk Edit"))
        self.bulk_options_btn.setObjectName("action-button")
        self.bulk_options_btn.clicked.connect(self.open_options_editor)
        btn_row.addWidget(self.bulk_options_btn)
        btn_row.addStretch()
        self.options_layout.addLayout(btn_row)
        
        group.setLayout(self.options_layout)
        return group
    
    def create_multiple_choice_options(self):
        """Create multiple choice options widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        self.options_list = QListWidget()
        self.options_list.setAlternatingRowColors(True)
        self.options_list.setSpacing(6)
        self.options_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.options_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.options_list.setStyleSheet(
            "QListWidget::item { padding: 0px; margin: 0px; border: none; background: transparent; }"
            "QListWidget::item:selected { background: transparent; color: inherit; }"
            "QListWidget::item:hover { background: transparent; }"
        )
        try:
            self.options_list.setWordWrap(True)
        except Exception:
            pass
        self.options_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.options_list.itemDoubleClicked.connect(self.edit_option)
        try:
            self.options_list.itemClicked.connect(self.toggle_correct_option)
        except Exception:
            pass
        layout.addWidget(self.options_list)
        
        # Add some default options
        for i in range(4):
            self.add_multiple_choice_option(f"{self._t('import.default.option', 'Option')} {i + 1}", i == 0)
        self._update_compact_list_height(self.options_list, min_rows=4, max_rows=4)
        
        widget.setLayout(layout)
        self.options_stacked.addWidget(widget)
    
    def create_true_false_options(self):
        """Create true/false options widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        self.true_false_group = QButtonGroup()
        
        true_radio = QRadioButton(self._t("editor.center.true", "True"))
        false_radio = QRadioButton(self._t("editor.center.false", "False"))
        false_radio.setChecked(True)
        
        self.true_false_group.addButton(true_radio)
        self.true_false_group.setId(true_radio, 1)
        self.true_false_group.addButton(false_radio)
        self.true_false_group.setId(false_radio, 0)
        
        layout.addWidget(true_radio)
        layout.addWidget(false_radio)
        layout.addStretch()
        
        widget.setLayout(layout)
        self.options_stacked.addWidget(widget)
    
    def create_fill_blank_options(self):
        """Create fill-in-the-blank options widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        layout.addWidget(QLabel(self._t("editor.center.correct_answers_multiline", "Accepted answers (one per line):")))
        self.fill_blank_answers = QTextEdit()
        self.fill_blank_answers.setPlaceholderText(self._t("editor.center.answers_placeholder_multiline", "answer 1\nanswer 2\nanswer 3"))
        self.fill_blank_answers.setMaximumHeight(100)
        layout.addWidget(self.fill_blank_answers)
        
        # Case sensitivity
        self.case_sensitive_check = QCheckBox(self._t("editor.center.case_sensitive", "Case Sensitive"))
        layout.addWidget(self.case_sensitive_check)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        self.options_stacked.addWidget(widget)

        # Configure editor behavior for Tab key
        try:
            self.fill_blank_answers.setTabChangesFocus(False)
        except Exception:
            pass
        try:
            self.fill_blank_answers.setAcceptRichText(False)
        except Exception:
            pass
    
    def create_matching_options(self):
        """Create matching options widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        header_layout.setSpacing(8)
        left_label = QLabel(self._t("editor.center.left_column", "Left"))
        right_label = QLabel(self._t("editor.center.right_column", "Right"))
        try:
            left_label.setStyleSheet("QLabel { font-weight: 700; color: #475467; }")
            right_label.setStyleSheet("QLabel { font-weight: 700; color: #475467; }")
        except Exception:
            pass
        header_layout.addWidget(left_label, 1)
        header_layout.addWidget(right_label, 1)
        header_layout.addSpacing(28)
        layout.addWidget(header)
        
        self.matching_pairs_list = QListWidget()
        self.matching_pairs_list.setAlternatingRowColors(True)
        self.matching_pairs_list.setSpacing(6)
        self.matching_pairs_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.matching_pairs_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matching_pairs_list.setStyleSheet(
            "QListWidget::item { padding: 0px; margin: 0px; border: none; background: transparent; }"
            "QListWidget::item:selected { background: transparent; color: inherit; }"
            "QListWidget::item:hover { background: transparent; }"
        )
        layout.addWidget(self.matching_pairs_list)
        
        # Add some default pairs
        for i in range(3):
            self.add_matching_pair(f"{self._t('editor.center.item_prefix', 'Item')} {i + 1}", f"{self._t('editor.center.content_prefix', 'Content')} {i + 1}")
        self._update_compact_list_height(self.matching_pairs_list, min_rows=3, max_rows=4)
        
        widget.setLayout(layout)
        self.options_stacked.addWidget(widget)
    
    def create_short_answer_options(self):
        """Create short answer options widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        layout.addWidget(QLabel(self._t("editor.center.correct_answers_multiline", "Accepted answers (one per line):")))
        self.short_answer_answers = QTextEdit()
        self.short_answer_answers.setPlaceholderText(self._t("editor.center.answers_placeholder_multiline", "answer 1\nanswer 2\nanswer 3"))
        self.short_answer_answers.setMaximumHeight(100)
        layout.addWidget(self.short_answer_answers)
        
        # Answer length limit
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel(self._t("editor.center.answer_length_limit", "Answer length limit:")))
        self.answer_length_spin = QSpinBox()
        self.answer_length_spin.setRange(10, 500)
        self.answer_length_spin.setValue(100)
        self.answer_length_spin.setSuffix(self._t("editor.center.characters_suffix", " chars"))
        length_layout.addWidget(self.answer_length_spin)
        length_layout.addStretch()
        layout.addLayout(length_layout)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        self.options_stacked.addWidget(widget)
    
    def create_question_settings_group(self):
        """Create question settings group"""
        group = QGroupBox(self._t("editor.center.question_settings_group", "Question Settings"))
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Difficulty level
        difficulty_layout = QHBoxLayout()
        difficulty_layout.addWidget(QLabel(self._t("editor.left.difficulty_label", "Difficulty:")))
        self.difficulty_combo = FlatDropdown()
        self.difficulty_combo.addItems([
            self._t("editor.left.difficulty_easy", "Easy"),
            self._t("editor.left.difficulty_medium", "Medium"),
            self._t("editor.left.difficulty_hard", "Hard"),
        ])
        difficulty_layout.addWidget(self.difficulty_combo)
        difficulty_layout.addStretch()
        layout.addLayout(difficulty_layout)
        
        # Time limit for this question
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel(self._t("editor.center.time_limit", "Time for this question (seconds):")))
        self.question_time_spin = QSpinBox()
        self.question_time_spin.setRange(0, 300)
        self.question_time_spin.setSuffix(self._t("editor.center.seconds_suffix", " sec"))
        self.question_time_spin.setValue(30)
        time_layout.addWidget(self.question_time_spin)
        time_layout.addStretch()
        layout.addLayout(time_layout)
        
        # Auto points mirror toggle (global) for quick access
        auto_mirror_layout = QHBoxLayout()
        self.question_auto_points_check = QCheckBox(self._t("editor.center.auto_points_global", "Auto-distribute points (global)"))
        try:
            # Default to True; will sync after game config loads
            self.question_auto_points_check.setChecked(True)
        except Exception:
            pass
        try:
            self.question_auto_points_check.toggled.connect(self.on_question_auto_points_toggled)
        except Exception:
            pass
        try:
            # Global auto-points toggle now lives in the left settings tab.
            self.question_auto_points_check.setVisible(False)
        except Exception:
            pass
        auto_mirror_layout.addWidget(self.question_auto_points_check)
        auto_mirror_layout.addStretch()
        layout.addLayout(auto_mirror_layout)
        
        # Points for this question
        points_layout = QHBoxLayout()
        points_layout.addWidget(QLabel(self._t("editor.center.points_label", "Points:")))
        self.question_points_spin = QSpinBox()
        self.question_points_spin.setRange(1, 100)
        self.question_points_spin.setValue(10)
        points_layout.addWidget(self.question_points_spin)
        points_layout.addStretch()
        layout.addLayout(points_layout)

        try:
            self.question_time_spin.valueChanged.connect(self._on_question_settings_spin_changed)
            self.question_points_spin.valueChanged.connect(self._on_question_settings_spin_changed)
        except Exception:
            pass
        
        # Question tags (optional)
        layout.addWidget(QLabel(self._t("editor.center.question_tags", "Tags (optional):")))
        self.question_tags = QLineEdit()
        self.question_tags.setPlaceholderText(self._t("editor.center.question_tags_placeholder", "math, grade 6, algebra (comma-separated)"))
        layout.addWidget(self.question_tags)
        
        group.setLayout(layout)
        return group
    
    def on_question_auto_points_toggled(self, checked: bool):
        try:
            # Mirror to global toggle if available
            if hasattr(self, 'auto_points_check') and self.auto_points_check.isChecked() != checked:
                blocker = QSignalBlocker(self.auto_points_check)
                self.auto_points_check.setChecked(checked)
                del blocker
        except Exception:
            pass
        # Reuse the same logic as global toggle
        self.on_auto_points_toggled(checked)

    def on_question_type_changed(self, button):
        """Handle question type change"""
        type_index = self.question_type_group.id(button)
        question_types = ["multiple_choice", "true_false", "fill_blank", "matching", "short_answer"]
        
        if type_index < len(question_types):
            self.current_question_type = question_types[type_index]
            self.options_stacked.setCurrentIndex(type_index)
            is_fill_blank = self.current_question_type == "fill_blank"
            if hasattr(self, "fill_blank_question_hint"):
                self.fill_blank_question_hint.setVisible(is_fill_blank)
            if hasattr(self, "question_text"):
                self.question_text.setPlaceholderText(
                    self._question_placeholder_fill_blank if is_fill_blank else self._question_placeholder_default
                )
            
            # Show/hide add option button
            show_add_button = self.current_question_type in ["multiple_choice", "matching"]
            self.add_option_btn.setVisible(show_add_button)
            if hasattr(self, 'bulk_options_btn'):
                self.bulk_options_btn.setVisible(self.current_question_type == "multiple_choice")
    
    def on_content_changed(self):
        """Handle content changes"""
        # Try smart parse if content looks like a pasted block
        if not self.is_processing_paste:
            self._try_smart_parse()
            
        self.preview_requested.emit()
        try:
            self.unsaved_changed.emit(True)
        except Exception:
            pass

    def _on_question_settings_spin_changed(self, _v: int):
        try:
            current_question = self._get_current_project_question()
            if isinstance(current_question, dict):
                current_question["time_limit"] = int(self.question_time_spin.value())
                if getattr(self, "_is_adjusting_points", False):
                    current_question["points"] = int(self.question_points_spin.value())
                else:
                    self._on_manual_question_points_changed(int(self.question_points_spin.value()))
        except Exception:
            pass
        self.on_content_changed()

    def _on_manual_question_points_changed(self, new_points: int):
        try:
            current_question = self._get_current_project_question()
            if not isinstance(current_question, dict):
                return
            if hasattr(self, "auto_points_check") and bool(self.auto_points_check.isChecked()):
                try:
                    self._is_adjusting_points = True
                    self._distribute_points_across_questions()
                    current_question = self._get_current_project_question()
                    self.question_points_spin.setValue(int(current_question.get("points", self._auto_points_value())))
                finally:
                    self._is_adjusting_points = False
                return
            qs = self._get_project_questions()
            if not isinstance(qs, list) or len(qs) <= 1:
                current_question["points"] = int(max(1, new_points))
                return
            total = int(self.total_points_spin.value()) if hasattr(self, "total_points_spin") else 100
            try:
                idx = int(getattr(self, "current_index", -1))
            except Exception:
                idx = -1
            if idx < 0 or idx >= len(qs) or qs[idx] is not current_question:
                idx = -1
                for i, q in enumerate(qs):
                    if q is current_question:
                        idx = i
                        break
            if idx < 0:
                current_question["points"] = int(max(1, new_points))
                return

            other_count = len(qs) - 1
            min_others_sum = other_count * 1
            target_for_current = int(max(1, min(int(new_points), total - min_others_sum)))
            remaining = int(total - target_for_current)
            base = remaining // other_count if other_count > 0 else 0
            rem = remaining - (base * other_count)
            try:
                self._is_adjusting_points = True
                current_question["points"] = target_for_current
                j = 0
                for i, q in enumerate(qs):
                    if i == idx or not isinstance(q, dict):
                        continue
                    v = int(max(1, base + (1 if j < rem else 0)))
                    q["points"] = v
                    j += 1
                try:
                    self.question_points_spin.setValue(int(current_question.get("points", target_for_current)))
                except Exception:
                    pass
            finally:
                self._is_adjusting_points = False
        except Exception:
            try:
                current_question = self._get_current_project_question()
                if isinstance(current_question, dict):
                    current_question["points"] = int(max(1, new_points))
            except Exception:
                pass

    def _try_smart_parse(self):
        """Try to parse content as a smart question block"""
        text = self.question_text.toPlainText()
        if not text or len(text) < 20:  # Too short
            return

        # Check for indicators of a full question block
        has_newlines = text.count('\n') >= 2
        # Stronger heuristics to avoid false positives while typing
        has_mc_indicators = (
            (('A.' in text or 'A)' in text or 'A:' in text) and ('B.' in text or 'B)' in text or 'B:' in text)) or
            ('- ' in text and '\n- ' in text) or
            ('* ' in text and '\n* ' in text) or
            (re.search(r'\n1[\\.)]\\s', text) and re.search(r'\n2[\\.)]\\s', text))
        )
        has_answer = ('Answer:' in text or 'Đáp án:' in text or 'Câu:' in text or 'Question:' in text)
        has_tf = 'True' in text and 'False' in text
        
        # Only proceed if it looks like a structured block
        if not (has_newlines and (has_mc_indicators or has_answer or has_tf)):
            return

        try:
            # Parse
            questions = self.import_service.parse_smart_format(text)
            if questions and len(questions) > 0:
                q = questions[0]
                
                # Check if parse actually extracted something meaningful (not just the text as question)
                if len(q.get('options', [])) > 0 or q.get('answers') or q.get('pairs'):
                    self.is_processing_paste = True
                    # Update UI with parsed data
                    self._populate_question_from_data(q)
        except Exception:
            pass
        finally:
            self.is_processing_paste = False

    def _set_question_type(self, type_str: str):
        """Set question type by string"""
        mapping = {
            "multiple_choice": 0,
            "true_false": 1,
            "fill_blank": 2,
            "matching": 3,
            "short_answer": 4
        }
        idx = mapping.get(type_str, 0)
        btn = self.question_type_group.button(idx)
        if btn:
            btn.setChecked(True)
            self.on_question_type_changed(btn)

    def _populate_question_from_data(self, data: dict):
        """Populate UI from question data"""
        # Set type
        q_type = data.get("type", "multiple_choice")
        self._set_question_type(q_type)
        
        # Set question text
        self.question_text.setPlainText(data.get("question", ""))
        
        # Set explanation
        if data.get("explanation"):
            self.explanation_text.setPlainText(data.get("explanation", ""))
            
        # Set options based on type
        if q_type == "multiple_choice":
            self.options_list.clear()
            ca = data.get("correct_answer", 0)
            correct_idx = 0
            if isinstance(ca, int):
                correct_idx = ca
            else:
                s = str(ca).strip().upper()
                if len(s) == 1 and s in "ABCDEF":
                    correct_idx = ord(s) - ord('A')
                elif s.isdigit():
                    try:
                        correct_idx = int(s)
                    except Exception:
                        correct_idx = 0
            
            options = data.get("options", [])
            for i, opt in enumerate(options):
                # Determine if correct
                is_correct = (i == correct_idx)
                
                self.add_multiple_choice_option(opt, is_correct)
            self._update_compact_list_height(self.options_list, min_rows=4, max_rows=4)
                
        elif q_type == "true_false":
            is_true = data.get("correct_answer") is True or str(data.get("correct_answer")).lower() == "true"
            try:
                btn = self.true_false_group.button(1 if is_true else 0)
                if btn:
                    btn.setChecked(True)
            except Exception:
                pass
                    
        elif q_type == "fill_blank":
            answers = data.get("answers", []) or data.get("correct_answers", [])
            self.fill_blank_answers.setPlainText("\n".join(answers))
            if "case_sensitive" in data:
                self.case_sensitive_check.setChecked(data["case_sensitive"])
        elif q_type == "matching":
            self.matching_pairs_list.clear()
            pairs = data.get("pairs", [])
            for pair in pairs:
                self.add_matching_pair(pair.get("left", ""), pair.get("right", ""))
            self._update_compact_list_height(self.matching_pairs_list, min_rows=3, max_rows=4)
        elif q_type == "short_answer":
            answers = data.get("answers", [])
            self.short_answer_answers.setPlainText("\n".join(answers))
    
    def open_options_editor(self):
        """Open a simple bulk editor for multiple-choice options"""
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, QLabel, QSpinBox, QPushButton
            if self.get_current_question_type() != "multiple_choice":
                return
            
            dlg = QDialog(self)
            dlg.setWindowTitle(self._t("editor.center.bulk_options_dialog_title", "Answer Options"))
            
            # Get current theme
            try:
                theme = SettingsManager().get_theme() or 'dark'
            except:
                theme = 'dark'
            
            # Set dialog style based on theme
            if theme == 'dark':
                dlg.setStyleSheet("""
                    QDialog {
                        background-color: #1E1E1E;
                    }
                    QLabel {
                        color: #E0E0E0;
                        font-size: 13px;
                        padding: 5px 0px;
                    }
                    QTextEdit {
                        background-color: #2D2D30;
                        border: 1px solid #3A3A40;
                        border-radius: 4px;
                        padding: 8px;
                        color: #E0E0E0;
                        font-size: 13px;
                    }
                    QTextEdit:focus {
                        border: 2px solid #4CAF50;
                        background-color: #25252B;
                    }
                    QSpinBox {
                        background-color: #2D2D30;
                        border: 1px solid #3A3A40;
                        border-radius: 4px;
                        padding: 5px;
                        color: #E0E0E0;
                        min-width: 80px;
                    }
                    QSpinBox::up-button, QSpinBox::down-button {
                        background-color: #3A3A40;
                        border: none;
                    }
                    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                        background-color: #4A4A50;
                    }
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 10px 20px;
                        font-size: 13px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:pressed {
                        background-color: #3d8b40;
                    }
                    QPushButton#cancelBtn {
                        background-color: #f44336;
                    }
                    QPushButton#cancelBtn:hover {
                        background-color: #da190b;
                    }
                """)
            else:
                dlg.setStyleSheet("""
                    QDialog {
                        background-color: #f5f5f5;
                    }
                    QLabel {
                        color: #333333;
                        font-size: 13px;
                        padding: 5px 0px;
                    }
                    QTextEdit {
                        background-color: white;
                        border: 1px solid #cccccc;
                        border-radius: 4px;
                        padding: 8px;
                        color: #333333;
                        font-size: 13px;
                    }
                    QTextEdit:focus {
                        border: 2px solid #4CAF50;
                    }
                    QSpinBox {
                        background-color: white;
                        border: 1px solid #cccccc;
                        border-radius: 4px;
                        padding: 5px;
                        color: #333333;
                        min-width: 80px;
                    }
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 10px 20px;
                        font-size: 13px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:pressed {
                        background-color: #3d8b40;
                    }
                    QPushButton#cancelBtn {
                        background-color: #f44336;
                    }
                    QPushButton#cancelBtn:hover {
                        background-color: #da190b;
                    }
                """)
            
            lay = QVBoxLayout(dlg)
            lay.setSpacing(10)
            lay.setContentsMargins(20, 20, 20, 20)
            
            txt = QTextEdit()
            txt.setPlaceholderText(self._t("editor.center.bulk_options_dialog_placeholder", "Enter each option on a new line..."))
            
            current_options = []
            correct_idx = 0
            for i in range(self.options_list.count()):
                it = self.options_list.item(i)
                d = it.data(Qt.ItemDataRole.UserRole) or {}
                current_options.append(str(d.get("text","")).strip())
                if bool(d.get("correct", False)):
                    correct_idx = i
            txt.setPlainText("\n".join([o for o in current_options if o]))
            
            lay.addWidget(QLabel(self._t("editor.center.bulk_options_dialog_hint", "Each line is one answer:")))
            lay.addWidget(txt)
            
            row = QHBoxLayout()
            row.setSpacing(10)
            row.addWidget(QLabel(self._t("editor.center.bulk_options_dialog_correct_index", "Correct answer (index starting from 1):")))
            spin = QSpinBox()
            spin.setMinimum(1)
            spin.setMaximum(max(1, max(4, len(current_options))))
            spin.setValue(max(1, correct_idx+1))
            row.addWidget(spin)
            row.addStretch()
            lay.addLayout(row)
            
            btns = QHBoxLayout()
            btns.setSpacing(10)
            btns.addStretch()
            ok = QPushButton(self._t("common.save", "Save"))
            cancel = QPushButton(self._t("common.cancel", "Cancel"))
            cancel.setObjectName("cancelBtn")
            btns.addWidget(cancel)
            btns.addWidget(ok)
            lay.addLayout(btns)
            
            cancel.clicked.connect(dlg.reject)
            ok.clicked.connect(dlg.accept)
            
            if dlg.exec():
                lines = [l.strip() for l in txt.toPlainText().splitlines() if l.strip()]
                idx = max(1, min(spin.value(), max(1, len(lines)))) - 1
                self.options_list.clear()
                for i, line in enumerate(lines):
                    self.add_multiple_choice_option(line, i == idx)
        except Exception:
            pass
    
    def delete_current_question(self):
        """Emit delete action for current question"""
        try:
            if not self.current_question:
                return
            payload = {
                "action": "delete",
                "question": self.current_question,
                "question_id": self.current_question.get("id") if isinstance(self.current_question, dict) else None
            }
            try:
                idx = getattr(self, "current_index", None)
                if isinstance(idx, int) and idx >= 0:
                    payload["index"] = idx
            except Exception:
                pass
            self.question_updated.emit(payload)
        except Exception:
            pass

    def duplicate_current_question(self):
        try:
            if not self.current_question:
                return
            payload = {
                "action": "duplicate",
                "question": self.current_question,
                "question_id": self.current_question.get("id") if isinstance(self.current_question, dict) else None,
            }
            self.question_updated.emit(payload)
        except Exception:
            pass
                


    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            h = max(self.height(), 400)
            qh = max(120, int(h * 0.20))
            eh = max(100, int(h * 0.15))
            self.question_text.setMinimumHeight(qh)
            self.explanation_text.setMinimumHeight(eh)
        except Exception:
            pass
    
    def add_option(self):
        """Add a new option (for multiple choice and matching)"""
        qtype = None
        try:
            qtype = self.get_current_question_type()
        except Exception:
            qtype = None
        if qtype == "multiple_choice":
            option_text = f"Đáp án {self.options_list.count() + 1}"
            item = self.add_multiple_choice_option(option_text, False)
            self.edit_option(item)
            try:
                self.unsaved_changed.emit(True)
            except Exception:
                pass
        elif qtype == "matching":
            self.add_matching_pair("Mục mới", "Nội dung mới")
    
    def add_multiple_choice_option(self, text: str, is_correct: bool = False):
        """Add a multiple choice option"""
        item = QListWidgetItem()
        self._apply_multiple_choice_item_state(item, str(text or ""), bool(is_correct))
        self.options_list.addItem(item)
        self._attach_multiple_choice_row_widget(item)
        self._update_compact_list_height(self.options_list, min_rows=4, max_rows=4)
        return item

    def _apply_multiple_choice_item_state(self, item: QListWidgetItem, text: str, is_correct: bool):
        clean_text = str(text or "")
        self._is_syncing_option_item = True
        try:
            item.setData(Qt.ItemDataRole.UserRole, {"text": clean_text, "correct": bool(is_correct)})
            item.setData(Qt.ItemDataRole.EditRole, clean_text)
            item.setText("")
            row_widget = self.options_list.itemWidget(item) if hasattr(self, "options_list") else None
            if isinstance(row_widget, _MultipleChoiceOptionRow):
                row_widget.update_state(clean_text, bool(is_correct))
        finally:
            self._is_syncing_option_item = False

    def _attach_multiple_choice_row_widget(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        row_widget = _MultipleChoiceOptionRow(
            text=data.get("text", ""),
            is_correct=bool(data.get("correct", False)),
            parent=self.options_list,
        )
        row_widget.activated.connect(lambda item=item: self._focus_option_item(item))
        row_widget.correct_requested.connect(lambda item=item: self.toggle_correct_option(item))
        row_widget.text_changed.connect(lambda value, item=item: self._on_option_row_text_changed(item, value))
        row_widget.delete_requested.connect(lambda item=item: self.remove_multiple_choice_option(item))
        self.options_list.setItemWidget(item, row_widget)
        item.setSizeHint(row_widget.sizeHint())

    def _focus_option_item(self, item: QListWidgetItem):
        if not item:
            return
        try:
            self.options_list.setCurrentItem(item)
            self.options_list.scrollToItem(item)
        except Exception:
            pass

    def _on_option_row_text_changed(self, item: QListWidgetItem, value: str):
        if not item:
            return
        try:
            data = item.data(Qt.ItemDataRole.UserRole) or {}
        except Exception:
            data = {}
        self._apply_multiple_choice_item_state(item, value, bool(data.get("correct", False)))
        try:
            self.unsaved_changed.emit(True)
        except Exception:
            pass

    def remove_multiple_choice_option(self, item: QListWidgetItem):
        if not item:
            return
        row = self.options_list.row(item)
        if row < 0:
            return
        try:
            data = item.data(Qt.ItemDataRole.UserRole) or {}
            was_correct = bool(data.get("correct", False))
        except Exception:
            was_correct = False
        widget = self.options_list.itemWidget(item)
        removed = self.options_list.takeItem(row)
        try:
            if widget:
                widget.deleteLater()
        except Exception:
            pass
        del removed
        if was_correct and self.options_list.count() > 0:
            self.toggle_correct_option(self.options_list.item(min(row, self.options_list.count() - 1)))
        self._update_compact_list_height(self.options_list, min_rows=4, max_rows=4)
        try:
            self.unsaved_changed.emit(True)
        except Exception:
            pass

    def _extract_option_edit_text(self, item: QListWidgetItem) -> str:
        raw_text = str(item.data(Qt.ItemDataRole.EditRole) or item.text() or "").strip()
        if raw_text.startswith("✓ ") or raw_text.startswith("○ "):
            raw_text = raw_text[2:].strip()
        return raw_text

    def _on_option_item_changed(self, item: QListWidgetItem):
        if self._is_syncing_option_item:
            return
        try:
            data = item.data(Qt.ItemDataRole.UserRole) or {}
        except Exception:
            data = {}
        new_text = self._extract_option_edit_text(item) or str(data.get("text", "") or "").strip()
        self._apply_multiple_choice_item_state(item, new_text, bool(data.get("correct", False)))
        try:
            self.unsaved_changed.emit(True)
        except Exception:
            pass
    
    def toggle_correct_option(self, item: QListWidgetItem):
        try:
            self._focus_option_item(item)
            for i in range(self.options_list.count()):
                it = self.options_list.item(i)
                d = it.data(Qt.ItemDataRole.UserRole) or {}
                self._apply_multiple_choice_item_state(it, d.get("text", it.text()), it is item)
        except Exception:
            pass
        try:
            self.unsaved_changed.emit(True)
        except Exception:
            pass
    
    def add_matching_pair(self, left: str, right: str):
        """Add a matching pair"""
        item = QListWidgetItem()
        self._apply_matching_pair_state(item, left, right)
        self.matching_pairs_list.addItem(item)
        self._attach_matching_pair_row_widget(item)
        self._update_compact_list_height(self.matching_pairs_list, min_rows=3, max_rows=4)
        return item

    def _apply_matching_pair_state(self, item: QListWidgetItem, left: str, right: str):
        left_text = str(left or "")
        right_text = str(right or "")
        item.setData(Qt.ItemDataRole.UserRole, {"left": left_text, "right": right_text})
        item.setText("")
        row_widget = self.matching_pairs_list.itemWidget(item) if hasattr(self, "matching_pairs_list") else None
        if isinstance(row_widget, _MatchingPairRow):
            row_widget.update_values(left_text, right_text)

    def _attach_matching_pair_row_widget(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        row_widget = _MatchingPairRow(
            left=data.get("left", ""),
            right=data.get("right", ""),
            parent=self.matching_pairs_list,
        )
        row_widget.activated.connect(lambda item=item: self._focus_matching_item(item))
        row_widget.values_changed.connect(
            lambda left, right, item=item: self._on_matching_pair_changed(item, left, right)
        )
        row_widget.delete_requested.connect(lambda item=item: self.remove_matching_pair(item))
        self.matching_pairs_list.setItemWidget(item, row_widget)
        item.setSizeHint(row_widget.sizeHint())

    def _focus_matching_item(self, item: QListWidgetItem):
        if not item:
            return
        try:
            self.matching_pairs_list.setCurrentItem(item)
            self.matching_pairs_list.scrollToItem(item)
        except Exception:
            pass

    def _on_matching_pair_changed(self, item: QListWidgetItem, left: str, right: str):
        if not item:
            return
        self._apply_matching_pair_state(item, left, right)
        try:
            self.unsaved_changed.emit(True)
        except Exception:
            pass

    def remove_matching_pair(self, item: QListWidgetItem):
        if not item:
            return
        row = self.matching_pairs_list.row(item)
        if row < 0:
            return
        widget = self.matching_pairs_list.itemWidget(item)
        removed = self.matching_pairs_list.takeItem(row)
        try:
            if widget:
                widget.deleteLater()
        except Exception:
            pass
        del removed
        self._update_compact_list_height(self.matching_pairs_list, min_rows=3, max_rows=4)
        try:
            self.unsaved_changed.emit(True)
        except Exception:
            pass

    def _update_compact_list_height(self, list_widget: QListWidget, min_rows: int = 1, max_rows: int = 4):
        try:
            count = max(int(list_widget.count()), 0)
            if count <= 0:
                return
            sample_item = list_widget.item(0)
            sample_widget = list_widget.itemWidget(sample_item) if sample_item else None
            row_height = sample_widget.height() if sample_widget else list_widget.sizeHintForRow(0)
            row_height = max(int(row_height), 28)
            visible_rows = min(max_rows, max(min_rows, count))
            frame = int(list_widget.frameWidth()) * 2
            spacing = int(list_widget.spacing()) * max(0, visible_rows - 1)
            height = frame + spacing + (row_height * visible_rows) + 20
            list_widget.setMinimumHeight(height)
            list_widget.setMaximumHeight(height)
            list_widget.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff if count <= max_rows else Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            parent = list_widget.parentWidget()
            if parent is not None:
                parent.setMinimumHeight(height + 12)
        except Exception:
            pass
    
    def edit_option(self, item: QListWidgetItem):
        """Edit a multiple choice option"""
        try:
            if not item:
                return
            self._focus_option_item(item)
            row_widget = self.options_list.itemWidget(item)
            if isinstance(row_widget, _MultipleChoiceOptionRow):
                row_widget.focus_editor()
        except Exception:
            pass
    
    def edit_matching_pair(self, item: QListWidgetItem):
        """Edit a matching pair"""
        try:
            if not item:
                return
            self._focus_matching_item(item)
            row_widget = self.matching_pairs_list.itemWidget(item)
            if isinstance(row_widget, _MatchingPairRow):
                row_widget.focus_left()
        except Exception:
            pass
    
    def browse_image(self):
        """Browse for question image"""
        try:
            from PySide6.QtWidgets import QFileDialog
            title = self._t("editor.center.image_dialog_title", "Select Image")
            images_label = self._t("editor.center.image_filter_images", "Images")
            all_label = self._t("editor.center.image_filter_all_files", "All Files")
            filters = f"{images_label} (*.png *.jpg *.jpeg *.bmp *.gif);;{all_label} (*.*)"
            file_path, _ = QFileDialog.getOpenFileName(self, title, "", filters)
            if file_path:
                self.question_image_path.setText(file_path)
        except Exception:
            pass
    
    def preview_question(self):
        """Preview the current question"""
        # Deprecated: per-question preview removed
        pass
    
    def save_question(self):
        """Save the current question"""
        if not self.question_text.toPlainText().strip():
            # TODO: Show error message
            return
        try:
            if hasattr(self, "auto_points_check") and bool(self.auto_points_check.isChecked()):
                self._distribute_points_across_questions()
        except Exception:
            pass
        
        question_data = self.get_question_data()
        self.current_question = question_data
        self.question_updated.emit(question_data)
        try:
            self.game_config_updated.emit(self.get_game_config_data())
        except Exception:
            pass
        
        # TODO: Show success message
        return
    
    def get_question_data(self) -> dict:
        """Get current question data"""
        question_type = self.get_current_question_type()
        
        data = {
            "type": question_type,
            "question": self.question_text.toPlainText().strip(),
            "explanation": self.explanation_text.toPlainText().strip(),
            "image": self.question_image_path.text().strip(),
            "difficulty": self.difficulty_combo.currentText(),
            "time_limit": self.question_time_spin.value(),
            "points": self.question_points_spin.value(),
            "tags": [tag.strip() for tag in self.question_tags.text().split(",") if tag.strip()]
        }
        
        # Add type-specific data
        if question_type == "multiple_choice":
            options = []
            for i in range(self.options_list.count()):
                item = self.options_list.item(i)
                option_data = item.data(Qt.ItemDataRole.UserRole)
                options.append(option_data)
            data["options"] = options
        
        elif question_type == "true_false":
            try:
                data["correct_answer"] = int(self.true_false_group.checkedId()) == 1
            except Exception:
                data["correct_answer"] = False
        
        elif question_type == "fill_blank":
            answers = self.fill_blank_answers.toPlainText().strip().split("\n")
            data["answers"] = [answer.strip() for answer in answers if answer.strip()]
            data["case_sensitive"] = self.case_sensitive_check.isChecked()
        
        elif question_type == "matching":
            pairs = []
            for i in range(self.matching_pairs_list.count()):
                item = self.matching_pairs_list.item(i)
                pair_data = item.data(Qt.ItemDataRole.UserRole)
                pairs.append(pair_data)
            data["pairs"] = pairs
        
        elif question_type == "short_answer":
            answers = self.short_answer_answers.toPlainText().strip().split("\n")
            data["answers"] = [answer.strip() for answer in answers if answer.strip()]
            data["max_length"] = self.answer_length_spin.value()
        
        return data
    
    def get_current_question_type(self) -> str:
        """Get current question type"""
        checked_button = self.question_type_group.checkedButton()
        if checked_button:
            type_index = self.question_type_group.id(checked_button)
            question_types = ["multiple_choice", "true_false", "fill_blank", "matching", "short_answer"]
            return question_types[type_index] if type_index < len(question_types) else "multiple_choice"
        return "multiple_choice"
    
    def on_game_type_changed(self, game_type: str):
        """Handle game type change"""
        gtl = (game_type or "").strip().lower()
        is_millionaire = False
        try:
            self._force_hide_question_type_if_millionaire()
            gt = str(self.game_type_combo.currentText() if hasattr(self, "game_type_combo") else "").lower().strip()
            is_millionaire = (
                ("triệu phú" in gtl) or ("trieu phu" in gtl) or ("millionaire" in gtl) or ("quiz_millionaire" in gtl) or ("altp" in gtl)
                or ("triệu phú" in gt) or ("trieu phu" in gt) or ("millionaire" in gt) or ("quiz_millionaire" in gt) or ("altp" in gt)
            )
        except Exception:
            is_millionaire = (
                ("triệu phú" in gtl) or ("trieu phu" in gtl) or ("millionaire" in gtl) or ("quiz_millionaire" in gtl) or ("altp" in gtl)
            )
        is_fishing = (
            ("câu cá" in gtl)
            or ("cau ca" in gtl)
            or ("bắt cá" in gtl)
            or ("bat ca" in gtl)
            or ("fishing" in gtl)
        )
        self.quiz_settings_group.setVisible(not is_fishing)
        self.fishing_settings_group.setVisible(is_fishing)

        if is_millionaire:
            try:
                self._restore_widget(self.preview_btn)
                self._restore_widget(self.preview_config_btn)
            except Exception:
                pass
            try:
                # Millionaire không dùng điểm
                self.auto_points_check.setChecked(False)
                self.auto_points_check.setEnabled(False)
                self.total_points_spin.setEnabled(False)
                self.points_spin.setEnabled(False)
            except Exception:
                pass
            # Chỉ cho phép 'Trắc nghiệm' trong Ai là triệu phú
            try:
                for key, btn in (self._question_type_buttons or {}).items():
                    if key == "multiple_choice":
                        btn.setVisible(True)
                        btn.setEnabled(True)
                        btn.setChecked(True)
                    else:
                        btn.setVisible(False)
                        btn.setEnabled(False)
                # Đưa stack về trang 'multiple_choice'
                if hasattr(self, 'options_stacked'):
                    self.options_stacked.setCurrentIndex(0)
                # Ẩn cả nhóm "Loại câu hỏi" để giao diện gọn hơn
                if hasattr(self, 'question_type_group_box') and self.question_type_group_box:
                    self.question_type_group_box.setVisible(False)
                # Buộc ẩn cả khi UI refresh lại
                try:
                    self.question_type_group_box.hide()
                except Exception:
                    pass
            except Exception:
                pass
        else:
            try:
                self._restore_widget(self.preview_btn)
                self._restore_widget(self.preview_config_btn)
            except Exception:
                pass
            try:
                # Khôi phục điều khiển điểm cho game thường & câu cá
                self.auto_points_check.setEnabled(True)
                self.total_points_spin.setEnabled(True)
                self.points_spin.setEnabled(True)
            except Exception:
                pass
            # Hiển thị lại tất cả loại câu hỏi
            try:
                for btn in (self._question_type_buttons or {}).values():
                    btn.setVisible(True)
                    btn.setEnabled(True)
                if hasattr(self, 'question_type_group_box') and self.question_type_group_box:
                    self.question_type_group_box.setVisible(True)
            except Exception:
                pass
    
    def preview_game_config(self):
        """Preview game configuration"""
        self.preview_requested.emit()
    
    def save_game_config(self):
        """Save game configuration"""
        config = {
            "game_type": self.game_type_combo.currentText(),
            "time_limit": self.time_limit_spin.value(),
            "question_time": self.time_limit_spin.value(),
            # Lưu cả chế độ tự chia điểm và tổng điểm (mặc định 100)
            "auto_points_enabled": self.auto_points_check.isChecked(),
            "total_points": self.total_points_spin.value(),
            "points_per_question": self.points_spin.value(),
            "show_correct_answer": self.show_correct_check.isChecked(),
            "randomize_questions": self.randomize_check.isChecked(),
            "quiz_settings": {
                "num_options": self.num_options_spin.value(),
                "allow_multiple_answers": self.multiple_answers_check.isChecked(),
                "show_progress_bar": self.show_progress_check.isChecked()
            },
            "fishing_settings": {
                "fish_speed": self.fish_speed_spin.value(),
                "fish_count": self.fish_count_spin.value(),
                "fish_size": self.fish_size_combo.currentText()
            },
            "cute_effects": self.cute_effects_check.isChecked()
        }
        # Emit updated config; screen will normalize and set top-level game_type
        
        self.game_config_updated.emit(config)
        print("Game configuration saved")

    def get_game_config_data(self) -> dict:
        try:
            return {
                "game_type": self.game_type_combo.currentText(),
                "time_limit": self.time_limit_spin.value(),
                "question_time": self.time_limit_spin.value(),
                "auto_points_enabled": self.auto_points_check.isChecked(),
                "total_points": self.total_points_spin.value(),
                "points_per_question": self.points_spin.value(),
                "show_correct_answer": self.show_correct_check.isChecked(),
                "randomize_questions": self.randomize_check.isChecked(),
                "quiz_settings": {
                    "num_options": self.num_options_spin.value(),
                    "allow_multiple_answers": self.multiple_answers_check.isChecked(),
                    "show_progress_bar": self.show_progress_check.isChecked(),
                },
                "fishing_settings": {
                    "fish_speed": self.fish_speed_spin.value(),
                    "fish_count": self.fish_count_spin.value(),
                    "fish_size": self.fish_size_combo.currentText(),
                },
                "cute_effects": self.cute_effects_check.isChecked(),
            }
        except Exception:
            return {}
    
    def load_project(self, project_data: dict):
        """Load project data"""
        self.current_project = project_data
        
        # Load game config if available
        game_config = project_data.get("game_config", {})
        if game_config:
            self.load_game_config(game_config)
        else:
            try:
                gt = str(project_data.get("game_type", "")).strip()
                if gt:
                    self.on_game_type_changed(gt)
            except Exception:
                pass
        try:
            self._force_hide_question_type_if_millionaire()
        except Exception:
            pass
        try:
            self.apply_project_permissions(project_data)
        except Exception:
            pass

    def apply_project_permissions(self, project_data: dict | None = None):
        proj = project_data if isinstance(project_data, dict) else (getattr(self, "current_project", None) or {})
        try:
            cfg = (proj or {}).get("game_config", {}) or {}
        except Exception:
            cfg = {}
        allow_delete = True
        try:
            allow_delete = bool(cfg.get("allow_delete_question", True))
        except Exception:
            allow_delete = True
        try:
            if hasattr(self, "delete_question_btn") and self.delete_question_btn:
                self.delete_question_btn.setVisible(allow_delete)
                self.delete_question_btn.setEnabled(allow_delete)
        except Exception:
            pass
    
    def set_question(self, question_data: dict | None, index: int = -1):
        """Compatibility method used by EditorScreen to set current question.
        When question_data is None, clear the editor UI; otherwise load the question."""
        try:
            self.current_index = index
        except Exception:
            pass
        try:
            if question_data:
                self.load_question(question_data)
            else:
                self.current_question = None
                self.current_mode = "question"
                try:
                    if self._empty_state_index >= 0:
                        self.stacked_widget.setCurrentIndex(self._empty_state_index)
                    else:
                        self.stacked_widget.setCurrentIndex(0)
                except Exception:
                    pass
                try:
                    self.question_text.setPlainText("")
                except Exception:
                    pass
                try:
                    self.explanation_text.setPlainText("")
                except Exception:
                    pass
                try:
                    self.question_image_path.setText("")
                except Exception:
                    pass
                try:
                    if hasattr(self, 'options_list') and self.options_list:
                        self.options_list.clear()
                        self._update_compact_list_height(self.options_list, min_rows=4, max_rows=4)
                except Exception:
                    pass
                try:
                    if hasattr(self, 'fill_blank_answers') and self.fill_blank_answers:
                        self.fill_blank_answers.setPlainText("")
                    if hasattr(self, 'case_sensitive_check') and self.case_sensitive_check:
                        self.case_sensitive_check.setChecked(False)
                except Exception:
                    pass
                try:
                    if hasattr(self, 'matching_pairs_list') and self.matching_pairs_list:
                        self.matching_pairs_list.clear()
                        self._update_compact_list_height(self.matching_pairs_list, min_rows=3, max_rows=4)
                except Exception:
                    pass
                try:
                    if hasattr(self, 'short_answer_answers') and self.short_answer_answers:
                        self.short_answer_answers.setPlainText("")
                except Exception:
                    pass
        except Exception:
            # Fail-safe: do not crash if UI elements are not yet ready
            pass
        try:
            self._force_hide_question_type_if_millionaire()
        except Exception:
            pass

    def _force_hide_question_type_if_millionaire(self):
        try:
            def _has_m_assets(obj) -> bool:
                try:
                    if obj is None:
                        return False
                    if isinstance(obj, str):
                        s = obj.lower()
                        return (
                            ("assets/millionaire/" in s)
                            or ("millionaire/sounds" in s)
                            or ("0_to_1000" in s)
                            or ("correct answer.mp3" in s)
                            or ("wrong answer.mp3" in s)
                            or ("altp_vn" in s)
                        )
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if _has_m_assets(k) or _has_m_assets(v):
                                return True
                        return False
                    if isinstance(obj, (list, tuple, set)):
                        for it in obj:
                            if _has_m_assets(it):
                                return True
                        return False
                except Exception:
                    return False
                return False

            gt_text = str(self.game_type_combo.currentText() if hasattr(self, 'game_type_combo') else "")
            gt = gt_text.lower().strip()
            proj = getattr(self, "current_project", None) or {}
            cfg = {}
            try:
                if isinstance(proj.get("game_config"), dict):
                    cfg = proj.get("game_config") or {}
            except Exception:
                cfg = {}
            gt2 = str(proj.get("game_type") or cfg.get("game_type") or "").lower().strip()
            fv = str(proj.get("force_variant") or cfg.get("force_variant") or "").lower().strip()
            mk = str(proj.get("variant_marker") or cfg.get("variant_marker") or "").lower().strip()

            is_m = (
                ("triệu phú" in gt) or ("trieu phu" in gt) or ("millionaire" in gt) or ("quiz_millionaire" in gt) or ("altp" in gt)
                or ("triệu phú" in gt2) or ("trieu phu" in gt2) or ("millionaire" in gt2) or ("quiz_millionaire" in gt2) or ("altp" in gt2)
                or (fv in ("millionaire", "quiz_millionaire", "wwbm", "altp_vn"))
                or ("millionaire" in mk) or ("altp" in mk)
                or _has_m_assets(cfg)
            )
            if is_m and hasattr(self, 'question_type_group_box') and self.question_type_group_box:
                try:
                    self.question_type_group_box.hide()
                except Exception:
                    pass
                try:
                    self.question_type_group_box.setEnabled(False)
                    self.question_type_group_box.setMaximumHeight(0)
                except Exception:
                    pass
                for key, btn in (getattr(self, "_question_type_buttons", {}) or {}).items():
                    if key != "multiple_choice":
                        btn.setVisible(False)
                        btn.setEnabled(False)
        except Exception:
            pass
    
    def load_question(self, question_data: dict):
        """Load question for editing"""
        self.current_question = question_data
        try:
            project_question = self._get_current_project_question()
            if isinstance(project_question, dict):
                question_data = project_question
                self.current_question = project_question
        except Exception:
            pass
        self.current_mode = "question"
        self.stacked_widget.setCurrentIndex(0)
        
        # Set question type
        question_type = question_data.get("type", "multiple_choice")
        type_mapping = {
            "multiple_choice": 0,
            "true_false": 1,
            "fill_blank": 2,
            "matching": 3,
            "short_answer": 4
        }
        type_index = type_mapping.get(question_type, 0)
        
        # Check the appropriate radio button
        buttons = self.question_type_group.buttons()
        if type_index < len(buttons):
            buttons[type_index].setChecked(True)
            self.on_question_type_changed(buttons[type_index])
        
        # Set question content
        self.question_text.setPlainText(question_data.get("question", ""))
        self.explanation_text.setPlainText(question_data.get("explanation", ""))
        self.question_image_path.setText(question_data.get("image", ""))
        
        # Set question settings
        difficulty = question_data.get("difficulty", "Trung bình")
        try:
            index = self.difficulty_combo.findText(difficulty)
        except Exception:
            index = -1
        if index >= 0:
            try:
                self.difficulty_combo.setCurrentIndex(index)
            except Exception:
                pass
        
        try:
            self._is_adjusting_points = True
            self.question_time_spin.setValue(question_data.get("time_limit", 30))
            self.question_points_spin.setValue(question_data.get("points", 10))
        finally:
            self._is_adjusting_points = False
        
        tags = ", ".join(question_data.get("tags", []))
        self.question_tags.setText(tags)
        
        # Set type-specific content
        if question_type == "multiple_choice":
            options = question_data.get("options", [])
            if isinstance(options, dict):
                try:
                    ordered = []
                    for k in ["A", "B", "C", "D", "E", "F"]:
                        if k in options:
                            ordered.append(options.get(k))
                    if not ordered:
                        ordered = list(options.values())
                    options = ordered
                except Exception:
                    options = []
            if isinstance(options, str):
                try:
                    options = [s.strip() for s in options.splitlines() if s.strip()]
                except Exception:
                    options = []
            if not isinstance(options, list):
                options = []
            self.options_list.clear()
            if options and isinstance(options[0], dict):
                for option in options:
                    self.add_multiple_choice_option(
                        option.get("text", ""),
                        option.get("correct", False)
                    )
            else:
                ca = question_data.get("correct_answer", 0)
                correct_idx = 0
                if isinstance(ca, int):
                    correct_idx = ca
                else:
                    s = str(ca).strip().upper()
                    if len(s) == 1 and s in "ABCDEF":
                        correct_idx = ord(s) - ord('A')
                    elif s.isdigit():
                        try:
                            correct_idx = int(s)
                        except Exception:
                            correct_idx = 0
                for i, opt in enumerate(options):
                    self.add_multiple_choice_option(str(opt), i == correct_idx)
            self._update_compact_list_height(self.options_list, min_rows=4, max_rows=4)
        
        elif question_type == "true_false":
            correct_answer = question_data.get("correct_answer", False)
            try:
                self.true_false_group.button(1 if bool(correct_answer) else 0).setChecked(True)
            except Exception:
                pass
        
        elif question_type == "fill_blank":
            answers = question_data.get("answers", []) or question_data.get("correct_answers", [])
            self.fill_blank_answers.setPlainText("\n".join(answers))
            self.case_sensitive_check.setChecked(question_data.get("case_sensitive", False))
        
        elif question_type == "matching":
            pairs = question_data.get("pairs", [])
            self.matching_pairs_list.clear()
            for pair in pairs:
                self.add_matching_pair(
                    pair.get("left", ""),
                    pair.get("right", "")
                )
            self._update_compact_list_height(self.matching_pairs_list, min_rows=3, max_rows=4)
        
        elif question_type == "short_answer":
            answers = question_data.get("answers", [])
            self.short_answer_answers.setPlainText("\n".join(answers))
            self.answer_length_spin.setValue(question_data.get("max_length", 100))
    
    def load_game_config(self, game_config: dict):
        """Load game configuration"""
        gt_raw = game_config.get("game_type", "")
        gt_lower = str(gt_raw or "").strip().lower()
        fishing_markers = ("fishing", "fish", "câu cá", "cau ca", "bắt cá", "bat ca", "pesca", "pêche", "peche", "fischen", "angeln")
        millionaire_markers = ("millionaire", "triệu phú", "trieu phu", "altp", "millionnaire", "millonario", "millionär", "millionar")
        if any(token in gt_lower for token in fishing_markers):
            target_type = self._t("editor.left.game_type_fishing", "Fishing Game")
        elif any(token in gt_lower for token in millionaire_markers):
            target_type = self._t("editor.left.game_type_millionaire", "Who Wants to Be a Millionaire")
        else:
            target_type = self._t("editor.left.game_type_quiz", "Quiz Classic")
        try:
            index = self.game_type_combo.findText(target_type)
        except Exception:
            index = -1
        if index >= 0:
            try:
                self.game_type_combo.setCurrentIndex(index)
            except Exception:
                pass
            self.on_game_type_changed(target_type)
        else:
            self.on_game_type_changed(target_type)
        try:
            self._force_hide_question_type_if_millionaire()
        except Exception:
            pass
        
        # Set general settings
        self.time_limit_spin.setValue(int(game_config.get("question_time", game_config.get("time_limit", 30)) or 30))
        try:
            ap = bool(game_config.get("auto_points_enabled", True))
        except Exception:
            ap = True
        self.auto_points_check.setChecked(ap)
        self.total_points_spin.setValue(int(game_config.get("total_points", 100)))
        self.points_spin.setValue(int(game_config.get("points_per_question", 10)))
        try:
            # Sync mirror toggle in question settings if present
            if hasattr(self, 'question_auto_points_check'):
                self.question_auto_points_check.setChecked(ap)
                # Apply enable/disable to question points spin
                self.on_auto_points_toggled(ap)
        except Exception:
            pass
        self.show_correct_check.setChecked(game_config.get("show_correct_answer", True))
        self.randomize_check.setChecked(game_config.get("randomize_questions", True))
        
        # Set quiz settings
        quiz_settings = game_config.get("quiz_settings", {})
        self.num_options_spin.setValue(quiz_settings.get("num_options", 4))
        self.multiple_answers_check.setChecked(quiz_settings.get("allow_multiple_answers", False))
        self.show_progress_check.setChecked(quiz_settings.get("show_progress_bar", True))
        
        # Set fishing settings
        fishing_settings = game_config.get("fishing_settings", {})
        self.fish_speed_spin.setValue(fishing_settings.get("fish_speed", 5))
        self.fish_count_spin.setValue(fishing_settings.get("fish_count", 10))
        
        fish_size = fishing_settings.get("fish_size", "Vừa")
        size_index = self.fish_size_combo.findText(fish_size)
        if size_index >= 0:
            self.fish_size_combo.setCurrentIndex(size_index)
        
        self.cute_effects_check.setChecked(fishing_settings.get("cute_effects", False))
        
        # Luôn hiển thị nút xem trước bình thường
        try:
            if hasattr(self, "preview_btn"):
                self._restore_widget(self.preview_btn)
            if hasattr(self, "preview_config_btn"):
                self._restore_widget(self.preview_config_btn)
        except Exception:
            pass
    
    def show_game_config(self):
        """Show game configuration editor"""
        self.current_mode = "game_config"
        self.stacked_widget.setCurrentIndex(1)

    @Slot()
    def _do_hide_preview_buttons(self):
        # Giữ lại để tương thích, nhưng không thay đổi trạng thái nút nữa
        pass
 
    def hide_preview_buttons(self):
        """Hide preview buttons for millionaire game"""
        try:
            from PySide6.QtCore import Qt, QMetaObject, Slot
            # Ensure we have a dedicated slot method name for queued invoke
            # Invoke on UI thread by name (requires @Slot above)
            try:
                QMetaObject.invokeMethod(self, "_do_hide_preview_buttons", Qt.QueuedConnection)
            except Exception:
                try:
                    # Fallback direct call (already on UI thread)
                    self._do_hide_preview_buttons()
                except Exception:
                    pass
        except Exception:
            # Fallback direct minimize
            if hasattr(self, 'preview_btn'):
                self._minimize_widget(self.preview_btn)
            if hasattr(self, 'preview_config_btn'):
                self._minimize_widget(self.preview_config_btn)

