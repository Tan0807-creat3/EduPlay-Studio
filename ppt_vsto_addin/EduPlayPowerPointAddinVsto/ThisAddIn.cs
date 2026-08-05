using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows.Forms;
using Office = Microsoft.Office.Core;

namespace EduPlay.PowerPointAddin
{
    public partial class ThisAddIn
    {
        private static readonly string LogDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "EduPlayPowerPointAddin",
            "Logs");

        private static readonly string LogFilePath = Path.Combine(LogDirectory, "addin.log");

        private void ThisAddIn_Startup(object sender, EventArgs e)
        {
            try
            {
                Directory.CreateDirectory(LogDirectory);

                AppDomain.CurrentDomain.UnhandledException += CurrentDomain_UnhandledException;
                System.Windows.Forms.Application.ThreadException += Application_ThreadException;

                Log("Startup begin.");
                Log("PowerPoint version: " + (this.Application?.Version ?? "unknown"));
                EduPlayHtmlFrames.Initialize(this.Application);
                Log("Startup completed successfully.");
            }
            catch (Exception ex)
            {
                LogException("Startup failed", ex);
                throw;
            }
        }

        private void ThisAddIn_Shutdown(object sender, EventArgs e)
        {
            Log("Shutdown.");
            EduPlayHtmlFrames.Shutdown();
            AppDomain.CurrentDomain.UnhandledException -= CurrentDomain_UnhandledException;
            System.Windows.Forms.Application.ThreadException -= Application_ThreadException;
        }

        protected override Office.IRibbonExtensibility CreateRibbonExtensibilityObject()
        {
            try
            {
                Log("Creating ribbon extensibility object.");
                return new Ribbon();
            }
            catch (Exception ex)
            {
                LogException("Failed to create ribbon extensibility object", ex);
                throw;
            }
        }

        private static void CurrentDomain_UnhandledException(object sender, UnhandledExceptionEventArgs e)
        {
            LogException("Unhandled AppDomain exception", e.ExceptionObject as Exception);
        }

        private static void Application_ThreadException(object sender, ThreadExceptionEventArgs e)
        {
            LogException("Unhandled UI thread exception", e.Exception);
        }

        internal static void Log(string message)
        {
            try
            {
                Directory.CreateDirectory(LogDirectory);
                File.AppendAllText(
                    LogFilePath,
                    $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff}] {message}{Environment.NewLine}",
                    Encoding.UTF8);
            }
            catch
            {
                // Avoid throwing from logging during Office startup.
            }
        }

        internal static void LogException(string context, Exception ex)
        {
            if (ex == null)
            {
                Log(context + ": <no exception details>");
                return;
            }

            Log(context + Environment.NewLine + ex);
        }

        #region VSTO generated code
        private void InternalStartup()
        {
            this.Startup += new EventHandler(ThisAddIn_Startup);
            this.Shutdown += new EventHandler(ThisAddIn_Shutdown);
        }
        #endregion
    }
}
