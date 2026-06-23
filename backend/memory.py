"""Cross-channel memory: one thread per customer, written to by both the
Strategist's outbound marketing actions AND the Concierge's conversations on
any channel. This is the literal mechanism behind "seamless across
channels" -- there's exactly one memory, and every channel reads/writes it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Message:
    channel: str       # e.g. "sms", "web_chat", "whatsapp", "email_support"
    role: str          # "agent" | "customer" | "system"
    text: str
    ts: float = field(default_factory=time.time)
    meta: dict = field(default_factory=dict)


class MemoryStore:
    def __init__(self):
        self._threads: dict[str, list[Message]] = {}

    def append(self, customer_id: str, channel: str, role: str, text: str, meta: dict | None = None) -> Message:
        msg = Message(channel=channel, role=role, text=text, meta=meta or {})
        self._threads.setdefault(customer_id, []).append(msg)
        return msg

    def history(self, customer_id: str, limit: int = 40) -> list[Message]:
        return self._threads.get(customer_id, [])[-limit:]

    def context_summary(self, customer_id: str, limit: int = 8) -> str:
        """Compact cross-channel summary fed into LLM prompts so the agent can
        reference something that happened on a *different* channel."""
        hist = self.history(customer_id, limit=limit)
        if not hist:
            return "No prior interaction history."
        lines = []
        for m in hist:
            who = {"agent": "Agent", "customer": "Customer", "system": "System"}.get(m.role, m.role)
            lines.append(f"[{m.channel}] {who}: {m.text}")
        return "\n".join(lines)
