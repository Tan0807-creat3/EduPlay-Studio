using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Xml.Linq;
using EduPlayPowerPointAddin.Core;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using Microsoft.Office.Core;
using PowerPoint = Microsoft.Office.Interop.PowerPoint;

namespace EduPlay.PowerPointAddin
{
    internal static class EduPlayHtmlFrames
    {
        private const string XmlNamespace = "urn:eduplay:powerpoint:html";
        private const string XmlRootName = "EduPlayHtml";
        private const string TagTypeKey = "EduPlay.Type";
        private const string TagTypeValue = "HtmlFrame";
        private const string TagHtmlIdKey = "EduPlay.HtmlId";
        private const string TagHtmlNameKey = "EduPlay.HtmlName";
        private const string TagRendererKey = "EduPlay.Renderer";
        private const string TagRendererActiveXValue = "ActiveXWebBrowser";
        private const string TagRendererWebView2OverlayValue = "WebView2Overlay";
        private const int RefreshIntervalMs = 1000;
        private static readonly int FrameBorderRgb = System.Drawing.ColorTranslator.ToOle(System.Drawing.Color.FromArgb(148, 163, 184));
        private const float FrameBorderWeightPoints = 3.5f;
        private const int EditOverlayInsetPixels = 6;

        private static HtmlOverlayController _controller;

        internal static void Initialize(PowerPoint.Application application)
        {
            if (_controller != null)
            {
                return;
            }

            _controller = new HtmlOverlayController(application);
        }

        internal static void Shutdown()
        {
            if (_controller == null)
            {
                return;
            }

            _controller.Dispose();
            _controller = null;
        }

        internal static void ImportHtmlToCurrentSlide(string htmlPath)
        {
            if (string.IsNullOrWhiteSpace(htmlPath) || !File.Exists(htmlPath))
            {
                throw new FileNotFoundException("File HTML không tồn tại.", htmlPath);
            }

            var app = Globals.ThisAddIn?.Application;
            if (app == null)
            {
                throw new InvalidOperationException("Không lấy được PowerPoint Application.");
            }

            var pres = app.ActivePresentation;
            if (pres == null)
            {
                throw new InvalidOperationException("Chưa có file PowerPoint nào đang mở.");
            }

            var slide = GetActiveSlide(app);
            if (slide == null)
            {
                throw new InvalidOperationException("Không lấy được slide hiện tại.");
            }

            ThisAddIn.Log($"Importing HTML from: {htmlPath}");
            
            HtmlBundle bundle = null;
            try
            {
                bundle = CreateBundleFromHtmlPath(htmlPath);
            }
            catch (Exception ex)
            {
                ThisAddIn.LogException("Failed to create bundle from HTML path", ex);
                throw new IOException($"Không thể đọc file HTML và các file liên quan. Lỗi: {ex.Message}", ex);
            }

            if (bundle == null || bundle.Files.Length == 0)
            {
                throw new IOException("Không có file nào được load từ thư mục HTML.");
            }

            var htmlId = AddBundleToPresentation(pres, bundle);
            CreateFrameShape(slide, htmlId, bundle.EntryPath);

            try
            {
                pres.Saved = MsoTriState.msoFalse;
            }
            catch
            {
            }

            ThisAddIn.Log($"HTML imported successfully. ID: {htmlId}, Files: {bundle.Files.Length}");
        }

        internal static void ImportHtmlTextToCurrentSlide(
            string htmlText,
            string htmlName,
            float? frameWidthPoints = null,
            float? frameHeightPoints = null)
        {
            if (string.IsNullOrWhiteSpace(htmlText))
            {
                throw new InvalidOperationException("HTML trống.");
            }

            var app = Globals.ThisAddIn?.Application;
            if (app == null)
            {
                throw new InvalidOperationException("Không lấy được PowerPoint Application.");
            }

            var pres = app.ActivePresentation;
            if (pres == null)
            {
                throw new InvalidOperationException("Chưa có file PowerPoint nào đang mở.");
            }

            var slide = GetActiveSlide(app);
            if (slide == null)
            {
                throw new InvalidOperationException("Không lấy được slide hiện tại.");
            }

            var name = string.IsNullOrWhiteSpace(htmlName) ? "index.html" : htmlName.Trim();
            var bytes = Encoding.UTF8.GetBytes(htmlText);
            var bundle = new HtmlBundle(name, new[] { new HtmlBundleFile(name, bytes) });

            var htmlId = AddBundleToPresentation(pres, bundle);
            CreateFrameShape(slide, htmlId, bundle.EntryPath, frameWidthPoints, frameHeightPoints);

            try
            {
                pres.Saved = MsoTriState.msoFalse;
            }
            catch
            {
            }
        }

        private static PowerPoint.Slide GetActiveSlide(PowerPoint.Application app)
        {
            try
            {
                if (app.ActiveWindow?.View == null)
                {
                    return null;
                }

                return app.ActiveWindow.View.Slide as PowerPoint.Slide;
            }
            catch
            {
                return null;
            }
        }

        private static HtmlBundle CreateBundleFromHtmlPath(string htmlPath)
        {
            // Chỉ đọc 1 file HTML duy nhất (đã self-contained, không cần folder)
            if (!File.Exists(htmlPath))
            {
                throw new FileNotFoundException("File HTML không tồn tại.", htmlPath);
            }

            byte[] htmlBytes = null;
            
            // Retry logic for locked files
            for (int retry = 0; retry < 3; retry++)
            {
                try
                {
                    htmlBytes = File.ReadAllBytes(htmlPath);
                    break;
                }
                catch (IOException ex) when (retry < 2)
                {
                    ThisAddIn.Log($"Retry reading file (attempt {retry + 1}): {ex.Message}");
                    System.Threading.Thread.Sleep(100);
                }
                catch (Exception ex)
                {
                    ThisAddIn.LogException($"Cannot read HTML file: {htmlPath}", ex);
                    throw;
                }
            }

            if (htmlBytes == null)
            {
                throw new IOException($"Không thể đọc file HTML sau 3 lần thử: {htmlPath}");
            }

            var fileName = Path.GetFileName(htmlPath);
            var file = new HtmlBundleFile(fileName, htmlBytes);
            
            return new HtmlBundle(fileName, new[] { file });
        }

