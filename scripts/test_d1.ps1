param(
    [switch]$Coverage,
    [int]$MinCoverage = 20
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) {
    Write-Error '.venv introuvable. Lancez d''abord: scripts\install_env.bat'
}

if ($Coverage) {
    Write-Host "[INFO] Tests D1 avec couverture (seuil $MinCoverage%)."
    & $python -m pytest -c pytest.ini tests_d1 --cov=src --cov=ui --cov-report=term-missing --cov-fail-under=$MinCoverage -q
} else {
    Write-Host '[INFO] Tests D1 sans couverture.'
    & $python -m pytest -c pytest.ini tests_d1 -q
}

exit $LASTEXITCODE
