import asyncio
from telegram import Bot as TBot


class Bot(TBot):
    def __init__(self, token: str):
        super().__init__(token=token)

    def send_message(self, chat_id: str, text: str, *args, **kwargs) -> None:
        async def _send():
            await super(Bot, self).send_message(chat_id=chat_id, text=text, *args, **kwargs)

        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(_send())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_send())
