#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

#ifndef SourceDir
#define SourceDir "..\..\backend\dist\wence_ai"
#endif

#ifndef OutputDir
#define OutputDir "..\..\backend\package"
#endif

#ifndef OutputBaseFilename
#define OutputBaseFilename "wence_ai-windows-x86_64-installer"
#endif

#ifndef IconFile
#define IconFile "..\robot.ico"
#endif

[Setup]
AppId={{3E1F8619-7E15-491F-B8F9-8919D7850B19}
AppName=WenCe AI
AppVersion={#AppVersion}
AppPublisher=WenCe AI Team
AppPublisherURL=https://github.com/visresearch/WordAgent
AppSupportURL=https://github.com/visresearch/WordAgent/issues
AppUpdatesURL=https://github.com/visresearch/WordAgent/releases
DefaultDirName={autopf}\WenCe AI
DefaultGroupName=WenCe AI
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
SetupIconFile={#IconFile}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\wence_ai.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\WenCe AI"; Filename: "{app}\wence_ai.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\WenCe AI"; Filename: "{app}\wence_ai.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\wence_ai.exe"; Description: "{cm:LaunchProgram,WenCe AI}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
