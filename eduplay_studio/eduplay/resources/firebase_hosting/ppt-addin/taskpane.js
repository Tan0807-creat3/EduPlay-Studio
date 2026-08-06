(function () {
  const GLOBAL_SETTINGS_KEY = "eduplay_embedded_html";
  const GLOBAL_HASH_KEY = "eduplay_embedded_html_hash";
  const SLIDE_SETTINGS_PREFIX = "eduplay_embedded_html_slide_";
  const SLIDE_HASH_PREFIX = "eduplay_embedded_html_hash_slide_";
  const MAX_HTML_LENGTH = 2500000;
  const STATUS_CLASSES = ["status-info", "status-success", "status-error"];

  function setStatus(text, type) {
    const el = document.getElementById("status");
    if (!el) return;
    el.textContent = text || "";
    STATUS_CLASSES.forEach((cls) => el.classList.remove(cls));
    if (type === "success") {
      el.classList.add("status-success");
    } else if (type === "error") {
      el.classList.add("status-error");
    } else {
      el.classList.add("status-info");
    }
  }

  function getFrame() {
    return document.getElementById("htmlFrame");
  }

  function getInput() {
    return document.getElementById("htmlFileInput");
  }

  function loadIntoFrame(htmlText) {
    const frame = getFrame();
    if (!frame) return;
    frame.srcdoc = htmlText || "<html><body></body></html>";
  }

  function hashText(value) {
    const text = String(value || "");
    let hash = 0;
    for (let i = 0; i < text.length; i += 1) {
      hash = ((hash << 5) - hash) + text.charCodeAt(i);
      hash |= 0;
    }
    return String(hash);
  }

  function hasExternalRefs(htmlText) {
    const html = String(htmlText || "");
    return /(?:src|href)\s*=\s*["']\s*https?:\/\//i.test(html);
  }

  async function getSelectedSlideId() {
    try {
      if (typeof PowerPoint === "undefined" || !PowerPoint || !PowerPoint.run) return null;
      return await PowerPoint.run(async (context) => {
        const slides = context.presentation.getSelectedSlides();
        slides.load("items/id");
        await context.sync();
        const first = slides.items && slides.items.length ? slides.items[0] : null;
        return first && first.id ? String(first.id) : null;
      });
    } catch (_e) {
      return null;
    }
  }

  function keysForSlideId(slideId) {
    const id = String(slideId || "").trim();
    if (!id) {
      return { htmlKey: GLOBAL_SETTINGS_KEY, hashKey: GLOBAL_HASH_KEY, label: "toàn bộ file PPT" };
    }
    return {
      htmlKey: `${SLIDE_SETTINGS_PREFIX}${id}`,
      hashKey: `${SLIDE_HASH_PREFIX}${id}`,
      label: `slide ${id}`,
    };
  }

  function saveToDocument(htmlText, slideId) {
    return new Promise((resolve, reject) => {
      try {
        const safeHtml = String(htmlText || "");
        const keys = keysForSlideId(slideId);
        Office.context.document.settings.set(keys.htmlKey, safeHtml);
        Office.context.document.settings.set(keys.hashKey, hashText(safeHtml));
        Office.context.document.settings.saveAsync((res) => {
          if (res.status === Office.AsyncResultStatus.Succeeded) {
            resolve();
          } else {
            reject(new Error(res.error && res.error.message ? res.error.message : "Save failed"));
          }
        });
      } catch (e) {
        reject(e);
      }
    });
  }

  function loadFromDocument(slideId) {
    try {
      const keys = keysForSlideId(slideId);
      return Office.context.document.settings.get(keys.htmlKey) || "";
    } catch (_e) {
      return "";
    }
  }

  async function onLoadHtmlClick() {
    const input = getInput();
    if (!input || !input.files || !input.files.length) {
      setStatus("Vui lòng chọn file HTML trước.", "error");
      return;
    }
    const file = input.files[0];
    const reader = new FileReader();
    reader.onload = async () => {
      const html = String(reader.result || "");
      if (!html.trim()) {
        setStatus("File HTML trống.", "error");
        return;
      }
      if (html.length > MAX_HTML_LENGTH) {
        setStatus("File HTML quá lớn để lưu trong PowerPoint. Hãy export dạng single-file nhỏ hơn.", "error");
        return;
      }
      if (hasExternalRefs(html)) {
        setStatus("File HTML có tham chiếu HTTP/HTTPS bên ngoài. Vì an toàn, chỉ hỗ trợ single-file không tải tài nguyên từ Internet.", "error");
        return;
      }
      const slideId = await getSelectedSlideId();
      if (!slideId) {
        setStatus("Hãy click chọn slide (hoặc click chọn viewer trên slide) rồi import lại.", "error");
        return;
      }
      loadIntoFrame(html);
      try {
        await saveToDocument(html, slideId);
        setStatus(`Đã gán HTML cho ${keysForSlideId(slideId).label}: ${file.name}`, "success");
      } catch (e) {
        setStatus(`Đã nhập HTML nhưng chưa lưu được vào PPT: ${e}`, "error");
      }
    };
    reader.onerror = () => setStatus("Không đọc được file.", "error");
    reader.readAsText(file, "utf-8");
  }

  async function onSaveClick() {
    const frame = getFrame();
    const html = frame ? frame.srcdoc || "" : "";
    try {
      const slideId = await getSelectedSlideId();
      if (!slideId) {
        setStatus("Hãy click chọn slide (hoặc click chọn viewer trên slide) rồi lưu lại.", "error");
        return;
      }
      if (html.length > MAX_HTML_LENGTH) {
        setStatus("HTML hiện tại quá lớn để lưu trong PowerPoint.", "error");
        return;
      }
      if (hasExternalRefs(html)) {
        setStatus("HTML có tham chiếu HTTP/HTTPS bên ngoài. Vì an toàn, chỉ hỗ trợ single-file không tải tài nguyên từ Internet.", "error");
        return;
      }
      await saveToDocument(html, slideId);
      setStatus(`Đã lưu HTML cho ${keysForSlideId(slideId).label}.`, "success");
    } catch (e) {
      setStatus(`Lưu thất bại: ${e}`, "error");
    }
  }

  async function onClearClick() {
    loadIntoFrame("");
    try {
      const slideId = await getSelectedSlideId();
      if (!slideId) {
        setStatus("Hãy click chọn slide (hoặc click chọn viewer trên slide) rồi xóa lại.", "error");
        return;
      }
      await saveToDocument("", slideId);
      setStatus(`Đã xóa nội dung của ${keysForSlideId(slideId).label}.`, "success");
    } catch (_e) {
      setStatus("Đã xóa phần hiển thị (lưu thất bại).", "error");
    }
  }

  function insertSlideUiPlaceholder() {
    const html =
      "<div style=\"font-family:Segoe UI,Arial,sans-serif;padding:18px;border:2px solid #2563eb;" +
      "border-radius:14px;background:#eff6ff;color:#0f172a;max-width:760px\">" +
      "<div style=\"font-size:22px;font-weight:700;margin-bottom:10px\">EduPlay Viewer Placeholder</div>" +
      "<div style=\"font-size:14px;line-height:1.6\">" +
      "Vào tab <b>Insert</b> và bấm <b>My Add-ins</b> để chèn <b>EduPlay Viewer</b> lên slide này. " +
      "Sau đó dùng nút <b>Import EduPlay</b> để nạp file HTML từ EduPlay Studio." +
      "</div>" +
      "</div>";
    return new Promise((resolve, reject) => {
      try {
        Office.context.document.setSelectedDataAsync(
          html,
          { coercionType: Office.CoercionType.Text },
          (res) => {
            if (res.status === Office.AsyncResultStatus.Succeeded) {
              resolve();
            } else {
              reject(new Error(res.error && res.error.message ? res.error.message : "Insert failed"));
            }
          }
        );
      } catch (e) {
        reject(e);
      }
    });
  }

  async function onInsertUiClick() {
    try {
      await insertSlideUiPlaceholder();
      setStatus(
        "Đã chèn khung hướng dẫn. Để có web viewer thật trên slide, hãy vào Insert > My Add-ins > EduPlay Viewer.",
        "success"
      );
    } catch (e) {
      setStatus(`Không chèn được vào slide: ${e}. Hãy chọn một textbox trước.`, "error");
    }
  }

  async function refreshPreviewForSelection() {
    const slideId = await getSelectedSlideId();
    const saved = loadFromDocument(slideId);
    if (saved) {
      loadIntoFrame(saved);
      setStatus(`Đã khôi phục HTML của ${keysForSlideId(slideId).label}.`, "success");
    } else if (slideId) {
      loadIntoFrame("");
      setStatus(`Chưa có HTML cho ${keysForSlideId(slideId).label}. Hãy import file HTML.`, "info");
    } else {
      const fallback = loadFromDocument("");
      if (fallback) {
        loadIntoFrame(fallback);
        setStatus("Đã khôi phục HTML (chế độ cũ theo toàn bộ PPT).", "success");
      } else {
        loadIntoFrame("");
        setStatus("Sẵn sàng. Hãy click chọn slide rồi import file HTML.", "info");
      }
    }
  }

  Office.onReady(() => {
    const btnLoad = document.getElementById("loadBtn");
    const btnSave = document.getElementById("saveBtn");
    const btnInsertUi = document.getElementById("insertUiBtn");
    const btnClear = document.getElementById("clearBtn");
    if (btnLoad) btnLoad.addEventListener("click", onLoadHtmlClick);
    if (btnSave) btnSave.addEventListener("click", onSaveClick);
    if (btnInsertUi) btnInsertUi.addEventListener("click", onInsertUiClick);
    if (btnClear) btnClear.addEventListener("click", onClearClick);

    refreshPreviewForSelection();
    try {
      Office.context.document.addHandlerAsync(
        Office.EventType.DocumentSelectionChanged,
        () => refreshPreviewForSelection(),
        () => {}
      );
    } catch (_e) {}
  });
})();
