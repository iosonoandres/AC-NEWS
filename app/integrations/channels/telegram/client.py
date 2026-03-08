import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, bot_token: str, timeout_seconds: float = 10.0) -> None:
        self.bot_token = bot_token.strip()
        self.timeout_seconds = timeout_seconds
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    async def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None) -> bool:
        payload: dict = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        data = await self._post("sendMessage", payload)
        return bool(data and data.get("ok"))

    async def send_photo(
        self,
        chat_id: int,
        photo_url: str,
        caption: str,
        reply_markup: dict | None = None,
    ) -> bool:
        payload: dict = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024],
            "parse_mode": "HTML",
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        data = await self._post("sendPhoto", payload)
        return bool(data and data.get("ok"))

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> None:
        payload: dict = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text:
            payload["text"] = text

        await self._post("answerCallbackQuery", payload)

    async def _post(self, method: str, payload: dict) -> dict | None:
        if not self.bot_token:
            logger.error("Telegram token is missing. Set TELEGRAM_BOT_TOKEN.")
            return None

        url = f"{self.api_base}/{method}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                if not data.get("ok"):
                    logger.error("Telegram API returned error for %s: %s", method, data)
                return data
        except Exception as exc:  # noqa: BLE001
            logger.exception("Telegram API call failed for %s: %s", method, exc)
            return None
