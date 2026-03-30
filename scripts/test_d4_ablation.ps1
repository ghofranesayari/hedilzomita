param(
    [string]$Golden = "evaluation/d3/golden_set.template.jsonl",
    [string]$VariantsDir = "evaluation/d3/variants",
    [string]$Baseline = "baseline",
    [double]$MinMicroF1 = 0.65
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Error ".venv introuvable. Lancez d'abord: scripts\install_env.bat"
}

Write-Host "[D4] Running ablation study..."
& $python scripts\eval_d3_ablation.py --golden $Golden --variants-dir $VariantsDir --baseline $Baseline --min-micro-f1 $MinMicroF1
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[D4] Done."
exit 0
