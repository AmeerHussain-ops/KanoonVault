; KanoonVault Windows Installer Configuration
; Build with: iscc kanoonvault-installer.iss
;
; This Inno Setup script creates KanoonVault-Setup.exe
; 
; Features:
; - Installs to Program Files\KanoonVault
; - Creates Start Menu shortcuts
; - Creates Desktop shortcut (optional)
; - Preserves user data in %APPDATA%\KanoonVault during upgrades
; - Provides standard uninstall via Control Panel

#define MyAppName "KanoonVault"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "KanoonVault Contributors"
#define MyAppURL "https://github.com/AmeerHussain-ops/KanoonVault"
#define MyAppExeName "KanoonVault.exe"
#define MyAppIcon "frontend\logo.ico"
#define BuildDir "dist\KanoonVault"

[Setup]
; Installer configuration
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Install directory
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
AllowNoIcons=yes

; Output configuration
OutputBaseFilename=KanoonVault-Setup
OutputDir=.\installer-output
SetupIconFile={#MyAppIcon}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Installer behavior
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=yes
ChangesAssociations=no

; Brand information
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}

; Uninstall behavior - don't remove user data
UninstallFilesDir={app}\uninstall
UsePreviousSetupType=yes
UsePreviousAppDir=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Tasks (optional installations)
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdmin

[Files]
; Copy all files from the dist/KanoonVault directory
; The wildcard recursion includes all subdirectories and files
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Note: Don't copy frontend\logo files individually - they're already in the build

[Dirs]
; Create these directories if they don't exist (but don't remove them on uninstall)
Name: "{app}\frontend"; Flags: uninsneveruninstall

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop icon (if selected during install)
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

; Quick Launch icon (legacy, for older Windows versions)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
; No need to run anything after installation - user can launch from Start Menu

; Prompt to launch the app after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent workingdir: "{app}"

[UninstallDelete]
; Delete generated files but keep user data
; The launcher creates these at runtime, so they should be removed
Name: "{app}\*.log"; Type: files

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstalling then
  begin
    MsgBox(
      'Your documents and settings in ' + ExpandConstant('{%APPDATA%}') + '\KanoonVault have been preserved.' + #13#10 +
      'To completely remove KanoonVault, you can manually delete that folder.',
      'Uninstall Complete',
      MB_ICONINFORMATION
    );
  end;
end;

function InitializeSetup(): Boolean;
const
  RequiredWinVer = $060100; // Windows Vista / Server 2008 or later
begin
  if GetWindowsVersionEx >= RequiredWinVer then
    Result := True
  else
  begin
    MsgBox(
      'This application requires Windows Vista or later.',
      'Unsupported Windows Version',
      MB_ICONERROR
    );
    Result := False;
  end;
end;

procedure InitializeWizard;
begin
  // Custom welcome message
  WizardForm.WelcomeLabel2.Caption := 
    'This will install KanoonVault, a self-hosted legal case management application.' + #13#10 +
    '' + #13#10 +
    'No Python installation is required. All dependencies are bundled.' + #13#10 +
    '' + #13#10 +
    'Your documents and case data will be stored in: ' + ExpandConstant('{%APPDATA%}') + '\KanoonVault';
end;
