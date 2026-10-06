$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Pin = "f97608f178d1ffeca59860195ab7da295f7c8e5f"
$Runtime = Join-Path $Root ".hermes_runtime"
$InstallDir = Join-Path $Runtime "hermes-agent"
$HermesHome = Join-Path $Runtime "home"
$Installer = Join-Path $Runtime "install-hermes-h01.ps1"

New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

$InstallerUrl = "https://raw.githubusercontent.com/NousResearch/hermes-agent/$Pin/scripts/install.ps1"
Invoke-WebRequest -Uri $InstallerUrl -OutFile $Installer

powershell -ExecutionPolicy Bypass -File $Installer -Commit $Pin -ForceCommit -SkipSetup -SkipComputerUse -HermesHome $HermesHome -InstallDir $InstallDir

$Actual = (git -C $InstallDir rev-parse HEAD).Trim()
if ($Actual -ne $Pin) {
    throw "H01_INSTALL=FAIL expected=$Pin actual=$Actual"
}

New-Item -ItemType Directory -Force -Path $HermesHome | Out-Null
Copy-Item (Join-Path $Root "hermes\h01\config.yaml") (Join-Path $HermesHome "config.yaml") -Force

Write-Host "H01_INSTALL=PASS"
Write-Host "Hermes commit: $Actual"
Write-Host "Hermes home:   $HermesHome"
Write-Host "Next: put OPENROUTER_API_KEY in $Root\.env, then run:"
Write-Host "  python scripts/run_hermes_h01_smoke.py"
