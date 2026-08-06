"""
Home Screen - Main landing screen with 3 action cards
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QFrame, QSpacerItem, QSizePolicy, QBoxLayout, QGraphicsOpacityEffect)
from PySide6.QtCore import Signal, Qt, QSize, QPoint, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer
from PySide6.QtGui import QFont, QIcon
from eduplay.ui.icon_factory import build_line_icon

from eduplay.core.asset_loader import materialize_asset_file

class HomeScreen(QWidget):
    """Home screen with 3 main action cards"""
    
    # Signals
    create_new_clicked = Signal()
    edit_project_clicked = Signal()
    play_game_clicked = Signal()
    open_recent_clicked = Signal()
    import_questions_clicked = Signal()
    quick_publish_clicked = Signal()
    resume_clicked = Signal()
    chat_toggled = Signal()
    help_requested = Signal()
    settings_requested = Signal()
    
    def __init__(self):
        super().__init__()
        try:
            self.setObjectName("home-root")
        except Exception:
            pass
        self._entrance_anim_refs = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create main content area
        self.create_main_content(layout)
        
        # Global chat button is handled by MainWindow
        
        self.setLayout(layout)
        
        self.apply_style(1.0)
    
    def create_main_content(self, layout):
        """Create main content area"""
        # Header help/settings are provided by MainWindow; avoid duplicates on Home
        
        # Main content area
        content_area = QFrame()
        content_layout = QVBoxLayout(content_area)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setSpacing(40)
        
        # Title (i18n)
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or "en"
            main_title = I18n.t("intro.title", l)
            sub_title = I18n.t("intro.tagline", l)
        except Exception:
            main_title = "EduPlay Studio"
            sub_title = "Learn. Create. Play."
        title_label = QLabel(main_title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._home_title_label = title_label
        subtitle_label = QLabel(sub_title)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._home_subtitle_label = subtitle_label
        content_layout.addWidget(title_label)
        content_layout.addWidget(subtitle_label)

        self.quick_actions_host = QFrame()
        self.quick_actions_host.setObjectName("home-quick-actions")
        quick_layout = QHBoxLayout(self.quick_actions_host)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(10)
        quick_layout.setAlignment(Qt.AlignCenter)
        self.quick_create_btn = self._create_quick_button("home.quick.create", "Tạo mới", self.on_create_new)
        self.quick_recent_btn = self._create_quick_button("home.quick.recent", "Mở gần đây", self.on_open_recent)
        self.quick_import_btn = self._create_quick_button("home.quick.import", "Import câu hỏi", self.on_import_questions)
        self.quick_publish_btn = self._create_quick_button("home.quick.publish", "Xuất bản nhanh", self.on_quick_publish)
        self.resume_btn = self._create_quick_button("home.quick.resume", "Tiếp tục chỉnh sửa", self.on_resume)
        self.resume_btn.setVisible(False)
        for btn in (
            self.quick_create_btn,
            self.quick_recent_btn,
            self.quick_import_btn,
            self.quick_publish_btn,
            self.resume_btn,
        ):
            quick_layout.addWidget(btn)
        content_layout.addWidget(self.quick_actions_host)
        # Quick actions now live in the left drawer to keep the home hero area cleaner.
        self.quick_actions_host.setVisible(False)
        
        self.cards_host = QFrame()
        try:
            self.cards_host.setObjectName("cards-host")
        except Exception:
            pass
        cards_layout = QHBoxLayout(self.cards_host)
        cards_layout.setSpacing(30)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            from PySide6.QtWidgets import QLayout
            cards_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        except Exception:
            pass
        
        # Create New card (i18n)
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or "en"
            create_title = I18n.t("home.create_title", l)
            create_desc = I18n.t("home.create_desc", l)
            create_btn = I18n.t("home.create_btn", l)
        except Exception:
            create_title = "CREATE"
            create_desc = "Create a new learning project with multiple question types and educational games."
            create_btn = "Start creating"
        self.create_card = self.create_action_card(
            icon="+",
            title=create_title,
            description=create_desc,
            button_text=create_btn,
            button_color="#7F56D9",
            on_click=self.on_create_new,
            refs_prefix="create"
        )
        cards_layout.addWidget(self.create_card)
        
        # Edit Project card (i18n)
        try:
            edit_title = I18n.t("home.edit_title", l)
            edit_desc = I18n.t("home.edit_desc", l)
            edit_btn = I18n.t("home.edit_btn", l)
        except Exception:
            edit_title = "EDIT"
            edit_desc = "Open and edit previously created projects."
            edit_btn = "Browse projects"
        self.edit_card = self.create_action_card(
            icon="✎",
            title=edit_title,
            description=edit_desc,
            button_text=edit_btn,
            button_color="#12B76A",
            on_click=self.on_edit_project,
            refs_prefix="edit"
        )
        cards_layout.addWidget(self.edit_card)
        
        # Play Game card (i18n)
        try:
            play_title = I18n.t("home.play_title", l)
            play_desc = I18n.t("home.play_desc", l)
            play_btn = I18n.t("home.play_btn", l)
        except Exception:
            play_title = "PLAY"
            play_desc = "Play test or publish the game you created."
            play_btn = "Play game"
        self.play_card = self.create_action_card(
            icon="▶",
            title=play_title,
            description=play_desc,
            button_text=play_btn,
            button_color="#F79009",
            on_click=self.on_play_game,
            refs_prefix="play"
        )
        cards_layout.addWidget(self.play_card)

        self.cards_layout = cards_layout
        content_layout.addWidget(self.cards_host)
        
        layout.addWidget(content_area, 1)
    
    def create_action_card(self, icon, title, description, button_text, button_color, on_click, refs_prefix: str = None):
        """Create an action card"""
        card = QFrame()
        card.setObjectName("action-card")
        
        card_layout = QVBoxLayout(card)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        card_layout.setSpacing(20)
        
        top_band = QFrame()
        top_band.setObjectName("card-topband")
        top_layout = QVBoxLayout(top_band)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.setSpacing(4)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("card-icon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setObjectName("card-title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(title_label)
        
        card_layout.addWidget(top_band)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setObjectName("card-description")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        try:
            desc_label.setMinimumHeight(48)
        except Exception:
            pass
        card_layout.addWidget(desc_label)

        button = QPushButton(button_text)
        button.setObjectName("card-button")
        try:
            if refs_prefix == "create":
                button.setProperty("primary", True)
            elif refs_prefix == "edit":
                button.setProperty("success", True)
            elif refs_prefix == "play":
                button.setProperty("warning", True)
        except Exception:
            pass
        button.clicked.connect(on_click)
        button.setMinimumHeight(44)
        card_layout.addWidget(button)
        
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        try:
            card.setMinimumHeight(240)
        except Exception:
            pass
        card.setCursor(Qt.PointingHandCursor)
        button.setCursor(Qt.PointingHandCursor)
        # Click anywhere on card to navigate, but avoid double-trigger when clicking the inner button.
        def _card_mouse_release(event, c=card, b=button, cb=on_click):
            try:
                if event.button() == Qt.MouseButton.LeftButton:
                    p = event.position().toPoint() if hasattr(event, "position") else event.pos()
                    child = c.childAt(p)
                    on_button = (child is b) or (child is not None and b.isAncestorOf(child))
                    if not on_button:
                        cb()
            except Exception:
                pass
            try:
                QFrame.mouseReleaseEvent(c, event)
            except Exception:
                pass
        card.mouseReleaseEvent = _card_mouse_release
        
        if refs_prefix:
            setattr(self, f"{refs_prefix}_title_label", title_label)
            setattr(self, f"{refs_prefix}_desc_label", desc_label)
            setattr(self, f"{refs_prefix}_button", button)
            setattr(self, f"{refs_prefix}_icon_label", icon_label)
        
        return card

    def _create_quick_button(self, i18n_key: str, fallback: str, callback):
        try:
            from eduplay.core.i18n import I18n
            from eduplay.core.settings_manager import SettingsManager
            l = SettingsManager().get_language() or "en"
            text = I18n.t(i18n_key, l)
            if not isinstance(text, str) or text == i18n_key:
                text = fallback
        except Exception:
            text = fallback
        btn = QPushButton(text)
        btn.setObjectName("home-quick-button")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(36)
        btn.clicked.connect(callback)
        return btn

    def set_quick_context(self, has_current_project: bool):
        try:
            self.resume_btn.setVisible(bool(has_current_project))
        except Exception:
            pass
    
    def _apply_dark_style(self, scale):
        root_bg = "#0B0E14"
        card_bg = "#161925"
        card_border = "rgba(57,64,82,0.45)"
        card_hover_border = "rgba(127,86,217,0.65)"
        desc_color = "#A0AEC0"
        title_color = "#E5E7EB"
        subtitle_color = "#A0AEC0"
        band_bg = "#0B0E14"
        topband_bg = "#1C2233"
        title_size = int(30 * scale)
        desc_size = int(18 * scale)
        icon_size = int(72 * scale)
        button_font = int(16 * scale)
        padding = int(30 * scale)
        style = f"""
        #home-root {{
            background: {root_bg};
        }}
        #cards-host {{
            background: {band_bg};
            border-radius: 24px;
            padding: {int(16*scale)}px;
        }}
        #action-card {{
            border: 1px solid {card_border};
            border-radius: 16px;
            padding: {padding}px;
            background-color: {card_bg};
        }}
        #action-card:hover {{
            border-color: {card_hover_border};
        }}
        #card-topband {{
            background-color: transparent;
            padding: {int(12*scale)}px {int(8*scale)}px {int(10*scale)}px {int(8*scale)}px;
            margin-bottom: {int(8*scale)}px;
        }}
        #card-icon {{
            font-size: {icon_size}px;
            margin-bottom: {int(4*scale)}px;
            color: {title_color};
            background-color: transparent;
            border: none;
        }}
        #card-title {{
            font-size: {title_size}px;
            font-weight: 800;
            margin-top: 0px;
            margin-bottom: 0px;
            background-color: transparent;
            border: none;
            padding: 0px;
            color: {title_color};
        }}
        #card-description {{
            font-size: {desc_size}px;
            line-height: 1.5;
            margin-bottom: {int(12*scale)}px;
            background-color: {card_bg};
            border-radius: {int(10*scale)}px;
            padding: {int(8*scale)}px {int(14*scale)}px;
            color: {desc_color};
        }}
        #card-button {{
            border: 2px solid;
            border-radius: 12px;
            padding: {int(10*scale)}px {int(22*scale)}px;
            font-size: {button_font}px;
            font-weight: 600;
        }}
        QPushButton#card-button[primary="true"] {{
            background-color: #7F56D9;
            border-color: #7F56D9;
            color: #FFFFFF;
        }}
        QPushButton#card-button[primary="true"]:hover {{
            background-color: #8B66E9;
            border-color: #8B66E9;
        }}
        QPushButton#card-button[success="true"] {{
            background-color: #12B76A;
            border-color: #12B76A;
            color: #FFFFFF;
        }}
        QPushButton#card-button[success="true"]:hover {{
            background-color: #22C77A;
            border-color: #22C77A;
        }}
        QPushButton#card-button[warning="true"] {{
            background-color: #F79009;
            border-color: #F79009;
            color: #FFFFFF;
        }}
        QPushButton#card-button[warning="true"]:hover {{
            background-color: #FF9F1A;
            border-color: #FF9F1A;
        }}
        #home-quick-button {{
            background-color: #182230;
            color: #E5E7EB;
            border: 1px solid rgba(127,86,217,0.35);
            border-radius: 18px;
            padding: {int(8*scale)}px {int(14*scale)}px;
            font-size: {int(13*scale)}px;
            font-weight: 700;
        }}
        #home-quick-button:hover {{
            background-color: #1D2939;
            border-color: rgba(127,86,217,0.8);
        }}
        """
        self.setStyleSheet(style)
        try:
            for pref in ("create", "edit", "play"):
                btn = getattr(self, f"{pref}_button", None)
                if btn:
                    btn.setMinimumHeight(int(40 * scale))
        except Exception:
            pass
        try:
            if hasattr(self, "_home_title_label") and self._home_title_label:
                main_title = int(60 * scale)
                self._home_title_label.setStyleSheet(
                    f"QLabel{{color:{title_color};font-size:{main_title}px;font-weight:800;margin-bottom:{int(16*scale)}px;padding-top:{int(6*scale)}px;}}"
                )
            if hasattr(self, "_home_subtitle_label") and self._home_subtitle_label:
                sub_title = int(22 * scale)
                self._home_subtitle_label.setStyleSheet(
                    f"QLabel{{color:{subtitle_color};font-size:{sub_title}px;font-weight:300;margin-bottom:{int(34*scale)}px;padding-bottom:{int(4*scale)}px;}}"
                )
        except Exception:
            pass
    def _apply_light_style(self, scale):
        root_bg = "transparent"
        card_bg = "#FFFFFF"
        card_border = "rgba(148,163,184,0.35)"
        card_hover_border = "rgba(127,86,217,0.55)"
        desc_color = "#4B5563"
        title_color = "#374151"
        subtitle_color = "#4B5563"
        band_bg = "rgba(255,255,255,0.75)"
        topband_bg = root_bg
        title_size = int(30 * scale)
        desc_size = int(18 * scale)
        icon_size = int(72 * scale)
        button_font = int(16 * scale)
        padding = int(30 * scale)
        try:
            self.setAttribute(Qt.WA_StyledBackground, True)
        except Exception:
            pass
        style = f"""
        HomeScreen, HomeScreen > QWidget, #home-root {{
            background: {root_bg};
        }}
        HomeScreen QLabel {{
            background: transparent;
        }}
        HomeScreen QFrame {{
            background: transparent;
        }}
        #cards-host {{
            background: {band_bg};
            border-radius: 24px;
            padding: {int(16*scale)}px;
            border: 1px solid rgba(148,163,184,0.30);
        }}
        #action-card {{
            border: 1px solid {card_border};
            border-radius: 16px;
            padding: {padding}px;
            background-color: {card_bg};
        }}
        #action-card:hover {{
            border-color: {card_hover_border};
        }}
        #card-topband {{
            background-color: transparent;
            padding: {int(12*scale)}px {int(8*scale)}px {int(10*scale)}px {int(8*scale)}px;
            margin-bottom: {int(8*scale)}px;
        }}
        #card-icon {{
            font-size: {icon_size}px;
            margin-bottom: {int(4*scale)}px;
            color: {title_color};
            background-color: transparent;
            border: none;
        }}
        #card-title {{
            font-size: {title_size}px;
            font-weight: 800;
            margin-top: 0px;
            margin-bottom: 0px;
            background-color: transparent;
            border: none;
            padding: 0px;
            color: {title_color};
        }}
        #card-description {{
            font-size: {desc_size}px;
            line-height: 1.5;
            margin-bottom: {int(12*scale)}px;
            background-color: {card_bg};
            border-radius: {int(10*scale)}px;
            padding: {int(8*scale)}px {int(14*scale)}px;
            color: {desc_color};
        }}
        #card-button {{
            border: 2px solid;
            border-radius: 12px;
            padding: {int(10*scale)}px {int(22*scale)}px;
            font-size: {button_font}px;
            font-weight: 600;
        }}
        QPushButton#card-button[primary="true"] {{
            background-color: #7F56D9;
            border-color: #7F56D9;
            color: #FFFFFF;
        }}
        QPushButton#card-button[primary="true"]:hover {{
            background-color: #8B66E9;
            border-color: #8B66E9;
        }}
        QPushButton#card-button[success="true"] {{
            background-color: #12B76A;
            border-color: #12B76A;
            color: #FFFFFF;
        }}
        QPushButton#card-button[success="true"]:hover {{
            background-color: #22C77A;
            border-color: #22C77A;
        }}
        QPushButton#card-button[warning="true"] {{
            background-color: #F79009;
            border-color: #F79009;
            color: #FFFFFF;
        }}
        QPushButton#card-button[warning="true"]:hover {{
            background-color: #FF9F1A;
            border-color: #FF9F1A;
        }}
        #home-quick-button {{
            background-color: rgba(255,255,255,0.92);
            color: #334155;
            border: 1px solid rgba(127,86,217,0.28);
            border-radius: 18px;
            padding: {int(8*scale)}px {int(14*scale)}px;
            font-size: {int(13*scale)}px;
            font-weight: 700;
        }}
        #home-quick-button:hover {{
            background-color: #F8FAFC;
            border-color: rgba(127,86,217,0.6);
        }}
        """
        self.setStyleSheet(style)
        try:
            for pref in ("create", "edit", "play"):
                btn = getattr(self, f"{pref}_button", None)
                if btn:
                    btn.setMinimumHeight(int(40 * scale))
        except Exception:
            pass
        try:
            if hasattr(self, "_home_title_label") and self._home_title_label:
                main_title = int(60 * scale)
                # Render gradient pixmap like splash animation
                try:
                    import os
                    from PySide6.QtGui import (QPainter, QLinearGradient, QColor,
                                               QFont, QFontMetrics, QFontDatabase,
                                               QImage, QPixmap, QPainterPath)
                    font_path = str(materialize_asset_file("eduplay/resources/fonts/FC-Ethnocentric-Rg.otf"))
                    family = None
                    if os.path.exists(font_path):
                        fid = QFontDatabase.addApplicationFont(font_path)
                        fams = QFontDatabase.applicationFontFamilies(fid)
                        if fams:
                            family = fams[0]
                    f = QFont(family or "Arial")
                    f.setPointSize(int(42 * scale))
                    f.setBold(True)
                    try:
                        f.setLetterSpacing(QFont.AbsoluteSpacing, -1.2)
                    except Exception:
                        pass
                    text = self._home_title_label.text() or "EduPlay Studio"
                    fm = QFontMetrics(f)
                    margin = 14
                    tw = fm.horizontalAdvance(text)
                    th = fm.height()
                    w = max(1, tw + margin * 2)
                    h = max(1, th + margin * 2)
                    img = QImage(w, h, QImage.Format.Format_ARGB32)
                    img.fill(0)
                    p = QPainter(img)
                    p.setRenderHint(QPainter.Antialiasing, True)
                    p.setRenderHint(QPainter.TextAntialiasing, True)
                    path = QPainterPath()
                    baseline = margin + fm.ascent()
                    path.addText(margin, baseline, f, text)
                    from PySide6.QtCore import Qt as _Qt
                    from PySide6.QtGui import QPen
                    outline = QPen(QColor(255, 255, 255, 200))
                    outline.setWidth(6)
                    outline.setJoinStyle(_Qt.MiterJoin)
                    p.setPen(outline)
                    p.setBrush(_Qt.NoBrush)
                    p.drawPath(path)
                    grad = QLinearGradient(0, margin, w, h - margin)
                    grad.setColorAt(0.0, QColor("#F59E0B"))
                    grad.setColorAt(0.5, QColor("#EF4444"))
                    grad.setColorAt(1.0, QColor("#8B5CF6"))
                    p.setPen(_Qt.NoPen)
                    p.setBrush(grad)
                    p.drawPath(path)
                    p.end()
                    pm = QPixmap.fromImage(img)
                    self._home_title_label.setPixmap(pm)
                    self._home_title_label.setText("")
                    self._home_title_label.setStyleSheet("background:transparent;")
                except Exception:
                    self._home_title_label.setStyleSheet(
                        f"QLabel{{color:{title_color};font-size:{main_title}px;font-weight:800;margin-bottom:{int(16*scale)}px;padding-top:{int(6*scale)}px;background:transparent;}}"
                    )
            if hasattr(self, "_home_subtitle_label") and self._home_subtitle_label:
                sub_title = int(22 * scale)
                self._home_subtitle_label.setStyleSheet(
                    f"QLabel{{color:{subtitle_color};font-size:{sub_title}px;font-weight:300;margin-bottom:{int(34*scale)}px;padding-bottom:{int(4*scale)}px;background:transparent;}}"
                )
        except Exception:
            pass

    def apply_style(self, scale):
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = SettingsManager().get_theme() or "dark"
        except Exception:
            theme = "dark"
        if theme == "dark":
            self._apply_dark_style(scale)
        else:
            self._apply_light_style(scale)

    def _lighter(self, hex_color):
        try:
            c = hex_color.lstrip('#')
            r = min(255, int(c[0:2], 16) + 20)
            g = min(255, int(c[2:4], 16) + 20)
            b = min(255, int(c[4:6], 16) + 20)
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color
    
    def create_chat_button(self):
        """Create floating chat button"""
        self.chat_button = QPushButton("")
        self.chat_button.setFixedSize(60, 60)
        try:
            self.chat_button.setIcon(build_line_icon("chat", "#FFFFFF", 26, stroke_width=2))
            self.chat_button.setIconSize(QSize(26, 26))
        except Exception:
            pass
        self.chat_button.setStyleSheet("""
            QPushButton {
                background-color: #7F56D9;
                border: none;
                border-radius: 30px;
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8B66E9;
            }
            QPushButton:pressed {
                background-color: #6B46C1;
            }
        """)
        
        # Position the button (will be set in resize event)
        self.chat_button.setParent(self)
        self.chat_button.clicked.connect(self.toggle_chat)
        self.chat_button.raise_()
        self.chat_button.show()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'chat_button'):
            btn_size = max(48, min(72, int(min(self.width(), self.height()) * 0.06)))
            self.chat_button.setFixedSize(btn_size, btn_size)
            x = self.width() - btn_size - 20
            y = self.height() - btn_size - 20
            self.chat_button.move(x, y)
        try:
            w_scale = self.width() / 1200 if self.width() else 1.0
            h_scale = self.height() / 800 if self.height() else 1.0
            scale = max(0.60, min(1.60, min(w_scale, h_scale)))
        except Exception:
            scale = 1.0
        if hasattr(self, 'help_btn'):
            size = max(40, min(64, int(self.width() * 0.04)))
            self.help_btn.setFixedSize(size, size)
        if hasattr(self, 'settings_btn'):
            size = max(40, min(64, int(self.width() * 0.04)))
            self.settings_btn.setFixedSize(size, size)
        try:
            if hasattr(self, 'cards_layout'):
                if self.width() < 1100:
                    self.cards_layout.setDirection(QBoxLayout.TopToBottom)
                    self.cards_layout.setSpacing(16)
                else:
                    self.cards_layout.setDirection(QBoxLayout.LeftToRight)
                    self.cards_layout.setSpacing(30)
        except Exception:
            pass
        try:
            self.apply_style(scale)
        except Exception:
            pass

    def refresh_theme(self):
        try:
            w_scale = self.width() / 1200 if self.width() else 1.0
            h_scale = self.height() / 800 if self.height() else 1.0
            scale = max(0.60, min(1.60, min(w_scale, h_scale)))
        except Exception:
            scale = 1.0
        try:
            self.apply_style(scale)
        except Exception:
            pass
        self.apply_style(scale)

    def set_language(self, lang: str):
        from eduplay.core.i18n import I18n
        l = lang or 'en'
        try:
            if hasattr(self, "_home_title_label"):
                self._home_title_label.setText(I18n.t("intro.title", l))
            if hasattr(self, "_home_subtitle_label"):
                self._home_subtitle_label.setText(I18n.t("intro.tagline", l))
            if hasattr(self, 'create_title_label'):
                self.create_title_label.setText(I18n.t('home.create_title', l))
            if hasattr(self, 'create_desc_label'):
                self.create_desc_label.setText(I18n.t('home.create_desc', l))
            if hasattr(self, 'create_button'):
                self.create_button.setText(I18n.t('home.create_btn', l))
            if hasattr(self, 'edit_title_label'):
                self.edit_title_label.setText(I18n.t('home.edit_title', l))
            if hasattr(self, 'edit_desc_label'):
                self.edit_desc_label.setText(I18n.t('home.edit_desc', l))
            if hasattr(self, 'edit_button'):
                self.edit_button.setText(I18n.t('home.edit_btn', l))
            if hasattr(self, 'play_title_label'):
                self.play_title_label.setText(I18n.t('home.play_title', l))
            if hasattr(self, 'play_desc_label'):
                self.play_desc_label.setText(I18n.t('home.play_desc', l))
            if hasattr(self, 'play_button'):
                self.play_button.setText(I18n.t('home.play_btn', l))
            if hasattr(self, 'quick_create_btn'):
                self.quick_create_btn.setText(I18n.t('home.quick.create', l))
            if hasattr(self, 'quick_recent_btn'):
                self.quick_recent_btn.setText(I18n.t('home.quick.recent', l))
            if hasattr(self, 'quick_import_btn'):
                self.quick_import_btn.setText(I18n.t('home.quick.import', l))
            if hasattr(self, 'quick_publish_btn'):
                self.quick_publish_btn.setText(I18n.t('home.quick.publish', l))
            if hasattr(self, 'resume_btn'):
                self.resume_btn.setText(I18n.t('home.quick.resume', l))
        except Exception:
            pass
    
    def on_create_new(self):
        """Handle create new button click"""
        self.create_new_clicked.emit()
    
    def on_edit_project(self):
        """Handle edit project button click"""
        self.edit_project_clicked.emit()
    
    def on_play_game(self):
        """Handle play game button click"""
        self.play_game_clicked.emit()

    def on_open_recent(self):
        self.open_recent_clicked.emit()

    def on_import_questions(self):
        self.import_questions_clicked.emit()

    def on_quick_publish(self):
        self.quick_publish_clicked.emit()

    def on_resume(self):
        self.resume_clicked.emit()
    
    def show_help(self):
        """Emit help request to MainWindow"""
        self.help_requested.emit()
    
    def show_settings(self):
        """Emit settings request to MainWindow"""
        self.settings_requested.emit()
    
    def toggle_chat(self):
        """Toggle AI chat widget"""
        self.chat_toggled.emit()

    def animate_cards_entrance(self):
        """Animate action cards from slightly below with fade-in."""
        try:
            cards = [getattr(self, "create_card", None), getattr(self, "edit_card", None), getattr(self, "play_card", None)]
            cards = [c for c in cards if c is not None]
            if not cards:
                return
            try:
                self._entrance_anim_refs = []
            except Exception:
                pass
            base_delay = 40
            stagger = 110
            lift = 26
            duration = 360
            for i, card in enumerate(cards):
                try:
                    end_pos = card.pos()
                    start_pos = QPoint(end_pos.x(), end_pos.y() + lift)
                    try:
                        card.move(start_pos)
                    except Exception:
                        pass
                    eff = card.graphicsEffect()
                    if not isinstance(eff, QGraphicsOpacityEffect):
                        eff = QGraphicsOpacityEffect(card)
                        card.setGraphicsEffect(eff)
                    eff.setOpacity(0.0)
                    pos_anim = QPropertyAnimation(card, b"pos", self)
                    pos_anim.setDuration(duration)
                    pos_anim.setStartValue(start_pos)
                    pos_anim.setEndValue(end_pos)
                    pos_anim.setEasingCurve(QEasingCurve.OutCubic)
                    op_anim = QPropertyAnimation(eff, b"opacity", self)
                    op_anim.setDuration(duration - 40)
                    op_anim.setStartValue(0.0)
                    op_anim.setEndValue(1.0)
                    op_anim.setEasingCurve(QEasingCurve.OutCubic)
                    grp = QParallelAnimationGroup(self)
                    grp.addAnimation(pos_anim)
                    grp.addAnimation(op_anim)
                    delay = base_delay + i * stagger
                    QTimer.singleShot(delay, grp.start)
                    self._entrance_anim_refs.append(grp)
                except Exception:
                    continue
        except Exception:
            pass

