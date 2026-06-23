"""Creative proof -- extends Foresight's predicted-vs-actual spine to the creative.

The synthetic-persona panel (pre_test.py) PREDICTS each variant's resonance.
This module holds the hidden GROUND-TRUTH resonance per (angle x segment) that
the panel is really estimating, samples a creative's ACTUAL engagement once it
is "shipped," and logs predicted-vs-actual into a ledger with a live calibration
error -- the same trust mechanism the original prototype used for uplift, now at
the creative level.

The ground truth is deliberately *not* identical to the panel's heuristic prior
(pre_test._ANGLE_SEGMENT_FIT), so predicted and actual differ by a realistic
margin instead of matching suspiciously.
"""
from __future__ import annotations

import hashlib
import time

_SEGMENT_KEY_BY_LABEL = {
    "Bargain Hunter": "bargain_hunter", "Loyalist": "loyalist",
    "Browser": "browser", "High Intent": "high_intent",
}

# Hidden ground-truth resonance (0..1) per (angle, segment). Never shown to the
# scorer; the panel is trying to recover these.
_TRUE = {
    "Urgency":    {"bargain_hunter": 0.82, "loyalist": 0.38, "browser": 0.56, "high_intent": 0.83},
    "Value":      {"bargain_hunter": 0.91, "loyalist": 0.50, "browser": 0.61, "high_intent": 0.57},
    "Aspiration": {"bargain_hunter": 0.39, "loyalist": 0.88, "browser": 0.74, "high_intent": 0.79},
}


def _seg_key(segment_label: str) -> str:
    return _SEGMENT_KEY_BY_LABEL.get(segment_label, "browser")


def true_resonance(angle: str, segment_label: str) -> float:
    return _TRUE.get(angle, {}).get(_seg_key(segment_label), 0.6)


def sample_actual(angle: str, segment_label: str, salt: str) -> float:
    """Actual engagement (0-100) the shipped creative earns -- ground truth plus
    deterministic per-ship noise so re-running the demo is reproducible."""
    base = true_resonance(angle, segment_label) * 100
    h = int(hashlib.sha1(f"{angle}|{segment_label}|{salt}".encode()).hexdigest()[:8], 16)
    noise = (h % 1600) / 100 - 8  # ~ -8 .. +8
    return round(max(3.0, min(99.0, base + noise)), 1)


class CreativeLedger:
    """Records shipped pre-test winners and their predicted-vs-actual resonance."""

    def __init__(self) -> None:
        self.entries: list[dict] = []
        self._n = 0

    def ship(self, *, intervention: str, intervention_label: str, segment: str, segment_label: str,
             variant_id: str, angle: str, copy: str, image_url: str,
             predicted_resonance: float) -> dict:
        self._n += 1
        actual = sample_actual(angle, segment_label, f"{variant_id}-{self._n}")
        entry = {
            "id": self._n,
            "ts": time.time(),
            "intervention": intervention,
            "intervention_label": intervention_label,
            "segment": segment,
            "segment_label": segment_label,
            "variant_id": variant_id,
            "angle": angle,
            "copy": copy,
            "image_url": image_url,
            "predicted_resonance": round(float(predicted_resonance), 1),
            "actual_engagement": actual,
            "error": round(abs(float(predicted_resonance) - actual), 1),
        }
        self.entries.insert(0, entry)
        return entry

    def calibration(self) -> dict:
        if not self.entries:
            return {"mae": None, "n": 0, "accuracy": None}
        mae = sum(e["error"] for e in self.entries) / len(self.entries)
        return {"mae": round(mae, 1), "n": len(self.entries), "accuracy": round(max(0.0, 100 - mae), 1)}

    def list(self, limit: int = 20) -> list[dict]:
        return self.entries[:limit]
