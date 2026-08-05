"""
Settings Dialog - For managing API keys and application preferences
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                               QWidget, QLineEdit, QPushButton, QLabel,
                               QComboBox, QSpinBox, QCheckBox, QGroupBox,
                               QTextEdit, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QFont
from eduplay.ui.widgets.custom_dropdown import FlatDropdown
import os
from urllib.parse import urlparse


class _BackgroundWorker(QObject):
    finished = Signal(object, object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        result = None
        error = None
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as e:
            error = e
        self.finished.emit(result, error)

class SettingsDialog(QDialog):
    """Settings dialog for API keys and preferences"""
    
    settings_changed = Signal()
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
            self.setWindowTitle(I18n.t('settings.title', lang))
        except Exception:
            self.setWindowTitle("Settings")
        self.setModal(True)
        try:
            self.setWindowFlags(
                Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint |
                Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint |
                Qt.WindowCloseButtonHint
            )
        except Exception:
            pass
        self.resize(900, 650)
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                g = screen.availableGeometry()
                w = min(self.width(), max(720, int(g.width() * 0.92)))
                h = min(self.height(), max(520, int(g.height() * 0.92)))
                self.resize(w, h)
        except Exception:
            pass
        self._background_threads = []
        self._background_workers = []
        
        self.setup_ui()
        self.load_settings()
        try:
            self._apply_theme()
        except Exception:
            pass
        try:
            self.apply_i18n()
        except Exception:
            pass

    def _lang(self) -> str:
        try:
            return self.settings_manager.get_language() or "en"
        except Exception:
            return "en"

    def _t(self, key: str, fallback: str, **kwargs) -> str:
        try:
            from eduplay.core.i18n import I18n
            value = I18n.t(key, self._lang(), **kwargs)
            return value if isinstance(value, str) else fallback
        except Exception:
            return fallback
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create tabs
        self.create_general_tab()
        self.create_editor_tab()
        self.create_game_defaults_tab()
        self.create_addin_tab()
        
        # Create buttons
        button_layout = QHBoxLayout()
        
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
            save_text = I18n.t('settings.save', lang)
            cancel_text = I18n.t('settings.cancel', lang)
            reset_text = I18n.t('settings.reset', lang)
        except Exception:
            save_text, cancel_text, reset_text = "Save", "Cancel", "Reset to Defaults"
        self.save_button = QPushButton(save_text)
        self.save_button.clicked.connect(self.save_settings)
        
        self.cancel_button = QPushButton(cancel_text)
        self.cancel_button.clicked.connect(self.reject)
        
        self.reset_button = QPushButton(reset_text)
        self.reset_button.clicked.connect(self.reset_settings)
        
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)

    def _wrap_scroll(self, widget: QWidget) -> QWidget:
        from PySide6.QtWidgets import QScrollArea, QFrame

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(widget)
        return scroll
    
    def _apply_theme(self):
        try:
            from eduplay.core.settings_manager import SettingsManager
            sm = self.settings_manager or SettingsManager()
            theme = sm.get_theme() or "dark"
        except Exception:
            theme = "dark"
        if theme == "dark":
            dialog_bg = "#020617"
            text_color = "#E5E7EB"
            group_bg = "#111827"
            group_border = "#1F2937"
            group_title = "#E5E7EB"
            popup_bg = "#111827"
            popup_border = "#4A4E5A"
            popup_text = "#E5E7EB"
            popup_hover = "#1F2933"
            extra_light_css = ""
        else:
            dialog_bg = "#FFFFFF"
            text_color = "#0F1728"
            group_bg = "#F9FAFF"
            group_border = "#E2E8F0"
            group_title = "#7F56D9"
            popup_bg = "#F9FAFF"
            popup_border = "#D0D5DD"
            popup_text = "#0F1728"
            popup_hover = "#E0EAFF"
            extra_light_css = """
            QScrollBar:vertical {
                background-color: #F2F4F7;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #CBD5E1;
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #A5B4FC;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: transparent;
                height: 0px;
            }
            QPushButton:hover {
                color: #0F1728;
            }
            """
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {dialog_bg};
                color: {text_color};
            }}
            QGroupBox {{
                background-color: {group_bg};
                border: 1px solid {group_border};
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                left: 10px;
                padding: 0 6px;
                font-weight: 600;
                color: {group_title};
            }}
            QComboBox::view {{
                margin: 0px;
                padding: 0px;
            }}
            QComboBox QFrame {{
                background-color: {popup_bg};
                border: 1px solid {popup_border};
                border-radius: 0px 0px 8px 8px;
                margin: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {popup_bg};
                color: {popup_text};
                border: none;
                padding: 0px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 12px;
                margin: 0px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #7F56D9;
                color: #FFFFFF;
            }}
            QComboBox QAbstractItemView::item:hover:!selected {{
                background-color: {popup_hover};
            }}
            {extra_light_css}
            """
        )
        try:
            dropdown_names = ("language_combo", "theme_combo", "model_combo", "font_family_combo")
            for name in dropdown_names:
                w = getattr(self, name, None)
                if not w or not hasattr(w, "button") or not hasattr(w, "popup"):
                    continue
                if theme == "dark":
                    w.button.setStyleSheet(
                        """
                        QToolButton {
                            background-color: #111827;
                            color: #E5E7EB;
                            border: 1px solid #4A4E5A;
                            border-radius: 8px;
                            padding: 8px 12px 8px 4px;
                            min-width: 160px;
                            text-align: left;
                        }
                        QToolButton::menu-indicator {
                            image: none;
                        }
                        """
                    )
                    w.popup.setStyleSheet(
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
                    w.button.setStyleSheet(
                        """
                        QToolButton {
                            background-color: #FFFFFF;
                            color: #0F1728;
                            border: 1px solid #D0D5DD;
                            border-radius: 10px;
                            padding: 8px 12px 8px 4px;
                            min-width: 160px;
                            text-align: left;
                        }
                        QToolButton::menu-indicator {
                            image: none;
                        }
                        """
                    )
                    w.popup.setStyleSheet(
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
    
    def create_general_tab(self):
        """Create general settings tab"""
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
        except Exception:
            I18n = None
            lang = "en"
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        if I18n:
            lang_title = I18n.t('settings.language', lang)
            app_lang_label = I18n.t('settings.app_language', lang)
        else:
            lang_title, app_lang_label = "Language", "Application Language:"
        lang_group = QGroupBox(lang_title)
        lang_layout = QVBoxLayout()
        
        self.language_combo = FlatDropdown()
        try:
            if not I18n:
                raise Exception("no_i18n")
            ln = lambda k: I18n.t(k, lang)
            names = [ln('lang.en'), ln('lang.vi'), ln('lang.fr'), ln('lang.es'), ln('lang.de')]
        except Exception:
            names = ["English", "Vietnamese", "French", "Spanish", "German"]
        language_codes = ["en", "vi", "fr", "es", "de"]
        for name, code in zip(names, language_codes):
            self.language_combo.addItem(name, code)
        
        lang_layout.addWidget(QLabel(app_lang_label))
        lang_layout.addWidget(self.language_combo)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        if I18n:
            theme_title = I18n.t('settings.appearance', lang)
            theme_label = I18n.t('settings.theme', lang)
            themes = [I18n.t('settings.dark', lang), I18n.t('settings.light', lang)]
        else:
            theme_title, theme_label, themes = "Appearance", "Theme:", ["Dark", "Light"]
        theme_group = QGroupBox(theme_title)
        theme_layout = QVBoxLayout()
        
        self.theme_combo = FlatDropdown()
        for t in themes:
            self.theme_combo.addItem(t)
        
        theme_layout.addWidget(QLabel(theme_label))
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)

        layout.addWidget(theme_group)
        
        if I18n:
            autosave_title = I18n.t('settings.autosave', lang)
            autosave_enable = I18n.t('settings.enable_autosave', lang)
            autosave_interval = I18n.t('settings.autosave_interval', lang)
        else:
            autosave_title, autosave_enable, autosave_interval = "Auto-save", "Enable auto-save", "Auto-save interval:"
        autosave_group = QGroupBox(autosave_title)
        autosave_layout = QVBoxLayout()
        
        self.autosave_check = QCheckBox(autosave_enable)
        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(30, 3600)  # 30 seconds to 1 hour
        self.autosave_interval.setSuffix(" seconds")
        self.autosave_interval.setSingleStep(30)
        
        autosave_layout.addWidget(self.autosave_check)
        autosave_layout.addWidget(QLabel(autosave_interval))
        autosave_layout.addWidget(self.autosave_interval)
        autosave_group.setLayout(autosave_layout)
        layout.addWidget(autosave_group)
        
        try:
            try:
                notif_title = I18n.t('settings.notifications', lang)
                notif_sys = I18n.t('settings.notifications_system', lang)
                notif_bg = I18n.t('settings.notifications_only_bg', lang)
                notif_test = I18n.t('settings.notifications_test', lang)
            except Exception:
                notif_title = "Notifications"
                notif_sys = "Enable system notifications"
                notif_bg = "Only when app is in background"
                notif_test = "Test notification"
        except Exception:
            notif_title = "Notifications"
            notif_sys = "Enable system notifications"
            notif_bg = "Only when app is in background"
            notif_test = "Test notification"
        notifications_group = QGroupBox(notif_title)
        notifications_layout = QVBoxLayout()
        self.notifications_system_check = QCheckBox(notif_sys)
        self.notifications_background_check = QCheckBox(notif_bg)
        notifications_layout.addWidget(self.notifications_system_check)
        notifications_layout.addWidget(self.notifications_background_check)
        notifications_group.setLayout(notifications_layout)
        layout.addWidget(notifications_group)

        try:
            accessibility_title = I18n.t('settings.accessibility', lang)
            ui_scale_label = I18n.t('settings.accessibility_ui_scale', lang)
            high_contrast_label = I18n.t('settings.accessibility_high_contrast', lang)
            reduce_motion_label = I18n.t('settings.accessibility_reduce_motion', lang)
        except Exception:
            accessibility_title = "Accessibility"
            ui_scale_label = "UI scale:"
            high_contrast_label = "High contrast"
            reduce_motion_label = "Reduce motion"
        accessibility_group = QGroupBox(accessibility_title)
        accessibility_layout = QVBoxLayout()
        scale_row = QHBoxLayout()
        self.ui_scale_spin = QSpinBox()
        self.ui_scale_spin.setRange(90, 150)
        self.ui_scale_spin.setSuffix("%")
        self.ui_scale_spin.setSingleStep(5)
        scale_row.addWidget(QLabel(ui_scale_label))
        scale_row.addWidget(self.ui_scale_spin)
        accessibility_layout.addLayout(scale_row)
        self.high_contrast_check = QCheckBox(high_contrast_label)
        self.reduce_motion_check = QCheckBox(reduce_motion_label)
        accessibility_layout.addWidget(self.high_contrast_check)
        accessibility_layout.addWidget(self.reduce_motion_check)
        accessibility_group.setLayout(accessibility_layout)
        layout.addWidget(accessibility_group)

        credits_btn_layout = QHBoxLayout()
        try:
            credits_btn_text = I18n.t('settings.view_credits', lang)
        except Exception:
            credits_btn_text = "View Credits"
        self.view_credits_btn = QPushButton(credits_btn_text)
        try:
            self.view_credits_btn.clicked.connect(self._on_view_credits_clicked)
        except Exception:
            pass
        try:
            from eduplay.core.i18n import I18n as _I18n
            download_text = _I18n.t('help.download_docx_btn', lang)
        except Exception:
            download_text = "⬇️ DOCX Template"
        self.download_template_btn = QPushButton(download_text)
        try:
            self.download_template_btn.clicked.connect(self._download_template)
        except Exception:
            pass
        credits_btn_layout.addStretch()
        credits_btn_layout.addWidget(self.view_credits_btn)
        credits_btn_layout.addWidget(self.download_template_btn)
        layout.addLayout(credits_btn_layout)
        
        layout.addStretch()
        tab_title = "General"
        if I18n:
            try:
                tab_title = I18n.t('settings.tabs.general', lang)
            except Exception:
                tab_title = "General"
        self.tabs.addTab(self._wrap_scroll(tab), tab_title)
    
    def create_ai_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
            tab_title = I18n.t('settings.tabs.ai', lang)
        except Exception:
            lang = "en"
            tab_title = "AI"

        api_group = QGroupBox(self._t("settings.ai_server_group", "AI Server"))
        api_layout = QVBoxLayout()

        api_layout.addWidget(QLabel(self._t(
            "settings.ai_server_desc",
            "EduPlay routes AI requests through the intermediate server. Keep the real provider key on the server, not in the desktop app."
        )))

        proxy_row = QHBoxLayout()
        proxy_row.addWidget(QLabel(self._t("settings.ai_base_url", "Base URL")))
        self.groq_base_url_input = QLineEdit()
        self.groq_base_url_input.setPlaceholderText("https://site--eduplay-ai--sx2zlgv27rbh.code.run/openai/v1")
        proxy_row.addWidget(self.groq_base_url_input)
        api_layout.addLayout(proxy_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel(self._t("settings.ai_model", "Model")))
        self.groq_model_input = QLineEdit()
        self.groq_model_input.setPlaceholderText("llama-3.1-8b-instant")
        model_row.addWidget(self.groq_model_input)
        api_layout.addLayout(model_row)

        task_model_row = QHBoxLayout()
        task_model_row.addWidget(QLabel(self._t("settings.ai_task_model", "Task model")))
        self.groq_task_model_input = QLineEdit()
        self.groq_task_model_input.setPlaceholderText("qwen/qwen3-32b")
        task_model_row.addWidget(self.groq_task_model_input)
        api_layout.addLayout(task_model_row)

        btn_row = QHBoxLayout()
        self.test_groq_btn = QPushButton(self._t("settings.ai_test_server", "Test AI Server"))
        self.test_groq_btn.clicked.connect(self.test_groq_key)
        btn_row.addWidget(self.test_groq_btn)
        btn_row.addStretch()
        api_layout.addLayout(btn_row)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        layout.addStretch()
        self.tabs.addTab(self._wrap_scroll(tab), tab_title)
    
    def create_editor_tab(self):
        """Create editor settings tab"""
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
        except Exception:
            I18n = None
            lang = "en"
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        if I18n:
            font_title = I18n.t('settings.font', lang)
            font_family_label = I18n.t('settings.font_family', lang)
            font_size_label = I18n.t('settings.font_size', lang)
            editor_opts_title = I18n.t('settings.editor_options', lang)
            ln_label = I18n.t('settings.line_numbers', lang)
            ac_label = I18n.t('settings.auto_complete', lang)
            sp_label = I18n.t('settings.spell_check', lang)
        else:
            font_title, font_family_label, font_size_label = "Font Settings", "Font Family:", "Font Size:"
            editor_opts_title, ln_label, ac_label, sp_label = "Editor Options", "Show line numbers", "Enable auto-complete", "Enable spell check"
        font_group = QGroupBox(font_title)
        font_layout = QVBoxLayout()
        
        # Font family
        family_layout = QHBoxLayout()
        self.font_family_combo = FlatDropdown()
        self.font_family_combo.addItems(["Arial", "Times New Roman", "Courier New", "Verdana", "Tahoma"])
        
        family_layout.addWidget(QLabel(font_family_label))
        family_layout.addWidget(self.font_family_combo)
        font_layout.addLayout(family_layout)
        
        # Font size
        size_layout = QHBoxLayout()
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setSingleStep(1)
        
        size_layout.addWidget(QLabel(font_size_label))
        size_layout.addWidget(self.font_size_spin)
        font_layout.addLayout(size_layout)
        
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        # Editor options
        options_group = QGroupBox(editor_opts_title)
        options_layout = QVBoxLayout()
        
        self.line_numbers_check = QCheckBox(ln_label)
        self.auto_complete_check = QCheckBox(ac_label)
        self.spell_check_check = QCheckBox(sp_label)
        
        options_layout.addWidget(self.line_numbers_check)
        options_layout.addWidget(self.auto_complete_check)
        options_layout.addWidget(self.spell_check_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        layout.addStretch()
        tab_title = "Editor"
        if I18n:
            try:
                tab_title = I18n.t('settings.tabs.editor', lang)
            except Exception:
                tab_title = "Editor"
        self.tabs.addTab(self._wrap_scroll(tab), tab_title)
    
    def create_game_defaults_tab(self):
        """Create game defaults settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
            title = I18n.t('settings.game_defaults', lang)
            qtime_label = I18n.t('settings.quiz_time_per_question', lang)
            show_expl_label = I18n.t('settings.show_explanations', lang)
            randomize_label = I18n.t('settings.randomize_questions', lang)
            points_label = I18n.t('settings.points_per_question', lang)
            auto_points_label = I18n.t('settings.auto_points_enabled', lang)
            time_limit_enabled_label = I18n.t('settings.time_limit_enabled', lang)
        except Exception:
            title = "Game Defaults"
            qtime_label = "Quiz time per question (seconds):"
            show_expl_label = "Show explanations after answer"
            randomize_label = "Randomize question order"
            points_label = "Points per question"
            auto_points_label = "Auto-distribute points (total 10 points)"
            time_limit_enabled_label = "Enable time limit"

        group = QGroupBox(title)
        group_layout = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel(qtime_label))
        self.quiz_time_per_question_spin = QSpinBox()
        self.quiz_time_per_question_spin.setRange(5, 300)
        self.quiz_time_per_question_spin.setSingleStep(5)
        self.quiz_time_per_question_spin.setSuffix(" s")
        row.addWidget(self.quiz_time_per_question_spin)
        row.addStretch()
        group_layout.addLayout(row)

        self.show_explanations_default = QCheckBox(show_expl_label)
        self.randomize_questions_default = QCheckBox(randomize_label)
        group_layout.addWidget(self.show_explanations_default)
        group_layout.addWidget(self.randomize_questions_default)

        points_row = QHBoxLayout()
        points_row.addWidget(QLabel(points_label))
        self.points_per_question_spin = QSpinBox()
        self.points_per_question_spin.setRange(1, 100)
        self.points_per_question_spin.setSingleStep(1)
        points_row.addWidget(self.points_per_question_spin)
        from PySide6.QtWidgets import QCheckBox as _QCheckBox
        try:
            self.auto_points_enabled_default = _QCheckBox(auto_points_label)
            points_row.addWidget(self.auto_points_enabled_default)
            def _sync_points_enabled():
                try:
                    self.points_per_question_spin.setEnabled(not self.auto_points_enabled_default.isChecked())
                except Exception:
                    pass
            self.auto_points_enabled_default.toggled.connect(_sync_points_enabled)
            _sync_points_enabled()
        except Exception:
            self.auto_points_enabled_default = None
        points_row.addStretch()
        group_layout.addLayout(points_row)

        self.time_limit_enabled_default = QCheckBox(time_limit_enabled_label)
        group_layout.addWidget(self.time_limit_enabled_default)

        group.setLayout(group_layout)
        layout.addWidget(group)
        layout.addStretch()
        tab_title = "Game Defaults"
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
            tab_title = I18n.t('settings.tabs.game_defaults', lang)
        except Exception:
            tab_title = "Game Defaults"
        self.tabs.addTab(self._wrap_scroll(tab), tab_title)

    def create_addin_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
            title = I18n.t("settings.addin.title", lang)
            status_label = I18n.t("settings.addin.status", lang)
            install_btn_label = I18n.t("settings.addin.install_btn", lang)
            open_folder_btn_label = I18n.t("settings.addin.open_folder_btn", lang)
            open_support_btn_label = I18n.t("settings.addin.open_support_btn", lang)
        except Exception:
            title = "Centralized Deployment"
            status_label = "Status:"
            install_btn_label = "Install / Update Add-in"
            open_folder_btn_label = "Open Add-in folder"
            open_support_btn_label = "Open guide"

        group = QGroupBox(title)
        group_layout = QVBoxLayout()

        try:
            from eduplay.core.ppt_vsto_addin_service import PptVstoAddinService
            svc = PptVstoAddinService(self.settings_manager)
            support_url = svc.support_url()
        except Exception:
            support_url = "https://eduplay-game.web.app/support/addin"

        self.addin_status_value = QLabel("-")
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel(status_label))
        status_row.addWidget(self.addin_status_value)
        status_row.addStretch()
        group_layout.addLayout(status_row)

        btn_row = QHBoxLayout()
        btn_install = QPushButton(install_btn_label)
        self._addin_btn_install = btn_install
        btn_open_folder = QPushButton(open_folder_btn_label)
        btn_open_support = QPushButton(open_support_btn_label)
        self._addin_btn_support = btn_open_support
        btn_install.clicked.connect(self._install_ppt_addin_manual)
        btn_open_folder.clicked.connect(self._open_ppt_addin_folder)
        btn_open_support.clicked.connect(lambda: self._open_url(support_url))
        btn_row.addWidget(btn_install)
        btn_row.addWidget(btn_open_folder)
        btn_row.addWidget(btn_open_support)
        btn_row.addStretch()
        group_layout.addLayout(btn_row)

        group.setLayout(group_layout)
        layout.addWidget(group)
        layout.addStretch()
        tab_title = "Add-in"
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
            tab_title = I18n.t("settings.tabs.addin", lang)
        except Exception:
            tab_title = "Add-in"
        self.tabs.addTab(self._wrap_scroll(tab), tab_title)

    def apply_i18n(self):
        """Apply translations to all controls after creation"""
        from eduplay.core.i18n import I18n
        lang = self.settings_manager.get_language()
        # Update language names
        names = [I18n.t('lang.en', lang), I18n.t('lang.vi', lang), I18n.t('lang.fr', lang), I18n.t('lang.es', lang), I18n.t('lang.de', lang)]
        try:
            for i, name in enumerate(names):
                if i >= self.language_combo.count():
                    break
                index = self.language_combo.model.index(i, 0)
                self.language_combo.model.setData(index, name, Qt.ItemDataRole.DisplayRole)
            current = self.language_combo.currentIndex()
            if 0 <= current < len(names):
                self.language_combo.button.setText(names[current])
        except Exception:
            pass

    def _normalized_ai_server_url(self, value: str) -> str:
        try:
            from eduplay.core.ai_service import AIService
            base = str(value or "").strip().rstrip("/")
            if not base:
                return AIService.DEFAULT_PROXY_BASE_URL
            if base in AIService.LEGACY_PROXY_BASE_URLS:
                return AIService.DEFAULT_PROXY_BASE_URL
            parsed = urlparse(base)
            if parsed.scheme in ("http", "https") and (parsed.path or "/") == "/":
                return base + "/openai/v1"
            return base
        except Exception:
            return str(value or "").strip().rstrip("/")
    
    def load_settings(self):
        """Load settings from settings manager"""
        # General settings
        language = self.settings_manager.get_language()
        language_index = {"en": 0, "vi": 1, "fr": 2, "es": 3, "de": 4}.get(language, 0)
        self.language_combo.setCurrentIndex(language_index)
        
        theme = self.settings_manager.get_theme()
        try:
            if theme == "dark":
                self.theme_combo.setCurrentIndex(0)
            else:
                self.theme_combo.setCurrentIndex(1)
        except Exception:
            pass
        
        self.autosave_check.setChecked(self.settings_manager.get("auto_save", True))
        self.autosave_interval.setValue(self.settings_manager.get("auto_save_interval", 300))
        try:
            self.notifications_system_check.setChecked(bool(self.settings_manager.get("notifications.system_enabled", True)))
            self.notifications_background_check.setChecked(bool(self.settings_manager.get("notifications.only_when_background", True)))
        except Exception:
            pass
        try:
            accessibility = self.settings_manager.get_accessibility_settings()
            self.ui_scale_spin.setValue(int(accessibility.get("ui_scale", 100)))
            self.high_contrast_check.setChecked(bool(accessibility.get("high_contrast", False)))
            self.reduce_motion_check.setChecked(bool(accessibility.get("reduce_motion", False)))
        except Exception:
            pass

        # Editor settings
        editor_settings = self.settings_manager.get_editor_settings()
        font_family = editor_settings.get("font_family", "Arial")
        font_index = self.font_family_combo.findText(font_family)
        if font_index >= 0:
            self.font_family_combo.setCurrentIndex(font_index)
        
        self.font_size_spin.setValue(editor_settings.get("font_size", 12))
        self.line_numbers_check.setChecked(editor_settings.get("show_line_numbers", True))
        self.auto_complete_check.setChecked(editor_settings.get("auto_complete", True))
        self.spell_check_check.setChecked(editor_settings.get("spell_check", True))
        
        # Game defaults
        game_defaults = self.settings_manager.get_game_defaults()
        self.quiz_time_per_question_spin.setValue(int(game_defaults.get("quiz_time_per_question", 30)))
        self.show_explanations_default.setChecked(bool(game_defaults.get("show_explanations", True)))
        self.randomize_questions_default.setChecked(bool(game_defaults.get("randomize_questions", True)))
        self.points_per_question_spin.setValue(int(game_defaults.get("points_per_question", 10)))
        try:
            if getattr(self, "auto_points_enabled_default", None) is not None:
                self.auto_points_enabled_default.setChecked(bool(game_defaults.get("auto_points_enabled", False)))
                self.points_per_question_spin.setEnabled(not self.auto_points_enabled_default.isChecked())
        except Exception:
            pass
        self.time_limit_enabled_default.setChecked(bool(game_defaults.get("time_limit_enabled", True)))
        try:
            ai_settings = self.settings_manager.get_ai_settings() or {}
        except Exception:
            ai_settings = {}
        try:
            base_url = str(ai_settings.get("server_base_url", "") or "").strip()
            self.groq_base_url_input.setText(self._normalized_ai_server_url(base_url))
        except Exception:
            pass
        try:
            self.groq_model_input.setText(str(ai_settings.get("groq_model", "") or ""))
        except Exception:
            pass
        try:
            self.groq_task_model_input.setText(str(ai_settings.get("task_model", "") or ""))
        except Exception:
            pass
        # Add-in
        try:
            from eduplay.core.ppt_vsto_addin_service import PptVstoAddinService
            status = PptVstoAddinService(self.settings_manager).detect_installed()
            if bool(status.get("installed")):
                ver = str(status.get("version", "") or "").strip()
                if ver:
                    self.addin_status_value.setText(self._t("settings.addin.status_installed_version", "Installed v{version}", version=ver))
                else:
                    self.addin_status_value.setText(self._t("settings.addin.status_installed", "Installed"))
            else:
                self.addin_status_value.setText(self._t("settings.addin.status_not_installed", "Not installed"))
        except Exception:
            addin_settings = self.settings_manager.get("ppt_addin", {}) or {}
            version = str(addin_settings.get("version", "") or "").strip()
            if version:
                self.addin_status_value.setText(self._t("settings.addin.status_installed_version", "Installed v{version}", version=version))
            else:
                self.addin_status_value.setText(self._t("settings.addin.status_not_installed", "Not installed"))
    
    def save_settings(self):
        """Save settings to settings manager"""
        # General settings
        try:
            language_code = self.language_combo.currentData() or "en"
        except Exception:
            index = self.language_combo.currentIndex()
            try:
                language_code = self.language_combo.itemData(index) or "en"
            except Exception:
                language_code = "en"
        self.settings_manager.set_language(language_code)
        
        try:
            theme = "dark" if self.theme_combo.currentIndex() == 0 else "light"
        except Exception:
            theme = "dark"
        self.settings_manager.set_theme(theme)
        self.settings_manager.set("auto_save", self.autosave_check.isChecked())
        self.settings_manager.set("auto_save_interval", self.autosave_interval.value())
        try:
            self.settings_manager.set("notifications.system_enabled", bool(self.notifications_system_check.isChecked()))
            self.settings_manager.set("notifications.only_when_background", bool(self.notifications_background_check.isChecked()))
        except Exception:
            pass
        try:
            self.settings_manager.set_accessibility_settings(
                {
                    "ui_scale": int(self.ui_scale_spin.value()),
                    "high_contrast": bool(self.high_contrast_check.isChecked()),
                    "reduce_motion": bool(self.reduce_motion_check.isChecked()),
                }
            )
        except Exception:
            pass
        
        # Editor settings
        editor_settings = {
            "font_family": self.font_family_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "show_line_numbers": self.line_numbers_check.isChecked(),
            "auto_complete": self.auto_complete_check.isChecked(),
            "spell_check": self.spell_check_check.isChecked()
        }
        self.settings_manager.set_editor_settings(editor_settings)
        
        # Game defaults
        defaults = self.settings_manager.get_game_defaults()
        defaults["quiz_time_per_question"] = int(self.quiz_time_per_question_spin.value())
        defaults["show_explanations"] = bool(self.show_explanations_default.isChecked())
        defaults["randomize_questions"] = bool(self.randomize_questions_default.isChecked())
        defaults["points_per_question"] = int(self.points_per_question_spin.value())
        try:
            if getattr(self, "auto_points_enabled_default", None) is not None:
                defaults["auto_points_enabled"] = bool(self.auto_points_enabled_default.isChecked())
        except Exception:
            pass
        defaults["time_limit_enabled"] = bool(self.time_limit_enabled_default.isChecked())
        self.settings_manager.set_game_defaults(defaults)
        try:
            ai_settings = self.settings_manager.get_ai_settings() or {}
        except Exception:
            ai_settings = {}
        try:
            ai_settings["server_base_url"] = self._normalized_ai_server_url(self.groq_base_url_input.text())
        except Exception:
            ai_settings["server_base_url"] = ""
        try:
            ai_settings["groq_model"] = str(self.groq_model_input.text() or "").strip()
        except Exception:
            ai_settings["groq_model"] = ""
        try:
            ai_settings["task_model"] = str(self.groq_task_model_input.text() or "").strip()
        except Exception:
            ai_settings["task_model"] = ""
        try:
            ai_settings["_user_set"] = True
        except Exception:
            pass
        self.settings_manager.set_ai_settings(ai_settings)
        
        # Emit signal and close
        self.settings_changed.emit()
        self.accept()

    def _copy_to_clipboard(self, text: str):
        try:
            from PySide6.QtGui import QGuiApplication
            cb = QGuiApplication.clipboard()
            if cb is not None:
                cb.setText(str(text or ""))
        except Exception:
            pass

    def _open_url(self, url: str):
        try:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(str(url or "")))
        except Exception:
            pass

    def _install_ppt_addin_manual(self):
        try:
            if getattr(self, "_addin_install_running", False):
                return
            self._addin_install_running = True
            try:
                if getattr(self, "_addin_btn_install", None):
                    self._addin_btn_install.setEnabled(False)
            except Exception:
                pass
            try:
                self.addin_status_value.setText(self._t("settings.addin.status_installing", "Installing..."))
            except Exception:
                pass

            try:
                from eduplay.core.ppt_vsto_addin_service import PptVstoAddinService
            except Exception:
                PptVstoAddinService = None

            def _do_install():
                if PptVstoAddinService is None:
                    raise RuntimeError(self._t("settings.addin.installer_unavailable", "VSTO add-in installer is not available."))
                svc = PptVstoAddinService(self.settings_manager)
                return svc.install_or_update()

            thread = QThread()
            worker = _BackgroundWorker(_do_install)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)

            def _on_finished(result, error):
                try:
                    from eduplay.core.i18n import I18n
                    lang = self.settings_manager.get_language()
                    dialog_title = self._t("settings.tabs.addin", "Add-in")
                    if error is not None:
                        self.addin_status_value.setText(self._t("settings.addin.status_install_failed", "Install failed"))
                        QMessageBox.warning(self, dialog_title, f"{error}")
                        return
                    if not isinstance(result, dict):
                        self.addin_status_value.setText(self._t("settings.addin.status_install_failed", "Install failed"))
                        QMessageBox.warning(self, dialog_title, self._t("settings.addin.unknown_error", "Unknown error"))
                        return
                    if result.get("installed"):
                        self.addin_status_value.setText(self._t(
                            "settings.addin.status_installed_version",
                            "Installed v{version}",
                            version=str(result.get("version", "") or "").strip(),
                        ))
                        title = I18n.t("settings.addin.install_done_title", lang)
                        msg = I18n.t("settings.addin.install_done_desc", lang)
                        QMessageBox.information(self, title, msg)
                    else:
                        self.addin_status_value.setText(self._t("settings.addin.status_install_failed", "Install failed"))
                        title = I18n.t("settings.addin.install_failed_title", lang)
                        details = "\n".join((result.get("errors", []) or [])[:5])
                        msg = I18n.t("settings.addin.install_failed_desc", lang, error=details or "Unknown error")
                        QMessageBox.warning(self, title, msg)
                finally:
                    try:
                        self._addin_install_running = False
                        if getattr(self, "_addin_btn_install", None):
                            self._addin_btn_install.setEnabled(True)
                    except Exception:
                        pass

            def _on_worker_finished(result, error):
                try:
                    from PySide6.QtCore import QTimer
                    try:
                        QTimer.singleShot(0, self, lambda: _on_finished(result, error))
                    except Exception:
                        QTimer.singleShot(0, lambda: _on_finished(result, error))
                except Exception:
                    try:
                        _on_finished(result, error)
                    except Exception:
                        pass

            worker.finished.connect(_on_worker_finished)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)

            self._background_threads.append(thread)
            self._background_workers.append(worker)

            def _cleanup_thread():
                try:
                    if thread in self._background_threads:
                        self._background_threads.remove(thread)
                except Exception:
                    pass
                try:
                    if worker in self._background_workers:
                        self._background_workers.remove(worker)
                except Exception:
                    pass

            thread.finished.connect(_cleanup_thread)
            thread.start()
        except Exception as e:
            try:
                self._addin_install_running = False
                if getattr(self, "_addin_btn_install", None):
                    self._addin_btn_install.setEnabled(True)
            except Exception:
                pass
            QMessageBox.warning(self, self._t("settings.tabs.addin", "Add-in"), f"{self._t('settings.addin.install_failed_title', 'Install failed')}: {e}")

    def _open_ppt_addin_folder(self):
        try:
            from eduplay.core.ppt_vsto_addin_service import PptVstoAddinService
            svc = PptVstoAddinService(self.settings_manager)
            msi_path = str(svc.msi_path() or "").strip()
            if msi_path and os.path.exists(msi_path):
                os.startfile(os.path.dirname(msi_path))
            else:
                QMessageBox.information(
                    self,
                    self._t("settings.tabs.addin", "Add-in"),
                    self._t("settings.addin.open_folder_missing", "Installer does not exist:\n{path}", path=msi_path or "-"),
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                self._t("settings.tabs.addin", "Add-in"),
                self._t("settings.addin.open_folder_failed", "Cannot open folder: {error}", error=str(e)),
            )
    
    def _on_view_credits_clicked(self):
        parent = self.parent()
        try:
            self.accept()
        except Exception:
            try:
                self.close()
            except Exception:
                pass
        try:
            if parent and hasattr(parent, "show_intro_credits"):
                parent.show_intro_credits()
        except Exception:
            pass
    
    def _download_template(self):
        try:
            from PySide6.QtWidgets import QFileDialog
            from PySide6.QtCore import Qt
            from eduplay.core.import_service import ImportService
            from eduplay.core.i18n import I18n
            from eduplay.ui.widgets.template_selection_dialog import TemplateSelectionDialog
        except Exception:
            return
        lang = self.settings_manager.get_language()
        
        # Ask for template type using custom dialog
        try:
            dialog = TemplateSelectionDialog(self, lang)
            if dialog.exec():
                template_type = dialog.get_selected_type()
            else:
                return
        except Exception:
            template_type = "general"

        try:
            title = I18n.t('help.download_template', lang)
        except Exception:
            title = "Download sample template"
        
        dlg = QFileDialog(self, title)
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        dlg.setFileMode(QFileDialog.AnyFile)
        try:
            dlg.setNameFilter("Word Document (*.docx);;Excel Spreadsheet (*.xlsx);;Text File (*.txt)")
        except Exception:
            pass
        try:
            dlg.setOption(QFileDialog.DontUseNativeDialog, True)
        except Exception:
            pass
        try:
            dlg.setWindowModality(Qt.ApplicationModal)
        except Exception:
            pass
        try:
            dlg.setStyleSheet("""
                QFileDialog, QDialog, QWidget {
                    background-color: #FFFFFF;
                    color: #101828;
                }
                QLabel { color: #101828; }
                QLineEdit, QListView, QTreeView, QAbstractItemView {
                    background-color: #FFFFFF;
                    color: #101828;
                    selection-background-color: #7F56D9;
                    selection-color: #FFFFFF;
                }
                QHeaderView::section {
                    background-color: #F2F4F7;
                    color: #101828;
                    padding: 4px 8px;
                    border: none;
                }
                QPushButton {
                    background-color: #F2F4F7;
                    color: #101828;
                    border: 1px solid #D0D5DD;
                    border-radius: 6px;
                    padding: 6px 10px;
                }
                QPushButton:hover { background-color: #EAECF0; }
            """)
        except Exception:
            pass
        if dlg.exec():
            sel = dlg.selectedFiles()
            save_path = sel[0] if sel else ""
        else:
            save_path = ""
        if not save_path:
            return
        try:
            if not os.path.splitext(save_path)[1]:
                save_path = save_path + ".docx"
        except Exception:
            if not save_path.lower().endswith(".docx"):
                save_path = save_path + ".docx"
        # Determine format
        fmt = "docx"
        if save_path.lower().endswith('.xlsx'):
            fmt = "xlsx"
        elif save_path.lower().endswith('.txt'):
            fmt = "txt"
        fmt = "docx"
        if save_path.lower().endswith('.xlsx'):
            fmt = "xlsx"
        elif save_path.lower().endswith('.txt'):
            fmt = "txt"
            
        try:
            ImportService().create_sample_template(save_path, fmt, lang, template_type)
            try:
                done_title = I18n.t('help.title', lang)
                done_msg = I18n.t('help.download_done', lang)
            except Exception:
                done_title = "Help"
                done_msg = "Sample template has been created successfully."
            QMessageBox.information(self, done_title, done_msg)
        except Exception as e:
            try:
                err_title = I18n.t('help.title', lang)
                msg = I18n.t('help.download_failed', lang)
                try:
                    msg = msg.format(error=str(e))
                except Exception:
                    pass
            except Exception:
                err_title = "Help"
                msg = f"Cannot create sample file: {str(e)}"
            QMessageBox.critical(self, err_title, msg)
    
    def reset_settings(self):
        """Reset settings to defaults"""
        try:
            from eduplay.core.i18n import I18n
            lang = self.settings_manager.get_language()
            title = I18n.t('settings.reset_confirm_title', lang)
            msg = I18n.t('settings.reset_confirm_message', lang)
            done_title = I18n.t('settings.reset_done_title', lang)
            done_msg = I18n.t('settings.reset_done_message', lang)
        except Exception:
            title = "Reset Settings"
            msg = "Are you sure you want to reset all settings to defaults?"
            done_title = "Settings Reset"
            done_msg = "Settings have been reset to defaults."
        reply = QMessageBox.question(self, title, msg, QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_to_defaults()
            self.load_settings()
            try:
                self.settings_changed.emit()
            except Exception:
                pass
            QMessageBox.information(self, done_title, done_msg)
    
    def test_groq_key(self):
        try:
            import requests
        except Exception:
            QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.ai_network_unavailable", "Cannot test the network right now. Save settings and try chatting directly in EduPlay."))
            return

        base_url = ""
        try:
            base_url = os.getenv("EDUPLAY_AI_SERVER_URL") or ""
        except Exception:
            base_url = ""
        if not base_url:
            try:
                base_url = str(self.groq_base_url_input.text() or "").strip()
            except Exception:
                base_url = ""
        base_url = str(base_url).rstrip("/")
        if not base_url:
            QMessageBox.warning(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.ai_missing_base_url", "Missing AI server Base URL."))
            return
        root_url = base_url
        if root_url.endswith("/openai/v1"):
            root_url = root_url[: -len("/openai/v1")]
        elif "/openai/v1" in root_url:
            root_url = root_url.rsplit("/openai/v1", 1)[0]
        health_url = root_url.rstrip("/") + "/health"
        try:
            resp = requests.get(health_url, timeout=10)
            if resp.status_code == 200:
                QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.ai_server_reachable", "AI server is reachable."))
                return
            if resp.status_code in (502, 503, 504):
                QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.ai_server_waking", "AI server is waking up. Please try again in a few seconds."))
                return
            QMessageBox.critical(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.ai_server_status_error", "AI server error (status {status}).", status=resp.status_code))
        except Exception as e:
            QMessageBox.critical(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.ai_server_connect_error", "Cannot connect to AI server: {error}", error=str(e)))

    def test_gemini_key(self):
        """Test Google Gemini API key"""
        # Remove all whitespace
        import re
        api_key = re.sub(r'[^a-zA-Z0-9_\-\.]', '', self.gemini_key_input.text())
        if not api_key:
            QMessageBox.warning(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.gemini_missing_key", "Please enter a Google Gemini API key."))
            return
        
        # Basic validation
        if not self.settings_manager.validate_api_key("google_gemini", api_key):
            QMessageBox.warning(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.gemini_invalid_key", "Invalid Google Gemini API key format."))
            return
        
        try:
            import google.generativeai as genai
        except Exception:
            QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.ai_key_format_valid", "API key format appears valid. Full functionality will be available when saved."))
            return
        
        genai.configure(api_key=api_key)
        try:
            selected = ""
            try:
                selected = self.model_combo.currentText().strip()
            except Exception:
                selected = ""
            candidates = []
            if selected and selected.startswith("gemini"):
                candidates.append(selected)
            candidates.extend([
                "gemini-2.5-flash-native-audio-dialog",
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash-tts",
                "gemini-3-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-2.0-flash-exp",
                "gemini-flash-lite"
            ])
            seen = set()
            ordered = []
            for name in candidates:
                if name in seen:
                    continue
                seen.add(name)
                ordered.append(name)
            last_err = None
            for model_name in ordered:
                try:
                    m = genai.GenerativeModel(model_name)
                    _ = m.generate_content("ping")
                    QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.gemini_key_valid_model", "API key is valid. Using model: {model}", model=model_name))
                    return
                except Exception as e:
                    last_err = e
                    continue
            msg = str(last_err) if last_err else "Unknown error"
            lower = msg.lower()
            if "429" in msg or "quota" in lower or "resource exhausted" in lower:
                friendly = self._t("settings.gemini_quota_exceeded", "API key is valid but quota is exceeded or the service is overloaded (code 429). Please try again later or choose a lighter model such as gemini-flash-lite.")
                QMessageBox.critical(self, self._t("settings.ai_test_failed_title", "Test Failed"), friendly)
            elif "404 models/" in msg or "not found" in lower:
                friendly = self._t("settings.gemini_model_unavailable", "The selected model is not available for this API key. Please choose a supported model, for example gemini-1.5-flash or gemini-flash-lite.")
                QMessageBox.critical(self, self._t("settings.ai_test_failed_title", "Test Failed"), friendly)
            else:
                QMessageBox.critical(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.ai_api_call_failed", "API call failed: {error}", error=msg))
        except Exception as e:
            QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.ai_key_format_valid", "API key format appears valid. Full functionality will be available when saved."))
    
    def test_openai_key(self):
        """Test OpenAI API key"""
        api_key = self.openai_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.openai_missing_key", "Please enter an OpenAI API key."))
            return
        
        # Basic validation
        if not self.settings_manager.validate_api_key("openai", api_key):
            QMessageBox.warning(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.openai_invalid_key", "Invalid OpenAI API key format."))
            return

        try:
            import requests
        except Exception:
            QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.ai_key_format_valid", "API key format appears valid. Full functionality will be available when saved."))
            return

        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
            code = resp.status_code
            if code == 200:
                QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.openai_key_valid", "API key is valid and OpenAI API is reachable."))
                return
            text = ""
            try:
                text = resp.text or ""
            except Exception:
                text = ""
            lower = text.lower()
            if code == 401:
                QMessageBox.critical(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.openai_unauthorized", "API key is invalid or not authorized. Please check the key and your OpenAI account."))
            elif code == 429 or "quota" in lower or "rate limit" in lower:
                QMessageBox.critical(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.openai_quota_exceeded", "API key is valid but quota is exceeded or rate limit reached (code 429). Please try again later or review your OpenAI billing limits."))
            else:
                preview = text[:200] if text else ""
                QMessageBox.critical(self, self._t("settings.ai_test_failed_title", "Test Failed"), self._t("settings.openai_unexpected_response", "Unexpected response from OpenAI (status {status}). {preview}", status=code, preview=preview))
        except Exception as e:
            msg = str(e)
            QMessageBox.information(self, self._t("settings.ai_test_result_title", "Test Result"), self._t("settings.openai_contact_failed", "API key format appears valid but could not contact OpenAI: {error}", error=msg))

"""
Nguyen-Thanh-Tan ¬_¬
"""
