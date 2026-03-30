param(
    [string]$D3 = "outputs/evaluation/d3/metrics_d3.json",
    [string]$D4 = "outputs/evaluation/d3/ablation_d4.json",
    [string]$D5 = "outputs/evaluation/d3/stability_d5.json",
    [string]$EnforceGate = "true"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Error ".venv introuvable. Lancez d'abord: scripts\install_env.bat"
}

$enforceGateNormalized = $EnforceGate.Trim().ToLowerInvariant()
$enforceGateBool = @("1", "true", "yes", "y", "on") -contains $enforceGateNormalized

$argsEval = @(
    "scripts\eval_d6_calibration.py",
    "--d3", $D3,
    "--d4", $D4,
    "--d5", $D5
)
if ($enforceGateBool) {
    $argsEval += "--enforce-gate"
}

Write-Host "[D6] Running calibration..."
& $python @argsEval
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[D6] Done."
exit 0
