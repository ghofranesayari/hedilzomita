param(
    [string]$OutDir = "outputs/soutenance",
    [string]$ZipName = "AEBM_HANDOVER_PACKAGE.zip"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Error ".venv introuvable. Lancez d'abord: scripts\install_env.bat"
}

Write-Host "[E5] Building handover bundle..."
& $python scripts\build_handover_bundle.py --out-dir $OutDir --zip-name $ZipName
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[E5] Done."
exit 0
