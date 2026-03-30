$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host '======================================================='
Write-Host 'AEBM - Installation environnement'
Write-Host '======================================================='

if (!(Test-Path '.venv\Scripts\python.exe')) {
    Write-Host '[INFO] Creation du venv...'
    try { py -3.12 -m venv .venv } catch { python -m venv .venv }
}

if (!(Test-Path '.venv\Scripts\python.exe')) {
    throw 'Impossible de creer .venv'
}

& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
if (Test-Path 'requirements.lock') {
    Write-Host '[INFO] Installation depuis requirements.lock ...'
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements.lock
} else {
    Write-Host '[INFO] Installation depuis requirements.txt ...'
    & '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
}

& '.\.venv\Scripts\python.exe' scripts\preflight.py --quick
