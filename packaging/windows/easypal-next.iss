#define MyAppName "EasyPal-Next"
#define MyAppVersion "0.2.0"
#define MyAppPublisher "Shane Daley M0VUB (ShaYmez)"
#define MyAppURL "https://github.com/ShaYmez/EasyPal-Next"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=EasyPal-Next-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
SetupIconFile=..\..\resources\brand\easypal-next.ico
UninstallDisplayIcon={app}\EasyPal-Next.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\EasyPal-Next\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\EasyPal-Next.exe"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\EasyPal-Next.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EasyPal-Next.exe"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
