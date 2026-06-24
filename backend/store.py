"""Cart-recovery engine — Foresight's third-party store integration.

A business plugs its shopping site into Foresight by POSTing cart events
(`cart_updated`, `cart_abandoned`, `purchase`). Foresight then runs the full
loop on a *real* external signal:

    abandoned cart -> predict recovery odds -> issue a budget-safe discount
    -> WhatsApp the customer a deep link back to their cart
    -> they buy (recovered) or not (lost) -> resolve predicted-vs-actual

The discount escalates: start low, and only step up to a bigger discount if the
cheaper one fails *and* the bigger one still fits the per-cart margin and the
daily budget. Every push is recorded in the same proof ledger as everything
else, so recovery shows up as real calibration (predicted odds vs. actual buys).
"""
from __future__ import annotations

import asyncio
import secrets
import time

import appconfig
import channels
import config as C
import db
import tracking


def _int_setting(key: str, default) -> float:
    v = appconfig.get(key)
    try:
        return float(v) if v not in (None, "") else float(default)
    except (TypeError, ValueError):
        return float(default)


class StoreEngine:
    def __init__(self, ctx: dict, broadcast):
        self.ctx = ctx
        self.broadcast = broadcast
        self._task: asyncio.Task | None = None

    # --------------------------------------------------------------- config
    def ingest_key(self) -> str:
        k = appconfig.get("INGEST_API_KEY")
        if not k:
            k = "fs_" + secrets.token_urlsafe(18)
            db.set_setting("INGEST_API_KEY", k)
        return k

    def _store_url(self) -> str:
        return appconfig.get("STORE_CART_URL") or C.STORE_CART_URL

    def _abandon_window(self) -> float:
        return _int_setting("ABANDON_WINDOW_SEC", C.ABANDON_WINDOW_SEC)

    def _escalate_window(self) -> float:
        return _int_setting("ESCALATE_WINDOW_SEC", C.ESCALATE_WINDOW_SEC)

    # --------------------------------------------------------------- budget
    @staticmethod
    def _day_start() -> float:
        return time.time() - 86400  # rolling 24h window

    def _budget_spent(self) -> float:
        spent = 0.0
        for d in db.discounts_issued_since(self._day_start()):
            cart = db.cart_get(d["cart_id"])
            if cart and cart.get("value"):
                spent += cart["value"] * (d["percent"] / 100.0)
        return spent

    def _budget_remaining(self) -> float:
        return max(0.0, C.DAILY_BUDGET_USD - self._budget_spent())

    def _select_tier(self, cart: dict, min_idx: int):
        """Pick the discount tier at `min_idx` if it fits margin + budget.
        Returns (tier_idx, percent, predicted_prob) or None (exhausted)."""
        ladder = C.DISCOUNT_LADDER
        if min_idx >= len(ladder):
            return None
        percent = ladder[min_idx]
        value = cart.get("value") or 0.0
        # Never discount away more than the gross margin.
        if percent / 100.0 >= C.MARGIN_RATE:
            return None
        discount_amt = value * percent / 100.0
        if discount_amt > self._budget_remaining():
            return None
        prob = C.RECOVERY_PROB.get(percent, 0.2)
        return min_idx, percent, prob

    # --------------------------------------------------------------- events
    async def handle_event(self, ev: dict) -> dict:
        t = ev.get("type")
        cart_id = (ev.get("cart_id") or "").strip()
        if not cart_id:
            return {"ok": False, "error": "cart_id required"}
        if t == "purchase":
            return await self._on_purchase(ev)
        explicit = t == "cart_abandoned"
        await self._on_cart(ev, explicit_abandon=explicit)
        return {"ok": True, "cart_id": cart_id, "status": "abandoned" if explicit else "active"}

    async def _on_cart(self, ev: dict, explicit_abandon: bool) -> None:
        cart_id = ev["cart_id"].strip()
        cust = ev.get("customer") or {}
        existing = db.cart_get(cart_id)
        # Don't resurrect a cart we've already acted on via a routine update.
        keep = existing and existing.get("status") in ("pushed", "recovered", "lost")
        status = existing["status"] if keep else "active"
        cart = db.cart_upsert(cart_id, {
            "customer_id": cust.get("id") or (existing or {}).get("customer_id"),
            "name": cust.get("name") or (existing or {}).get("name"),
            "phone": cust.get("phone") or (existing or {}).get("phone"),
            "email": cust.get("email") or (existing or {}).get("email"),
            "items": ev.get("items") or (existing or {}).get("items") or [],
            "value": ev.get("value") if ev.get("value") is not None else (existing or {}).get("value"),
            "currency": ev.get("currency") or "INR",
            "status": status,
        })
        await self._emit("cart_updated", cart)
        if explicit_abandon and cart.get("status") == "active":
            await self._recover(cart, 0)

    async def _on_purchase(self, ev: dict) -> dict:
        cart_id = ev["cart_id"].strip()
        value = ev.get("value") or 0.0
        code = ev.get("discount_code")
        cart = db.cart_get(cart_id)
        ledger = self.ctx["ledger"]
        attributed, recovered, run_id = False, False, None

        if cart and cart.get("status") == "pushed" and cart.get("proof_id"):
            # The push worked — resolve the prediction as a real recovery.
            ledger.resolve(cart["proof_id"], 1.0)
            if code or cart.get("discount_code"):
                db.discount_redeem(code or cart["discount_code"], value)
            db.cart_update(cart_id, status="recovered", recovered_value=value)
            db.update_run(cart["run_id"], status="recovered",
                          summary={"recovered_value": value, "code": code or cart.get("discount_code")})
            db.record_engagement("purchase", "whatsapp", cart.get("phone") or "", cart["run_id"],
                                 detail=f"recovered ₹{value:,.0f} via {code or cart.get('discount_code') or 'n/a'}")
            attributed, recovered, run_id = True, True, cart["run_id"]
            cart = db.cart_get(cart_id)
        else:
            # Organic purchase (no active recovery push).
            if cart:
                db.cart_update(cart_id, status="recovered", recovered_value=value)
                cart = db.cart_get(cart_id)
            db.record_engagement("purchase", "store", (cart or {}).get("phone") or "", None,
                                 detail=f"organic ₹{value:,.0f}")

        await self._emit("purchase", cart or {"cart_id": cart_id}, attributed=attributed, value=value)
        return {"ok": True, "attributed": attributed, "run_id": run_id, "recovered": recovered}

    # ------------------------------------------------------------- recovery
    async def _recover(self, cart: dict, min_idx: int) -> None:
        # If we're escalating, the previous (cheaper) push failed to convert —
        # resolve its prediction as actual=0 so each tier gets honest calibration.
        if cart.get("status") == "pushed" and cart.get("proof_id"):
            self.ctx["ledger"].resolve(cart["proof_id"], 0.0)
        sel = self._select_tier(cart, min_idx)
        if not sel:
            await self._give_up(cart, "no tier fits budget/margin" if min_idx < len(C.DISCOUNT_LADDER)
                                else "discount ladder exhausted")
            return
        tier_idx, percent, prob = sel
        cart_id = cart["cart_id"]
        value = cart.get("value") or 0.0
        name = cart.get("name") or "there"
        phone = cart.get("phone") or ""
        items = cart.get("items") or []
        item_name = items[0].get("name") if items and isinstance(items[0], dict) else "your items"
        discount_amt = value * percent / 100.0
        expected_rev = prob * value
        code = f"BACK{percent}-{secrets.token_hex(2).upper()}"

        # Run + proof entry (shared ledger -> shows up in Proof calibration).
        run_id = db.insert_run("cart_recovery", f"Cart recovery · {name}", name, "whatsapp", {
            "cart_id": cart_id, "value": value, "tier": tier_idx, "percent": percent, "code": code})
        ledger = self.ctx["ledger"]
        body = (f"Hi {name}, you left {item_name} in your cart 🛒 "
                f"Here's {percent}% off to finish up — code {code}.")
        entry = ledger.record_decision(
            source="cart_recovery", run_id=run_id, customer_id=cart.get("customer_id") or cart_id,
            first_name=name, segment="Cart abandoner", intervention="cart_recovery_push",
            intervention_label=f"{percent}% comeback offer", channel="whatsapp",
            predicted_rel_lift=prob, predicted_revenue=expected_rev, cost=discount_amt,
            message=body, message_source="template")
        proof_id = entry["id"]
        db.discount_create(code, cart_id, percent, run_id, proof_id, expires_ts=time.time() + 86400)

        # Deep link back to the exact cart with the code applied.
        store_url = self._store_url().replace("{cart_id}", cart_id)
        dest = f"{store_url}{'&' if '?' in store_url else '?'}fs_code={code}"
        tracked = tracking.append_link(body, run_id, "whatsapp", phone, url=dest)

        delivered, provider, err = False, "", ""
        ch = channels.get_channel("whatsapp")
        if ch and ch.configured() and phone:
            res = await asyncio.to_thread(ch.send, phone, tracked, {"run_id": run_id, "kind": "cart_recovery"})
            delivered, provider, err = res.ok, res.provider_id, res.error
            db.log_channel(channel="whatsapp", to_addr=phone, body=tracked,
                           status="sent" if res.ok else "failed", provider_id=provider, error=err,
                           run_id=run_id, meta={"kind": "cart_recovery", "sandbox": res.sandbox})
        db.record_engagement("push", "whatsapp", phone, run_id, detail=f"{percent}% / {code}")
        db.cart_update(cart_id, status="pushed", tier=tier_idx, run_id=run_id, proof_id=proof_id,
                       discount_code=code, last_push_ts=time.time())
        db.update_run(run_id, status="pushed", summary={
            "percent": percent, "code": code, "predicted_prob": prob,
            "expected_revenue": round(expected_rev, 2), "discount_cost": round(discount_amt, 2),
            "delivered": delivered, "tier": tier_idx})
        cart = db.cart_get(cart_id)
        escalated = min_idx > 0
        await self._emit("push", cart, percent=percent, code=code, prob=prob,
                         delivered=delivered, escalated=escalated, tier=tier_idx)

    async def _give_up(self, cart: dict, reason: str) -> None:
        # Only abandon a cart we actually pushed to (its last proof was already
        # resolved as actual=0 by _recover before we got here).
        if cart.get("status") != "pushed":
            return
        db.cart_update(cart["cart_id"], status="lost")
        if cart.get("run_id"):
            db.update_run(cart["run_id"], status="lost", summary={"reason": reason})
        await self._emit("lost", db.cart_get(cart["cart_id"]), reason=reason)

    # ----------------------------------------------------------- discounts
    def validate_code(self, code: str) -> dict:
        d = db.discount_get(code)
        if not d:
            return {"valid": False}
        if d.get("expires_ts") and d["expires_ts"] < time.time():
            return {"valid": False, "reason": "expired"}
        return {"valid": True, "percent": d["percent"], "cart_id": d["cart_id"],
                "expires_at": d.get("expires_ts")}

    # --------------------------------------------------------------- sweeper
    async def _sweep_once(self) -> None:
        now = time.time()
        for cart in db.carts_by_status("active"):
            if cart.get("phone") and now - (cart.get("updated_ts") or 0) > self._abandon_window():
                await self._recover(cart, 0)
        for cart in db.carts_by_status("pushed"):
            if now - (cart.get("last_push_ts") or 0) > self._escalate_window():
                await self._recover(cart, (cart.get("tier") or 0) + 1)

    async def _sweeper(self) -> None:
        while True:
            await asyncio.sleep(8)
            try:
                await self._sweep_once()
            except Exception as e:  # never let the loop die
                print("[store] sweeper error:", e)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._sweeper())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()

    # --------------------------------------------------------------- emit
    async def _emit(self, event: str, cart: dict, **extra) -> None:
        await self.broadcast({"type": "store", "event": event, "cart": cart, **extra})

    # --------------------------------------------------------------- demo
    async def simulate(self) -> dict:
        """Create a fake abandoned cart and fire recovery — safe demo button."""
        n = secrets.randbelow(9000) + 1000
        cid = f"sim_{n}"
        products = [("Kurta Set", 1299), ("Sneakers", 2499), ("Tote Bag", 899),
                    ("Watch", 3499), ("Headphones", 1999)]
        name, price = products[secrets.randbelow(len(products))]
        phone = appconfig.get("DEMO_RECOVERY_PHONE") or appconfig.get("TWILIO_WHATSAPP_TO") or ""
        await self._on_cart({
            "type": "cart_abandoned", "cart_id": cid,
            "customer": {"id": f"u_{n}", "name": "Demo Shopper", "phone": phone},
            "items": [{"name": name, "qty": 1, "price": price}], "value": float(price), "currency": "INR",
        }, explicit_abandon=True)
        return db.cart_get(cid)

    # --------------------------------------------------------------- manual
    async def manual_nudge(self, name: str, phone: str, value: float = 0.0,
                           item: str | None = None, cart_id: str | None = None) -> dict:
        """Operator-triggered nudge — WhatsApp a specific customer a discount now.
        Safety net for the demo when no live cart event has fired."""
        cart_id = (cart_id or "").strip() or f"manual_{secrets.token_hex(3)}"
        value = float(value or 0.0)
        cart = db.cart_upsert(cart_id, {
            "customer_id": cart_id, "name": (name or "there").strip(),
            "phone": (phone or "").strip(),
            "items": [{"name": item or "your items", "qty": 1, "price": value}],
            "value": value, "currency": "INR", "status": "active",
        })
        await self._emit("cart_updated", cart)
        await self._recover(cart, 0)
        return db.cart_get(cart_id)

    # --------------------------------------------------------------- state
    def state(self) -> dict:
        carts = db.carts_list(80)
        acted = [c for c in carts if c.get("status") in ("pushed", "recovered", "lost")]
        recovered = [c for c in carts if c.get("status") == "recovered"]
        lost = [c for c in carts if c.get("status") == "lost"]
        pending = [c for c in carts if c.get("status") == "pushed"]
        resolved = len(recovered) + len(lost)
        recovered_value = sum(c.get("recovered_value") or 0 for c in recovered)
        return {
            "carts": carts,
            "metrics": {
                "active": len([c for c in carts if c.get("status") == "active"]),
                "pushed": len(acted),
                "awaiting": len(pending),
                "recovered": len(recovered),
                "lost": len(lost),
                "recovery_rate": round(100 * len(recovered) / resolved, 1) if resolved else None,
                "recovered_value": round(recovered_value, 2),
                "budget_spent": round(self._budget_spent(), 2),
                "budget_cap": C.DAILY_BUDGET_USD,
            },
            "ladder": C.DISCOUNT_LADDER,
            "abandon_window": self._abandon_window(),
            "ingest_key_set": bool(appconfig.get("INGEST_API_KEY")),
            "store_url": self._store_url(),
        }
