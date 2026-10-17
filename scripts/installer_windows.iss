; Inno Setup Script for Huawei EMS B1 Battery Manager
; Generates a professional Windows Setup Installer (.exe) with desktop & start menu shortcuts

#define MyAppName "Huawei EMS B1 Battery Manager"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Huawei EMS BMS Project"
#define MyAppURL "https://github.com/example/huawei-ems-b1-manager"
#define MyAppExeName "HuaweiEMSManager.exe"

[Setup]
AppId={{8B84B224-5D8E-4A3C-9C1D-89EF234805B1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Huawei-EMS-B1-Manager-Windows-x64-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\HuaweiEMSManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Serial driver and user documentation
Source: "..\docs\RS485_WIRING_GUIDE.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\INSTALLATION_WINDOWS.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"
