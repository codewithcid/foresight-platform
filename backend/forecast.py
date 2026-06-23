"""Trend forecasting: a 30-day synthetic engagement history per tag, plus a
simple linear-trend fit projecting 7 days ahead -- the upgrade from "what's
popular right now" (a snapshot) to "what's about to be popular" (a forecast).

The historical points are synthetic (we don't have real multi-day telemetry),
generated deterministically so each tag's recent history already ramps up as
its nearest real-calendar occasion approaches -- which is exactly the pattern
a forecaster should detect and flag, rather than something hand-coded into
the "trending" output directly.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np

import occasions as O

HISTORY_DAYS = 30
_SEED = 11


def _days_to_nearest_occasion(tag: str, today: date) -> int:
    best = 999
    for o in O.OCCASIONS:
        if tag not in o.tags:
            continue
        target = O.next_occurrence(*o.start, after=today)
        best = min(best, (target - today).days)
    return best


def _build_history() -> dict[str, list[float]]:
    rng = np.random.default_rng(_SEED)
    today = date.today()
    history: dict[str, list[float]] = {}
    for tag in O.ALL_TAGS:
        days_out = _days_to_nearest_occasion(tag, today)
        # Closer occasions -> steeper recent ramp. Capped so far-off tags stay flat-ish.
        urgency = max(0.0, 1.0 - min(days_out, 60) / 60.0)
        series = []
        base = 5.0 + rng.uniform(0, 3)
        for d in range(HISTORY_DAYS, 0, -1):
            ramp = urgency * (HISTORY_DAYS - d) / HISTORY_DAYS * 8.0
            noise = rng.normal(0, 0.6)
            series.append(max(0.1, base + ramp + noise))
        history[tag] = series
    return history


_HISTORY = _build_history()


def forecast_tag(tag: str, recent_days: int = 10, horizon: int = 7) -> dict:
    series = _HISTORY.get(tag, [1.0] * HISTORY_DAYS)
    recent = series[-recent_days:]
    x = np.arange(len(recent))
    slope, intercept = np.polyfit(x, recent, 1)
    current = recent[-1]
    forecast_value = max(0.0, intercept + slope * (len(recent) - 1 + horizon))
    direction = "rising" if slope > 0.08 else ("falling" if slope < -0.08 else "flat")
    return {
        "tag": tag, "current": round(float(current), 1), "forecast_7d": round(float(forecast_value), 1),
        "slope": round(float(slope), 3), "direction": direction,
    }


def forecast_all(tags: list[str] | None = None) -> list[dict]:
    tags = tags or O.ALL_TAGS
    return [forecast_tag(t) for t in tags]


def rising_tags(limit: int = 6) -> list[dict]:
    rows = [forecast_tag(t) for t in O.ALL_TAGS]
    rows.sort(key=lambda r: r["slope"], reverse=True)
    return rows[:limit]
