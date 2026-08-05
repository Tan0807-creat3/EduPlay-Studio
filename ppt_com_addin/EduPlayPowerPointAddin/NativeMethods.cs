using System;
using System.Runtime.InteropServices;

namespace EduPlay.PowerPointAddin;

internal static class NativeMethods
{
    [DllImport("user32.dll")]
    internal static extern bool SetForegroundWindow(IntPtr hWnd);
}

