param(
    [string]$Path = ".env"
)

if (!(Test-Path $Path)) {
    exit 0
}

$allowed = @(
    "AEBM_NEO4J_MODE",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "NEO4J_CONTAINER",
    "GROQ_API_KEY"
)

Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) { return }
    if ($line.StartsWith("#")) { return }
    if (-not $line.Contains("=")) { return }

    $parts = $line.Split("=", 2)
    $key = $parts[0].Trim()
    $value = $parts[1].Trim()

    if (-not ($allowed -contains $key)) { return }

    if ($value.Length -ge 2) {
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
    }

    Write-Output ("{0}={1}" -f $key, $value)
}
