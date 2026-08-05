from __future__ import annotations

from typing import List

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QApplication
from PySide6.QtGui import QIcon


_DEFAULT_FILE_DIALOG_STYLE = """
    QFileDialog, QDialog, QWidget {
        background-color: #FFFFFF;
        color: #101828;
    }
    QLabel { color: #101828; }
    QLineEdit, QListView, QTreeView, QAbstractItemView {
        background-color: #FFFFFF;
        color: #101828;
        selection-background-color: #7F56D9;
        selection-color: #FFFFFF;
    }
    QHeaderView::section {
        background-color: #F2F4F7;
        color: #101828;
        padding: 4px 8px;
        border: none;
    }
    QPushButton {
        background-color: #F2F4F7;
        color: #101828;
        border: 1px solid #D0D5DD;
        border-radius: 6px;
        padding: 6px 10px;
    }
    QPushButton:hover { background-color: #EAECF0; }
"""


def _create_dialog(
    parent,
    title: str,
    file_mode: QFileDialog.FileMode,
    accept_mode: QFileDialog.AcceptMode,
    directory: str = "",
    name_filter: str = "",
) -> QFileDialog:
    dlg = QFileDialog(parent, title, directory)
    dlg.setFileMode(file_mode)
    dlg.setAcceptMode(accept_mode)
    try:
        icon = None
        try:
            icon = parent.windowIcon() if parent else None
        except Exception:
            icon = None
        try:
            if icon is None or icon.isNull():
                icon = QApplication.windowIcon()
        except Exception:
            pass
        try:
            if icon is None or icon.isNull():
                base = Path(__file__).resolve().parents[1]
                ico = base / "resources" / "icons" / "icon.ico"
                png = base / "resources" / "icons" / "icon.png"
                if ico.exists():
                    icon = QIcon(str(ico))
                elif png.exists():
                    icon = QIcon(str(png))
        except Exception:
            pass
        if icon is not None and not icon.isNull():
            dlg.setWindowIcon(icon)
    except Exception:
        pass
    try:
        if name_filter:
            dlg.setNameFilter(name_filter)
    except Exception:
        pass
    try:
        dlg.setOption(QFileDialog.DontUseNativeDialog, True)
    except Exception:
        pass
    try:
        dlg.setWindowModality(Qt.ApplicationModal)
    except Exception:
        pass
    try:
        dlg.setStyleSheet(_DEFAULT_FILE_DIALOG_STYLE)
    except Exception:
        pass
    return dlg


def get_open_file_name(parent, title: str, directory: str = "", name_filter: str = "") -> str:
    dlg = _create_dialog(
        parent=parent,
        title=title,
        file_mode=QFileDialog.ExistingFile,
        accept_mode=QFileDialog.AcceptOpen,
        directory=directory,
        name_filter=name_filter,
    )
    if dlg.exec():
        sel = dlg.selectedFiles()
        return sel[0] if sel else ""
    return ""


def get_open_file_names(parent, title: str, directory: str = "", name_filter: str = "") -> List[str]:
    dlg = _create_dialog(
        parent=parent,
        title=title,
        file_mode=QFileDialog.ExistingFiles,
        accept_mode=QFileDialog.AcceptOpen,
        directory=directory,
        name_filter=name_filter,
    )
    if dlg.exec():
        return list(dlg.selectedFiles() or [])
    return []
