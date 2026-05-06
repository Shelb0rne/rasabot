$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"

if (-not (Test-Path $envPath)) {
    throw ".env file was not found."
}

Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }

    $parts = $line.Split("=", 2)
    if ($parts.Count -ne 2) {
        return
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim().Trim('"').Trim("'")
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
}

$token = [Environment]::GetEnvironmentVariable("TELEGRAM_BOT_TOKEN", "Process")
$username = [Environment]::GetEnvironmentVariable("TELEGRAM_BOT_USERNAME", "Process")
$webhookUrl = [Environment]::GetEnvironmentVariable("TELEGRAM_WEBHOOK_URL", "Process")

Write-Host "TELEGRAM_BOT_TOKEN length:" $token.Length
Write-Host "TELEGRAM_BOT_TOKEN has colon:" $token.Contains(":")
Write-Host "TELEGRAM_BOT_USERNAME:" $username
Write-Host "TELEGRAM_WEBHOOK_URL:" $webhookUrl

Push-Location $projectRoot
try {
    & (Join-Path $projectRoot ".venv\Scripts\python.exe") -c "import os; from aiogram.bot.api import check_token; token=os.environ.get('TELEGRAM_BOT_TOKEN'); check_token(token); print('Token format is valid for aiogram')"
}
finally {
    Pop-Location
}
