from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QWidget, QToolButton, QFrame, QVBoxLayout, QListView, QSizePolicy


class FlatDropdown(QWidget):
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_index = -1
        self.max_visible_items = 4

        self.button = QToolButton(self)
        self.button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        try:
            self.button.setStyleSheet(
                """
                QToolButton {
                    text-align: left;
                    padding: 0px 12px;
                }
                """
            )
        except Exception:
            pass
        self.button.clicked.connect(self._toggle_popup)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.button)

        self.popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        self.popup.setObjectName("FlatDropdownPopup")
        # Explicit white background to prevent inheriting dark app theme
        self.popup.setStyleSheet("""
            QFrame#FlatDropdownPopup {
                background-color: #FFFFFF;
                border: 1px solid #D0D5DD;
                border-radius: 8px;
            }
            QListView {
                background-color: #FFFFFF;
                color: #0F172A;
                border: none;
                outline: none;
            }
            QListView::item {
                padding: 8px 12px;
                color: #0F172A;
            }
            QListView::item:selected {
                background-color: #7F56D9;
                color: #FFFFFF;
            }
            QListView::item:hover:!selected {
                background-color: #EEF2FF;
                color: #0F172A;
            }
            QScrollBar:vertical {
                background: #F5F6FA;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self.popup_layout = QVBoxLayout(self.popup)
        self.popup_layout.setContentsMargins(0, 0, 0, 0)
        self.popup_layout.setSpacing(0)

        self.view = QListView(self.popup)
        self.view.setUniformItemSizes(True)
        self.view.setSelectionMode(QListView.SingleSelection)
        self.view.setEditTriggers(QListView.NoEditTriggers)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.model = QStandardItemModel(self)
        self.view.setModel(self.model)

        self.view.clicked.connect(self._on_item_clicked)

        self.popup_layout.addWidget(self.view)
        
    def _ensure_model(self):
        try:
            # Accessing rowCount will raise if underlying C++ object was deleted
            _ = self.model.rowCount()
        except Exception:
            try:
                self.model = QStandardItemModel(self)
                self.view.setModel(self.model)
            except Exception:
                pass

    def addItem(self, text: str, user_data=None):
        self._ensure_model()
        item = QStandardItem(text)
        item.setEditable(False)
        if user_data is not None:
            item.setData(user_data, Qt.ItemDataRole.UserRole)
        self.model.appendRow(item)
        if self._current_index == -1:
            self.setCurrentIndex(0)

    def addItems(self, texts):
        self._ensure_model()
        for text in texts:
            self.addItem(text)

    def clear(self):
        self._ensure_model()
        self.model.clear()
        self._current_index = -1
        self.button.setText("")

    def count(self) -> int:
        self._ensure_model()
        try:
            return self.model.rowCount()
        except Exception:
            return 0

    def currentIndex(self) -> int:
        return self._current_index

    def currentText(self) -> str:
        self._ensure_model()
        if 0 <= self._current_index < self.model.rowCount():
            index = self.model.index(self._current_index, 0)
            value = self.model.data(index, Qt.ItemDataRole.DisplayRole)
            if value is not None:
                return str(value)
        return ""

    def setCurrentIndex(self, index: int):
        self._ensure_model()
        if self.model.rowCount() == 0:
            self._current_index = -1
            self.button.setText("")
            return
        index = max(0, min(index, self.model.rowCount() - 1))
        if index == self._current_index:
            return
        self._current_index = index
        model_index = self.model.index(index, 0)
        value = self.model.data(model_index, Qt.ItemDataRole.DisplayRole)
        text = str(value) if value is not None else ""
        self.button.setText(text)
        self.view.setCurrentIndex(model_index)
        self.currentIndexChanged.emit(index)
        self.currentTextChanged.emit(text)

    def setItemData(self, index: int, value, role=Qt.ItemDataRole.UserRole):
        if 0 <= index < self.model.rowCount():
            item = self.model.item(index)
            if item is not None:
                item.setData(value, role)

    def itemData(self, index: int, role=Qt.ItemDataRole.UserRole):
        if 0 <= index < self.model.rowCount():
            item = self.model.item(index)
            if item is not None:
                return item.data(role)
        return None

    def currentData(self, role=Qt.ItemDataRole.UserRole):
        self._ensure_model()
        if 0 <= self._current_index < self.model.rowCount():
            return self.itemData(self._current_index, role)
        return None

    def findText(self, text: str) -> int:
        self._ensure_model()
        target = (text or "").strip().lower()
        try:
            rows = self.model.rowCount()
        except Exception:
            return -1
        for row in range(rows):
            try:
                index = self.model.index(row, 0)
                value = self.model.data(index, Qt.ItemDataRole.DisplayRole)
            except Exception:
                continue
            if value is None:
                continue
            if str(value).strip().lower() == target:
                return row
        return -1

    def findData(self, data, role=Qt.ItemDataRole.UserRole) -> int:
        self._ensure_model()
        try:
            rows = self.model.rowCount()
        except Exception:
            return -1
        for row in range(rows):
            try:
                index = self.model.index(row, 0)
                item_data = self.model.data(index, role)
            except Exception:
                continue
            if item_data == data:
                return row
        return -1

    def setCurrentData(self, data, role=Qt.ItemDataRole.UserRole):
        self._ensure_model()
        index = self.findData(data, role)
        if index != -1:
            self.setCurrentIndex(index)

    def setCurrentText(self, text: str):
        self._ensure_model()
        index = self.findText(text)
        if index != -1:
            self.setCurrentIndex(index)

    def _toggle_popup(self):
        if self.popup.isVisible():
            self.popup.hide()
            return
        self._show_popup()

    def _show_popup(self):
        self.popup.adjustSize()
        width = max(self.width(), self.popup.sizeHint().width())
        self._ensure_model()
        try:
            rows = self.model.rowCount()
        except Exception:
            rows = 0
        if rows > 0:
            row_height = self.view.sizeHintForRow(0)
            visible = min(rows, self.max_visible_items)
            height = row_height * visible + 2
        else:
            height = self.popup.sizeHint().height()
        self.popup.resize(width, height)
        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        self.popup.move(global_pos)
        self.popup.show()
        self.popup.raise_()

    def _on_item_clicked(self, index):
        row = index.row()
        self.setCurrentIndex(row)
        self.popup.hide()

    def sizeHint(self):
        return self.button.sizeHint()

"""
Nguyen-Thanh-Tan ¬_¬
"""
