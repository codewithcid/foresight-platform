"""Novu channel — delivers by triggering a Novu workflow (provider-agnostic).

The actual channel (WhatsApp / SMS / email / push / in-app) is decided by the
workflow you configure in Novu, so Foresight stays out of provider details.
"""
from __future__ import annotations

import appconfig
import novu
from .base import Channel, DeliveryResult


class Novu(Channel):
    id = "novu"
    label = "Novu"
    kind = "chat"
    icon = "ri-notification-3-line"
    needs = ["NOVU_API_KEY", "NOVU_WORKFLOW_ID"]

    def configured(self) -> bool:
        return novu.configured()

    def sandbox(self) -> bool:
        # Live as soon as the key is set; what it does is up to your Novu workflow.
        return False

    def send(self, to: str, body: str, meta: dict | None = None) -> DeliveryResult:
        meta = meta or {}
        subscriber = meta.get("subscriber_id") or to or "foresight-user"
        payload = {"body": body, **(meta.get("payload") or {})}
        ok, tx, err = novu.trigger(subscriber, payload, phone=to or None, email=meta.get("email"))
        return DeliveryResult(ok=ok, channel=self.id, to=to, provider_id=tx, error=err)
