import os
from pathlib import Path
from typing import Optional, List


class OcrService:
    def __init__(self):
        self._configured = False
        self._last_error = ""

    def _configure_tesseract(self) -> bool:
        if self._configured:
            return True
        try:
            import pytesseract
        except Exception as e:
            self._last_error = str(e)
            self._configured = False
            return False

        cmd = os.getenv("TESSERACT_CMD") or os.getenv("TESSERACT_PATH") or ""
        candidates: List[str] = []
        if cmd:
            candidates.append(cmd)
        candidates.extend(
            [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
        )
        for c in candidates:
            try:
                p = Path(str(c))
                if p.exists() and p.is_file():
                    pytesseract.pytesseract.tesseract_cmd = str(p)
                    self._configured = True
                    return True
            except Exception:
                continue
        self._last_error = "tesseract.exe not found"
        self._configured = False
        return False

    def last_error(self) -> str:
        return str(self._last_error or "")

    def ocr_image_bytes(self, data: bytes, lang: str = "vie+eng") -> str:
        if not self._configure_tesseract():
            raise RuntimeError(self._last_error or "OCR not available")
        from PIL import Image
        import pytesseract
        import io

        img = Image.open(io.BytesIO(data))
        try:
            img = img.convert("RGB")
        except Exception:
            pass
        try:
            return str(pytesseract.image_to_string(img, lang=lang) or "").strip()
        except Exception:
            try:
                return str(pytesseract.image_to_string(img, lang="eng") or "").strip()
            except Exception as e:
                raise RuntimeError(str(e))

    def ocr_pdf_bytes(self, data: bytes, lang: str = "vie+eng", max_pages: int = 3, dpi: int = 220) -> str:
        if not self._configure_tesseract():
            raise RuntimeError(self._last_error or "OCR not available")
        import fitz
        from PIL import Image
        import pytesseract

        doc = fitz.open(stream=data, filetype="pdf")
        chunks: List[str] = []
        try:
            total = int(doc.page_count)
        except Exception:
            total = 0
        limit_pages = min(max_pages, total) if total else max_pages
        for i in range(limit_pages):
            try:
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=dpi, alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                try:
                    txt = str(pytesseract.image_to_string(img, lang=lang) or "").strip()
                except Exception:
                    txt = str(pytesseract.image_to_string(img, lang="eng") or "").strip()
                if txt:
                    chunks.append(txt)
            except Exception:
                continue
        return "\n\n".join(chunks).strip()

