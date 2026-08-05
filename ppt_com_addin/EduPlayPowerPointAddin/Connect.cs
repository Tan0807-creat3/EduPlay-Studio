using System;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;
using Extensibility;
using Microsoft.Office.Core;
using PowerPoint = Microsoft.Office.Interop.PowerPoint;

namespace EduPlay.PowerPointAddin;

[ComVisible(true)]
[Guid("8C9A52B6-DBA7-4E68-AE70-2E5A6B6F38E0")]
[ProgId("EduPlay.PowerPointAddin.Connect")]
public sealed class Connect : IDTExtensibility2, IRibbonExtensibility
{
    private PowerPoint.Application? _app;
    private OverlayForm? _overlay;
    private IRibbonUI? _ribbon;

    public void OnConnection(object Application, ext_ConnectMode ConnectMode, object AddInInst, ref Array custom)
    {
        _app = Application as PowerPoint.Application;
        TryWireEvents();
    }

    public void OnDisconnection(ext_DisconnectMode RemoveMode, ref Array custom)
    {
        try { _overlay?.Hide(); } catch { }
        try { _overlay?.Dispose(); } catch { }
        _overlay = null;
        _ribbon = null;
        _app = null;
    }

    public void OnAddInsUpdate(ref Array custom)
    {
    }

    public void OnStartupComplete(ref Array custom)
    {
    }

    public void OnBeginShutdown(ref Array custom)
    {
    }

    public string GetCustomUI(string RibbonID)
    {
        return LoadEmbeddedText("EduPlay.PowerPointAddin.Ribbon.xml");
    }

    public void OnRibbonLoad(IRibbonUI ribbonUI)
    {
        _ribbon = ribbonUI;
    }

    public stdole.IPictureDisp GetImportImage(IRibbonControl control)
    {
        try
        {
            using var s = Assembly.GetExecutingAssembly().GetManifestResourceStream("EduPlay.PowerPointAddin.Resources.file-import.ico");
            if (s == null) return null!;
            using var ico = new Icon(s);
            using var bmp = ico.ToBitmap();
            return ImageToPictureDisp(bmp);
        }
        catch
        {
            return null!;
        }
    }

    public void OnImportEduPlay(IRibbonControl control)
    {
        try
        {
            if (_app == null) return;
            var pres = _app.ActivePresentation;
            var slide = GetCurrentSlide();
            if (pres == null || slide == null) return;

            using var dlg = new OpenFileDialog
            {
                Filter = "HTML Files (*.html;*.htm)|*.html;*.htm|All Files (*.*)|*.*",
                Title = "Import EduPlay HTML"
            };
            var ok = dlg.ShowDialog() == DialogResult.OK;
            if (!ok) return;

            var html = File.ReadAllText(dlg.FileName, Encoding.UTF8);
            if (string.IsNullOrWhiteSpace(html)) return;

            var storage = new EduPlayStorage(pres);
            storage.SaveSlideHtml(slide.SlideID, html);
            EnsurePlaceholderShape(slide);
        }
        catch
        {
        }
    }

