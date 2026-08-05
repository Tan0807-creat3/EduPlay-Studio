from __future__ import annotations

import os
import sys
import json
import time
import tempfile
from typing import Dict, List, Optional, Any

try:
    if os.name == "nt":
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
except Exception:
    pass

from PySide6.QtCore import Qt, QSettings, QStandardPaths, QUrl, QThread, Signal, QEventLoop
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QFileDialog,
    QProgressBar, QFrame, QSplitter, QTabWidget, QScrollArea, QSizePolicy,
    QSpacerItem, QGridLayout, QGroupBox, QCheckBox, QRadioButton, QSpinBox,
    QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit, QListView, QListWidget,
    QTreeWidget, QHeaderView, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QAbstractScrollArea, QAbstractButton, QAbstractSlider, QAbstractSpinBox,
    QStatusBar, QToolBar,
    QMenu, QMenuBar, QDialog, QMessageBox, QWizard, QWizardPage,
    QErrorMessage
)
from PySide6.QtWidgets import QProxyStyle, QStyle
from PySide6.QtGui import (
    QAction, QActionGroup, QCursor, QFont, QFontDatabase, QIcon, QImage,
    QKeySequence, QLinearGradient, QPalette, QPixmap, QBrush, QPen, QPolygon,
    QRegion, QTransform, QValidator, QIntValidator, QDoubleValidator,
    QInputMethod, QInputMethodEvent, QInputMethodQueryEvent, QTouchEvent, QTabletEvent,
    QWheelEvent, QFocusEvent, QCloseEvent, QContextMenuEvent, QDragEnterEvent,
    QDragMoveEvent, QDragLeaveEvent, QDropEvent, QHelpEvent, QHoverEvent, QMouseEvent,
    QMoveEvent, QResizeEvent, QShowEvent, QHideEvent, QPaintEvent, QEnterEvent,
    QNativeGestureEvent, QScrollEvent, QNativeInterface, QPlatformSurfaceEvent,
    QWindow, QBackingStore, QPaintEngine, QPaintDevice
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter, QPrinterInfo
from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator, QCoreApplication

from eduplay.core.ai_service import AIService
from eduplay.core.asset_loader import load_asset_text
from eduplay.core.project_manager import ProjectManager
from eduplay.core.settings_manager import SettingsManager
from eduplay.core.asset_manager import AssetManager
from eduplay.core.import_service import ImportService
from eduplay.ui.main_window import MainWindow

class EduPlayApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("EduPlay - Studio")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("EduPlay")
        try:
            icon_path = self._get_icon_path()
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
        self.main_window = None
        self.ai_service = None
        self.splash_shown = False
    
    def _play_intro_animation(self):
        try:
            if hasattr(self, "main_window") and self.main_window:
                try:
                    if hasattr(self.main_window, "start_startup_animation"):
                        self.main_window.start_startup_animation()
                except Exception:
                    pass
        except Exception:
            pass

    def _apply_theme_stylesheet(self, settings_manager: SettingsManager) -> None:
        try:
            theme = settings_manager.get_theme() or "light"
        except Exception:
            theme = "light"
        try:
            qss_name = "dark_theme.qss" if theme == "dark" else "light_theme.qss"
            qss = load_asset_text(f"eduplay/resources/styles/{qss_name}")
            try:
                brand = settings_manager.get("brand_color", "#10B981")
                if brand and brand.startswith("#"):
                    qss = qss.replace("#7F56D9", brand)
            except Exception:
                pass
            self.setStyleSheet(qss)
        except Exception:
            pass
        try:
            from PySide6.QtGui import QFont, QFontDatabase
            fam = "Times New Roman"
            if fam in QFontDatabase.families():
                self.setFont(QFont(fam, 13))
        except Exception:
            pass

    def _maybe_prompt_language_on_first_run(self, settings_manager: SettingsManager) -> None:
        try:
            if hasattr(settings_manager, "should_run_first_time_flow"):
                first_run = bool(settings_manager.should_run_first_time_flow())
            elif getattr(settings_manager, "settings_file_existed", False):
                first_run = False
            else:
                first_run = bool(settings_manager.get("first_run", True))
        except Exception:
            first_run = False
        if not first_run:
            try:
                from eduplay.core.i18n import I18n
                I18n.set_locale(settings_manager.get_language() or "en")
            except Exception:
                pass
            return
        try:
            sys_lang = (QLocale.system().name() or "").split("_")[0].strip().lower()
        except Exception:
            sys_lang = "en"
        supported = ["en", "vi", "fr", "es", "de"]
        suggested = sys_lang if sys_lang in supported else "en"
        try:
            from eduplay.core.i18n import I18n
            I18n.set_locale(suggested)
        except Exception:
            I18n = None  # type: ignore
        try:
            from eduplay.ui.widgets.custom_dropdown import FlatDropdown
        except Exception:
            FlatDropdown = None  # type: ignore
        dlg = QDialog()
        try:
            dlg.setWindowModality(Qt.ApplicationModal)
        except Exception:
            pass
        try:
            title = I18n.t("first_run.language.title", suggested) if I18n else "Select language"
            heading = I18n.t("first_run.language.heading", suggested) if I18n else "Choose your language"
            desc = I18n.t("first_run.language.desc", suggested) if I18n else "You can change this later in Settings."
            label = I18n.t("first_run.language.label", suggested) if I18n else "Application language:"
            ok_text = I18n.t("first_run.language.continue", suggested) if I18n else "Continue"
            cancel_text = I18n.t("first_run.language.skip", suggested) if I18n else "Use default"
        except Exception:
            title = "Select language"
            heading = "Choose your language"
            desc = "You can change this later in Settings."
            label = "Application language:"
            ok_text = "Continue"
            cancel_text = "Use default"
        dlg.setWindowTitle(title)
        dlg.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #101828;
            }
            QLabel {
                color: #101828;
                background-color: transparent;
            }
            QPushButton {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: 600;
                font-size: 14px;
                min-width: 110px;
            }
            QPushButton:hover {
                background-color: #8B66E9;
            }
            QPushButton#cancel-btn {
                background-color: #F2F4F7;
                color: #344054;
                border: 1px solid #D0D5DD;
            }
            QPushButton#cancel-btn:hover {
                background-color: #E4E7EC;
            }
        """)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        title_lbl = QLabel(heading)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title_lbl)
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #667085;")
        layout.addWidget(desc_lbl)
        layout.addWidget(QLabel(label))
        if FlatDropdown:
            lang_combo = FlatDropdown()
            try:
                names = [I18n.t("lang.en", suggested), I18n.t("lang.vi", suggested), I18n.t("lang.fr", suggested), I18n.t("lang.es", suggested), I18n.t("lang.de", suggested)] if I18n else ["English", "Vietnamese", "French", "Spanish", "German"]
            except Exception:
                names = ["English", "Vietnamese", "French", "Spanish", "German"]
            for n, c in zip(names, supported):
                lang_combo.addItem(n, c)
            try:
                lang_combo.setCurrentData(suggested)
            except Exception:
                pass
        else:
            lang_combo = QComboBox()
            for c in supported:
                lang_combo.addItem(c.upper(), c)
            try:
                lang_combo.setCurrentIndex(supported.index(suggested))
            except Exception:
                pass
        layout.addWidget(lang_combo)
        actions = QHBoxLayout()
        actions.addStretch()
        cancel_btn = QPushButton(cancel_text)
        try:
            cancel_btn.setObjectName("cancel-btn")
        except Exception:
            pass
        ok_btn = QPushButton(ok_text)
        try:
            ok_btn.setDefault(True)
        except Exception:
            pass
        cancel_btn.clicked.connect(dlg.reject)
        ok_btn.clicked.connect(dlg.accept)
        actions.addWidget(cancel_btn)
        actions.addWidget(ok_btn)
        layout.addLayout(actions)
        try:
            dlg.setFixedWidth(420)
        except Exception:
            pass
        accepted = dlg.exec()
        selected = suggested
        try:
            if accepted:
                selected = lang_combo.currentData() or suggested
        except Exception:
            selected = suggested
        try:
            settings_manager.set_language(selected)
        except Exception:
            try:
                settings_manager.set("app_language", selected)
            except Exception:
                pass
        try:
            from eduplay.core.i18n import I18n
            I18n.set_locale(selected)
        except Exception:
            pass
    
    def exec(self):
        """Start the application event loop"""
        # SettingsManager MUST be constructed BEFORE AIService and shared with
        # it. If AIService is created first without a settings_manager, it builds
        # its own internal SettingsManager (inside _resolve_base_url/_device_key)
        # which writes settings.json before we reach the explicit construction.
        # The later instance would then see the file as "pre-existing" and
        # silently skip the first-time flow (language popup + onboarding), even
        # on a machine where settings.json did not exist before launch.
        settings_manager = SettingsManager()
        self.ai_service = AIService(settings_manager)

        if not self.ai_service.check_ready_fast():
            QMessageBox.critical(
                None,
                "Lỗi",
                ("Không thể chuẩn bị AI server.\n\n"
                 "Hãy kiểm tra `ai_settings.server_base_url` hoặc biến môi trường `EDUPLAY_AI_SERVER_URL`, rồi mở lại EduPlay Studio."),
            )
            sys.exit(1)

        if not self.ai_service.setup_ai():
            QMessageBox.critical(
                None,
                "Lỗi",
                "Không thể khởi tạo AI service. Hãy kiểm tra cấu hình AI server/Groq và kết nối mạng.",
            )
            sys.exit(1)
        
        try:
            self._apply_theme_stylesheet(settings_manager)
        except Exception:
            pass
        try:
            self._maybe_prompt_language_on_first_run(settings_manager)
        except Exception:
            pass
        project_manager = ProjectManager()
        asset_manager = AssetManager()
        try:
            asset_manager.scan_bundled_assets()
        except Exception:
            pass
        import_service = ImportService()

        self.main_window = MainWindow(
            project_manager=project_manager,
            ai_service=self.ai_service,
            asset_manager=asset_manager,
            settings_manager=settings_manager,
            import_service=import_service,
        )
        try:
            # Create the startup overlay before the first window paint so Home
            # does not flash briefly ahead of the intro.
            if hasattr(self.main_window, "_startup_animation_requested"):
                self.main_window._startup_animation_requested = True
        except Exception:
            pass
        self._play_intro_animation()
        try:
            self.main_window.showMaximized()
        except Exception:
            self.main_window.show()
        
        return super().exec()
    
    def _get_icon_path(self):
        """Get icon path - try multiple locations"""
        icon_paths = [
            "eduplay/resources/icons/icon.ico",
            os.path.join(os.path.dirname(__file__), "eduplay", "resources", "icons", "icon.ico"),
            os.path.join(os.path.dirname(__file__), "eduplay", "resources", "icons", "icon.png"),
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                return path
        
        return None


def main():
    """Main entry point for the application"""
    if len(sys.argv) >= 2 and sys.argv[1] == "--preview-runner":
        from eduplay.core import preview_runner
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        return preview_runner.main()
    try:
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    except Exception:
        pass
    app = EduPlayApp(sys.argv)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

"""
Nguyen-Thanh-Tan ¬_¬
"""
