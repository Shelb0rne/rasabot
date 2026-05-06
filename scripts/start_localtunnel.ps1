$ErrorActionPreference = "Stop"

$port = "5005"

Write-Host "Starting LocalTunnel for http://localhost:$port ..."
Write-Host "Copy the generated https://*.loca.lt URL and put it into .env as:"
Write-Host "TELEGRAM_WEBHOOK_URL=https://your-url.loca.lt/webhooks/telegram/webhook"
Write-Host ""

npx.cmd localtunnel --port $port
