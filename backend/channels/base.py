"""Common channel interface + delivery result."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DeliveryResult:
    ok: bool
    channel: str
    to: str
    provider_id: str = ""
    error: str = ""
    sandbox: bool = False

    def as_dict(self) -> dict:
        return {
            "ok": self.ok, "channel": self.channel, "to": self.to,
            "provider_id": self.provider_id, "error": self.error, "sandbox": self.sandbox,
        }


class Channel:
    """Base channel. Subclasses set id/label/kind and implement configured()/send()."""

    id: str = ""
    label: str = ""
    kind: str = ""          # sms | whatsapp | email | chat
    icon: str = "ri-send-plane-line"
    needs: list[str] = []   # env var names required to go live

    def configured(self) -> bool:
        raise NotImplementedError

    def sandbox(self) -> bool:
        """Live but using a shared/test sender (e.g. Twilio WhatsApp sandbox)."""
        return False

    def send(self, to: str, body: str, meta: dict | None = None) -> DeliveryResult:
        raise NotImplementedError

    def status(self) -> dict:
        configured = self.configured()
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "icon": self.icon,
            "configured": configured,
            "sandbox": self.sandbox() if configured else False,
            "mode": ("sandbox" if (configured and self.sandbox()) else "live") if configured else "needs_key",
            "needs": self.needs,
        }
