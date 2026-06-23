"""Real SMS over Twilio."""
from __future__ import annotations

import os

from . import _twilio
from .base import Channel, DeliveryResult


class TwilioSMS(Channel):
    id = "sms"
    label = "SMS"
    kind = "sms"
    icon = "ri-message-2-line"
    needs = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_SMS_FROM"]

    def _from(self) -> str:
        return os.environ.get("TWILIO_SMS_FROM", "")

    def configured(self) -> bool:
        return _twilio.has_account() and bool(self._from())

    def send(self, to: str, body: str, meta: dict | None = None) -> DeliveryResult:
        ok, pid, err = _twilio.send_message(self._from(), to, body)
        return DeliveryResult(ok=ok, channel=self.id, to=to, provider_id=pid, error=err)
