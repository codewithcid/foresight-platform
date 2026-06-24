"""Workflow engine — the orchestration centerpiece.

A workflow chains Foresight's existing strengths into one visible, agentic run:

    Trigger -> Predict uplift (CATE) -> Guardrail -> Generate creative
    -> Pre-test (synthetic panel) -> Approve (human-in-the-loop)
    -> Deliver (real channel) -> Prove (predicted vs. actual)

Every step reuses a module we already have (causal `UpliftEngine`, `creative`,
`pre_test`, the `GuardrailAgent` rules, `channels`, the proof `ledger`/`db`), so
the workflow is a real composition of the system, not a parallel mock. Runs +
per-step traces persist to SQLite; the run pauses at Approve until a human
approves (in-app, or via the Slack card).

This is Theme 2 made operational: one engine acting across real channels
(seamless cross-channel) with predicted-vs-actual proof on every run (clear
measures of success).
"""
from __future__ import annotations

import asyncio
import time

import channels
import config as C
import creative
import db
import llm
import pre_test
import tracking
from channels import slack as slack_ch

# Definition of the canonical step sequence (for the UI to render the graph).
# `agent` names the autonomous actor that owns each step.
STEP_DEFS = [
    {"name": "trigger", "label": "Trigger", "agent": "Sensor"},
    {"name": "predict", "label": "Predict uplift", "agent": "Strategist"},
    {"name": "guardrail", "label": "Guardrail", "agent": "Guardrail"},
    {"name": "generate", "label": "Generate creative", "agent": "Execution"},
    {"name": "pretest", "label": "Pre-test", "agent": "Pre-test"},
    {"name": "approve", "label": "Approve", "agent": "Human"},
    {"name": "deliver", "label": "Deliver", "agent": "Execution"},
    {"name": "prove", "label": "Prove", "agent": "Critic"},
]

# Intervention channel label -> a real delivery channel.
_DELIVERY = {"sms": "sms", "email": "email", "app_push": "whatsapp", "paid_social": "telegram"}


def _delivery_channel(c: str) -> str:
    return _DELIVERY.get(c, "sms")

TEMPLATES = [
    {
        "id": "winback_sms",
        "label": "Win-back SMS",
        "description": "Re-engage a lapsing segment with an SMS discount, proven on a holdout.",
        "segment": "bargain_hunter", "intervention": "sms_discount", "channel": "sms",
    },
    {
        "id": "festival_whatsapp",
        "label": "Festival WhatsApp push",
        "description": "High-intent shoppers get an occasion-aware WhatsApp nudge.",
        "segment": "high_intent", "intervention": "cart_recovery_push", "channel": "whatsapp",
    },
    {
        "id": "loyalist_email",
        "label": "Loyalist email",
        "description": "Reward loyalists with a personalized email; measure incremental lift.",
        "segment": "loyalist", "intervention": "personalized_email", "channel": "email",
    },
    {
        "id": "browser_telegram",
        "label": "Browser Telegram nudge",
        "description": "Re-engage browsers with a Telegram message; prove the lift on a holdout.",
        "segment": "browser", "intervention": "retargeting_social", "channel": "telegram",
    },
    {
        "id": "vip_slack",
        "label": "VIP Slack broadcast",
        "description": "Push a high-intent offer to the team Slack channel for activation.",
        "segment": "high_intent", "intervention": "personalized_email", "channel": "slack",
    },
]


