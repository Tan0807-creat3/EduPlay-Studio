from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QRadioButton, 
                               QButtonGroup, QDialogButtonBox, QWidget, QFrame, QHBoxLayout)
from PySide6.QtCore import Qt, QEvent
from eduplay.core.i18n import I18n

class OptionWidget(QFrame):
    """Clickable option widget containing a radio button and description"""
    def __init__(self, radio_btn, description_text, parent=None):
        super().__init__(parent)
        self.radio_btn = radio_btn
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("OptionWidget")
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Add radio button
        layout.addWidget(self.radio_btn)
        
        # Add description
        self.desc_label = QLabel(description_text)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #555; margin-left: 20px; font-size: 0.9em;")
        layout.addWidget(self.desc_label)
        
        # Style
        self.setStyleSheet("""
            #OptionWidget {
                background-color: #FFFFFF;
                border: 1px solid #DDD;
                border-radius: 8px;
            }
            #OptionWidget:hover {
                background-color: #F5F7FA;
                border-color: #BBB;
            }
        """)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.radio_btn.setChecked(True)
        super().mousePressEvent(event)

class TemplateSelectionDialog(QDialog):
    def __init__(self, parent=None, lang="vi"):
        super().__init__(parent)
        self.setWindowTitle(I18n.t("template.choice.title", lang))
        self.setMinimumWidth(450)
        self.lang = lang
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Instruction label
        lbl = QLabel(I18n.t("template.choice.label", lang))
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(lbl)
        
        # Options container
        self.btn_group = QButtonGroup(self)
        
        # General Option
        self.rb_general = QRadioButton(I18n.t("template.choice.general", lang))
        self.rb_general.setStyleSheet("font-weight: bold;")
        self.rb_general.setChecked(True)
        self.btn_group.addButton(self.rb_general, 0)
        
        desc_gen_text = I18n.t("template.docx.note_others", lang)
        self.opt_general = OptionWidget(self.rb_general, desc_gen_text)
        layout.addWidget(self.opt_general)
        
        # Millionaire Option
        self.rb_millionaire = QRadioButton(I18n.t("template.choice.millionaire", lang))
        self.rb_millionaire.setStyleSheet("font-weight: bold;")
        self.btn_group.addButton(self.rb_millionaire, 1)
        
        desc_mil_text = I18n.t("template.docx.note_millionaire", lang)
        self.opt_millionaire = OptionWidget(self.rb_millionaire, desc_mil_text)
        layout.addWidget(self.opt_millionaire)
        
        layout.addStretch()
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        try:
            from eduplay.core.settings_manager import SettingsManager
            theme = None
            try:
                sm = getattr(parent, "settings_manager", None)
                if sm is not None and hasattr(sm, "get_theme"):
                    theme = sm.get_theme()
            except Exception:
                theme = None
            if not theme:
                theme = SettingsManager().get_theme()
            if theme == "dark":
                self.apply_dark_theme()
            else:
                self.apply_light_theme()
        except:
            pass

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog { background-color: #2D2F3A; color: #FFF; }
            QLabel { color: #FFF; }
            QRadioButton { color: #FFF; }
            QDialogButtonBox QPushButton { color: #FFF; }
        """)
        for opt in [self.opt_general, self.opt_millionaire]:
            opt.desc_label.setStyleSheet("color: #AAA; margin-left: 20px; font-size: 0.9em;")
            opt.setStyleSheet("""
                #OptionWidget {
                    background-color: #3A3C47;
                    border: 1px solid #4A4E5A;
                    border-radius: 8px;
                }
                #OptionWidget:hover {
                    background-color: #4A4E5A;
                    border-color: #7F56D9;
                }
            """)

    def apply_light_theme(self):
        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; color: #111827; }
            QLabel { color: #111827; }
            QRadioButton { color: #111827; }
            QDialogButtonBox QPushButton { color: #111827; }
        """)
        for opt in [self.opt_general, self.opt_millionaire]:
            opt.desc_label.setStyleSheet("color: #555; margin-left: 20px; font-size: 0.9em;")
            opt.setStyleSheet("""
                #OptionWidget {
                    background-color: #FFFFFF;
                    border: 1px solid #DDD;
                    border-radius: 8px;
                }
                #OptionWidget:hover {
                    background-color: #F5F7FA;
                    border-color: #BBB;
                }
            """)

    def get_selected_type(self):
        if self.rb_millionaire.isChecked():
            return "millionaire"
        return "general"
