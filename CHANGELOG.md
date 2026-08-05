# Changelog

All notable changes to EduPlay Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-05

### Added
- Desktop application (PySide6) for creating educational games.
- Edubot (AI assistant) using Groq (OpenAI-compatible API). Requires `GROQ_API_KEY` (or `EDUPLAY_GROQ_API_KEY`).
- Game templates:
  - Quiz Classic
  - Quiz Millionaire
  - Fishing
- Export:
  - HTML5 web game export (bundles assets for offline use)
  - Native/PyGame export
- PowerPoint integration (Windows): installs local Office add-ins (taskpane + content) from within the app.
- Packaging scripts: PyInstaller spec + Inno Setup installer script.

### Notes
- PowerPoint add-ins may require Office activation and a PowerPoint restart after installation.
