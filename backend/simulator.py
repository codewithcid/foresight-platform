"""Replays the synthetic event timeline as a live stream, calling the agent
loop for each event. This is the structural piece that turns the original
static dataset into something that runs in front of judges instead of sitting
in a chart -- speed is adjustable so a 4000-customer day can play out in a
few minutes of demo time.
"""
from __future__ import annotations

import asyncio

import pandas as pd

from agent import AgentLoop


class LiveSimulator:
    def __init__(self, agent_loop: AgentLoop, timeline: pd.DataFrame, broadcast, speed: float = 3.0):
        self.agent_loop = agent_loop
        self.timeline = timeline.reset_index(drop=True)
        self.broadcast = broadcast
        self.speed = speed
        self.running = False
        self._task: asyncio.Task | None = None
        self._cursor = 0

    async def _run(self):
        self.running = True
        last_ts = self.timeline.iloc[self._cursor]["ts_min"] if self._cursor < len(self.timeline) else 0.0
        while self._cursor < len(self.timeline) and self.running:
            row = self.timeline.iloc[self._cursor]
            gap = max(0.0, row["ts_min"] - last_ts)
            last_ts = row["ts_min"]
            await asyncio.sleep(min(gap, 3.0) / max(self.speed, 0.1))
            if not self.running:
                break
            await self.agent_loop.handle_event(row["customer_id"], row["event"], self.broadcast)
            self._cursor += 1
        self.running = False

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    def pause(self):
        self.running = False

    def reset(self):
        self.pause()
        self._cursor = 0

    def set_speed(self, speed: float):
        self.speed = max(0.1, speed)

    def status(self) -> dict:
        return {
            "running": self.running,
            "cursor": self._cursor,
            "total": len(self.timeline),
            "speed": self.speed,
        }
