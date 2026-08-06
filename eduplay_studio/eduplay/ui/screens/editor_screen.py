from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QSplitter, QPushButton, QFrame, QTextEdit, QLineEdit, 
                                QFileDialog, QMessageBox, QApplication, QStyle)
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QEvent, QSize
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect
from eduplay.core.i18n import I18n
from eduplay.core.settings_manager import SettingsManager
from eduplay.core.asset_loader import materialize_asset_file
from eduplay.core.path_resolver import PathResolver
from eduplay.ui.file_dialogs import get_open_file_name
from eduplay.ui.icon_factory import build_line_icon_pixmap, strip_icon_text
import os
import sys
import shutil
import random
import tempfile
from pathlib import Path

from eduplay.ui.widgets.editor_left_panel import EditorLeftPanel
from eduplay.ui.widgets.editor_center_panel import EditorCenterPanel
from eduplay.ui.widgets.editor_right_panel import EditorRightPanel


class EditorScreen(QWidget):
    back_requested = Signal()
    back_to_home = Signal()
    export_requested = Signal(str)  # 'html' or 'native'
    publish_requested = Signal()    # publish to web

    def __init__(self, project_manager, ai_service, import_service=None, parent=None):
        super().__init__(parent)
        self.project_manager = project_manager
        self.ai_service = ai_service
        self.import_service = import_service
        self.current_project = None
        self.current_question_index = -1
        self._unsaved_changes = False
        self._save_status_key = "saved"
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._perform_autosave)
        self.setup_ui()
        self.connect_signals()
        self.refresh_autosave_settings()
        
    def apply_theme(self, theme: str | None = None):
        t = theme or 'dark'
        self.current_theme = 'dark' if str(t).lower() == 'dark' else 'light'
        try:
            if self.current_theme == 'dark':
                splitter_bg = "#3A3A40"
            else:
                splitter_bg = "#E5E7EB"
            if hasattr(self, "main_splitter") and self.main_splitter:
                self.main_splitter.setStyleSheet(
                    f"""
                    QSplitter::handle {{
                        background-color: {splitter_bg};
                        width: 2px;
                    }}
                    QSplitter::handle:hover {{
                        background-color: #7F56D9;
                    }}
                """
                )
        except Exception:
            pass
        try:
            if self.current_theme == 'dark':
                header_bg = "rgba(27,31,42,0.65)"
                header_border = "#2A2F3A"
                title_color = "#E0E0E0"
                back_bg = "#2D3340"
                back_fg = "#E0E0E0"
                back_hover_bg = "#394150"
            else:
                header_bg = "#FFFEFA"
                header_border = "#E4E7EC"
                title_color = "#0F1728"
                back_bg = "#F5F3FF"
                back_fg = "#344054"
                back_hover_bg = "#EEE7FF"
            self._apply_header_style(pad=10, header_bg=header_bg, header_border=header_border)
            if hasattr(self, "back_btn") and self.back_btn:
                self.back_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {back_bg};
                        color: {back_fg};
                        border: 1px solid {header_border};
                        padding: 8px 14px;
                        border-radius: 10px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {back_hover_bg};
                    }}
                """
                )
                try:
                    self._apply_header_icons(back_fg)
                except Exception:
                    pass
            if hasattr(self, "project_title") and self.project_title:
                self.project_title.setStyleSheet(
                    f"""
                    QLabel {{
                        color: {title_color};
                        font-size: 18px;
                        font-weight: bold;
                        margin-left: 20px;
                    }}
                """
                )
        except Exception:
            pass
        try:
            # Check if panels exist
            has_left = getattr(self, "left_panel", None) is not None
            has_center = getattr(self, "center_panel", None) is not None
            
            # If both exist, just update theme
            if has_left and has_center:
                try:
                    if hasattr(self.left_panel, 'apply_theme'):
                        self.left_panel.apply_theme(self.current_theme)
                except Exception:
                    pass
                    
                try:
                    if hasattr(self.center_panel, 'apply_theme'):
                        self.center_panel.apply_theme(self.current_theme)
                except Exception:
                    pass
            else:
                # Recreate if missing
                old_left = getattr(self, "left_panel", None)
                old_center = getattr(self, "center_panel", None)
                sizes = []
                if hasattr(self, "main_splitter") and self.main_splitter:
                    try:
                        sizes = self.main_splitter.sizes()
                    except Exception:
                        sizes = []
                    if old_left:
                        old_left.setParent(None)
                    if old_center:
                        old_center.setParent(None)
                    self.left_panel = EditorLeftPanel()
                    self.left_panel.setMinimumWidth(240)
                    self.center_panel = EditorCenterPanel()
                    self.main_splitter.insertWidget(0, self.left_panel)
                    self.main_splitter.insertWidget(1, self.center_panel)
                    self.main_splitter.setStretchFactor(0, 1)
                    self.main_splitter.setStretchFactor(1, 2)
                    if sizes:
                        try:
                            self.main_splitter.setSizes(sizes)
                        except Exception:
                            pass
                    self.connect_signals()
                    if self.current_project:
                        try:
                            self.left_panel.set_project(self.current_project)
                        except Exception:
                            pass
                        try:
                            questions = self.current_project.get("questions", [])
                        except Exception:
                            questions = []
                        try:
                            idx = self.current_question_index
                        except Exception:
                            idx = -1
                        if isinstance(idx, int) and idx >= 0 and idx < len(questions):
                            try:
                                self.center_panel.set_question(questions[idx], idx)
                            except Exception:
                                pass
                        else:
                            try:
                                self.center_panel.set_question(None, -1)
                            except Exception:
                                pass
        except Exception:
            pass
            
        
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.header = self.create_header()
        layout.addWidget(self.header)
        
        # Main content area (remove right preview column)
        self.main_splitter = QSplitter(Qt.Horizontal)
        try:
            theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            theme = 'dark'
        self.current_theme = theme
        if self.current_theme == 'dark':
            splitter_bg = "#3A3A40"
        else:
            splitter_bg = "#E5E7EB"
        self.main_splitter.setStyleSheet(
            f"""
            QSplitter::handle {{
                background-color: {splitter_bg};
                width: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: #7F56D9;
            }}
        """
        )
        
        # Left panel (Questions, Game Config, Media)
        self.left_panel = EditorLeftPanel()
        self.left_panel.setMinimumWidth(240)
        
        # Center panel (Question editor)
        self.center_panel = EditorCenterPanel()
        
        # Add panels to splitter (left + center only)
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(self.center_panel)
        
        # Set splitter proportions: left 1/3, center 2/3
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 2)
        try:
            QTimer.singleShot(0, self._apply_splitter_sizes)
        except Exception:
            pass
        
        layout.addWidget(self.main_splitter)
        try:
            self.apply_theme(self.current_theme)
        except Exception:
            pass

    def _apply_splitter_sizes(self):
        try:
            if not hasattr(self, "main_splitter") or not self.main_splitter:
                return
            if self.main_splitter.orientation() == Qt.Horizontal:
                total = max(self.width(), 1080)
                left_width = max(360, min(430, int(total * 0.31)))
                self.main_splitter.setSizes([left_width, max(680, total - left_width)])
            else:
                total = max(self.height(), 760)
                top_height = max(260, min(340, int(total * 0.34)))
                self.main_splitter.setSizes([top_height, max(420, total - top_height)])
        except Exception:
            pass
        
    def show_toast(self, message: str, duration_ms: int = 5000, kind: str = "info"):
        try:
            if hasattr(self, '_toast_widget') and self._toast_widget:
                self._toast_widget.hide()
                self._toast_widget.deleteLater()
                self._toast_widget = None
        except Exception:
            pass
        try:
            if hasattr(self, '_toast_label') and self._toast_label:
                self._toast_label.hide()
                self._toast_label.deleteLater()
                self._toast_label = None
        except Exception:
            pass
        try:
            if hasattr(self, '_toast_close_btn') and self._toast_close_btn:
                self._toast_close_btn.hide()
                self._toast_close_btn.deleteLater()
                self._toast_close_btn = None
        except Exception:
            pass
        try:
            if hasattr(self, '_toast_icon') and self._toast_icon:
                self._toast_icon.hide()
                self._toast_icon.deleteLater()
                self._toast_icon = None
        except Exception:
            pass
        from PySide6.QtWidgets import QGraphicsDropShadowEffect, QToolButton
        from PySide6.QtGui import QColor, QPixmap
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            theme = 'dark'
        kind_value = (kind or "info").lower()
        if kind_value not in ("success", "error", "warning", "info"):
            kind_value = "info"
        if theme == 'dark':
            if kind_value == "success":
                toast_bg = "rgba(15,23,42,0.96)"
                toast_border = "rgba(22,163,74,0.85)"
                toast_fg = "#E5E7EB"
                accent = "#22C55E"
            elif kind_value == "error":
                toast_bg = "rgba(15,23,42,0.96)"
                toast_border = "rgba(248,113,113,0.9)"
                toast_fg = "#E5E7EB"
                accent = "#FB7185"
            elif kind_value == "warning":
                toast_bg = "rgba(15,23,42,0.96)"
                toast_border = "rgba(250,204,21,0.9)"
                toast_fg = "#E5E7EB"
                accent = "#FACC15"
            else:
                toast_bg = "rgba(15,23,42,0.96)"
                toast_border = "rgba(148,163,184,0.9)"
                toast_fg = "#E5E7EB"
                accent = "#38BDF8"
            shadow_color = QColor(15, 23, 42, 200)
            close_fg = "rgba(148,163,184,0.95)"
            close_hover_fg = "#FFFFFF"
        else:
            if kind_value == "success":
                toast_bg = "#ECFDF3"
                toast_border = "#BBF7D0"
                toast_fg = "#166534"
                accent = "#22C55E"
            elif kind_value == "error":
                toast_bg = "#FEF2F2"
                toast_border = "#FECACA"
                toast_fg = "#991B1B"
                accent = "#EF4444"
            elif kind_value == "warning":
                toast_bg = "#FFFBEB"
                toast_border = "#FDE68A"
                toast_fg = "#92400E"
                accent = "#F59E0B"
            else:
                toast_bg = "#EFF6FF"
                toast_border = "#BFDBFE"
                toast_fg = "#1E3A8A"
                accent = "#3B82F6"
            shadow_color = QColor(15, 23, 42, 80)
            close_fg = "rgba(71,85,105,0.92)"
            close_hover_fg = "#0F1728"
        text = message
        owner = self.window() or self
        self._toast_owner = owner
        self._toast_widget = QFrame(owner)
        self._toast_widget.setObjectName("toastWidget")
        try:
            base_w = owner.width() if owner and owner.width() > 0 else self.width()
            if base_w and base_w > 0:
                max_w = max(320, int(base_w * 0.42))
            else:
                max_w = 420
        except Exception:
            max_w = 420
        try:
            from PySide6.QtWidgets import QSizePolicy
            self._toast_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        except Exception:
            pass
        self._toast_widget.setMaximumWidth(max_w)
        layout = QHBoxLayout(self._toast_widget)
        layout.setContentsMargins(16, 12, 14, 12)
        layout.setSpacing(12)
        icon_label = QLabel(self._toast_widget)
        icon_label.setFixedSize(32, 32)
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            icon_path = os.path.join(base_dir, "resources", "icons", "notification.png")
            pix = QPixmap(icon_path)
            if not pix.isNull():
                icon_label.setPixmap(pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass
        layout.addWidget(icon_label, 0, Qt.AlignVCenter)
        self._toast_icon = icon_label
        text_label = QLabel(text, self._toast_widget)
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        text_label.setStyleSheet(
            f"""
            QLabel {{
                color: {toast_fg};
                background-color: transparent;
                font-size: 14px;
                font-weight: 500;
                letter-spacing: 0.2px;
            }}
            """
        )
        try:
            text_label.setMinimumWidth(min(280, max_w))
        except Exception:
            pass
        layout.addWidget(text_label, 1)
        self._toast_label = text_label
        self._toast_widget.setStyleSheet(
            f"""
            QFrame#toastWidget {{
                background-color: {toast_bg};
                color: {toast_fg};
                border-radius: 12px;
                border: 1px solid {toast_border};
                border-left: 5px solid {accent};
            }}
            QToolButton#toastCloseBtn {{
                background-color: transparent;
                border: none;
                color: {close_fg};
                font-size: 18px;
                font-weight: 700;
                padding: 0px;
                margin: 0px;
                border-radius: 12px;
            }}
            QToolButton#toastCloseBtn:hover {{
                background-color: rgba(148,163,184,0.16);
                color: {close_hover_fg};
            }}
            QToolButton#toastCloseBtn:pressed {{
                background-color: rgba(148,163,184,0.28);
            }}
        """
        )
        try:
            self._toast_close_btn = QToolButton(self._toast_widget)
            self._toast_close_btn.setObjectName("toastCloseBtn")
            self._toast_close_btn.setCursor(Qt.PointingHandCursor)
            self._toast_close_btn.setFixedSize(26, 26)
            self._toast_close_btn.setAutoRaise(True)
            try:
                self._toast_close_btn.setText("×")
            except Exception:
                pass
            try:
                self._toast_close_btn.setFocusPolicy(Qt.NoFocus)
            except Exception:
                pass
        except Exception:
            self._toast_close_btn = None
        try:
            opacity_effect = QGraphicsOpacityEffect(self._toast_widget)
            opacity_effect.setOpacity(0.0)
            self._toast_widget.setGraphicsEffect(opacity_effect)
            self._toast_opacity_effect = opacity_effect
        except Exception:
            self._toast_opacity_effect = None
        self._position_toast()
        try:
            target = self._toast_widget if hasattr(self, '_toast_widget') and self._toast_widget else self._toast_label
        except Exception:
            target = getattr(self, '_toast_label', None)
        if not target:
            return
        end_pos = target.pos()
        def _place_close_btn():
            try:
                if not getattr(self, "_toast_widget", None) or not getattr(self, "_toast_close_btn", None):
                    return
                m = 8
                self._toast_widget.adjustSize()
                self._toast_close_btn.move(self._toast_widget.width() - self._toast_close_btn.width() - m, m)
                self._toast_close_btn.raise_()
            except Exception:
                pass
        try:
            start_pos = QPoint(end_pos.x(), end_pos.y() + 40)
            target.move(start_pos)
            target.show()
            target.raise_()
            try:
                if self._toast_close_btn:
                    _place_close_btn()
            except Exception:
                pass
            try:
                if hasattr(self, '_toast_anim') and self._toast_anim:
                    self._toast_anim.stop()
            except Exception:
                pass
            try:
                if hasattr(self, "_toast_anim_group") and self._toast_anim_group:
                    self._toast_anim_group.stop()
            except Exception:
                pass
            self._toast_anim = QPropertyAnimation(target, b"pos", self)
            self._toast_anim.setDuration(260)
            self._toast_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._toast_anim.setStartValue(start_pos)
            self._toast_anim.setEndValue(end_pos)
            opacity_effect = getattr(self, "_toast_opacity_effect", None)
            if opacity_effect is not None:
                self._toast_opacity_anim = QPropertyAnimation(opacity_effect, b"opacity", self)
                self._toast_opacity_anim.setDuration(220)
                self._toast_opacity_anim.setEasingCurve(QEasingCurve.OutCubic)
                self._toast_opacity_anim.setStartValue(0.0)
                self._toast_opacity_anim.setEndValue(1.0)
                self._toast_anim_group = QParallelAnimationGroup(self)
                self._toast_anim_group.addAnimation(self._toast_anim)
                self._toast_anim_group.addAnimation(self._toast_opacity_anim)
                self._toast_anim_group.start()
            else:
                self._toast_anim_group = None
                self._toast_anim.start()
        except Exception:
            target.show()
            target.raise_()
        try:
            _place_close_btn()
        except Exception:
            pass
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.setInterval(max(duration_ms, 5000))

        def _cleanup_toast():
            try:
                if hasattr(self, '_toast_widget') and self._toast_widget:
                    self._toast_widget.hide()
                    self._toast_widget.deleteLater()
                    self._toast_widget = None
            except Exception:
                pass
            try:
                if hasattr(self, '_toast_label') and self._toast_label:
                    self._toast_label.hide()
                    self._toast_label.deleteLater()
                    self._toast_label = None
            except Exception:
                pass
            try:
                if hasattr(self, '_toast_close_btn') and self._toast_close_btn:
                    self._toast_close_btn.hide()
                    self._toast_close_btn.deleteLater()
                    self._toast_close_btn = None
            except Exception:
                pass
            try:
                if hasattr(self, '_toast_icon') and self._toast_icon:
                    self._toast_icon.hide()
                    self._toast_icon.deleteLater()
                    self._toast_icon = None
            except Exception:
                pass
            try:
                if hasattr(self, '_toast_anim') and self._toast_anim:
                    self._toast_anim.stop()
                    self._toast_anim.deleteLater()
                    self._toast_anim = None
            except Exception:
                pass
            try:
                if hasattr(self, '_toast_hide_anim') and self._toast_hide_anim:
                    self._toast_hide_anim.stop()
                    self._toast_hide_anim.deleteLater()
                    self._toast_hide_anim = None
            except Exception:
                pass
            try:
                if hasattr(self, '_toast_timer') and self._toast_timer:
                    self._toast_timer.stop()
                    self._toast_timer.deleteLater()
                    self._toast_timer = None
            except Exception:
                pass

        def hide_toast():
            try:
                target = None
                if hasattr(self, '_toast_widget') and self._toast_widget:
                    target = self._toast_widget
                elif hasattr(self, '_toast_label') and self._toast_label:
                    target = self._toast_label
            except Exception:
                target = None
            if not target:
                _cleanup_toast()
                return
            try:
                start_pos = target.pos()
                end_pos = QPoint(start_pos.x(), start_pos.y() + 40)
                try:
                    if hasattr(self, '_toast_hide_anim') and self._toast_hide_anim:
                        self._toast_hide_anim.stop()
                except Exception:
                    pass
                self._toast_hide_anim = QPropertyAnimation(target, b"pos", self)
                self._toast_hide_anim.setDuration(220)
                self._toast_hide_anim.setEasingCurve(QEasingCurve.InCubic)
                self._toast_hide_anim.setStartValue(start_pos)
                self._toast_hide_anim.setEndValue(end_pos)
                opacity_effect = getattr(self, "_toast_opacity_effect", None)
                if opacity_effect is not None:
                    self._toast_hide_opacity_anim = QPropertyAnimation(opacity_effect, b"opacity", self)
                    self._toast_hide_opacity_anim.setDuration(180)
                    self._toast_hide_opacity_anim.setEasingCurve(QEasingCurve.InCubic)
                    self._toast_hide_opacity_anim.setStartValue(float(opacity_effect.opacity()))
                    self._toast_hide_opacity_anim.setEndValue(0.0)
                    self._toast_hide_anim_group = QParallelAnimationGroup(self)
                    self._toast_hide_anim_group.addAnimation(self._toast_hide_anim)
                    self._toast_hide_anim_group.addAnimation(self._toast_hide_opacity_anim)
                    self._toast_hide_anim_group.finished.connect(_cleanup_toast)
                    self._toast_hide_anim_group.start()
                else:
                    try:
                        self._toast_hide_anim.finished.connect(_cleanup_toast)
                    except Exception:
                        pass
                    self._toast_hide_anim.start()
            except Exception:
                _cleanup_toast()

        self._toast_timer.timeout.connect(hide_toast)
        try:
            if self._toast_close_btn:
                self._toast_close_btn.clicked.connect(hide_toast)
        except Exception:
            pass
        self._toast_timer.start()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            w = self.width()
            if hasattr(self, 'main_splitter'):
                if w < 1000:
                    changed_orientation = self.main_splitter.orientation() != Qt.Vertical
                    self.main_splitter.setOrientation(Qt.Vertical)
                    try:
                        self.left_panel.setMinimumHeight(200)
                        self.center_panel.setMinimumHeight(300)
                    except Exception:
                        pass
                    if changed_orientation:
                        self._apply_splitter_sizes()
                else:
                    changed_orientation = self.main_splitter.orientation() != Qt.Horizontal
                    self.main_splitter.setOrientation(Qt.Horizontal)
                    try:
                        self.left_panel.setMinimumWidth(320)
                    except Exception:
                        pass
                    if changed_orientation:
                        self._apply_splitter_sizes()
            toast_target = None
            if hasattr(self, '_toast_widget') and getattr(self, '_toast_widget', None):
                toast_target = self._toast_widget
            elif hasattr(self, '_toast_label') and getattr(self, '_toast_label', None):
                toast_target = self._toast_label
            if toast_target and toast_target.isVisible():
                self._position_toast()
            self._apply_header_style(pad=8)
            if hasattr(self, 'project_title'):
                f = self.project_title.font()
                f.setPointSize(18)
                self.project_title.setFont(f)
            if self.main_splitter.orientation() == Qt.Horizontal:
                self._apply_splitter_sizes()
            if hasattr(self, 'zoom_combo'):
                self.zoom_combo.setMinimumWidth(90)
            base = 42
            for btn in [getattr(self, 'back_btn', None), getattr(self, 'save_btn', None), getattr(self, 'preview_btn', None), getattr(self, 'export_web_btn', None), getattr(self, 'export_html_btn', None)]:
                if btn:
                    btn.setFixedHeight(base)
        except Exception:
            pass

    def _position_toast(self):
        try:
            target = None
            if hasattr(self, '_toast_widget') and self._toast_widget:
                target = self._toast_widget
            elif hasattr(self, '_toast_label') and self._toast_label:
                target = self._toast_label
            if not target:
                return
            owner = getattr(self, '_toast_owner', None)
            if owner is None:
                owner = self.window() or self
            geo = owner.rect()
            try:
                target.adjustSize()
            except Exception:
                pass
            w = target.width()
            h = target.height()
            margin = 24
            x = geo.right() - w - margin
            y = geo.bottom() - h - margin
            try:
                btn = getattr(owner, "_chat_toggle_btn", None)
                if btn is not None:
                    btn_geo = btn.geometry()
                    from PySide6.QtCore import QRect
                    toast_rect = QRect(x, y, w, h)
                    overlap_rect = btn_geo.adjusted(-14, -14, 14, 14)
                    if toast_rect.intersects(overlap_rect):
                        x = btn_geo.left() - w - (margin // 2)
                        if x < margin:
                            x = margin
                            y = btn_geo.top() - h - (margin // 2)
            except Exception:
                pass
            if x < margin:
                x = margin
            if y < margin:
                y = margin
            target.move(x, y)
            target.raise_()
        except Exception:
            pass

    def set_scale(self, scale: float):
        try:
            try:
                theme = SettingsManager().get_theme() or 'dark'
            except Exception:
                theme = 'dark'
            if theme == 'dark':
                header_bg = "rgba(27,31,42,0.65)"
                header_border = "#2A2F3A"
            else:
                header_bg = "#FFFFFF"
                header_border = "#CBD5E1"
            self._apply_header_style(pad=int(8 * scale), header_bg=header_bg, header_border=header_border)
            if hasattr(self, 'project_title'):
                f = self.project_title.font()
                f.setPointSize(18)
                self.project_title.setFont(f)
            if hasattr(self, 'zoom_combo'):
                self.zoom_combo.setMinimumWidth(90)
            base = 42
            for btn in [getattr(self, 'back_btn', None), getattr(self, 'save_btn', None), getattr(self, 'preview_btn', None), getattr(self, 'export_web_btn', None), getattr(self, 'export_html_btn', None)]:
                if btn:
                    btn.setFixedHeight(base)
        except Exception:
            pass

    def _build_action_icon_pixmap(self, kind: str, color_hex: str, size: int, stroke_width: float = 1.6) -> QPixmap:
        return build_line_icon_pixmap(kind, color_hex, size, stroke_width=stroke_width)

    def _header_action_icon(self, kind: str) -> QIcon:
        try:
            icon_rel = {
                "preview": "eduplay/resources/icons/screen.png",
                "web": "eduplay/resources/icons/computer.png",
                "export": "eduplay/resources/icons/presentation.png",
            }.get(str(kind or "").lower())
            if icon_rel:
                icon_path = materialize_asset_file(icon_rel)
                if icon_path:
                    icon = QIcon(str(icon_path))
                    if not icon.isNull():
                        return icon
        except Exception:
            pass
        try:
            if str(kind or "").lower() == "save":
                icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
                if not icon.isNull():
                    return icon
        except Exception:
            pass
        return QIcon(self._build_action_icon_pixmap(kind, "#111827", 16, stroke_width=1.5))

    def _button_text(self, text: str | None) -> str:
        return strip_icon_text(text)

    def _apply_header_icons(self, back_color: str):
        icon_px = 16
        try:
            if hasattr(self, "back_btn") and self.back_btn:
                self.back_btn.setIcon(QIcon(self._build_action_icon_pixmap("back", back_color, icon_px)))
                self.back_btn.setIconSize(QSize(icon_px, icon_px))
        except Exception:
            pass
        for attr_name, kind in (
            ("save_btn", "save"),
            ("preview_btn", "preview"),
            ("export_web_btn", "web"),
            ("export_html_btn", "export"),
        ):
            try:
                btn = getattr(self, attr_name, None)
                if btn:
                    btn.setIcon(self._header_action_icon(kind))
                    btn.setIconSize(QSize(icon_px, icon_px))
            except Exception:
                pass

    def create_header(self):
        header = QWidget()
        header.setObjectName("EditorHeader")
        try:
            theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            theme = 'dark'
        if theme == 'dark':
            header_bg = "rgba(27,31,42,0.65)"
            header_border = "#2A2F3A"
            title_color = "#E0E0E0"
            back_bg = "#2D3340"
            back_fg = "#E0E0E0"
            back_hover_bg = "#394150"
        else:
            header_bg = "#FFFEFA"
            header_border = "#E4E7EC"
            title_color = "#0F1728"
            back_bg = "#F5F3FF"
            back_fg = "#344054"
            back_hover_bg = "#EEE7FF"
        header.setStyleSheet(
            f"""
            QWidget#EditorHeader {{
                background-color: {header_bg};
                border-bottom: 1px solid {header_border};
                padding: 12px;
            }}
        """
        )
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 12, 28, 12)
        
        # Back button
        lang = SettingsManager().get_language()
        self.back_btn = QPushButton(self._button_text(I18n.t('editor.back', lang)))
        self.back_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {back_bg};
                color: {back_fg};
                border: 1px solid {header_border};
                padding: 10px 16px;
                border-radius: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {back_hover_bg};
                color: {back_fg};
            }}
        """
        )
        try:
            self.back_btn.setIcon(QIcon(self._build_action_icon_pixmap("back", back_fg, 16)))
            self.back_btn.setIconSize(QSize(16, 16))
        except Exception:
            pass
        self.back_btn.clicked.connect(self.back_to_home.emit)
        layout.addWidget(self.back_btn)
        
        # Project title
        self.project_title = QLabel(I18n.t('editor.no_project_loaded', lang))
        self.project_title.setStyleSheet(
            f"""
            QLabel {{
                color: {title_color};
                background-color: transparent;
                font-size: 18px;
                font-weight: bold;
                margin-left: 20px;
                padding: 0px;
            }}
        """
        )
        try:
            self.project_title.setWordWrap(False)
            self.project_title.setMinimumHeight(42)
            self.project_title.setMaximumHeight(42)
            self.project_title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        except Exception:
            pass
        layout.addWidget(self.project_title)

        self.save_status_label = QLabel("")
        self.save_status_label.setObjectName("EditorSaveStatus")
        self.save_status_label.setMinimumHeight(32)
        self.save_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.save_status_label)

        layout.addStretch()

        # Action buttons
        icon_px = 16
        self.save_btn = QPushButton(self._button_text(I18n.t('editor.save', lang)))
        try:
            self.save_btn.setIcon(self._header_action_icon("save"))
            self.save_btn.setIconSize(QSize(icon_px, icon_px))
        except Exception:
            pass
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #12B76A;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0F9C5A;
                color: #FFFFFF;
            }
        """)
        self.save_btn.clicked.connect(self.save_project)
        layout.addWidget(self.save_btn)
        
        # Preview button (open preview window on demand)
        try:
            preview_text = I18n.t('editor.preview_title', lang)
        except Exception:
            preview_text = "Preview"
        self.preview_btn = QPushButton(self._button_text(preview_text))
        try:
            self.preview_btn.setIcon(self._header_action_icon("preview"))
            self.preview_btn.setIconSize(QSize(icon_px, icon_px))
        except Exception:
            pass
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
                color: #FFFFFF;
            }
        """)
        self.preview_btn.clicked.connect(self.open_preview_window)
        layout.addWidget(self.preview_btn)
        try:
            lang = SettingsManager().get_language() or 'en'
        except Exception:
            lang = 'en'
        try:
            export_web_text = I18n.t('editor.export_web', lang)
        except Exception:
            export_web_text = "Export Web"
        self.export_web_btn = QPushButton(self._button_text(export_web_text))
        try:
            self.export_web_btn.setIcon(self._header_action_icon("web"))
            self.export_web_btn.setIconSize(QSize(icon_px, icon_px))
        except Exception:
            pass
        self.export_web_btn.setStyleSheet("QPushButton { background-color:#3B82F6; color:#fff; border:none; padding:8px 16px; border-radius:10px; font-weight:bold; } QPushButton:hover { background-color:#2563EB; color:#fff; }")
        self.export_web_btn.clicked.connect(self.on_export_web)
        layout.addWidget(self.export_web_btn)
        try:
            export_html_text = I18n.t('editor.export_html_internal', lang)
        except Exception:
            export_html_text = "Export HTML"
        self.export_html_btn = QPushButton(self._button_text(export_html_text))
        try:
            self.export_html_btn.setIcon(self._header_action_icon("export"))
            self.export_html_btn.setIconSize(QSize(icon_px, icon_px))
        except Exception:
            pass
        self.export_html_btn.setStyleSheet("QPushButton { background-color:#F79009; color:#fff; border:none; padding:8px 16px; border-radius:10px; font-weight:bold; } QPushButton:hover { background-color:#E68008; color:#fff; }")
        self.export_html_btn.clicked.connect(self.on_export_html)
        layout.addWidget(self.export_html_btn)
        try:
            base_h = 42
            for btn in [self.back_btn, self.save_btn, self.preview_btn, self.export_web_btn, self.export_html_btn]:
                if not btn:
                    continue
                btn.setMinimumHeight(base_h)
                btn.setMaximumHeight(base_h)
        except Exception:
            pass
        try:
            self._apply_header_icons(back_fg)
        except Exception:
            pass
        self._update_save_status_label()
        
        try:
            from PySide6.QtWidgets import QGraphicsDropShadowEffect
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(24)
            shadow.setOffset(0, 4)
            header.setGraphicsEffect(shadow)
        except Exception:
            pass
        return header

    def _apply_header_style(self, pad: int = 10, header_bg: str | None = None, header_border: str | None = None):
        try:
            if not hasattr(self, "header") or not self.header:
                return
            if header_bg is None or header_border is None:
                try:
                    theme = SettingsManager().get_theme() or 'dark'
                except Exception:
                    theme = 'dark'
                if theme == 'dark':
                    header_bg = "rgba(27,31,42,0.65)"
                    header_border = "#2A2F3A"
                else:
                    header_bg = "#FFFEFA"
                    header_border = "#E4E7EC"
            self.header.setStyleSheet(
                f"""
                QWidget#EditorHeader {{
                    background-color: {header_bg};
                    border-bottom: 1px solid {header_border};
                }}
                """
            )
            try:
                lay = self.header.layout()
                if lay:
                    pad = max(6, int(pad))
                    lay.setContentsMargins(24, pad, 24, pad)
                header_h = 42 + (max(6, int(pad)) * 2)
                self.header.setMinimumHeight(header_h)
                self.header.setMaximumHeight(header_h)
            except Exception:
                pass
            try:
                if hasattr(self, "project_title") and self.project_title:
                    self.project_title.setStyleSheet(
                        """
                        QLabel {
                            color: #101828;
                            background-color: transparent;
                            font-size: 17px;
                            font-weight: 700;
                            margin-left: 16px;
                            padding: 0px;
                        }
                        """
                        if (header_bg == "#FFFEFA")
                        else
                        """
                        QLabel {
                            color: #E0E0E0;
                            background-color: transparent;
                            font-size: 17px;
                            font-weight: 700;
                            margin-left: 16px;
                            padding: 0px;
                        }
                        """
                    )
            except Exception:
                pass
        except Exception:
            pass

    def _status_text(self, key: str) -> str:
        try:
            lang = SettingsManager().get_language() or "en"
        except Exception:
            lang = "en"
        mapping = {
            "saved": ("Đã lưu", "Saved"),
            "saving": ("Đang lưu...", "Saving..."),
            "error": ("Lỗi lưu", "Save error"),
            "dirty": ("Chưa lưu", "Unsaved"),
        }
        vi, en = mapping.get(str(key or "saved"), mapping["saved"])
        return vi if str(lang).lower().startswith("vi") else en

    def _update_save_status_label(self):
        try:
            label = getattr(self, "save_status_label", None)
            if label is None:
                return
            key = str(getattr(self, "_save_status_key", "saved") or "saved")
            color_map = {
                "saved": ("#ECFDF3", "#027A48"),
                "saving": ("#EFF8FF", "#175CD3"),
                "error": ("#FEF3F2", "#D92D20"),
                "dirty": ("#FFF7ED", "#B54708"),
            }
            bg, fg = color_map.get(key, color_map["saved"])
            label.setText(self._status_text(key))
            label.setStyleSheet(
                f"""
                QLabel#EditorSaveStatus {{
                    background-color: {bg};
                    color: {fg};
                    border: 1px solid rgba(15, 23, 40, 0.08);
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 800;
                    margin-left: 14px;
                    margin-right: 10px;
                }}
                """
            )
        except Exception:
            pass

    def _set_save_status(self, key: str):
        self._save_status_key = str(key or "saved")
        self._update_save_status_label()

    def refresh_autosave_settings(self):
        try:
            enabled = bool(SettingsManager().get("auto_save", True))
        except Exception:
            enabled = True
        try:
            interval_sec = int(SettingsManager().get("auto_save_interval", 300))
        except Exception:
            interval_sec = 300
        self._autosave_enabled = enabled
        self._autosave_interval_ms = max(30, interval_sec) * 1000
        try:
            self._autosave_timer.stop()
        except Exception:
            pass
        if self._autosave_enabled and getattr(self, "_unsaved_changes", False):
            try:
                self._autosave_timer.start(self._autosave_interval_ms)
            except Exception:
                pass

    def _perform_autosave(self):
        if not getattr(self, "_autosave_enabled", True):
            return
        if not getattr(self, "_unsaved_changes", False):
            return
        self.save_project(silent=True, autosave=True)

    def connect_signals(self):
        """Connect signals between panels"""
        # Left panel signals
        self.left_panel.question_selected.connect(self.on_question_selected)
        self.left_panel.game_config_changed.connect(self.on_game_config_changed)
        try:
            if hasattr(self.left_panel, "question_settings_applied"):
                self.left_panel.question_settings_applied.connect(self.on_question_settings_applied)
        except Exception:
            pass
        try:
            if hasattr(self.left_panel, 'import_questions_requested'):
                self.left_panel.import_questions_requested.connect(self.on_import_questions)
        except Exception:
            pass
        try:
            if hasattr(self.left_panel, "delete_question_requested"):
                self.left_panel.delete_question_requested.connect(self.on_delete_selected_question_requested)
        except Exception:
            pass
        try:
            if hasattr(self.left_panel, "preview_question_requested"):
                self.left_panel.preview_question_requested.connect(self.on_preview_selected_question_requested)
        except Exception:
            pass
        
        # Center panel signals  
        self.center_panel.question_updated.connect(self.on_question_updated)
        try:
            self._unsaved_changes = False
            self.center_panel.unsaved_changed.connect(self._on_unsaved_changed)
        except Exception:
            self._unsaved_changes = False
        try:
            if hasattr(self.center_panel, "quick_preview_requested"):
                self.center_panel.quick_preview_requested.connect(self.on_quick_preview_current_question_requested)
        except Exception:
            pass
        
        # Connect game config updates from center panel
        try:
            if hasattr(self.center_panel, 'game_config_updated'):
                self.center_panel.game_config_updated.connect(self.on_game_config_changed)
        except Exception:
            pass
        
        # Preview/export actions handled by bottom action bar
        
    def load_project(self, project):
        """Load a project into the editor"""
        self.current_project = project
        self._unsaved_changes = False
        self._set_save_status("saved")
        self.refresh_autosave_settings()
        self.project_title.setText(project.get('name', 'Untitled Project'))
        
        # Load project data into panels
        self.left_panel.set_project(project)
        try:
            if hasattr(self.center_panel, "load_project"):
                self.center_panel.load_project(project)
            else:
                cfg = project.get('game_config', {}) or {}
                if hasattr(self.center_panel, 'load_game_config'):
                    self.center_panel.load_game_config(cfg)
                if hasattr(self.center_panel, '_force_hide_question_type_if_millionaire'):
                    self.center_panel._force_hide_question_type_if_millionaire()
        except Exception:
            pass
        self.center_panel.set_question(None, -1)
        
        # Giữ nguyên các nút “Xem trước” hiển thị bình thường cho mọi game
        try:
            if hasattr(self, 'preview_btn'):
                self.preview_btn.setEnabled(True)
        except Exception:
            pass

    def _apply_game_config_to_project(self, config: dict, persist: bool = True):
        if not self.current_project:
            return
        if not isinstance(config, dict):
            config = {}
        merged_config = dict(self.current_project.get('game_config') or {})
        merged_config.update(config)
        self.current_project['game_config'] = merged_config
        try:
            gt_text = str(merged_config.get('game_type') or '')
            if hasattr(self, 'center_panel') and self.center_panel and hasattr(self.center_panel, 'on_game_type_changed'):
                self.center_panel.on_game_type_changed(gt_text)
        except Exception:
            pass
        top_gt = str(self.current_project.get('game_type') or '').lower()
        if top_gt == 'fishing':
            self.current_project['game_config']['game_type'] = 'Fishing Game'
            try:
                fish_objects = self.current_project['game_config'].get('fish_objects')
                if not fish_objects:
                    base = 'assets/kenney_platformer-kit/PNG/Default'
                    fishes = [
                        {'sprite': f'{base}/fish_blue.png', 'wrong_sprite': f'{base}/fish_blue_skeleton.png', 'sound': ''},
                        {'sprite': f'{base}/fish_green.png', 'wrong_sprite': f'{base}/fish_green_skeleton.png', 'sound': ''},
                        {'sprite': f'{base}/fish_orange.png', 'wrong_sprite': f'{base}/fish_orange_skeleton.png', 'sound': ''},
                        {'sprite': f'{base}/fish_pink.png', 'wrong_sprite': f'{base}/fish_pink_skeleton.png', 'sound': ''},
                        {'sprite': f'{base}/fish_red.png', 'wrong_sprite': f'{base}/fish_red_skeleton.png', 'sound': ''},
                    ]
                    self.current_project['game_config'].update({
                        'fish_speed': self.current_project['game_config'].get('fish_speed', 5),
                        'fish_objects': fishes,
                        'background_music': self.current_project['game_config'].get('background_music', 'assets/sound/background.mp3'),
                        'correct_sound': self.current_project['game_config'].get('correct_sound', 'assets/sound/correct.wav'),
                        'wrong_sound': self.current_project['game_config'].get('wrong_sound', 'assets/sound/wrong.wav')
                    })
            except Exception:
                pass
        elif top_gt in ('quiz_millionaire','millionaire','ai la trieu phu'):
            self.current_project['game_config']['game_type'] = 'Ai là triệu phú'
            self.current_project['force_variant'] = 'millionaire'
            try:
                cfg = self.current_project.get('game_config', {}) or {}
                if 'question_time' not in cfg:
                    cfg['question_time'] = 30
                if 'points_per_question' not in cfg:
                    cfg['points_per_question'] = 1000
                if 'lifelines_enabled' not in cfg:
                    cfg['lifelines_enabled'] = True
                self.current_project['game_config'] = cfg
            except Exception:
                pass
        else:
            self.current_project['game_config']['game_type'] = 'Trắc nghiệm cổ điển'

        if not persist:
            return
        try:
            self.project_manager.save_project(self.current_project)
        except Exception:
            pass
        try:
            if self.project_manager:
                self.project_manager.update_game_config(self.current_project['game_config'])
        except Exception:
            pass

    def _is_current_preview_process(self, proc) -> bool:
        try:
            return getattr(self, "_preview_process", None) is proc
        except Exception:
            return False

    def _handle_preview_process_finished(self, proc, code, hide_callback, fail_callback, details: str = ""):
        if not EditorScreen._is_current_preview_process(self, proc):
            return
        try:
            self._preview_process = None
        except Exception:
            pass
        try:
            exit_code = int(code) if code is not None else 0
        except Exception:
            exit_code = 0
        if exit_code != 0:
            fail_callback(details)
            return
        hide_callback()

    def _handle_preview_process_error(self, proc, fail_callback, details: str = ""):
        if not EditorScreen._is_current_preview_process(self, proc):
            return
        fail_callback(details or "Process error")

    @staticmethod
    def _should_use_preview_placeholder(preview_mode: str) -> bool:
        mode = str(preview_mode or "full").strip().lower()
        return mode != "quick"

    @staticmethod
    def _format_quick_preview_question_text(question_text: str, question_number: int, lang: str) -> str:
        try:
            import re
            from eduplay.core.i18n import I18n
            prefix = I18n.t("editor.question_prefix", lang)
        except Exception:
            prefix = None
        if not prefix:
            prefix = "Câu" if (str(lang or "").strip().lower().startswith("vi")) else "Question"
        try:
            raw = str(question_text or "")
            cleaned = re.sub(
                r'^(?:\s*(?:(?:câu|cau|question|q)\s*(?:hỏi|hoi)?(?:\s+số)?\s*\d+\s*[:.\-]?\s*)+)',
                '',
                raw,
                flags=re.IGNORECASE,
            )
            return f"{prefix} {question_number}: {cleaned}"
        except Exception:
            return str(question_text or "")

    @staticmethod
    def _render_preview_output_file(
        current_project: dict,
        preview_dir: Path,
        safe_name: str,
        suffix: str,
        out_file: Path,
        preview_mode: str,
    ) -> None:
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        ok = svc.export_to_html(
            current_project,
            str(preview_dir),
            bundle_resources=True,
            single_file=True,
            output_filename=(safe_name + suffix),
        )
        if (not ok) or (not out_file.exists()):
            bundled = svc._bundle_media_files(current_project)
            html = svc._generate_html_content(bundled)
            out_file.write_text(html, encoding="utf-8")
        if str(preview_mode or "").strip().lower() == "quick" and out_file.exists():
            from eduplay.core.preview_utils import inject_quick_preview_autostart

            preview_html = out_file.read_text(encoding="utf-8")
            out_file.write_text(
                inject_quick_preview_autostart(preview_html),
                encoding="utf-8",
            )

    def open_preview_window(self, preview_mode: str = "full"):
        try:
            from PySide6.QtCore import QUrl, QTimer, QProcess
            from PySide6.QtWidgets import QApplication
            from eduplay.core.export_service import ExportService
            from eduplay.core.settings_manager import SettingsManager
            import copy
            try:
                from eduplay.core.i18n import I18n
                lang = SettingsManager().get_language() or 'en'
            except Exception:
                I18n = None
                lang = 'en'
            preview_mode = str(preview_mode or "full").strip().lower()
            if preview_mode not in ("quick", "full"):
                preview_mode = "full"

            try:
                import webview  # noqa: F401
            except Exception:
                try:
                    self.show_toast("Thiếu pywebview. Cài: pip install pywebview pythonnet PyQt5", kind="error")
                except Exception:
                    pass
                return

            overlay_owner = None
            try:
                win = self.window()
                if win and hasattr(win, "_show_loading") and hasattr(win, "_hide_loading"):
                    overlay_owner = win
                else:
                    win2 = QApplication.activeWindow()
                    if win2 and hasattr(win2, "_show_loading") and hasattr(win2, "_hide_loading"):
                        overlay_owner = win2
            except Exception:
                overlay_owner = None

            try:
                if preview_mode == "quick":
                    loading_msg = I18n.t('editor.loading_quick_preview', lang) if I18n else ("Đang mở xem nhanh..." if lang == "vi" else "Opening quick preview...")
                else:
                    loading_msg = I18n.t('editor.loading_preview', lang) if I18n else ("Đang mở xem trước..." if lang == "vi" else "Opening preview...")
            except Exception:
                loading_msg = "Đang mở xem nhanh..." if (lang == "vi" and preview_mode == "quick") else ("Opening quick preview..." if preview_mode == "quick" else ("Đang mở xem trước..." if lang == "vi" else "Opening preview..."))

            try:
                self.show_toast(loading_msg, kind="info")
            except Exception:
                pass

            try:
                if overlay_owner and hasattr(overlay_owner, "_show_loading"):
                    overlay_owner._show_loading(loading_msg, "default")
            except Exception:
                pass
            try:
                QApplication.processEvents()
            except Exception:
                pass

            def _run():
                try:
                    current_project = copy.deepcopy(self.current_project or {})
                    if not current_project:
                        try:
                            if overlay_owner and hasattr(overlay_owner, "_hide_loading"):
                                overlay_owner._hide_loading()
                        except Exception:
                            pass
                        try:
                            self.show_toast("Chưa có dự án để xem trước.", kind="warning")
                        except Exception:
                            pass
                        return

                    try:
                        idx = int(getattr(self, "current_question_index", -1))
                    except Exception:
                        idx = -1
                    try:
                        if idx >= 0 and hasattr(self.center_panel, "get_question_data"):
                            questions = current_project.get("questions", [])
                            if isinstance(questions, list) and idx < len(questions):
                                qd = self.center_panel.get_question_data()
                                if isinstance(qd, dict):
                                    if isinstance(questions[idx], dict) and "id" in questions[idx] and "id" not in qd:
                                        qd["id"] = questions[idx]["id"]
                                    current_project["questions"][idx] = self._normalize_question_media(qd)
                    except Exception:
                        pass

                    if preview_mode == "quick":
                        questions = current_project.get("questions", [])
                        if not isinstance(questions, list) or idx < 0 or idx >= len(questions):
                            try:
                                self.show_toast("Hãy chọn một câu hỏi để xem nhanh." if lang == "vi" else "Select a question to quick preview.", kind="warning")
                            except Exception:
                                pass
                            _hide()
                            return
                        selected_question = copy.deepcopy(questions[idx])
                        if isinstance(selected_question, dict):
                            selected_question["question"] = self._format_quick_preview_question_text(
                                selected_question.get("question", ""),
                                idx + 1,
                                lang,
                            )
                        current_project["questions"] = [self._normalize_question_media(selected_question)]

                    proj_id = current_project.get('id') or 'EduPlay_Game'
                    preview_dir = PathResolver.resolve_preview_dir(proj_id)
                    preview_dir.mkdir(parents=True, exist_ok=True)
                    name = current_project.get('name', 'EduPlay_Game')
                    safe = ''.join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_') or 'EduPlay_Game'
                    suffix = "_quick_preview" if preview_mode == "quick" else "_preview"
                    out_file = preview_dir / (safe + suffix + ".html")
                    use_placeholder = EditorScreen._should_use_preview_placeholder(preview_mode)

                    title = current_project.get('name', 'EduPlay Preview')
                    if preview_mode == "quick":
                        title = f"{title} - {'Xem nhanh' if lang == 'vi' else 'Quick Preview'}"

                    def _write_preview_error_html(err: str | None):
                        try:
                            is_vi = (lang or "").strip().lower().startswith("vi")
                            head = "Không thể tạo bản xem trước." if is_vi else "Failed to generate preview."
                            d = str(err or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            out_file.write_text(
                                "<!doctype html><html><head><meta charset='utf-8' />"
                                "<meta name='viewport' content='width=device-width, initial-scale=1' />"
                                f"<title>{head}</title></head>"
                                "<body style='font-family: Times New Roman, Times, serif; padding: 18px;'>"
                                f"<h3>{head}</h3><pre style='white-space: pre-wrap;'>{d}</pre>"
                                "</body></html>",
                                encoding="utf-8",
                            )
                        except Exception:
                            pass

                    if use_placeholder:
                        try:
                            from eduplay.core.preview_utils import ensure_preview_placeholder_file
                            ensure_preview_placeholder_file(out_file, title=title, lang=lang)
                        except Exception:
                            try:
                                out_file.write_text("<html><body>Loading...</body></html>", encoding="utf-8")
                            except Exception:
                                pass
                    else:
                        try:
                            EditorScreen._render_preview_output_file(
                                current_project=current_project,
                                preview_dir=preview_dir,
                                safe_name=safe,
                                suffix=suffix,
                                out_file=out_file,
                                preview_mode=preview_mode,
                            )
                        except Exception as e:
                            _write_preview_error_html(str(e))

                    uri = QUrl.fromLocalFile(str(out_file)).toString()

                    def _hide():
                        try:
                            if overlay_owner and hasattr(overlay_owner, "_hide_loading"):
                                overlay_owner._hide_loading()
                        except Exception:
                            pass

                    def _failed(msg_key: str, details: str | None = None):
                        _hide()
                        try:
                            msg = I18n.t(msg_key, lang) if I18n else ("Không thể mở xem trước." if lang == "vi" else "Could not open preview.")
                        except Exception:
                            msg = "Không thể mở xem trước." if lang == "vi" else "Could not open preview."
                        if details:
                            d = str(details).strip()
                            if d:
                                msg = msg + "\n" + d
                        try:
                            self.show_toast(msg, kind="error")
                        except Exception:
                            pass

                    try:
                        if getattr(self, "_preview_process", None) is not None:
                            try:
                                self._preview_process.kill()
                            except Exception:
                                pass
                    except Exception:
                        pass

                    proc = QProcess(self)
                    self._preview_process = proc  # Store reference immediately to prevent garbage collection
                    try:
                        from eduplay.core.preview_runner import build_preview_process_command
                        import os as _os
                        exe = sys.executable
                        bn = _os.path.basename(str(exe or "")).lower()
                        if "python" not in bn:
                            if getattr(sys, "frozen", False):
                                proc.setProgram(str(exe))
                                proc.setArguments(
                                    build_preview_process_command(
                                        executable=str(exe),
                                        uri=uri,
                                        title=title,
                                        frozen=True,
                                    )[1]
                                )
                            else:
                                alt = None
                                try:
                                    p = Path(str(exe))
                                    candidates = [
                                        p.with_name("pythonw.exe"),
                                        p.with_name("python.exe"),
                                        p.with_name("py.exe"),
                                    ]
                                    for c in candidates:
                                        if c.exists():
                                            alt = str(c)
                                            break
                                except Exception:
                                    alt = None
                                alt = alt or shutil.which("pythonw") or shutil.which("python") or shutil.which("py")
                                if alt:
                                    exe = alt
                                    program, arguments = build_preview_process_command(
                                        executable=str(exe),
                                        uri=uri,
                                        title=title,
                                        frozen=False,
                                    )
                                    proc.setProgram(program)
                                    proc.setArguments(arguments)
                                else:
                                    _failed(
                                        'editor.preview_failed',
                                        "Không tìm thấy Python để mở cửa sổ xem trước. Hãy cài Python hoặc chạy EduPlay Studio bằng môi trường Python có pywebview.",
                                    )
                                    return
                        else:
                            program, arguments = build_preview_process_command(
                                executable=str(exe),
                                uri=uri,
                                title=title,
                                frozen=bool(getattr(sys, "frozen", False)),
                            )
                            proc.setProgram(program)
                            proc.setArguments(arguments)
                    except Exception:
                        proc.setProgram(sys.executable)
                        if getattr(sys, "frozen", False):
                            proc.setArguments(["--preview-runner", uri, title])
                        else:
                            proc.setArguments(["-u", "-m", "eduplay.core.preview_runner", uri, title])
                    try:
                        wd = str(Path(__file__).resolve().parents[3])
                        if wd:
                            proc.setWorkingDirectory(wd)
                    except Exception:
                        pass
                    try:
                        proc.setProcessChannelMode(QProcess.MergedChannels)
                    except Exception:
                        pass

                    buf = {"s": ""}
                    def _on_out():
                        if not EditorScreen._is_current_preview_process(self, proc):
                            return
                        try:
                            chunk = bytes(proc.readAllStandardOutput()).decode(errors="ignore")
                        except (RuntimeError, AttributeError):
                            return
                        except Exception:
                            try:
                                chunk = str(proc.readAllStandardOutput())
                            except Exception:
                                chunk = ""
                        if not chunk:
                            return
                        buf["s"] = (buf["s"] + chunk)[-4096:]
                        if "EDUPLAY_PREVIEW_READY" in buf["s"]:
                            _hide()
                            return
                        if ("pywebview is required" in buf["s"]) or ("Failed to start preview window" in buf["s"]) or ("Backend" in buf["s"] and "failed" in buf["s"].lower()):
                            tail = (buf.get("s") or "").strip()
                            tail = tail[-800:] if tail else ""
                            _failed('editor.preview_failed', tail)

                    try:
                        proc.readyReadStandardOutput.connect(_on_out)
                    except Exception:
                        pass

                    try:
                        def _on_finished(code=None, *_args):
                            tail = (buf.get("s") or "").strip()
                            tail = tail[-800:] if tail else ""
                            EditorScreen._handle_preview_process_finished(
                                self,
                                proc,
                                code,
                                _hide,
                                lambda details: _failed('editor.preview_failed', details),
                                tail,
                            )
                        proc.finished.connect(_on_finished)
                    except Exception:
                        pass
                    try:
                        def _on_error(*_args):
                            try:
                                error_msg = proc.errorString()
                            except (RuntimeError, AttributeError):
                                error_msg = ""
                            EditorScreen._handle_preview_process_error(
                                self,
                                proc,
                                lambda details: _failed('editor.preview_failed', details),
                                error_msg or "Process error",
                            )
                        proc.errorOccurred.connect(_on_error)
                    except Exception:
                        pass

                    proc.start()
                    try:
                        if not proc.waitForStarted(2000):
                            p = self._preview_process
                            try:
                                error_msg = p.errorString() if p else ""
                            except (RuntimeError, AttributeError):
                                error_msg = ""
                            _failed('editor.preview_failed', error_msg or "Process failed to start")
                            return
                    except Exception:
                        pass
                    # Process reference already stored at creation time
                    QTimer.singleShot(15000, _hide)

                    if use_placeholder:
                        try:
                            import threading

                            def _export_worker():
                                err = None
                                try:
                                    EditorScreen._render_preview_output_file(
                                        current_project=current_project,
                                        preview_dir=preview_dir,
                                        safe_name=safe,
                                        suffix=suffix,
                                        out_file=out_file,
                                        preview_mode=preview_mode,
                                    )
                                except Exception as e:
                                    err = str(e)
                                if err:
                                    _write_preview_error_html(err)

                            t = threading.Thread(target=_export_worker, daemon=True)
                            t.start()
                        except Exception:
                            pass
                except Exception:
                    try:
                        if overlay_owner and hasattr(overlay_owner, "_hide_loading"):
                            overlay_owner._hide_loading()
                    except Exception:
                        pass
                    try:
                        self.show_toast("Không thể tạo xem trước.", kind="error")
                    except Exception:
                        pass

            try:
                QTimer.singleShot(0, _run)
            except Exception:
                _run()
            return

        except Exception:
            try:
                self.show_toast("Không thể tạo xem trước.", kind="error")
            except Exception:
                pass

    def on_export_web(self):
        pass

        try:
            # Center fade-in effect (compact)
            from PySide6.QtWidgets import QGraphicsOpacityEffect
            eff = QGraphicsOpacityEffect(self.center_panel)
            self.center_panel.setGraphicsEffect(eff)
            anim_c = QPropertyAnimation(eff, b"opacity", self)
            anim_c.setDuration(260)
            anim_c.setStartValue(0.0)
            anim_c.setEndValue(1.0)
            anim_c.setEasingCurve(QEasingCurve.OutCubic)
            anim_c.start()
        except Exception:
            pass

    
        
    def on_question_selected(self, question_data):
        """Handle question selection from left panel"""
        if not self.current_project or not question_data:
            return
        try:
            EditorScreen._rebalance_project_question_points(self)
            EditorScreen._resync_editor_project_refs(self, reload_center=False)
            if self.project_manager:
                self.project_manager.save_project(self.current_project)
        except Exception:
            pass
        index = -1
        try:
            if hasattr(self.left_panel, 'questions_list'):
                index = self.left_panel.questions_list.currentRow()
        except Exception:
            index = -1
        if not isinstance(index, int) or index < 0:
            questions = self.current_project.get('questions', [])
            for i, q in enumerate(questions):
                if q is question_data or q == question_data:
                    index = i
                    break
        self.current_question_index = index if isinstance(index, int) else -1
        self.center_panel.set_question(question_data, self.current_question_index)

    def _resolve_selected_question_request(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        question = payload.get("question")
        question_id = payload.get("question_id")
        index = payload.get("index")

        if not isinstance(index, int):
            try:
                if hasattr(self, "left_panel") and hasattr(self.left_panel, "questions_list"):
                    index = int(self.left_panel.questions_list.currentRow())
                else:
                    index = -1
            except Exception:
                index = -1

        questions = []
        try:
            questions = self.current_project.get("questions") or []
        except Exception:
            questions = []

        if (question is None or not isinstance(question, dict)) and isinstance(index, int) and 0 <= index < len(questions):
            try:
                question = questions[index]
            except Exception:
                question = None

        if not question_id and isinstance(question, dict):
            question_id = question.get("id")

        if (not isinstance(index, int) or index < 0) and question_id:
            for i, existing_question in enumerate(questions):
                if isinstance(existing_question, dict) and existing_question.get("id") == question_id:
                    index = i
                    if question is None:
                        question = existing_question
                    break

        if question is None and question_id is None:
            return None

        return {
            "question": question,
            "question_id": question_id,
            "index": index if isinstance(index, int) else -1,
        }

    def on_preview_selected_question_requested(self, payload=None):
        if not self.current_project:
            return
        resolved = EditorScreen._resolve_selected_question_request(self, payload)
        if not resolved:
            return
        question = resolved.get("question")
        index = resolved.get("index", -1)
        if isinstance(index, int) and index >= 0:
            self.current_question_index = index
        try:
            if question and hasattr(self, "center_panel") and self.center_panel:
                self.center_panel.set_question(question, self.current_question_index)
        except Exception:
            pass
        self.open_preview_window(preview_mode="quick")

    def on_quick_preview_current_question_requested(self):
        if not self.current_project:
            return
        idx = -1
        try:
            idx = int(getattr(self, "current_question_index", -1))
        except Exception:
            idx = -1
        if idx < 0:
            try:
                if hasattr(self, "left_panel") and hasattr(self.left_panel, "questions_list"):
                    idx = int(self.left_panel.questions_list.currentRow())
            except Exception:
                idx = -1
        if isinstance(idx, int) and idx >= 0:
            self.current_question_index = idx
        self.open_preview_window(preview_mode="quick")

    def on_delete_selected_question_requested(self, payload=None):
        if not self.current_project:
            return
        resolved = EditorScreen._resolve_selected_question_request(self, payload)
        if not resolved:
            return

        try:
            lang = SettingsManager().get_language() or "en"
        except Exception:
            lang = "en"
        try:
            title = I18n.t("editor.left.delete_confirm_title", lang)
        except Exception:
            title = "Xác nhận xóa" if str(lang).lower().startswith("vi") else "Confirm delete"
        question_text = ""
        try:
            question_text = str((resolved.get("question") or {}).get("question") or "").strip()
        except Exception:
            question_text = ""
        preview_text = (question_text[:120] + "...") if len(question_text) > 120 else question_text
        try:
            message_template = I18n.t("editor.left.delete_confirm_message", lang)
        except Exception:
            message_template = "Bạn có chắc muốn xóa câu hỏi này?\n\n{question}" if str(lang).lower().startswith("vi") else "Are you sure you want to delete this question?\n\n{question}"
        message = message_template.format(question=preview_text or ("Câu hỏi đang chọn" if str(lang).lower().startswith("vi") else "Selected question"))
        answer = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.on_question_updated(
            {
                "action": "delete",
                "question": resolved.get("question"),
                "question_id": resolved.get("question_id"),
                "index": resolved.get("index"),
            }
        )
        
    def on_import_questions(self):
        """Handle import questions request from left panel"""
        try:
            if not self.import_service:
                try:
                    self.show_toast("Import service is not available.", kind="warning")
                except Exception:
                    pass
                return
            try:
                lang = SettingsManager().get_language() or 'vi'
            except Exception:
                lang = 'vi'
            try:
                caption = I18n.t("import.dialog_title", lang)
            except Exception:
                caption = "Nhập câu hỏi"
            try:
                filt = I18n.t("import.file_filters_all", lang)
            except Exception:
                filt = "Documents (*.txt *.docx *.doc *.pdf *.xlsx);;All Files (*.*)"
            file_path = get_open_file_name(self, caption, "", filt)
            if not file_path:
                return
            try:
                questions = self.import_service.import_from_file(file_path)
            except Exception as e:
                try:
                    self.show_toast(f"Không thể nhập câu hỏi: {e}", kind="error")
                except Exception:
                    pass
                return
            if not questions:
                try:
                    self.show_toast("Không tìm thấy câu hỏi hợp lệ trong tệp.", kind="warning")
                except Exception:
                    pass
                return
            game_type = str((self.current_project or {}).get("game_type") or "").strip().lower()
            filtered = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                qt = str(q.get("type") or "").strip().lower()
                if game_type == "quiz_millionaire":
                    if qt != "multiple_choice":
                        continue
                    opts = q.get("options") or []
                    if not isinstance(opts, list) or len(opts) < 2:
                        continue
                filtered.append(q)

            if not filtered:
                try:
                    self.show_toast("File nhập không có câu hỏi phù hợp với game hiện tại.", kind="warning")
                except Exception:
                    pass
                return

            try:
                if self.project_manager and isinstance(self.current_project, dict):
                    pid = str(self.current_project.get("id") or "").strip()
                    if pid:
                        loaded = self.project_manager.load_project(pid)
                        if loaded:
                            self.current_project = loaded
                    self.project_manager.set_current_project(self.current_project)
            except Exception:
                pass

            ok_any = False
            for q in filtered:
                try:
                    if self.project_manager and self.project_manager.add_question(q):
                        ok_any = True
                except Exception:
                    pass

            if not ok_any:
                try:
                    self.show_toast("Nhập câu hỏi thất bại.", kind="error")
                except Exception:
                    pass
                return

            refreshed = None
            try:
                refreshed = self.project_manager.get_current_project()
            except Exception:
                refreshed = None
            if refreshed:
                self.current_project = refreshed
            try:
                self.left_panel.set_project(self.current_project)
            except Exception:
                pass
            try:
                if hasattr(self, 'show_toast'):
                    self.show_toast(f"Đã nhập {len(filtered)} câu hỏi", kind="success")
            except Exception:
                pass
        except Exception:
            pass

    def _resync_editor_project_refs(self, reload_center: bool = False):
        try:
            if hasattr(self, "left_panel") and self.left_panel:
                if hasattr(self.left_panel, "set_project"):
                    self.left_panel.set_project(self.current_project)
                else:
                    self.left_panel.current_project = self.current_project
        except Exception:
            pass
        try:
            if hasattr(self, "center_panel") and self.center_panel:
                self.center_panel.current_project = self.current_project
                if reload_center and hasattr(self.center_panel, "load_project"):
                    self.center_panel.load_project(self.current_project)
        except Exception:
            pass

    def _rebalance_project_question_points(self):
        try:
            if not self.current_project:
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
            count = len(valid_questions)
            base = max(1, total_points // count)
            remainder = max(0, total_points - (base * count))
            for i, q in enumerate(valid_questions):
                q["points"] = int(base + (1 if i < remainder else 0))
            cfg["points_per_question"] = int(base)
            self.current_project["questions"] = questions
            self.current_project["game_config"] = cfg
        except Exception:
            pass
        
    def on_question_updated(self, update_data):
        """Handle question updates from center panel"""
        if not self.current_project:
            return
            
        action = update_data.get('action')
        
        if action in (None, 'save'):
            if self.current_question_index >= 0:
                updated_question = update_data.get('question') if isinstance(update_data.get('question'), dict) else update_data
                if not isinstance(updated_question, dict):
                    updated_question = {}
                updated_question = self._normalize_question_media(updated_question)
                questions = self.current_project.get('questions', [])
                if self.current_question_index < len(questions):
                    self.current_project['questions'][self.current_question_index] = updated_question
                    EditorScreen._rebalance_project_question_points(self)
                    EditorScreen._resync_editor_project_refs(self, reload_center=False)
                    try:
                        self.left_panel.load_questions_silent()
                    except Exception:
                        self.left_panel.load_questions()
                    try:
                        if self.project_manager:
                            self.project_manager.save_project(self.current_project)
                    except Exception:
                        pass
                    try:
                        try:
                            lang = SettingsManager().get_language() or 'en'
                        except Exception:
                            lang = 'en'
                        try:
                            msg = I18n.t('toast.save_success', lang)
                        except Exception:
                            msg = "Đã lưu câu hỏi"
                        self.show_toast(msg, kind="success")
                    except Exception:
                        pass
            
        elif action == 'delete':
            question = update_data.get('question') or {}
            qid = update_data.get('question_id') or question.get('id')
            deleted = False
            if qid:
                try:
                    if self.project_manager:
                        deleted = self.project_manager.delete_question(qid)
                        refreshed = self.project_manager.get_current_project()
                        if refreshed:
                            self.current_project = refreshed
                            try:
                                if hasattr(self, "center_panel") and self.center_panel and hasattr(self.center_panel, "load_project"):
                                    self.center_panel.load_project(self.current_project)
                            except Exception:
                                pass
                except Exception:
                    deleted = False
            if not deleted and self.current_project:
                questions = self.current_project.get('questions', [])
                index = update_data.get('index')
                if not isinstance(index, int) or index < 0 or index >= len(questions):
                    for i, q in enumerate(questions):
                        if q is question or q == question:
                            index = i
                            break
                if isinstance(index, int) and 0 <= index < len(questions):
                    questions.pop(index)
                    self.current_project['questions'] = questions
                    try:
                        if self.project_manager:
                            self.project_manager.save_project(self.current_project)
                    except Exception:
                        pass
            EditorScreen._rebalance_project_question_points(self)
            try:
                if self.project_manager:
                    self.project_manager.save_project(self.current_project)
            except Exception:
                pass
            try:
                EditorScreen._resync_editor_project_refs(self, reload_center=True)
            except Exception:
                pass
            try:
                self.left_panel.load_questions_silent()
            except Exception:
                self.left_panel.load_questions()
            self.center_panel.set_question(None, -1)
            self.current_question_index = -1
                
        elif action == 'duplicate':
            question = update_data.get('question')
            if question:
                new_question_id = ""
                try:
                    qid = str(question.get("id") or "").strip() if isinstance(question, dict) else ""
                except Exception:
                    qid = ""
                try:
                    if self.project_manager and qid:
                        new_question_id = str(self.project_manager.duplicate_question(qid) or "").strip()
                        refreshed = self.project_manager.get_current_project()
                        if refreshed:
                            self.current_project = refreshed
                except Exception:
                    new_question_id = ""
                if not new_question_id:
                    if 'questions' not in self.current_project:
                        self.current_project['questions'] = []
                    import copy
                    import uuid

                    new_question = copy.deepcopy(question)
                    existing_ids = {
                        str(q.get("id") or "").strip()
                        for q in (self.current_project.get("questions") or [])
                        if isinstance(q, dict)
                    }
                    new_question_id = f"q_{uuid.uuid4().hex[:10]}"
                    while new_question_id in existing_ids:
                        new_question_id = f"q_{uuid.uuid4().hex[:10]}"
                    new_question["id"] = new_question_id
                    self.current_project['questions'].append(new_question)
                    try:
                        if self.project_manager:
                            self.project_manager.save_project(self.current_project)
                    except Exception:
                        pass
                EditorScreen._rebalance_project_question_points(self)
                EditorScreen._resync_editor_project_refs(self, reload_center=False)
                try:
                    self.left_panel.load_questions_silent()
                except Exception:
                    self.left_panel.load_questions()
                try:
                    for idx, q in enumerate(self.current_project.get("questions") or []):
                        if isinstance(q, dict) and str(q.get("id") or "") == new_question_id:
                            self.current_question_index = idx
                            self.center_panel.set_question(q, idx)
                            break
                except Exception:
                    pass
                
    def _project_media_dir(self) -> Path | None:
        try:
            if not self.current_project:
                return None
            project_id = self.current_project.get("id")
            if not project_id:
                return None
            base_dir = self.project_manager.projects_dir / project_id / "media"
            base_dir.mkdir(parents=True, exist_ok=True)
            return base_dir
        except Exception:
            return None

    def _copy_file_to_project_media(self, source_path: str) -> str:
        if not source_path:
            return ""
        src = Path(str(source_path))
        if not src.exists() or not src.is_file():
            return str(source_path)
        media_dir = self._project_media_dir()
        if media_dir is None:
            return str(source_path)
        try:
            src_resolved = src.resolve()
            media_resolved = media_dir.resolve()
            if str(src_resolved).startswith(str(media_resolved)):
                return f"media/{src.name}"
        except Exception:
            pass
        stem = src.stem
        suffix = src.suffix
        candidate = media_dir / f"{stem}{suffix}"
        idx = 1
        while candidate.exists():
            candidate = media_dir / f"{stem}_{idx}{suffix}"
            idx += 1
        shutil.copy2(str(src), str(candidate))
        return f"media/{candidate.name}"

    def _normalize_question_media(self, question_data: dict) -> dict:
        if not isinstance(question_data, dict):
            return question_data
        image_path = str(question_data.get("image") or "").strip()
        if image_path and os.path.exists(image_path):
            try:
                question_data["image"] = self._copy_file_to_project_media(image_path)
            except Exception:
                pass
        return question_data

    def on_question_settings_applied(self, settings: dict):
        if not self.current_project or not isinstance(settings, dict):
            return
        cfg = dict(self.current_project.get("game_config") or {})
        apply_fields = settings.get("apply_to_all_fields")
        if isinstance(apply_fields, (list, tuple, set)):
            apply_fields = {str(field or "").strip() for field in apply_fields if str(field or "").strip()}
        else:
            apply_fields = {
                "question_time",
                "allow_delete_question",
                "randomize_questions",
                "auto_points_enabled",
                "total_points",
                "export_mode",
                "background_music",
            }

        default_time = int(settings.get("default_question_time", cfg.get("question_time", 30)) or 30)
        try:
            if "allow_delete_question" in apply_fields and "allow_delete_question" in settings:
                cfg["allow_delete_question"] = bool(settings.get("allow_delete_question"))
        except Exception:
            pass
        try:
            if "randomize_questions" in apply_fields and "randomize_questions" in settings:
                cfg["randomize_questions"] = bool(settings.get("randomize_questions"))
        except Exception:
            pass
        try:
            if "auto_points_enabled" in apply_fields and "auto_points_enabled" in settings:
                cfg["auto_points_enabled"] = bool(settings.get("auto_points_enabled"))
        except Exception:
            pass
        try:
            if "total_points" in apply_fields and settings.get("total_points") is not None:
                cfg["total_points"] = int(settings.get("total_points"))
        except Exception:
            pass
        try:
            if "export_mode" in apply_fields:
                cfg["export_mode"] = str(settings.get("export_mode") or cfg.get("export_mode") or "student")
        except Exception:
            cfg["export_mode"] = "student"

        is_millionaire = bool(settings.get("is_millionaire"))
        mode = str(settings.get("music_mode") or "none").strip().lower()

        if "background_music" in apply_fields:
            if is_millionaire:
                cfg["background_music_mode"] = "none"
                cfg["background_music"] = ""
            else:
                builtin_1 = "assets/sound/background.mp3"
                builtin_2 = "assets/sound/background2.mp3"
                bgm_path = builtin_1
                if mode == "custom":
                    custom_src = str(settings.get("custom_music_path") or "").strip()
                    if custom_src and os.path.exists(custom_src):
                        bgm_path = self._copy_file_to_project_media(custom_src)
                    else:
                        bgm_path = cfg.get("background_music", builtin_1) or builtin_1
                elif mode == "random_builtin":
                    bgm_path = random.choice([builtin_1, builtin_2])
                elif mode == "builtin_2":
                    bgm_path = builtin_2
                else:
                    bgm_path = builtin_1
                cfg["background_music_mode"] = mode
                cfg["background_music"] = bgm_path

        questions = self.current_project.get("questions", [])
        if "question_time" in apply_fields:
            cfg["question_time"] = default_time
            for q in questions:
                if isinstance(q, dict):
                    q["time_limit"] = default_time

        self.current_project["questions"] = questions
        self.current_project["game_config"] = cfg
        EditorScreen._rebalance_project_question_points(self)
        try:
            if hasattr(self.center_panel, "load_project"):
                self.center_panel.load_project(self.current_project)
            elif hasattr(self.center_panel, "load_game_config"):
                self.center_panel.load_game_config(cfg)
        except Exception:
            pass
        try:
            if hasattr(self.left_panel, "set_project"):
                self.left_panel.set_project(self.current_project)
            else:
                if hasattr(self.left_panel, "load_questions"):
                    self.left_panel.load_questions()
                if hasattr(self.left_panel, "load_settings"):
                    self.left_panel.load_settings()
                if hasattr(self.left_panel, "load_game_config"):
                    self.left_panel.load_game_config()
        except Exception:
            pass
        try:
            idx = self.current_question_index
            if isinstance(idx, int) and 0 <= idx < len(questions):
                self.center_panel.set_question(questions[idx], idx)
        except Exception:
            pass
        try:
            if hasattr(self.center_panel, "apply_project_permissions"):
                self.center_panel.apply_project_permissions(self.current_project)
        except Exception:
            pass
        try:
            self.project_manager.save_project(self.current_project)
        except Exception:
            pass
        try:
            self.show_toast("Đã áp dụng cài đặt cho toàn bộ câu hỏi", kind="success")
        except Exception:
            pass

    def on_preview_requested(self):
        """Handle preview/export requests"""
        # This signal is emitted when export buttons are clicked
        # The main window should handle the actual export
        pass

    def _on_unsaved_changed(self, dirty: bool):
        try:
            self._unsaved_changes = bool(dirty)
        except Exception:
            self._unsaved_changes = True
        if getattr(self, "_unsaved_changes", False):
            self._set_save_status("dirty")
            if getattr(self, "_autosave_enabled", True):
                try:
                    self._autosave_timer.start(self._autosave_interval_ms)
                except Exception:
                    pass
        else:
            try:
                self._autosave_timer.stop()
            except Exception:
                pass
            self._set_save_status("saved")

    def on_export_web(self):
        self.publish_requested.emit()

    def on_export_html(self):
        """Handle HTML export request"""
        self.export_requested.emit('html')
        
    def on_export_native(self):
        """Handle native export request"""
        self.export_requested.emit('native')

    def on_export_exe(self):
        self.export_requested.emit('exe')

    def on_game_config_changed(self, config: dict):
        self._apply_game_config_to_project(config, persist=True)
        

    def set_language(self, lang: str):
        from eduplay.core.i18n import I18n
        l = lang or 'en'
        try:
            self.back_btn.setText(self._button_text(I18n.t('editor.back', l)))
            self.save_btn.setText(self._button_text(I18n.t('editor.save', l)))
            self.preview_btn.setText(self._button_text(I18n.t('editor.preview_title', l)))
            self.export_web_btn.setText(self._button_text(I18n.t('editor.export_web', l)))
            self.export_html_btn.setText(self._button_text(I18n.t('editor.export_html_internal', l)))
            if hasattr(self, "import_btn") and self.import_btn:
                self.import_btn.setText(self._button_text(I18n.t('editor.import', l)))
        except Exception:
            pass
        try:
            if hasattr(self.center_panel, 'set_language'):
                self.center_panel.set_language(l)
        except Exception:
            pass
        self._update_save_status_label()
        
    def save_project(self, silent: bool = False, autosave: bool = False):
        """Save the current project"""
        if autosave:
            self._set_save_status("saving")
        if self.current_project:
            try:
                if hasattr(self, "center_panel") and self.center_panel:
                    try:
                        if hasattr(self.center_panel, "get_game_config_data"):
                            cfg = self.center_panel.get_game_config_data()
                            self._apply_game_config_to_project(cfg, persist=False)
                    except Exception:
                        pass
                    try:
                        if hasattr(self.center_panel, "auto_points_check") and bool(self.center_panel.auto_points_check.isChecked()):
                            if hasattr(self.center_panel, "_distribute_points_across_questions"):
                                self.center_panel._distribute_points_across_questions()
                    except Exception:
                        pass
                    try:
                        idx = int(getattr(self, "current_question_index", -1))
                    except Exception:
                        idx = -1
                    try:
                        if idx >= 0 and hasattr(self.center_panel, "get_question_data"):
                            questions = self.current_project.get("questions", [])
                            if isinstance(questions, list) and idx < len(questions):
                                qd = self.center_panel.get_question_data()
                                if isinstance(questions[idx], dict) and isinstance(qd, dict):
                                    for k in ("id",):
                                        if k in questions[idx] and k not in qd:
                                            qd[k] = questions[idx][k]
                                qd = self._normalize_question_media(qd)
                                self.current_project["questions"][idx] = qd
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                questions = self.current_project.get("questions", [])
                self.current_project["questions"] = [self._normalize_question_media(q) for q in questions]
            except Exception:
                pass
            success = self.project_manager.save_project(self.current_project)
            if success:
                try:
                    self._unsaved_changes = False
                except Exception:
                    pass
                try:
                    self._autosave_timer.stop()
                except Exception:
                    pass
                self._set_save_status("saved")
                try:
                    if self.project_manager and isinstance(self.current_project.get("game_config"), dict):
                        self.project_manager.update_game_config(self.current_project["game_config"])
                except Exception:
                    pass
                try:
                    try:
                        lang = SettingsManager().get_language() or 'en'
                    except Exception:
                        lang = 'en'
                    try:
                        msg = I18n.t('toast.save_success', lang)
                    except Exception:
                        msg = "Đã lưu dự án"
                    if not silent:
                        self.show_toast(msg, kind="success")
                except Exception:
                    pass
                return True
            self._set_save_status("error")
            return False
        self._set_save_status("error")
        return False
                
    def import_questions(self):
        """Import questions from file"""
        if not self.import_service:
            try:
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or 'en'
            except Exception:
                lang = 'en'
            try:
                title = I18n.t('import.error_title', lang)
                msg = I18n.t('import.service_not_available', lang)
            except Exception:
                title = "Import Error"
                msg = "Import service is not available."
            QMessageBox.warning(self, title, msg)
            return
            
        # Open file dialog
        file_path = get_open_file_name(
            self,
            (I18n.t('import.dialog_title', SettingsManager().get_language() or 'en') if hasattr(I18n, 't') else "Import Questions"),
            "",
            (I18n.t('import.file_filters_all', SettingsManager().get_language() or 'en') if hasattr(I18n, 't') else "All Supported Files (*.doc *.docx *.pdf *.xlsx *.txt);;Word Documents (*.docx *.doc);;PDF Files (*.pdf);;Excel Files (*.xlsx);;Text Files (*.txt)"),
        )
        
        if not file_path:
            return
        overlay_owner = None
        try:
            win = QApplication.activeWindow()
            if win and hasattr(win, "_show_loading"):
                overlay_owner = win
                try:
                    from eduplay.core.i18n import I18n
                    from eduplay.core.settings_manager import SettingsManager
                    lang = 'en'
                    try:
                        lang = SettingsManager().get_language() or 'en'
                    except Exception:
                        lang = 'en'
                    msg = I18n.t('editor.loading_import', lang)
                except Exception:
                    lang = (lang if 'lang' in locals() else 'en')
                    msg = "Đang nhập câu hỏi..." if lang == 'vi' else "Importing questions..."
                try:
                    win._show_loading(msg, "default")
                except Exception:
                    pass
        except Exception:
            overlay_owner = None
        try:
            if file_path.lower().endswith('.txt'):
                imported_questions = self.import_service.import_from_txt(file_path)
            elif file_path.lower().endswith('.doc'):
                imported_questions = self.import_service.import_from_doc(file_path)
            else:
                imported_questions = self.import_service.import_from_file(file_path)
            if imported_questions:
                if not self.current_project:
                    try:
                        from eduplay.core.settings_manager import SettingsManager
                        lang = SettingsManager().get_language() or 'en'
                    except Exception:
                        lang = 'en'
                    try:
                        title = I18n.t('import.error_title', lang)
                        msg = I18n.t('import.no_project_loaded', lang)
                    except Exception:
                        title = "Import Error"
                        msg = "No project is currently loaded."
                    QMessageBox.warning(self, title, msg)
                    return
                existing_questions = self.current_project.get('questions', [])
                existing_questions.extend(imported_questions)
                self.current_project['questions'] = existing_questions
                if self.project_manager.save_project(self.current_project):
                    self.load_project(self.current_project)
                    try:
                        from eduplay.core.settings_manager import SettingsManager
                        lang = SettingsManager().get_language() or 'en'
                    except Exception:
                        lang = 'en'
                    try:
                        title = I18n.t('import.success_title', lang)
                        msg = I18n.t('import.success_count', lang, count=len(imported_questions))
                    except Exception:
                        title = "Import Successful"
                        msg = f"Successfully imported {len(imported_questions)} questions."
                    QMessageBox.information(self, title, msg)
                else:
                    try:
                        from eduplay.core.settings_manager import SettingsManager
                        lang = SettingsManager().get_language() or 'en'
                    except Exception:
                        lang = 'en'
                    try:
                        title = I18n.t('import.error_title', lang)
                        msg = I18n.t('import.save_failed', lang)
                    except Exception:
                        title = "Import Error"
                        msg = "Failed to save project after import."
                    QMessageBox.warning(self, title, msg)
            else:
                try:
                    from eduplay.core.settings_manager import SettingsManager
                    lang = SettingsManager().get_language() or 'en'
                except Exception:
                    lang = 'en'
                try:
                    title = I18n.t('import.result_title', lang)
                    msg = I18n.t('import.no_questions_found', lang)
                except Exception:
                    title = "Import Result"
                    msg = "No questions were found in the selected file."
                QMessageBox.information(self, title, msg)
        except ImportError as e:
            try:
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or 'en'
            except Exception:
                lang = 'en'
            try:
                title = I18n.t('import.error_title', lang)
                msg = I18n.t('import.required_library_missing', lang, error=str(e))
            except Exception:
                title = "Import Error"
                msg = f"Required library not available: {str(e)}"
            QMessageBox.warning(self, title, msg)
        except Exception as e:
            try:
                from eduplay.core.settings_manager import SettingsManager
                lang = SettingsManager().get_language() or 'en'
            except Exception:
                lang = 'en'
            try:
                title = I18n.t('import.error_title', lang)
                msg = I18n.t('import.failed_generic', lang, error=str(e))
            except Exception:
                title = "Import Error"
                msg = f"Failed to import questions: {str(e)}"
            QMessageBox.warning(self, title, msg)
        finally:
            try:
                if overlay_owner and hasattr(overlay_owner, "_hide_loading"):
                    overlay_owner._hide_loading()
            except Exception:
                pass
        
    def get_current_project(self):
        """Get the current project data"""
        return self.current_project

