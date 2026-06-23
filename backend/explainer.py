"""Shared explainability logic -- factored out so both the REST endpoint and
the Supervisor agent's tool registry call the exact same code path (no drift
between what a human sees on the dashboard and what the Supervisor agent
reasons over)."""
from __future__ import annotations

import db
import llm
import occasions as O
from ledger import Ledger


def explain_entry(ledger: Ledger, engine, entry_id: int) -> dict:
    entry = db.get_proof(entry_id)
    if not entry:
        return {"error": f"no ledger entry {entry_id}"}
    correction = engine.correction.get(entry.get("intervention"), 1.0) if entry.get("intervention") else None
    occasion_label = None
    if entry.get("occasion_key"):
        occ = next((o for o in O.OCCASIONS if o.key == entry["occasion_key"]), None)
        occasion_label = occ.label if occ else entry["occasion_key"]
    factors = {
        "customer": f"{entry['first_name']} ({entry['segment']})",
        "status": entry["status"],
        "intervention_label": entry.get("intervention_label") or "none (held)",
        "predicted_rel_lift": f"{entry.get('predicted_rel_lift', 0) * 100:.1f}%",
        "predicted_revenue": entry.get("predicted_revenue"),
        "cost": entry.get("cost"),
        "product_referenced": entry.get("product_name") or "none",
        "occasion_match": occasion_label or "none",
        "guardrail_status": entry.get("reason", "passed"),
        "live_correction_factor": correction,
        "bandit_reliability": entry.get("bandit_reliability"),
        "actual_rel_lift": (f"{entry['actual_rel_lift'] * 100:.1f}%" if entry.get("actual_rel_lift") is not None else "pending"),
    }
    narrative, source = llm.explain_decision(factors)
    return {"factors": factors, "narrative": narrative, "source": source}
