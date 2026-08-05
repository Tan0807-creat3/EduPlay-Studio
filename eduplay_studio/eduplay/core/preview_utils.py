from __future__ import annotations

from pathlib import Path


def build_preview_placeholder_html(*, lang: str = "vi", title: str = "EduPlay Preview") -> str:
    is_vi = (lang or "").strip().lower().startswith("vi")
    try:
        from eduplay.core.i18n import I18n
        heading = I18n.t("preview.placeholder_heading", lang)
        sub = I18n.t("preview.placeholder_sub", lang)
    except Exception:
        heading = "Đang tải bản xem trước..." if is_vi else "Loading preview..."
        sub = "Vui lòng chờ trong giây lát." if is_vi else "Please wait a moment."
    safe_title = (title or "EduPlay Preview").replace("<", "").replace(">", "").replace("&", "and")
    return f"""<!doctype html>
<html lang="{('vi' if is_vi else 'en')}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_title}</title>
  <style>
    html, body {{
      height: 100%;
      margin: 0;
      font-family: "Times New Roman", Times, serif;
      background: #0b1020;
      color: #e5e7eb;
    }}
    #eduplay-preview-placeholder {{
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px;
      box-sizing: border-box;
    }}
    .box {{
      width: min(560px, 100%);
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.06);
      backdrop-filter: blur(8px);
      padding: 22px 22px 18px;
    }}
    .row {{
      display: flex;
      gap: 14px;
      align-items: center;
    }}
    .spinner {{
      width: 30px;
      height: 30px;
      border-radius: 999px;
      border: 3px solid rgba(255, 255, 255, 0.25);
      border-top-color: rgba(127, 86, 217, 1);
      animation: spin 0.9s linear infinite;
      flex: 0 0 auto;
    }}
    h1 {{
      margin: 0;
      font-size: 19px;
      font-weight: 700;
      line-height: 1.25;
    }}
    p {{
      margin: 10px 0 0;
      font-size: 14px;
      opacity: 0.9;
      line-height: 1.5;
    }}
    @keyframes spin {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
  </style>
</head>
<body>
  <div id="eduplay-preview-placeholder">
    <div class="box">
      <div class="row">
        <div class="spinner" aria-hidden="true"></div>
        <h1>{heading}</h1>
      </div>
      <p>{sub}</p>
    </div>
  </div>
</body>
</html>
"""


def ensure_preview_placeholder_file(path: Path, *, title: str, lang: str = "vi") -> None:
    try:
        p = Path(path)
    except Exception:
        return
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        html = build_preview_placeholder_html(lang=lang, title=title)
        p.write_text(html, encoding="utf-8")
    except Exception:
        pass
