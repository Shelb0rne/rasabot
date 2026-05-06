$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"

if (Test-Path $envPath) {
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
}

$requiredVariables = @(
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_BOT_USERNAME",
    "TELEGRAM_WEBHOOK_URL"
)

foreach ($variableName in $requiredVariables) {
    $variableValue = [Environment]::GetEnvironmentVariable($variableName, "Process")
    if ([string]::IsNullOrWhiteSpace($variableValue)) {
        throw "Environment variable $variableName is empty. Fill it in .env before starting the Rasa server."
    }
}

$token = [Environment]::GetEnvironmentVariable("TELEGRAM_BOT_TOKEN", "Process")
if ($token -notmatch "^\d+:[A-Za-z0-9_-]{20,}$") {
    throw "TELEGRAM_BOT_TOKEN has an invalid format. It should look like 123456789:AA... and must be copied from BotFather."
}

$username = [Environment]::GetEnvironmentVariable("TELEGRAM_BOT_USERNAME", "Process")
if ($username.StartsWith("@")) {
    throw "TELEGRAM_BOT_USERNAME must be without @. Example: my_hr_bot, not @my_hr_bot."
}

$webhookUrl = [Environment]::GetEnvironmentVariable("TELEGRAM_WEBHOOK_URL", "Process")
if ($webhookUrl -notmatch "^https://.+/webhooks/telegram/webhook$") {
    throw "TELEGRAM_WEBHOOK_URL must look like https://your-url.loca.lt/webhooks/telegram/webhook."
}

Write-Host "Loaded Telegram env:"
Write-Host "- TELEGRAM_BOT_TOKEN length:" $token.Length
Write-Host "- TELEGRAM_BOT_USERNAME:" $username
Write-Host "- TELEGRAM_WEBHOOK_URL:" $webhookUrl
Write-Host ""

Push-Location $projectRoot
try {
    & (Join-Path $projectRoot ".venv\Scripts\rasa.exe") run --enable-api --credentials credentials.yml
}
finally {
    Pop-Location
}
