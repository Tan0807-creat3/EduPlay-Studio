using System;
using System.Runtime.InteropServices;

namespace Extensibility;

[ComVisible(true)]
[Guid("B65AD801-ABAF-11D0-BB8B-00A0C90F2744")]
[InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IDTExtensibility2
{
    void OnConnection([In, MarshalAs(UnmanagedType.IDispatch)] object Application, ext_ConnectMode ConnectMode, [In, MarshalAs(UnmanagedType.IDispatch)] object AddInInst, ref Array custom);
    void OnDisconnection(ext_DisconnectMode RemoveMode, ref Array custom);
    void OnAddInsUpdate(ref Array custom);
    void OnStartupComplete(ref Array custom);
    void OnBeginShutdown(ref Array custom);
}

public enum ext_ConnectMode
{
    ext_cm_AfterStartup = 0,
    ext_cm_Startup = 1,
    ext_cm_External = 2,
    ext_cm_CommandLine = 3
}

public enum ext_DisconnectMode
{
    ext_dm_HostShutdown = 0,
    ext_dm_UserClosed = 1
}

