param(
    [string]$D3 = "outputs/evaluation/d3/metrics_d3.json",
    [string]$D4 = "outputs/evaluation/d3/ablation_d4.json",
    [string]$D5 = "outputs/evaluation/d3/stability_d5.json",
    [string]$D6 = "outputs/evaluation/d3/calibration_d6.json",
    [string]$OutDir = "outputs/soutenance"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Error ".venv introuvable. Lancez d'abord: scripts\install_env.bat"
}

Write-Host "[E1] Building soutenance pack..."
& $python scripts\build_soutenance_pack.py --d3 $D3 --d4 $D4 --d5 $D5 --d6 $D6 --out-dir $OutDir
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[E1] Done."
exit 0
