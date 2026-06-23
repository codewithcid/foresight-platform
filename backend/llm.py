"""LLM layer -- Groq (OpenAI-compatible chat completions), used for every
generation task in Foresight: drafted outbound copy, concierge replies,
per-customer context summaries, CRM campaign copy, and decision explanations.

Every function has a deterministic template fallback so the demo never goes
mute without a key, network, or if Groq rate-limits mid-demo.
"""
from __future__ import annotations

import hashlib
import os
import time

import requests
from dotenv import load_dotenv

import config as C

load_dotenv(C.ROOT / "backend" / ".env")

GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# NVIDIA NIM (OpenAI-compatible) -- a pool of large models for advanced /
# strategic reasoning (analyst narratives, model card, CSV understanding). The
# high-frequency agent loop stays on fast Groq; these are for the heavyweight,
# low-frequency calls. The pool rotates on failure so a single model's rate
# limit never stalls a feature.
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
# Order = preference. The pure *instruct* models (qwen3, llama-3.3) return clean
# content; reasoning models (gpt-oss, nemotron) can leak chain-of-thought into
# the content field, so they sit last as capacity fallbacks.
NVIDIA_POOL = [
    ("qwen/qwen3-next-80b-a3b-instruct", "NVIDIA_API_KEY_QWEN"),
    ("meta/llama-3.3-70b-instruct", "NVIDIA_API_KEY_LLAMA"),
    ("openai/gpt-oss-120b", "NVIDIA_API_KEY_GPTOSS"),
    ("nvidia/nemotron-3-super-120b-a12b", "NVIDIA_API_KEY_NEMOTRON"),
]


def _strip_reasoning(text: str) -> str:
    """Defensive: drop any leaked <think>...</think> reasoning blocks."""
    import re
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()


def has_nvidia() -> bool:
    return any(os.environ.get(env) for _, env in NVIDIA_POOL)


def chat_advanced(system: str, user: str, max_tokens: int = 700, temperature: float = 0.4,
                  prefer: str | None = None) -> tuple[str | None, str]:
    """High-quality generation via the NVIDIA 120B/80B pool, rotating across
    models on failure, then falling back to Groq. Returns (text, source_model)."""
    cache_key = _cache_key("ADV|" + system, user)
    cached = _cache.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1], "cache"

    pool = sorted(NVIDIA_POOL, key=lambda mk: 0 if prefer and prefer in mk[0] else 1)
    for model, env in pool:
        key = os.environ.get(env)
        if not key:
            continue
        try:
            resp = requests.post(
                NVIDIA_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "system", "content": system},
                      {"role": "user", "content": user}], "temperature": temperature,
                      "max_tokens": max_tokens, "stream": False},
                timeout=45,
            )
            resp.raise_for_status()
            text = _strip_reasoning(resp.json()["choices"][0]["message"].get("content") or "")
            if text:
                _cache[cache_key] = (time.time(), text)
                return text, model.split("/")[-1]
        except Exception as exc:  # noqa: BLE001 - rotate to next model
            print(f"[llm] NVIDIA {model} failed, rotating: {str(exc)[:80]}")
            continue
    text = _chat(system, user, max_tokens=max_tokens, temperature=temperature)
    return (text, "groq") if text else (None, "fallback")

# Short-TTL cache so re-rendering a page (the Shop home tab calls the stylist
# and recommender on every mount) doesn't burn a fresh Groq request for an
# answer that hasn't meaningfully changed in the last few seconds. Keyed on
# the exact prompt, not on time -- this is purely about collapsing duplicate
# calls, not about staleness.
_CACHE_TTL_SECONDS = 45
_cache: dict[str, tuple[float, str]] = {}


def has_key() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def _cache_key(system: str, user: str) -> str:
    return hashlib.sha1(f"{GROQ_MODEL}|{system}|{user}".encode()).hexdigest()


def _chat(system: str, user: str, max_tokens: int = 200, temperature: float = 0.5) -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None

    cache_key = _cache_key(system, user)
    cached = _cache.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        if text:
            _cache[cache_key] = (time.time(), text)
        return text or None
    except Exception as exc:  # noqa: BLE001 - demo must never crash on LLM
        print(f"[llm] Groq call failed, using fallback: {exc}")
        return None


