"""The Time Machine: a virtual 'now' decoupled from the real system clock.

Every occasion-aware piece of the system (homepage merchandising, CRM
campaign drafting, trend analysis) reads time through this clock instead of
datetime.now(), so a judge can drag the date to Diwali or IPL season and
watch the whole system's behaviour change live -- that's the actual proof
that the occasion-awareness is wired in, not hardcoded for "today".
"""
from __future__ import annotations

from datetime import datetime, timedelta


class SimClock:
    def __init__(self):
        self._virtual_now: datetime = datetime.now()
        self._offset: timedelta = timedelta(0)
        self._frozen_at: datetime | None = None  # if set, clock is paused at a fixed virtual time

    def now(self) -> datetime:
        if self._frozen_at is not None:
            return self._frozen_at
        return datetime.now() + self._offset

    def set(self, iso_datetime: str) -> datetime:
        # Foresight only looks FORWARD: never let the virtual clock go before
        # real "now". Past dates are clamped to the present -- prediction, not
        # hindsight.
        target = datetime.fromisoformat(iso_datetime)
        floor = datetime.now()
        if target < floor:
            target = floor
        self._frozen_at = target
        return target

    def resume_live(self) -> datetime:
        """Unfreeze: resume real time, offset from whatever the frozen time was."""
        if self._frozen_at is not None:
            self._offset = self._frozen_at - datetime.now()
        self._frozen_at = None
        return self.now()

    def reset_to_real(self) -> datetime:
        self._frozen_at = None
        self._offset = timedelta(0)
        return self.now()

    def is_frozen(self) -> bool:
        return self._frozen_at is not None


CLOCK = SimClock()
