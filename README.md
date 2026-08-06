> [!NOTE]
> To comply with our security and copyright policies, certain features have been removed from this public release. These changes do not impact the software's core functionality or overall performance.

# EduPlay Studio 1.0.0

EduPlay Studio is a modern desktop application designed for educators to create, manage, and export interactive educational games. With built-in AI assistance, creating engaging content has never been easier.

## ✨ Key Features

- **🎯 Diverse Game Templates**: Choose from Quiz Classic, Quiz Millionaire, or the interactive Fishing Game.
- **🤖 Edubot (AI Assistant)**: Generate high-quality educational questions instantly using Groq AI.
- **🛠 Visual Editor**: Easily manage questions, media, and game configurations in a user-friendly interface.
- **🌐 Flexible Export**: Export your projects to HTML5 (web-ready) or Native (standalone) formats.
- **📊 PowerPoint Integration**: Seamlessly integrate your games into PowerPoint presentations.
- **🌍 Multi-language Support**: Available in English, Vietnamese, and more.

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (for OCR features)

### Installation
1. Clone the repository and navigate to the project folder.
2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

### Running the App
```powershell
python eduplay_studio/app.py
```

## 🤖 AI Configuration (Groq)

To enable AI features, set the following environment variables:
- `GROQ_API_KEY` (Required)
- `GROQ_MODEL` (Optional, default: `llama-3.1-8b-instant`)

## 📚 Documentation

Detailed documentation is available in the `docs/` folder:

- **[User Guide](docs/USER_GUIDE.md)**: How to use the app and its features.
- **[Installation Guide](docs/INSTALLATION.md)**: Detailed setup and troubleshooting.
- **[Roadmap](docs/ROADMAP.md)**: Future plans and upcoming features.
- **[Security Policy](docs/SECURITY.md)**: How we handle security and reporting.
- **[Changelog](docs/CHANGELOG.md)**: History of changes and releases.
- **[Contributing](docs/CONTRIBUTING.md)**: How to help improve EduPlay Studio.

## 📜 License

This project is licensed under the **PolyForm Noncommercial License 1.0.0**. See the [LICENSE](LICENSE) file for details.

---
Developed with ❤️ for Education.
