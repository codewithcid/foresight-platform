"""Shared Twilio REST helper (no SDK dependency — just `requests`).

Reads creds from the same backend/.env the rest of the app uses. SMS and
WhatsApp share one account; they differ only in the `From`/`To` prefix.
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

import config as C

load_dotenv(C.ROOT / "backend" / ".env")

API = "https://api.twilio.com/2010-04-01"
# Twilio's public WhatsApp sandbox sender — used if no dedicated number is set.
WHATSAPP_SANDBOX_FROM = "whatsapp:+14155238886"


def sid() -> str:
    return os.environ.get("TWILIO_ACCOUNT_SID", "")


def token() -> str:
    return os.environ.get("TWILIO_AUTH_TOKEN", "")


def has_account() -> bool:
    return bool(sid() and token())


def send_message(from_: str, to: str, body: str) -> tuple[bool, str, str]:
    """POST a message to Twilio. Returns (ok, provider_sid, error)."""
    if not has_account():
        return False, "", "Twilio account not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN)."
    if not from_:
        return False, "", "No sender configured for this channel."
    try:
        resp = requests.post(
            f"{API}/Accounts/{sid()}/Messages.json",
            data={"From": from_, "To": to, "Body": body},
            auth=(sid(), token()),
            timeout=15,
        )
        data = resp.json()
        if resp.status_code in (200, 201):
            return True, data.get("sid", ""), ""
        return False, "", data.get("message", f"Twilio error {resp.status_code}")
    except Exception as e:  # network / parse
        return False, "", f"Twilio request failed: {e}"
