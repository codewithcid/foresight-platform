"""Real WhatsApp over Twilio (dedicated number, or the shared public sandbox)."""
from __future__ import annotations

import appconfig
from . import _twilio
from .base import Channel, DeliveryResult


def _wa(addr: str) -> str:
    """Ensure a `whatsapp:` prefix on an E.164 number."""
    addr = addr.strip()
    return addr if addr.startswith("whatsapp:") else f"whatsapp:{addr}"


class TwilioWhatsApp(Channel):
    id = "whatsapp"
    label = "WhatsApp"
    kind = "whatsapp"
    icon = "ri-whatsapp-line"
    needs = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]

    def _from(self) -> str:
        # Dedicated number if provided, else the public Twilio sandbox sender.
        return appconfig.get("TWILIO_WHATSAPP_FROM", "") or _twilio.WHATSAPP_SANDBOX_FROM

    def configured(self) -> bool:
        return _twilio.has_account()

    def sandbox(self) -> bool:
        return not appconfig.get("TWILIO_WHATSAPP_FROM")

    def send(self, to: str, body: str, meta: dict | None = None) -> DeliveryResult:
        ok, pid, err = _twilio.send_message(_wa(self._from()), _wa(to), body)
        return DeliveryResult(ok=ok, channel=self.id, to=to, provider_id=pid, error=err, sandbox=self.sandbox())
