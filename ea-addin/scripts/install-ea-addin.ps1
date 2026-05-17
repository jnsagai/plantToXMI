param(
    [Parameter(Mandatory = $true)]
    [string]$DllPath,

    [ValidateSet("x86", "x64")]
    [string]$Platform = "x64",

    [string]$PlantToXmiPath,

    [string]$EaInstallDir = "C:\Program Files\Sparx Systems\EA Trial"
)

$ErrorActionPreference = "Stop"

& "$PSScriptRoot\register-ea-addin.ps1" `
    -DllPath $DllPath `
    -Platform $Platform `
    -PlantToXmiPath $PlantToXmiPath `
    -EaInstallDir $EaInstallDir

Write-Host "Install complete. Restart Enterprise Architect."
