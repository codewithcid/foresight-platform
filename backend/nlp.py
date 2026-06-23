"""Intent/sentiment classification on inbound customer messages.

This is the missing link between the WhatsApp-skin Concierge and the
marketing Strategist: right now a customer can type "stop messaging me" into
chat and the Strategist has no idea. Every inbound message gets classified
here (Groq, structured JSON output; keyword-rule fallback if the LLM is
unavailable) and the result feeds a per-customer signal the Strategist reads
before deciding to act.
"""
from __future__ import annotations

import json
import re

import llm

INTENTS = ["opt_out", "complaint", "price_objection", "sizing_question", "positive", "browsing"]

_OPT_OUT_PATTERNS = re.compile(r"\b(stop|unsubscribe|don'?t (message|text|email) me|leave me alone|no more)\b", re.I)
_NEGATIVE_WORDS = re.compile(r"\b(angry|annoyed|terrible|worst|scam|hate|ridiculous|too expensive|overpriced|never again)\b", re.I)
_PRICE_WORDS = re.compile(r"\b(expensive|price|discount|cheaper|afford|cost)\b", re.I)
_SIZE_WORDS = re.compile(r"\b(size|fit|small|large|medium|xl|measurements)\b", re.I)
_POSITIVE_WORDS = re.compile(r"\b(love|great|awesome|thanks|perfect|nice|good)\b", re.I)


def _fallback_classify(text: str) -> dict:
    if _OPT_OUT_PATTERNS.search(text):
        return {"intent": "opt_out", "sentiment": "negative", "confidence": 0.8, "source": "rules"}
    if _NEGATIVE_WORDS.search(text):
        return {"intent": "complaint", "sentiment": "negative", "confidence": 0.6, "source": "rules"}
    if _PRICE_WORDS.search(text):
        return {"intent": "price_objection", "sentiment": "neutral", "confidence": 0.6, "source": "rules"}
    if _SIZE_WORDS.search(text):
        return {"intent": "sizing_question", "sentiment": "neutral", "confidence": 0.6, "source": "rules"}
    if _POSITIVE_WORDS.search(text):
        return {"intent": "positive", "sentiment": "positive", "confidence": 0.6, "source": "rules"}
    return {"intent": "browsing", "sentiment": "neutral", "confidence": 0.4, "source": "rules"}


def classify_message(text: str) -> dict:
    system = (
        "Classify the customer message. Respond with ONLY a JSON object: "
        '{"intent": one of ' + json.dumps(INTENTS) + ', "sentiment": one of '
        '["positive","neutral","negative"], "confidence": number 0-1}. No prose, no markdown.'
    )
    raw = llm._chat(system, text, max_tokens=60, temperature=0.0)
    if raw:
        try:
            cleaned = raw.strip().strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            data = json.loads(cleaned)
            if data.get("intent") in INTENTS and data.get("sentiment") in ("positive", "neutral", "negative"):
                data["source"] = "ai"
                data["confidence"] = float(data.get("confidence", 0.7))
                return data
        except Exception as exc:  # noqa: BLE001
            print(f"[nlp] classification parse failed, using rules: {exc}")
    return _fallback_classify(text)