# ---------------------------------------------------------------------------
# Outbound marketing copy (Execution agent)
# ---------------------------------------------------------------------------
def draft_intervention_message(intervention_key: str, intervention_label: str, channel: str,
                                segment_label: str, first_name: str, predicted_rel_lift: float,
                                occasion_theme: str | None = None, product_name: str | None = None,
                                use_llm: bool = True) -> tuple[str, str]:
    # use_llm=False -> deterministic template copy, no API call. The background
    # sandbox simulator uses this so it never burns the LLM rate limit; real
    # user actions (workflows, creative, agent) keep use_llm=True.
    occasion_line = f" Tie it to the current theme: {occasion_theme}." if occasion_theme else ""
    product_line = f" Reference this specific item: {product_name}." if product_name else ""
    system = "You write short, warm, non-pushy brand messages for an Indian fashion e-commerce app. No hype words."
    user = (
        f"Write a {channel} message (1-2 sentences, no markdown) to {first_name}, a '{segment_label}' shopper "
        f"who just abandoned their cart. Intervention: {intervention_label}.{product_line}{occasion_line}"
    )
    text = _chat(system, user, max_tokens=80) if use_llm else None
    if text:
        return text, "ai"
    fallback = {
        "cart_recovery_push": f"Hi {first_name}, you left something behind — want to finish checking out?",
        "personalized_email": f"Hi {first_name}, based on what you've browsed, we picked a few things you might like.",
        "sms_discount": f"Hi {first_name}, here's 10% off to complete your order today.",
        "retargeting_social": f"Still thinking it over, {first_name}? Here's a reminder of what you viewed.",
    }
    return fallback.get(intervention_key, f"Hi {first_name}, following up on your recent visit."), "template"


# ---------------------------------------------------------------------------
# Concierge replies (cross-channel chat)
# ---------------------------------------------------------------------------
def concierge_reply(first_name: str, segment_label: str, channel: str, context_summary: str,
                     user_message: str, history: list[dict] | None = None) -> tuple[str, str]:
    system = (
        "You are the Mela Style Assistant, a cross-channel customer concierge for an Indian fashion brand. "
        "You have ONE memory across every channel the customer uses (the website, WhatsApp, email). Use the "
        "context -- including anything from OTHER channels -- to answer naturally, briefly (2-3 sentences), "
        "and helpfully. Never invent order or product details that aren't in the context."
    )
    user = (
        f"Customer: {first_name} ({segment_label})\nCurrent channel: {channel}\n"
        f"Cross-channel history:\n{context_summary}\n\nCustomer's new message: {user_message}\n"
    )
    text = _chat(system, user, max_tokens=160)
    if text:
        return text, "ai"
    last_other = None
    for m in reversed(history or []):
        is_dict = isinstance(m, dict)
        ch = m.get("channel") if is_dict else m.channel
        role = m.get("role") if is_dict else m.role
        meta = m.get("meta") if is_dict else m.meta
        txt = m.get("text") if is_dict else m.text
        if ch != channel and role == "agent" and not (meta or {}).get("continuity"):
            last_other = txt
            break
    if last_other:
        fallback = (f"Hi {first_name}, picking up where we left off — earlier I mentioned: "
                    f"\"{last_other}\". How can I help from here?")
    else:
        fallback = f"Hi {first_name}, thanks for reaching out on {channel} — how can I help?"
    return fallback, "template"


# ---------------------------------------------------------------------------
# Proactive outreach on a conversational channel (e.g. WhatsApp), distinct
# from a marketing blast -- this is the agent initiating, not replying.
# ---------------------------------------------------------------------------
def proactive_concierge_message(first_name: str, segment_label: str, trigger: str,
                                  product_name: str | None, occasion_theme: str | None) -> tuple[str, str]:
    system = "You write a short, friendly proactive WhatsApp-style message from a fashion brand's AI assistant. No hype words, no emoji spam (max one emoji)."
    extra = f" The item in question: {product_name}." if product_name else ""
    occ = f" Current theme: {occasion_theme}." if occasion_theme else ""
    user = f"Customer: {first_name} ({segment_label}). Trigger: {trigger}.{extra}{occ} Write the opening message."
    text = _chat(system, user, max_tokens=80)
    if text:
        return text, "ai"
    return (f"Hi {first_name}! Noticed you were checking out "
            f"{product_name or 'something nice'} — want a hand completing it?"), "template"


# ---------------------------------------------------------------------------
# Context summarizer -- condenses a customer's raw cross-channel + behavior
# history into a compact profile other agents consume instead of raw logs.
# ---------------------------------------------------------------------------
def summarize_context(first_name: str, segment_label: str, behavior_lines: list[str],
                       conversation_lines: list[str]) -> tuple[str, str]:
    system = "You are a context-compaction agent. Summarize in 2-3 sentences, plain prose, no markdown, no invented facts."
    user = (
        f"Customer: {first_name} ({segment_label}).\n"
        f"Recent behavior:\n" + "\n".join(behavior_lines[-12:]) + "\n\n"
        f"Recent conversation (all channels):\n" + "\n".join(conversation_lines[-12:]) + "\n\n"
        "Summarize who this customer is right now and what they likely want."
    )
    text = _chat(system, user, max_tokens=140)
    if text:
        return text, "ai"
    tags = behavior_lines[-3:]
    fallback = f"{first_name} ({segment_label}) — recent activity: {'; '.join(tags) if tags else 'no recent activity'}."
    return fallback, "template"


