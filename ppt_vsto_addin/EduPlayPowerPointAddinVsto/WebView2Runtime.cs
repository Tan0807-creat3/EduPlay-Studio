using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading.Tasks;
using Microsoft.Web.WebView2.Core;

namespace EduPlay.PowerPointAddin
{
    internal static class WebView2Runtime
    {
        private const string BootstrapperLink = "https://go.microsoft.com/fwlink/p/?LinkId=2124703";
        private static Task<bool> _ensureTask;

        internal static void Warmup()
        {
            try
            {
                _ = EnsureInstalledAsync();
            }
            catch
            {
            }
        }

        internal static Task<bool> EnsureInstalledAsync()
        {
            if (_ensureTask != null)
            {
                return _ensureTask;
            }

            _ensureTask = EnsureInstalledCoreAsync();
            return _ensureTask;
        }

        private static async Task<bool> EnsureInstalledCoreAsync()
        {
            if (IsRuntimeAvailable())
            {
                return true;
            }

            var installerPath = await GetBootstrapperPathAsync();
            if (string.IsNullOrWhiteSpace(installerPath) || !File.Exists(installerPath))
            {
                return false;
            }

            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = installerPath,
                    Arguments = "/silent /install",
                    UseShellExecute = true,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                ThisAddIn.LogException("WebView2 bootstrapper start failed", ex);
                return false;
            }

            var deadline = DateTime.UtcNow.AddMinutes(3);
            while (DateTime.UtcNow < deadline)
            {
                if (IsRuntimeAvailable())
                {
                    return true;
                }

                await Task.Delay(1000);
            }

            return IsRuntimeAvailable();
        }

        internal static bool IsRuntimeAvailable()
        {
            try
            {
                var v = CoreWebView2Environment.GetAvailableBrowserVersionString();
                return !string.IsNullOrWhiteSpace(v);
            }
            catch
            {
                return false;
            }
        }

        private static async Task<string> GetBootstrapperPathAsync()
        {
            var baseDir = AppDomain.CurrentDomain.BaseDirectory;
            var packagedPath = Path.Combine(baseDir, "MicrosoftEdgeWebView2Bootstrapper.exe");
            if (File.Exists(packagedPath))
            {
                return packagedPath;
            }

            var tempDir = Path.Combine(Path.GetTempPath(), "EduPlayPowerPointAddin", "WebView2");
            Directory.CreateDirectory(tempDir);
            var tempPath = Path.Combine(tempDir, "MicrosoftEdgeWebView2Bootstrapper.exe");
            if (File.Exists(tempPath))
            {
                return tempPath;
            }

            try
            {
                ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
            }
            catch
            {
            }

            try
            {
                using (var wc = new WebClient())
                {
                    await wc.DownloadFileTaskAsync(new Uri(BootstrapperLink), tempPath);
                }
            }
            catch (Exception ex)
            {
                ThisAddIn.LogException("WebView2 bootstrapper download failed", ex);
                return null;
            }

            return File.Exists(tempPath) ? tempPath : null;
        }
    }
}

