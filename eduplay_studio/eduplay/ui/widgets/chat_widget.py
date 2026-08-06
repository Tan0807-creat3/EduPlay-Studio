from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QTextEdit, QPushButton, QScrollArea,
                                QFrame, QSizePolicy, QFileDialog, QGraphicsBlurEffect, QGraphicsDropShadowEffect, QMenu)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QTextCursor, QPalette, QColor, QTextOption, QKeyEvent
from eduplay.core.i18n import I18n
from eduplay.core.settings_manager import SettingsManager
from eduplay.ui.file_dialogs import get_open_file_names


class ChatInputTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        try:
            self.setFocusPolicy(Qt.StrongFocus)
        except Exception:
            pass
        try:
            self.setTabChangesFocus(False)
        except Exception:
            pass
        try:
            self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        except Exception:
            pass
        try:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent):
        try:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                try:
                    event.accept()
                except Exception:
                    pass
                owner = None
                try:
                    w = self.parentWidget()
                    while w is not None and not hasattr(w, "send_message"):
                        w = w.parentWidget()
                    owner = w
                except Exception:
                    owner = None
                if owner and hasattr(owner, "send_message"):
                    try:
                        owner.send_message()
                    except Exception:
                        pass
                return
        except Exception:
            pass
        super().keyPressEvent(event)


