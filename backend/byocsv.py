"""Bring-Your-Own-CSV: run Foresight's uplift engine on a user's real
marketing-experiment data.

The synthetic demo validates predictions against a *hidden* ground-truth effect.
Real uploaded data has no hidden truth -- but it has actual observed outcomes, so
validation here is a genuine randomized-holdout incrementality measurement
(predicted uplift vs. the observed treated-minus-control lift on a test split),
which is exactly how marketers measure incrementality in practice.

Unlike the demo, this accepts the user's OWN arbitrary segment and treatment
names -- it doesn't force them into Foresight's taxonomy. The modeling technique
(S-learner over gradient-boosted trees) is the same family as `causal.py`.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

try:
    import lightgbm as lgb
    _HAS_LGB = True
except Exception:  # pragma: no cover
    _HAS_LGB = False

import spend_planner

# Column resolution (case/space-insensitive, with common aliases).
SEGMENT_ALIASES = ["segment", "audience", "cohort", "group", "persona", "tier", "customer_segment"]
TREATMENT_ALIASES = ["treatment", "intervention", "variant", "campaign", "arm", "action", "offer", "test_group"]
CONVERTED_ALIASES = ["converted", "conversion", "purchased", "purchase", "outcome", "response", "responded", "y", "label", "target", "success"]
COST_ALIASES = ["cost", "cost_per_contact", "spend", "cpc", "unit_cost", "contact_cost"]
REVENUE_ALIASES = ["revenue", "order_value", "aov", "sale_value", "amount", "gmv", "basket_value"]
ID_ALIASES = ["customer_id", "id", "user_id", "customer", "cust_id", "userid"]
CONTROL_TOKENS = {"control", "ctrl", "holdout", "hold-out", "none", "no_treatment", "untreated",
                  "baseline", "control_group", "no", "false", "0"}

DEFAULT_AOV = 2000.0
DEFAULT_COST = 5.0
MIN_ROWS = 40
MAX_SEGMENTS = 10
MAX_TREATMENTS = 8
MAX_CAT_CARDINALITY = 12
TEST_FRAC = 0.30
SEED = 42


def _norm(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def _resolve(cols_map: dict[str, str], aliases: list[str]) -> str | None:
    for a in aliases:
        if a in cols_map:
            return cols_map[a]
    for a in aliases:
        for norm, orig in cols_map.items():
            if a in norm:
                return orig
    return None


def _coerce_binary(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.astype(int)
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() > 0.9:
        return (num > 0.5).astype(int)
    truthy = {"1", "yes", "true", "y", "t", "converted", "purchased", "success", "won"}
    return s.astype(str).str.strip().str.lower().isin(truthy).astype(int)


def _read_csv(content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Could not parse the CSV file: {e}")
    if df.shape[1] < 3:
        raise ValueError("CSV needs at least 3 columns (segment, treatment, converted).")
    return df


def _make_classifier(n: int, seed: int = SEED):
    if _HAS_LGB:
        # Regularized: an under-constrained S-learner overfits the
        # treatment x feature interactions and inflates counterfactual uplift.
        # Shallower trees + larger leaves + L2 keep predicted lift calibrated to
        # what's actually observed on the holdout.
        leaves = 15 if n > 1500 else 8
        return lgb.LGBMClassifier(
            n_estimators=140, learning_rate=0.05, num_leaves=leaves,
            min_child_samples=max(40, n // 120), subsample=0.8, colsample_bytree=0.8,
            reg_lambda=5.0, random_state=seed, verbose=-1,
        )
    from sklearn.ensemble import GradientBoostingClassifier
    return GradientBoostingClassifier(n_estimators=120, max_depth=3, random_state=seed)


def _top_levels(series: pd.Series, cap: int) -> list[str]:
    counts = series.astype(str).value_counts()
    return list(counts.index[:cap])


def analyze(content: bytes, control_label: str | None = None, aov_override: float | None = None) -> dict:
    df = _read_csv(content)
    cols_map = {_norm(c): c for c in df.columns}

    seg_col = _resolve(cols_map, SEGMENT_ALIASES)
    trt_col = _resolve(cols_map, TREATMENT_ALIASES)
    conv_col = _resolve(cols_map, CONVERTED_ALIASES)
    cost_col = _resolve(cols_map, COST_ALIASES)
    rev_col = _resolve(cols_map, REVENUE_ALIASES)
    id_col = _resolve(cols_map, ID_ALIASES)

    missing = [n for n, c in [("segment", seg_col), ("treatment", trt_col), ("converted", conv_col)] if c is None]
    if missing:
        raise ValueError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Found columns: {', '.join(df.columns)}. "
            f"Need a segment column, a treatment column (incl. a control level), and a 0/1 converted column."
        )

    df = df.dropna(subset=[seg_col, trt_col, conv_col]).reset_index(drop=True)
    if len(df) < MIN_ROWS:
        raise ValueError(f"Need at least {MIN_ROWS} rows after dropping blanks; got {len(df)}.")

    df["__seg"] = df[seg_col].astype(str)
    df["__trt"] = df[trt_col].astype(str)
    df["__y"] = _coerce_binary(df[conv_col])

    if df["__y"].nunique() < 2:
        raise ValueError("The converted column has only one value — need both converted and non-converted rows.")

    # ---- control + treatment levels ----
    trt_counts = df["__trt"].value_counts()
    control = None
    if control_label and str(control_label) in set(trt_counts.index):
        control = str(control_label)
    if control is None:
        for lv in trt_counts.index:
            if _norm(lv) in CONTROL_TOKENS:
                control = lv
                break
    if control is None:
        control = trt_counts.index[0]  # most frequent as fallback control

    non_control = [t for t in _top_levels(df["__trt"], MAX_TREATMENTS + 1) if t != control][:MAX_TREATMENTS]
    if not non_control:
        raise ValueError(f"No non-control treatments found (control detected as '{control}').")
    trt_levels = [control] + non_control
    df = df[df["__trt"].isin(trt_levels)].reset_index(drop=True)

    # ---- segment levels ----
    seg_levels = _top_levels(df["__seg"], MAX_SEGMENTS)
    df = df[df["__seg"].isin(seg_levels)].reset_index(drop=True)

    # ---- feature columns ----
    used = {seg_col, trt_col, conv_col, cost_col, rev_col, id_col, "__seg", "__trt", "__y"}
    num_cols: list[str] = []
    cat_cols: list[str] = []
    for c in df.columns:
        if c in used:
            continue
        col = df[c]
        if pd.api.types.is_numeric_dtype(col):
            if pd.to_numeric(col, errors="coerce").nunique() > 1:
                num_cols.append(c)
        else:
            nun = col.astype(str).nunique()
            if 2 <= nun <= MAX_CAT_CARDINALITY:
                cat_cols.append(c)
    num_medians = {n: float(pd.to_numeric(df[n], errors="coerce").median()) for n in num_cols}
    cat_levels = {c: _top_levels(df[c], MAX_CAT_CARDINALITY) for c in cat_cols}

    # ---- design matrix (S-learner) ----
    # Index-based column names (seg_0, cat_1_2, num_0, trt_3) so arbitrary user
    # segment/treatment labels can't produce LightGBM-illegal feature names.
    trt_index = {lv: i for i, lv in enumerate(trt_levels)}

    def base_features(frame: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=frame.index)
        segv = frame["__seg"]
        for i, lv in enumerate(seg_levels):
            out[f"seg_{i}"] = (segv == lv).astype(float)
        for ci, c in enumerate(cat_cols):
            cv = frame[c].astype(str)
            for li, lv in enumerate(cat_levels[c]):
                out[f"cat_{ci}_{li}"] = (cv == lv).astype(float)
        for ni, nname in enumerate(num_cols):
            out[f"num_{ni}"] = pd.to_numeric(frame[nname], errors="coerce").fillna(num_medians[nname]).astype(float)
        return out

    base_cols = list(base_features(df.head(1)).columns)
    trt_cols = [f"trt_{i}" for i in range(len(trt_levels))]
    feature_cols = base_cols + trt_cols

    def with_treatment(base: pd.DataFrame, level: str) -> pd.DataFrame:
        out = base.copy()
        active = trt_index[level]
        for i in range(len(trt_levels)):
            out[f"trt_{i}"] = 1.0 if i == active else 0.0
        return out[feature_cols]

    base_all = base_features(df)

    # ---- train / test split ----
    rng = np.random.default_rng(SEED)
    n = len(df)
    perm = rng.permutation(n)
    n_test = max(int(n * TEST_FRAC), 1)
    test_idx = perm[:n_test]
    train_idx = perm[n_test:]

    train_base = base_all.iloc[train_idx].reset_index(drop=True)
    train_trt = df["__trt"].iloc[train_idx].to_numpy()
    Xtr = train_base.copy()
    for i, lv in enumerate(trt_levels):
        Xtr[f"trt_{i}"] = (train_trt == lv).astype(float)
    Xtr = Xtr[feature_cols]
    ytr = df["__y"].iloc[train_idx].to_numpy()
    if len(np.unique(ytr)) < 2:
        raise ValueError("Training split has only one outcome class — try a larger or more balanced file.")

    model = _make_classifier(len(train_idx))
    model.fit(Xtr, ytr)

    def prob(base: pd.DataFrame, level: str) -> np.ndarray:
        return model.predict_proba(with_treatment(base, level))[:, 1]

    # ---- holdout validation: predicted vs OBSERVED lift ----
    test_df = df.iloc[test_idx].reset_index(drop=True)
    test_base = base_all.iloc[test_idx].reset_index(drop=True)
    test_y = test_df["__y"].to_numpy()
    test_trt = test_df["__trt"].to_numpy()
    test_seg = test_df["__seg"].to_numpy()

    p_ctrl_test = prob(test_base, control)

    cell_rows = []
    rel_residuals = []
    for s in seg_levels:
        seg_mask = test_seg == s
        if seg_mask.sum() == 0:
            continue
        ctrl_obs = test_y[seg_mask & (test_trt == control)]
        ctrl_rate = float(ctrl_obs.mean()) if len(ctrl_obs) else float(p_ctrl_test[seg_mask].mean())
        pred_ctrl_seg = float(p_ctrl_test[seg_mask].mean())
        for t in non_control:
            pred_abs = float((prob(test_base.iloc[np.where(seg_mask)[0]], t) - p_ctrl_test[seg_mask]).mean())
            treated_obs = test_y[seg_mask & (test_trt == t)]
            row = {
                "segment": s, "treatment": t, "n": int(seg_mask.sum()),
                "n_treated": int(len(treated_obs)),
                "pred_abs_lift": round(pred_abs, 5),
                "pred_rel_lift": round(pred_abs / pred_ctrl_seg, 4) if pred_ctrl_seg > 0 else None,
                "obs_abs_lift": None, "obs_rel_lift": None, "abs_error_pp": None,
            }
            if len(treated_obs) >= 3 and len(ctrl_obs) >= 3:
                obs_abs = float(treated_obs.mean() - ctrl_rate)
                row["obs_abs_lift"] = round(obs_abs, 5)
                row["obs_rel_lift"] = round(obs_abs / ctrl_rate, 4) if ctrl_rate > 0 else None
                row["abs_error_pp"] = round(abs(pred_abs - obs_abs) * 100, 3)
                rel_residuals.append(pred_abs - obs_abs)
            cell_rows.append(row)

    measured = [c for c in cell_rows if c["abs_error_pp"] is not None]
    cell_mae_pp = round(float(np.mean([c["abs_error_pp"] for c in measured])), 3) if measured else None

    # ---- aggregate incrementality on the holdout (the headline proof) ----
    # Predicted: per-treated-row counterfactual uplift from the model.
    # Observed: segment-STRATIFIED treated-vs-control gap (each segment compared
    # to its own control rate) -- avoids the bias of a single global control rate
    # when treatment assignment isn't perfectly balanced across segments.
    treated_mask = test_trt != control
    n_treated = int(treated_mask.sum())
    pred_incr = 0.0
    for t in non_control:
        m = test_trt == t
        if m.any():
            sub = test_base.iloc[np.where(m)[0]]
            pred_incr += float((prob(sub, t) - prob(sub, control)).sum())
    obs_incr = 0.0
    for s in seg_levels:
        sm = test_seg == s
        ctrl_s = test_y[sm & (test_trt == control)]
        if len(ctrl_s) == 0:
            continue
        rate_s = float(ctrl_s.mean())
        treated_s = test_y[sm & (test_trt != control)]
        obs_incr += float(treated_s.sum() - len(treated_s) * rate_s)
    incr_accuracy = round(max(0.0, 100 - abs(pred_incr - obs_incr) / abs(obs_incr) * 100), 1) if abs(obs_incr) > 1e-9 else None

    # ---- uplift deciles: does the model RANK persuadability correctly? ----
    best_uplift = np.zeros(len(test_df))
    for t in non_control:
        best_uplift = np.maximum(best_uplift, prob(test_base, t) - p_ctrl_test)
    order = np.argsort(-best_uplift)
    n_buckets = 5 if len(test_df) < 400 else 10
    deciles = []
    for b in range(n_buckets):
        idx = order[int(b * len(order) / n_buckets):int((b + 1) * len(order) / n_buckets)]
        if len(idx) == 0:
            continue
        bt = test_trt[idx]
        by = test_y[idx]
        tr = by[bt != control]
        ct = by[bt == control]
        obs_gap = float(tr.mean() - ct.mean()) if len(tr) and len(ct) else None
        deciles.append({
            "bucket": b + 1,
            "avg_pred_uplift": round(float(best_uplift[idx].mean()), 4),
            "obs_uplift": round(obs_gap, 4) if obs_gap is not None else None,
            "n": int(len(idx)),
        })

    # ---- planner cells (full data, projected onto the uploaded population) ----
    aov = float(aov_override) if aov_override else (
        float(pd.to_numeric(df.loc[df["__y"] == 1, rev_col], errors="coerce").mean())
        if rev_col and df["__y"].sum() > 0 else DEFAULT_AOV
    )
    if not np.isfinite(aov) or aov <= 0:
        aov = DEFAULT_AOV
    aov_source = "from revenue column" if (rev_col and aov_override is None) else ("custom" if aov_override else f"assumed (no revenue column)")

    cost_by_trt: dict[str, float] = {}
    if cost_col:
        for t in non_control:
            cv = pd.to_numeric(df.loc[df["__trt"] == t, cost_col], errors="coerce")
            cost_by_trt[t] = float(cv.mean()) if cv.notna().any() else DEFAULT_COST
    cost_source = "from cost column" if cost_col else "assumed (no cost column)"

    cells = []
    for s in seg_levels:
        seg_mask = (df["__seg"] == s).to_numpy()
        if seg_mask.sum() == 0:
            continue
        seg_base = base_all.iloc[np.where(seg_mask)[0]]
        p_ctrl = prob(seg_base, control)
        base_conv = float(p_ctrl.mean())
        seg_size = int(seg_mask.sum())
        ctrl_obs = df["__y"].to_numpy()[seg_mask & (df["__trt"] == control).to_numpy()]
        ctrl_rate = float(ctrl_obs.mean()) if len(ctrl_obs) else base_conv
        for t in non_control:
            pred_abs = max(float((prob(seg_base, t) - p_ctrl).mean()), 0.0)
            treated_obs = df["__y"].to_numpy()[seg_mask & (df["__trt"] == t).to_numpy()]
            true_abs = max(float(treated_obs.mean() - ctrl_rate), 0.0) if len(treated_obs) >= 3 and len(ctrl_obs) >= 3 else pred_abs
            cpc = cost_by_trt.get(t, DEFAULT_COST)
            cells.append({
                "segment": s, "segment_label": s, "seg_size": seg_size,
                "intervention": t, "intervention_label": t, "channel": t,
                "reach": seg_size, "cost_per_contact": cpc,
                "baseline_conv": base_conv, "pred_abs_lift": pred_abs, "true_abs_lift": true_abs,
                "roi": ((pred_abs * aov) - cpc) / cpc if cpc > 0 else 0.0,
            })

    sigma = round(float(np.std(rel_residuals)), 4) if rel_residuals else 0.1
    full = spend_planner.optimize(None, 1e15, cells=cells, aov=aov, sigma=sigma)
    suggested = round(full["max_useful_budget"] * 0.5, 2)
    plan = spend_planner.optimize(None, suggested, cells=cells, aov=aov, sigma=sigma)

    n_customers = int(df[id_col].nunique()) if id_col else len(df)

    return {
        "dataset": {
            "rows": int(len(df)),
            "customers": n_customers,
            "conversion_rate": round(float(df["__y"].mean()), 4),
            "segments": [{"name": s, "n": int((df["__seg"] == s).sum())} for s in seg_levels],
            "treatments": [{"name": t, "n": int((df["__trt"] == t).sum()), "is_control": t == control} for t in trt_levels],
            "columns_detected": {
                "segment": seg_col, "treatment": trt_col, "converted": conv_col,
                "cost": cost_col, "revenue": rev_col, "customer_id": id_col,
            },
            "features_used": {"numeric": num_cols, "categorical": cat_cols},
        },
        "model": {
            "type": "S-learner (single model, treatment as feature)",
            "library": "LightGBM" if _HAS_LGB else "sklearn GradientBoosting",
            "n_train": int(len(train_idx)), "n_test": int(len(test_idx)),
            "n_features": len(feature_cols),
        },
        "validation": {
            "cell_mae_pp": cell_mae_pp,
            "incrementality": {
                "predicted_incr_conversions": round(pred_incr, 1),
                "observed_incr_conversions": round(obs_incr, 1),
                "accuracy_pct": incr_accuracy,
                "n_treated_test": n_treated,
            },
            "cells": cell_rows,
            "deciles": deciles,
        },
        "aov": round(aov, 2), "aov_source": aov_source, "cost_source": cost_source,
        "plan": plan,
        "planner_ctx": {"cells": cells, "aov": aov, "sigma": sigma},
    }


# ---------------------------------------------------------------- sample data
def sample_csv() -> str:
    """A realistic, ready-to-upload marketing-experiment CSV with the user's OWN
    arbitrary taxonomy (not Foresight's) and a known injected uplift, so the
    predicted-vs-observed proof reads well. ~3,000 rows."""
    rng = np.random.default_rng(7)
    n = 8000
    segments = ["VIP", "Loyal", "At-Risk", "New", "Window-Shopper"]
    seg_p = [0.12, 0.23, 0.18, 0.27, 0.20]
    treatments = ["control", "email_winback", "sms_promo", "app_nudge", "retarget_ad"]
    seg = rng.choice(segments, size=n, p=seg_p)
    # A sizeable randomized control holdout (~36%) so the control baseline — and
    # therefore the observed incrementality — is estimated tightly.
    trt = rng.choice(treatments, size=n, p=[0.36, 0.16, 0.16, 0.16, 0.16])

    base_rate = {"VIP": 0.34, "Loyal": 0.26, "At-Risk": 0.08, "New": 0.12, "Window-Shopper": 0.05}
    # injected true uplift per (segment, treatment) -- the ground truth the model must recover
    uplift = {
        "email_winback": {"VIP": 0.03, "Loyal": 0.09, "At-Risk": 0.12, "New": 0.05, "Window-Shopper": 0.03},
        "sms_promo":     {"VIP": 0.02, "Loyal": 0.03, "At-Risk": 0.14, "New": 0.06, "Window-Shopper": 0.08},
        "app_nudge":     {"VIP": 0.08, "Loyal": 0.05, "At-Risk": 0.04, "New": 0.10, "Window-Shopper": 0.04},
        "retarget_ad":   {"VIP": 0.04, "Loyal": 0.04, "At-Risk": 0.06, "New": 0.09, "Window-Shopper": 0.11},
    }
    cost = {"control": 0.0, "email_winback": 4.0, "sms_promo": 3.0, "app_nudge": 5.0, "retarget_ad": 42.0}

    recency = rng.integers(1, 365, size=n)
    prior_orders = rng.poisson(3, size=n)
    avg_basket = np.round(rng.normal(2200, 700, size=n).clip(300, 8000), 0)
    channel = rng.choice(["app", "web", "store"], size=n, p=[0.45, 0.4, 0.15])
    region = rng.choice(["north", "south", "east", "west"], size=n)

    rows = []
    for i in range(n):
        s = seg[i]
        t = trt[i]
        # behaviour nudges the base rate a little so features carry signal
        p = base_rate[s] + 0.05 * (prior_orders[i] / 10) - 0.04 * (recency[i] / 365)
        if t != "control":
            p += uplift[t][s]
        p = float(np.clip(p, 0.01, 0.95))
        converted = int(rng.random() < p)
        rows.append({
            "customer_id": f"U{100000 + i}",
            "segment": s,
            "recency_days": int(recency[i]),
            "prior_orders": int(prior_orders[i]),
            "avg_basket": float(avg_basket[i]),
            "channel": channel[i],
            "region": region[i],
            "treatment": t,
            "cost": cost[t],
            "converted": converted,
            "revenue": float(avg_basket[i]) if converted else 0.0,
        })
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)
