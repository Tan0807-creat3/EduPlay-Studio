(function () {
  const GLOBAL_SETTINGS_KEY = "eduplay_embedded_html";
  const GLOBAL_HASH_KEY = "eduplay_embedded_html_hash";
  const GLOBAL_REF_KEY = "eduplay_embedded_ref";
  const GLOBAL_REF_HASH_KEY = "eduplay_embedded_ref_hash";
  const SLIDE_SETTINGS_PREFIX = "eduplay_embedded_html_slide_";
  const SLIDE_HASH_PREFIX = "eduplay_embedded_html_hash_slide_";
  const SLIDE_REF_PREFIX = "eduplay_embedded_ref_slide_";
  const SLIDE_REF_HASH_PREFIX = "eduplay_embedded_ref_hash_slide_";
  const GLOBAL_REV_KEY = "eduplay_embedded_rev";
  const SLIDE_REV_PREFIX = "eduplay_embedded_rev_slide_";
  const CHUNK_NS = "urn:eduplay:embedded-html";
  const MAX_HTML_LENGTH = 2500000;
  const statusEl = () => document.getElementById("status");
  const frameEl = () => document.getElementById("htmlFrame");
  const emptyEl = () => document.getElementById("emptyState");
  const frameShellEl = () => document.getElementById("frameShell");
  const inputEl = () => document.getElementById("htmlFileInput");
  const loadBtnEl = () => document.getElementById("loadBtn");
  const fileNameEl = () => document.getElementById("fileName");
  const prevBtnEl = () => document.getElementById("prevBtn");
  const nextBtnEl = () => document.getElementById("nextBtn");
  const exitBtnEl = () => document.getElementById("exitBtn");
  const FRAME_BORDER_HIT_SIZE = 18;
  const FRAME_BORDER_READY_MS = 1400;
  let lastRev = "";
  let boundSlideId = null;
  let navInProgress = false;
  let lastRefUrl = "";
  let frameBorderReadyTimer = 0;

  function setStatus(text) {
    const el = statusEl();
    if (el) el.textContent = text || "";
  }

  function setEmpty(show) {
    const empty = emptyEl();
    const frame = frameEl();
    if (empty) empty.classList.toggle("hidden", !show);
    if (frame) frame.classList.toggle("hidden", !!show);
  }

  function setFileName(name) {
    const el = fileNameEl();
    if (!el) return;
    const v = String(name || "").trim();
    el.textContent = v ? v : "Chưa chọn file";
  }

  function setFrameBorderReady(active) {
    const shell = frameShellEl();
    if (!shell) return;
    if (frameBorderReadyTimer) {
      window.clearTimeout(frameBorderReadyTimer);
      frameBorderReadyTimer = 0;
    }
    shell.classList.toggle("resize-ready", !!active);
    if (!active) return;
    frameBorderReadyTimer = window.setTimeout(() => {
      const currentShell = frameShellEl();
      if (currentShell) currentShell.classList.remove("resize-ready");
      frameBorderReadyTimer = 0;
    }, FRAME_BORDER_READY_MS);
  }

  function isFrameBorderHit(event) {
    const shell = frameShellEl();
    if (!shell || !event) return false;
    const rect = shell.getBoundingClientRect();
    const x = Number(event.clientX);
    const y = Number(event.clientY);
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      const target = event.target;
      return !!(target && target === shell);
    }
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) return false;
    const edgeDistance = Math.min(
      x - rect.left,
      rect.right - x,
      y - rect.top,
      rect.bottom - y
    );
    return edgeDistance <= FRAME_BORDER_HIT_SIZE;
  }

  function exitFrameFocus() {
    const frame = frameEl();
    try {
      if (frame && typeof frame.blur === "function") frame.blur();
    } catch (_e) {}
    try {
      const active = document.activeElement;
      if (active && typeof active.blur === "function") active.blur();
    } catch (_e0) {}
    try {
      window.focus();
    } catch (_e2) {}
    try {
      const btn = exitBtnEl();
      if (btn && typeof btn.focus === "function") {
        btn.focus();
        return;
      }
    } catch (_e3) {}
    try {
      if (document && document.body) {
        document.body.setAttribute("tabindex", "-1");
        if (typeof document.body.focus === "function") document.body.focus();
      }
    } catch (_e4) {}
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

  function toUrl(value) {
    const v = String(value || "").trim();
    if (!v) return "";
    if (v.startsWith("http://") || v.startsWith("https://")) return v;
    if (v.startsWith("/")) return `${location.origin}${v}`;
    return `${location.origin}/${v.replace(/^\/+/, "")}`;
  }

  function hasExternalRefs(htmlText) {
    const html = String(htmlText || "");
    return /(?:src|href)\s*=\s*["']\s*https?:\/\//i.test(html);
  }

  function customXmlEnabled() {
    try {
      return !!(Office && Office.context && Office.context.document && Office.context.document.customXmlParts);
    } catch (_e) {
      return false;
    }
  }

  function getPartsByNamespace(ns) {
    return new Promise((resolve, reject) => {
      try {
        Office.context.document.customXmlParts.getByNamespaceAsync(ns, (res) => {
          if (res.status === Office.AsyncResultStatus.Succeeded) resolve(res.value || []);
          else reject(res.error || new Error("getByNamespace failed"));
        });
      } catch (e) {
        reject(e);
      }
    });
  }

  function getPartXml(part) {
    return new Promise((resolve, reject) => {
      try {
        part.getXmlAsync((res) => {
          if (res.status === Office.AsyncResultStatus.Succeeded) resolve(String(res.value || ""));
          else reject(res.error || new Error("getXml failed"));
        });
      } catch (e) {
        reject(e);
      }
    });
  }

  function getAllSettings() {
    return new Promise((resolve) => {
      try {
        if (!Office || !Office.context || !Office.context.document || !Office.context.document.settings) {
          resolve(null);
          return;
        }
        const s = Office.context.document.settings;
        if (!s || typeof s.getAllAsync !== "function") {
          resolve(null);
          return;
        }
        s.getAllAsync((res) => {
          if (res && res.status === Office.AsyncResultStatus.Succeeded) resolve(res.value || {});
          else resolve(null);
        });
      } catch (_e) {
        resolve(null);
      }
    });
  }

  async function resolveSlideIdFallbackFromSettings() {
    const all = await getAllSettings();
    if (!all) return null;
    let bestId = null;
    let bestRev = 0;
    try {
      for (const k of Object.keys(all)) {
        if (!k || !String(k).startsWith(SLIDE_REV_PREFIX)) continue;
        const id = String(k).slice(SLIDE_REV_PREFIX.length);
        if (!id) continue;
        const v = all[k];
        const rev = Number(String(v || "").trim() || "0");
        if (rev > bestRev) {
          bestRev = rev;
          bestId = id;
        }
      }
    } catch (_e) {}
    if (bestId) return bestId;
    try {
      for (const k of Object.keys(all)) {
        if (!k || !String(k).startsWith(SLIDE_SETTINGS_PREFIX)) continue;
        const id = String(k).slice(SLIDE_SETTINGS_PREFIX.length);
        if (!id) continue;
        const v = String(all[k] || "");
        if (v.trim()) return id;
      }
    } catch (_e2) {}
    try {
      for (const k of Object.keys(all)) {
        if (!k || !String(k).startsWith(SLIDE_REF_PREFIX)) continue;
        const id = String(k).slice(SLIDE_REF_PREFIX.length);
        if (!id) continue;
        const v = all[k];
        if (v && typeof v === "object" && v.url) return id;
      }
    } catch (_e3) {}
    return null;
  }

  function parseChunkXml(xml) {
    try {
      const doc = new DOMParser().parseFromString(String(xml || ""), "application/xml");
      const el = doc && doc.documentElement ? doc.documentElement : null;
      if (!el) return null;
      const key = el.getAttribute("key") || "";
      const idx = parseInt(el.getAttribute("idx") || "0", 10);
      const total = parseInt(el.getAttribute("total") || "0", 10);
      const data = el.textContent || "";
      return { key, idx, total, data };
    } catch (_e) {
      return null;
    }
  }

  async function loadHtmlFromCustomXml(key) {
    if (!customXmlEnabled()) return "";
    const parts = await getPartsByNamespace(CHUNK_NS);
    const chunks = [];
    let expectedTotal = 0;
    for (const p of parts) {
      try {
        const xml = await getPartXml(p);
        const parsed = parseChunkXml(xml);
        if (!parsed) continue;
        if (String(parsed.key || "") !== String(key || "")) continue;
        chunks.push(parsed);
        expectedTotal = Math.max(expectedTotal, parsed.total || 0);
      } catch (_e) {}
    }
    if (!chunks.length) return "";
    chunks.sort((a, b) => (a.idx || 0) - (b.idx || 0));
    if (expectedTotal && chunks.length < expectedTotal) return "";
    let out = "";
    for (const c of chunks) out += String(c.data || "");
    return out;
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

  async function ensureBoundSlideId() {
    if (boundSlideId) return boundSlideId;
    try {
      const cached = sessionStorage.getItem("eduplay_bound_slide_id");
      if (cached) {
        boundSlideId = String(cached);
        return boundSlideId;
      }
    } catch (_e) {}
    const current = await getSelectedSlideId();
    if (current) {
      await updateBoundSlideId(String(current));
      return boundSlideId;
    }
    const fallback = await resolveSlideIdFallbackFromSettings();
    if (fallback) {
      await updateBoundSlideId(String(fallback));
      return boundSlideId;
    }
    return null;
  }

  async function updateBoundSlideId(slideId) {
    const v = String(slideId || "").trim();
    if (!v) return;
    boundSlideId = v;
    try {
      sessionStorage.setItem("eduplay_bound_slide_id", boundSlideId);
    } catch (_e) {}
  }

  function injectSlideNavBridge(htmlText) {
    const html = String(htmlText || "");
    const snippet =
      "<script>(function(){try{window.addEventListener(\"keydown\",function(e){var k=(e&&e.key)?e.key:\"\";var d=0;if(k===\"ArrowRight\"||k===\"ArrowDown\")d=1;else if(k===\"ArrowLeft\"||k===\"ArrowUp\")d=-1;else if(k===\"Escape\"){try{parent.postMessage({type:\"eduplay_escape\"},\"*\");}catch(_e){}return;}else return;try{parent.postMessage({type:\"eduplay_nav\",delta:d},\"*\");}catch(_e4){}try{e.preventDefault();e.stopPropagation();}catch(_e2){}},true);}catch(_e3){}})();</script>";
    if (/<\/body\s*>/i.test(html)) return html.replace(/<\/body\s*>/i, snippet + "</body>");
    if (/<\/html\s*>/i.test(html)) return html.replace(/<\/html\s*>/i, snippet + "</html>");
    return html + snippet;
  }

  function clearBoundSlide() {
    boundSlideId = null;
    try {
      sessionStorage.removeItem("eduplay_bound_slide_id");
    } catch (_e) {}
  }

  async function navigateSlide(delta) {
    const step = Number(delta || 0);
    if (!step) return;
    if (navInProgress) return;
    navInProgress = true;
    try {
      if (!Office || !Office.context || !Office.context.document || !Office.context.document.goToByIdAsync) return;
      const goTo = step > 0 ? Office.Index.Next : Office.Index.Previous;
      await new Promise((resolve) => {
        Office.context.document.goToByIdAsync(goTo, Office.GoToType.Index, () => resolve());
      });
      clearBoundSlide();
      await refreshFromDocument(true);
    } catch (_e) {} finally {
      navInProgress = false;
    }
  }

  function installInteractionHandlers() {
    window.addEventListener("message", (ev) => {
      const data = ev && ev.data ? ev.data : null;
      if (!data || !data.type) return;
      if (data.type === "eduplay_nav") {
        const d = Number(data.delta || 0);
        if (d === 1 || d === -1) navigateSlide(d);
      } else if (data.type === "eduplay_escape") {
        exitFrameFocus();
      }
    });

    window.addEventListener("keydown", (e) => {
      const k = e && e.key ? e.key : "";
      if (k === "ArrowRight" || k === "ArrowDown") {
        try {
          e.preventDefault();
          e.stopPropagation();
        } catch (_e) {}
        navigateSlide(1);
      } else if (k === "ArrowLeft" || k === "ArrowUp") {
        try {
          e.preventDefault();
          e.stopPropagation();
        } catch (_e) {}
        navigateSlide(-1);
      } else if (k === "Escape") {
        exitFrameFocus();
      }
    }, true);

    try {
      Office.context.document.addHandlerAsync(
        Office.EventType.DocumentSelectionChanged,
        async () => {
          const current = await getSelectedSlideId();
          if (current && current !== boundSlideId) {
            await updateBoundSlideId(current);
            await refreshFromDocument(true);
          }
        },
        () => {}
      );
    } catch (_e) {}

    document.addEventListener("mousedown", (e) => {
      const frame = frameEl();
      if (!frame) return;
      if (isFrameBorderHit(e)) {
        setFrameBorderReady(true);
        exitFrameFocus();
      } else if (e && e.target && frame.contains(e.target)) {
        setFrameBorderReady(false);
        try {
          frame.focus();
        } catch (_e) {}
      } else {
        setFrameBorderReady(false);
        exitFrameFocus();
      }
    }, true);

    const prevBtn = prevBtnEl();
    if (prevBtn) prevBtn.addEventListener("click", () => navigateSlide(-1));
    const nextBtn = nextBtnEl();
    if (nextBtn) nextBtn.addEventListener("click", () => navigateSlide(1));
    const exitBtn = exitBtnEl();
    if (exitBtn) exitBtn.addEventListener("click", exitFrameFocus);
  }

  function keysForSlideId(slideId) {
    const id = String(slideId || "").trim();
    if (!id) {
      return {
        htmlKey: GLOBAL_SETTINGS_KEY,
        hashKey: GLOBAL_HASH_KEY,
        refKey: GLOBAL_REF_KEY,
        refHashKey: GLOBAL_REF_HASH_KEY,
        revKey: GLOBAL_REV_KEY,
        label: "toàn bộ file PPT",
      };
    }
    return {
      htmlKey: `${SLIDE_SETTINGS_PREFIX}${id}`,
      hashKey: `${SLIDE_HASH_PREFIX}${id}`,
      refKey: `${SLIDE_REF_PREFIX}${id}`,
      refHashKey: `${SLIDE_REF_HASH_PREFIX}${id}`,
      revKey: `${SLIDE_REV_PREFIX}${id}`,
      label: `slide ${id}`,
    };
  }

  function renderRef(refValue) {
    const frame = frameEl();
    if (!frame) return;
    const ref = refValue && typeof refValue === "object" ? refValue : null;
    const url = ref && ref.url ? toUrl(ref.url) : "";
    if (!url) {
      renderHtml("");
      return;
    }
    const busted = `${url}${url.includes("?") ? "&" : "?"}v=${encodeURIComponent(Date.now())}`;
    lastRefUrl = busted;
    setEmpty(false);
    setStatus("Đang nạp nội dung EduPlay...");
    (async () => {
      try {
        const res = await fetch(busted, { cache: "no-store" });
        const txt = await res.text();
        if (!res.ok || !String(txt || "").trim()) throw new Error("empty");
        if (busted !== lastRefUrl) return;
        try {
          frame.removeAttribute("src");
        } catch (_e2) {}
        frame.srcdoc = injectSlideNavBridge(txt);
        setStatus("Đã nạp nội dung EduPlay.");
        return;
      } catch (_e) {}
      if (busted !== lastRefUrl) return;
      try {
        frame.removeAttribute("srcdoc");
      } catch (_e3) {}
      frame.src = busted;
      setStatus("Đã nạp nội dung EduPlay.");
    })();
  }

  function renderHtml(htmlText) {
    const frame = frameEl();
    if (!frame) return;
    const html = String(htmlText || "");
    if (!html.trim()) {
      frame.removeAttribute("src");
      frame.srcdoc = "";
      setEmpty(true);
      setStatus("Chưa có dữ liệu EduPlay trong file PPT.");
      return;
    }
    frame.srcdoc = injectSlideNavBridge(html);
    setEmpty(false);
    setStatus("Đã nạp nội dung EduPlay vào slide.");
  }

  function saveToSettings(htmlText, slideId) {
    return new Promise((resolve, reject) => {
      try {
        const safeHtml = String(htmlText || "");
        const keys = keysForSlideId(slideId);
        Office.context.document.settings.set(keys.htmlKey, safeHtml);
        Office.context.document.settings.set(keys.hashKey, hashText(safeHtml));
        Office.context.document.settings.saveAsync((res) => {
          if (res.status === Office.AsyncResultStatus.Succeeded) resolve();
          else reject(new Error(res.error && res.error.message ? res.error.message : "Save failed"));
        });
      } catch (e) {
        reject(e);
      }
    });
  }

  function bumpRevision(slideId) {
    return new Promise((resolve) => {
      try {
        const keys = keysForSlideId(slideId);
        Office.context.document.settings.set(keys.revKey, String(Date.now()));
        Office.context.document.settings.saveAsync(() => resolve());
      } catch (_e) {
        resolve();
      }
    });
  }

  function loadFromSettings(slideId) {
    try {
      const keys = keysForSlideId(slideId);
      return {
        ref: Office.context.document.settings.get(keys.refKey) || null,
        refHash: Office.context.document.settings.get(keys.refHashKey) || "",
        html: Office.context.document.settings.get(keys.htmlKey) || "",
        hash: Office.context.document.settings.get(keys.hashKey) || "",
      };
    } catch (_err) {
      return { ref: null, refHash: "", html: "", hash: "" };
    }
  }

  async function refreshFromDocument(force) {
    try {
      const current = await getSelectedSlideId();
      if (current && current !== boundSlideId) {
        await updateBoundSlideId(String(current));
      }
    } catch (_e) {}
    const slideId = (await ensureBoundSlideId()) || "";
    const keys = keysForSlideId(slideId);
    let rev = "";
    try {
      rev = String(Office.context.document.settings.get(keys.revKey) || "");
    } catch (_e) {
      rev = "";
    }
    if (!force && rev && rev === lastRev) return;
    if (rev) lastRev = rev;

    const embedded = await loadHtmlFromCustomXml(String(slideId || ""));
    if (embedded && String(embedded).trim()) {
      renderHtml(embedded);
      setStatus(`Đã nạp nội dung EduPlay (${keys.label}).`);
      return;
    }

    const saved = loadFromSettings(slideId);
    if (saved.ref && typeof saved.ref === "object" && saved.ref.url) {
      renderRef(saved.ref);
      setStatus(`Đã nạp nội dung EduPlay (${keys.label}).`);
      return;
    }
    renderHtml(saved.html);
    if (!saved.html.trim()) {
      setStatus(`Chưa có dữ liệu EduPlay cho ${keys.label}.`);
    } else {
      setStatus(`Đã nạp nội dung EduPlay (${keys.label}).`);
    }
  }

  async function importSelectedFile() {
    const input = inputEl();
    if (!input || !input.files || !input.files.length) {
      setStatus("Vui lòng chọn file HTML trước.");
      return;
    }
    const file = input.files[0];
    setFileName(file && file.name ? file.name : "");
    const reader = new FileReader();
    reader.onload = async () => {
      const html = String(reader.result || "");
      if (!html.trim()) {
        setStatus("File HTML trống.");
        return;
      }
      if (html.length > MAX_HTML_LENGTH) {
        setStatus("File HTML quá lớn để lưu trong PowerPoint.");
        return;
      }
      if (hasExternalRefs(html)) {
        setStatus("File HTML có tham chiếu HTTP/HTTPS bên ngoài. Một số tài nguyên có thể không load được trong viewer.");
      }
      const slideId = await ensureBoundSlideId();
      try {
        await saveToSettings(html, slideId || "");
        await bumpRevision(slideId || "");
        renderHtml(html);
        setStatus(`Đã lưu và nạp: ${file.name} (${keysForSlideId(slideId || "").label}).`);
      } catch (e) {
        setStatus(`Đã đọc file nhưng lưu thất bại: ${e}`);
      }
    };
    reader.onerror = () => setStatus("Không đọc được file.");
    reader.readAsText(file, "utf-8");
  }

  Office.onReady(() => {
    installInteractionHandlers();
    const btn = loadBtnEl();
    const input = inputEl();
    if (btn && input) {
      btn.addEventListener("click", () => input.click());
    }
    if (input) {
      input.addEventListener("change", () => {
        importSelectedFile();
      });
    }
    setFileName("");
    refreshFromDocument(true);
    setInterval(() => {
      refreshFromDocument(false);
    }, 1500);
  });
})();
