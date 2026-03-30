param(
    [int]$TotalMinutes = 15,
    [string]$D6Json = "outputs/evaluation/d3/calibration_d6.json",
    [string]$ChecklistJson = "outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.json",
    [string]$OutputMd = "outputs/soutenance/DRY_RUN_SOUTENANCE.md",
    [string]$OutputJson = "outputs/soutenance/DRY_RUN_SOUTENANCE.json"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Error ".venv introuvable. Lancez d'abord: scripts\install_env.bat"
}

Write-Host "[E3] Building dry-run script..."
& $python scripts\build_soutenance_dryrun.py --total-minutes $TotalMinutes --d6-json $D6Json --checklist-json $ChecklistJson --output-md $OutputMd --output-json $OutputJson
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[E3] Done."
exit 0
