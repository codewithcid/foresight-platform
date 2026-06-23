"""Causal brain: per-customer treatment-effect (CATE) estimation.

Same family of model as the original Foresight prototype (S-learner over
LightGBM) because that part of the dummy submission was the legitimately good
piece of ML -- the evolution here is *who consumes its output*. In Foresight
it fed a chart for a human to read. Here it feeds a live agent that acts on it
every time a customer event comes in, and a Critic that keeps it honest.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    import lightgbm as lgb
    _HAS_LGB = True
except Exception:  # pragma: no cover - sandbox safety net
    from sklearn.ensemble import GradientBoostingClassifier
    _HAS_LGB = False

import config as C

_SEG_COLS = [f"seg_{s}" for s in C.SEGMENT_KEYS]
_CH_COLS = [f"ch_{c}" for c in C.NBA_CHANNELS]
_TRT_COLS = [f"trt_{t}" for t in (["control"] + C.INTERVENTION_KEYS)]
_NUM_COLS = ["engagement_propensity", "price_sensitivity"]
FEATURE_COLS = _SEG_COLS + _CH_COLS + _NUM_COLS + _TRT_COLS


def _base_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for s in C.SEGMENT_KEYS:
        out[f"seg_{s}"] = (df["segment"] == s).astype(float)
    for c in C.NBA_CHANNELS:
        out[f"ch_{c}"] = (df["preferred_channel"] == c).astype(float)
    out["engagement_propensity"] = df["engagement_propensity"].values
    out["price_sensitivity"] = df["price_sensitivity"].values
    return out


def _with_treatment(base: pd.DataFrame, treatment: str) -> pd.DataFrame:
    out = base.copy()
    for t in ["control"] + C.INTERVENTION_KEYS:
        out[f"trt_{t}"] = 1.0 if t == treatment else 0.0
    return out[FEATURE_COLS]


@dataclass
class ActionPrediction:
    intervention: str
    predicted_abs_lift: float
    predicted_rel_lift: float
    expected_incremental_conversions: float  # for 1 customer, this is a probability
    expected_revenue: float
    cost: float
    expected_roi: float
    bandit_reliability: float = 0.5  # set by the Strategist after bandit sampling


class UpliftEngine:
    """S-learner CATE model + self-validation, now exposed per-customer."""

    def __init__(self, customers: pd.DataFrame, seed: int = C.SEED):
        self.seed = seed
        self.customers = customers
        self.pool = customers[customers.reached_intent].reset_index(drop=True)
        self.model = None
        self.train_idx: np.ndarray | None = None
        self.test_idx: np.ndarray | None = None
        self.model_rel_sigma = 0.0
        # Critic-driven correction factor per intervention -- starts at 1.0,
        # nudged by observed actual/predicted ratios as the agent runs live.
        self.correction: dict[str, float] = {k: 1.0 for k in C.INTERVENTION_KEYS}

    def _make_clf(self, n: int):
        if _HAS_LGB:
            leaves = 31 if n > 1500 else 15
            return lgb.LGBMClassifier(
                n_estimators=250, learning_rate=0.05, num_leaves=leaves,
                min_child_samples=20, subsample=0.9, colsample_bytree=0.9,
                random_state=self.seed, verbose=-1,
            )
        from sklearn.ensemble import GradientBoostingClassifier
        return GradientBoostingClassifier(n_estimators=150, random_state=self.seed)

    def train(self) -> None:
        pool = self.pool
        rng = np.random.default_rng(self.seed)
        perm = rng.permutation(len(pool))
        n_test = int(len(pool) * C.TEST_SIZE)
        self.test_idx = perm[:n_test]
        self.train_idx = perm[n_test:]
        train = pool.iloc[self.train_idx]

        feat = _base_features(train)
        assigned = train["assigned_treatment"].values
        for t in ["control"] + C.INTERVENTION_KEYS:
            feat[f"trt_{t}"] = (assigned == t).astype(float)
        self.model = self._make_clf(len(train))
        self.model.fit(feat[FEATURE_COLS], train["converted"].values)

        val = self.validate()
        residuals = [c["predicted_rel_lift"] - c["actual_rel_lift"] for c in val["per_cell"]]
        self.model_rel_sigma = float(np.std(residuals)) if residuals else 0.05

    def _predict_prob(self, df: pd.DataFrame, treatment: str) -> np.ndarray:
        X = _with_treatment(_base_features(df), treatment)
        return self.model.predict_proba(X)[:, 1]

    def predict_for_customer(self, customer_row: pd.Series) -> list[ActionPrediction]:
        df1 = pd.DataFrame([customer_row])
        ctrl = self._predict_prob(df1, "control")[0]
        out = []
        for k in C.INTERVENTION_KEYS:
            tau = (self._predict_prob(df1, k)[0] - ctrl) * self.correction[k]
            rel = tau / ctrl if ctrl > 0 else 0.0
            cost = C.INTERVENTIONS[k]["cost_per_contact"]
            revenue = tau * C.AOV
            roi = (revenue - cost) / cost if cost > 0 else 0.0
            out.append(ActionPrediction(
                intervention=k, predicted_abs_lift=float(tau), predicted_rel_lift=float(rel),
                expected_incremental_conversions=float(tau), expected_revenue=float(revenue),
                cost=float(cost), expected_roi=float(roi),
            ))
        return out

    def apply_correction(self, intervention: str, actual_rel_lift: float, predicted_rel_lift: float,
                          alpha: float = 0.15) -> None:
        """Critic feedback: nudge the correction factor toward what's actually
        being observed live, so the agent's own confidence self-corrects."""
        if predicted_rel_lift == 0:
            return
        ratio = actual_rel_lift / predicted_rel_lift if predicted_rel_lift != 0 else 1.0
        ratio = float(np.clip(ratio, 0.2, 3.0))
        self.correction[intervention] = float(
            (1 - alpha) * self.correction[intervention] + alpha * ratio
        )

    def validate(self) -> dict:
        test = self.pool.iloc[self.test_idx]
        per_cell = []
        for k in C.INTERVENTION_KEYS:
            for s in C.SEGMENT_KEYS:
                df = test[test.segment == s]
                if len(df) == 0:
                    continue
                ctrl = self._predict_prob(df, "control")
                pred_abs = (self._predict_prob(df, k) - ctrl).mean()
                pred_rel = pred_abs / ctrl.mean() if ctrl.mean() > 0 else 0.0
                true_abs = (df[f"p1_{k}"] - df["p0"]).mean()
                true_rel = true_abs / df["p0"].mean()
                per_cell.append({
                    "intervention": k, "segment": s,
                    "predicted_rel_lift": float(pred_rel), "actual_rel_lift": float(true_rel),
                    "abs_error": float(abs(pred_rel - true_rel)), "n": int(len(df)),
                })
        mae = float(np.mean([c["abs_error"] for c in per_cell])) if per_cell else 0.0
        return {"per_cell": per_cell, "cell_mae": mae}
