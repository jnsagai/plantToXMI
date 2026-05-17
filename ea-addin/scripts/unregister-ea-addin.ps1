param(
    [string]$DllPath,

    [ValidateSet("x86", "x64")]
    [string]$Platform = "x64",

    [switch]$RemoveSettings
)

$ErrorActionPreference = "Stop"

$regAsm = if ($Platform -eq "x64") {
    "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe"
} else {
    "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe"
}

if ($DllPath) {
    $resolvedDll = Resolve-Path -LiteralPath $DllPath
    & $regAsm $resolvedDll /unregister
    if ($LASTEXITCODE -ne 0) {
        throw "RegAsm unregister failed with exit code $LASTEXITCODE. Run this script from an elevated PowerShell session because RegAsm writes COM registration under HKCR."
    }
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

Remove-Item -Path $eaKey -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path $legacyEaKey -Recurse -Force -ErrorAction SilentlyContinue

if ($RemoveSettings) {
    Remove-Item -Path "HKCU:\Software\PlantToXMI\EAAddin" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Unregistered PlantToXmi EA Add-In for $Platform."