        private static string AddBundleToPresentation(PowerPoint.Presentation pres, HtmlBundle bundle)
        {
            var id = Guid.NewGuid().ToString("N");
            var xml = new XDocument(
                new XElement(XName.Get(XmlRootName, XmlNamespace),
                    new XAttribute("id", id),
                    new XAttribute("name", bundle.EntryPath ?? "index.html"),
                    bundle.Files.Select(file =>
                        new XElement(XName.Get("File", XmlNamespace),
                            new XAttribute("path", file.Path),
                            Convert.ToBase64String(file.Bytes)))));

            pres.CustomXMLParts.Add(xml.ToString(SaveOptions.DisableFormatting));
            return id;
        }

        private static string MakeRelativePath(string rootDir, string fullPath)
        {
            var rootUri = new Uri(AppendDirectorySeparator(rootDir));
            var fileUri = new Uri(fullPath);
            return Uri.UnescapeDataString(rootUri.MakeRelativeUri(fileUri).ToString())
                .Replace('/', Path.DirectorySeparatorChar);
        }

        private static string AppendDirectorySeparator(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return path;
            }

            return path.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal)
                ? path
                : path + Path.DirectorySeparatorChar;
        }

        private static string GetHtmlCacheRoot()
        {
            try
            {
                var baseDir = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrWhiteSpace(baseDir))
                {
                    baseDir = Path.GetTempPath();
                }

                var root = Path.Combine(baseDir, "EduPlayPowerPointAddin", "html");
                Directory.CreateDirectory(root);
                return root;
            }
            catch
            {
                try
                {
                    var root = Path.Combine(Path.GetTempPath(), "EduPlayPowerPointAddin", "html");
                    Directory.CreateDirectory(root);
                    return root;
                }
                catch
                {
                    return Path.GetTempPath();
                }
            }
        }

        private static void CreateFrameShape(
            PowerPoint.Slide slide,
            string htmlId,
            string htmlName,
            float? requestedWidthPoints = null,
            float? requestedHeightPoints = null)
        {
            var pres = slide.Parent as PowerPoint.Presentation;
            var slideWidth = pres?.PageSetup?.SlideWidth ?? 960f;
            var slideHeight = pres?.PageSetup?.SlideHeight ?? 540f;
            var frameSize = HtmlFrameLayout.ResolveFrameSize(
                slideWidth,
                slideHeight,
                requestedWidthPoints,
                requestedHeightPoints);
            var width = frameSize.Width;
            var height = frameSize.Height;
            var left = (slideWidth - width) / 2f;
            var top = (slideHeight - height) / 2f;

            var shape = slide.Shapes.AddShape(MsoAutoShapeType.msoShapeRectangle, left, top, width, height);
            shape.Name = "EduPlayHtmlFrame_" + htmlId;
            shape.Tags.Add(TagTypeKey, TagTypeValue);
            shape.Tags.Add(TagHtmlIdKey, htmlId);
            shape.Tags.Add(TagHtmlNameKey, htmlName ?? "index.html");
            shape.Tags.Add(TagRendererKey, TagRendererWebView2OverlayValue);

            try
            {
                ApplyFrameChrome(shape);
            }
            catch
            {
            }
        }

        private static HtmlBundle TryGetHtmlBundle(PowerPoint.Presentation pres, string htmlId)
        {
            if (pres == null || string.IsNullOrWhiteSpace(htmlId))
            {
                return null;
            }

            foreach (CustomXMLPart part in pres.CustomXMLParts)
            {
                try
                {
                    var doc = XDocument.Parse(part.XML);
                    var root = doc.Root;
                    if (root == null)
                    {
                        continue;
                    }

                    if (root.Name.LocalName != XmlRootName || root.Name.NamespaceName != XmlNamespace)
                    {
                        continue;
                    }

                    var idAttr = root.Attribute("id")?.Value;
                    if (!string.Equals(idAttr, htmlId, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    var entryPath = root.Attribute("name")?.Value;
                    var files = root.Elements(XName.Get("File", XmlNamespace))
                        .Select(element =>
                        {
                            var path = element.Attribute("path")?.Value;
                            var base64 = (element.Value ?? string.Empty).Trim();
                            if (string.IsNullOrWhiteSpace(path) || string.IsNullOrWhiteSpace(base64))
                            {
                                return null;
                            }

                            return new HtmlBundleFile(path, Convert.FromBase64String(base64));
                        })
                        .Where(file => file != null)
                        .ToArray();

                    if (files.Length == 0)
                    {
                        return null;
                    }

                    return new HtmlBundle(entryPath ?? "index.html", files);
                }
                catch
                {
                }
            }

            return null;
        }

        private static string ComputeSha256Hex(byte[] bytes)
        {
            if (bytes == null)
            {
                return string.Empty;
            }

            using (var sha = SHA256.Create())
            {
                var hash = sha.ComputeHash(bytes);
                var sb = new StringBuilder(hash.Length * 2);
                for (var i = 0; i < hash.Length; i++)
                {
                    sb.Append(hash[i].ToString("x2"));
                }
                return sb.ToString();
            }
        }

        private static void ApplyFrameChrome(PowerPoint.Shape shape)
        {
            if (shape == null)
            {
                return;
            }

            try
            {
                shape.Fill.Visible = MsoTriState.msoTrue;
                shape.Fill.ForeColor.RGB = 0xFFFFFF;
                shape.Fill.Transparency = 0f;
                shape.Line.Visible = MsoTriState.msoTrue;
                shape.Line.ForeColor.RGB = FrameBorderRgb;
                shape.Line.Weight = FrameBorderWeightPoints;
                shape.TextFrame.TextRange.Text = "";
            }
            catch
            {
            }
        }

        private static PowerPoint.Shape EnsureOverlayFrame(PowerPoint.Slide slide, PowerPoint.Shape shape)
        {
            if (slide == null || shape == null)
            {
                return shape;
            }

            var renderer = SafeGetTag(shape, TagRendererKey);
            if (string.Equals(renderer, TagRendererWebView2OverlayValue, StringComparison.OrdinalIgnoreCase))
            {
                return shape;
            }

            bool isOle = false;
            try
            {
                isOle = shape.Type == MsoShapeType.msoEmbeddedOLEObject || shape.Type == MsoShapeType.msoLinkedOLEObject;
            }
            catch
            {
                isOle = false;
            }

            if (!string.IsNullOrWhiteSpace(renderer) && !isOle)
            {
                try
                {
                    shape.Tags.Add(TagRendererKey, TagRendererWebView2OverlayValue);
                }
                catch
                {
                }
                return shape;
            }

            float left;
            float top;
            float width;
            float height;
            try
            {
                left = shape.Left;
                top = shape.Top;
                width = shape.Width;
                height = shape.Height;
            }
            catch
            {
                return shape;
            }

            var htmlId = SafeGetTag(shape, TagHtmlIdKey);
            var htmlName = SafeGetTag(shape, TagHtmlNameKey);
            if (string.IsNullOrWhiteSpace(htmlId))
            {
                return shape;
            }

            var newShape = slide.Shapes.AddShape(MsoAutoShapeType.msoShapeRectangle, left, top, width, height);
            try
            {
                newShape.Name = shape.Name;
            }
            catch
            {
            }

            try
            {
                newShape.Tags.Add(TagTypeKey, TagTypeValue);
                newShape.Tags.Add(TagHtmlIdKey, htmlId);
                newShape.Tags.Add(TagHtmlNameKey, htmlName ?? "index.html");
                newShape.Tags.Add(TagRendererKey, TagRendererWebView2OverlayValue);
            }
            catch
            {
            }

            try
            {
                ApplyFrameChrome(newShape);
            }
            catch
            {
            }

            try
            {
                shape.Delete();
            }
            catch
            {
            }

            return newShape;
        }

        private sealed class HtmlOverlayController : IDisposable
        {
            private readonly PowerPoint.Application _app;
            private readonly Timer _refreshTimer;
            private SlideShowOverlays _slideShowOverlays;
            private EditModeOverlays _editModeOverlays;
            private bool _isEnsuring;
            private bool _isRefreshing;
            private DateTime _lastRefreshTime = DateTime.MinValue;
            private const int MinRefreshIntervalMs = 500;

            public HtmlOverlayController(PowerPoint.Application app)
            {
                _app = app;
                _app.SlideShowBegin += App_SlideShowBegin;
                _app.SlideShowNextSlide += App_SlideShowNextSlide;
                _app.SlideShowEnd += App_SlideShowEnd;
                _app.WindowActivate += App_WindowActivate;
                _app.WindowSelectionChange += App_WindowSelectionChange;
                _app.WindowDeactivate += App_WindowDeactivate;

                _refreshTimer = new Timer();
                _refreshTimer.Interval = RefreshIntervalMs;
                _refreshTimer.Tick += RefreshTimer_Tick;
                _refreshTimer.Start();

                RefreshCurrent();
            }

            private void App_SlideShowBegin(PowerPoint.SlideShowWindow Wn)
            {
                try
                {
                    RefreshCurrent();
                }
                catch (Exception ex)
                {
                    ThisAddIn.LogException("App_SlideShowBegin failed", ex);
                }
            }

            private void App_SlideShowNextSlide(PowerPoint.SlideShowWindow Wn)
            {
                try
                {
                    RefreshCurrent();
                }
                catch (Exception ex)
                {
                    ThisAddIn.LogException("App_SlideShowNextSlide failed", ex);
                }
            }

            private void App_SlideShowEnd(PowerPoint.Presentation Pres)
            {
                try
                {
                    RefreshCurrent();
                }
                catch (Exception ex)
                {
                    ThisAddIn.LogException("App_SlideShowEnd failed", ex);
                }
            }

            private void App_WindowActivate(PowerPoint.Presentation Pres, PowerPoint.DocumentWindow Wn)
            {
                try
                {
                    RefreshCurrent();
                }
                catch (Exception ex)
                {
                    ThisAddIn.LogException("App_WindowActivate failed", ex);
                }
            }

            private void App_WindowSelectionChange(PowerPoint.Selection Sel)
            {
                try
                {
                    RefreshCurrent();
                }
                catch (Exception ex)
                {
                    ThisAddIn.LogException("App_WindowSelectionChange failed", ex);
                }
            }

            private void App_WindowDeactivate(PowerPoint.Presentation Pres, PowerPoint.DocumentWindow Wn)
            {
                try
                {
                    CloseSlideShowOverlays();
                    CloseEditModeOverlays();
                }
                catch
                {
                }
            }

            private void RefreshTimer_Tick(object sender, EventArgs e)
            {
                try
                {
                    if (_isRefreshing)
                    {
                        return;
                    }

                    var timeSinceLastRefresh = (DateTime.Now - _lastRefreshTime).TotalMilliseconds;
                    if (timeSinceLastRefresh < MinRefreshIntervalMs)
                    {
                        return;
                    }

                    _isRefreshing = true;
                    _lastRefreshTime = DateTime.Now;
                    RefreshCurrent();
                }
                catch
                {
                }
                finally
                {
                    _isRefreshing = false;
                }
            }

            private PowerPoint.DocumentWindow SafeGetActiveWindow()
            {
                try
                {
                    return _app.ActiveWindow;
                }
                catch (COMException ex) when (ex.ErrorCode == unchecked((int)0x80048240))
                {
                    return null;
                }
                catch (Exception ex)
                {
                    ThisAddIn.LogException("SafeGetActiveWindow failed", ex);
                    return null;
                }
            }

            private PowerPoint.Presentation SafeGetActivePresentation()
            {
                try
                {
                    return _app.ActivePresentation;
                }
                catch
                {
                    return null;
                }
            }

            private void RefreshCurrent()
            {
                try
                {
                    if (_app.SlideShowWindows != null && _app.SlideShowWindows.Count > 0)
                    {
                        var ssWindow = _app.SlideShowWindows[1];
                        RefreshSlideShow(ssWindow);
                        return;
                    }
                }
                catch
                {
                }

                RefreshEditMode(SafeGetActiveWindow());
            }

            private void RefreshSlideShow(PowerPoint.SlideShowWindow window)
            {
                CloseEditModeOverlays();

                var slide = window?.View?.Slide;
                var pres = window?.Presentation;
                if (slide == null || pres == null)
                {
                    CloseSlideShowOverlays();
                    return;
                }

                EnsureOverlayFrames(slide);

                if (_slideShowOverlays == null)
                {
                    _slideShowOverlays = new SlideShowOverlays(TryGetHtmlBundle);
                }

                _slideShowOverlays.Show(window);
            }

            private void RefreshEditMode(PowerPoint.DocumentWindow window)
            {
                CloseSlideShowOverlays();

                if (!IsDocumentWindowUsable(window))
                {
                    CloseEditModeOverlays();
                    return;
                }

                var slide = GetWindowSlide(window);
                var pres = slide?.Parent as PowerPoint.Presentation;
                if (slide == null || pres == null)
                {
                    CloseEditModeOverlays();
                    return;
                }

                EnsureOverlayFrames(slide);

                if (_editModeOverlays == null)
                {
                    _editModeOverlays = new EditModeOverlays(TryGetHtmlBundle);
                }

                _editModeOverlays.Show(window);
            }

            private void CloseSlideShowOverlays()
            {
                if (_slideShowOverlays == null)
                {
                    return;
                }

                _slideShowOverlays.Dispose();
                _slideShowOverlays = null;
            }

            private void CloseEditModeOverlays()
            {
                if (_editModeOverlays == null)
                {
                    return;
                }

                _editModeOverlays.Dispose();
                _editModeOverlays = null;
            }

            private void EnsureOverlayFrames(PowerPoint.Slide slide)
            {
                if (_isEnsuring)
                {
                    return;
                }

                if (slide == null)
                {
                    return;
                }

                _isEnsuring = true;
                try
                {
                    var frames = GetHtmlFrameShapes(slide);
                    if (frames.Length == 0)
                    {
                        return;
                    }

                    foreach (var frame in frames.ToArray())
                    {
                        ApplyFrameChrome(frame);
                        var renderer = SafeGetTag(frame, TagRendererKey);
                        if (string.IsNullOrWhiteSpace(renderer) || string.Equals(renderer, TagRendererActiveXValue, StringComparison.OrdinalIgnoreCase))
                        {
                            EnsureOverlayFrame(slide, frame);
                            continue;
                        }

                        if (!string.Equals(renderer, TagRendererWebView2OverlayValue, StringComparison.OrdinalIgnoreCase))
                        {
                            try
                            {
                                frame.Tags.Add(TagRendererKey, TagRendererWebView2OverlayValue);
                            }
                            catch
                            {
                            }
                        }
                    }
                }
                finally
                {
                    _isEnsuring = false;
                }
            }

            public void Dispose()
            {
                _refreshTimer.Stop();
                _refreshTimer.Tick -= RefreshTimer_Tick;
                _refreshTimer.Dispose();
                CloseSlideShowOverlays();
                CloseEditModeOverlays();
                _app.SlideShowBegin -= App_SlideShowBegin;
                _app.SlideShowNextSlide -= App_SlideShowNextSlide;
                _app.SlideShowEnd -= App_SlideShowEnd;
                _app.WindowActivate -= App_WindowActivate;
                _app.WindowSelectionChange -= App_WindowSelectionChange;
                _app.WindowDeactivate -= App_WindowDeactivate;
            }
        }

        private sealed class SlideShowOverlays : IDisposable
        {
            private readonly Func<PowerPoint.Presentation, string, HtmlBundle> _loader;
            private HtmlOverlayItem[] _items = Array.Empty<HtmlOverlayItem>();
            private int _slideId;

            public SlideShowOverlays(Func<PowerPoint.Presentation, string, HtmlBundle> loader)
            {
                _loader = loader;
            }

            public void Show(PowerPoint.SlideShowWindow window)
            {
                var slide = window?.View?.Slide;
                var pres = window?.Presentation;
                if (slide == null || pres == null)
                {
                    Dispose();
                    return;
                }

                var frames = GetHtmlFrameShapes(slide)
                    .Where(shape => string.Equals(SafeGetTag(shape, TagRendererKey), TagRendererWebView2OverlayValue, StringComparison.OrdinalIgnoreCase))
                    .ToArray();
                if (frames.Length == 0)
                {
                    Dispose();
                    return;
                }

                var slideId = slide.SlideID;
                var frameIds = frames.Select(shape => SafeGetTag(shape, TagHtmlIdKey)).Where(id => !string.IsNullOrWhiteSpace(id)).ToArray();
                var needsRebuild = _slideId != slideId
                    || _items.Length != frameIds.Length
                    || !_items.Select(item => item.HtmlId).OrderBy(id => id).SequenceEqual(frameIds.OrderBy(id => id));

                if (needsRebuild)
                {
                    Dispose();
                    _slideId = slideId;
                    _items = frames.Select(shape =>
                    {
                        var htmlId = SafeGetTag(shape, TagHtmlIdKey);
                        var bundle = _loader(pres, htmlId);
                        if (bundle == null)
                        {
                            return null;
                        }

                        var htmlFile = ExtractBundleToTemp(htmlId, bundle);
                        if (string.IsNullOrWhiteSpace(htmlFile))
                        {
                            return null;
                        }

                        var rect = MapShapeToSlideShowRect(window, shape);
                        var form = new HtmlOverlayForm(htmlFile, rect, IntPtr.Zero, true, () => window.View.Next(), () => window.View.Previous(), () => window.View.Exit());
                        form.Show();
                        return new HtmlOverlayItem(htmlId, form);
                    }).Where(item => item != null).ToArray();
                }
                else
                {
                    foreach (var shape in frames)
                    {
                        var htmlId = SafeGetTag(shape, TagHtmlIdKey);
                        var item = _items.FirstOrDefault(current => string.Equals(current.HtmlId, htmlId, StringComparison.OrdinalIgnoreCase));
                        if (item != null)
                        {
                            item.Form.SetOverlayBounds(MapShapeToSlideShowRect(window, shape));
                        }
                    }
                }
            }

            public void Dispose()
            {
                foreach (var item in _items)
                {
                    try
                    {
                        item.Form.Dispose();
                    }
                    catch
                    {
                    }
                }

                _items = Array.Empty<HtmlOverlayItem>();
                _slideId = 0;
            }
        }

        private sealed class EditModeOverlays : IDisposable
        {
            private readonly Func<PowerPoint.Presentation, string, HtmlBundle> _loader;
            private HtmlOverlayItem[] _items = Array.Empty<HtmlOverlayItem>();
            private int _slideId;
            private IntPtr _windowHwnd = IntPtr.Zero;

            public EditModeOverlays(Func<PowerPoint.Presentation, string, HtmlBundle> loader)
            {
                _loader = loader;
            }

            public void Show(PowerPoint.DocumentWindow window)
            {
                if (!IsDocumentWindowUsable(window))
                {
                    Dispose();
                    return;
                }

                try
                {
                    var sel = window.Selection;
                    if (sel != null && sel.Type == PowerPoint.PpSelectionType.ppSelectionShapes)
                    {
                        var range = sel.ShapeRange;
                        if (range != null)
                        {
                            for (var i = 1; i <= range.Count; i++)
                            {
                                PowerPoint.Shape selected = null;
                                try { selected = range[i]; } catch { selected = null; }
                                if (selected == null)
                                {
                                    continue;
                                }

                                try
                                {
                                    if (string.Equals(selected.Tags[TagTypeKey], TagTypeValue, StringComparison.OrdinalIgnoreCase))
                                    {
                                        Dispose();
                                        return;
                                    }
                                }
                                catch
                                {
                                }
                            }
                        }
                    }
                }
                catch
                {
                }

                var slide = GetWindowSlide(window);
                var pres = slide?.Parent as PowerPoint.Presentation;
                if (slide == null || pres == null)
                {
                    Dispose();
                    return;
                }

                var frames = GetHtmlFrameShapes(slide)
                    .Where(shape => string.Equals(SafeGetTag(shape, TagRendererKey), TagRendererWebView2OverlayValue, StringComparison.OrdinalIgnoreCase))
                    .ToArray();
                if (frames.Length == 0)
                {
                    Dispose();
                    return;
                }

                var slideId = slide.SlideID;
                var frameIds = frames.Select(shape => SafeGetTag(shape, TagHtmlIdKey)).Where(id => !string.IsNullOrWhiteSpace(id)).ToArray();
                var hwnd = GetWindowHandle(window);
                var needsRebuild = _slideId != slideId
                    || _windowHwnd != hwnd
                    || _items.Length != frameIds.Length
                    || !_items.Select(item => item.HtmlId).OrderBy(id => id).SequenceEqual(frameIds.OrderBy(id => id));

                if (needsRebuild)
                {
                    Dispose();
                    _slideId = slideId;
                    _windowHwnd = hwnd;
                    _items = frames.Select(shape =>
                    {
                        var htmlId = SafeGetTag(shape, TagHtmlIdKey);
                        var bundle = _loader(pres, htmlId);
                        if (bundle == null)
                        {
                            return null;
                        }

                        var htmlFile = ExtractBundleToTemp(htmlId, bundle);
                        if (string.IsNullOrWhiteSpace(htmlFile))
                        {
                            return null;
                        }

                        ScreenRect rect;
                        if (!TryMapShapeToDocumentRect(window, shape, out rect))
                        {
                            return null;
                        }

                        var form = new HtmlOverlayForm(htmlFile, rect, hwnd, false, null, null, null);
                        form.Show();
                        return new HtmlOverlayItem(htmlId, form);
                    }).Where(item => item != null).ToArray();
                }
                else
                {
                    foreach (var shape in frames)
                    {
                        var htmlId = SafeGetTag(shape, TagHtmlIdKey);
                        var item = _items.FirstOrDefault(current => string.Equals(current.HtmlId, htmlId, StringComparison.OrdinalIgnoreCase));
                        if (item != null)
                        {
                            ScreenRect rect;
                            if (TryMapShapeToDocumentRect(window, shape, out rect))
                            {
                                item.Form.SetOverlayBounds(rect);
                            }
                        }
                    }
                }
            }

            public void Dispose()
            {
                foreach (var item in _items)
                {
                    try
                    {
                        item.Form.Dispose();
                    }
                    catch
                    {
                    }
                }

                _items = Array.Empty<HtmlOverlayItem>();
                _slideId = 0;
                _windowHwnd = IntPtr.Zero;
            }
        }

        private static PowerPoint.Shape[] GetHtmlFrameShapes(PowerPoint.Slide slide)
        {
            return slide.Shapes.Cast<PowerPoint.Shape>()
                .Where(shape =>
                {
                    try
                    {
                        return string.Equals(shape.Tags[TagTypeKey], TagTypeValue, StringComparison.OrdinalIgnoreCase);
                    }
                    catch
                    {
                        return false;
                    }
                })
                .ToArray();
        }

        private static string SafeGetTag(PowerPoint.Shape shape, string key)
        {
            try
            {
                return shape.Tags[key];
            }
            catch
            {
                return null;
            }
        }

        private static string ExtractBundleToTemp(string htmlId, HtmlBundle bundle)
        {
            if (bundle == null || bundle.Files.Length == 0)
            {
                return null;
            }

            var tempDir = Path.Combine(GetHtmlCacheRoot(), htmlId);
            Directory.CreateDirectory(tempDir);

            foreach (var file in bundle.Files)
            {
                var outputPath = Path.Combine(tempDir, file.Path);
                var outputDir = Path.GetDirectoryName(outputPath);
                if (!string.IsNullOrWhiteSpace(outputDir))
                {
                    Directory.CreateDirectory(outputDir);
                }

                File.WriteAllBytes(outputPath, file.Bytes);
            }

            return Path.Combine(tempDir, bundle.EntryPath);
        }

        private static PowerPoint.Slide GetWindowSlide(PowerPoint.DocumentWindow window)
        {
            try
            {
                if (window?.View == null)
                {
                    return null;
                }

                return window.View.Slide as PowerPoint.Slide;
            }
            catch
            {
                return null;
            }
        }

        private static bool IsDocumentWindowUsable(PowerPoint.DocumentWindow window)
        {
            if (window == null)
            {
                return false;
            }

            try
            {
                if (window.HWND == 0 || window.View == null)
                {
                    return false;
                }

                // PowerPoint can temporarily expose a document window that rejects pixel mapping.
                window.PointsToScreenPixelsX(0f);
                window.PointsToScreenPixelsY(0f);
                return true;
            }
            catch (COMException)
            {
                return false;
            }
            catch
            {
                return false;
            }
        }

        private static ScreenRect MapShapeToSlideShowRect(PowerPoint.SlideShowWindow window, PowerPoint.Shape shape)
        {
            var slideWidth = window.Presentation.PageSetup.SlideWidth;
            var slideHeight = window.Presentation.PageSetup.SlideHeight;

            var wnLeft = window.Left;
            var wnTop = window.Top;
            var wnWidth = window.Width;
            var wnHeight = window.Height;

            var scale = Math.Min(wnWidth / slideWidth, wnHeight / slideHeight);
            var viewWidth = slideWidth * scale;
            var viewHeight = slideHeight * scale;
            var viewLeft = wnLeft + (wnWidth - viewWidth) / 2;
            var viewTop = wnTop + (wnHeight - viewHeight) / 2;

            var x = viewLeft + shape.Left * scale;
            var y = viewTop + shape.Top * scale;
            var w = shape.Width * scale;
            var h = shape.Height * scale;

            using (var g = GraphicsProvider.GetGraphics())
            {
                var pxX = (int)Math.Round(x * g.DpiX / 72f);
                var pxY = (int)Math.Round(y * g.DpiY / 72f);
                var pxW = (int)Math.Round(w * g.DpiX / 72f);
                var pxH = (int)Math.Round(h * g.DpiY / 72f);
                return new ScreenRect(pxX, pxY, pxW, pxH);
            }
        }

        private static ScreenRect MapShapeToDocumentRect(PowerPoint.DocumentWindow window, PowerPoint.Shape shape)
        {
            var x1 = window.PointsToScreenPixelsX(shape.Left);
            var y1 = window.PointsToScreenPixelsY(shape.Top);
            var x2 = window.PointsToScreenPixelsX(shape.Left + shape.Width);
            var y2 = window.PointsToScreenPixelsY(shape.Top + shape.Height);
            return new ScreenRect(x1, y1, Math.Max(1, x2 - x1), Math.Max(1, y2 - y1));
        }

        private static bool TryMapShapeToDocumentRect(PowerPoint.DocumentWindow window, PowerPoint.Shape shape, out ScreenRect rect)
        {
            try
            {
                rect = MapShapeToDocumentRect(window, shape);
                return true;
            }
            catch (COMException)
            {
                rect = default(ScreenRect);
                return false;
            }
            catch
            {
                rect = default(ScreenRect);
                return false;
            }
        }

        private static IntPtr GetWindowHandle(PowerPoint.DocumentWindow window)
        {
            try
            {
                return new IntPtr(window.HWND);
            }
            catch
            {
                return IntPtr.Zero;
            }
        }

        private static IntPtr SetWindowLongPtr(IntPtr hWnd, int nIndex, IntPtr dwNewLong)
        {
            if (IntPtr.Size == 8)
            {
                return SetWindowLongPtr64(hWnd, nIndex, dwNewLong);
            }

            return new IntPtr(SetWindowLong32(hWnd, nIndex, dwNewLong.ToInt32()));
        }

        private static string GetAutoFitDocumentScript()
        {
            return @"(function () {
  if (window.__eduPlayAutoFitInstalled) {
    return;
  }

  window.__eduPlayAutoFitInstalled = true;
  var scheduled = false;

  function maxValue(values) {
    var result = 0;
    for (var i = 0; i < values.length; i++) {
      var current = values[i];
      if (current && current > result) {
        result = current;
      }
    }

    return Math.max(1, result);
  }

  function measureContent() {
    var docEl = document.documentElement;
    var body = document.body;
    if (!docEl || !body) {
      return {
        width: Math.max(1, window.innerWidth || 1),
        height: Math.max(1, window.innerHeight || 1)
      };
    }

    var previousBodyZoom = body.style.zoom;
    var previousDocZoom = docEl.style.zoom;
    body.style.zoom = '1';
    docEl.style.zoom = '1';

    var size = {
      width: maxValue([body.scrollWidth, body.offsetWidth, body.clientWidth, docEl.scrollWidth, docEl.offsetWidth, docEl.clientWidth]),
      height: maxValue([body.scrollHeight, body.offsetHeight, body.clientHeight, docEl.scrollHeight, docEl.offsetHeight, docEl.clientHeight])
    };

    body.style.zoom = previousBodyZoom;
    docEl.style.zoom = previousDocZoom;
    return size;
  }

  function applyFit() {
    scheduled = false;
    var docEl = document.documentElement;
    var body = document.body;
    if (!docEl || !body) {
      return;
    }

    var natural = measureContent();
    var viewportWidth = Math.max(window.innerWidth || 0, docEl.clientWidth || 0);
    var viewportHeight = Math.max(window.innerHeight || 0, docEl.clientHeight || 0);
    if (viewportWidth <= 0 || viewportHeight <= 0) {
      return;
    }

    var scale = Math.min(viewportWidth / natural.width, viewportHeight / natural.height);
    if (!isFinite(scale) || scale <= 0) {
      scale = 1;
    }

    docEl.style.overflow = 'hidden';
    body.style.zoom = scale.toFixed(4);
    body.style.transformOrigin = 'top left';
    body.style.margin = '0';
    body.style.marginLeft = Math.max(0, (viewportWidth - (natural.width * scale)) / 2) + 'px';
    body.style.marginTop = Math.max(0, (viewportHeight - (natural.height * scale)) / 2) + 'px';
  }

  function scheduleFit() {
    if (scheduled) {
      return;
    }

    scheduled = true;
    window.requestAnimationFrame(applyFit);
  }

  window.eduplayAutoFit = scheduleFit;
  window.addEventListener('load', scheduleFit);
  window.addEventListener('resize', scheduleFit);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scheduleFit, { once: true });
  } else {
    scheduleFit();
  }

  new MutationObserver(scheduleFit).observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true
  });
})();";
        }

        [DllImport("user32.dll", EntryPoint = "SetWindowLong", SetLastError = true)]
        private static extern int SetWindowLong32(IntPtr hWnd, int nIndex, int dwNewLong);

        [DllImport("user32.dll", EntryPoint = "SetWindowLongPtr", SetLastError = true)]
        private static extern IntPtr SetWindowLongPtr64(IntPtr hWnd, int nIndex, IntPtr dwNewLong);

        [DllImport("dwmapi.dll")]
        private static extern int DwmSetWindowAttribute(IntPtr hwnd, int dwAttribute, ref int pvAttribute, int cbAttribute);

        private sealed class HtmlOverlayForm : Form
        {
            private readonly string _htmlFile;
            private readonly IntPtr _ownerHwnd;
            private readonly bool _interactive;
            private readonly WebView2 _webView;
            private readonly Label _fallbackLabel;
            private readonly Action _nextAction;
            private readonly Action _previousAction;
            private readonly Action _escapeAction;
            private bool _disposeRequested;

            public HtmlOverlayForm(string htmlFile, ScreenRect rect, IntPtr ownerHwnd, bool interactive, Action nextAction, Action previousAction, Action escapeAction)
            {
                _htmlFile = htmlFile;
                _ownerHwnd = ownerHwnd;
                _interactive = interactive;
                _nextAction = nextAction;
                _previousAction = previousAction;
                _escapeAction = escapeAction;

                KeyPreview = interactive;
                FormBorderStyle = FormBorderStyle.None;
                ShowInTaskbar = false;
                StartPosition = FormStartPosition.Manual;
                TopMost = interactive;
                BackColor = System.Drawing.Color.White;
                Padding = Padding.Empty;

                _fallbackLabel = new Label
                {
                    Dock = DockStyle.Fill,
                    TextAlign = System.Drawing.ContentAlignment.MiddleCenter,
                    Text = "Khong khoi tao duoc WebView2.",
                    Visible = false
                };
                _fallbackLabel.BackColor = System.Drawing.Color.White;
                _fallbackLabel.Margin = Padding.Empty;

                _webView = new WebView2
                {
                    Dock = DockStyle.Fill,
                    Visible = false
                };
                _webView.Margin = Padding.Empty;

                Controls.Add(_fallbackLabel);
                Controls.Add(_webView);

                Load += HtmlOverlayForm_Load;
                SetOverlayBounds(rect);
            }

            protected override CreateParams CreateParams
            {
                get
                {
                    var cp = base.CreateParams;
                    cp.ExStyle |= 0x00000080;
                    if (!_interactive)
                    {
                        cp.ExStyle |= 0x00000020;
                        cp.ExStyle |= 0x08000000;
                    }
                    return cp;
                }
            }

            public void SetOverlayBounds(ScreenRect rect)
            {
                var x = rect.X;
                var y = rect.Y;
                var w = rect.Width;
                var h = rect.Height;

                if (!_interactive)
                {
                    x += EditOverlayInsetPixels;
                    y += EditOverlayInsetPixels;
                    w = Math.Max(1, w - (EditOverlayInsetPixels * 2));
                    h = Math.Max(1, h - (EditOverlayInsetPixels * 2));
                }

                var finalW = Math.Max(1, w - 1);
                var finalH = Math.Max(1, h - 1);
                Bounds = new System.Drawing.Rectangle(x, y, finalW, finalH);
                try
                {
                    Region = new System.Drawing.Region(new System.Drawing.Rectangle(0, 0, finalW, finalH));
                }
                catch
                {
                }
            }

            private async void HtmlOverlayForm_Load(object sender, EventArgs e)
            {
                TryAttachToOwner();
                TryDisableShadow();
                await InitializeBrowserAsync();
            }

            private void TryDisableShadow()
            {
                try
                {
                    var disabled = 1;
                    DwmSetWindowAttribute(Handle, 2, ref disabled, sizeof(int));
                }
                catch
                {
                }

                try
                {
                    var disableTransitions = 1;
                    DwmSetWindowAttribute(Handle, 3, ref disableTransitions, sizeof(int));
                }
                catch
                {
                }
            }

            private void TryAttachToOwner()
            {
                if (_ownerHwnd == IntPtr.Zero)
                {
                    return;
                }

                try
                {
                    SetWindowLongPtr(Handle, -8, _ownerHwnd);
                }
                catch
                {
                }
            }

            private async Task InitializeBrowserAsync()
            {
                if (_disposeRequested || IsDisposed || Disposing)
                {
                    return;
                }

                if (string.IsNullOrWhiteSpace(_htmlFile) || !File.Exists(_htmlFile))
                {
                    ShowFallback("Khong tim thay file HTML de mo.");
                    return;
                }

                if (!await WebView2Runtime.EnsureInstalledAsync())
                {
                    if (_disposeRequested || IsDisposed || Disposing)
                    {
                        return;
                    }

                    ShowFallback("Chua co WebView2 Runtime. Khong the hien thi HTML.");
                    return;
                }

                try
                {
                    if (_disposeRequested || IsDisposed || Disposing)
                    {
                        return;
                    }

                    if (_webView.CoreWebView2 == null)
                    {
                        string userDataFolder = null;
                        try
                        {
                            userDataFolder = Path.Combine(
                                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                                "EduPlayPowerPointAddin",
                                "WebView2UserData");
                            Directory.CreateDirectory(userDataFolder);
                        }
                        catch
                        {
                            userDataFolder = null;
                        }

                        CoreWebView2Environment env = null;
                        try
                        {
                            if (!string.IsNullOrWhiteSpace(userDataFolder))
                            {
                                env = await CoreWebView2Environment.CreateAsync(null, userDataFolder);
                            }
                        }
                        catch
                        {
                            env = null;
                        }

                        if (env == null)
                        {
                            try
                            {
                                var fallbackFolder = Path.Combine(Path.GetTempPath(), "EduPlayPowerPointAddin", "WebView2UserData");
                                Directory.CreateDirectory(fallbackFolder);
                                env = await CoreWebView2Environment.CreateAsync(null, fallbackFolder);
                            }
                            catch
                            {
                                env = null;
                            }
                        }

                        if (env != null)
                        {
                            await _webView.EnsureCoreWebView2Async(env);
                        }
                        else
                        {
                            await _webView.EnsureCoreWebView2Async();
                        }
                    }

                    if (_disposeRequested || IsDisposed || Disposing || _webView.CoreWebView2 == null)
                    {
                        return;
                    }

                    _webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
                    _webView.CoreWebView2.Settings.AreDevToolsEnabled = false;
                    _webView.CoreWebView2.Settings.IsStatusBarEnabled = false;
                    _webView.CoreWebView2.NavigationCompleted += CoreWebView2_NavigationCompleted;
                    if (_interactive)
                    {
                        _webView.CoreWebView2.WebMessageReceived += CoreWebView2_WebMessageReceived;
                        await _webView.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(@"
window.addEventListener('keydown', function (e) {
  var key = e.key || '';
  if (key === 'ArrowRight' || key === 'ArrowDown' || key === 'ArrowLeft' || key === 'ArrowUp' || key === 'Escape') {
    try {
      window.chrome.webview.postMessage(key);
      e.preventDefault();
      e.stopPropagation();
    } catch (err) {
    }
  }
}, true);");
                    }
                    await _webView.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(GetAutoFitDocumentScript());
                    _webView.Source = new Uri(_htmlFile);
                    _webView.Visible = true;
                    _fallbackLabel.Visible = false;
                }
                catch (COMException ex) when (ex.ErrorCode == unchecked((int)0x80004004) || _disposeRequested || IsDisposed || Disposing)
                {
                }
                catch (ObjectDisposedException)
                {
                }
                catch (Exception ex)
                {
                    ThisAddIn.LogException("WebView2 initialization failed", ex);
                    ShowFallback("Khong khoi tao duoc WebView2. Hay cai WebView2 Runtime.");
                }
            }

            private async void CoreWebView2_NavigationCompleted(object sender, CoreWebView2NavigationCompletedEventArgs e)
            {
                if (!e.IsSuccess || _webView.CoreWebView2 == null)
                {
                    return;
                }

                try
                {
                    await _webView.CoreWebView2.ExecuteScriptAsync(
                        "window.eduplayAutoFit && window.eduplayAutoFit();");
                }
                catch
                {
                }
            }

            private void CoreWebView2_WebMessageReceived(object sender, CoreWebView2WebMessageReceivedEventArgs e)
            {
                var key = e.TryGetWebMessageAsString();

                if (string.Equals(key, "ArrowRight", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(key, "ArrowDown", StringComparison.OrdinalIgnoreCase))
                {
                    InvokeAction(_nextAction);
                    return;
                }

                if (string.Equals(key, "ArrowLeft", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(key, "ArrowUp", StringComparison.OrdinalIgnoreCase))
                {
                    InvokeAction(_previousAction);
                    return;
                }

                if (string.Equals(key, "Escape", StringComparison.OrdinalIgnoreCase))
                {
                    InvokeAction(_escapeAction);
                }
            }

            private void InvokeAction(Action action)
            {
                if (action == null)
                {
                    return;
                }

                try
                {
                    action();
                }
                catch
                {
                }
            }

            private void ShowFallback(string message)
            {
                if (_disposeRequested || IsDisposed || Disposing)
                {
                    return;
                }

                _webView.Visible = false;
                _fallbackLabel.Text = message;
                _fallbackLabel.Visible = true;
            }

            protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
            {
                if (keyData == Keys.Right || keyData == Keys.Down)
                {
                    InvokeAction(_nextAction);
                    return _nextAction != null || base.ProcessCmdKey(ref msg, keyData);
                }

                if (keyData == Keys.Left || keyData == Keys.Up)
                {
                    InvokeAction(_previousAction);
                    return _previousAction != null || base.ProcessCmdKey(ref msg, keyData);
                }

                if (keyData == Keys.Escape)
                {
                    InvokeAction(_escapeAction);
                    return _escapeAction != null || base.ProcessCmdKey(ref msg, keyData);
                }

                return base.ProcessCmdKey(ref msg, keyData);
            }

            protected override void Dispose(bool disposing)
            {
                _disposeRequested = true;
                if (disposing)
                {
                    try
                    {
                        if (_webView.CoreWebView2 != null)
                        {
                            _webView.CoreWebView2.NavigationCompleted -= CoreWebView2_NavigationCompleted;
                            if (_interactive)
                            {
                                _webView.CoreWebView2.WebMessageReceived -= CoreWebView2_WebMessageReceived;
                            }
                        }
                    }
                    catch
                    {
                    }

                    _webView.Dispose();
                    _fallbackLabel.Dispose();
                }

                base.Dispose(disposing);
            }
        }

        private sealed class HtmlOverlayItem
        {
            public string HtmlId { get; }
            public HtmlOverlayForm Form { get; }

            public HtmlOverlayItem(string htmlId, HtmlOverlayForm form)
            {
                HtmlId = htmlId;
                Form = form;
            }
        }

        private sealed class HtmlBundle
        {
            public string EntryPath { get; }
            public HtmlBundleFile[] Files { get; }

            public HtmlBundle(string entryPath, HtmlBundleFile[] files)
            {
                EntryPath = entryPath;
                Files = files ?? Array.Empty<HtmlBundleFile>();
            }
        }

        private sealed class HtmlBundleFile
        {
            public string Path { get; }
            public byte[] Bytes { get; }

            public HtmlBundleFile(string path, byte[] bytes)
            {
                Path = path;
                Bytes = bytes ?? Array.Empty<byte>();
            }
        }

        private readonly struct ScreenRect
        {
            public int X { get; }
            public int Y { get; }
            public int Width { get; }
            public int Height { get; }

            public ScreenRect(int x, int y, int width, int height)
            {
                X = x;
                Y = y;
                Width = width;
                Height = height;
            }
        }

        private static class GraphicsProvider
        {
            public static System.Drawing.Graphics GetGraphics()
            {
                return System.Drawing.Graphics.FromHwnd(IntPtr.Zero);
            }
        }
    }
}
