# Telegram via LocalTunnel

1. Fill `.env`:

```env
TELEGRAM_BOT_TOKEN=token_from_botfather
TELEGRAM_BOT_USERNAME=bot_username_without_at
TELEGRAM_WEBHOOK_URL=https://your-localtunnel-url.loca.lt/webhooks/telegram/webhook
```

2. Start the action server:

```powershell
.\scripts\start_action_server.ps1
```

3. Start the Rasa server:

```powershell
.\scripts\start_rasa_server.ps1
```

4. Start LocalTunnel:

```powershell
.\scripts\start_localtunnel.ps1
```

5. Copy the generated `https://*.loca.lt` URL into `.env`:

```env
TELEGRAM_WEBHOOK_URL=https://generated-url.loca.lt/webhooks/telegram/webhook
```

6. Restart the Rasa server:

```powershell
Ctrl + C
.\scripts\start_rasa_server.ps1
```

Keep all three processes running while testing Telegram:

- action server
- Rasa server
- LocalTunnel
