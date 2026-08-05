import math
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QStyle

from eduplay.core.asset_loader import materialize_asset_file


_LEADING_ICON_RE = re.compile(
    r"^[\s\u2190-\u21FF\u2300-\u27BF\U0001F000-\U0001FAFF\U00002600-\U000027BF\ufe0f]+",
    re.UNICODE,
)

_STOCK_ICON_ASSETS = {
    "create": "eduplay/resources/icons/book.png",
    "edit": "eduplay/resources/icons/computer.png",
    "play": "eduplay/resources/icons/prize.png",
    "import": "eduplay/resources/icons/file-import.ico",
}

_ICON_GLYPHS = {
    "create": "+",
    "edit": "✎",
    "play": "▶",
    "settings": "⚙️",
    "help": "❓",
}

_ACTION_STANDARD_PIXMAPS = {
    "create": (QStyle.StandardPixmap.SP_FileDialogNewFolder,),
    "import": (
        QStyle.StandardPixmap.SP_DialogOpenButton,
        QStyle.StandardPixmap.SP_DirOpenIcon,
        QStyle.StandardPixmap.SP_FileIcon,
    ),
    "delete": (QStyle.StandardPixmap.SP_TrashIcon,),
}


def strip_icon_text(text: str | None) -> str:
    raw = " ".join(str(text or "").split())
    stripped = _LEADING_ICON_RE.sub("", raw).strip()
    return stripped or raw


def icon_glyph(kind: str) -> str:
    return _ICON_GLYPHS.get(str(kind or "").lower(), "")


def build_glyph_icon(kind: str, color_hex: str, size: int) -> QIcon:
    glyph = icon_glyph(kind)
    if not glyph:
        return QIcon()
    try:
        pix = QPixmap(int(size), int(size))
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        key = str(kind or "").lower()
        font_family = "Segoe UI Emoji" if key in {"help", "settings"} else "Segoe UI Symbol"
        font = QFont(font_family)
        font.setPixelSize(max(12, int(size * 0.82)))
        font.setBold(False)
        p.setFont(font)
        p.setPen(QColor(color_hex))
        fm = QFontMetricsF(font)
        bounds = fm.tightBoundingRect(glyph)
        x = (pix.width() - bounds.width()) / 2.0 - bounds.left()
        y = (pix.height() - bounds.height()) / 2.0 - bounds.top()
        p.drawText(x, y, glyph)
        p.end()
        return QIcon(pix)
    except Exception:
        return QIcon()


