param(
    [string]$Golden = "evaluation/d3/golden_set.template.jsonl",
    [string]$Predictions = "evaluation/d3/predictions.template.jsonl",
    [int]$Runs = 10,
    [double]$MinMicroF1 = 0.65,
    [double]$MaxStdMicroF1 = 0.02,
    [double]$MaxStdUnsupportedRate = 0.02,
    [double]$MaxStdFalseClaimRate = 0.02,
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
    "scripts\eval_d3_stability.py",
    "--golden", $Golden,
    "--predictions", $Predictions,
    "--runs", "$Runs",
    "--min-micro-f1", "$MinMicroF1",
    "--max-std-micro-f1", "$MaxStdMicroF1",
    "--max-std-unsupported-rate", "$MaxStdUnsupportedRate",
    "--max-std-false-claim-rate", "$MaxStdFalseClaimRate"
)
if ($enforceGateBool) {
    $argsEval += "--enforce-gate"
}

Write-Host "[D5] Running stability test..."
& $python @argsEval
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[D5] Done."
exit 0
