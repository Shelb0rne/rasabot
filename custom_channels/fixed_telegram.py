import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Text

from aiogram.types import Update
from aiogram.utils.exceptions import TelegramAPIError
from rasa.core.channels.channel import InputChannel, UserMessage
from rasa.core.channels.telegram import TelegramOutput
from rasa.shared.constants import INTENT_MESSAGE_PREFIX
from rasa.shared.core.constants import USER_INTENT_RESTART
from rasa.shared.exceptions import RasaException
from sanic import Blueprint, response
from sanic.request import Request
from sanic.response import HTTPResponse

logger = logging.getLogger(__name__)


class FixedTelegramInput(InputChannel):
    """Telegram channel variant that avoids closing aiogram's event loop on Windows."""

    @classmethod
    def name(cls) -> Text:
        return "telegram"

    @classmethod
    def from_credentials(
        cls, credentials: Optional[Dict[Text, Any]]
    ) -> "FixedTelegramInput":
        if not credentials:
            cls.raise_missing_credentials_exception()

        return cls(
            credentials.get("access_token"),
            credentials.get("verify"),
            credentials.get("webhook_url"),
        )

    def __init__(
        self,
        access_token: Optional[Text],
        verify: Optional[Text],
        webhook_url: Optional[Text],
        debug_mode: bool = True,
    ) -> None:
        self.access_token = access_token
        self.verify = verify
        self.webhook_url = webhook_url
        self.debug_mode = debug_mode
        self._bot_username: Optional[Text] = None

    @staticmethod
    def _is_location(message: Any) -> bool:
        return message.location is not None

    @staticmethod
    def _is_user_message(message: Any) -> bool:
        return message.text is not None

    @staticmethod
    def _is_edited_message(message: Update) -> bool:
        return message.edited_message is not None

    @staticmethod
    def _is_button(message: Update) -> bool:
        return message.callback_query is not None

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[Any]]
    ) -> Blueprint:
        telegram_webhook = Blueprint("fixed_telegram_webhook", __name__)
        out_channel: Optional[TelegramOutput] = None

        async def ensure_output_channel() -> TelegramOutput:
            nonlocal out_channel

            if out_channel is None:
                out_channel = TelegramOutput(self.access_token)

            if self._bot_username is None:
                credentials = await out_channel.get_me()
                self._bot_username = credentials.username
                if self._bot_username != self.verify:
                    raise RasaException(
                        "Telegram verify username does not match the bot token. "
                        f"Expected '{self.verify}', got '{self._bot_username}'."
                    )

            return out_channel

        @telegram_webhook.listener("before_server_start")
        async def setup_webhook(app: Any, loop: Any) -> None:
            try:
                channel = await ensure_output_channel()
                success = await channel.set_webhook(url=self.webhook_url)
            except TelegramAPIError as error:
                raise RasaException(
                    "Failed to set channel webhook: " + str(error)
                ) from error

            if success:
                logger.info("Telegram webhook setup successful")
            else:
                raise RasaException("Telegram webhook setup failed")

        @telegram_webhook.route("/", methods=["GET"])
        async def health(_: Request) -> HTTPResponse:
            return response.json({"status": "ok"})

        @telegram_webhook.route("/set_webhook", methods=["GET", "POST"])
        async def set_webhook(_: Request) -> HTTPResponse:
            channel = await ensure_output_channel()
            success = await channel.set_webhook(self.webhook_url)
            if success:
                logger.info("Telegram webhook setup successful")
                return response.text("Webhook setup successful")

            logger.warning("Telegram webhook setup failed")
            return response.text("Invalid webhook", status=500)

        @telegram_webhook.route("/webhook", methods=["GET", "POST"])
        async def message(request: Request) -> Any:
            if request.method != "POST":
                return response.text("success")

            channel = await ensure_output_channel()

            request_dict = request.json
            if isinstance(request_dict, Text):
                request_dict = json.loads(request_dict)

            update = Update(**request_dict)
            if self._bot_username != self.verify:
                logger.debug("Invalid access token, check it matches Telegram")
                return response.text("failed")

            if self._is_button(update):
                msg = update.callback_query.message
                text = update.callback_query.data
            elif self._is_edited_message(update):
                msg = update.edited_message
                text = update.edited_message.text
            else:
                msg = update.message
                if self._is_user_message(msg):
                    text = msg.text.replace("/bot", "")
                elif self._is_location(msg):
                    text = '{{"lng":{0}, "lat":{1}}}'.format(
                        msg.location.longitude, msg.location.latitude
                    )
                else:
                    return response.text("success")

            sender_id = msg.chat.id
            metadata = self.get_metadata(request)

            try:
                if text == (INTENT_MESSAGE_PREFIX + USER_INTENT_RESTART):
                    await on_new_message(
                        UserMessage(
                            text,
                            channel,
                            sender_id,
                            input_channel=self.name(),
                            metadata=metadata,
                        )
                    )
                    await on_new_message(
                        UserMessage(
                            "/start",
                            channel,
                            sender_id,
                            input_channel=self.name(),
                            metadata=metadata,
                        )
                    )
                else:
                    await on_new_message(
                        UserMessage(
                            text,
                            channel,
                            sender_id,
                            input_channel=self.name(),
                            metadata=metadata,
                        )
                    )
            except Exception as error:
                logger.error(f"Exception when trying to handle message. {error}")
                logger.debug(error, exc_info=True)
                if self.debug_mode:
                    raise

            return response.text("success")

        return telegram_webhook
