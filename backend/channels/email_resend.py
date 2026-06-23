"""Real transactional email via Resend (resend.com — free tier, simple API).

Needs RESEND_API_KEY. The sender defaults to Resend's shared onboarding address
(works for testing to your own verified email); set RESEND_FROM to a verified-
domain address for arbitrary recipients. Subject comes from meta['subject'] or a
default; the body is sent as plain text.
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

import config as C
from .base import Channel, DeliveryResult

load_dotenv(C.ROOT / "backend" / ".env")

API = "https://api.resend.com/emails"
DEFAULT_FROM = "Foresight <onboarding@resend.dev>"


def _key() -> str:
    return os.environ.get("RESEND_API_KEY", "")


class Email(Channel):
    id = "email"
    label = "Email"
    kind = "email"
    icon = "ri-mail-line"
    needs = ["RESEND_API_KEY"]
    hint = "Add a Resend API key (resend.com) to send real email."

    def configured(self) -> bool:
        return bool(_key())

    def sandbox(self) -> bool:
        # Using the shared onboarding sender = restricted to your own verified inbox.
        return bool(_key()) and not os.environ.get("RESEND_FROM")

    def send(self, to: str, body: str, meta: dict | None = None) -> DeliveryResult:
        if not _key():
            return DeliveryResult(ok=False, channel=self.id, to=to, error="Email not configured (RESEND_API_KEY).")
        subject = (meta or {}).get("subject") or "A note from Foresight"
        sender = os.environ.get("RESEND_FROM") or DEFAULT_FROM
        try:
            r = requests.post(API, headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
                              json={"from": sender, "to": [to], "subject": subject, "text": body}, timeout=15)
            data = r.json()
            if r.status_code in (200, 201) and data.get("id"):
                return DeliveryResult(ok=True, channel=self.id, to=to, provider_id=data["id"], sandbox=self.sandbox())
            return DeliveryResult(ok=False, channel=self.id, to=to,
                                  error=(data.get("message") or data.get("error") or f"Resend error {r.status_code}"))
        except Exception as e:
            return DeliveryResult(ok=False, channel=self.id, to=to, error=f"Resend request failed: {e}")

    def status(self) -> dict:
        return {**super().status(), "hint": self.hint}
