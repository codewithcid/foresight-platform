"""A real contextual bandit, replacing the flat EWMA correction factor with
per (segment, intervention) learned reliability.

This directly answers the honest-scope note in the README that flagged the
original correction factor as "a simple nudge, not a full bandit." It's
Thompson sampling over a Beta posterior per arm: each arm tracks how often an
action's predicted lift was actually borne out, and the Strategist samples
from each candidate's posterior (rather than taking the causal model's point
estimate at face value) when ranking actions -- so the agent explores arms
it's still uncertain about instead of permanently trusting whichever arm
looked best on day one.

The causal model still gets graded independently in the proof ledger
(predicted vs. actual) -- the bandit only influences *which* action gets
tried, not what the model claims it will do. Keeping those two honest and
separate is the point: prediction accuracy and exploration policy are
different questions.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Arm:
    alpha: float = 2.0  # successes (+ Bayesian prior pseudo-count)
    beta: float = 2.0   # failures (+ prior)
    n: int = 0

    def sample(self, rng) -> float:
        return float(rng.beta(self.alpha, self.beta))

    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


class ThompsonBandit:
    def __init__(self, seed: int = 7):
        import numpy as np
        self._rng = np.random.default_rng(seed)
        self.arms: dict[tuple[str, str], Arm] = {}

    def _arm(self, segment: str, intervention: str) -> Arm:
        key = (segment, intervention)
        if key not in self.arms:
            self.arms[key] = Arm()
        return self.arms[key]

    def sample(self, segment: str, intervention: str) -> float:
        return self._arm(segment, intervention).sample(self._rng)

    def update(self, segment: str, intervention: str, success: bool) -> None:
        arm = self._arm(segment, intervention)
        if success:
            arm.alpha += 1.0
        else:
            arm.beta += 1.0
        arm.n += 1

    def status(self) -> list[dict]:
        out = []
        for (segment, intervention), arm in self.arms.items():
            out.append({
                "segment": segment, "intervention": intervention,
                "mean_reliability": round(arm.mean(), 3), "trials": arm.n,
                "alpha": round(arm.alpha, 1), "beta": round(arm.beta, 1),
            })
        out.sort(key=lambda r: r["trials"], reverse=True)
        return out
