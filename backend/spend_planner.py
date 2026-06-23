"""Spend Planner -- portfolio-level budget optimization on top of the causal brain.

Turns per-customer CATE into a CMO-level, provable media plan:
  1. ALLOCATE a fixed budget across segment x channel to maximize predicted
     incremental revenue. Each channel can only reach a capped fraction of a
     segment (app-push reaches app users, email reaches the opted-in list, etc.),
     so covering a segment means MIXING channels -- realistic media planning,
     and it makes the budget actually bind instead of one cheap channel winning
     everything.
  2. CURVE: sweep the budget 0..max to expose diminishing returns (the saturation
     point beyond which extra spend stops paying off).
  3. PROVE: compare the plan's predicted incremental revenue to the ACTUAL
     incremental revenue from held-out ground truth -- incrementality, the gold
     standard of marketing measurement, applied at the portfolio level.

Reads the live, self-corrected model, so the plan reflects what the Critic has
learned so far.
"""
from __future__ import annotations

import config as C
from causal import UpliftEngine

# Fraction of a segment each channel can realistically reach (planner-local).
CHANNEL_REACH = {"app_push": 0.45, "email": 0.75, "sms": 0.60, "paid_social": 0.95}

# The plan projects onto a realistic addressable base, not just the simulated
# sample -- per-segment lift is learned from the sample, then applied at market
# scale. Keeps budgets and revenue at an industry-credible magnitude.
MARKET_SIZE = 500_000


def cell_economics(engine: UpliftEngine) -> list[dict]:
    """Per (segment, intervention/channel): channel-capped reach, cost, predicted
    & true incremental revenue, ROI -- over the addressable (reached-Intent) pool."""
    pool = engine.pool
    cells = []
    for s in C.SEGMENT_KEYS:
        seg = pool[pool.segment == s]
        if len(seg) == 0:
            continue
        seg_size = int(MARKET_SIZE * C.SEGMENTS[s]["prop"])  # projected addressable base
        ctrl = engine._predict_prob(seg, "control")
        base = float(ctrl.mean())
        for k in C.INTERVENTION_KEYS:
            channel = C.INTERVENTIONS[k]["channel"]
            cap = CHANNEL_REACH.get(channel, 0.6)
            reach = int(seg_size * cap)
            if reach == 0:
                continue
            # Use the calibrated base model (not the agent's live, early-noisy
            # correction overlay) -- the planner is a strategic, one-shot plan.
            pred_abs = max(float((engine._predict_prob(seg, k) - ctrl).mean()), 0.0)
            true_abs = max(float((seg[f"p1_{k}"] - seg["p0"]).mean()), 0.0)
            cpc = C.INTERVENTIONS[k]["cost_per_contact"]
            cells.append({
                "segment": s, "segment_label": C.SEGMENTS[s]["label"], "seg_size": seg_size,
                "intervention": k, "intervention_label": C.INTERVENTIONS[k]["label"],
                "channel": channel, "reach": reach, "cost_per_contact": cpc,
                "baseline_conv": base, "pred_abs_lift": pred_abs, "true_abs_lift": true_abs,
                "roi": ((pred_abs * C.AOV) - cpc) / cpc if cpc > 0 else 0.0,  # per-contact ROI
            })
    return cells


def _allocate(cells: list[dict], budget: float, aov: float = C.AOV) -> tuple[list[dict], float]:
    """Greedy by per-contact ROI; a segment can be covered by MULTIPLE channels
    up to 100% of its audience; fractional on the channel where budget runs out."""
    cands = sorted([c for c in cells if c["roi"] > 0], key=lambda c: c["roi"], reverse=True)
    funded_reach: dict[str, int] = {}
    spend = 0.0
    plan: list[dict] = []
    for c in cands:
        if spend >= budget:
            break
        already = funded_reach.get(c["segment"], 0)
        cap_left = c["seg_size"] - already
        avail = min(c["reach"], cap_left)
        if avail <= 0:
            continue
        cpc = c["cost_per_contact"]
        max_cost = avail * cpc
        frac = min(1.0, (budget - spend) / max_cost) if max_cost > 0 else 0.0
        if frac <= 0:
            continue
        reach_funded = int(round(avail * frac))
        if reach_funded <= 0:
            continue
        cost = reach_funded * cpc
        funded_reach[c["segment"]] = already + reach_funded
        spend += cost
        plan.append({
            "segment": c["segment"], "segment_label": c["segment_label"],
            "intervention": c["intervention"], "intervention_label": c["intervention_label"],
            "channel": c["channel"], "reach_funded": reach_funded, "cost": cost,
            "pred_incr_conversions": c["pred_abs_lift"] * reach_funded,
            "pred_incr_revenue": c["pred_abs_lift"] * reach_funded * aov,
            "true_incr_revenue": c["true_abs_lift"] * reach_funded * aov,
            "roi": c["roi"],
        })
    return plan, spend


