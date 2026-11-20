#define AppName "Epi Control"
#define AppVersion "1.0.1"
#define AppExe "EpiControl.exe"
#define AppId "EpiControl.Standalone"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Rafael Oliveira de Jesus
AppSupportURL=mailto:rafaelentele@gmail.com
DefaultDirName={localappdata}\Programs\Epi Control
DefaultGroupName=Epi Control
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile={#SourcePath}app\assets\icone_sistema.ico
OutputDir={#SourcePath}dist_instalador
OutputBaseFilename=EpiControlSetup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
Uninstallable=yes
SetupLogging=yes
; O banco em %LOCALAPPDATA%\EPIControl\data permanece fora da pasta do app.
; O desinstalador não remove os dados do usuário.

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Files]
Source: "{#SourcePath}dist_instalacao\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Epi Control"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\Epi Control"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Iniciar o Epi Control"; Flags: postinstall nowait skipifsilent
