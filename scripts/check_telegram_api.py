import asyncio
import os

import aiohttp


async def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is empty")

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get("https://api.telegram.org") as response:
            print("api.telegram.org status:", response.status)

        url = f"https://api.telegram.org/bot{token}/getMe"
        async with session.get(url) as response:
            data = await response.json()
            print("getMe ok:", data.get("ok"))
            if data.get("ok"):
                result = data.get("result", {})
                print("bot username:", result.get("username"))
            else:
                print("telegram error:", data)


if __name__ == "__main__":
    asyncio.run(main())
