using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Office = Microsoft.Office.Core;

namespace EduPlay.PowerPointAddin
{
    [ComVisible(true)]
    public class Ribbon : Office.IRibbonExtensibility
    {
        private Office.IRibbonUI _ribbon;

        public string GetCustomUI(string ribbonID)
        {
            var asm = Assembly.GetExecutingAssembly();
            using (var stream = asm.GetManifestResourceStream("EduPlay.PowerPointAddin.Ribbon.xml"))
            {
                if (stream == null)
                {
                    return "";
                }
                using (var reader = new StreamReader(stream))
                {
                    return reader.ReadToEnd();
                }
            }
        }

        public void OnLoad(Office.IRibbonUI ribbonUI)
        {
            _ribbon = ribbonUI;
        }

        public void OnOpenClicked(Office.IRibbonControl control)
        {
            try
            {
                using (var dialog = new OpenFileDialog())
                {
                    dialog.Title = "Chọn file HTML";
                    dialog.Filter = "HTML files (*.html;*.htm)|*.html;*.htm|All files (*.*)|*.*";
                    dialog.Multiselect = false;

                    if (dialog.ShowDialog() != DialogResult.OK)
                    {
                        return;
                    }

                    EduPlayHtmlFrames.ImportHtmlToCurrentSlide(dialog.FileName);
                }
            }
            catch (Exception ex)
            {
                ThisAddIn.LogException("OnOpenClicked failed", ex);
                MessageBox.Show(ex.Message, "EduPlay");
            }
        }

        public object GetOpenIcon(Office.IRibbonControl control)
        {
            return RibbonImageHelper.LoadIcoResourceAsPictureDisp(
                "EduPlay.PowerPointAddin.Resources.file-import.ico");
        }

        private class RibbonImageHelper : AxHost
        {
            private RibbonImageHelper()
                : base("")
            {
            }

            public static object LoadIcoResourceAsPictureDisp(string resourceName)
            {
                if (string.IsNullOrWhiteSpace(resourceName))
                {
                    return null;
                }

                try
                {
                    var asm = Assembly.GetExecutingAssembly();
                    using (var stream = asm.GetManifestResourceStream(resourceName))
                    {
                        if (stream == null)
                        {
                            return null;
                        }

                        using (var icon = new System.Drawing.Icon(stream))
                        {
                            var bitmap = icon.ToBitmap();
                            return GetIPictureDispFromPicture(bitmap);
                        }
                    }
                }
                catch
                {
                    return null;
                }
            }

            public static object LoadIcoAsPictureDisp(string icoPath)
            {
                if (string.IsNullOrWhiteSpace(icoPath) || !File.Exists(icoPath))
                {
                    return null;
                }

                using (var icon = new System.Drawing.Icon(icoPath))
                {
                    var bitmap = icon.ToBitmap();
                    return GetIPictureDispFromPicture(bitmap);
                }
            }
        }
    }
}
