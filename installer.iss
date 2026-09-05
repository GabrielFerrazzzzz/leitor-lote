; Instalador do leitor-lote (Inno Setup).
; Empacota a saída --onedir do PyInstaller (dist\leitor-lote\) num instalador
; de usuário único (sem admin), com atalho na área de trabalho.
;
; O usuário escolhe a pasta de instalação (DisableDirPage=no). O padrão sugerido
; é C:\Users\<voce>\leitor-lote -- fácil de achar no Explorer e sem precisar de
; admin. Antes ia pra %LOCALAPPDATA% (AppData, oculto), que era difícil de achar.
;
; Uso local: iscc installer.iss   (depois de "uv run pyinstaller leitor-lote.spec")
; Uso no CI: ISCC.exe installer.iss /DMyAppVersion=0.1.2

#define MyAppName "leitor-lote"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif
#define MyAppExeName "leitor-lote.exe"
#define MyAppPublisher "Gabriel Ferraz"
#define MyAppURL "https://github.com/GabrielFerrazzzzz/leitor-lote"

[Setup]
AppId={{6F2D7C9A-6C3E-4A1B-9C6E-5B1E2C7A9F31}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={%USERPROFILE}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=.
OutputBaseFilename=leitor-lote-setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"

[Files]
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
