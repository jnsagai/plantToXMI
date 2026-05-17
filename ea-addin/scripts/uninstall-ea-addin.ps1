param(
    [string]$DllPath,

    [ValidateSet("x86", "x64")]
    [string]$Platform = "x64",

    [switch]$RemoveSettings
)

$ErrorActionPreference = "Stop"

& "$PSScriptRoot\unregister-ea-addin.ps1" `
    -DllPath $DllPath `
    -Platform $Platform `
    -RemoveSettings:$RemoveSettings

Write-Host "Uninstall complete. Restart Enterprise Architect."
