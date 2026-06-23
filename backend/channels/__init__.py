"""Real outbound channels for Foresight.

Each channel implements the same `Channel` interface (id / label / configured /
status / send). The registry exposes which are live vs. need a key, so the same
agent + workflow code can deliver across SMS, WhatsApp, and (stubbed) email /
Slack / Telegram without caring which is which — that's the "seamless
cross-channel" half of Theme 2, made real instead of skinned.
"""
from .base import Channel, DeliveryResult
from .registry import all_channels, get_channel, status_list

__all__ = ["Channel", "DeliveryResult", "all_channels", "get_channel", "status_list"]
