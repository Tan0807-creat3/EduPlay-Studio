from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QListWidget, 
                                QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, 
                                QHBoxLayout, QGroupBox, QComboBox, QSpinBox, 
                                QCheckBox, QTextEdit, QSplitter, QListWidgetItem,
                                QLineEdit, QScrollArea, QFrame, QFileDialog, QMessageBox,
                                QStyle)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
import os

from eduplay.ui.widgets.custom_dropdown import FlatDropdown
from eduplay.ui.icon_factory import build_app_action_icon
from eduplay.core.asset_loader import materialize_asset_file
from eduplay.core.i18n import I18n


class EditorLeftPanel(QWidget):
    question_selected = Signal(dict)
    game_config_changed = Signal(dict)
    asset_selected = Signal(str)
    import_questions_requested = Signal()  # New signal for import requests
    question_settings_applied = Signal(dict)
    delete_question_requested = Signal(dict)
    preview_question_requested = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.questions_tab = self.create_questions_tab()
        self.media_tab = self.create_media_tab()
        self.settings_tab = self.create_settings_tab()
        
        self.tab_widget.addTab(self.questions_tab, I18n.t("editor.left.tab_questions"))
        self.tab_widget.addTab(self.settings_tab, I18n.t("editor.left.tab_settings"))
        
        layout.addWidget(self.tab_widget)
        try:
            from eduplay.core.settings_manager import SettingsManager
            self.apply_theme(SettingsManager().get_theme() or "dark")
        except Exception:
            self.apply_theme("dark")
        
    def create_questions_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Button layout for Add and Import
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Add Question button
        self.add_btn = QPushButton(I18n.t('editor.left.add_question_btn'))
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #12B76A;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0F9C5A;
            }
        """)
        try:
            self.add_btn.setIcon(build_app_action_icon("create", self.style(), size=16))
            self.add_btn.setIconSize(QSize(16, 16))
        except Exception:
            pass
        self.add_btn.clicked.connect(self.add_question)
        self.add_btn.setMinimumHeight(36)
        button_layout.addWidget(self.add_btn)
        
        # Import Questions button
        self.import_btn = QPushButton(I18n.t('editor.left.import_btn'))
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #7F56D9;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6B46C1;
            }
        """)
        try:
            self.import_btn.setIcon(build_app_action_icon("import", self.style(), size=16))
            self.import_btn.setIconSize(QSize(16, 16))
        except Exception:
            pass
        self.import_btn.clicked.connect(self.import_questions)
        self.import_btn.setMinimumHeight(36)
        button_layout.addWidget(self.import_btn)

        layout.addLayout(button_layout)

        self.questions_empty_state = self._create_questions_empty_state()
        layout.addWidget(self.questions_empty_state)

        # Questions list
        self.questions_list = QListWidget()
        self.questions_list.itemClicked.connect(self.on_question_selected)
        self.questions_list.currentItemChanged.connect(self._on_current_question_changed)
        layout.addWidget(self.questions_list)

        self.questions_list.hide()
        
        return tab

    def _create_questions_empty_state(self) -> QWidget:
        card = QFrame()
        card.setObjectName("editorQuestionsEmptyCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        try:
            icon_path = materialize_asset_file("eduplay/resources/icons/question_framework.png.png")
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                icon_label.setPixmap(
                    pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
        except Exception:
            pass
        layout.addWidget(icon_label)

        title_label = QLabel("No questions yet")
        title_label.setObjectName("editorQuestionsEmptyTitle")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        subtitle_label = QLabel('Click "Add Question" or "Import"\nto get started!')
        subtitle_label.setObjectName("editorQuestionsEmptySubtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle_label)

        return card

    def _question_action_button_stylesheet(self, bg_color: str, hover_color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover:enabled {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #D0D5DD;
                color: #FFFFFF;
            }}
        """

    def _build_selected_question_payload(self):
        item = self.questions_list.currentItem() if hasattr(self, "questions_list") else None
        if item is None:
            return None
        question_data = item.data(Qt.UserRole)
        index = -1
        try:
            index = int(self.questions_list.row(item))
        except Exception:
            index = -1
        payload = {
            "question": question_data,
            "index": index,
        }
        if isinstance(question_data, dict):
            payload["question_id"] = question_data.get("id")
        return payload

    def _update_question_action_buttons(self):
        has_selection = self._build_selected_question_payload() is not None
        for attr_name in ("delete_selected_btn", "preview_selected_btn"):
            btn = getattr(self, attr_name, None)
            if btn is not None:
                btn.setEnabled(has_selection)

    def _on_current_question_changed(self, current, _previous):
        self._update_question_action_buttons()
        if current is not None:
            self.on_question_selected(current)
        
    def create_game_config_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # Wrap in scroll area so content never overflows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        from PySide6.QtWidgets import QSizePolicy
        inner.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        scroll.setWidget(inner)
        tab_layout.addWidget(scroll)
        
        # Game Type
        game_type_group = QGroupBox(I18n.t("editor.left.game_type_label"))
        game_type_group.setStyleSheet("""
            QGroupBox {
                color: #E0E0E0;
                border: 1px solid #3A3A40;
                border-radius: 4px;
                margin-top: 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        game_type_layout = QVBoxLayout(game_type_group)
        
        self.game_type_combo = FlatDropdown()
        # Add items with (Display Text, User Data)
        self.game_type_combo.addItem(I18n.t("editor.left.game_type_quiz"), "quiz_classic")
        self.game_type_combo.addItem(I18n.t("editor.left.game_type_millionaire"), "quiz_millionaire")
        self.game_type_combo.addItem(I18n.t("editor.left.game_type_fishing"), "fishing")
        
        self.game_type_combo.currentTextChanged.connect(self.on_game_config_changed)
        game_type_layout.addWidget(self.game_type_combo)
        layout.addWidget(game_type_group)
        
        # Difficulty Settings
        difficulty_group = QGroupBox(I18n.t("editor.left.difficulty_label"))
        difficulty_group.setStyleSheet(game_type_group.styleSheet())
        difficulty_layout = QVBoxLayout(difficulty_group)
        
        self.difficulty_combo = FlatDropdown()
        self.difficulty_combo.button.setStyleSheet("""
            QToolButton {
                background-color: #1E1E24;
                color: #E0E0E0;
                border: 1px solid #3A3A40;
                border-radius: 4px;
                padding: 8px 12px;
                text-align: left;
            }
        """)
        self.difficulty_combo.popup.setStyleSheet("""
            QFrame#FlatDropdownPopup {
                background-color: #1E1E24;
                border: 1px solid #3A3A40;
                border-radius: 4px;
            }
            QListView {
                background-color: transparent;
                color: #E0E0E0;
                border: none;
            }
            QListView::item {
                padding: 8px 12px;
            }
            QListView::item:selected {
                background-color: #7F56D9;
                color: #FFFFFF;
            }
            QListView::item:hover:!selected {
                background-color: #2A2A30;
            }
        """)
        self.difficulty_combo.addItem(I18n.t("editor.left.difficulty_easy"), "Easy")
        self.difficulty_combo.addItem(I18n.t("editor.left.difficulty_medium"), "Medium")
        self.difficulty_combo.addItem(I18n.t("editor.left.difficulty_hard"), "Hard")
        
        self.difficulty_combo.currentTextChanged.connect(self.on_game_config_changed)
        difficulty_layout.addWidget(self.difficulty_combo)
        layout.addWidget(difficulty_group)
        
        # Time Settings
        time_group = QGroupBox(I18n.t("editor.left.time_settings_label"))
        time_group.setStyleSheet(game_type_group.styleSheet())
        time_layout = QVBoxLayout(time_group)
        
        time_layout.addWidget(QLabel(I18n.t("editor.left.question_time_label")))
        self.question_time_spin = QSpinBox()
        self.question_time_spin.setRange(5, 300)
        self.question_time_spin.setValue(30)
        self.question_time_spin.setStyleSheet("""
            QSpinBox {
                background-color: #1E1E24;
                color: #E0E0E0;
                border: 1px solid #3A3A40;
                border-radius: 4px;
                padding: 6px 30px 6px 6px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #161925;
                border-left: 1px solid #3A3A40;
                width: 20px;
                subcontrol-origin: border;
            }
            QSpinBox::up-button {
                subcontrol-position: top right;
                border-top-right-radius: 3px;
            }
            QSpinBox::down-button {
                subcontrol-position: bottom right;
                border-bottom-right-radius: 3px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #2A2A30; }
        """)
        self.question_time_spin.valueChanged.connect(self.on_game_config_changed)
        time_layout.addWidget(self.question_time_spin)
        
        self.time_limit_check = QCheckBox(I18n.t("editor.left.enable_time_limit"))
        self.time_limit_check.setChecked(True)
        self.time_limit_check.setStyleSheet("""
            QCheckBox {
                color: #E0E0E0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #1E1E24;
                border: 1px solid #3A3A40;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #7F56D9;
            }
        """)
        self.time_limit_check.toggled.connect(self.on_game_config_changed)
        time_layout.addWidget(self.time_limit_check)
        layout.addWidget(time_group)
        
        # Scoring
        scoring_group = QGroupBox(I18n.t("editor.left.scoring_label"))
        scoring_group.setStyleSheet(game_type_group.styleSheet())
        scoring_layout = QVBoxLayout(scoring_group)
        
        # Basic settings (bottom-left)
        basic_group = QGroupBox(I18n.t("editor.left.basic_settings_label"))
        basic_group.setStyleSheet(game_type_group.styleSheet())
        basic_layout = QVBoxLayout(basic_group)
        self.show_explanations_check = QCheckBox(I18n.t("editor.left.show_explanations"))
        self.show_explanations_check.setChecked(True)
        self.show_explanations_check.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: transparent;
                border: 1px solid #3A3A40;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #7F56D9;
            }
        """)
        self.show_explanations_check.toggled.connect(self.on_game_config_changed)
        basic_layout.addWidget(self.show_explanations_check)
        self.randomize_questions_check = QCheckBox(I18n.t("editor.left.randomize_questions"))
        self.randomize_questions_check.setChecked(True)
        self.randomize_questions_check.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: transparent;
                border: 1px solid #3A3A40;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #7F56D9;
            }
        """)
        self.randomize_questions_check.toggled.connect(self.on_game_config_changed)
        basic_layout.addWidget(self.randomize_questions_check)
        layout.addWidget(basic_group)
    
    def apply_theme(self, theme: str):
        t = 'dark' if str(theme).lower() == 'dark' else 'light'
        if t == 'dark':
            frame_border = "#3A3A40"
            frame_bg = "#25252B"
            tab_bg = "#1E1E24"
            hover_bg = "#2A2A30"
            text_color = "#E0E0E0"
            list_bg = "#1E1E24"
            list_fg = "#E0E0E0"
            list_border = "#3A3A40"
            list_divider = "#2A2A30"
            list_hover = "#2A2A30"
            group_border = "#3A3A40"
            group_bg = "#1E1E24"
            spin_bg = "#1E1E24"
            spin_fg = "#E0E0E0"
            spin_border = "#3A3A40"
            cb_fg = "#E0E0E0"
            cb_bg = "#1E1E24"
            cb_border = "#3A3A40"
            input_bg = "#1E1E24"
            input_fg = "#E5E7EB"
            input_border = "#3A3A40"
            btn_secondary_bg = "#2A2A30"
            btn_secondary_fg = "#E5E7EB"
            btn_secondary_hover = "#3A3A40"
        else:
            frame_border = "#CBD5E1"
            frame_bg = "#F8FAFC"
            tab_bg = "#FFFFFF"
            hover_bg = "#F1F5F9"
            text_color = "#0F172A"
            list_bg = "#FFFFFF"
            list_fg = "#0F172A"
            list_border = "#E2E8F0"
            list_divider = "#E2E8F0"
            list_hover = "#F1F5F9"
            group_border = "#E2E8F0"
            group_bg = "#FFFFFF"
            spin_bg = "#FFFFFF"
            spin_fg = "#1A1A1A"
            spin_border = "#CBD5E1"
            cb_fg = "#1A1A1A"
            cb_bg = "#FFFFFF"
            cb_border = "#CBD5E1"
            input_bg = "#FFFFFF"
            input_fg = "#111827"
            input_border = "#CBD5E1"
            btn_secondary_bg = "#EEF2FF"
            btn_secondary_fg = "#1E3A8A"
            btn_secondary_hover = "#E0EAFF"
        empty_card_bg = "#FFFFFF" if t == "light" else "#1E1E24"
        empty_card_border = "#E4E7EC" if t == "light" else "#3A3A40"
        empty_title = "#101828" if t == "light" else "#F8FAFC"
        empty_subtitle = "#667085" if t == "light" else "#98A2B3"
        try:
            if hasattr(self, 'tab_widget') and self.tab_widget:
                self.tab_widget.setStyleSheet(
                    f"""
                    QTabWidget::pane {{
                        border: none;
                        background-color: transparent;
                    }}
                    QTabBar::tab {{
                        background-color: {tab_bg};
                        color: {text_color};
                        padding: 8px 16px;
                        border: 1px solid {frame_border};
                        border-radius: 8px;
                        margin-right: 4px;
                        min-height: 34px;
                        max-height: 34px;
                        font-weight: 600;
                    }}
                    QTabBar::tab:selected {{
                        background-color: #7F56D9;
                        color: white;
                    }}
                    QTabBar::tab:hover:!selected {{
                        background-color: {hover_bg};
                        color: {text_color};
                    }}
                """
                )
        except Exception:
            pass
        try:
            if hasattr(self, 'questions_list') and self.questions_list:
                self.questions_list.setStyleSheet(
                    f"""
                    QListWidget {{
                        background-color: {list_bg};
                        border: 1px solid {list_border};
                        border-radius: 14px;
                        color: {list_fg};
                        padding: 8px 0px;
                    }}
                    QListWidget::item {{
                        padding: 12px 14px;
                        border-bottom: 1px solid {list_divider};
                    }}
                    QListWidget::item:selected {{
                        background-color: #7F56D9;
                        color: white;
                    }}
                    QListWidget::item:hover {{
                        background-color: {list_hover};
                        color: {list_fg};
                    }}
                """
                )
        except Exception:
            pass
        try:
            if hasattr(self, "questions_empty_state") and self.questions_empty_state:
                self.questions_empty_state.setStyleSheet(
                    f"""
                    QFrame#editorQuestionsEmptyCard {{
                        background-color: {empty_card_bg};
                        border: 1px solid {empty_card_border};
                        border-radius: 16px;
                    }}
                    QLabel#editorQuestionsEmptyTitle {{
                        color: {empty_title};
                        font-size: 18px;
                        font-weight: 800;
                        background: transparent;
                    }}
                    QLabel#editorQuestionsEmptySubtitle {{
                        color: {empty_subtitle};
                        font-size: 13px;
                        font-weight: 500;
                        background: transparent;
                    }}
                    """
                )
            if hasattr(self, "add_btn") and self.add_btn:
                self.add_btn.setCursor(Qt.PointingHandCursor)
            if hasattr(self, "import_btn") and self.import_btn:
                self.import_btn.setCursor(Qt.PointingHandCursor)
        except Exception:
            pass
        try:
            self.setStyleSheet(
                f"""
                QGroupBox {{
                    color: {text_color};
                    border: 1px solid {group_border};
                    border-radius: 4px;
                    background-color: {group_bg};
                }}
                QSpinBox {{
                    background-color: {spin_bg};
                    color: {spin_fg};
                    border: 1px solid {spin_border};
                    border-radius: 4px;
                    padding: 6px;
                }}
                QSpinBox::up-button, QSpinBox::down-button {{
                    background-color: {group_bg};
                    border-left: 1px solid {spin_border};
                    width: 20px;
                    subcontrol-origin: border;
                }}
                QSpinBox::up-button {{
                    subcontrol-position: top right;
                    border-top-right-radius: 3px;
                }}
                QSpinBox::down-button {{
                    subcontrol-position: bottom right;
                    border-bottom-right-radius: 3px;
                }}
                QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                    background-color: {list_hover};
                }}
                QCheckBox {{
                    color: {cb_fg};
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
            """
            )
        except Exception:
            pass
        try:
            if hasattr(self, "settings_default_time_spin"):
                self.settings_default_time_spin.setStyleSheet(
                    f"""
                    QSpinBox {{
                        background-color: {spin_bg};
                        color: {spin_fg};
                        border: 1px solid {spin_border};
                        border-radius: 6px;
                        padding: 6px 8px;
                    }}
                    QSpinBox::up-button, QSpinBox::down-button {{
                        background-color: {group_bg};
                        border-left: 1px solid {spin_border};
                        width: 20px;
                        subcontrol-origin: border;
                    }}
                    QSpinBox::up-button {{
                        subcontrol-position: top right;
                        border-top-right-radius: 5px;
                    }}
                    QSpinBox::down-button {{
                        subcontrol-position: bottom right;
                        border-bottom-right-radius: 5px;
                    }}
                    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                        background-color: {list_hover};
                    }}
                    """
                )
            if hasattr(self, "settings_music_mode_combo"):
                self.settings_music_mode_combo.setStyleSheet(
                    f"""
                    QComboBox {{
                        background-color: {input_bg};
                        color: {input_fg};
                        border: 1px solid {input_border};
                        border-radius: 6px;
                        padding: 6px 8px;
                    }}
                    QComboBox::drop-down {{
                        border: none;
                        width: 20px;
                    }}
                    """
                )
            if hasattr(self, "settings_export_mode_combo"):
                self.settings_export_mode_combo.setStyleSheet(
                    f"""
                    QComboBox {{
                        background-color: {input_bg};
                        color: {input_fg};
                        border: 1px solid {input_border};
                        border-radius: 6px;
                        padding: 6px 8px;
                    }}
                    QComboBox::drop-down {{
                        border: none;
                        width: 20px;
                    }}
                    """
                )
            if hasattr(self, "settings_custom_music_edit"):
                self.settings_custom_music_edit.setStyleSheet(
                    f"""
                    QLineEdit {{
                        background-color: {input_bg};
                        color: {input_fg};
                        border: 1px solid {input_border};
                        border-radius: 6px;
                        padding: 6px 8px;
                    }}
                    """
                )
            if hasattr(self, "settings_custom_music_browse_btn"):
                self.settings_custom_music_browse_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {btn_secondary_bg};
                        color: {btn_secondary_fg};
                        border: 1px solid {input_border};
                        padding: 6px 12px;
                        border-radius: 6px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: {btn_secondary_hover};
                    }}
                    """
                )
            if hasattr(self, "apply_settings_btn"):
                self.apply_settings_btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #2563EB;
                        color: #FFFFFF;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background-color: #1D4ED8;
                        color: #FFFFFF;
                    }
                    """
                )
            if hasattr(self, "settings_tab"):
                self.settings_tab.setStyleSheet(
                    f"""
                    QLabel {{
                        background-color: transparent;
                        color: {text_color};
                    }}
                    QGroupBox::title {{
                        color: {text_color};
                    }}
                    """
                )
        except Exception:
            pass
        
    def create_media_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or "dark"
        except Exception:
            theme = "dark"
        if theme == "dark":
            bg = "#1E1E24"; fg = "#E0E0E0"; border = "#3A3A40"; hover = "#2A2A30"; primary = "#7F56D9"; primary_hover = "#6A48C0"
            group_fg = "#E0E0E0"
        else:
            bg = "#FFFFFF"; fg = "#1A1A1A"; border = "#D0D5DD"; hover = "#F5F6FA"; primary = "#2563EB"; primary_hover = "#1D4ED8"
            group_fg = "#0F1728"
        
        # Search bar
        search_layout = QHBoxLayout()
        self.media_search = QLineEdit()
        self.media_search.setPlaceholderText(I18n.t("editor.left.search_placeholder"))
        self.media_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 8px;
            }}
            QLineEdit:focus {{
                border-color: {primary};
            }}
        """)
        self.media_search.textChanged.connect(self.search_assets)
        search_layout.addWidget(self.media_search)
        
        search_btn = QPushButton(I18n.t("editor.left.search_btn"))
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {primary};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {primary_hover};
            }}
        """)
        search_btn.clicked.connect(self.search_assets)
        search_layout.addWidget(search_btn)
        layout.addLayout(search_layout)
        
        # Asset categories
        categories_group = QGroupBox(I18n.t("editor.left.media_categories_title"))
        categories_group.setStyleSheet(f"""
            QGroupBox {{
                color: {group_fg};
                border: 1px solid {border};
                border-radius: 4px;
                margin-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
        """)
        categories_layout = QVBoxLayout(categories_group)
        
        self.categories_tree = QTreeWidget()
        self.categories_tree.setHeaderLabel(I18n.t("editor.left.asset_categories"))
        self.categories_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
                color: {fg};
            }}
            QTreeWidget::item {{
                padding: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {primary};
                color: white;
            }}
            QTreeWidget::item:hover {{
                background-color: {hover};
            }}
        """)
        self.categories_tree.itemClicked.connect(self.on_category_selected)
        categories_layout.addWidget(self.categories_tree)
        layout.addWidget(categories_group)
        
        # Assets list
        assets_group = QGroupBox(I18n.t("editor.left.assets_group"))
        assets_group.setStyleSheet(categories_group.styleSheet())
        assets_layout = QVBoxLayout(assets_group)
        
        self.assets_list = QListWidget()
        self.assets_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
                color: {fg};
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {hover};
            }}
            QListWidget::item:selected {{
                background-color: {primary};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {hover};
            }}
        """)
        self.assets_list.itemDoubleClicked.connect(self.on_asset_selected)
        assets_layout.addWidget(self.assets_list)
        layout.addWidget(assets_group)
        
        return tab
        
    def set_project(self, project):
        """Load project data into the panel"""
        self.current_project = project
        self.load_questions()
        self.load_game_config()
        self.load_assets()
        self.load_settings()

    def load_settings(self):
        try:
            cfg = (self.current_project or {}).get("game_config", {}) or {}
            self.settings_default_time_spin.setValue(int(cfg.get("question_time", 30) or 30))
            mode = str(cfg.get("background_music_mode", "builtin_1") or "builtin_1")
            idx = self.settings_music_mode_combo.findData(mode)
            if idx >= 0:
                self.settings_music_mode_combo.setCurrentIndex(idx)
            bgm = str(cfg.get("background_music", "") or "")
            if bgm.startswith("media/"):
                self.settings_custom_music_edit.setText(bgm)
            try:
                if hasattr(self, "settings_randomize_questions_check") and self.settings_randomize_questions_check:
                    self.settings_randomize_questions_check.setChecked(bool(cfg.get("randomize_questions", True)))
            except Exception:
                pass
            try:
                if hasattr(self, "settings_auto_points_check") and self.settings_auto_points_check:
                    self.settings_auto_points_check.setChecked(bool(cfg.get("auto_points_enabled", True)))
            except Exception:
                pass
            try:
                if hasattr(self, "settings_export_mode_combo") and self.settings_export_mode_combo:
                    export_mode = str(cfg.get("export_mode", "student") or "student")
                    idx = self.settings_export_mode_combo.findData(export_mode)
                    if idx >= 0:
                        self.settings_export_mode_combo.setCurrentIndex(idx)
            except Exception:
                pass
            try:
                if hasattr(self, "settings_allow_delete_check") and self.settings_allow_delete_check:
                    self.settings_allow_delete_check.setChecked(bool(cfg.get("allow_delete_question", True)))
            except Exception:
                pass
            self._sync_settings_for_game_type()
        except Exception:
            pass
        
    def load_questions(self):
        """Load questions from current project"""
        self.questions_list.clear()
        has_questions = False
        if self.current_project and 'questions' in self.current_project:
            for i, question in enumerate(self.current_project['questions']):
                item = QListWidgetItem(f"Q{i+1}: {question.get('question', 'Untitled')}")
                item.setData(Qt.UserRole, question)
                self.questions_list.addItem(item)
            has_questions = self.questions_list.count() > 0
        try:
            self.questions_empty_state.setVisible(not has_questions)
            self.questions_list.setVisible(has_questions)
        except Exception:
            pass
        self._update_question_action_buttons()

    def _rebalance_question_points(self):
        try:
            if not isinstance(self.current_project, dict):
                return
            cfg = dict(self.current_project.get("game_config") or {})
            if not bool(cfg.get("auto_points_enabled", False)):
                return
            questions = self.current_project.get("questions") or []
            valid_questions = [q for q in questions if isinstance(q, dict)]
            if not valid_questions:
                cfg["points_per_question"] = 0
                self.current_project["game_config"] = cfg
                return
            total_points = int(cfg.get("total_points", 100) or 100)
            total_points = max(1, total_points)
            base = max(1, total_points // len(valid_questions))
            remainder = max(0, total_points - (base * len(valid_questions)))
            for idx, question in enumerate(valid_questions):
                question["points"] = int(base + (1 if idx < remainder else 0))
            cfg["points_per_question"] = int(base)
            self.current_project["game_config"] = cfg
        except Exception:
            pass
    
    def import_questions(self):
        """Emit signal to request question import"""
        self.import_questions_requested.emit()

    def _is_millionaire_game(self) -> bool:
        try:
            top_gt = str((self.current_project or {}).get("game_type") or "").lower()
            cfg_gt = str(((self.current_project or {}).get("game_config") or {}).get("game_type") or "").lower()
            merged = f"{top_gt} {cfg_gt}"
            return ("triệu phú" in merged) or ("trieu phu" in merged) or ("millionaire" in merged)
        except Exception:
            return False

    def create_settings_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        # Wrap content in scroll area so it never overflows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        from PySide6.QtWidgets import QSizePolicy
        inner.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)
        layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)

        scroll.setWidget(inner)
        tab_layout.addWidget(scroll)

        cfg_group = QGroupBox(I18n.t("editor.left.settings_group_title"))
        cfg_layout = QVBoxLayout(cfg_group)
        cfg_layout.setSpacing(10)

        cfg_layout.addWidget(QLabel(I18n.t("editor.left.settings_default_time_label")))
        self.settings_default_time_spin = QSpinBox()
        self.settings_default_time_spin.setRange(5, 300)
        self.settings_default_time_spin.setValue(30)
        cfg_layout.addWidget(self.settings_default_time_spin)

        self.settings_music_label = QLabel(I18n.t("editor.left.settings_music_label"))
        cfg_layout.addWidget(self.settings_music_label)
        self.settings_music_mode_combo = QComboBox()
        self.settings_music_mode_combo.addItem(I18n.t("editor.left.settings_music_custom"), "custom")
        self.settings_music_mode_combo.addItem(I18n.t("editor.left.settings_music_random"), "random_builtin")
        self.settings_music_mode_combo.addItem(I18n.t("editor.left.settings_music_builtin_1"), "builtin_1")
        self.settings_music_mode_combo.addItem(I18n.t("editor.left.settings_music_builtin_2"), "builtin_2")
        cfg_layout.addWidget(self.settings_music_mode_combo)

        self.settings_custom_music_label = QLabel(I18n.t("editor.left.settings_custom_music_label"))
        cfg_layout.addWidget(self.settings_custom_music_label)
        self.settings_custom_music_wrap = QWidget()
        custom_music_layout = QHBoxLayout(self.settings_custom_music_wrap)
        custom_music_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_custom_music_edit = QLineEdit()
        self.settings_custom_music_edit.setPlaceholderText(I18n.t("editor.left.settings_custom_music_placeholder"))
        custom_music_layout.addWidget(self.settings_custom_music_edit)
        self.settings_custom_music_browse_btn = QPushButton(I18n.t("editor.left.settings_browse_btn"))
        custom_music_layout.addWidget(self.settings_custom_music_browse_btn)
        cfg_layout.addWidget(self.settings_custom_music_wrap)

        self.settings_millionaire_note = QLabel(I18n.t("editor.left.settings_millionaire_note"))
        self.settings_millionaire_note.setWordWrap(True)
        cfg_layout.addWidget(self.settings_millionaire_note)

        checkbox_style = """
            QCheckBox {
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: transparent;
                border: 1px solid #6B7280;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #7F56D9;
                border-color: #7F56D9;
            }
        """

        self.settings_randomize_questions_check = QCheckBox(I18n.t("editor.left.randomize_questions") if hasattr(I18n, 't') else "Trộn câu hỏi")
        self.settings_randomize_questions_check.setChecked(True)
        self.settings_randomize_questions_check.setStyleSheet(checkbox_style)
        cfg_layout.addWidget(self.settings_randomize_questions_check)

        self.settings_auto_points_check = QCheckBox(I18n.t("settings.auto_points_enabled"))
        self.settings_auto_points_check.setChecked(True)
        self.settings_auto_points_check.setStyleSheet(checkbox_style)
        cfg_layout.addWidget(self.settings_auto_points_check)

        self.settings_export_mode_label = QLabel(I18n.t("editor.left.export_mode_label"))
        cfg_layout.addWidget(self.settings_export_mode_label)
        self.settings_export_mode_combo = QComboBox()
        self.settings_export_mode_combo.addItem(I18n.t("editor.left.export_mode_student"), "student")
        self.settings_export_mode_combo.addItem(I18n.t("editor.left.export_mode_teaching"), "teaching")
        cfg_layout.addWidget(self.settings_export_mode_combo)

        actions_row = QHBoxLayout()
        self.apply_settings_btn = QPushButton(I18n.t("editor.left.settings_apply_btn"))
        self.apply_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        actions_row.addWidget(self.apply_settings_btn)
        self.apply_selected_settings_btn = QPushButton(I18n.t("editor.left.settings_apply_selected_btn") if hasattr(I18n, "t") else "Áp dụng có chọn")
        self.apply_selected_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #7F56D9;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6941C6;
            }
        """)
        actions_row.addWidget(self.apply_selected_settings_btn)
        cfg_layout.addLayout(actions_row)

        layout.addWidget(cfg_group)
        layout.addStretch()

        self.settings_music_mode_combo.currentIndexChanged.connect(self._sync_settings_custom_music_visibility)
        self.settings_custom_music_browse_btn.clicked.connect(self._browse_settings_custom_music)
        self.apply_settings_btn.clicked.connect(self.apply_settings_tab)
        self.apply_selected_settings_btn.clicked.connect(self.apply_settings_with_selection)
        self._sync_settings_custom_music_visibility()
        self._sync_settings_for_game_type()

        return tab

    def _browse_settings_custom_music(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            I18n.t("editor.left.settings_select_music_title"),
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.m4a);;All Files (*.*)"
        )
        if file_path:
            self.settings_custom_music_edit.setText(file_path)

    def _sync_settings_custom_music_visibility(self):
        try:
            mode = self.settings_music_mode_combo.currentData()
            visible = (mode == "custom")
            self.settings_custom_music_label.setVisible(visible)
            self.settings_custom_music_wrap.setVisible(visible)
        except Exception:
            pass

    def _sync_settings_for_game_type(self):
        is_millionaire = self._is_millionaire_game()
        enable_music_controls = not is_millionaire
        self.settings_music_label.setVisible(enable_music_controls)
        self.settings_music_mode_combo.setVisible(enable_music_controls)
        self.settings_millionaire_note.setVisible(is_millionaire)
        if is_millionaire:
            self.settings_custom_music_label.setVisible(False)
            self.settings_custom_music_wrap.setVisible(False)
        else:
            self._sync_settings_custom_music_visibility()

    def apply_settings_tab(self):
        payload = self._build_settings_payload()
        self.question_settings_applied.emit(payload)

    def _build_settings_payload(self):
        is_millionaire = self._is_millionaire_game()
        return {
            "default_question_time": int(self.settings_default_time_spin.value()),
            "is_millionaire": bool(is_millionaire),
            "music_mode": "none" if is_millionaire else (self.settings_music_mode_combo.currentData() or "builtin_1"),
            "custom_music_path": "" if is_millionaire else self.settings_custom_music_edit.text().strip(),
            "randomize_questions": bool(getattr(self, "settings_randomize_questions_check", None) and self.settings_randomize_questions_check.isChecked()),
            "auto_points_enabled": bool(getattr(self, "settings_auto_points_check", None) and self.settings_auto_points_check.isChecked()),
            "export_mode": str(getattr(self, "settings_export_mode_combo", None).currentData() if getattr(self, "settings_export_mode_combo", None) else "student"),
        }

    def apply_settings_with_selection(self):
        try:
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QDialogButtonBox
        except Exception:
            self.apply_settings_tab()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(I18n.t("editor.left.settings_apply_selected_title") if hasattr(I18n, "t") else "Chọn mục áp dụng")
        try:
            dialog.setMinimumWidth(420)
        except Exception:
            pass
        layout = QVBoxLayout(dialog)
        description_label = QLabel(I18n.t("editor.left.settings_apply_selected_desc") if hasattr(I18n, "t") else "Chọn các trường muốn áp dụng cho toàn bộ câu hỏi và dự án hiện tại.")
        try:
            description_label.setWordWrap(True)
        except Exception:
            pass
        layout.addWidget(description_label)

        field_defs = [
            ("question_time", I18n.t("editor.left.settings_field_time") if hasattr(I18n, "t") else "Thời gian mỗi câu"),
            ("randomize_questions", I18n.t("editor.left.settings_field_shuffle") if hasattr(I18n, "t") else "Xáo trộn câu hỏi"),
            ("background_music", I18n.t("editor.left.settings_field_music") if hasattr(I18n, "t") else "Nhạc nền"),
            ("export_mode", I18n.t("editor.left.settings_field_export_mode") if hasattr(I18n, "t") else "Chế độ xuất"),
            ("auto_points_enabled", I18n.t("editor.left.settings_field_auto_points") if hasattr(I18n, "t") else "Tự chia điểm"),
        ]
        checks = []
        for field_key, label in field_defs:
            check = QCheckBox(label, dialog)
            check.setChecked(True)
            layout.addWidget(check)
            checks.append((field_key, check))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        self._apply_selection_dialog_theme(dialog, description_label, [check for _, check in checks], buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        selected_fields = [field_key for field_key, check in checks if check.isChecked()]
        if not selected_fields:
            return
        payload = self._build_settings_payload()
        payload["apply_to_all_fields"] = selected_fields
        self.question_settings_applied.emit(payload)

    def _selection_dialog_theme_tokens(self) -> dict:
        try:
            from eduplay.core.settings_manager import SettingsManager

            theme = SettingsManager().get_theme() or "dark"
        except Exception:
            theme = "dark"
        if str(theme).lower() == "dark":
            return {
                "dialog_bg": "#111827",
                "dialog_fg": "#E5E7EB",
                "muted_fg": "#94A3B8",
                "border": "#374151",
                "hover": "#1F2937",
                "button_bg": "#F9FAFB",
                "button_fg": "#111827",
                "button_hover": "#E5E7EB",
            }
        return {
            "dialog_bg": "#FFFFFF",
            "dialog_fg": "#0F172A",
            "muted_fg": "#475467",
            "border": "#D0D5DD",
            "hover": "#F8FAFC",
            "button_bg": "#F9FAFB",
            "button_fg": "#111827",
            "button_hover": "#E5E7EB",
        }

    def _apply_selection_dialog_theme(self, dialog, description_label, checkboxes, buttons):
        colors = self._selection_dialog_theme_tokens()
        try:
            dialog.setStyleSheet(
                f"""
                QDialog {{
                    background-color: {colors["dialog_bg"]};
                    color: {colors["dialog_fg"]};
                }}
                QLabel {{
                    background: transparent;
                    color: {colors["dialog_fg"]};
                }}
                QCheckBox {{
                    background: transparent;
                    color: {colors["dialog_fg"]};
                    spacing: 8px;
                    padding: 2px 0px;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1px solid {colors["border"]};
                    background-color: transparent;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #7F56D9;
                    border-color: #7F56D9;
                }}
                QDialogButtonBox QPushButton {{
                    min-width: 84px;
                    padding: 8px 14px;
                    border-radius: 10px;
                    border: 1px solid {colors["border"]};
                    background-color: {colors["button_bg"]};
                    color: {colors["button_fg"]};
                    font-weight: 600;
                }}
                QDialogButtonBox QPushButton:hover {{
                    background-color: {colors["button_hover"]};
                }}
                """
            )
        except Exception:
            pass
        try:
            description_label.setStyleSheet(f"color: {colors['muted_fg']};")
        except Exception:
            pass
        for check in checkboxes or []:
            try:
                check.setCursor(Qt.PointingHandCursor)
            except Exception:
                pass
        try:
            for btn in buttons.buttons():
                btn.setCursor(Qt.PointingHandCursor)
            ok_btn = buttons.button(QDialogButtonBox.Ok)
            if ok_btn is not None:
                ok_btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #111827;
                        border: 1px solid #D0D5DD;
                        border-radius: 10px;
                        padding: 8px 14px;
                        font-weight: 700;
                    }
                    QPushButton:hover {
                        background-color: #E5E7EB;
                    }
                    """
                )
        except Exception:
            pass
                
    def load_game_config(self):
        """Load game configuration"""
        if self.current_project and 'game_config' in self.current_project:
            config = self.current_project['game_config']
            try:
                if hasattr(self, 'game_type_combo') and self.game_type_combo:
                    raw = str(config.get('game_type', '') or '').strip().lower()
                    if raw in ("quiz classic", "quiz_classic", "quiz"):
                        self.game_type_combo.setCurrentData("quiz_classic")
                    elif raw in ("fishing game", "fishing", "fish", "trò chơi câu cá", "tro choi cau ca", "câu cá", "cau ca", "bắt cá", "bat ca"):
                        self.game_type_combo.setCurrentData("fishing")
                    elif raw in ("ai là triệu phú", "ai la trieu phu", "millionaire", "who wants to be a millionaire", "quiz_millionaire"):
                        self.game_type_combo.setCurrentData("quiz_millionaire")
                    else:
                        self.game_type_combo.setCurrentData("quiz_classic")
            except Exception:
                pass
            try:
                if hasattr(self, 'difficulty_combo') and self.difficulty_combo:
                    raw = str(config.get('difficulty', '') or '').strip().lower()
                    if raw in ("easy", "dễ", "de"):
                        self.difficulty_combo.setCurrentData("Easy")
                    elif raw in ("hard", "khó", "schwer", "difficile"):
                        self.difficulty_combo.setCurrentData("Hard")
                    else:
                        self.difficulty_combo.setCurrentData("Medium")
            except Exception:
                pass
            try:
                if hasattr(self, 'question_time_spin') and self.question_time_spin:
                    self.question_time_spin.setValue(config.get('question_time', 30))
            except Exception:
                pass
            try:
                if hasattr(self, 'time_limit_check') and self.time_limit_check:
                    self.time_limit_check.setChecked(config.get('time_limit_enabled', True))
            except Exception:
                pass
            try:
                if hasattr(self, 'points_spin') and self.points_spin:
                    self.points_spin.setValue(config.get('points_per_question', 10))
            except Exception:
                pass
            try:
                if hasattr(self, 'penalty_check') and self.penalty_check:
                    self.penalty_check.setChecked(config.get('penalty_enabled', False))
            except Exception:
                pass
            try:
                if hasattr(self, 'show_explanations_check') and self.show_explanations_check:
                    self.show_explanations_check.setChecked(config.get('show_explanations', True))
            except Exception:
                pass
            try:
                if hasattr(self, 'randomize_questions_check') and self.randomize_questions_check:
                    self.randomize_questions_check.setChecked(config.get('randomize_questions', True))
            except Exception:
                pass
            try:
                if hasattr(self, 'settings_randomize_questions_check') and self.settings_randomize_questions_check:
                    self.settings_randomize_questions_check.setChecked(config.get('randomize_questions', True))
            except Exception:
                pass
            try:
                if hasattr(self, 'settings_auto_points_check') and self.settings_auto_points_check:
                    self.settings_auto_points_check.setChecked(config.get('auto_points_enabled', True))
            except Exception:
                pass
            
    def load_assets(self):
        """Load asset categories and assets"""
        self.categories_tree.clear()
        self.assets_list.clear()
        
        # Add default categories
        categories = [
            I18n.t("editor.left.category_backgrounds"),
            I18n.t("editor.left.category_characters"),
            I18n.t("editor.left.category_ui_elements"),
            I18n.t("editor.left.category_sounds"),
            I18n.t("editor.left.category_animations"),
        ]
        for category in categories:
            item = QTreeWidgetItem(self.categories_tree)
            item.setText(0, category)
            
        # Load some sample assets
        sample_assets = [
            ('Backgrounds', 'sky_background.png'),
            ('Backgrounds', 'forest_background.png'),
            ('Characters', 'player_sprite.png'),
            ('Characters', 'enemy_sprite.png'),
            ('UI Elements', 'button_normal.png'),
            ('UI Elements', 'button_hover.png'),
            ('Sounds', 'correct_answer.wav'),
            ('Sounds', 'wrong_answer.wav')
        ]
        
        for category, asset in sample_assets:
            item = QListWidgetItem(f"{asset}")
            item.setData(Qt.UserRole, {'category': category, 'name': asset})
            self.assets_list.addItem(item)
            
    def add_question(self):
        """Add a new question"""
        if self.current_project:
            default_time = 30
            try:
                default_time = int(((self.current_project.get("game_config") or {}).get("question_time", 30)) or 30)
            except Exception:
                default_time = 30
            new_question = {
                'question': I18n.t("editor.left.new_question"),
                'type': 'multiple_choice',
                'options': [
                    f"{I18n.t('import.default.option')} A",
                    f"{I18n.t('import.default.option')} B",
                    f"{I18n.t('import.default.option')} C",
                    f"{I18n.t('import.default.option')} D",
                ],
                'correct_answer': 0,
                'explanation': '',
                'time_limit': default_time,
            }
            try:
                import uuid
                new_question["id"] = f"q_{uuid.uuid4().hex[:10]}"
            except Exception:
                pass
            
            if 'questions' not in self.current_project:
                self.current_project['questions'] = []
            self.current_project['questions'].append(new_question)
            EditorLeftPanel._rebalance_question_points(self)
            
            self.load_questions()
            # Select the newly added question
            last_item = self.questions_list.item(self.questions_list.count() - 1)
            if last_item:
                self.questions_list.setCurrentItem(last_item)
                self._update_question_action_buttons()
                
    def on_question_selected(self, item):
        """Handle question selection"""
        if item is None:
            self._update_question_action_buttons()
            return
        question_data = item.data(Qt.UserRole)
        self.question_selected.emit(question_data)

    def request_delete_selected_question(self):
        payload = self._build_selected_question_payload()
        if payload is not None:
            self.delete_question_requested.emit(payload)

    def request_preview_selected_question(self):
        payload = self._build_selected_question_payload()
        if payload is not None:
            self.preview_question_requested.emit(payload)
        
    def on_game_config_changed(self):
        """Handle game configuration changes"""
        config = {
            'game_type': self.game_type_combo.currentData() or "Quiz Classic",
            'difficulty': self.difficulty_combo.currentData() or "Medium",
            'question_time': self.question_time_spin.value(),
            'time_limit_enabled': self.time_limit_check.isChecked(),
            'points_per_question': self.points_spin.value(),
            'penalty_enabled': self.penalty_check.isChecked(),
            'show_explanations': self.show_explanations_check.isChecked() if hasattr(self, 'show_explanations_check') else True,
            'randomize_questions': self.randomize_questions_check.isChecked() if hasattr(self, 'randomize_questions_check') else True
        }
        self.game_config_changed.emit(config)
        
    def on_category_selected(self, item):
        """Handle category selection"""
        category = item.text(0)
        self.filter_assets_by_category(category)
        
    def filter_assets_by_category(self, category):
        """Filter assets by category"""
        for i in range(self.assets_list.count()):
            item = self.assets_list.item(i)
            asset_data = item.data(Qt.UserRole)
            if asset_data and asset_data.get('category') == category:
                item.setHidden(False)
            else:
                item.setHidden(True)
                
    def search_assets(self):
        """Search assets by name"""
        search_text = self.media_search.text().lower()
        for i in range(self.assets_list.count()):
            item = self.assets_list.item(i)
            if search_text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)
                
    def on_asset_selected(self, item):
        """Emit asset_selected when an asset is double-clicked"""
        try:
            data = item.data(Qt.UserRole) or {}
            asset_name = data.get('name') or str(item.text())
            self.asset_selected.emit(asset_name)
        except Exception:
            try:
                self.asset_selected.emit(str(item.text()))
            except Exception:
                pass
                
    def get_game_config(self):
        """Get current game configuration"""
        return {
            'game_type': self.game_type_combo.currentData() or "Quiz Classic",
            'difficulty': self.difficulty_combo.currentData() or "Medium",
            'question_time': self.question_time_spin.value(),
            'time_limit_enabled': self.time_limit_check.isChecked(),
            'points_per_question': self.points_spin.value(),
            'penalty_enabled': self.penalty_check.isChecked(),
            'show_explanations': self.show_explanations_check.isChecked() if hasattr(self, 'show_explanations_check') else True,
            'randomize_questions': self.randomize_questions_check.isChecked() if hasattr(self, 'randomize_questions_check') else True
        }

