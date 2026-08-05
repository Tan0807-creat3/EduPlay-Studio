from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QToolButton, QSizePolicy, QToolTip
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QEvent
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QIcon, QCursor

from eduplay.core.asset_loader import materialize_asset_file
from eduplay.core.settings_manager import SettingsManager
from eduplay.ui.icon_factory import build_line_icon_pixmap, build_glyph_icon


class LeftNavDrawer(QFrame):
    navigate_requested = Signal(str)
    quick_action_requested = Signal(str)
    hover_entered = Signal()
    hover_left = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lang = "en"
        self._active_key = None
        self._tooltip_last_widget = None
        self._tooltip_last_text = ""
        self._tooltip_last_anchor = None
        self.setObjectName("left-nav-drawer")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        self._root_layout = layout
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(10)

        self.header_icon = QLabel()
        self.header_icon.setObjectName("left-nav-app-icon")
        self.header_icon.setAlignment(Qt.AlignCenter)
        try:
            p = materialize_asset_file("eduplay/resources/icons/icon.png")
            pix = QPixmap(str(p))
            if pix and (not pix.isNull()):
                self.header_icon.setPixmap(
                    pix.scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.header_icon.setFixedSize(40, 40)
        except Exception:
            pass
        layout.addWidget(self.header_icon, alignment=Qt.AlignHCenter)

        self.brand_label = QLabel("EDUPLAY")
        self.brand_label.setObjectName("left-nav-brand")
        self.brand_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.brand_label)

        self.studio_label = QLabel("Studio")
        self.studio_label.setObjectName("left-nav-studio")
        self.studio_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.studio_label)

        layout.addSpacing(4)

        self.btn_home = self._make_btn("home", "Home", "home")
        self.btn_projects = self._make_btn("browser", "Projects", "projects")
        self.btn_preview = self._make_btn("player", "Preview", "preview")
        self._nav_buttons = (self.btn_home, self.btn_projects, self.btn_preview)

        layout.addWidget(self.btn_home, alignment=Qt.AlignHCenter)
        layout.addWidget(self.btn_projects, alignment=Qt.AlignHCenter)
        layout.addWidget(self.btn_preview, alignment=Qt.AlignHCenter)
        layout.addSpacing(6)

        self.quick_separator = QFrame()
        self.quick_separator.setObjectName("left-nav-separator")
        self.quick_separator.setFixedHeight(1)
        layout.addWidget(self.quick_separator)

        self.quick_section_label = QLabel("Quick actions")
        self.quick_section_label.setObjectName("left-nav-section-title")
        self.quick_section_label.setWordWrap(True)
        self.quick_section_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.quick_section_label)

        self.btn_recent = self._make_quick_btn("recent", "Recent", "recent")
        self.btn_publish = self._make_quick_btn("publish", "Publish", "publish")
        self.btn_resume = self._make_quick_btn("resume", "Resume", "resume")
        self._quick_buttons = (self.btn_recent, self.btn_publish, self.btn_resume)

        layout.addWidget(self.btn_recent)
        layout.addWidget(self.btn_publish)
        layout.addWidget(self.btn_resume)
        layout.addStretch(1)

        self._apply_quick_icon(self.btn_recent)
        self._apply_quick_icon(self.btn_publish)
        self._apply_quick_icon(self.btn_resume)
        for widget in (
            self.btn_home,
            self.btn_projects,
            self.btn_preview,
            self.btn_recent,
            self.btn_publish,
            self.btn_resume,
            self.quick_section_label,
        ):
            try:
                widget.setMouseTracking(True)
                widget.installEventFilter(self)
            except Exception:
                pass
        self.set_quick_context(False)
        self.set_active("home")
        try:
            self.set_language(SettingsManager().get_language() or "en")
        except Exception:
            self.set_language("en")
        self._apply_responsive_layout()

    def _make_btn(self, nav_key: str, label: str, icon_kind: str) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("left-nav-item")
        btn.setProperty("navKey", nav_key)
        btn.setProperty("iconKind", icon_kind)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setIconSize(QSize(20, 20))
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.setText(label)
        btn.setToolTip(label)
        btn.clicked.connect(lambda: self.navigate_requested.emit(nav_key))
        return btn

    def _make_quick_btn(self, action_key: str, label: str, icon_kind: str) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("left-nav-quick-item")
        btn.setProperty("actionKey", action_key)
        btn.setProperty("iconKind", icon_kind)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setIconSize(QSize(16, 16))
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.setText(label)
        btn.setToolTip(label)
        btn.clicked.connect(lambda: self.quick_action_requested.emit(action_key))
        return btn

    def _wrap_words(self, raw: str, limit: int) -> str:
        words = [part for part in str(raw or "").split() if part]
        if not words:
            return ""
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if len(trial) <= limit:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        if len(lines) <= 2:
            return "\n".join(lines)
        split_at = max(1, len(words) // 2)
        return " ".join(words[:split_at]) + "\n" + " ".join(words[split_at:])

    def _format_quick_label(self, text: str, compact: bool = False) -> str:
        raw = str(text or "").strip()
        mapping = {
            "Mở gần đây": "Mở gần\nđây",
            "Xuất bản nhanh": "Xuất bản\nnhanh",
            "Tiếp tục chỉnh sửa": "Tiếp tục\nchỉnh sửa",
            "Recent": "Recent",
            "Quick publish": "Quick\npublish",
            "Publish": "Quick\npublish",
            "Resume editing": "Resume\nediting",
            "Resume": "Resume\nediting",
        }
        if raw in mapping:
            return mapping[raw]
        parts = raw.split()
        limit = 8 if compact else 10
        if len(parts) >= 2:
            return self._wrap_words(raw, limit)
        return raw

    def set_language(self, lang: str | None):
        l = str(lang or "en")
        self._lang = l
        try:
            from eduplay.core.i18n import I18n

            home = I18n.t("nav.home", l)
            projects = I18n.t("nav.projects", l)
            preview = I18n.t("nav.preview", l)
            quick_title = I18n.t("nav.quick_actions", l)
            recent = I18n.t("home.quick.recent", l)
            publish = I18n.t("home.quick.publish", l)
            resume = I18n.t("home.quick.resume", l)
            tip_home = I18n.t("tooltip.leftnav.home", l)
            tip_projects = I18n.t("tooltip.leftnav.projects", l)
            tip_preview = I18n.t("tooltip.leftnav.preview", l)
            tip_recent = I18n.t("tooltip.quick.recent", l)
            tip_publish = I18n.t("tooltip.quick.publish", l)
            tip_resume = I18n.t("tooltip.quick.resume", l)
        except Exception:
            home = "Home"
            projects = "Projects"
            preview = "Preview"
            quick_title = "Quick actions"
            recent = "Recent"
            publish = "Publish"
            resume = "Resume"
            tip_home = "Go to Home"
            tip_projects = "Browse projects"
            tip_preview = "Open Preview"
            tip_recent = "Open a recent project"
            tip_publish = "Quick export / publish"
            tip_resume = "Resume current project"
        try:
            self.btn_home.setText(home)
            self.btn_home.setToolTip(tip_home if isinstance(tip_home, str) and tip_home != "tooltip.leftnav.home" else home)
        except Exception:
            pass
        try:
            self.btn_projects.setText(projects)
            self.btn_projects.setToolTip(tip_projects if isinstance(tip_projects, str) and tip_projects != "tooltip.leftnav.projects" else projects)
        except Exception:
            pass
        try:
            self.btn_preview.setText(preview)
            self.btn_preview.setToolTip(tip_preview if isinstance(tip_preview, str) and tip_preview != "tooltip.leftnav.preview" else preview)
        except Exception:
            pass
        try:
            self.quick_section_label.setText(self._format_quick_label(quick_title, compact=False))
            self.quick_section_label.setProperty("displayText", quick_title)
            self.quick_section_label.setToolTip(quick_title)
        except Exception:
            pass
        for btn, text in (
            (getattr(self, "btn_recent", None), recent),
            (getattr(self, "btn_publish", None), publish),
            (getattr(self, "btn_resume", None), resume),
        ):
            if not btn:
                continue
            try:
                btn.setProperty("displayText", text)
                btn.setText(self._format_quick_label(text, compact=True))
            except Exception:
                pass
        try:
            self.btn_recent.setToolTip(tip_recent if isinstance(tip_recent, str) and tip_recent != "tooltip.quick.recent" else recent)
        except Exception:
            pass
        try:
            self.btn_publish.setToolTip(tip_publish if isinstance(tip_publish, str) and tip_publish != "tooltip.quick.publish" else publish)
        except Exception:
            pass
        try:
            self.btn_resume.setToolTip(tip_resume if isinstance(tip_resume, str) and tip_resume != "tooltip.quick.resume" else resume)
        except Exception:
            pass
        try:
            self._apply_responsive_layout()
        except Exception:
            pass

    def set_active(self, nav_key: str):
        self._active_key = nav_key
        for b in (self.btn_home, self.btn_projects, self.btn_preview):
            is_active = str(b.property("navKey") or "") == str(nav_key)
            b.setProperty("active", "true" if is_active else "false")
            try:
                self._apply_nav_icon(b, is_active)
            except Exception:
                pass
            b.style().unpolish(b)
            b.style().polish(b)

    def _apply_nav_icon(self, btn: QToolButton, is_active: bool):
        color = "#7F56D9" if is_active else "#94A3B8"
        kind = str(btn.property("iconKind") or "")
        pix = build_line_icon_pixmap(kind, color, 20)
        btn.setIcon(QIcon(pix))

    def _apply_quick_icon(self, btn: QToolButton):
        kind = str(btn.property("iconKind") or "")
        if kind == "resume":
            btn.setIcon(build_glyph_icon("edit", "#7F56D9", 18))
            return
        pix = build_line_icon_pixmap(kind, "#7F56D9", 18)
        btn.setIcon(QIcon(pix))

    def set_quick_context(self, has_current_project: bool):
        try:
            self.btn_resume.setVisible(True)
            if has_current_project:
                self.btn_resume.setProperty("hasProject", "true")
                self.btn_resume.setToolTip(self.btn_resume.toolTip() or self.btn_resume.text().replace("\n", " "))
            else:
                self.btn_resume.setProperty("hasProject", "false")
            self.btn_resume.setEnabled(True)
        except Exception:
            pass
        try:
            self._apply_responsive_layout()
        except Exception:
            pass

    def _is_compact_layout(self) -> bool:
        return False

    def _apply_responsive_layout(self):
        try:
            if self._root_layout:
                self._root_layout.setContentsMargins(12, 14, 12, 14)
                self._root_layout.setSpacing(10)
        except Exception:
            pass
        try:
            self.quick_section_label.setMaximumWidth(max(64, self.width() - 20))
        except Exception:
            pass
        nav_size = QSize(84, 56)
        nav_icon = QSize(20, 20)
        for btn in getattr(self, "_nav_buttons", ()):
            try:
                btn.setFixedSize(nav_size)
                btn.setIconSize(nav_icon)
            except Exception:
                pass
        quick_height = 52
        quick_width = max(96, min(102, self.width() - 24))
        quick_icon = QSize(18, 18)
        for btn in getattr(self, "_quick_buttons", ()):
            try:
                btn.setFixedSize(quick_width, quick_height)
                btn.setIconSize(quick_icon)
            except Exception:
                pass
        try:
            quick_title = self.quick_section_label.property("displayText") or self.quick_section_label.toolTip() or self.quick_section_label.text().replace("\n", " ")
            self.quick_section_label.setText(self._format_quick_label(quick_title, compact=False))
        except Exception:
            pass
        for btn in getattr(self, "_quick_buttons", ()):
            try:
                source_text = btn.property("displayText") or btn.toolTip() or btn.text().replace("\n", " ")
                btn.setText(self._format_quick_label(source_text, compact=True))
            except Exception:
                pass

    def _tooltip_text_for(self, widget) -> str:
        try:
            tip = str(widget.toolTip() or "").strip()
        except Exception:
            tip = ""
        if tip:
            return tip
        try:
            return str(widget.text() or "").replace("\n", " ").strip()
        except Exception:
            return ""

    def _show_tooltip_now(self, widget, local_pos: QPoint | None = None):
        if widget is None:
            return
        text = self._tooltip_text_for(widget)
        if not text:
            return
        try:
            if local_pos is None:
                local_pos = widget.rect().center()
        except Exception:
            local_pos = QPoint(0, 0)
        try:
            anchor = widget.mapToGlobal(local_pos)
        except Exception:
            anchor = QPoint()
        try:
            last_anchor = getattr(self, "_tooltip_last_anchor", None)
            same_widget = widget is getattr(self, "_tooltip_last_widget", None)
            same_text = text == getattr(self, "_tooltip_last_text", "")
            if same_widget and same_text and isinstance(last_anchor, QPoint):
                if abs(last_anchor.x() - anchor.x()) <= 6 and abs(last_anchor.y() - anchor.y()) <= 6:
                    return
        except Exception:
            pass
        try:
            QToolTip.showText(anchor, text, widget, widget.rect(), 3000)
            self._tooltip_last_widget = widget
            self._tooltip_last_text = text
            self._tooltip_last_anchor = QPoint(anchor)
        except Exception:
            pass

    def _hide_tooltip_now(self):
        try:
            QToolTip.hideText()
        except Exception:
            pass
        self._tooltip_last_widget = None
        self._tooltip_last_text = ""
        self._tooltip_last_anchor = None

    def eventFilter(self, watched, event):
        try:
            etype = event.type()
        except Exception:
            etype = None
        if watched in (
            getattr(self, "btn_home", None),
            getattr(self, "btn_projects", None),
            getattr(self, "btn_preview", None),
            getattr(self, "btn_recent", None),
            getattr(self, "btn_publish", None),
            getattr(self, "btn_resume", None),
            getattr(self, "quick_section_label", None),
        ):
            try:
                if etype in (QEvent.Enter, QEvent.ToolTip):
                    self._show_tooltip_now(watched)
                elif etype == QEvent.MouseMove:
                    self._show_tooltip_now(watched, event.position().toPoint())
                elif etype in (QEvent.Leave, QEvent.Hide, QEvent.FocusOut):
                    self._hide_tooltip_now()
            except Exception:
                pass
        return super().eventFilter(watched, event)

    def enterEvent(self, event):
        try:
            self.hover_entered.emit()
        except Exception:
            pass
        try:
            super().enterEvent(event)
        except Exception:
            pass

    def showEvent(self, event):
        try:
            self._apply_responsive_layout()
        except Exception:
            pass
        try:
            super().showEvent(event)
        except Exception:
            pass

    def resizeEvent(self, event):
        try:
            self._apply_responsive_layout()
        except Exception:
            pass
        try:
            super().resizeEvent(event)
        except Exception:
            pass

    def leaveEvent(self, event):
        try:
            self.hover_left.emit()
        except Exception:
            pass
        try:
            super().leaveEvent(event)
        except Exception:
            pass


class LeftEdgeHotZone(QWidget):
    hover_entered = Signal()
    hover_left = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("left-nav-hotzone")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self._active_key = "home"
        self._marker_y = {"home": None, "browser": None, "player": None}
        self._tooltip_anchor = None

    def set_active(self, nav_key: str, marker_y: dict | None = None, tooltip_text: str | None = None):
        try:
            self._active_key = str(nav_key or "home")
        except Exception:
            self._active_key = "home"
        if isinstance(marker_y, dict):
            try:
                self._marker_y.update(marker_y)
            except Exception:
                pass
        try:
            if tooltip_text:
                self.setToolTip(str(tooltip_text))
        except Exception:
            pass
        try:
            self.update()
        except Exception:
            pass

    def _fallback_y(self, key: str) -> int:
        h = max(1, self.height())
        if key == "home":
            return int(h * 0.34)
        if key == "browser":
            return int(h * 0.48)
        if key == "player":
            return int(h * 0.62)
        return int(h * 0.34)

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            key = str(getattr(self, "_active_key", "home") or "home")
            y0 = None
            try:
                y0 = (getattr(self, "_marker_y", {}) or {}).get(key, None)
            except Exception:
                y0 = None
            if y0 is None:
                y0 = self._fallback_y(key)
            cx = max(0, int(self.width() / 2))
            cy = max(0, min(self.height(), int(y0)))
            r = 3
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#7F56D9"))
            p.drawEllipse(QPoint(cx, cy), r, r)
            p.end()
        except Exception:
            pass

    def enterEvent(self, event):
        try:
            self._show_tooltip(QCursor.pos())
        except Exception:
            pass
        try:
            self.hover_entered.emit()
        except Exception:
            pass
        try:
            super().enterEvent(event)
        except Exception:
            pass

    def leaveEvent(self, event):
        try:
            self._hide_tooltip()
        except Exception:
            pass
        try:
            self.hover_left.emit()
        except Exception:
            pass
        try:
            super().leaveEvent(event)
        except Exception:
            pass

    def mouseMoveEvent(self, event):
        try:
            self._show_tooltip(self.mapToGlobal(event.position().toPoint()))
        except Exception:
            pass
        try:
            super().mouseMoveEvent(event)
        except Exception:
            pass

    def _show_tooltip(self, anchor: QPoint):
        try:
            text = str(self.toolTip() or "").strip()
        except Exception:
            text = ""
        if not text:
            return
        try:
            last_anchor = getattr(self, "_tooltip_anchor", None)
            if isinstance(last_anchor, QPoint):
                if abs(last_anchor.x() - anchor.x()) <= 6 and abs(last_anchor.y() - anchor.y()) <= 6:
                    return
        except Exception:
            pass
        try:
            QToolTip.showText(anchor, text, self, self.rect(), 2500)
            self._tooltip_anchor = QPoint(anchor)
        except Exception:
            pass

    def _hide_tooltip(self):
        try:
            QToolTip.hideText()
        except Exception:
            pass
        self._tooltip_anchor = None
