"""
Theme management for EduPlay Studio
"""
from typing import Dict, Any
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

class ThemeManager(QObject):
    """Manages application themes"""
    theme_changed = Signal(str)  # Signal emitted when theme changes
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._current_theme = 'light'
            cls._instance._themes = {
                'dark': {
                    'background': '#1E1E24',
                    'text': '#E2E8F0',
                    'primary': '#4F46E5',
                    'secondary': '#6B7280',
                    'success': '#10B981',
                    'danger': '#EF4444',
                    'warning': '#F59E0B',
                    'card_bg': '#2D2F3A',
                    'card_border': '#4A4E5A',
                    'input_bg': '#2D3748',
                    'input_border': '#4A5568',
                    'input_text': '#E2E8F0',
                    'button_bg': '#4F46E5',
                    'button_text': '#FFFFFF',
                    'button_hover': '#4338CA',
                    'button_border': '#4F46E5',
                },
                'light': {
                    'background': '#F5F5F5',
                    'text': '#1F2937',
                    'primary': '#10B981',
                    'secondary': '#6B7280',
                    'success': '#10B981',
                    'danger': '#EF4444',
                    'warning': '#F59E0B',
                    'card_bg': '#FFFFFF',
                    'card_border': '#E5E7EB',
                    'input_bg': '#FFFFFF',
                    'input_border': '#D1D5DB',
                    'input_text': '#1F2937',
                    'button_bg': '#10B981',
                    'button_text': '#FFFFFF',
                    'button_hover': '#059669',
                    'button_border': '#10B981',
                }
            }
        return cls._instance
    
    @property
    def current_theme(self) -> str:
        """Get current theme name"""
        return self._current_theme
    
    @current_theme.setter
    def current_theme(self, theme_name: str):
        """Set current theme"""
        if theme_name in self._themes and theme_name != self._current_theme:
            self._current_theme = theme_name
            self.theme_changed.emit(theme_name)
    
    def get_theme(self, theme_name: str = None) -> Dict[str, str]:
        """Get theme colors"""
        theme = theme_name or self._current_theme
        return self._themes.get(theme, self._themes['dark'])
    
    def apply_stylesheet(self, app: QApplication = None):
        """Apply current theme stylesheet to the application"""
        theme = self.get_theme()
        
        stylesheet = f"""
            /* Main window */
            QWidget {{
                color: {text};
                background-color: {background};
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }}
            
            /* Buttons */
            QPushButton {{
                background-color: {button_bg};
                color: {button_text};
                border: 1px solid {button_border};
                border-radius: 6px;
                padding: 8px 16px;
                min-height: 32px;
            }}
            
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            
            QPushButton:disabled {{
                background-color: {secondary};
                color: {text};
                opacity: 0.6;
            }}
            
            /* Line edits */
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding: 6px 12px;
                selection-background-color: {primary};
                selection-color: white;
            }}
            
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border: 1px solid {primary};
            }}
            
            /* Combo boxes */
            QComboBox {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 120px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {card_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 0px;
                selection-background-color: #7F56D9;
                selection-color: #FFFFFF;
                padding: 0px;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: 6px 12px;
                margin: 0px;
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: #7F56D9;
                color: #FFFFFF;
            }}
            
            QComboBox QAbstractItemView::item:hover:!selected {{
                background-color: {card_bg};
                color: {input_text};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            
            QComboBox::down-arrow {{
                image: url(:/icons/arrow-down.svg);
                width: 16px;
                height: 16px;
            }}
            
            /* Scroll bars */
            QScrollBar:vertical {{
                border: none;
                background: {card_bg};
                width: 10px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background: {secondary};
                min-height: 20px;
                border-radius: 5px;
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            /* Tabs */
            QTabBar::tab {{
                background: {card_bg};
                color: {text};
                padding: 8px 16px;
                border: 1px solid {card_border};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            
            QTabBar::tab:selected {{
                background: {primary};
                color: white;
                border-color: {primary};
            }}
            
            /* Cards */
            .card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                padding: 16px;
            }}
            
            /* Custom game type colors */
            .game-type-quiz {{
                background-color: #4F46E5;
                color: white;
            }}
            
            .game-type-fishing {{
                background-color: #10B981;
                color: white;
            }}
            
            .game-type-millionaire {{
                background-color: #8B5CF6;
                color: white;
            }}
        """.format(**theme)
        
        if app:
            app.setStyleSheet(stylesheet)
        return stylesheet

# Global theme manager instance
theme_manager = ThemeManager()

