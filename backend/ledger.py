"""The proof ledger: every autonomous decision the agent makes, with its
predicted outcome, and -- once resolved -- the actual outcome and error. This
is "prove it" turned into a live, growing log instead of a one-time chart, and
it's what the calibration score and the Critic's self-correction are computed
from.

Now backed by SQLite (`db.py`) so the proof trail survives restarts and real
workflow runs (source='workflow') persist as a genuine audit log. Method
signatures are unchanged so the agent loop and API routes don't care.
"""
from __future__ import annotations

import time

import db


class Ledger:
    def __init__(self):
        db.init()  # ensures schema + clears stale sandbox rows

    def record_decision(self, *, source: str = "sandbox", run_id: int | None = None, **kwargs) -> dict:
        return db.insert_proof({
            "ts": time.time(), "status": "acted", "resolved": 0,
            "source": source, "run_id": run_id, **kwargs,
        })

    def record_hold(self, *, source: str = "sandbox", run_id: int | None = None, **kwargs) -> dict:
        return db.insert_proof({
            "ts": time.time(), "status": "held", "resolved": 1,
            "source": source, "run_id": run_id, **kwargs,
        })

    def resolve(self, eid: int, actual_rel_lift: float) -> dict:
        entry = db.get_proof(eid)
        error = abs(entry.get("predicted_rel_lift", 0.0) - actual_rel_lift)
        return db.update_proof(eid, {
            "actual_rel_lift": actual_rel_lift, "error": error,
            "resolved": 1, "status": "proven",
        })

    def recent(self, limit: int = 60) -> list[dict]:
        return db.recent_proof(limit)

    def calibration(self, window: int = 25) -> dict:
        entries = db.all_proof()
        resolved = [e for e in entries if e.get("error") is not None]
        window_entries = resolved[-window:]
        acted = sum(1 for e in entries if e["status"] != "held")
        held = sum(1 for e in entries if e["status"] == "held")
        if not window_entries:
            return {"mae": None, "n": 0, "acted": acted, "held": held}
        mae = sum(e["error"] for e in window_entries) / len(window_entries)
        return {"mae": mae, "n": len(window_entries), "acted": acted, "held": held}

    def total_spent(self) -> float:
        return sum(e.get("cost") or 0.0 for e in db.all_proof() if e["status"] != "held")

    def total_projected_revenue(self) -> float:
        return sum(e.get("predicted_revenue") or 0.0 for e in db.all_proof() if e["status"] != "held")
