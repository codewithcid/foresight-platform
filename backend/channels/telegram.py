"""Real Telegram channel via the Bot API (free, no billing).

Create a bot with @BotFather to get TELEGRAM_BOT_TOKEN. A bot can only message a
user/chat that has messaged it first — the recipient is a numeric chat_id (the
`to` arg, or TELEGRAM_CHAT_ID as the default for workflow delivery).
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

import config as C
from .base import Channel, DeliveryResult

load_dotenv(C.ROOT / "backend" / ".env")


def _token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


class Telegram(Channel):
    id = "telegram"
    label = "Telegram"
    kind = "chat"
    icon = "ri-telegram-line"
    needs = ["TELEGRAM_BOT_TOKEN"]
    hint = "Create a bot via @BotFather, then message it once so it can reply."

    def configured(self) -> bool:
        return bool(_token())

    def send(self, to: str, body: str, meta: dict | None = None) -> DeliveryResult:
        chat_id = (to or os.environ.get("TELEGRAM_CHAT_ID", "")).strip()
        if not _token():
            return DeliveryResult(ok=False, channel=self.id, to=chat_id, error="Telegram not configured (TELEGRAM_BOT_TOKEN).")
        if not chat_id:
            return DeliveryResult(ok=False, channel=self.id, to="", error="No chat_id — message the bot once, or set TELEGRAM_CHAT_ID.")
        try:
            r = requests.post(f"https://api.telegram.org/bot{_token()}/sendMessage",
                              json={"chat_id": chat_id, "text": body}, timeout=15)
            data = r.json()
            if data.get("ok"):
                return DeliveryResult(ok=True, channel=self.id, to=chat_id,
                                      provider_id=str(data.get("result", {}).get("message_id", "")))
            return DeliveryResult(ok=False, channel=self.id, to=chat_id, error=data.get("description", "telegram error"))
        except Exception as e:
            return DeliveryResult(ok=False, channel=self.id, to=chat_id, error=f"Telegram request failed: {e}")

    def status(self) -> dict:
        return {**super().status(), "hint": self.hint}
