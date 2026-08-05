; =========================================
; EduPlay PowerPoint COM Add-in – Inno Setup Script (x64)
; =========================================

#define AddinName "EduPlay PowerPoint COM Add-in"
#define AddinVersion "1.0.0"
#define AddinId "{{EDUPLAY-PPT-COM-ADDIN}}"
#define RepoRoot SourcePath
#define BuildDir RepoRoot + "EduPlayPowerPointAddin\\bin\\Release\\net48"
#define OutputDir RepoRoot + "..\\installer"

[Setup]
AppId={#AddinId}
AppName={#AddinName}
AppVersion={#AddinVersion}
DefaultDirName={userappdata}\EduPlay\PowerPointComAddin
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
OutputDir={#OutputDir}
OutputBaseFilename=EduPlay-PowerPointComAddin-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin.Connect"; ValueType: string; ValueName: "FriendlyName"; ValueData: "EduPlay"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin.Connect"; ValueType: string; ValueName: "Description"; ValueData: "EduPlay PowerPoint Add-in"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin.Connect"; ValueType: dword; ValueName: "LoadBehavior"; ValueData: "3"; Flags: uninsdeletevalue

[Run]
Filename: "{win}\Microsoft.NET\Framework64\v4.0.30319\regasm.exe"; Parameters: """{app}\EduPlayPowerPointAddin.dll"" /codebase"; Flags: runhidden waituntilterminated