def _naive_revenue(cells: list[dict], budget: float, by: str, aov: float = C.AOV) -> float:
    """Predicted incremental revenue for a NAIVE allocation at the same budget --
    the baselines Foresight is measured against. `by='even'` spreads the budget
    equally across every segment x channel (no ROI ranking); `by='biggest'` puts
    it all into the single largest segment, spread across its channels. Both
    under-fund the best opportunities and waste spend on weak channels."""
    if not cells:
        return 0.0
    if by == "even":
        chosen = [c for c in cells if c["reach"] > 0]
    else:  # biggest segment only
        sizes = {c["segment"]: c["seg_size"] for c in cells}
        big = max(sizes, key=lambda s: sizes[s])
        chosen = [c for c in cells if c["segment"] == big and c["reach"] > 0]
    if not chosen:
        return 0.0
    share = budget / len(chosen)
    funded: dict[str, int] = {}
    rev = 0.0
    for c in chosen:
        avail = min(c["reach"], c["seg_size"] - funded.get(c["segment"], 0))
        cpc = c["cost_per_contact"]
        if avail <= 0 or cpc <= 0:
            continue
        rf = min(avail, int(share / cpc))
        if rf <= 0:
            continue
        funded[c["segment"]] = funded.get(c["segment"], 0) + rf
        rev += c["pred_abs_lift"] * rf * aov
    return rev


def optimize(engine: UpliftEngine | None, budget: float,
             cells: list[dict] | None = None, aov: float | None = None,
             sigma: float | None = None) -> dict:
    """Allocate a budget across cells to maximize predicted incremental revenue.

    By default it reads the synthetic engine's cell economics. The Bring-Your-Own-CSV
    path passes precomputed `cells` (built from a user-uploaded dataset), an `aov`, and
    the model's held-out `sigma`, reusing this exact allocation/curve/baseline machinery.
    """
    aov = C.AOV if aov is None else float(aov)
    if cells is None:
        cells = cell_economics(engine)
    max_useful = _allocate(cells, 1e15, aov)[1] or 1.0  # spend to fund all positive-ROI reach
    budget = max(0.0, float(budget))

    plan, spend = _allocate(cells, budget, aov)
    pred_rev = sum(p["pred_incr_revenue"] for p in plan)
    true_rev = sum(p["true_incr_revenue"] for p in plan)
    conv = sum(p["pred_incr_conversions"] for p in plan)
    roi = (pred_rev - spend) / spend if spend > 0 else 0.0

    steps = 24
    curve = [{"budget": round(max_useful * i / steps, 2),
              "incr_revenue": round(sum(p["pred_incr_revenue"] for p in _allocate(cells, max_useful * i / steps, aov)[0]), 2)}
             for i in range(steps + 1)]

    err = abs(pred_rev - true_rev)
    accuracy = round(max(0.0, 100 - (err / true_rev * 100)), 1) if true_rev > 0 else None

    # 90% confidence band from the model's own held-out relative error -- never
    # ship a point estimate without uncertainty.
    if sigma is None:
        sigma = getattr(engine, "model_rel_sigma", 0.0) or 0.08
    sigma = sigma or 0.08
    z = 1.64
    rev_ci = [round(max(0.0, pred_rev * (1 - z * sigma)), 2), round(pred_rev * (1 + z * sigma), 2)]

    even_rev = _naive_revenue(cells, budget, "even", aov)
    big_rev = _naive_revenue(cells, budget, "biggest", aov)
    baselines = {
        "foresight": round(pred_rev, 2),
        "even_split": round(even_rev, 2),
        "biggest_segment": round(big_rev, 2),
        "uplift_vs_even_pct": round((pred_rev / even_rev - 1) * 100, 1) if even_rev > 0 else None,
        "uplift_vs_even_abs": round(pred_rev - even_rev, 2),
    }

    return {
        "budget": round(budget, 2), "max_useful_budget": round(max_useful, 2),
        "spend": round(spend, 2), "pred_incr_revenue": round(pred_rev, 2),
        "pred_incr_revenue_ci": rev_ci,
        "pred_incr_conversions": round(conv, 1), "blended_roi": round(roi, 2),
        "plan": [{**p, "cost": round(p["cost"], 2),
                  "pred_incr_revenue": round(p["pred_incr_revenue"], 2),
                  "pred_incr_conversions": round(p["pred_incr_conversions"], 1),
                  "roi": round(p["roi"], 2)} for p in plan],
        "curve": curve,
        "incrementality": {
            "predicted_incr_revenue": round(pred_rev, 2), "actual_incr_revenue": round(true_rev, 2),
            "error": round(err, 2), "accuracy": accuracy,
        },
        "baselines": baselines,
        "aov": aov,
    }