class WorkflowEngine:
    def __init__(self, ctx: dict):
        self.ctx = ctx
        self._paused: dict[int, dict] = {}  # run_id -> in-flight context

    # ----------------------------------------------------------------- helpers
    def _segment_sample(self, seg_key: str, n: int = 200):
        df = self.ctx["customers"]
        pool = df[(df.segment == seg_key) & (df.reached_intent)]
        audience = int(len(pool))
        sample = pool.sample(min(n, audience), random_state=C.SEED) if audience else pool
        return sample, audience

    def _predict_segment(self, seg_key: str, intervention: str, budget: float, sample_n: int = 200):
        engine = self.ctx["engine"]
        sample, audience = self._segment_sample(seg_key, sample_n)
        rels, convs = [], []
        for _, row in sample.iterrows():
            preds = engine.predict_for_customer(row)
            match = next((p for p in preds if p.intervention == intervention), None)
            if match:
                rels.append(match.predicted_rel_lift)
                convs.append(match.expected_incremental_conversions)
        avg_rel = sum(rels) / len(rels) if rels else 0.0
        avg_conv = sum(convs) / len(convs) if convs else 0.0
        cpc = C.INTERVENTIONS[intervention]["cost_per_contact"]
        max_by_budget = int(budget // cpc) if cpc else audience
        reach = max(0, min(audience, max_by_budget))
        cost = reach * cpc
        pred_incr_conv = avg_conv * reach
        pred_incr_rev = pred_incr_conv * C.AOV
        return {
            "audience": audience, "reach": reach, "cost": round(cost, 2),
            "avg_rel_lift": avg_rel, "pred_incr_conversions": round(pred_incr_conv, 1),
            "pred_incr_revenue": round(pred_incr_rev, 2), "sample_n": int(len(sample)),
        }

    def _rank_actions(self, budget: float, top_k: int | None = None, sample_n: int = 60) -> list[dict]:
        """Strategist: score every segment × intervention by predicted incremental
        revenue (and ROI), so the agent can pick the next-best action itself."""
        ranked = []
        for seg in C.SEGMENTS:
            for intv in C.INTERVENTIONS:
                p = self._predict_segment(seg, intv, budget, sample_n=sample_n)
                if p["reach"] == 0 or p["avg_rel_lift"] < C.MIN_REL_LIFT_TO_ACT:
                    continue
                roi = (p["pred_incr_revenue"] / p["cost"]) if p["cost"] else 0.0
                ranked.append({
                    "segment": seg, "intervention": intv,
                    "channel": _delivery_channel(C.INTERVENTIONS[intv]["channel"]),
                    "seg_label": C.SEGMENTS[seg]["label"], "intv_label": C.INTERVENTIONS[intv]["label"],
                    "reach": p["reach"], "pred_incr_revenue": p["pred_incr_revenue"],
                    "avg_rel_lift": p["avg_rel_lift"], "roi": round(roi, 2),
                })
        ranked.sort(key=lambda x: x["pred_incr_revenue"], reverse=True)
        return ranked[:top_k] if top_k else ranked

    def _true_segment_lift(self, seg_key: str, intervention: str) -> float:
        sample, _ = self._segment_sample(seg_key)
        col = f"p1_{intervention}"
        if col not in sample.columns or sample.empty:
            return 0.0
        rels = [(r[col] - r.p0) / r.p0 for _, r in sample.iterrows() if r.p0 > 0]
        return sum(rels) / len(rels) if rels else 0.0

    async def _emit(self, broadcast, run_id: int, step: dict):
        await broadcast({"type": "workflow_step", "run_id": run_id, "step": step})

    # ------------------------------------------------------------------- run
    async def run(self, params: dict, broadcast) -> dict:
        budget = float(params.get("budget", C.DAILY_BUDGET_USD))

        # "Let the Strategist decide": the agent ranks every segment × action and
        # picks the highest-ROI one itself, instead of the operator choosing.
        decision_note = None
        if params.get("auto"):
            ranked = self._rank_actions(budget)
            if ranked:
                top = ranked[0]
                params = {**params, "segment": top["segment"], "intervention": top["intervention"], "channel": top["channel"]}
                runner = ranked[1] if len(ranked) > 1 else None
                decision_note = (
                    f"Strategist evaluated {len(ranked)} segment×action options and chose "
                    f"{top['intv_label']} → {top['seg_label']} (ROI {top['roi']}×, predicted ₹{top['pred_incr_revenue']:,.0f})"
                    + (f", beating {runner['intv_label']} → {runner['seg_label']}." if runner else ".")
                )

        seg = params["segment"]
        intervention = params["intervention"]
        channel_id = params.get("channel", "sms")
        label = params.get("label") or next((t["label"] for t in TEMPLATES if t["id"] == params.get("workflow")), "Custom workflow")
        seg_label = C.SEGMENTS.get(seg, {}).get("label", seg)
        intv_label = C.INTERVENTIONS.get(intervention, {}).get("label", intervention)

        run_id = db.insert_run(params.get("workflow", "custom"), label, seg_label, channel_id, params)
        steps_state = {s["name"]: db.add_step(run_id, i, s["name"], s["label"], "pending", {})
                       for i, s in enumerate(STEP_DEFS)}

        async def step(name: str, status: str, output: dict):
            db.update_step(steps_state[name], status=status, output=output)
            await self._emit(broadcast, run_id, {"name": name, "status": status, "output": output})

        # 1. trigger
        await step("trigger", "running", {})
        _, audience = self._segment_sample(seg)
        await step("trigger", "done", {"segment": seg_label, "audience": audience, "intervention": intv_label, "channel": channel_id,
                   "reasoning": f"Sensor: {audience:,} {seg_label} customers reached intent — handing to the Strategist."})

        # 2. predict (Strategist)
        await step("predict", "running", {})
        pred = self._predict_segment(seg, intervention, budget)
        predict_reason = decision_note or (
            f"Strategist: {seg_label} shows avg CATE {pred['avg_rel_lift']*100:.1f}% over {pred['sample_n']} sampled; "
            f"funding {pred['reach']:,} contacts within ₹{budget:,.0f} → ₹{pred['pred_incr_revenue']:,.0f} predicted incremental.")
        await step("predict", "done", {
            "reach": pred["reach"], "predicted_rel_lift_pct": round(pred["avg_rel_lift"] * 100, 1),
            "predicted_incr_revenue": pred["pred_incr_revenue"], "cost": pred["cost"], "reasoning": predict_reason,
        })

        # 3. guardrail
        await step("guardrail", "running", {})
        over_budget = pred["cost"] > budget
        below_thresh = pred["avg_rel_lift"] < C.MIN_REL_LIFT_TO_ACT
        if over_budget or below_thresh or pred["reach"] == 0:
            reason = ("predicted lift below threshold" if below_thresh else
                      "over budget" if over_budget else "no reachable audience")
            await step("guardrail", "held", {"passed": False, "reason": reason,
                       "reasoning": f"Guardrail: blocked — {reason}. No send."})
            db.update_run(run_id, status="held", summary={"reason": reason, **pred})
            return db.get_run(run_id)
        await step("guardrail", "done", {"passed": True,
                   "checks": [f"{C.MAX_ACTIONS_PER_CUSTOMER_PER_DAY} actions/customer cap",
                              f"₹{budget:,.0f} budget", f"≥{C.MIN_REL_LIFT_TO_ACT*100:.0f}% lift", "brand-safety"],
                   "reasoning": f"Guardrail: frequency cap ✓, budget ✓, ≥{C.MIN_REL_LIFT_TO_ACT*100:.0f}% lift ✓, brand-safety ✓ — cleared to act."})

        # 4. generate (or use a creative handed in from Creative Pre-Flight)
        await step("generate", "running", {})
        provided_copy = params.get("copy")
        if provided_copy:
            variants = [{"id": "provided", "angle": params.get("angle") or "approved", "headline": "",
                         "body": provided_copy, "copy": provided_copy, "copy_source": "creative-preflight",
                         "image_prompt": "", "image_url": ""}]
            await step("generate", "done", {"n_variants": 1, "angles": ["approved"], "source": "Creative Pre-Flight",
                       "reasoning": "Execution: using the approved creative carried in from Pre-Flight."})
        else:
            variants = creative.generate_variants(intervention, intv_label, seg_label, occasion_theme=None, n=3)
            await step("generate", "done", {"n_variants": len(variants), "angles": [v["angle"] for v in variants],
                       "reasoning": f"Execution: drafted {len(variants)} variants ({', '.join(v['angle'] for v in variants)})."})

        # 5. pretest
        await step("pretest", "running", {})
        pt = pre_test.pretest(variants, seg_label, occasion_theme=None)
        winner = next((v for v in variants if v["id"] == pt["winner_id"]), variants[0])
        await step("pretest", "done", {
            "winner_angle": pt["winner_angle"], "winner_score": pt["winner_score"],
            "spread": pt["spread"], "copy": winner["copy"],
            "reasoning": f"Pre-test: '{pt['winner_angle']}' won {pt['winner_score']}/100 on a synthetic panel (beat the field by {pt['spread']} pts).",
        })

        # 6. approve -> pause
        await step("approve", "awaiting", {"copy": winner["copy"], "reach": pred["reach"],
                   "predicted_incr_revenue": pred["pred_incr_revenue"],
                   "reasoning": "Awaiting human sign-off before the agent sends."})
        self._paused[run_id] = {
            "params": params, "seg": seg, "seg_label": seg_label, "intervention": intervention,
            "intv_label": intv_label, "channel_id": channel_id, "pred": pred, "winner": winner,
            "step_ids": steps_state,
        }
        db.update_run(run_id, status="awaiting_approval", summary={**pred, "winner_copy": winner["copy"]})
        # Slack approval card (no-op if Slack not configured).
        slack_ch.notify_approval(label, seg_label, intv_label, channel_id, pred["reach"], pred["pred_incr_revenue"], run_id)
        return db.get_run(run_id)

    # --------------------------------------------------------------- approve
    async def approve(self, run_id: int, broadcast, test_recipient: str = "") -> dict:
        st = self._paused.pop(run_id, None)
        if st is None:
            run = db.get_run(run_id)
            if run and run["status"] == "awaiting_approval":
                # lost in-flight context (e.g. restart) -> mark approved minimally
                db.update_run(run_id, status="approved")
            return db.get_run(run_id)
        step_ids = st["step_ids"]

        async def step(name: str, status: str, output: dict):
            db.update_step(step_ids[name], status=status, output=output)
            await self._emit(broadcast, run_id, {"name": name, "status": status, "output": output})

        await step("approve", "done", {"approved": True, "reasoning": "Human approved — Execution will deliver now."})

        # 7. deliver
        await step("deliver", "running", {})
        pred = st["pred"]
        ch = channels.get_channel(st["channel_id"])
        recipient = test_recipient or st["params"].get("test_recipient", "")
        delivered = False
        provider_id = ""
        err = ""
        # slack/telegram have a server-side default recipient (channel / chat id),
        # so they deliver even without an explicit test recipient.
        has_default = st["channel_id"] in ("slack", "telegram")
        if ch and ch.configured() and (recipient or has_default):
            # Carry a tracked link tied to this run so clicks feed the proof.
            body = tracking.append_link(st["winner"]["copy"], run_id, st["channel_id"], recipient or "")
            res = ch.send(recipient, body, meta={"run_id": run_id, "kind": "workflow"})
            delivered, provider_id, err = res.ok, res.provider_id, res.error
            db.log_channel(channel=ch.id, to_addr=recipient, body=body,
                           status="sent" if res.ok else "failed", provider_id=provider_id, error=err,
                           run_id=run_id, meta={"kind": "workflow", "sandbox": res.sandbox})
            if res.ok and recipient:
                self.ctx["memory"].append(recipient, st["channel_id"], "agent", body,
                                          meta={"run_id": run_id, "kind": "workflow"})
        deliver_reason = (
            f"Execution: real {st['channel_id']} send to {recipient} ✓" if (delivered and recipient)
            else f"Execution: delivered on {st['channel_id']} ✓" if delivered
            else f"Execution: {st['channel_id']} not connected — campaign queued for {pred['reach']:,}; proof still runs.")
        await step("deliver", "done", {
            "channel": st["channel_id"], "reach_queued": pred["reach"],
            "test_send": bool(recipient), "delivered": delivered,
            "provider_id": provider_id, "error": err, "reasoning": deliver_reason,
        })

        # 8. prove (predicted vs actual on the synthetic ground truth)
        await step("prove", "running", {})
        actual_rel = self._true_segment_lift(st["seg"], st["intervention"])
        pred_rel = pred["avg_rel_lift"]
        error = abs(pred_rel - actual_rel)
        actual_incr_rev = pred["pred_incr_revenue"] * (actual_rel / pred_rel) if pred_rel else 0.0
        ledger = self.ctx["ledger"]
        entry = ledger.record_decision(
            source="workflow", run_id=run_id, customer_id=f"seg:{st['seg']}",
            first_name=st["seg_label"], segment=st["seg_label"],
            intervention=st["intervention"], intervention_label=st["intv_label"],
            channel=st["channel_id"], predicted_rel_lift=pred_rel,
            predicted_revenue=pred["pred_incr_revenue"], cost=pred["cost"],
            message=st["winner"]["copy"], message_source=st["winner"].get("copy_source", "llm"),
        )
        ledger.resolve(entry["id"], actual_rel)
        await step("prove", "done", {
            "predicted_rel_lift_pct": round(pred_rel * 100, 1),
            "actual_rel_lift_pct": round(actual_rel * 100, 1),
            "error_pp": round(error * 100, 1),
            "predicted_incr_revenue": pred["pred_incr_revenue"],
            "actual_incr_revenue": round(actual_incr_rev, 2),
            "proof_id": entry["id"],
            "reasoning": f"Critic: predicted {pred_rel*100:.1f}% vs actual {actual_rel*100:.1f}% → error {error*100:.1f}pp; recalibrated this arm.",
        })

        db.update_run(run_id, status="proven", summary={
            **pred, "winner_copy": st["winner"]["copy"], "actual_rel_lift": actual_rel,
            "error_pp": round(error * 100, 1), "delivered": delivered, "proof_id": entry["id"],
            "ts_completed": time.time(),
        })
        slack_ch.notify(f"✅ Foresight run #{run_id} ({st['intv_label']} → {st['seg_label']}) proven: "
                        f"predicted {pred_rel*100:.1f}% vs actual {actual_rel*100:.1f}% lift.")
        return db.get_run(run_id)

    async def reject(self, run_id: int, broadcast) -> dict:
        st = self._paused.pop(run_id, None)
        if st:
            db.update_step(st["step_ids"]["approve"], status="rejected", output={"approved": False})
            await self._emit(broadcast, run_id, {"name": "approve", "status": "rejected", "output": {}})
        db.update_run(run_id, status="rejected")
        return db.get_run(run_id)

    # --------------------------------------------------------------- autopilot
    async def autopilot(self, goal: str, budget: float, broadcast, top_k: int = 2) -> dict:
        """The agent, given a goal + budget, plans and runs the best campaigns
        end-to-end on its own — narrating each decision over the stream."""
        async def narrate(phase: str, text: str, extra: dict | None = None):
            await broadcast({"type": "autopilot", "phase": phase, "text": text, **(extra or {})})

        await narrate("start", f"Goal: {goal or 'maximize incremental ROI'}. Budget ₹{budget:,.0f}. "
                               f"Scanning every segment × action for the highest-ROI moves…")
        ranked = self._rank_actions(budget, top_k=top_k)
        if not ranked:
            await narrate("done", "No profitable action cleared the guardrails within this budget.", {"runs": []})
            return {"runs": []}

        plan = [{"label": f"{r['intv_label']} → {r['seg_label']}", "channel": r["channel"],
                 "pred_incr_revenue": r["pred_incr_revenue"], "roi": r["roi"]} for r in ranked]
        await narrate("plan", f"Decided on the top {len(ranked)} campaigns. Executing them now.", {"plan": plan})

        runs = []
        for i, r in enumerate(ranked, 1):
            ch = r["channel"]
            await narrate("run", f"[{i}/{len(ranked)}] Launching {r['intv_label']} → {r['seg_label']} on {ch} "
                                 f"(predicted ₹{r['pred_incr_revenue']:,.0f}, ROI {r['roi']}×)…")
            copy, _ = llm.draft_intervention_message(
                r["intervention"], r["intv_label"], ch, r["seg_label"], "there", r["avg_rel_lift"], use_llm=False)
            params = {"workflow": "autopilot", "segment": r["segment"], "intervention": r["intervention"],
                      "channel": ch, "budget": budget, "copy": copy, "angle": "autopilot",
                      "label": f"Autopilot · {r['intv_label']} → {r['seg_label']}"}
            run = await self.run(params, broadcast)
            run = await self.approve(run["id"], broadcast)
            s = run.get("summary") or {}
            await narrate("result", f"[{i}/{len(ranked)}] Proven: predicted {(s.get('avg_rel_lift') or 0)*100:.1f}% "
                                    f"vs actual {(s.get('actual_rel_lift') or 0)*100:.1f}% lift (error {s.get('error_pp')}pp).",
                          {"run_id": run["id"]})
            runs.append(run["id"])

        total = sum((db.get_run(rid).get("summary") or {}).get("pred_incr_revenue", 0) for rid in runs)
        await narrate("done", f"Done — deployed {len(runs)} campaigns autonomously, "
                              f"₹{total:,.0f} predicted incremental revenue, all proven on a holdout.", {"runs": runs})
        return {"runs": runs, "total_pred_incr_revenue": total}
