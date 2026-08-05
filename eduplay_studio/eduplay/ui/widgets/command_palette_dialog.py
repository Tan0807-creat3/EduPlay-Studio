from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel

from eduplay.core.command_palette import filter_items
from eduplay.core.i18n import I18n


class CommandPaletteDialog(QDialog):
    item_triggered = Signal(dict)

    def __init__(self, items: list[dict] | None = None, parent=None, lang: str = "en"):
        super().__init__(parent)
        self._lang = str(lang or "en")
        self._all_items = list(items or [])
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setMinimumWidth(620)
        self.setObjectName("command-palette")
        self._build()
        self.set_items(self._all_items)

    def _t(self, vi: str, en: str) -> str:
        return vi if self._lang.startswith("vi") else en

    def _tr(self, key: str, fallback_vi: str, fallback_en: str) -> str:
        try:
            value = I18n.t(key, self._lang)
            if isinstance(value, str) and value != key and value.strip():
                return value
        except Exception:
            pass
        return self._t(fallback_vi, fallback_en)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        self.title_label = QLabel(self._tr("command_palette.title", "Tìm nhanh", "Quick Search"))
        self.title_label.setStyleSheet("QLabel{font-size:18px;font-weight:800;color:#E5E7EB;}")
        root.addWidget(self.title_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            self._tr(
                "command_palette.placeholder",
                "Gõ để mở dự án, tạo mới, preview, export...",
                "Type to open a project, create, preview, export...",
            )
        )
        self.search_input.textChanged.connect(self._refresh_list)
        self.search_input.returnPressed.connect(self._activate_current)
        root.addWidget(self.search_input)

        self.hint_label = QLabel(self._tr("command_palette.hint", "Enter để chọn, Esc để đóng", "Press Enter to open, Esc to close"))
        self.hint_label.setStyleSheet("QLabel{font-size:12px;color:#98A2B3;}")
        root.addWidget(self.hint_label)

        self.list_widget = QListWidget()
        self.list_widget.itemActivated.connect(self._emit_item)
        self.list_widget.itemClicked.connect(self._emit_item)
        root.addWidget(self.list_widget, 1)

        self.setStyleSheet(
            """
            QDialog#command-palette {
                background-color: #101828;
                border: 1px solid #344054;
                border-radius: 16px;
            }
            QLineEdit {
                background-color: #182230;
                color: #F8FAFC;
                border: 1px solid #475467;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #7F56D9;
            }
            QListWidget {
                background-color: #101828;
                border: none;
                color: #E5E7EB;
                outline: none;
            }
            QListWidget::item {
                border: 1px solid transparent;
                border-radius: 10px;
                padding: 10px 12px;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background-color: #1D2939;
                border: 1px solid #7F56D9;
            }
            """
        )

    def set_items(self, items: list[dict] | None):
        self._all_items = list(items or [])
        self._refresh_list()

    def open_and_focus(self):
        self._refresh_list()
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _render_text(self, item: dict) -> str:
        title = str(item.get("title") or "").strip()
        subtitle = str(item.get("subtitle") or "").strip()
        markers: list[str] = []
        if bool(item.get("is_current")):
            markers.append(self._t("đang mở", "open"))
        if bool(item.get("is_recent")):
            markers.append(self._t("gần đây", "recent"))
        if markers:
            title = f"{title} [{' / '.join(markers)}]"
        if subtitle:
            return f"{title}\n{subtitle}"
        return title

    def _refresh_list(self):
        query = self.search_input.text() if hasattr(self, "search_input") else ""
        items = filter_items(self._all_items, query)
        self.list_widget.clear()
        for item in items:
            row = QListWidgetItem(self._render_text(item))
            row.setData(Qt.UserRole, item)
            self.list_widget.addItem(row)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _activate_current(self):
        item = self.list_widget.currentItem()
        if item is not None:
            self._emit_item(item)

    def _emit_item(self, item):
        payload = item.data(Qt.UserRole) if isinstance(item, QListWidgetItem) else None
        if not isinstance(payload, dict):
            return
        self.item_triggered.emit(payload)
        self.accept()
