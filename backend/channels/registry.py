"""Channel registry: the single list of delivery channels + their live status.

All five are real adapters (SMS, WhatsApp, Slack, Email, Telegram); each reports
live / sandbox / needs_key from whether its env keys are present, so the same
agent + workflow code delivers across any of them.
"""
from __future__ import annotations

from .base import Channel
from .email_resend import Email
from .slack import Slack
from .telegram import Telegram
from .twilio_sms import TwilioSMS
from .twilio_whatsapp import TwilioWhatsApp


_CHANNELS: dict[str, Channel] = {
    c.id: c
    for c in [
        TwilioSMS(),
        TwilioWhatsApp(),
        Slack(),
        Email(),
        Telegram(),
    ]
}


def all_channels() -> list[Channel]:
    return list(_CHANNELS.values())


def get_channel(channel_id: str) -> Channel | None:
    return _CHANNELS.get(channel_id)


def status_list() -> list[dict]:
    return [c.status() for c in _CHANNELS.values()]
