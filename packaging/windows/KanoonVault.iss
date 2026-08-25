; Inno Setup Script for KanoonVault
; Produces: installer\KanoonVault-Setup.exe

#define MyAppName "KanoonVault"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "KanoonVault Contributors"
#define MyAppURL "https://github.com/AmeerHussain-ops/KanoonVault"
#define MyAppExeName "KanoonVault.exe"
#define MyAppIcon "..\..\frontend\logo.ico"
#define BuildDir "..\..\dist\KanoonVault"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
AllowNoIcons=yes
SetupIconFile={#MyAppIcon}
OutputBaseFilename=KanoonVault-Setup
OutputDir=..\..\installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=yes
ChangesAssociations=no
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch KanoonVault"; Flags: nowait postinstall skipifsilent workingdir: "{app}"

[UninstallDelete]
Type: files; Name: "{app}\*.log"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
