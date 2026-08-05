from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QFrame, QBoxLayout
from PySide6.QtCore import Qt, Signal


class WhatsNewDialog(QDialog):
    closed = Signal(bool)

    def __init__(self, parent=None, lang: str = "en"):
        super().__init__(parent)
        self._lang = str(lang or "en")
        self._theme = self._detect_theme()
        try:
            from eduplay.core.i18n import I18n

            dismiss_text = I18n.t("onboarding.dismiss", self._lang)
        except Exception:
            dismiss_text = "Đừng hiện lại" if self._lang == "vi" else "Don't show again"
        self._dont_show = QCheckBox(dismiss_text)
        self._build()

    def _t(self, vi: str, en: str) -> str:
        return vi if self._lang == "vi" else en

    def _tr(self, key: str, fallback: str) -> str:
        try:
            from eduplay.core.i18n import I18n

            val = I18n.t(str(key or ""), self._lang)
            if isinstance(val, str) and val.strip() and val != key:
                return val.replace("\\n", "\n")
        except Exception:
            pass
        try:
            return str(fallback).replace("\\n", "\n")
        except Exception:
            return fallback

    def _detect_theme(self) -> str:
        try:
            from eduplay.core.settings_manager import SettingsManager

            theme = SettingsManager().get_theme() or "dark"
            if str(theme).lower() in ("dark", "light"):
                return str(theme).lower()
        except Exception:
            pass
        return "dark"

    def _build(self):
        self.setWindowTitle(self._tr("whats_new.rc2.window_title", self._t("Có gì mới", "What's new")))
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("whats-new-dialog")

        if self._theme == "light":
            dialog_bg = "#F8FBFF"
            dialog_border = "#D7E1EE"
            title_color = "#0F172A"
            subtitle_color = "#475467"
            card_bg = "#FFFFFF"
            card_border = "#DCE5F0"
            card_head = "#111827"
            card_body = "#475467"
            checkbox_color = "#475467"
            button_bg = "#7F56D9"
            button_hover = "#6941C6"
        else:
            dialog_bg = "#0F172A"
            dialog_border = "#243145"
            title_color = "#F8FAFC"
            subtitle_color = "#94A3B8"
            card_bg = "#162133"
            card_border = "#2B3A4F"
            card_head = "#F8FAFC"
            card_body = "#C7D2E0"
            checkbox_color = "#C7D2E0"
            button_bg = "#8B5CF6"
            button_hover = "#7C3AED"

        self.setStyleSheet(
            f"""
            QDialog#whats-new-dialog {{
                background-color: {dialog_bg};
                border: 1px solid {dialog_border};
                border-radius: 18px;
            }}
            QCheckBox {{
                color: {checkbox_color};
                font-weight: 700;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {dialog_border};
                background-color: {card_bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {button_bg};
                border-color: {button_bg};
            }}
            QPushButton#whatsNewPrimary {{
                background: {button_bg};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 900;
                min-width: 90px;
            }}
            QPushButton#whatsNewPrimary:hover {{
                background: {button_hover};
            }}
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        title = QLabel(self._tr("whats_new.rc2.title", self._t("EduPlay Studio v1.0.0 RC2", "EduPlay Studio v1.0.0 RC2")))
        title.setWordWrap(True)
        title.setStyleSheet(f"QLabel{{font-size:20px;font-weight:900;color:{title_color};background:transparent;}}")
        root.addWidget(title)

        subtitle = QLabel(self._tr("whats_new.rc2.subtitle", self._t("Những thay đổi chính để thao tác nhanh hơn:", "Key updates to help you work faster:")))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"QLabel{{font-size:14px;font-weight:700;color:{subtitle_color};background:transparent;}}")
        root.addWidget(subtitle)

        cards = QBoxLayout(QBoxLayout.LeftToRight)
        self._cards_layout = cards
        cards.setSpacing(12)

        def _card(emoji: str, head: str, body: str) -> QFrame:
            c = QFrame()
            c.setAttribute(Qt.WA_StyledBackground, True)
            c.setStyleSheet(
                f"""
                QFrame{{
                    background:{card_bg};
                    border:1px solid {card_border};
                    border-radius:14px;
                }}
                QLabel{{background:transparent;border:none;padding:0px;margin:0px;}}
                QLabel#wn_emoji{{font-size:22px;}}
                QLabel#wn_head{{font-size:15px;font-weight:900;color:{card_head};}}
                QLabel#wn_body{{font-size:13px;font-weight:600;color:{card_body};}}
                """
            )
            lay = QVBoxLayout(c)
            lay.setContentsMargins(14, 12, 14, 12)
            lay.setSpacing(6)
            e = QLabel(emoji)
            e.setObjectName("wn_emoji")
            h = QLabel(head)
            h.setObjectName("wn_head")
            h.setWordWrap(True)
            b = QLabel(body)
            b.setObjectName("wn_body")
            b.setWordWrap(True)
            lay.addWidget(e)
            lay.addWidget(h)
            lay.addWidget(b, 1)
            return c

        cards.addWidget(
            _card(
                "🧭",
                self._tr("whats_new.rc2.card_toolbar.title", self._t("Thanh công cụ bên trái", "Left toolbar")),
                self._tr("whats_new.rc2.card_toolbar.body", self._t("Mở nhanh bằng cách đưa chuột sát mép trái màn hình.", "Hover near the left edge to open it instantly.")),
            )
        )
        cards.addWidget(
            _card(
                "🎓",
                self._tr("whats_new.rc2.card_modes.title", self._t("2 chế độ xuất bản", "2 export modes")),
                self._tr(
                    "whats_new.rc2.card_modes.body",
                    self._t(
                        "Học sinh: chỉ chọn 1 lần.\nGiảng dạy: được chọn lại, sửa và trực quan khi dạy.",
                        "Student: one attempt.\nTeaching: retry, adjust, clearer for class.",
                    ),
                ),
            )
        )
        root.addLayout(cards)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        self._dont_show.setCursor(Qt.PointingHandCursor)
        bottom.addWidget(self._dont_show)
        bottom.addStretch()

        btn = QPushButton(self._t("OK", "OK"))
        try:
            btn.setText(self._tr("whats_new.rc2.ok", btn.text()))
        except Exception:
            pass
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("whatsNewPrimary")
        btn.clicked.connect(self._on_close)
        bottom.addWidget(btn)
        root.addLayout(bottom)
        self._update_cards_layout()

    def resizeEvent(self, event):
        try:
            self._update_cards_layout()
        except Exception:
            pass
        try:
            super().resizeEvent(event)
        except Exception:
            pass

    def _update_cards_layout(self):
        try:
            cards = getattr(self, "_cards_layout", None)
            if not cards:
                return
            cards.setDirection(QBoxLayout.TopToBottom if self.width() < 640 else QBoxLayout.LeftToRight)
        except Exception:
            pass

    def _on_close(self):
        try:
            dont = bool(self._dont_show.isChecked())
        except Exception:
            dont = False
        try:
            self.closed.emit(dont)
        except Exception:
            pass
        try:
            self.accept()
        except Exception:
            pass
