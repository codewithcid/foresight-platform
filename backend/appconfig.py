"""Runtime configuration resolver.

Lets the app be configured from the UI (stored in the SQLite `settings` table)
*or* from environment variables — DB value wins, env is the fallback. This is
what turns Foresight from a `.env`-only demo into a product you connect in-app.
"""
from __future__ import annotations

import os

import db

# Keys treated as secrets (masked when returned to the UI).
SECRET_KEYS = {
    "GROQ_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
    "SLACK_BOT_TOKEN", "RESEND_API_KEY", "TELEGRAM_BOT_TOKEN",
    "NVIDIA_API_KEY_QWEN", "NVIDIA_API_KEY_LLAMA", "NVIDIA_API_KEY_GPTOSS", "NVIDIA_API_KEY_NEMOTRON",
}


def get(key: str, default: str | None = None) -> str | None:
    v = db.get_setting(key)
    if v:
        return v
    return os.environ.get(key, default)


def is_set(key: str) -> bool:
    return bool(get(key))


def set_many(updates: dict) -> None:
    for k, v in updates.items():
        db.set_setting(k, "" if v is None else str(v))


def masked(key: str) -> str:
    v = get(key)
    if not v:
        return ""
    return ("•" * max(0, len(v) - 4)) + v[-4:] if len(v) > 4 else "••••"
