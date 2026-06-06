# EduPlay Studio 1.0.0

EduPlay Studio is a desktop application for creating educational games with AI-assisted content generation. It provides project management, a visual editor, preview, and export to HTML5 and Native/PyGame.

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0. See [LICENSE](LICENSE).

## System requirements

- Windows 10/11 (tested)
- Python 3.10+ (tested with Python 3.12)
- pip

## Install & run (from source)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python eduplay_studio\app.py
```

## AI (Groq)

- EduPlay Studio uses Groq (OpenAI-compatible API).
- Set environment variables:
  - `GROQ_API_KEY` (or `EDUPLAY_GROQ_API_KEY`) (required)
  - `GROQ_MODEL` (optional, default: `llama-3.1-8b-instant`)

## PowerPoint integration (Windows)

EduPlay Studio can install local Office add-ins for PowerPoint (taskpane + content viewer).

- Open EduPlay Studio → Settings → Add-in → Install PowerPoint Add-in.
- Approve the admin prompt (needed to register Shared Folder catalog).
- Restart PowerPoint.
- PowerPoint → Add-ins → Office Add-ins → Shared Folder → select the EduPlay add-in.

Notes:
- Office should be activated; deactivated Office may hide add-ins.
- The add-in host runs locally on `http://localhost:18777`.

## Export

- HTML5 export (offline-ready)
- Native/PyGame export

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Docs

- [INSTALLATION.md](INSTALLATION.md)
- [USER_GUIDE.md](USER_GUIDE.md)
- [ROADMAP.md](ROADMAP.md)
- [SECURITY.md](SECURITY.md)
