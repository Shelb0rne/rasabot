$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    & (Join-Path $projectRoot ".venv\Scripts\rasa.exe") run actions
}
finally {
    Pop-Location
}
