# EduPlay Studio

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-6.5+-green.svg)](https://pypi.org/project/PySide6/)
[![GitHub](https://img.shields.io/badge/GitHub-Tan0807--creat3%2FEduPlay-blue)](https://github.com/Tan0807-creat3/EduPlay.git)

A comprehensive educational game creation tool for teachers, built with PySide6 and Python.

## Features

- **Dual Creation Modes**: Manual creation with full control and AI-assisted generation
- **Multiple Game Types**: Quiz games, fishing games, and interactive educational content
- **Cross-Platform Support**: Export to HTML5 (iOS/Mac/Windows) and native applications
- **Rich Media Support**: Images, audio, video integration
- **AI Integration**: Gemini-powered content generation and assistance
- **Professional Export**: HTML, EXE, and APP formats

## Installation

1. Install Python 3.8 or higher
2. Clone this repository
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python -m eduplay
```

Or directly:
```bash
python eduplay/__main__.py
```

## Project Structure

```
eduplay_studio/
├── eduplay/                    # Main source code
│   ├── __main__.py             # Entry point
│   ├── app.py                  # Main application class
│   ├── core/                   # Backend logic
│   │   ├── ai_service.py       # AI integration
│   │   ├── project_manager.py  # Project management
│   │   ├── import_service.py   # File import
│   │   ├── export_service.py   # Export functionality
│   │   └── asset_manager.py    # Asset management
│   ├── ui/                     # User interface
│   │   ├── main_window.py      # Main window
│   │   ├── screens/            # Screen components
│   │   └── widgets/            # Reusable widgets
│   └── resources/              # Application resources
├── assets_bundle/              # Game assets
└── requirements.txt            # Dependencies
```

## Contact

- Email: Eduplay.pro@hotmail.com
- Repository: https://github.com/Tan0807-creat3/EduPlay.git
