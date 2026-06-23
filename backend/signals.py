"""Per-customer conversational signal, fed by nlp.classify_message() on every
inbound WhatsApp/chat message. The Strategist reads this before deciding to
act -- this is the actual wiring between the Concierge and the marketing
agent that didn't exist before.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ConversationSignal:
    intent: str = "browsing"
    sentiment: str = "neutral"
    confidence: float = 0.0
    opt_out: bool = False
    updated_at: float = field(default_factory=time.time)
    history: list[dict] = field(default_factory=list)

    def should_suppress_marketing(self) -> tuple[bool, str]:
        if self.opt_out:
            return True, "customer opted out via chat ('stop messaging me')"
        if self.sentiment == "negative" and (time.time() - self.updated_at) < 3600:
            return True, f"recent negative sentiment in chat (intent: {self.intent})"
        return False, ""


class SignalRegistry:
    def __init__(self):
        self._signals: dict[str, ConversationSignal] = {}

    def get(self, customer_id: str) -> ConversationSignal:
        if customer_id not in self._signals:
            self._signals[customer_id] = ConversationSignal()
        return self._signals[customer_id]

    def record(self, customer_id: str, text: str, classification: dict) -> ConversationSignal:
        sig = self.get(customer_id)
        sig.intent = classification["intent"]
        sig.sentiment = classification["sentiment"]
        sig.confidence = classification.get("confidence", 0.5)
        sig.updated_at = time.time()
        if classification["intent"] == "opt_out":
            sig.opt_out = True
        sig.history.append({"text": text, **classification, "ts": sig.updated_at})
        sig.history = sig.history[-20:]
        return sig

    def all(self) -> dict[str, ConversationSignal]:
        return self._signals
