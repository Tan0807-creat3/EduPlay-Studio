# Installation (EduPlay Studio 1.0.0)

EduPlay Studio 1.0.0 is primarily tested on Windows 10/11.

## Prerequisites

- **Python 3.10+**
- **Tesseract OCR**: Required for OCR features (reading text from images).
  - Download and install from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
  - Add the installation path to your system's PATH variable.

1. Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Configure AI (Groq):

- Set `GROQ_API_KEY` (or `EDUPLAY_GROQ_API_KEY`) in your environment.
- Optional: `GROQ_MODEL` (default: `llama-3.1-8b-instant`)

4. Run the app:

```powershell
python eduplay_studio\app.py
```

## PowerPoint add-in (Windows)

- In EduPlay Studio: Settings → Add-in → Install / Repair Add-in.
- Approve the admin prompt when asked.
- Restart PowerPoint.
- In PowerPoint, find the EduPlay button/tab on the ribbon (it may be under Add-ins).

## Build Windows executable (optional)

This repository contains:
- PyInstaller spec: [eduplay_studio.spec](eduplay_studio.spec)
- Inno Setup script: [setup.iss](setup.iss)

Notes:
- Build scripts may contain machine-specific paths. Update them to match your local folders before building.