class ChatWidget(QWidget):
    message_sent = Signal(str)
    file_uploaded = Signal(str)
    dock_mode_changed = Signal(bool)
    width_mode_changed = Signal(str)
    detail_level_changed = Signal(str)
    visibility_changed = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_minimized = True
        self._busy = False
        try:
            self.language = SettingsManager().get_language() or 'en'
        except Exception:
            self.language = 'en'
        self._manual_positioned = False
        self._scale = 1.0
        self.is_docked = False
        self.width_mode = 'narrow'
        self.detail_level = 'chuẩn'
        self.messages = []
        self._pending_attachments = []
        self.setup_ui()
        try:
            self.set_language(self.language)
        except Exception:
            pass
        
    def setup_ui(self):
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        try:
            self.theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            self.theme = 'dark'

        self.chat_container = QWidget()
        self.chat_container.setObjectName("chat-container")
        if self.theme == 'dark':
            base_bg = 'rgba(18,20,28,0.88)'
            base_border = '#313543'
        else:
            base_bg = '#E6F7FF'
            base_border = '#93C5FD'
        docked = getattr(self, "is_docked", False)
        radius_style = "border-radius: 0px;"
        self.chat_container.setStyleSheet(f"""
            #chat-container {{
                background-color: {base_bg};
                border: 1px solid {base_border};
                {radius_style}
                padding: 0px;
            }}
        """)
        
        container_layout = QVBoxLayout(self.chat_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        container_layout.addWidget(header)
        
        # Chat area
        chat_area = self.create_chat_area()
        container_layout.addWidget(chat_area)
        
        # Input area
        input_area = self.create_input_area()
        container_layout.addWidget(input_area)
        try:
            container_layout.setStretch(0, 0)  # header
            container_layout.setStretch(1, 1)  # chat
            container_layout.setStretch(2, 0)  # input
        except Exception:
            pass
        
        layout.addWidget(self.chat_container)
        try:
            from PySide6.QtGui import QColor
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)
            shadow.setOffset(0, 10)
            shadow.setColor(QColor(0, 0, 0, 160))
            self.chat_container.setGraphicsEffect(shadow)
        except Exception:
            pass
        
        self.setMinimumSize(360, 460)
        
    def create_header(self):
        header = QWidget()
        header.setObjectName("chat-header")
        try:
            brand = SettingsManager().get("brand_color", "#10B981")
        except Exception:
            brand = "#10B981"
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            header_bg = 'linear-gradient(135deg, #1B1F2A, #222739)'
            btn_bg = '#111827'
            btn_hover_bg = '#1F2937'
            btn_border = '#374151'
            btn_fg = '#E5E7EB'
            close_bg = '#B91C1C'
            close_hover_bg = '#DC2626'
        else:
            header_bg = '#E6F7FF'
            btn_bg = '#EEF2FF'
            btn_hover_bg = '#E0EAFF'
            btn_border = '#7F56D9'
            btn_fg = '#7F56D9'
            close_bg = '#DC2626'
            close_hover_bg = '#EF4444'
        header.setStyleSheet(f"""
            #chat-header {{
                background: {header_bg};
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                padding: 4px 14px 10px 14px;
            }}
        """)
        header_btn_style = f"""
            QPushButton {{
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 16px;
                color: {btn_fg};
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
                padding: 0px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
                border-color: {btn_border};
            }}
        """
        close_btn_style = f"""
            QPushButton {{
                background-color: {close_bg};
                border: 1px solid {close_bg};
                border-radius: 16px;
                color: #FFFFFF;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
                padding: 0px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {close_hover_bg};
                border-color: {close_hover_bg};
            }}
        """
        layout = QHBoxLayout(header)
        try:
            layout.setContentsMargins(16, 10, 22, 10)
            layout.setSpacing(14)
            layout.setAlignment(Qt.AlignVCenter)
        except Exception:
            pass
        
        title = QLabel(self._t('title').upper())
        title.setStyleSheet(f"""
            QLabel {{
                color: {('#FFFFFF' if theme == 'dark' else '#1A1A1A')};
                font-weight: 800;
                font-size: 16px;
            }}
        """)
        self._title_label = title
        layout.addWidget(title)
        
        layout.addStretch()

        minimize_btn = QPushButton("–")
        minimize_btn.setStyleSheet(header_btn_style)
        minimize_btn.clicked.connect(self.toggle_minimize)
        try:
            minimize_btn.setToolTip(self._t('minimize'))
        except Exception:
            pass
        layout.addWidget(minimize_btn)
        
        # Close button
        close_btn = QPushButton("✖")
        close_btn.setStyleSheet(close_btn_style)
        try:
            if _ef: close_btn.setFont(_ef)
        except Exception:
            pass
        close_btn.clicked.connect(self.hide)
        try:
            close_btn.setToolTip(self._t('close'))
        except Exception:
            pass
        layout.addWidget(close_btn)

        self._header_btns = [minimize_btn, close_btn]
        self.chat_header = header
        try:
            for b in header.findChildren(QPushButton):
                try:
                    t = str(b.text() or "").strip()
                except Exception:
                    t = ""
                if t in ("⋯", "...", "…", "💬", "🗨", "🗨️", "💭"):
                    try:
                        b.setVisible(False)
                    except Exception:
                        pass
        except Exception:
            pass
        return header

    def create_chat_area(self):
        # Chat messages area - ScrollArea
        self.chat_view = QScrollArea()
        self.chat_view.setWidgetResizable(True)
        self.chat_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        try:
            self.chat_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        except Exception:
            pass
            
        self.chat_view.setFrameShape(QFrame.NoFrame)
        self.chat_view.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        # Container for messages
        self.chat_content = QWidget()
        self.chat_content.setObjectName("chat_content")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(16)
        self.chat_layout.addStretch() # Push messages to top (spacer at bottom)
        
        self.chat_view.setWidget(self.chat_content)
        
        theme = getattr(self, 'theme', 'dark')
        chat_bg = '#FFFFFF' if theme != 'dark' else '#020617'
        self.chat_content.setStyleSheet(f"#chat_content {{ background-color: {chat_bg}; }}")
        
        return self.chat_view
        
    def _render_message(self, sender, message, message_type):
        """Render a message as a bubble widget"""
        try:
            brand = SettingsManager().get("brand_color", "#7F56D9")
            theme = getattr(self, 'theme', SettingsManager().get_theme() or 'dark')
        except Exception:
            brand = "#7F56D9"
            theme = getattr(self, 'theme', 'dark')
            
        # Row container
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        # Message processing
        try:
            msg = str(message)
            import re
            msg = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            msg = msg.replace("\n", "<br>")
            msg = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", msg)
            msg = re.sub(r"\*(.+?)\*", r"<i>\1</i>", msg)
            msg = re.sub(r"__(.+?)__", r"<u>\1</u>", msg)
            msg = re.sub(
                r"```(.*?)```",
                r"<pre style='background:rgba(0,0,0,0.2); padding:8px; border-radius:6px; font-family:Consolas, \"Cascadia Mono\", \"Courier New\", monospace; white-space:pre-wrap;'>\1</pre>",
                msg,
                flags=re.DOTALL,
            )
            msg = re.sub(
                r"`(.*?)`",
                r"<code style='background:rgba(0,0,0,0.2); padding:2px 4px; border-radius:4px; font-family:Consolas, \"Cascadia Mono\", \"Courier New\", monospace;'>\1</code>",
                msg,
            )
        except Exception:
            msg = str(message)

        bubble = QLabel(msg)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setOpenExternalLinks(True)
        bubble.setTextFormat(Qt.RichText)
        
        # Styles
        if message_type == "user":
            bg = brand
            fg = "#FFFFFF"
            border = f"1px solid {brand}"
            radius_style = "border-radius: 18px; border-bottom-right-radius: 2px;"
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:
            if theme == 'dark':
                bg = "#1F2937"
                fg = "#F9FAFB"
                border = "1px solid #374151"
            else:
                bg = "#F3F4F6"
                fg = "#111827"
                border = "1px solid #E5E7EB"
            radius_style = "border-radius: 18px; border-bottom-left-radius: 2px;"
            row_layout.addWidget(bubble)
            row_layout.addStretch()
            
        bubble.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: {border};
                {radius_style}
                padding: 10px 16px;
                font-size: 13px;
                line-height: 1.4;
            }}
        """)
        
        # Max width
        try:
            max_w = int(self.chat_view.width() * 0.8)
        except:
            max_w = 280
        bubble.setMaximumWidth(max(200, max_w))
        
        # Add to layout before stretch
        try:
            cnt = self.chat_layout.count()
            if cnt > 0:
                item = self.chat_layout.itemAt(cnt - 1)
                if item.spacerItem():
                    self.chat_layout.insertWidget(cnt - 1, row)
                else:
                    self.chat_layout.addWidget(row)
            else:
                self.chat_layout.addWidget(row)
        except Exception:
            pass
            
        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        try:
            sb = self.chat_view.verticalScrollBar()
            sb.setValue(sb.maximum())
        except:
            pass

    def add_message(self, sender, message, message_type="user"):
        """Add a message to the chat display"""
        try:
            sender_s = str(sender or "").strip().lower()
        except Exception:
            sender_s = ""
        if (message_type != "user") and sender_s in ("ai", "system"):
            try:
                message = self._sanitize_ai_chat_text(message)
            except Exception:
                pass
        self.messages.append({"sender": sender, "message": message, "type": message_type})
        self._render_message(sender, message, message_type)

    def _sanitize_ai_chat_text(self, text):
        try:
            s = str(text or "")
        except Exception:
            s = ""
        if not s:
            return s
        try:
            import re
        except Exception:
            re = None
        try:
            s = re.sub(r"<think>[\s\S]*?</think>", "", s, flags=re.IGNORECASE) if re is not None else s
        except Exception:
            pass
        tool_names = (
            "CREATE_PROJECT",
            "OPEN_PROJECT",
            "ADD_QUESTION",
            "UPDATE_QUESTION",
            "SET_QUESTION_IMAGE",
            "SET_QUESTION_IMAGE_URL",
            "SEARCH_IMAGE",
            "UPDATE_GAME_CONFIG",
            "READ_PROJECT_DETAILS",
            "WEB_SEARCH",
            "WEB_FETCH",
        )
        lines = str(s or "").splitlines()
        out_lines = []
        for ln in lines:
            t = str(ln or "").strip()
            if not t:
                if out_lines and out_lines[-1] != "":
                    out_lines.append("")
                continue
            tl = t.upper()
            if tl.startswith("TOOL_ERROR:"):
                continue
            if re is not None and re.match(r"^\[TOOL_NAME\s*:\s*[A-Za-z0-9_]+\]\s*$", t):
                continue
            if re is not None and re.match(r"^\[(?:XEM_[A-Z0-9_]+)\]\s*$", t):
                continue
            if t.startswith("[") and (":" in t) and t.endswith("]"):
                try:
                    cmd = t[1 : t.find(":")].strip().upper()
                except Exception:
                    cmd = ""
                if cmd in tool_names:
                    continue
            if re is not None:
                m = re.match(r"^(?:[\-\*\u2022]?\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*", t)
                if m and str(m.group(1) or "").strip().upper() in tool_names:
                    continue
            out_lines.append(str(ln or ""))
        out = "\n".join(out_lines).strip()
        try:
            if len(out) >= 2 and ((out.startswith('"') and out.endswith('"')) or (out.startswith("'") and out.endswith("'"))):
                out2 = out[1:-1]
                out2 = out2.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                out = out2.strip()
        except Exception:
            pass
        return out

    def _format_rich_text(self, message) -> str:
        try:
            msg = str(message)
            import re
            msg = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            msg = msg.replace("\n", "<br>")
            msg = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", msg)
            msg = re.sub(r"\*(.+?)\*", r"<i>\1</i>", msg)
            msg = re.sub(r"__(.+?)__", r"<u>\1</u>", msg)
            msg = re.sub(
                r"```(.*?)```",
                r"<pre style='background:rgba(0,0,0,0.2); padding:8px; border-radius:6px; font-family:Consolas, \"Cascadia Mono\", \"Courier New\", monospace; white-space:pre-wrap;'>\1</pre>",
                msg,
                flags=re.DOTALL,
            )
            msg = re.sub(
                r"`(.*?)`",
                r"<code style='background:rgba(0,0,0,0.2); padding:2px 4px; border-radius:4px; font-family:Consolas, \"Cascadia Mono\", \"Courier New\", monospace;'>\1</code>",
                msg,
            )
            return msg
        except Exception:
            return str(message)

    def set_status(self, text: str, owner=None):
        try:
            theme = getattr(self, 'theme', SettingsManager().get_theme() or 'dark')
        except Exception:
            theme = getattr(self, 'theme', 'dark')

        row = getattr(self, "_status_row", None)
        bubble = getattr(self, "_status_bubble", None)
        if not row or not bubble:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            bubble = QLabel()
            bubble.setWordWrap(True)
            bubble.setTextInteractionFlags(Qt.NoTextInteraction)
            bubble.setTextFormat(Qt.RichText)

            if theme == 'dark':
                bg = "rgba(31,41,55,0.55)"
                fg = "#E5E7EB"
                border = "1px solid rgba(55,65,81,0.55)"
            else:
                bg = "rgba(243,244,246,0.8)"
                fg = "#111827"
                border = "1px solid rgba(229,231,235,0.9)"
            radius_style = "border-radius: 18px; border-bottom-left-radius: 2px;"

            bubble.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg};
                    color: {fg};
                    border: {border};
                    {radius_style}
                    padding: 10px 16px;
                    font-size: 12px;
                    line-height: 1.35;
                }}
            """)

            row_layout.addWidget(bubble)
            row_layout.addStretch()
            self._status_row = row
            self._status_bubble = bubble
            try:
                self._status_owner = owner
            except Exception:
                pass

            try:
                cnt = self.chat_layout.count()
                if cnt > 0:
                    item = self.chat_layout.itemAt(cnt - 1)
                    if item.spacerItem():
                        self.chat_layout.insertWidget(cnt - 1, row)
                    else:
                        self.chat_layout.addWidget(row)
                else:
                    self.chat_layout.addWidget(row)
            except Exception:
                pass
        else:
            try:
                self._status_owner = owner
            except Exception:
                pass

        try:
            bubble.setText(self._format_rich_text(text))
        except Exception:
            try:
                bubble.setText(str(text))
            except Exception:
                pass

        try:
            max_w = int(self.chat_view.width() * 0.8)
        except Exception:
            max_w = 280
        try:
            bubble.setMaximumWidth(max(200, max_w))
        except Exception:
            pass

        QTimer.singleShot(50, self._scroll_to_bottom)

    def clear_status(self, owner=None):
        try:
            if owner is not None and getattr(self, "_status_owner", None) != owner:
                return
        except Exception:
            pass
        row = getattr(self, "_status_row", None)
        if not row:
            return
        try:
            self.chat_layout.removeWidget(row)
        except Exception:
            pass
        try:
            row.deleteLater()
        except Exception:
            pass
        try:
            self._status_row = None
            self._status_bubble = None
            self._status_owner = None
        except Exception:
            pass

    def create_input_area(self):
        input_widget = QFrame()
        input_widget.setObjectName("chat-input")
        theme = getattr(self, 'theme', 'dark')
        input_bg = '#E6F7FF' if theme != 'dark' else 'rgba(27,31,42,0.7)'
        self._input_bg_style = f"#chat-input {{ background-color: {input_bg}; border-bottom-left-radius: 14px; border-bottom-right-radius: 14px; padding: 10px; }}"
        input_widget.setStyleSheet(self._input_bg_style)

        root = QVBoxLayout(input_widget)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        attach_bar = QFrame()
        attach_bar.setObjectName("chat-attach-bar")
        attach_bar.setStyleSheet("background: transparent;")
        attach_layout = QHBoxLayout(attach_bar)
        attach_layout.setContentsMargins(0, 0, 0, 0)
        attach_layout.setSpacing(6)

        attach_scroll = QScrollArea()
        attach_scroll.setFrameShape(QFrame.NoFrame)
        attach_scroll.setWidgetResizable(True)
        attach_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        attach_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        attach_scroll.setFixedHeight(36)

        attach_inner = QWidget()
        attach_inner_layout = QHBoxLayout(attach_inner)
        attach_inner_layout.setContentsMargins(0, 0, 0, 0)
        attach_inner_layout.setSpacing(6)
        attach_inner_layout.addStretch()

        attach_scroll.setWidget(attach_inner)
        attach_layout.addWidget(attach_scroll)

        try:
            attach_bar.hide()
        except Exception:
            pass

        self._attach_bar = attach_bar
        self._attach_inner = attach_inner
        self._attach_inner_layout = attach_inner_layout
        self._attach_scroll = attach_scroll

        root.addWidget(attach_bar)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        input_box = QFrame()
        input_box.setObjectName("chat-input-box")
        input_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        ib_layout = QHBoxLayout(input_box)
        ib_layout.setContentsMargins(10, 8, 8, 8)
        ib_layout.setSpacing(8)

        self.upload_btn = QPushButton("📎")
        self.upload_btn.setStyleSheet("")
        try:
            from PySide6.QtGui import QFont as _QFont
            self.upload_btn.setFont(_QFont("Segoe UI Emoji", 16))
        except Exception:
            pass
        try:
            self.upload_btn.setProperty("no_bg", True)
        except Exception:
            pass
        self.upload_btn.clicked.connect(self.upload_file)
        ib_layout.addWidget(self.upload_btn, 0, Qt.AlignVCenter)

        self.input_field = ChatInputTextEdit(self)
        try:
            self.input_field.setPlaceholderText(self._t('input_placeholder'))
        except Exception:
            pass
        self.input_field.setStyleSheet("")
        try:
            self.input_field.textChanged.connect(self._update_input_height)
        except Exception:
            pass
        ib_layout.addWidget(self.input_field, 1)

        self.send_btn = QPushButton("➤")
        self.send_btn.setStyleSheet("")
        try:
            from PySide6.QtGui import QFont as _QFont
            self.send_btn.setFont(_QFont("Segoe UI Emoji", 16))
        except Exception:
            pass
        try:
            self.send_btn.setProperty("no_bg", True)
        except Exception:
            pass
        self.send_btn.clicked.connect(self.send_message)
        ib_layout.addWidget(self.send_btn, 0, Qt.AlignVCenter)

        layout.addWidget(input_box, 1)
        self._input_layout = layout
        try:
            self.upload_btn.setToolTip("Đính kèm" if getattr(self, "language", "vi") == "vi" else "Attach")
            self.send_btn.setToolTip(self._t('send'))
        except Exception:
            pass
        self._input_buttons = [self.upload_btn, self.send_btn]
        root.addWidget(row)
        try:
            self._update_input_height()
        except Exception:
            pass
        return input_widget

    def _render_attachments(self):
        try:
            pending = list(getattr(self, "_pending_attachments", []) or [])
        except Exception:
            pending = []

        bar = getattr(self, "_attach_bar", None)
        inner_layout = getattr(self, "_attach_inner_layout", None)
        if not bar or not inner_layout:
            return

        try:
            while inner_layout.count():
                item = inner_layout.takeAt(0)
                w = item.widget()
                if w:
                    try:
                        w.deleteLater()
                    except Exception:
                        pass
        except Exception:
            pass

        if not pending:
            try:
                bar.hide()
            except Exception:
                pass
            return

        try:
            bar.show()
        except Exception:
            pass

        try:
            theme = getattr(self, "theme", "dark")
            if theme == "dark":
                chip_bg = "rgba(19,22,33,0.95)"
                chip_fg = "#E5E7EB"
                chip_border = "#374151"
                chip_hover = "rgba(35,40,58,1.0)"
            else:
                chip_bg = "#FFFFFF"
                chip_fg = "#0F172A"
                chip_border = "#CBD5E1"
                chip_hover = "#F1F5F9"
        except Exception:
            chip_bg = "#FFFFFF"
            chip_fg = "#0F172A"
            chip_border = "#CBD5E1"
            chip_hover = "#F1F5F9"

        for fp in pending:
            try:
                import os
                name = os.path.basename(str(fp or "")) or str(fp or "")
            except Exception:
                name = str(fp or "")

            chip = QPushButton(f"📎 {name}  ×")
            chip.setStyleSheet(
                f"QPushButton {{ background-color: {chip_bg}; color: {chip_fg}; border: 1px solid {chip_border}; "
                f"border-radius: 10px; padding: 4px 10px; text-align: left; }}"
                f"QPushButton:hover {{ background-color: {chip_hover}; }}"
            )

            def _mk_remove(path):
                def _remove():
                    try:
                        cur = list(getattr(self, "_pending_attachments", []) or [])
                    except Exception:
                        cur = []
                    try:
                        cur = [p for p in cur if str(p) != str(path)]
                    except Exception:
                        pass
                    self._pending_attachments = cur
                    try:
                        self._render_attachments()
                    except Exception:
                        pass
                return _remove

            chip.clicked.connect(_mk_remove(fp))
            inner_layout.addWidget(chip)

        inner_layout.addStretch()

    def _update_input_height(self):
        te = getattr(self, "input_field", None)
        if not te:
            return
        try:
            scale = float(getattr(self, "_scale", 1.0) or 1.0)
        except Exception:
            scale = 1.0
        try:
            fm = te.fontMetrics()
            line_h = int(fm.lineSpacing())
        except Exception:
            line_h = 18
        pad = int(18 * scale)
        min_lines = 1
        max_lines = 3
        min_h = max(int((min_lines * line_h) + pad), int(34 * scale), 28)
        max_h = max(int((max_lines * line_h) + pad), min_h)
        desired = min_h
        try:
            desired = int(float(te.document().size().height()) + pad)
        except Exception:
            desired = min_h
        h = max(min_h, min(max_h, desired))
        try:
            te.setFixedHeight(h)
        except Exception:
            pass

    def apply_theme(self):
        try:
            self.theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            self.theme = 'dark'
            
        # Update chat content background
        if hasattr(self, 'chat_content'):
            chat_bg = '#FFFFFF' if self.theme != 'dark' else '#020617'
            self.chat_content.setStyleSheet(f"#chat_content {{ background-color: {chat_bg}; }}")
            
        # Re-render messages with new theme
        if hasattr(self, 'chat_layout') and hasattr(self, 'messages'):
            # Clear existing items
            while self.chat_layout.count():
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Re-add stretch to push messages up
            self.chat_layout.addStretch()
            
            # Re-render all messages
            for msg in self.messages:
                self._render_message(msg['sender'], msg['message'], msg['type'])
        
        if self.theme == 'dark':
            base_bg = 'rgba(18,20,28,0.88)'
            base_border = '#313543'
        else:
            base_bg = '#E6F7FF'
            base_border = '#93C5FD'
            
        docked = getattr(self, "is_docked", False)
        if docked:
            radius_style = "border-top-left-radius: 20px; border-bottom-left-radius: 20px; border-top-right-radius: 0px; border-bottom-right-radius: 0px;"
        else:
            radius_style = "border-radius: 20px;"
            
        if hasattr(self, 'chat_container'):
            self.chat_container.setStyleSheet(f"""
                #chat-container {{
                    background-color: {base_bg};
                    border: 1px solid {base_border};
                    {radius_style}
                    padding: 0px;
                }}
            """)
            
        input_bg = '#E6F7FF' if self.theme != 'dark' else 'rgba(27,31,42,0.7)'
        self._input_bg_style = f"#chat-input {{ background-color: {input_bg}; border-bottom-left-radius: 14px; border-bottom-right-radius: 14px; padding: 10px; }}"
        try:
            self.findChild(QWidget, "chat-input").setStyleSheet(self._input_bg_style)
        except Exception:
            pass

        try:
            brand = SettingsManager().get("brand_color", "#7F56D9")
        except Exception:
            brand = "#7F56D9"
        try:
            self.findChild(QWidget, "chat-header").setStyleSheet(f"""
                #chat-header {{
                    background-color: {brand};
                    background: linear-gradient(135deg, {brand}, #059669);
                    border-top-left-radius: 16px;
                    border-top-right-radius: 16px;
                    padding: 12px;
                }}
            """)
        except Exception:
            pass
            
        # Input field and buttons styling
        try:
            if self.theme == 'dark':
                input_bg_color = "rgba(30, 30, 40, 0.8)"
                input_text_color = "#FFFFFF"
                input_border = "1px solid #374151"
                placeholder_color = "#9CA3AF"
                box_bg = "rgba(19, 22, 33, 0.9)"
            else:
                input_bg_color = "#FFFFFF"
                input_text_color = "#1A1A1A"
                input_border = "1px solid #CBD5E1"
                placeholder_color = "#64748B"
                box_bg = "#FFFFFF"
                
            if hasattr(self, 'input_field') and self.input_field:
                self.input_field.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {input_bg_color};
                        color: {input_text_color};
                        border: none;
                        border-radius: 8px;
                        padding: 8px;
                    }}
                """)
            try:
                box = self.findChild(QFrame, "chat-input-box")
                if box:
                    box.setStyleSheet(f"QFrame#chat-input-box {{ background-color: {box_bg}; border: {input_border}; border-radius: 12px; }}")
            except Exception:
                pass
            try:
                self._render_attachments()
            except Exception:
                pass
                
            # Input buttons
            for btn in getattr(self, '_input_buttons', []):
                if not btn: continue
                
                # Default values based on theme
                if self.theme == 'dark':
                    bg_color = "rgba(19, 22, 33, 0.95)"
                    text_color = "#E5E7EB"
                    border = "1px solid #374151"
                    hover_bg = "rgba(35, 40, 58, 1.0)"
                else:
                    bg_color = "#FFFFFF"
                    text_color = "#64748B"
                    border = "1px solid #E2E8F0"
                    hover_bg = "#F8FAFC"
                
                if btn.property("no_bg"):
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            color: {text_color};
                            border: none;
                            border-radius: 10px;
                            padding: 0px;
                            min-width: 34px;
                            max-width: 34px;
                            min-height: 34px;
                            max-height: 34px;
                        }}
                        QPushButton:hover {{
                            background-color: {hover_bg};
                        }}
                    """)
                else:
                    if btn.property("primary"):
                        bg_color = "#7F56D9"
                        text_color = "#FFFFFF"
                        border = "none"
                        hover_bg = "#6941C6"
                    elif btn.property("success"):
                        bg_color = "#12B76A"
                        text_color = "#FFFFFF"
                        border = "none"
                        hover_bg = "#0F9C5A"
                    elif btn.property("warning"):
                        bg_color = "#F79009"
                        text_color = "#FFFFFF"
                        border = "none"
                        hover_bg = "#D97706"
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {bg_color};
                            color: {text_color};
                            border: {border};
                            border-radius: 999px;
                            padding: 0px;
                            min-width: 36px;
                            max-width: 36px;
                            min-height: 36px;
                            max-height: 36px;
                        }}
                        QPushButton:hover {{
                            background-color: {hover_bg};
                        }}
                    """)
        except Exception:
            pass

        try:
            self._resize_controls()
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self._resize_controls()
        except Exception:
            pass
        try:
            if not getattr(self, "_manual_positioned", False):
                from PySide6.QtWidgets import QApplication
                screen = QApplication.primaryScreen().availableGeometry()
                x = min(max(self.x(), screen.left()), screen.right() - self.width())
                y = min(max(self.y(), screen.top()), screen.bottom() - self.height())
                self.move(x, y)
        except Exception:
            pass

    def _resize_controls(self):
        w = max(self.width(), 320)
        h = max(self.height(), 360)
        scale = getattr(self, "_scale", 1.0)
        btn = max(int(32 * scale), min(int(48 * scale), int(h * 0.07)))
        radius = btn // 2
        theme = getattr(self, "theme", "dark")
        if theme == "dark":
            btn_bg = "rgba(19,22,33,0.95)"
            btn_hover = "rgba(35,40,58,1.0)"
            btn_border = "#374151"
            btn_fg = "#E5E7EB"
        else:
            btn_bg = "#EEF2FF"
            btn_hover = "#E0EAFF"
            btn_border = "#7F56D9"
            btn_fg = "#7F56D9"
        header_btns = getattr(self, '_header_btns', [])
        for idx, b in enumerate(header_btns):
            b.setMinimumSize(btn, btn)
            b.setMaximumSize(btn, btn)
            try:
                bg = btn_bg
                hover_bg = btn_hover
                fg = btn_fg
                border = btn_border
                if idx == 1:
                    bg = "#DC2626"
                    hover_bg = "#EF4444"
                    border = "#DC2626"
                    fg = "#FFFFFF"
                style = (
                    f"QPushButton {{ padding: 0px; margin: 0px; border-radius: {radius}px; "
                    f"background-color: {bg}; color: {fg}; border: 1px solid {border}; }}"
                    f"QPushButton:hover {{ background-color: {hover_bg}; }}"
                )
                b.setStyleSheet(style)
                hf = b.font()
                hf.setPointSizeF(max(9.0, min(14.0, 10.0 * float(scale))))
                b.setFont(hf)
            except Exception:
                pass
        try:
            if hasattr(self, "chat_header") and self.chat_header:
                header_h = max(int(btn * 1.6), int(44 * scale))
                self.chat_header.setMinimumHeight(header_h)
                self.chat_header.setMaximumHeight(header_h)
        except Exception:
            pass
        try:
            # Font size calculation preserved for potential future use or other widgets
            fsize = max(int(13 * scale), min(int(20 * scale), int(w * 0.035 * scale)))
            pad = max(int(8 * scale), min(int(18 * scale), int(w * 0.02 * scale)))
        except Exception:
            pass
        try:
            ih = max(int(40 * scale), min(int(56 * scale), int(h * 0.09)))
            for b in getattr(self, '_input_buttons', []):
                b.setMinimumHeight(ih)
                b.setMaximumHeight(ih)
                b.setMinimumWidth(ih)
                b.setMaximumWidth(ih)
                try:
                    bf = b.font()
                    bf.setPointSizeF(max(12.0, min(24.0, 15.0 * float(scale))))
                    b.setFont(bf)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            min_text = max(int(160 * scale), int(h * 0.5))
            if hasattr(self, 'chat_view'):
                # Adjust scroll area minimum height if needed, or just pass
                pass
        except Exception:
            pass
        try:
            if hasattr(self, "input_field") and self.input_field:
                ff = self.input_field.font()
                ff.setPointSizeF(max(12.0, min(22.0, 14.0 * float(scale))))
                self.input_field.setFont(ff)
                try:
                    self._update_input_height()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if hasattr(self, "_title_label") and self._title_label:
                f = self._title_label.font()
                base = 16.0
                f.setPointSizeF(max(12.0, min(22.0, base * float(scale))))
                self._title_label.setFont(f)
        except Exception:
            pass
        
    def set_scale(self, scale: float):
        try:
            self._scale = max(0.55, min(1.9, float(scale)))
        except Exception:
            self._scale = 1.0
        try:
            self._resize_controls()
        except Exception:
            pass

        
    def send_message(self):
        """Send user message"""
        try:
            if bool(getattr(self, "_busy", False)):
                return
        except Exception:
            pass
        message = ""
        try:
            message = str(self.input_field.toPlainText() or "").strip()
        except Exception:
            try:
                message = str(self.input_field.text() or "").strip()
            except Exception:
                message = ""
        try:
            files = list(getattr(self, "_pending_attachments", []) or [])
        except Exception:
            files = []
        if not message and not files:
            return

        display = message
        if files:
            try:
                import os
                names = [os.path.basename(str(p or "")) for p in files]
            except Exception:
                names = [str(p or "") for p in files]
            tail = ", ".join([n for n in names if n])[:220]
            if display:
                display = display + "\n\n" + ("Đính kèm: " if getattr(self, "language", "vi") == "vi" else "Attachments: ") + tail
            else:
                display = ("Đính kèm: " if getattr(self, "language", "vi") == "vi" else "Attachments: ") + tail
            
        # Add user message
        self.add_message("You", display, "user")
        
        # Clear input
        try:
            self.input_field.clear()
        except Exception:
            pass
        try:
            self._pending_attachments = []
            self._render_attachments()
        except Exception:
            pass
        try:
            self._update_input_height()
        except Exception:
            pass
        
        # Emit signal for AI processing
        payload = message
        if not payload:
            payload = "Phân tích các file đính kèm" if getattr(self, "language", "vi") == "vi" else "Analyze the attached files"
        if files:
            payload = payload + "\n\n[ATTACHMENTS]\n" + "\n".join([str(p) for p in files if str(p or "").strip()])
        self.message_sent.emit(payload)
        
        # Simulate AI response only when mock mode is enabled
        try:
            if bool(SettingsManager().get('ai.mock', False)):
                QTimer.singleShot(700, lambda: self.simulate_ai_response(message))
        except Exception:
            pass

    def set_busy(self, busy: bool):
        try:
            self._busy = bool(busy)
        except Exception:
            self._busy = bool(busy)
        disabled = bool(getattr(self, "_busy", False))
        try:
            if hasattr(self, "input_field") and self.input_field:
                self.input_field.setEnabled(not disabled)
                try:
                    if disabled:
                        self.input_field.setPlaceholderText(self._t('busy_placeholder'))
                    else:
                        self.input_field.setPlaceholderText(self._t('input_placeholder'))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if hasattr(self, "send_btn") and self.send_btn:
                self.send_btn.setEnabled(not disabled)
        except Exception:
            pass
        try:
            if hasattr(self, "upload_btn") and self.upload_btn:
                self.upload_btn.setEnabled(not disabled)
        except Exception:
            pass

    def set_language(self, lang: str):
        self.language = lang or 'en'
        try:
            # Update UI texts
            self.input_field.setPlaceholderText(self._t('input_placeholder'))
            if hasattr(self, '_header_btns'):
                try:
                    if len(self._header_btns) >= 5:
                        self._header_btns[0].setToolTip(self._t('dock'))
                        self._header_btns[1].setToolTip(self._t('wide'))
                        self._header_btns[2].setToolTip(self._t('detail'))
                        self._header_btns[3].setToolTip(self._t('minimize'))
                        self._header_btns[4].setToolTip(self._t('close'))
                except Exception:
                    pass
            try:
                self.findChild(QLabel).setText(self._t('title').upper())
            except Exception:
                pass
        except Exception:
            pass
        try:
            if not getattr(self, "messages", None):
                self.add_message("Edubot", self._t('welcome'), "ai")
        except Exception:
            pass

    def _t(self, key: str) -> str:
        mapping = {
            'welcome': 'chat.welcome',
            'title': 'chat.title',
            'input_placeholder': 'chat.input_placeholder',
            'send': 'chat.send',
            'upload': 'chat.upload',
            'suggest': 'chat.suggest',
            'copy': 'chat.copy',
            'dock': 'chat.dock',
            'wide': 'chat.wide',
            'detail': 'chat.detail',
            'brief': 'chat.brief',
            'standard': 'chat.standard',
            'detailed': 'chat.detailed',
            'minimize': 'chat.minimize',
            'close': 'chat.close'
        }
        lang = getattr(self, 'language', 'en')
        return I18n.t(mapping.get(key, key), lang)

    def upload_file(self):
        try:
            if getattr(self, "language", "vi") == "vi":
                caption = "Đính kèm tệp"
                filt = "Tài liệu (*.docx *.doc *.pdf *.txt);;Hình ảnh (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All Files (*.*)"
            else:
                caption = "Attach files"
                filt = "Documents (*.docx *.doc *.pdf *.txt);;Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All Files (*.*)"
            files = get_open_file_names(self, caption, "", filt)
            if not files:
                return
            cur = list(getattr(self, "_pending_attachments", []) or [])
            for fp in files:
                p = str(fp or "").strip()
                if not p:
                    continue
                if p not in cur:
                    cur.append(p)
            self._pending_attachments = cur
            self._render_attachments()
        except Exception as e:
            self.add_message("AI", f"Upload failed: {str(e)}", "ai")
        
    def simulate_ai_response(self, user_message):
        """Simulate AI response based on user message"""
        message_lower = user_message.lower()
        lang = getattr(self, 'language', 'en')
        if lang == 'vi':
            if any(k in message_lower for k in ["câu hỏi", "quiz", "trắc nghiệm"]):
                response = "Mình có thể tạo câu hỏi trắc nghiệm cho bạn! Hãy thử yêu cầu: ví dụ ‘Tạo 5 câu hỏi Toán lớp 6 về phân số’."
            elif "game" in message_lower or "trò chơi" in message_lower:
                response = "Mình giúp thiết kế trò chơi giáo dục! Bạn muốn gợi ý cơ chế trò chơi cho chủ đề của bạn, hay tạo Quiz Classic hoặc Câu Cá?"
            elif any(k in message_lower for k in ["giúp", "hỗ trợ", "assist", "help"]):
                response = "Mình sẵn sàng hỗ trợ! Mình có thể:\n• Tạo câu hỏi theo chủ đề\n• Gợi ý cơ chế/gameplay\n• Định dạng câu hỏi chuẩn\n• Gợi ý nội dung giáo dục\n\nBạn muốn làm việc với phần nào?"
            elif any(k in message_lower for k in ["xin chào", "chào", "hello", "hi"]):
                response = "Xin chào! Bạn muốn mình hỗ trợ gì để tạo game giáo dục hôm nay?"
            else:
                response = "Mình hiểu bạn đang cần trợ giúp. Bạn mô tả rõ hơn loại câu hỏi hoặc trò chơi giáo dục bạn muốn tạo nhé!"
        else:
            if "question" in message_lower or "quiz" in message_lower:
                response = "I can help you create quiz questions! Try asking me to generate questions about a specific topic, like 'Generate 5 questions about photosynthesis'."
            elif "game" in message_lower:
                response = "I can help you design educational games! Would you like me to suggest game mechanics for your topic, or help you create a fishing game or quiz classic?"
            elif "help" in message_lower or "assist" in message_lower:
                response = "I'm here to help! I can:\n• Generate quiz questions on any topic\n• Suggest game mechanics and designs\n• Help with question formatting\n• Provide educational content suggestions\n\nWhat would you like to work on?"
            elif "hello" in message_lower or "hi" in message_lower:
                response = "Hello! How can I assist you with creating educational games today?"
            elif "math" in message_lower or "science" in message_lower or "history" in message_lower:
                response = f"Great! I can help you create educational content about {message_lower.split()[0]}. What specific topic would you like to focus on?"
            else:
                response = "I understand you're looking for help. Could you tell me more about what kind of educational game or questions you'd like to create?"
            
        self.add_message("AI", response, "ai")
        
    def set_ai_response(self, response):
        """Set actual AI response (for real AI integration)"""
        try:
            self._last_ai_response = str(response)
        except Exception:
            self._last_ai_response = None
        self.add_message("AI", response, "ai")
        
    def toggle_minimize(self):
        """Toggle chat window minimize state"""
        try:
            self.is_minimized = True
        except Exception:
            pass
        try:
            self.hide()
        except Exception:
            pass
            
    def showEvent(self, event):
        """Handle show event"""
        super().showEvent(event)
        try:
            self.is_minimized = False
            if not getattr(self, "_manual_positioned", False):
                from PySide6.QtWidgets import QApplication
                screen = QApplication.primaryScreen().availableGeometry()
                x = screen.right() - self.width() - 20
                y = screen.bottom() - self.height() - 20
                if x < screen.left() + 10:
                    x = screen.left() + 10
                if y < screen.top() + 10:
                    y = screen.top() + 10
                self.move(x, y)
        except Exception:
            pass
        
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.LeftButton:
            try:
                dp = getattr(self, "drag_position", None)
                if dp is None:
                    dp = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    self.drag_position = dp
                self.move(event.globalPosition().toPoint() - dp)
                event.accept()
            except Exception:
                try:
                    self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                except Exception:
                    pass