    public void OnOpenPanel(IRibbonControl control)
    {
        try
        {
            MessageBox.Show("EduPlay Panel (đang triển khai).", "EduPlay", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch
        {
        }
    }

    private void TryWireEvents()
    {
        try
        {
            if (_app == null) return;
            _app.SlideShowBegin += OnSlideShowBegin;
            _app.SlideShowNextSlide += OnSlideShowNextSlide;
            _app.SlideShowEnd += OnSlideShowEnd;
        }
        catch
        {
        }
    }

    private void OnSlideShowBegin(PowerPoint.SlideShowWindow Wn)
    {
        TryShowForCurrentSlide(Wn);
    }

    private void OnSlideShowNextSlide(PowerPoint.SlideShowWindow Wn)
    {
        TryShowForCurrentSlide(Wn);
    }

    private void OnSlideShowEnd(PowerPoint.Presentation Pres)
    {
        try { _overlay?.Hide(); } catch { }
    }

    private void TryShowForCurrentSlide(PowerPoint.SlideShowWindow wn)
    {
        try
        {
            if (_app == null) return;
            var pres = wn.Presentation;
            var slide = wn.View?.Slide;
            if (pres == null || slide == null) return;

            var storage = new EduPlayStorage(pres);
            if (!storage.HasSlideData(slide.SlideID))
            {
                _overlay?.Hide();
                return;
            }

            var file = storage.MaterializeTempFile(slide.SlideID);
            if (string.IsNullOrWhiteSpace(file))
            {
                _overlay?.Hide();
                return;
            }

            var rect = ComputeOverlayRect(wn, slide);
            if (rect.Width <= 0 || rect.Height <= 0)
            {
                _overlay?.Hide();
                return;
            }

            if (_overlay == null || _overlay.IsDisposed)
            {
                _overlay = new OverlayForm();
            }

            try
            {
                var hwnd = new IntPtr(wn.HWND);
                _overlay.SetPowerPointWindowHandle(hwnd);
            }
            catch
            {
            }

            _overlay.SetBoundsPx(rect);
            if (!_overlay.Visible) _overlay.Show();
            _overlay.NavigateToFile(file);
            _overlay.Activate();
        }
        catch
        {
        }
    }

    private static Rectangle ComputeOverlayRect(PowerPoint.SlideShowWindow wn, PowerPoint.Slide slide)
    {
        var left = (int)Math.Round((double)wn.Left);
        var top = (int)Math.Round((double)wn.Top);
        var width = (int)Math.Round((double)wn.Width);
        var height = (int)Math.Round((double)wn.Height);
        if (width <= 0 || height <= 0) return Rectangle.Empty;

        var slideW = 0.0;
        var slideH = 0.0;
        try
        {
            slideW = (double)wn.Presentation.PageSetup.SlideWidth;
            slideH = (double)wn.Presentation.PageSetup.SlideHeight;
        }
        catch
        {
            slideW = 0;
            slideH = 0;
        }

        var shape = FindPlaceholderShape(slide);
        if (shape == null || slideW <= 0 || slideH <= 0)
        {
            return new Rectangle(left, top, width, height);
        }

        var sx = (double)shape.Left;
        var sy = (double)shape.Top;
        var sw = (double)shape.Width;
        var sh = (double)shape.Height;

        var px = left + (int)Math.Round((sx / slideW) * width);
        var py = top + (int)Math.Round((sy / slideH) * height);
        var pw = (int)Math.Round((sw / slideW) * width);
        var ph = (int)Math.Round((sh / slideH) * height);

        return new Rectangle(px, py, Math.Max(1, pw), Math.Max(1, ph));
    }

    private static PowerPoint.Shape? FindPlaceholderShape(PowerPoint.Slide slide)
    {
        try
        {
            foreach (PowerPoint.Shape s in slide.Shapes)
            {
                try
                {
                    if (string.Equals(s.Tags["EduPlay"], "1", StringComparison.OrdinalIgnoreCase))
                    {
                        return s;
                    }
                }
                catch
                {
                }
            }
        }
        catch
        {
        }
        return null;
    }

    private static void EnsurePlaceholderShape(PowerPoint.Slide slide)
    {
        try
        {
            if (FindPlaceholderShape(slide) != null) return;
            var w = 960.0;
            var h = 540.0;
            try
            {
                if (slide.Parent is PowerPoint.Slides slides && slides.Parent is PowerPoint.Presentation pres)
                {
                    w = (double)pres.PageSetup.SlideWidth;
                    h = (double)pres.PageSetup.SlideHeight;
                }
            }
            catch
            {
            }
            var margin = 40.0;
            var shape = slide.Shapes.AddShape(
                Microsoft.Office.Core.MsoAutoShapeType.msoShapeRoundedRectangle,
                (float)margin,
                (float)margin,
                (float)Math.Max(200.0, w - (margin * 2)),
                (float)Math.Max(120.0, h - (margin * 2))
            );
            shape.TextFrame.TextRange.Text = "EduPlay Viewer";
            shape.TextFrame.TextRange.Font.Size = 24;
            shape.TextFrame.TextRange.Font.Bold = Microsoft.Office.Core.MsoTriState.msoTrue;
            shape.Fill.ForeColor.RGB = ColorTranslator.ToOle(Color.FromArgb(239, 246, 255));
            shape.Line.ForeColor.RGB = ColorTranslator.ToOle(Color.FromArgb(37, 99, 235));
            shape.Tags.Add("EduPlay", "1");
        }
        catch
        {
        }
    }

    private PowerPoint.Slide? GetCurrentSlide()
    {
        try
        {
            if (_app == null) return null;
            var view = _app.ActiveWindow?.View;
            if (view == null) return null;
            return view.Slide as PowerPoint.Slide;
        }
        catch
        {
            return null;
        }
    }

    private static string LoadEmbeddedText(string name)
    {
        try
        {
            using var s = Assembly.GetExecutingAssembly().GetManifestResourceStream(name);
            if (s == null) return "";
            using var r = new StreamReader(s, Encoding.UTF8);
            return r.ReadToEnd();
        }
        catch
        {
            return "";
        }
    }

    private static stdole.IPictureDisp ImageToPictureDisp(Image image)
    {
        return (stdole.IPictureDisp)AxHostShim.ImageToPictureDisp(image);
    }

    private sealed class AxHostShim : AxHost
    {
        private AxHostShim() : base("") { }
        public static object ImageToPictureDisp(Image image)
        {
            return GetIPictureDispFromPicture(image);
        }
    }
}
