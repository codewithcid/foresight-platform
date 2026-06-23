"""Synthetic-persona pre-test -- the second half of the self-testing creative loop.

Inspired by AdWise (last year's winning project): instead of A/B testing live
creative on real customers and paying for the loser, a panel of synthetic
shopper personas reacts to each candidate variant and scores its predicted
resonance (0-100) BEFORE anything is sent. The winner is the variant with the
highest predicted resonance for the target segment.

This is the "predicted" side of the creative proof: Phase 3's Critic later
compares this predicted resonance to the variant's actual engagement, extending
Foresight's predicted-vs-actual spine from the *intervention* to the *creative*.

One Groq call scores the whole panel x all variants (cheap, fast); a fully
deterministic heuristic scorer is the fallback so the demo never stalls.
"""
from __future__ import annotations

import hashlib
import json

import llm

# Fixed synthetic panel -- "users that don't exist" giving honest reactions.
PERSONAS = [
    {"name": "Meena", "blurb": "38, deal-driven homemaker; compares prices, responds to savings and urgency, distrusts hype"},
    {"name": "Aarav", "blurb": "27, brand-conscious young professional; aspirational, loves premium framing, dislikes pushy discounts"},
    {"name": "Lakshmi", "blurb": "45, busy working mother; values clarity and convenience over flash, skims fast"},
]

# How strongly each copy angle lands with each customer segment (heuristic prior,
# also used as the deterministic fallback when Groq is unavailable).
_ANGLE_SEGMENT_FIT = {
    "Urgency":    {"bargain_hunter": 0.85, "loyalist": 0.45, "browser": 0.60, "high_intent": 0.80},
    "Value":      {"bargain_hunter": 0.90, "loyalist": 0.55, "browser": 0.65, "high_intent": 0.60},
    "Aspiration": {"bargain_hunter": 0.40, "loyalist": 0.85, "browser": 0.70, "high_intent": 0.75},
}
_SEGMENT_KEY_BY_LABEL = {
    "Bargain Hunter": "bargain_hunter", "Loyalist": "loyalist",
    "Browser": "browser", "High Intent": "high_intent",
}


# Persona-specific reaction voices (deterministic fallback flavor), by score band.
_PERSONA_VOICE = {
    "Meena": {"hi": "The savings angle hooks me - I'd tap through.",
              "mid": "Decent, but I'd still compare prices first.",
              "lo": "Not enough of a deal to pull me in."},
    "Aarav": {"hi": "Feels premium and aspirational - on-brand for me.",
              "mid": "Fine, a touch generic for my taste.",
              "lo": "Reads pushy; I'd scroll right past it."},
    "Lakshmi": {"hi": "Clear and quick - I get it at a glance.",
                "mid": "Okay, though I'd want it shorter.",
                "lo": "Too vague; I don't have time to decode it."},
}


def _heuristic_scores(variants: list[dict], segment_label: str) -> list[dict]:
    seg = _SEGMENT_KEY_BY_LABEL.get(segment_label, "browser")
    out = []
    for v in variants:
        fit = _ANGLE_SEGMENT_FIT.get(v["angle"], {}).get(seg, 0.6)
        per = []
        for p in PERSONAS:
            # deterministic per-(variant,persona) jitter so the panel isn't flat
            h = int(hashlib.sha1(f"{v['id']}|{p['name']}".encode()).hexdigest()[:6], 16) % 17
            score = int(max(5, min(98, round(fit * 100 + (h - 8)))))
            band = "hi" if score >= 70 else ("mid" if score >= 50 else "lo")
            reaction = _PERSONA_VOICE.get(p["name"], {}).get(band, "")
            per.append({"name": p["name"], "score": score, "reaction": reaction})
        mean = round(sum(x["score"] for x in per) / len(per), 1)
        out.append({"variant_id": v["id"], "angle": v["angle"], "mean_score": mean, "per_persona": per})
    return out


def pretest(variants: list[dict], segment_label: str, occasion_theme: str | None = None) -> dict:
    """Score every variant against the synthetic panel; return ranked results + winner."""
    method = "heuristic"
    scored: list[dict] | None = None

    persona_block = "\n".join(f"- {p['name']}: {p['blurb']}" for p in PERSONAS)
    variant_block = "\n".join(f"{v['id']} [{v['angle']}]: {v['copy']}" for v in variants)
    system = (
        "You simulate a panel of synthetic shopper personas reacting to draft ad copy, "
        "for pre-launch testing. For each persona and each variant, give an honest predicted "
        "resonance score 0-100 (how likely this persona is to engage/convert) and a 6-10 word "
        "reaction. Be discriminating -- spread the scores. Respond ONLY with JSON."
    )
    occ = f" Occasion: {occasion_theme}." if occasion_theme else ""
    user = (
        f"Target segment: {segment_label}.{occ}\nPanel:\n{persona_block}\n\nVariants:\n{variant_block}\n\n"
        'Return JSON: [{"variant_id":..., "per_persona":[{"name":..., "score":0-100, "reaction":...}]}]'
    )
    raw = llm._chat(system, user, max_tokens=700, temperature=0.4)
    if raw:
        try:
            txt = raw.strip()
            if txt.startswith("```"):
                txt = txt.strip("`").lstrip("json").strip()
            data = json.loads(txt)
            by_id = {d["variant_id"]: d for d in data}
            built = []
            for v in variants:
                d = by_id.get(v["id"])
                if not d:
                    raise ValueError(f"missing scores for {v['id']}")
                per = [{"name": str(x["name"]), "score": int(x["score"]), "reaction": str(x.get("reaction", ""))}
                       for x in d["per_persona"]]
                mean = round(sum(x["score"] for x in per) / len(per), 1)
                built.append({"variant_id": v["id"], "angle": v["angle"], "mean_score": mean, "per_persona": per})
            scored = built
            method = "ai"
        except Exception as exc:  # noqa: BLE001
            print(f"[pre_test] panel parse failed, using heuristic: {exc}")

    if scored is None:
        scored = _heuristic_scores(variants, segment_label)

    scored.sort(key=lambda s: s["mean_score"], reverse=True)
    winner = scored[0]
    spread = round(scored[0]["mean_score"] - scored[-1]["mean_score"], 1) if len(scored) > 1 else 0.0
    return {
        "personas": PERSONAS,
        "scores": scored,
        "winner_id": winner["variant_id"],
        "winner_angle": winner["angle"],
        "winner_score": winner["mean_score"],
        "spread": spread,
        "method": method,
    }
