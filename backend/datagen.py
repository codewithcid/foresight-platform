"""Synthetic customer + journey generator with a known ground-truth treatment
effect (so predicted-vs-actual validation is possible), PLUS a chronological
event stream so the data can be replayed live instead of consumed as a static
batch. This is the key structural change from the original Foresight dummy:
the dataset is a *timeline to live through*, not a table to chart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config as C
import occasions as O


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


TAU_BASE = {
    "cart_recovery_push": {"bargain_hunter": 0.10, "loyalist": 0.03, "browser": 0.05, "high_intent": 0.14},
    "personalized_email": {"bargain_hunter": 0.05, "loyalist": 0.10, "browser": 0.08, "high_intent": 0.06},
    "sms_discount":       {"bargain_hunter": 0.12, "loyalist": 0.02, "browser": 0.04, "high_intent": 0.08},
    "retargeting_social": {"bargain_hunter": 0.04, "loyalist": 0.04, "browser": 0.11, "high_intent": 0.05},
}


def true_tau(intervention: str, segment: np.ndarray, price_sensitivity: np.ndarray) -> np.ndarray:
    base = np.array([TAU_BASE[intervention][s] for s in segment])
    if intervention == "sms_discount":
        base = base * (0.5 + price_sensitivity)
    elif intervention == "cart_recovery_push":
        base = base * (1.2 - 0.4 * price_sensitivity)
    return base


def generate_customers(n: int = C.N_CUSTOMERS, seed: int = C.SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    seg_keys = C.SEGMENT_KEYS
    seg_probs = np.array([C.SEGMENTS[k]["prop"] for k in seg_keys])
    seg_probs = seg_probs / seg_probs.sum()
    segment = rng.choice(seg_keys, size=n, p=seg_probs)

    engagement = rng.beta(2.0, 2.0, size=n)
    price_sensitivity = rng.beta(2.0, 2.0, size=n)
    first_name = rng.choice(
        ["Aanya", "Rohan", "Mira", "Kabir", "Zoe", "Liam", "Sara", "Devan",
         "Priya", "Omar", "Lena", "Theo", "Nadia", "Ishaan", "Maya", "Eli"], size=n)
    customer_id = np.array([f"C{100000+i}" for i in range(n)])

    seg_intent_offset = {"bargain_hunter": -0.1, "loyalist": 0.3, "browser": -0.4, "high_intent": 0.8}
    intent_off = np.array([seg_intent_offset[s] for s in segment])
    p_consideration = _sigmoid(1.1 + 1.4 * (engagement - 0.5))
    reached_consideration = rng.random(n) < p_consideration
    p_intent = _sigmoid(0.65 + 1.6 * (engagement - 0.5) + intent_off)
    reached_intent = reached_consideration & (rng.random(n) < p_intent)

    seg_purchase_offset = {"bargain_hunter": -0.4, "loyalist": 0.5, "browser": -0.2, "high_intent": 0.8}
    purch_off = np.array([seg_purchase_offset[s] for s in segment])
    logit_p0 = -0.9 + purch_off + 1.2 * (engagement - 0.5) - 0.3 * (price_sensitivity - 0.5)
    p0 = _sigmoid(logit_p0)

    assigned_treatment = rng.choice(["control"] + C.INTERVENTION_KEYS, size=n)
    p1 = {k: np.clip(p0 + true_tau(k, segment, price_sensitivity), 0.0, 0.97) for k in C.INTERVENTION_KEYS}

    converted = np.zeros(n, dtype=bool)
    for i in range(n):
        if not reached_intent[i]:
            continue
        t = assigned_treatment[i]
        p = p0[i] if t == "control" else p1[t][i]
        converted[i] = rng.random() < p
    reached_purchase = reached_intent & converted
    reached_retention = reached_purchase & (rng.random(n) < 0.55)

    preferred_channel = {}  # marketing-channel preference, kept for realism
    channel_pref = {
        "bargain_hunter": [0.15, 0.30, 0.20, 0.35],
        "loyalist":       [0.35, 0.10, 0.35, 0.20],
        "browser":        [0.20, 0.15, 0.15, 0.50],
        "high_intent":    [0.30, 0.25, 0.30, 0.15],
    }
    preferred_channel = np.array([rng.choice(C.NBA_CHANNELS, p=channel_pref[s]) for s in segment])

    # Taste tags (occasion/style tags) -- purely so the trend engine + CRM
    # audience-size estimates have a real population to compute against,
    # independent of whatever the live demo shopper does in the storefront.
    tag_pool = O.ALL_TAGS
    preferred_tags = [
        ",".join(rng.choice(tag_pool, size=rng.integers(2, 5), replace=False))
        for _ in range(n)
    ]

    df = pd.DataFrame({
        "customer_id": customer_id,
        "first_name": first_name,
        "segment": segment,
        "engagement_propensity": engagement,
        "price_sensitivity": price_sensitivity,
        "preferred_channel": preferred_channel,
        "reached_consideration": reached_consideration,
        "reached_intent": reached_intent,
        "reached_purchase": reached_purchase,
        "reached_retention": reached_retention,
        "assigned_treatment": assigned_treatment,
        "converted": converted,
        "p0": p0,
        "preferred_tags": preferred_tags,
    })
    for k in C.INTERVENTION_KEYS:
        df[f"p1_{k}"] = p1[k]
    return df


DEMO_PERSONAS = [
    {"customer_id": "DEMO_AANYA", "first_name": "Aanya", "segment": "bargain_hunter",
     "engagement_propensity": 0.62, "price_sensitivity": 0.78, "preferred_channel": "sms"},
    {"customer_id": "DEMO_ROHAN", "first_name": "Rohan", "segment": "loyalist",
     "engagement_propensity": 0.71, "price_sensitivity": 0.35, "preferred_channel": "email"},
    {"customer_id": "DEMO_PRIYA", "first_name": "Priya", "segment": "high_intent",
     "engagement_propensity": 0.85, "price_sensitivity": 0.45, "preferred_channel": "app_push"},
]


def make_demo_personas(seed: int = C.SEED) -> pd.DataFrame:
    """Fixed, named personas the judge actually shops/chats as in the live
    demo. They use the SAME ground-truth formulas as the synthetic
    population so the causal model and the proof ledger treat them exactly
    like any other addressable customer -- just with a stable identity that
    persists across the Shop and WhatsApp tabs.
    """
    rng = np.random.default_rng(seed + 7)
    rows = []
    for p in DEMO_PERSONAS:
        seg_purchase_offset = {"bargain_hunter": -0.4, "loyalist": 0.5, "browser": -0.2, "high_intent": 0.8}
        logit_p0 = (-0.9 + seg_purchase_offset[p["segment"]]
                    + 1.2 * (p["engagement_propensity"] - 0.5)
                    - 0.3 * (p["price_sensitivity"] - 0.5))
        p0 = float(_sigmoid(np.array([logit_p0]))[0])
        row = {
            **p,
            "reached_consideration": True, "reached_intent": True,
            "reached_purchase": False, "reached_retention": False,
            "assigned_treatment": "control", "converted": False,
            "p0": p0, "preferred_tags": "",
        }
        for k in C.INTERVENTION_KEYS:
            tau = float(true_tau(k, np.array([p["segment"]]), np.array([p["price_sensitivity"]]))[0])
            row[f"p1_{k}"] = float(np.clip(p0 + tau, 0.0, 0.97))
        rows.append(row)
    return pd.DataFrame(rows)


def build_event_timeline(customers: pd.DataFrame, seed: int = C.SEED) -> pd.DataFrame:
    """Turn the static table into a chronological stream of journey events,
    one event per customer per stage actually reached, with a synthetic
    timestamp -- this is what the LiveSimulator replays instead of a batch.
    """
    rng = np.random.default_rng(seed + 1)
    rows = []
    base_minutes = 0
    # Only customers who reach Intent are interesting for the agent loop --
    # they're the addressable, at-risk pool (mirrors the original's "pool").
    pool = customers[customers.reached_intent].reset_index(drop=True)
    order = rng.permutation(len(pool))
    for rank, idx in enumerate(order):
        row = pool.iloc[idx]
        ts = base_minutes + rank * rng.uniform(0.4, 2.5)
        rows.append({
            "ts_min": ts,
            "customer_id": row.customer_id,
            "event": "reached_intent_no_purchase" if not row.reached_purchase else "reached_purchase",
        })
    out = pd.DataFrame(rows).sort_values("ts_min").reset_index(drop=True)
    return out
