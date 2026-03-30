param(
    [string]$OutputMd = "outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.md",
    [string]$OutputJson = "outputs/soutenance/PRE_SOUTENANCE_CHECKLIST.json",
    [string]$EnforceStrict = "false"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (!(Test-Path $python)) {
    Write-Error ".venv introuvable. Lancez d'abord: scripts\install_env.bat"
}

$strictNormalized = $EnforceStrict.Trim().ToLowerInvariant()
$strictBool = @("1", "true", "yes", "y", "on") -contains $strictNormalized

$argsEval = @(
    "scripts\pre_soutenance_check.py",
    "--project-root", ".",
    "--output-md", $OutputMd,
    "--output-json", $OutputJson
)
if ($strictBool) {
    $argsEval += "--enforce-strict"
}

Write-Host "[E2] Running pre-soutenance checklist..."
& $python @argsEval
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
Write-Host "[E2] Done."
exit 0
