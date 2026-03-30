param(
    [string]$D3 = "outputs/evaluation/d3/metrics_d3.json",
    [string]$D5 = "outputs/evaluation/d3/stability_d5.json",
    [string]$D6 = "outputs/evaluation/d3/calibration_d6.json",
    [string]$OutputMd = "outputs/soutenance/QA_JURY.md"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Error ".venv introuvable. Lancez d'abord: scripts\install_env.bat"
}

Write-Host "[E4] Building Q&A pack..."
& $python scripts\build_soutenance_qa.py --d3 $D3 --d5 $D5 --d6 $D6 --output-md $OutputMd
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[E4] Done."
exit 0
