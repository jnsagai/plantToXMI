# PlantToXMI Enterprise Architect Add-In

This optional Add-In lets Enterprise Architect users import PlantUML files into
the currently selected EA package by calling the installed `planttoxmi` CLI.

The Add-In is intentionally thin. It does not parse PlantUML or generate XMI;
it runs:

```powershell
planttoxmi convert input.puml -o output.xmi --profile ea
```

## Requirements

- Windows
- Sparx Enterprise Architect, 64-bit recommended
- .NET Framework 4.8 developer tools
- .NET Framework 4.8 Developer Pack / targeting pack for MSBuild
- Visual Studio or MSBuild capable of building .NET Framework projects
- `planttoxmi` available through the managed runtime state, PATH, `PLANTTOXMI_EXE`, or the registry

## Build

Set `EA_INSTALL_DIR` if EA is not installed in the default location:

```powershell
$env:EA_INSTALL_DIR = "C:\Program Files\Sparx Systems\EA Trial"
```

Build the solution in Visual Studio or with MSBuild:

```powershell
msbuild ea-addin\PlantToXmi.EAAddin.sln /p:Configuration=Release /p:Platform=x64
```

Close Enterprise Architect before rebuilding an already registered Add-In. EA
loads the DLL into its process and Windows will prevent MSBuild from replacing
the file while EA is running.

If using `dotnet msbuild`, install the .NET Framework 4.8 Developer Pack first;
the modern .NET SDK alone does not include .NET Framework reference assemblies.

The project targets .NET Framework 4.8 and x64 by default.

## Install

Run an elevated PowerShell session from the repository root. `RegAsm /codebase`
writes COM registration under HKCR and normally requires Administrator rights.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass

.\ea-addin\scripts\install-ea-addin.ps1 `
  -DllPath ".\ea-addin\PlantToXmi.EAAddin\bin\x64\Release\PlantToXmi.EAAddin.dll" `
  -Platform x64 `
  -PlantToXmiPath "C:\path\to\planttoxmi.exe" `
  -EaInstallDir "C:\Program Files\Sparx Systems\EA Trial"
```

Restart Enterprise Architect. The Add-In should appear under:

```text
Specialize -> Add-Ins -> PlantToXMI
```

## Configuration

The Add-In resolves `planttoxmi` in this order:

1. `%LOCALAPPDATA%\PlantToXMI\current.json`
2. `HKCU\Software\PlantToXMI\EAAddin\PlantToXmiPath`
3. `PLANTTOXMI_EXE`
4. `planttoxmi.exe` or `planttoxmi` on PATH

Optional settings:

```powershell
reg add "HKCU\Software\PlantToXMI\EAAddin" /v KeepTempFiles /d true /f
reg add "HKCU\Software\PlantToXMI\EAAddin" /v TimeoutSeconds /d 60 /f
```

Update settings are stored in:

```text
%LOCALAPPDATA%\PlantToXMI\settings.json
```

Example:

```json
{
  "updateMode": "Daily",
  "updateSource": {
    "type": "github-releases",
    "owner": "YOUR_ORG_OR_USER",
    "repo": "planttoxmi",
    "channel": "stable"
  }
}
```

The active updated runtime is tracked by:

```text
%LOCALAPPDATA%\PlantToXMI\current.json
```

## Usage

1. Open an EA repository.
2. Select a target package in the Browser.
3. Choose `Specialize -> Add-Ins -> PlantToXMI -> Import PlantUML...`.
4. Select a `.puml` or `.plantuml` file.
5. Review the success or diagnostic message.

Use `PlantToXMI -> Check for Updates` to check GitHub Releases for a newer
runtime. The Add-In downloads ZIP assets to `%LOCALAPPDATA%\PlantToXMI\update-cache`,
verifies SHA-256, extracts into `%LOCALAPPDATA%\PlantToXMI\versions\<version>`,
runs `planttoxmi.exe --version`, and switches `current.json` only after the
smoke test succeeds.

## Troubleshooting

### Add-In does not appear in EA

- Register with the correct RegAsm bitness.
- Use `EAAddins64` for 64-bit EA.
- Confirm the registry default value is `PlantToXmi.EAAddin.Main`.
- Restart EA after registration.
- Build the project for x64 when using 64-bit EA.

### Add-In appears but fails to load

- Confirm .NET Framework 4.8 is installed.
- Confirm `Interop.EA.dll` resolves during build.
- Keep the built DLL and dependencies in place after `/codebase` registration.
- Check whether COM registration failed.

### planttoxmi not found

Set:

```powershell
$env:PLANTTOXMI_EXE = "C:\path\to\planttoxmi.exe"
```

or:

```powershell
reg add "HKCU\Software\PlantToXMI\EAAddin" /v PlantToXmiPath /d "C:\path\to\planttoxmi.exe" /f
```

### EA import fails

- Confirm the generated XMI file exists.
- Run `planttoxmi validate generated.xmi --profile ea`.
- Confirm the target package is writable.
- Review the diagnostic log path shown by the Add-In.