def build_stock_icon_pixmap(kind: str, size: int) -> QPixmap:
    asset_rel = _STOCK_ICON_ASSETS.get(str(kind or "").lower())
    if not asset_rel:
        return QPixmap()
    try:
        asset_path = materialize_asset_file(asset_rel)
        if not asset_path:
            return QPixmap()
        source = QPixmap(str(asset_path))
        if source.isNull():
            return QPixmap()
        scaled = source.scaled(int(size), int(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        canvas = QPixmap(int(size), int(size))
        canvas.fill(Qt.transparent)
        p = QPainter(canvas)
        x = max(0, (int(size) - scaled.width()) // 2)
        y = max(0, (int(size) - scaled.height()) // 2)
        p.drawPixmap(x, y, scaled)
        p.end()
        return canvas
    except Exception:
        return QPixmap()


def build_stock_icon(kind: str) -> QIcon:
    asset_rel = _STOCK_ICON_ASSETS.get(str(kind or "").lower())
    if not asset_rel:
        return QIcon()
    try:
        asset_path = materialize_asset_file(asset_rel)
        if not asset_path:
            return QIcon()
        icon = QIcon(str(asset_path))
        if not icon.isNull():
            return icon
    except Exception:
        pass
    return QIcon()


def build_standard_ui_icon(
    kind: str,
    style: QStyle | None = None,
    color_hex: str = "#374151",
    size: int = 18,
) -> QIcon:
    style_obj = style or QApplication.style()
    key = str(kind or "").lower()
    if key in {"help", "settings"}:
        glyph_icon = build_glyph_icon(key, color_hex, size)
        if not glyph_icon.isNull():
            return glyph_icon
    theme_names = {
        "help": (),
        "settings": (),
    }.get(key, ())
    for theme_name in theme_names:
        try:
            icon = QIcon.fromTheme(theme_name)
            if not icon.isNull():
                return icon
        except Exception:
            pass
    if style_obj is not None:
        fallback_pixmaps = {
            "help": (QStyle.StandardPixmap.SP_MessageBoxQuestion,),
            "settings": (
                QStyle.StandardPixmap.SP_FileDialogDetailedView,
                QStyle.StandardPixmap.SP_FileDialogInfoView,
                QStyle.StandardPixmap.SP_ComputerIcon,
            ),
        }.get(key, ())
        for pixmap_kind in fallback_pixmaps:
            try:
                icon = style_obj.standardIcon(pixmap_kind)
                if not icon.isNull():
                    return icon
            except Exception:
                pass
    asset_fallback = {"help": "play"}.get(key)
    if asset_fallback:
        pix = build_stock_icon_pixmap(asset_fallback, size)
        if not pix.isNull():
            return QIcon(pix)
    return QIcon()


def build_app_action_icon(
    kind: str,
    style: QStyle | None = None,
    color_hex: str = "#FFFFFF",
    size: int = 16,
) -> QIcon:
    key = str(kind or "").lower()
    style_obj = style or QApplication.style()
    for pixmap_kind in _ACTION_STANDARD_PIXMAPS.get(key, ()):
        try:
            if style_obj is None:
                continue
            icon = style_obj.standardIcon(pixmap_kind)
            if not icon.isNull():
                return icon
        except Exception:
            pass
    stock_icon = build_stock_icon(key)
    if not stock_icon.isNull():
        return stock_icon
    stroke = 1.5 if key == "import" else 2
    return build_line_icon(key, color_hex, size, stroke_width=stroke)


def build_line_icon_pixmap(kind: str, color_hex: str, size: int, stroke_width: float = 2) -> QPixmap:
    pix = QPixmap(int(size), int(size))
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)

    pen = QPen(QColor(color_hex))
    pen.setWidthF(max(1.0, float(stroke_width)))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if kind == "home":
        cell = int(size * 0.32)
        gap = int(size * 0.12)
        r = int(size * 0.16)
        x0 = int((size - (cell * 2 + gap)) / 2)
        y0 = int((size - (cell * 2 + gap)) / 2)
        for ry in (0, 1):
            for rx in (0, 1):
                x = x0 + rx * (cell + gap)
                y = y0 + ry * (cell + gap)
                p.drawRoundedRect(x, y, cell, cell, r, r)
    elif kind in ("projects", "import"):
        x = int(size * 0.14)
        y = int(size * 0.26)
        w = int(size * 0.72)
        h = int(size * 0.54)
        tab_w = int(size * 0.34)
        tab_h = int(size * 0.18)
        p.drawRoundedRect(x, y + tab_h // 2, w, h, 4, 4)
        p.drawRoundedRect(x + int(size * 0.06), y, tab_w, tab_h, 3, 3)
        if kind == "import":
            cx = x + int(w * 0.58)
            top = y + int(size * 0.16)
            bottom = y + h - int(size * 0.10)
            p.drawLine(cx, top, cx, bottom)
            p.drawLine(cx, bottom, cx - int(size * 0.10), bottom - int(size * 0.10))
            p.drawLine(cx, bottom, cx + int(size * 0.10), bottom - int(size * 0.10))
    elif kind == "preview":
        x = int(size * 0.12)
        y = int(size * 0.18)
        w = int(size * 0.76)
        h = int(size * 0.46)
        p.drawRoundedRect(x, y, w, h, 4, 4)
        cx = size // 2
        cy = y + (h // 2)
        p.drawEllipse(cx - int(size * 0.22), cy - int(size * 0.14), int(size * 0.44), int(size * 0.28))
        p.drawEllipse(cx - int(size * 0.06), cy - int(size * 0.06), int(size * 0.12), int(size * 0.12))
        base_y = y + h + int(size * 0.12)
        p.drawLine(cx - int(size * 0.16), base_y, cx + int(size * 0.16), base_y)
        p.drawLine(cx, y + h, cx, base_y)
    elif kind == "delete":
        body_x = int(size * 0.28)
        body_y = int(size * 0.34)
        body_w = int(size * 0.44)
        body_h = int(size * 0.44)
        lid_y = int(size * 0.24)
        p.drawLine(int(size * 0.22), lid_y, int(size * 0.78), lid_y)
        p.drawLine(int(size * 0.40), int(size * 0.18), int(size * 0.60), int(size * 0.18))
        p.drawRoundedRect(body_x, body_y, body_w, body_h, 3, 3)
        p.drawLine(int(size * 0.42), int(size * 0.42), int(size * 0.42), int(size * 0.66))
        p.drawLine(int(size * 0.50), int(size * 0.42), int(size * 0.50), int(size * 0.66))
        p.drawLine(int(size * 0.58), int(size * 0.42), int(size * 0.58), int(size * 0.66))
    elif kind == "recent":
        p.drawEllipse(int(size * 0.16), int(size * 0.16), int(size * 0.68), int(size * 0.68))
        p.drawLine(size // 2, int(size * 0.28), size // 2, size // 2)
        p.drawLine(size // 2, size // 2, int(size * 0.66), int(size * 0.60))
    elif kind in ("publish", "export", "download"):
        x = int(size * 0.18)
        y = int(size * 0.56)
        w = int(size * 0.64)
        h = int(size * 0.18)
        p.drawRoundedRect(x, y, w, h, 4, 4)
        cx = size // 2
        top = int(size * 0.18)
        p.drawLine(cx, top, cx, y)
        if kind == "publish":
            p.drawLine(cx, top, cx - int(size * 0.14), top + int(size * 0.16))
            p.drawLine(cx, top, cx + int(size * 0.14), top + int(size * 0.16))
        else:
            p.drawLine(cx, y, cx - int(size * 0.14), y - int(size * 0.14))
            p.drawLine(cx, y, cx + int(size * 0.14), y - int(size * 0.14))
    elif kind == "resume":
        p.drawLine(int(size * 0.74), int(size * 0.72), int(size * 0.60), int(size * 0.58))
        p.drawLine(int(size * 0.60), int(size * 0.58), int(size * 0.30), int(size * 0.28))
        p.drawLine(int(size * 0.38), int(size * 0.20), int(size * 0.22), int(size * 0.36))
        p.drawLine(int(size * 0.78), int(size * 0.76), int(size * 0.66), int(size * 0.88))
        p.drawLine(int(size * 0.78), int(size * 0.76), int(size * 0.84), int(size * 0.90))
    elif kind == "save":
        x = int(size * 0.18)
        y = int(size * 0.18)
        w = int(size * 0.64)
        h = int(size * 0.64)
        r = int(size * 0.12)
        p.drawRoundedRect(x, y, w, h, r, r)
        p.drawLine(x + int(size * 0.10), y + int(size * 0.24), x + w - int(size * 0.10), y + int(size * 0.24))
        p.drawRect(x + int(size * 0.20), y + int(size * 0.34), int(size * 0.34), int(size * 0.22))
        p.drawEllipse(x + int(size * 0.56), y + int(size * 0.36), int(size * 0.14), int(size * 0.14))
    elif kind == "web":
        r = int(size * 0.34)
        cx = size // 2
        cy = size // 2
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        p.drawLine(cx - r, cy, cx + r, cy)
        p.drawLine(cx, cy - r, cx, cy + r)
        p.drawEllipse(cx - int(r * 0.55), cy - r, int(r * 1.10), r * 2)
        p.drawEllipse(cx - r, cy - int(r * 0.55), r * 2, int(r * 1.10))
    elif kind == "create":
        cx = size / 2.0
        cy = size / 2.0
        bar = max(4.0, size * 0.10)
        arm = size * 0.20
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color_hex))
        p.drawRoundedRect(cx - arm, cy - bar / 2.0, arm * 2.0, bar, bar / 2.0, bar / 2.0)
        p.drawRoundedRect(cx - bar / 2.0, cy - arm, bar, arm * 2.0, bar / 2.0, bar / 2.0)
        p.restore()
    elif kind == "edit":
        path = QPainterPath()
        path.moveTo(size * 0.24, size * 0.67)
        path.lineTo(size * 0.33, size * 0.76)
        path.lineTo(size * 0.70, size * 0.39)
        path.lineTo(size * 0.61, size * 0.30)
        path.closeSubpath()

        tip = QPainterPath()
        tip.moveTo(size * 0.70, size * 0.39)
        tip.lineTo(size * 0.78, size * 0.31)
        tip.lineTo(size * 0.69, size * 0.22)
        tip.lineTo(size * 0.61, size * 0.30)
        tip.closeSubpath()

        eraser = QPainterPath()
        eraser.moveTo(size * 0.20, size * 0.63)
        eraser.lineTo(size * 0.28, size * 0.71)
        eraser.lineTo(size * 0.33, size * 0.76)
        eraser.lineTo(size * 0.25, size * 0.68)
        eraser.closeSubpath()

        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color_hex))
        p.drawPath(path)
        p.drawPath(tip)
        p.drawPath(eraser)
        p.restore()
    elif kind == "play":
        path = QPainterPath()
        path.moveTo(int(size * 0.38), int(size * 0.28))
        path.lineTo(int(size * 0.70), size // 2)
        path.lineTo(int(size * 0.38), int(size * 0.72))
        path.closeSubpath()
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color_hex))
        p.drawPath(path)
        p.restore()
    elif kind == "chat":
        x = int(size * 0.16)
        y = int(size * 0.18)
        w = int(size * 0.68)
        h = int(size * 0.48)
        p.drawRoundedRect(x, y, w, h, 5, 5)
        p.drawLine(x + int(size * 0.20), y + h, x + int(size * 0.34), y + h + int(size * 0.14))
        p.drawLine(x + int(size * 0.34), y + h + int(size * 0.14), x + int(size * 0.38), y + h)
        p.drawLine(x + int(size * 0.18), y + int(size * 0.28), x + int(size * 0.66), y + int(size * 0.28))
        p.drawLine(x + int(size * 0.18), y + int(size * 0.42), x + int(size * 0.56), y + int(size * 0.42))
    elif kind == "help":
        r = int(size * 0.34)
        cx = size // 2
        cy = size // 2
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        path = QPainterPath()
        path.moveTo(cx - int(size * 0.12), int(size * 0.32))
        path.cubicTo(
            cx - int(size * 0.14),
            int(size * 0.18),
            cx + int(size * 0.20),
            int(size * 0.18),
            cx + int(size * 0.16),
            int(size * 0.38),
        )
        path.cubicTo(
            cx + int(size * 0.14),
            int(size * 0.48),
            cx,
            int(size * 0.46),
            cx,
            int(size * 0.56),
        )
        p.drawPath(path)
        dot = max(2, int(size * 0.05))
        p.drawEllipse(cx - dot, int(size * 0.68) - dot, dot * 2, dot * 2)
    elif kind == "settings":
        cx = size // 2
        cy = size // 2
        inner_r = int(size * 0.16)
        outer_r = int(size * 0.28)
        p.drawEllipse(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
        for angle_deg in range(0, 360, 45):
            angle = math.radians(angle_deg)
            start_r = int(size * 0.24)
            end_r = outer_r
            sx = cx + int(math.cos(angle) * start_r)
            sy = cy + int(math.sin(angle) * start_r)
            ex = cx + int(math.cos(angle) * end_r)
            ey = cy + int(math.sin(angle) * end_r)
            p.drawLine(sx, sy, ex, ey)
        p.drawEllipse(cx - int(size * 0.28), cy - int(size * 0.28), int(size * 0.56), int(size * 0.56))
    elif kind == "refresh":
        p.drawArc(int(size * 0.18), int(size * 0.18), int(size * 0.64), int(size * 0.64), 35 * 16, 265 * 16)
        p.drawLine(int(size * 0.68), int(size * 0.22), int(size * 0.80), int(size * 0.22))
        p.drawLine(int(size * 0.68), int(size * 0.22), int(size * 0.74), int(size * 0.34))
    elif kind == "back":
        cy = size // 2
        p.drawLine(int(size * 0.78), cy, int(size * 0.24), cy)
        p.drawLine(int(size * 0.24), cy, int(size * 0.42), int(size * 0.30))
        p.drawLine(int(size * 0.24), cy, int(size * 0.42), int(size * 0.70))
    else:
        p.drawEllipse(int(size * 0.22), int(size * 0.22), int(size * 0.56), int(size * 0.56))

    p.end()
    return pix


def build_line_icon(kind: str, color_hex: str, size: int, stroke_width: float = 2) -> QIcon:
    return QIcon(build_line_icon_pixmap(kind, color_hex, size, stroke_width=stroke_width))
