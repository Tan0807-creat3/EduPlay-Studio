; =========================================
; EduPlay Studio – Professional Installer
; Version: 1.0.0
; =========================================

#define AppName "EduPlay Studio"
#define AppVersion "1.0.0"
#define AppPublisher "EduPlay Studio"
#define AppExeName "EduPlayStudio.exe"
#define AppId "{{EDUPLAY-STUDIO-APP-2026}}"
#define AppURL "https://eduplay-game.web.app"
#define SupportURL "https://eduplay-game.web.app/support"
#define UpdateURL "https://eduplay-game.web.app/download"

#define RepoRoot SourcePath
#define BuildDir RepoRoot + "eduplay_studio\dist\EduPlayStudio"
#define AppIcon RepoRoot + "eduplay_studio\eduplay\resources\icons\icon.ico"
#define OutputDir RepoRoot + "installer"
#define VstoMsiPath RepoRoot + "eduplay_studio\eduplay\resources\vsto_addin\EduPlayPowerPointAddin.msi"
 

[Setup]
; App Identity
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#SupportURL}
AppUpdatesURL={#UpdateURL}
AppContact=eduplay.line@hotmail.com
AppComments=Educational game creation platform
AppCopyright=Copyright (C) 2026 {#AppPublisher}

; Install Directories
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallFilesDir={app}\uninstall

; Wizard Configuration
DisableProgramGroupPage=yes
DisableDirPage=no
DisableFinishedPage=no
DisableReadyPage=no
DisableWelcomePage=no
ShowLanguageDialog=auto
WizardStyle=modern
WizardSizePercent=120,100
WizardResizable=yes

; UI Configuration
SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}

; Output Configuration
OutputDir={#OutputDir}
OutputBaseFilename=EduPlay-Studio-v{#AppVersion}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
CompressionThreads=auto
InternalCompressLevel=ultra64
LZMANumBlockThreads=2
LZMADictionarySize=1048576
LZMAUseSeparateProcess=yes

; Version Info
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
VersionInfoCopyright=Copyright (C) 2026 {#AppPublisher}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

; Privileges & Architecture
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

; Installation Behavior
AllowNoIcons=yes
ChangesEnvironment=yes
ChangesAssociations=yes
CloseApplications=force
RestartApplications=no
RestartIfNeededByRun=no
AllowCancelDuringInstall=yes
CreateUninstallRegKey=yes
UpdateUninstallLogAppName=yes

; Previous Install Detection
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
UsePreviousLanguage=yes
UsePreviousSetupType=yes
AppMutex=EduPlayStudioSingleInstance

; Logging
SetupLogging=yes
AlwaysShowComponentsList=no
ShowComponentSizes=yes
FlatComponentsList=no 

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "vietnamese"; MessagesFile: "compiler:Languages\Vietnamese.isl"

[CustomMessages]
; English Messages
english.AdditionalTasks=Additional options:
english.DesktopIcon=Create &desktop shortcut
english.QuickLaunchIcon=Create Quick Launch shortcut
english.FileAssoc=Register .eduplay file association
english.AddToPath=Add application directory to PATH
english.FirewallException=Add Windows Firewall exception
english.CleanInstallPrompt=A previous installation was detected. Do you want to perform a clean installation?%n%nClean Install: Removes all previous data and settings%nUpgrade: Keeps your projects and settings%n%nRecommended: Upgrade
english.UninstallCleanupPrompt=Do you want to completely remove all application data?%n%nThis includes:%n• All projects in Documents\EduPlay%n• Application settings and cache%n• File associations and registry entries%n%nDefault: Keep user data (No)
english.RemoveAppData=Remove application data and settings
english.RemoveProjects=Remove all projects in Documents\EduPlay
english.UninstallingOld=Uninstalling previous version...
english.ClosingApp=Closing running application...
english.LaunchApp=Launch {#AppName}

; Vietnamese Messages
vietnamese.AdditionalTasks=Tùy chọn bổ sung:
vietnamese.DesktopIcon=Tạo biểu tượng trên &Desktop
vietnamese.QuickLaunchIcon=Tạo biểu tượng Quick Launch
vietnamese.FileAssoc=Đăng ký định dạng file .eduplay
vietnamese.AddToPath=Thêm thư mục ứng dụng vào PATH
vietnamese.FirewallException=Thêm ngoại lệ Windows Firewall
vietnamese.CleanInstallPrompt=Phát hiện phiên bản cũ. Bạn muốn cài đặt sạch hay nâng cấp?%n%nCài đặt sạch: Xóa toàn bộ dữ liệu và cài đặt cũ%nNâng cấp: Giữ nguyên dự án và cài đặt%n%nKhuyên dùng: Nâng cấp
vietnamese.UninstallCleanupPrompt=Bạn có muốn xóa hoàn toàn dữ liệu ứng dụng?%n%nBao gồm:%n• Tất cả dự án trong Documents\EduPlay%n• Cài đặt và cache ứng dụng%n• File associations và registry%n%nMặc định: Giữ dữ liệu người dùng (Không)
vietnamese.RemoveAppData=Xóa dữ liệu và cài đặt ứng dụng
vietnamese.RemoveProjects=Xóa tất cả dự án trong Documents\EduPlay
vietnamese.UninstallingOld=Đang gỡ phiên bản cũ...
vietnamese.ClosingApp=Đang đóng ứng dụng...
vietnamese.LaunchApp=Khởi chạy {#AppName}

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "{cm:QuickLaunchIcon}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "fileassoc"; Description: "{cm:FileAssoc}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: unchecked
Name: "addtopath"; Description: "{cm:AddToPath}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: unchecked
Name: "firewall"; Description: "{cm:FirewallException}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: unchecked

[Dirs]
Name: "{app}"; Permissions: users-modify
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\cache"; Permissions: users-modify
Name: "{app}\temp"; Permissions: users-modify
Name: "{commonappdata}\{#AppName}"; Permissions: users-modify
Name: "{commonappdata}\{#AppName}\Templates"; Permissions: users-modify
Name: "{userdocs}\EduPlay"; Permissions: users-modify
Name: "{userdocs}\EduPlay\Projects"; Permissions: users-modify
Name: "{userdocs}\EduPlay\Exports"; Permissions: users-modify
Name: "{localappdata}\{#AppName}"; Permissions: users-modify
Name: "{localappdata}\{#AppName}\Cache"; Permissions: users-modify
Name: "{localappdata}\{#AppName}\Logs"; Permissions: users-modify

[Files]
; Main Application Files
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs solidbreak

; VSTO Add-in (Optional - for PowerPoint integration)
#ifexist VstoMsiPath
Source: "{#VstoMsiPath}"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: WantsVstoAddin
#endif

[Registry]
; Application Registration
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; Flags: uninsdeletekeyifempty
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#AppVersion}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "ExecutablePath"; ValueData: "{app}\{#AppExeName}"; Flags: uninsdeletevalue

; Uninstall Information
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: string; ValueName: "URLInfoAbout"; ValueData: "{#AppURL}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: string; ValueName: "HelpLink"; ValueData: "{#SupportURL}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: string; ValueName: "URLUpdateInfo"; ValueData: "{#UpdateURL}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: dword; ValueName: "NoModify"; ValueData: "1"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: dword; ValueName: "NoRepair"; ValueData: "1"; Flags: uninsdeletevalue

; File Association (.eduplay)
Root: HKCR; Subkey: ".eduplay"; ValueType: string; ValueData: "EduPlayProject"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "EduPlayProject"; ValueType: string; ValueData: "EduPlay Project File"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "EduPlayProject\DefaultIcon"; ValueType: string; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "EduPlayProject\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: fileassoc

; Current User File Association (Fallback)
Root: HKCU; Subkey: "Software\Classes\.eduplay"; ValueType: string; ValueData: "EduPlayProject"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\EduPlayProject"; ValueType: string; ValueData: "EduPlay Project File"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\EduPlayProject\DefaultIcon"; ValueType: string; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\EduPlayProject\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: fileassoc

; App Paths (allows running app from Run dialog)
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExeName}"; ValueType: string; ValueData: "{app}\{#AppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Flags: uninsdeletekey

[Icons]
; Start Menu
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Comment: "Launch {#AppName}"; IconIndex: 0
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"; Comment: "Uninstall {#AppName}"

; Desktop
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Comment: "{#AppName}"; IconIndex: 0; Tasks: desktopicon

; Quick Launch (Windows 7 and earlier)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
; Launch application after install
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent unchecked

; Add Windows Firewall exception
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#AppName}"" dir=in action=allow program=""{app}\{#AppExeName}"" enable=yes profile=any"; Flags: runhidden; Tasks: firewall; Check: IsAdminInstallMode

[UninstallRun]
; Remove Windows Firewall exception
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#AppName}"""; Flags: runhidden; RunOnceId: "RemoveFirewall"

[UninstallDelete]
; ==========================================
; CLEANUP: Files Created During Runtime
; ==========================================

; App Installation Directory - Temporary/Cache Files
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"
Type: files; Name: "{app}\*.cache"
Type: files; Name: "{app}\*.pyc"
Type: files; Name: "{app}\*.pyo"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cache"
Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\__pycache__"

; LocalAppData - Runtime Cache (ALWAYS DELETE - app creates this)
Type: filesandordirs; Name: "{localappdata}\EduPlayStudio\runtime_cache"
Type: filesandordirs; Name: "{localappdata}\EduPlay Studio\runtime_cache"

; LocalAppData - VSTO Add-in Trusted Slides Cache (ALWAYS DELETE)
Type: filesandordirs; Name: "{localappdata}\EduPlayPPTAddin\TrustedSlides"

; Temp Directory - Preview Files (ALWAYS DELETE)
Type: filesandordirs; Name: "{tmp}\eduplay_preview_files"

; User Documents - Publish Cache (ALWAYS DELETE)
Type: filesandordirs; Name: "{userdocs}\EduPlay\PublishCache"

; ==========================================
; CONDITIONAL CLEANUP: User Data
; ==========================================

; LocalAppData - App Settings and Cache (if user chooses)
Type: filesandordirs; Name: "{localappdata}\EduPlay Studio"; Check: ShouldDeleteAppData
Type: filesandordirs; Name: "{localappdata}\EduPlayStudio"; Check: ShouldDeleteAppData

; CommonAppData - Shared Templates (if user chooses)
Type: filesandordirs; Name: "{commonappdata}\EduPlay Studio"; Check: ShouldDeleteAppData

; User Documents - Projects and Exports (if user chooses)
; IMPORTANT: Settings folder is NEVER deleted (contains proxy token - 1 per machine only)
Type: filesandordirs; Name: "{userdocs}\EduPlay\Projects"; Check: ShouldDeleteProjects
Type: filesandordirs; Name: "{userdocs}\EduPlay\Exports"; Check: ShouldDeleteProjects
; NOTE: EduPlay folder NOT deleted to preserve Settings folder with proxy token

; ==========================================
; CLEANUP: Installation Artifacts
; ==========================================

; Uninstaller files (ALWAYS DELETE)
Type: files; Name: "{app}\unins000.exe"
Type: files; Name: "{app}\unins000.dat"
Type: files; Name: "{app}\unins001.exe"
Type: files; Name: "{app}\unins001.dat"

; Empty installation directory if all cleaned up
Type: dirifempty; Name: "{app}"

[Code]
// ==========================================
// Global Variables
// ==========================================
var
  DeleteAppData: Boolean;
  DeleteProjects: Boolean;
  OldVersionUninstalled: Boolean;
  CleanInstall: Boolean;

// ==========================================
// Utility Functions
// ==========================================

// Check if application is running
function IsAppRunning(): Boolean;
var
  FSWbemLocator: Variant;
  FWMIService: Variant;
  FWbemObjectSet: Variant;
begin
  Result := False;
  try
    FSWbemLocator := CreateOleObject('WbemScripting.SWbemLocator');
    FWMIService := FSWbemLocator.ConnectServer('localhost', 'root\CIMV2', '', '');
    FWbemObjectSet := FWMIService.ExecQuery('SELECT * FROM Win32_Process WHERE Name="' + '{#AppExeName}' + '"');
    Result := (FWbemObjectSet.Count > 0);
  except
    Result := False;
  end;
end;

// Force close application
function CloseApp(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if IsAppRunning() then
  begin
    if MsgBox('EduPlay Studio is currently running. Setup needs to close it to continue.' + #13#10 + #13#10 + 'Click OK to close the application, or Cancel to exit Setup.', mbConfirmation, MB_OKCANCEL) = IDOK then
    begin
      Exec('taskkill.exe', '/F /IM "{#AppExeName}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(1000);
      Result := not IsAppRunning();
    end
    else
      Result := False;
  end;
end;

// Get installed version
function GetInstalledVersion(): String;
var
  Version: String;
begin
  if RegQueryStringValue(HKLM, 'Software\{#AppPublisher}\{#AppName}', 'Version', Version) then
    Result := Version
  else if RegQueryStringValue(HKCU, 'Software\{#AppPublisher}\{#AppName}', 'Version', Version) then
    Result := Version
  else
    Result := '';
end;

// Get uninstall string
function GetUninstallString(): String;
var
  UninstallPath: String;
begin
  Result := '';
  if RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1', 'UninstallString', UninstallPath) then
    Result := UninstallPath
  else if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1', 'UninstallString', UninstallPath) then
    Result := UninstallPath;
end;

// Uninstall previous version
function UninstallOldVersion(): Boolean;
var
  UninstallString: String;
  ResultCode: Integer;
begin
  Result := True;
  UninstallString := GetUninstallString();
  
  if UninstallString <> '' then
  begin
    UninstallString := RemoveQuotes(UninstallString);
    
    if CleanInstall then
      Result := Exec(UninstallString, '/VERYSILENT /NORESTART /SUPPRESSMSGBOXES /FORCEREMOVE', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
    else
      Result := Exec(UninstallString, '/VERYSILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      
    if Result then
    begin
      Sleep(2000);
      OldVersionUninstalled := True;
    end;
  end;
end;

// Check if old version exists
function OldVersionExists(): Boolean;
begin
  Result := (GetInstalledVersion() <> '');
end;

// Add to PATH environment variable
procedure AddToPath();
var
  Path: String;
  AppPath: String;
begin
  if not RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path) then
    Path := '';
    
  AppPath := ExpandConstant('{app}');
  
  if Pos(AppPath, Path) = 0 then
  begin
    if Path <> '' then
      Path := Path + ';';
    Path := Path + AppPath;
    RegWriteStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path);
  end;
end;

// Remove from PATH environment variable
procedure RemoveFromPath();
var
  Path: String;
  AppPath: String;
  P: Integer;
begin
  if RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path) then
  begin
    AppPath := ExpandConstant('{app}');
    P := Pos(AppPath, Path);
    
    if P > 0 then
    begin
      Delete(Path, P, Length(AppPath));
      
      if (P > 1) and (Path[P - 1] = ';') then
        Delete(Path, P - 1, 1);
        
      if (P <= Length(Path)) and (Path[P] = ';') then
        Delete(Path, P, 1);
        
      RegWriteStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path);
    end;
  end;
end;

// Refresh environment after changes
procedure RefreshEnvironment();
var
  ResultCode: Integer;
begin
  // Broadcast WM_SETTINGCHANGE message to notify all windows
  Exec('cmd.exe', '/c setx EDUPLAY_REFRESH "1" >nul 2>&1 & setx EDUPLAY_REFRESH "" >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

// Check functions for conditional execution
function WantsVstoAddin(): Boolean;
begin
  Result := True; // Can be expanded with a custom page
end;

function ShouldDeleteAppData(): Boolean;
begin
  Result := DeleteAppData;
end;

function ShouldDeleteProjects(): Boolean;
begin
  Result := DeleteProjects;
end;

// ==========================================
// Setup Event Handlers
// ==========================================

function InitializeSetup(): Boolean;
var
  OldVersion: String;
  Response: Integer;
begin
  Result := True;
  CleanInstall := False;
  OldVersionUninstalled := False;
  
  // Check if app is running
  if not CloseApp() then
  begin
    Result := False;
    Exit;
  end;
  
  // Check for old version
  if OldVersionExists() then
  begin
    OldVersion := GetInstalledVersion();
    
    if not WizardSilent() then
    begin
      Response := MsgBox(
        'Version ' + OldVersion + ' is currently installed.' + #13#10 + #13#10 +
        'Do you want to perform a CLEAN installation?' + #13#10 + #13#10 +
        'YES = Clean Install (removes all data and settings)' + #13#10 +
        'NO = Upgrade (keeps your projects and settings)' + #13#10 +
        'CANCEL = Exit Setup' + #13#10 + #13#10 +
        'Recommended: NO (Upgrade)',
        mbConfirmation,
        MB_YESNOCANCEL
      );
      
      case Response of
        IDYES: CleanInstall := True;
        IDNO: CleanInstall := False;
        IDCANCEL:
        begin
          Result := False;
          Exit;
        end;
      end;
    end;
    
    // Uninstall old version
    if not UninstallOldVersion() then
    begin
      MsgBox('Failed to uninstall the previous version. Setup will now exit.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  case CurStep of
    ssPostInstall:
    begin
      // Add to PATH if task selected
      if IsTaskSelected('addtopath') then
        AddToPath();
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  LocalAppData: String;
  UserDocs: String;
  TempDir: String;
begin
  case CurUninstallStep of
    usUninstall:
    begin
      // Close app if running
      if IsAppRunning() then
      begin
        if MsgBox('{#AppName} is currently running. Click OK to close it.', mbConfirmation, MB_OKCANCEL) = IDOK then
          Exec('taskkill.exe', '/F /IM "{#AppExeName}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
    end;
    
    usPostUninstall:
    begin
      // Remove from PATH
      RemoveFromPath();
      
      // ==========================================
      // ALWAYS DELETE: Runtime-Created Files/Folders
      // ==========================================
      
      // Get environment paths
      LocalAppData := ExpandConstant('{localappdata}');
      UserDocs := ExpandConstant('{userdocs}');
      TempDir := ExpandConstant('{tmp}');
      
      // Delete runtime cache (always - these are temporary files)
      DelTree(LocalAppData + '\EduPlayStudio\runtime_cache', True, True, True);
      DelTree(LocalAppData + '\EduPlay Studio\runtime_cache', True, True, True);
      
      // Delete VSTO addin trusted slides cache (always - these are temporary)
      DelTree(LocalAppData + '\EduPlayPPTAddin\TrustedSlides', True, True, True);
      DelTree(LocalAppData + '\EduPlayPPTAddin', True, True, True);
      
      // Delete preview temp files (always - these are temporary)
      DelTree(TempDir + '\eduplay_preview_files', True, True, True);
      
      // Delete publish cache (always - these are export artifacts)
      DelTree(UserDocs + '\EduPlay\PublishCache', True, True, True);
      
      // ==========================================
      // CONDITIONAL: User Data (based on user choice)
      // ==========================================
      
      if DeleteAppData then
      begin
        // Delete app data directories
        DelTree(LocalAppData + '\EduPlay Studio', True, True, True);
        DelTree(LocalAppData + '\EduPlayStudio', True, True, True);
        DelTree(ExpandConstant('{commonappdata}') + '\EduPlay Studio', True, True, True);
      end;
      
      if DeleteProjects then
      begin
        // Delete user projects and exports
        DelTree(UserDocs + '\EduPlay\Projects', True, True, True);
        DelTree(UserDocs + '\EduPlay\Exports', True, True, True);
        
        // IMPORTANT: DO NOT delete EduPlay folder to preserve Settings folder
        // Settings folder contains proxy token (1 per machine - cannot be regenerated)
        // RemoveDir(UserDocs + '\EduPlay'); // DISABLED - keeps Settings folder
      end;
      
      // ==========================================
      // REGISTRY CLEANUP
      // ==========================================
      
      // Remove application registry keys
      RegDeleteKeyIncludingSubkeys(HKLM, 'Software\{#AppPublisher}\{#AppName}');
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\{#AppPublisher}\{#AppName}');
      
      // Remove file association registry keys
      RegDeleteKeyIncludingSubkeys(HKCR, '.eduplay');
      RegDeleteKeyIncludingSubkeys(HKCR, 'EduPlayProject');
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\.eduplay');
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\EduPlayProject');
      
      // Remove App Paths registry
      RegDeleteKeyIncludingSubkeys(HKLM, 'Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExeName}');
      
      // Notify system of file association changes
      RefreshEnvironment();
    end;
  end;
end;

function InitializeUninstall(): Boolean;
var
  Response: Integer;
  Message: String;
  LocalAppData: String;
  UserDocs: String;
begin
  Result := True;
  DeleteAppData := False;
  DeleteProjects := False;
  
  LocalAppData := ExpandConstant('{localappdata}');
  UserDocs := ExpandConstant('{userdocs}');
  
  if not UninstallSilent() then
  begin
    // First dialog: Explain what will always be deleted
    Message := 'The following temporary files will be automatically removed:' + #13#10 + #13#10 +
      '• Runtime cache: ' + LocalAppData + '\EduPlayStudio\runtime_cache' + #13#10 +
      '• VSTO cache: ' + LocalAppData + '\EduPlayPPTAddin' + #13#10 +
      '• Preview files: ' + ExpandConstant('{tmp}') + '\eduplay_preview_files' + #13#10 +
      '• Publish cache: ' + UserDocs + '\EduPlay\PublishCache' + #13#10 + #13#10 +
      'Do you also want to remove application settings and cache?' + #13#10 + #13#10 +
      'This includes:' + #13#10 +
      '• App settings: ' + LocalAppData + '\EduPlay Studio' + #13#10 +
      '• Shared templates: ' + ExpandConstant('{commonappdata}') + '\EduPlay Studio' + #13#10 + #13#10 +
      'Choose YES to remove settings (clean uninstall)' + #13#10 +
      'Choose NO to keep settings (for reinstall)' + #13#10 + #13#10 +
      'Recommended: NO if you plan to reinstall';
    
    Response := MsgBox(Message, mbConfirmation, MB_YESNO or MB_DEFBUTTON2);
    
    DeleteAppData := (Response = IDYES);
    
    // Second dialog: Ask about projects
    Message := 'Do you want to DELETE YOUR PROJECTS?' + #13#10 + #13#10 +
      'Location: ' + UserDocs + '\EduPlay' + #13#10 + #13#10 +
      'This includes:' + #13#10 +
      '• All .eduplay project files in Projects folder' + #13#10 +
      '• All exported games in Exports folder' + #13#10 +
      '• All media files in project folders' + #13#10 + #13#10 +
      'Will be preserved:' + #13#10 +
      '✓ Settings folder (contains proxy token - cannot be regenerated)' + #13#10 + #13#10 +
      '⚠ WARNING: PROJECT DELETION CANNOT BE UNDONE! ⚠' + #13#10 + #13#10 +
      'Choose YES only if you want to permanently delete all your work' + #13#10 +
      'Choose NO to keep your projects (RECOMMENDED)';
    
    Response := MsgBox(Message, mbConfirmation, MB_YESNO or MB_DEFBUTTON2);
    
    DeleteProjects := (Response = IDYES);
  end;
end;

procedure DeinitializeUninstall();
var
  Message: String;
  Details: String;
begin
  Details := '';
  
  // Always deleted
  Details := Details + 'Cleaned up:' + #13#10;
  Details := Details + '✓ Temporary runtime cache' + #13#10;
  Details := Details + '✓ Preview files' + #13#10;
  Details := Details + '✓ Publish cache' + #13#10;
  Details := Details + '✓ VSTO add-in cache' + #13#10;
  Details := Details + '✓ Registry entries' + #13#10;
  Details := Details + '✓ File associations' + #13#10 + #13#10;
  
  if DeleteAppData then
    Details := Details + '✓ Application settings and cache' + #13#10
  else
    Details := Details + '✗ Application settings kept (for future use)' + #13#10;
    
  if DeleteProjects then
    Details := Details + '✓ All projects and exports DELETED' + #13#10
  else
    Details := Details + '✗ Projects preserved in Documents\EduPlay' + #13#10;
  
  Message := '{#AppName} has been uninstalled.' + #13#10 + #13#10 + Details;
    
  if not UninstallSilent() then
    MsgBox(Message, mbInformation, MB_OK);
end;
