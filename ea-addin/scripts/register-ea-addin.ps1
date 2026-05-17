param(
    [Parameter(Mandatory = $true)]
    [string]$DllPath,

    [ValidateSet("x86", "x64")]
    [string]$Platform = "x64",

    [string]$PlantToXmiPath,

    [string]$EaInstallDir = "C:\Program Files\Sparx Systems\EA Trial"
)

$ErrorActionPreference = "Stop"

$resolvedDll = Resolve-Path -LiteralPath $DllPath
$regAsm = if ($Platform -eq "x64") {
    "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe"
} else {
    "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe"
}

if (-not (Test-Path -LiteralPath $regAsm)) {
    throw "RegAsm not found at $regAsm"
}

$dllDirectory = Split-Path -Parent $resolvedDll
$interopTarget = Join-Path $dllDirectory "Interop.EA.dll"
if (-not (Test-Path -LiteralPath $interopTarget)) {
    $interopSource = Join-Path $EaInstallDir "Interop.EA.dll"
    if (-not (Test-Path -LiteralPath $interopSource)) {
        throw "Interop.EA.dll not found next to add-in DLL or at $interopSource. Copy Interop.EA.dll beside the add-in DLL or pass -EaInstallDir."
    }
    Copy-Item -LiteralPath $interopSource -Destination $interopTarget -Force
}

& $regAsm $resolvedDll /codebase
if ($LASTEXITCODE -ne 0) {
    throw "RegAsm failed with exit code $LASTEXITCODE. Run this script from an elevated PowerShell session because RegAsm /codebase writes COM registration under HKCR."
}

$eaKey = if ($Platform -eq "x64") {
    "HKCU:\Software\Sparx Systems\EAAddins64\PlantToXmi.EAAddin"
} else {
    "HKCU:\Software\Sparx Systems\EAAddins\PlantToXmi.EAAddin"
}

$legacyEaKey = if ($Platform -eq "x64") {
    "HKCU:\Software\Sparx Systems\EAAddins64\PlantToXmiEaAddin"
} else {
    "HKCU:\Software\Sparx Systems\EAAddins\PlantToXmiEaAddin"
}
Remove-Item -Path $legacyEaKey -Recurse -Force -ErrorAction SilentlyContinue

New-Item -Path $eaKey -Force | Out-Null
reg add ($eaKey -replace "HKCU:", "HKCU") /ve /d "PlantToXmi.EAAddin.Main" /f | Out-Null

if ($PlantToXmiPath) {
    if (-not (Test-Path -LiteralPath $PlantToXmiPath)) {
        throw "PlantToXMI executable not found: $PlantToXmiPath"
    }
    $settingsKey = "HKCU:\Software\PlantToXMI\EAAddin"
    New-Item -Path $settingsKey -Force | Out-Null
    New-ItemProperty -Path $settingsKey -Name PlantToXmiPath -Value (Resolve-Path -LiteralPath $PlantToXmiPath) -PropertyType String -Force | Out-Null
}

Write-Host "Registered PlantToXmi EA Add-In for $Platform."
