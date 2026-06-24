"""Wati (WhatsApp Business API) client — used by the admin chatbot.

Wati POSTs incoming messages to our webhook; we reply with a *session* message
(allowed free-form because the admin messaged first, opening the 24h window).

Config (Settings -> Admin WhatsApp bot):
  WATI_BASE_URL     e.g. https://live-mt-server.wati.io/<tenantId>  (from Wati -> API Docs)
  WATI_ACCESS_TOKEN the Bearer token from Wati -> API Docs
"""
from __future__ import annotations

import re
import requests

import appconfig


def configured() -> bool:
    return bool(appconfig.get("WATI_BASE_URL") and appconfig.get("WATI_ACCESS_TOKEN"))


def _base() -> str:
    return (appconfig.get("WATI_BASE_URL") or "").rstrip("/")


def _auth() -> str:
    tok = (appconfig.get("WATI_ACCESS_TOKEN") or "").strip()
    return tok if tok.lower().startswith("bearer ") else f"Bearer {tok}"


def normalize(number: str) -> str:
    """Wati wants the bare international number (digits only)."""
    return re.sub(r"\D", "", number or "")


def send_session_message(wa_id: str, text: str) -> tuple[bool, str]:
    """Send a free-form session message. Returns (ok, error)."""
    if not configured():
        return False, "Wati not configured"
    num = normalize(wa_id)
    if not num:
        return False, "no recipient"
    url = f"{_base()}/api/v1/sendSessionMessage/{num}"
    try:
        r = requests.post(url, params={"messageText": text},
                          headers={"Authorization": _auth(), "Content-Type": "application/json"},
                          timeout=15)
    except requests.RequestException as e:
        return False, f"wati request failed: {e}"
    if r.status_code in (200, 201):
        try:
            data = r.json()
        except ValueError:
            return True, ""
        msg = data.get("message") or {}
        if msg.get("whatsappMessageId"):
            return True, ""
        # Wati accepted the call (result:success) but couldn't deliver — almost
        # always because the 24h customer-initiated session isn't open.
        return False, "no open 24h WhatsApp session — the recipient must message the business number first"
    return False, f"wati {r.status_code}: {r.text[:200]}"
