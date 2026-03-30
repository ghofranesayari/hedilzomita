param(
    [string]$Golden = "evaluation/d3/golden_set.template.jsonl",
    [string]$Predictions = "evaluation/d3/predictions.template.jsonl",
    [string]$OutputJson = "outputs/evaluation/d3/metrics_d3.json",
    [string]$OutputMd = "outputs/evaluation/d3/report_d3.md",
    [double]$MinMicroF1 = 0.65,
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

Write-Host "[D3] Running evaluation..."
$argsEval = @(
    "scripts\eval_d3.py",
    "--golden", $Golden,
    "--predictions", $Predictions,
    "--output", $OutputJson,
    "--output-md", $OutputMd,
    "--min-micro-f1", "$MinMicroF1"
)
if ($enforceGateBool) {
    $argsEval += "--enforce-gate"
}
& $python @argsEval

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "[D3] Done."
Write-Host "[D3] JSON: $OutputJson"
Write-Host "[D3] MD  : $OutputMd"
exit 0
