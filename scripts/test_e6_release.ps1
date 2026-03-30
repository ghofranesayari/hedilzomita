param(
    [string]$OutputJson = "outputs/soutenance/RELEASE_READINESS.json",
    [string]$OutputMd = "outputs/soutenance/RELEASE_READINESS.md"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Error ".venv introuvable. Lancez d'abord: scripts\install_env.bat"
}

Write-Host "[E6] Building release readiness..."
& $python scripts\build_release_readiness.py --output-json $OutputJson --output-md $OutputMd
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[E6] Done."
exit 0
