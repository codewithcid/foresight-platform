"""Model Card + Qini/AUUC uplift evaluation -- measurement-science rigor.

The Qini curve is the standard way to judge an *uplift* model: rank the held-out
customers by predicted treatment effect, then plot the cumulative ACTUAL
incremental conversions captured as you target from the top down. A model that
ranks well sits well above the random diagonal; the area between them is the
Qini/AUUC coefficient. The Model Card documents the model, data, metrics, and
honest limitations -- the responsible-AI artifact enterprises expect.
"""
from __future__ import annotations

import numpy as np

import config as C
from causal import UpliftEngine


def qini_curve(engine: UpliftEngine, intervention: str, points: int = 20) -> dict:
    test = engine.pool.iloc[engine.test_idx]
    ctrl = engine._predict_prob(test, "control")
    pred_tau = engine._predict_prob(test, intervention) - ctrl
    true_tau = (test[f"p1_{intervention}"] - test["p0"]).to_numpy()
    n = len(true_tau)
    order = np.argsort(-pred_tau)                 # rank by predicted uplift, best first
    cum = np.cumsum(true_tau[order])
    total = float(cum[-1]) if n else 0.0

    curve = []
    for i in range(points + 1):
        idx = int(round(n * i / points))
        gain = float(cum[idx - 1]) if idx > 0 else 0.0
        curve.append({
            "frac": round(i / points, 3),
            "model": round(gain / total, 4) if total else 0.0,   # cumulative share of total uplift
            "random": round(i / points, 4),                       # diagonal baseline
        })
    xs = np.array([c["frac"] for c in curve])
    ym = np.array([c["model"] for c in curve])
    d = ym - xs                                    # model lift over random, per point
    qini = float(np.sum((d[:-1] + d[1:]) / 2 * np.diff(xs)))  # trapezoid area (numpy-2 safe)
    return {"intervention": intervention, "intervention_label": C.INTERVENTIONS[intervention]["label"],
            "curve": curve, "qini": round(qini, 4)}


def model_card(engine: UpliftEngine) -> dict:
    val = engine.validate()
    qinis = {k: qini_curve(engine, k)["qini"] for k in C.INTERVENTION_KEYS}
    return {
        "name": "Foresight Uplift Engine",
        "version": "0.3",
        "model_type": "S-learner (single-model meta-learner) over gradient-boosted trees",
        "library": "LightGBM",
        "objective": "Per-customer conditional average treatment effect (CATE) for each marketing intervention",
        "features": ["customer segment", "preferred channel", "engagement propensity",
                     "price sensitivity", "intervention (treatment indicator)"],
        "training_data": f"{len(engine.pool):,} reached-Intent customers; "
                         f"{int(C.TEST_SIZE * 100)}% held out for validation",
        "interventions": [C.INTERVENTIONS[k]["label"] for k in C.INTERVENTION_KEYS],
        "metrics": {
            "cell_mae_pp": round(val["cell_mae"] * 100, 1),
            "n_validation_cells": len(val["per_cell"]),
            "mean_qini": round(sum(qinis.values()) / len(qinis), 4) if qinis else 0.0,
            "qini_by_intervention": qinis,
        },
        "validation": ["Predicted-vs-actual relative lift on held-out cells",
                       "Qini/AUUC ranking quality per intervention",
                       "Live Critic self-correction (EWMA) against realized outcomes",
                       "Incrementality (randomized-holdout) proof at the portfolio level"],
        "assumptions": [
            "Synthetic data carries a known ground-truth treatment effect, which is what makes live "
            "predicted-vs-actual proof possible without a production feed.",
            "Treatment assignment in training is randomized (unconfounded), so the S-learner recovers CATE.",
            "Channel reach caps and fully-loaded costs are illustrative but realistic.",
        ],
        "limitations": [
            "Per-segment lift is learned from a sample then projected to the addressable base.",
            "On real data, incrementality should be validated with a live randomized/geo holdout.",
            "The S-learner is deliberately simple and explainable; a DR-/X-learner could reduce bias further.",
        ],
        "responsible_ai": [
            "Guardrails: frequency cap, daily budget cap, brand-safety filter, opt-out suppression.",
            "Every autonomous decision is explainable (structured factors + plain-English rationale).",
            "Confidence intervals are shown on headline predictions; no point estimate ships alone.",
        ],
    }
