using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace EduPlay.PowerPointAddin;

internal sealed class OverlayForm : Form
{
    private readonly WebView2 _webView;
    private IntPtr _pptHwnd;

    public OverlayForm()
    {
        KeyPreview = true;
        FormBorderStyle = FormBorderStyle.None;
        ShowInTaskbar = false;
        StartPosition = FormStartPosition.Manual;
        TopMost = true;

        _webView = new WebView2
        {
            Dock = DockStyle.Fill
        };
        Controls.Add(_webView);

        KeyDown += OnKeyDown;
    }

    public void SetPowerPointWindowHandle(IntPtr hwnd)
    {
        _pptHwnd = hwnd;
    }

    public async void NavigateToFile(string filePath)
    {
        if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
        {
            return;
        }

        try
        {
            if (_webView.CoreWebView2 == null)
            {
                await _webView.EnsureCoreWebView2Async();
            }
        }
        catch
        {
            return;
        }

        try
        {
            var uri = new Uri(filePath).AbsoluteUri;
            _webView.CoreWebView2.Navigate(uri);
        }
        catch
        {
        }
    }

    public void SetBoundsPx(Rectangle rect)
    {
        if (rect.Width <= 0 || rect.Height <= 0)
        {
            Hide();
            return;
        }
        Bounds = rect;
    }

    private void OnKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.KeyCode == Keys.Escape)
        {
            try
            {
                e.Handled = true;
                e.SuppressKeyPress = true;
            }
            catch
            {
            }
            Hide();
            try
            {
                if (_pptHwnd != IntPtr.Zero)
                {
                    NativeMethods.SetForegroundWindow(_pptHwnd);
                }
            }
            catch
            {
            }
        }
    }
}

