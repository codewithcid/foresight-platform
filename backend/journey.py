"""Cross-channel journey orchestration.

A journey is an ordered, multi-channel cadence with **branch-on-response**: send
on channel 1; if the customer engages (clicks the tracked link / replies / buys)
the journey stops — goal met. If not, after a wait it escalates to the next
channel, following the customer wherever they are. This is "seamless cross-channel
experiences" made operational; every touch is logged for the Customer-360 timeline
and the proof spine.

Reuses the same primitives as everything else: channel adapters, tracked links
(`/r/{token}` clicks = engagement), the engagement table, and a sweeper loop
(same pattern as the cart-recovery engine).
"""
from __future__ import annotations

import asyncio
import time

import appconfig
import channels
import db
import tracking

# Each step is a real channel + a short re-engagement line. {name} is filled in.
TEMPLATES = [
    {"id": "winback", "name": "Win-back cadence", "goal": "click", "steps": [
        {"channel": "sms", "copy": "Hi {name}, we miss you — here's 10% off your next order:"},
        {"channel": "whatsapp", "copy": "Hi {name} 👋 still thinking it over? Your 10% is waiting:"},
        {"channel": "email", "copy": "{name}, your comeback offer expires soon — grab 10% off:"},
    ]},
    {"id": "highvalue", "name": "High-value re-engage", "goal": "click", "steps": [
        {"channel": "whatsapp", "copy": "Hi {name}, a hand-picked pick just for you:"},
        {"channel": "telegram", "copy": "{name}, still available — take a look:"},
        {"channel": "email", "copy": "{name}, last call on your VIP pick:"},
    ]},
    {"id": "browser", "name": "Browser nudge", "goal": "click", "steps": [
        {"channel": "sms", "copy": "Hi {name}, the styles you viewed are selling fast:"},
        {"channel": "email", "copy": "{name}, still interested? Here's what you were looking at:"},
    ]},
]
TEMPLATES_BY_ID = {t["id"]: t for t in TEMPLATES}


def _wait() -> float:
    v = appconfig.get("JOURNEY_STEP_SEC")
    try:
        return float(v) if v else 45.0
    except (TypeError, ValueError):
        return 45.0


class JourneyEngine:
    def __init__(self, ctx: dict, broadcast):
        self.ctx = ctx
        self.broadcast = broadcast
        self._task: asyncio.Task | None = None

    def _recipient(self, channel: str, j: dict) -> str:
        if channel == "email":
            return j.get("email") or ""
        if channel == "slack":
            return ""  # slack posts to its configured channel
        return j.get("phone") or ""

    async def _emit(self, event: str, j: dict, **extra):
        await self.broadcast({"type": "journey", "event": event, "journey": j, **extra})

    async def _send_step(self, j: dict, idx: int) -> dict:
        step = j["steps"][idx]
        ch_id = step["channel"]
        name = j.get("name") or "there"
        recipient = self._recipient(ch_id, j)
        body = step["copy"].replace("{name}", name)
        # tracked link keyed to the recipient -> a click registers engagement (the branch signal)
        link = tracking.make_tracked_link(tracking.DEFAULT_DEST, None, ch_id, recipient or (j.get("phone") or ""))
        full = f"{body} {link}"

        delivered, err = False, ""
        ch = channels.get_channel(ch_id)
        has_default = ch_id == "slack"
        if ch and ch.configured() and (recipient or has_default):
            res = await asyncio.to_thread(ch.send, recipient, full, {"kind": "journey", "journey_id": j["id"]})
            delivered, err = res.ok, res.error
            db.log_channel(channel=ch_id, to_addr=recipient, body=full,
                           status="sent" if res.ok else "failed", provider_id=res.provider_id,
                           error=err, meta={"kind": "journey", "journey_id": j["id"]})
        touch = {"channel": ch_id, "ts": time.time(), "delivered": delivered, "copy": body}
        return touch

    async def start(self, template_id: str, phone: str, email: str, name: str) -> dict:
        tmpl = TEMPLATES_BY_ID.get(template_id) or TEMPLATES[0]
        jid = db.journey_create(tmpl["id"], (name or "there").strip(), (phone or "").strip(),
                                (email or "").strip(), tmpl["steps"], tmpl.get("goal", "click"))
        j = db.journey_get(jid)
        touch = await self._send_step(j, 0)
        db.journey_update(jid, step_idx=0, last_step_ts=time.time(),
                          next_due_ts=time.time() + _wait(), touches=[touch])
        j = db.journey_get(jid)
        await self._emit("started", j)
        return j

    def _engaged(self, j: dict) -> bool:
        since = j.get("last_step_ts") or 0.0
        for addr in (j.get("phone"), j.get("email")):
            if addr and db.engagement_for(addr, since):
                return True
        return False

    async def _advance(self, j: dict):
        jid = j["id"]
        if self._engaged(j):
            db.journey_update(jid, status="converted")
            await self._emit("converted", db.journey_get(jid))
            return
        nxt = (j.get("step_idx") or 0) + 1
        if nxt >= len(j["steps"]):
            db.journey_update(jid, status="exhausted")
            await self._emit("exhausted", db.journey_get(jid))
            return
        touch = await self._send_step(j, nxt)
        touches = (j.get("touches") or []) + [touch]
        db.journey_update(jid, step_idx=nxt, last_step_ts=time.time(),
                          next_due_ts=time.time() + _wait(), touches=touches)
        await self._emit("step", db.journey_get(jid), escalated=True)

    async def respond(self, jid: int) -> dict:
        """Simulate a customer response (records engagement) so the next sweep converts it."""
        j = db.journey_get(jid)
        if not j:
            return {"error": "not found"}
        addr = j.get("phone") or j.get("email") or f"journey:{jid}"
        db.record_engagement("reply", j["steps"][max(0, j.get("step_idx") or 0)]["channel"], addr, detail="simulated response")
        # resolve immediately for a snappy demo
        db.journey_update(jid, status="converted")
        j = db.journey_get(jid)
        await self._emit("converted", j)
        return j

    async def _sweep_once(self):
        now = time.time()
        for j in db.journeys_active():
            if (j.get("next_due_ts") or 0) <= now:
                await self._advance(j)

    async def _sweeper(self):
        while True:
            await asyncio.sleep(5)
            try:
                await self._sweep_once()
            except Exception as e:  # noqa: BLE001
                print("[journey] sweep error:", str(e)[:120])

    def start_sweeper(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._sweeper())

    def stop(self):
        if self._task:
            self._task.cancel()

    def state(self) -> dict:
        js = db.journeys_list(60)
        return {
            "templates": [{"id": t["id"], "name": t["name"],
                           "channels": [s["channel"] for s in t["steps"]]} for t in TEMPLATES],
            "journeys": js,
            "wait_sec": _wait(),
            "metrics": {
                "active": len([j for j in js if j["status"] == "active"]),
                "converted": len([j for j in js if j["status"] == "converted"]),
                "exhausted": len([j for j in js if j["status"] == "exhausted"]),
            },
        }
