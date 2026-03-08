from typing import Protocol


class ChannelClient(Protocol):
    async def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        ...