# ---------------------------------------------------------------------------
# CRM campaign copy (occasion-aware)
# ---------------------------------------------------------------------------
def draft_campaign_copy(occasion_label: str, theme: str, product_names: list[str],
                         segment_label: str) -> tuple[str, str]:
    system = "You write short Indian e-commerce CRM campaign copy: punchy subject line + 1-2 line body. No markdown."
    user = (
        f"Occasion: {occasion_label}. Theme: {theme}. Target segment: {segment_label}. "
        f"Hero products: {', '.join(product_names[:3])}. Write 'Subject: ...' then 'Body: ...'."
    )
    text = _chat(system, user, max_tokens=120)
    if text:
        return text, "ai"
    fallback = f"Subject: {theme} is here!\nBody: Shop the {occasion_label} edit, picked for {segment_label} shoppers."
    return fallback, "template"


# ---------------------------------------------------------------------------
# Explainability -- plain-English narrative on top of the structured factor
# breakdown the dashboard already computes.
# ---------------------------------------------------------------------------
# Tool-capable models (clean OpenAI tool-calling on NIM), preferred order.
NVIDIA_TOOL_POOL = [
    ("meta/llama-3.3-70b-instruct", "NVIDIA_API_KEY_LLAMA"),
    ("qwen/qwen3-next-80b-a3b-instruct", "NVIDIA_API_KEY_QWEN"),
    ("openai/gpt-oss-120b", "NVIDIA_API_KEY_GPTOSS"),
]


def chat_with_tools(messages: list[dict], tools: list[dict], max_tokens: int = 700) -> dict | None:
    """Tool-calling for the Supervisor's ReAct loop. Tries the NVIDIA pool
    (capable models, fresh quota) and falls back to Groq. Returns the raw
    OpenAI-format response dict, or None if every provider fails."""
    for model, env in NVIDIA_TOOL_POOL:
        key = os.environ.get(env)
        if not key:
            continue
        try:
            resp = requests.post(
                NVIDIA_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "tools": tools, "tool_choice": "auto",
                      "temperature": 0.2, "max_tokens": max_tokens, "stream": False},
                timeout=45,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - rotate to next provider
            print(f"[llm] NVIDIA {model} tool-call failed, rotating: {str(exc)[:80]}")
            continue
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "tools": tools, "tool_choice": "auto",
                  "temperature": 0.2, "max_tokens": max_tokens},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        print(f"[llm] Groq tool-calling fallback failed: {exc}")
        return None


def style_rationale(first_name: str, segment_label: str, occasion_label: str | None,
                     item_names: list[str]) -> tuple[str, str]:
    system = "You are a fashion stylist for an Indian clothing brand. In 2 sentences, explain why these pieces work together as a look. No markdown, no invented items."
    occ = f" for {occasion_label}" if occasion_label else ""
    user = f"Customer: {first_name} ({segment_label}). Look{occ}: {', '.join(item_names)}."
    text = _chat(system, user, max_tokens=100)
    if text:
        return text, "ai"
    return (f"A {('' if not occasion_label else occasion_label + ' ')}look built around "
            f"{', '.join(item_names)} — picked to match {first_name}'s taste profile."), "template"


def draft_support_reply(first_name: str, segment_label: str, subject: str, body: str, case_type: str,
                         policy_title: str | None, policy_text: str | None, context_summary: str) -> tuple[str, str]:
    system = (
        "You are a customer support agent for an Indian fashion e-commerce brand, drafting an email "
        "reply for a human support rep to review and send. Be empathetic, concise, and state next steps "
        "clearly. Ground your reply ONLY in the policy provided -- do not invent refund amounts, "
        "timelines, or terms not in the policy. If no policy is given, ask a clarifying question instead "
        "of guessing."
    )
    policy_block = f"Applicable policy ({policy_title}): {policy_text}" if policy_text else "No specific policy matched -- ask a clarifying question."
    user = (
        f"Customer: {first_name} ({segment_label}).\n"
        f"Case type: {case_type}\nSubject: {subject}\nCustomer's email:\n{body}\n\n"
        f"{policy_block}\n\nCustomer context (other channels):\n{context_summary}\n\n"
        "Write the reply email body only (no subject line, no markdown)."
    )
    text = _chat(system, user, max_tokens=220)
    if text:
        return text, "ai"
    fallback = (
        f"Hi {first_name},\n\nThanks for reaching out. "
        + (f"Per our policy: {policy_text}" if policy_text else "Could you share a bit more detail so we can help?")
        + "\n\nLet us know if you have any other questions.\n\nBest,\nCustomer Support"
    )
    return fallback, "template"


def explain_decision(factors: dict) -> tuple[str, str]:
    system = "You are an explainable-AI narrator. In 2 sentences, explain a marketing AI's decision using ONLY the given factors. No invented numbers."
    user = "Factors:\n" + "\n".join(f"- {k}: {v}" for k, v in factors.items())
    text = _chat(system, user, max_tokens=120)
    if text:
        return text, "ai"
    return (f"Predicted lift {factors.get('predicted_rel_lift', '?')} drove the choice of "
            f"{factors.get('intervention_label', 'this action')}; occasion match: "
            f"{factors.get('occasion_match', 'none')}; guardrails: {factors.get('guardrail_status', 'ok')}."), "template"
