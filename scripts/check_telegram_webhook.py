import asyncio
import os

import aiohttp


async def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    expected_url = os.environ.get("TELEGRAM_WEBHOOK_URL")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is empty")

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
        async with session.get(url) as response:
            data = await response.json()

    print("getWebhookInfo ok:", data.get("ok"))
    result = data.get("result", {})
    actual_url = result.get("url")
    print("expected url:", expected_url)
    print("actual url:  ", actual_url)
    print("url matches:", actual_url == expected_url)
    print("pending updates:", result.get("pending_update_count"))
    print("last error date:", result.get("last_error_date"))
    print("last error message:", result.get("last_error_message"))


if __name__ == "__main__":
    asyncio.run(main())
