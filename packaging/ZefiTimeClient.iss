; Inno Setup 6 — один установщик для клиента (сначала: PyInstaller → dist\ZefiTime).
; Сборка: открыть этот файл в Inno → Compile, либо запустить packaging\build_client.ps1 (если ISCC в PATH).
;
; Перенос на той же Windows: можно переместить всю папку, куда установили (ZefiTime.exe и каталог _internal
; должны остаться рядом). Ярлыки в меню Пуск укажут на старый путь — запускайте ZefiTime.exe из новой папки
; или переустановите установщиком в новое место.

#define MyAppName "ZefiTime"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ZefiTime"
#define MyAppExeName "ZefiTime.exe"

#define ProjectRoot ".."
#define DistDir ProjectRoot + "\dist\ZefiTime"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Папка пользователя без прав администратора; при установке можно выбрать другой диск/каталог.
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableProgramGroupPage=no
DisableDirPage=no
OutputDir=..\dist\installer
OutputBaseFilename=ZefiTime-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
