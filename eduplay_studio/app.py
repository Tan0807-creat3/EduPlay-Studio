import sys
import os
from PySide6.QtWidgets import QApplication

# Add the current directory to sys.path to allow imports from eduplay_studio
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from eduplay.ui.main_window import MainWindow

def main():
    # Set up the application
    app = QApplication(sys.argv)
    app.setApplicationName("EduPlay Studio")
    app.setOrganizationName("EduPlay")
    
    # Create and show the main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
