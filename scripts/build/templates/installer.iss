; Central de Gestao — Inno Setup Installer (Single-File Mode)
; Versao injetada via /DMyAppVersion=<versao>

#define MyAppName "Central de Gestao"
#define MyAppPublisher "Fernando H. Garcia"
#define MyAppURL "https://github.com/Fernando-H-Garcia/Central_de_Gestao"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=./
OutputBaseFilename=CentralDeGestao_Installer
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na &Area de Trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce

[Files]
Source: "CentralDeGestao.exe"; DestDir: "{app}"; Flags: ignoreversion
; VC++ Redist (opcional)
#if FileExists("VC_redist.x64.exe")
Source: "VC_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: IsWin64
#endif

[Dirs]
Name: "{localappdata}\CentralGestao"; Permissions: users-modify
Name: "{localappdata}\CentralGestao\database"; Permissions: users-modify
Name: "{localappdata}\CentralGestao\logs"; Permissions: users-modify
Name: "{localappdata}\CentralGestao\config"; Permissions: users-modify
Name: "{localappdata}\CentralGestao\backups"; Permissions: users-modify

[Icons]
Name: "{group}\Central de Gestao"; Filename: "{app}\CentralDeGestao.exe"
Name: "{group}\Desinstalar Central de Gestao"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Central de Gestao"; Filename: "{app}\CentralDeGestao.exe"; Tasks: desktopicon

[Run]
; Nao executa nada — o app faz auto-configuracao no primeiro run

[UninstallRun]
; Nao executa nada — preserva dados do usuario

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\CentralGestao\.initialized"
