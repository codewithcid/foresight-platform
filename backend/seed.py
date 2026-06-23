"""Seed a few proven workflow runs + engagement on first boot, so a fresh
visitor lands on a populated Proof / Command instead of empty states. Uses
deterministic template data only (no LLM calls), and only runs if there are no
workflow runs yet.
"""
from __future__ import annotations

import config as C
import db
import workflow as W

# (template_id, predicted_rel_lift, actual_rel_lift, reach, copy, opens, clicks)
_SEED = [
    ("winback_sms", 0.34, 0.31, 590,
     "Hi! Your cart's waiting — here's 10% off to finish checking out.", 0, 0),
    ("festival_whatsapp", 0.27, 0.30, 512,
     "Don't miss out — complete your order and it's on its way.", 4, 2),
    ("loyalist_email", 0.18, 0.20, 803,
     "A little thank-you: your members-only picks are ready.", 9, 3),
]


def seed_if_empty() -> int:
    if db.list_runs(1):
        return 0  # already has runs — don't double-seed
    seeded = 0
    for tmpl_id, pred, actual, reach, copy, opens, clicks in _SEED:
        tmpl = next((t for t in W.TEMPLATES if t["id"] == tmpl_id), None)
        if not tmpl:
            continue
        seg, intv, ch = tmpl["segment"], tmpl["intervention"], tmpl["channel"]
        seg_label = C.SEGMENTS.get(seg, {}).get("label", seg)
        intv_label = C.INTERVENTIONS.get(intv, {}).get("label", intv)
        cpc = C.INTERVENTIONS.get(intv, {}).get("cost_per_contact", 3.0)
        cost = round(reach * cpc, 2)
        pred_rev = round(reach * 0.02 * (1 + pred) * C.AOV / 10, 2)
        run_id = db.insert_run(tmpl_id, tmpl["label"], seg_label, ch,
                               {"segment": seg, "intervention": intv, "channel": ch, "seed": True})
        for i, s in enumerate(W.STEP_DEFS):
            db.add_step(run_id, i, s["name"], s["label"], "done", {})
        db.update_run(run_id, status="proven", summary={
            "audience": reach + 200, "reach": reach, "cost": cost, "avg_rel_lift": pred,
            "pred_incr_revenue": pred_rev, "actual_rel_lift": actual,
            "error_pp": round(abs(pred - actual) * 100, 1), "winner_copy": copy,
            "delivered": True, "sample_n": 200,
        })
        entry = db.insert_proof({
            "ts": __import__("time").time(), "status": "proven", "resolved": 1,
            "source": "workflow", "run_id": run_id, "customer_id": f"seg:{seg}",
            "first_name": seg_label, "segment": seg_label, "intervention": intv,
            "intervention_label": intv_label, "channel": ch, "predicted_rel_lift": pred,
            "predicted_revenue": pred_rev, "cost": cost, "actual_rel_lift": actual,
            "error": abs(pred - actual), "message": copy, "message_source": "template",
        })
        for _ in range(opens):
            db.record_engagement("open", ch, "", run_id=run_id, detail="seed")
        for _ in range(clicks):
            db.record_engagement("click", ch, "", run_id=run_id, detail="seed")
        db.log_channel(channel=ch, to_addr="(segment)", body=copy, status="sent",
                       run_id=run_id, meta={"seed": True})
        seeded += 1
    return seeded
