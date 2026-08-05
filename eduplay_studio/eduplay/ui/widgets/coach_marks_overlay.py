from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QCheckBox, QHBoxLayout
from PySide6.QtCore import Qt, QRect, Signal, QPoint, QTimer
from PySide6.QtGui import QPainter, QColor, QPen


class CoachMarksOverlay(QWidget):
    finished = Signal(bool)

    def __init__(self, parent: QWidget, marks: list[tuple[QWidget, str]], lang: str = "en"):
        super().__init__(parent)
        self._lang = str(lang or "en")
        self._marks = [(w, str(t or "")) for (w, t) in (marks or []) if w is not None]
        self._bubbles: list[QFrame] = []
        self._targets: list[QWidget] = []
        self._dismiss_check = None
        self._done_btn = None
        self._fallback_lbl = None
        self._footer = None
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Keep the onboarding as a child overlay of the main window.
        # Using Qt.Tool here creates a separate native window on Windows,
        # which can render the dimmed background as an opaque black layer.
        self.setFocusPolicy(Qt.NoFocus)
        self.setMouseTracking(True)
        self._build_ui()

    def _build_ui(self):
        for w, text in self._marks:
            bubble = QFrame(self)
            bubble.setObjectName("coach-bubble")
            bubble.setAttribute(Qt.WA_StyledBackground, True)
            lbl = QLabel(text, bubble)
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lay = QHBoxLayout(bubble)
            lay.setContentsMargins(14, 12, 14, 12)
            lay.addWidget(lbl)
            bubble.setStyleSheet(
                """
                #coach-bubble {
                    background-color: rgba(30,41,59,0.95);
                    border: 1px solid rgba(127,86,217,0.9);
                    border-radius: 14px;
                }
                #coach-bubble QLabel {
                    color: #F8FAFC;
                    font-size: 14px;
                    font-weight: 600;
                    line-height: 1.4;
                }
                """
            )
            bubble.hide()
            self._bubbles.append(bubble)
            self._targets.append(w)

        self._fallback_lbl = QLabel(self)
        self._fallback_lbl.setAlignment(Qt.AlignCenter)
        self._fallback_lbl.setWordWrap(True)
        self._fallback_lbl.setStyleSheet(
            "color:#F8FAFC;font-size:16px;font-weight:600;background:transparent;padding:24px;"
        )
        self._fallback_lbl.hide()

        try:
            from eduplay.core.i18n import I18n

            dismiss_text = I18n.t("onboarding.dismiss", self._lang)
        except Exception:
            dismiss_text = "Đừng hiện lại" if self._lang == "vi" else "Don't show again"
        try:
            from eduplay.core.i18n import I18n

            done_text = I18n.t("onboarding.done", self._lang)
        except Exception:
            done_text = "Xong" if self._lang == "vi" else "Done"

        # Group the Done button + "don't show again" checkbox into a single
        # footer pill so they stay together and never float loose at the
        # extreme screen corner (which previously landed on the taskbar).
        self._footer = QFrame(self)
        self._footer.setObjectName("coach-footer")
        self._footer.setAttribute(Qt.WA_StyledBackground, True)
        self._footer.setStyleSheet(
            """
            #coach-footer {
                background-color: rgba(15,23,42,0.92);
                border: 1px solid rgba(127,86,217,0.6);
                border-radius: 14px;
            }
            #coach-footer QCheckBox { color:#F8FAFC; font-weight:700; background:transparent; }
            #coach-footer QPushButton {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 800;
                font-size: 14px;
            }
            #coach-footer QPushButton:hover { background-color: #6941C6; }
            """
        )
        footer_lay = QHBoxLayout(self._footer)
        footer_lay.setContentsMargins(16, 10, 16, 10)
        footer_lay.setSpacing(12)
        footer_lay.addStretch(1)
        self._dismiss_check = QCheckBox(dismiss_text, self._footer)
        self._dismiss_check.setCursor(Qt.PointingHandCursor)
        footer_lay.addWidget(self._dismiss_check)
        self._done_btn = QPushButton(done_text, self._footer)
        self._done_btn.setCursor(Qt.PointingHandCursor)
        self._done_btn.setFocusPolicy(Qt.NoFocus)
        footer_lay.addWidget(self._done_btn)
        self._done_btn.clicked.connect(self._on_done_clicked)

    def _on_done_clicked(self):
        try:
            dont_show = bool(self._dismiss_check.isChecked()) if self._dismiss_check else False
        except Exception:
            dont_show = False
        try:
            self.hide()
        except Exception:
            pass
        try:
            self.finished.emit(dont_show)
        except Exception:
            pass
        try:
            self.deleteLater()
        except Exception:
            pass

    def mousePressEvent(self, event):
        try:
            if not event or event.button() != Qt.LeftButton:
                super().mousePressEvent(event)
                return
        except Exception:
            try:
                super().mousePressEvent(event)
            except Exception:
                pass
            return

        try:
            p = event.position().toPoint() if hasattr(event, "position") else event.pos()
        except Exception:
            p = None

        target = None
        if p is not None:
            for w in self._targets:
                r = self._target_rect(w)
                try:
                    if r.contains(p):
                        target = w
                        break
                except Exception:
                    continue

        if target is None:
            try:
                super().mousePressEvent(event)
            except Exception:
                pass
            return

        try:
            dont_show = bool(self._dismiss_check.isChecked()) if self._dismiss_check else False
        except Exception:
            dont_show = False

        click_cb = getattr(target, "click", None)
        try:
            self.hide()
        except Exception:
            pass
        try:
            self.finished.emit(dont_show)
        except Exception:
            pass
        try:
            self.deleteLater()
        except Exception:
            pass

        if callable(click_cb):
            try:
                QTimer.singleShot(0, click_cb)
            except Exception:
                pass

    def showEvent(self, event):
        try:
            self.setGeometry(self.parentWidget().rect())
        except Exception:
            pass
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass
        try:
            self._schedule_reposition()
        except Exception:
            pass
        try:
            visible_count = 0
            for b in self._bubbles:
                if b.isVisible():
                    visible_count += 1
                b.show()
                b.raise_()
            if self._fallback_lbl:
                if visible_count == 0:
                    self._fallback_lbl.show()
                    self._fallback_lbl.raise_()
                else:
                    self._fallback_lbl.hide()
        except Exception:
            pass
        try:
            super().showEvent(event)
        except Exception:
            pass

    def resizeEvent(self, event):
        try:
            self._reposition()
        except Exception:
            pass
        try:
            super().resizeEvent(event)
        except Exception:
            pass

    def _target_rect(self, w: QWidget) -> QRect:
        try:
            top_left = w.mapTo(self, QPoint(0, 0))
            return QRect(top_left.x(), top_left.y(), w.width(), w.height())
        except Exception:
            return QRect(0, 0, 0, 0)

    def _is_edge_strip(self, r: QRect) -> bool:
        """A thin full-height target like the left-edge hover hotzone.

        Such targets are invisible strips; placing a bubble directly beside
        them lands on top of card content, so they need special placement.
        """
        try:
            if r.width() <= 12 and r.height() >= int(self.height() * 0.6):
                return True
        except Exception:
            pass
        return False

    def _is_large_tile(self, r: QRect) -> bool:
        """A big clickable card/tile such as the home action cards.

        For large tiles we want the description bubble clearly outside the
        highlight area, usually centered below or above the card, instead of
        floating over the card itself.
        """
        try:
            if r.width() >= 150 and r.height() >= 150:
                return True
            if r.width() >= int(self.width() * 0.18) and r.height() >= int(self.height() * 0.22):
                return True
        except Exception:
            pass
        return False

    def _schedule_reposition(self):
        """Reposition now and retry a few times so bubbles track targets whose
        geometry settles after the home entrance animation / layout pass."""
        try:
            self._reposition()
        except Exception:
            pass
        try:
            for ms in (60, 220, 600):
                QTimer.singleShot(ms, self._reposition)
        except Exception:
            pass

    def _reposition(self):
        margin = 20
        footer_h = self._footer.height() if getattr(self, "_footer", None) else 0
        # Keep bubbles clear of the footer pill at the bottom.
        footer_reserved = max(80, int(footer_h) + 24)
        max_bubble_w = int(min(340, max(220, self.width() * 0.26)))
        visible_count = 0
        for idx, w in enumerate(self._targets):
            bubble = self._bubbles[idx]
            r = self._target_rect(w)
            if r.width() <= 0 or r.height() <= 0:
                bubble.hide()
                continue
            visible_count += 1
            bubble.setFixedWidth(max_bubble_w)
            try:
                bubble.adjustSize()
            except Exception:
                pass
            bw = bubble.width()
            bh = bubble.height()

            # Thin full-height edge strip (e.g. left-edge hover hotzone):
            # the painted highlight already marks the edge, so keep the bubble
            # near the left edge but above the footer, well away from the cards.
            if self._is_edge_strip(r):
                x = max(margin, r.right() + margin)
                y = max(margin, self.height() - footer_reserved - bh - margin)
                bubble.move(int(x), int(y))
                continue

            # Large home cards: center the bubble below the card (or above if
            # there is no room), so the description sits right under each of
            # the three main buttons instead of overlapping them.
            if self._is_large_tile(r):
                center_x = int(r.center().x() - bw / 2)
                x = max(margin, min(self.width() - bw - margin, center_x))
                below_y = r.bottom() + margin
                above_y = r.top() - margin - bh
                if below_y + bh <= self.height() - footer_reserved:
                    y = below_y
                elif above_y >= margin:
                    y = above_y
                else:
                    y = max(margin, min(self.height() - footer_reserved - bh, int((self.height() - footer_reserved - bh) / 2)))
                bubble.move(int(x), int(y))
                continue

            center_x = int(r.center().x() - bw / 2)
            center_y = int(r.center().y() - bh / 2)
            right_pos = (r.right() + margin, center_y)
            left_pos = (r.left() - margin - bw, center_y)
            above_pos = (center_x, r.top() - margin - bh)
            below_pos = (center_x, r.bottom() + margin)

            if r.bottom() >= (self.height() - footer_reserved - 40):
                candidates = (above_pos, right_pos, left_pos, below_pos)
            elif r.left() <= int(self.width() * 0.12):
                candidates = (right_pos, below_pos, above_pos, left_pos)
            elif r.right() >= int(self.width() * 0.88):
                candidates = (left_pos, below_pos, above_pos, right_pos)
            else:
                candidates = (above_pos, right_pos, left_pos, below_pos)

            x = margin
            y = margin
            placed = False
            for cand_x, cand_y in candidates:
                fits_h = margin <= cand_x and (cand_x + bw) <= (self.width() - margin)
                fits_v = margin <= cand_y and (cand_y + bh) <= (self.height() - footer_reserved)
                if fits_h and fits_v:
                    x, y = cand_x, cand_y
                    placed = True
                    break
            if not placed:
                x = max(margin, min(self.width() - bw - margin, candidates[0][0]))
                y = max(margin, min(self.height() - footer_reserved - bh, candidates[0][1]))
            bubble.move(int(x), int(y))

        if self._fallback_lbl:
            try:
                if visible_count == 0:
                    self._fallback_lbl.show()
                    self._fallback_lbl.raise_()
                    fw = max(200, int(self.width() * 0.5))
                    fh = max(80, int(self.height() * 0.22))
                    fx = int((self.width() - fw) / 2)
                    fy = int((self.height() - fh) / 2 - footer_reserved / 2)
                    if fy < margin:
                        fy = margin
                    self._fallback_lbl.setGeometry(fx, fy, fw, fh)
                    self._fallback_lbl.setText(
                        "👋\\n" + (self._marks[0][1] if self._marks else "Welcome!")
                    )
                else:
                    self._fallback_lbl.hide()
            except Exception:
                pass

        if getattr(self, "_footer", None):
            try:
                self._footer.adjustSize()
                fw = self._footer.width()
                fh = self._footer.height()
                fx = int((self.width() - fw) / 2)
                fy = self.height() - fh - margin
                if fy < margin:
                    fy = margin
                self._footer.move(fx, fy)
                self._footer.show()
                self._footer.raise_()
            except Exception:
                pass

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.fillRect(self.rect(), QColor(15, 23, 42, 160))
            pen = QPen(QColor("#7F56D9"))
            # Qt draws the pen centered on the rectangle path. With a 2 px pen
            # and a 1 px inset, the outer edge of the highlight lands exactly
            # on the widget's visible edge instead of floating outside it.
            pen.setWidth(2)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            for w in self._targets:
                r = self._target_rect(w)
                if r.width() <= 0 or r.height() <= 0:
                    continue
                rr = r.adjusted(1, 1, -1, -1)
                p.drawRoundedRect(rr, 16, 16)
            p.end()
        except Exception:
            pass
