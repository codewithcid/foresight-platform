"""The canonical tool registry: every capability Foresight's internal agents
have is defined exactly once here, with a name/description/JSON-schema the
same way an LLM tool-calling API expects. Two consumers share this registry
unmodified:

  1. The in-app Supervisor agent (backend/supervisor.py) -- a business user
     asks a free-form question, Groq decides which of these tools to call.
  2. The standalone MCP server (backend/mcp_server.py) -- the same tools,
     exposed over the Model Context Protocol so an external MCP client
     (Claude Desktop, another agent) can call them too.

Keeping one registry instead of two parallel implementations is the point:
whatever the in-app agent can do, the external MCP surface can do, exactly.
"""


import asyncio
from dataclasses import dataclass
from typing import Any, Callable

import channels
import config as C
import db
import explainer
import forecast
import occasions as O
import workflow as workflow_mod
from clock import CLOCK


async def _noop(_payload):  # broadcast sink for agent-initiated workflow runs
    return None


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., Any]


def _customer_brief(ctx: dict, customer_id: str):
    row = ctx["agent_loop"].get_customer(customer_id)
    seg_label = row.segment
    from config import SEGMENTS
    return row, SEGMENTS[row.segment]["label"]


def build_tools(ctx: dict) -> list[Tool]:
    engine = ctx["engine"]
    ledger = ctx["ledger"]
    trend_analyzer = ctx["trend_analyzer"]
    shopper_registry = ctx["shopper_registry"]
    signal_registry = ctx.get("signal_registry")
    bandit = ctx.get("bandit")
    memory = ctx["memory"]
    agent_loop = ctx["agent_loop"]

    def predict_uplift(customer_id: str) -> dict:
        row = agent_loop.get_customer(customer_id)
        preds = engine.predict_for_customer(row)
        preds.sort(key=lambda p: p.expected_roi, reverse=True)
        return {"customer_id": customer_id, "segment": row.segment, "predictions": [
            {"intervention": p.intervention, "predicted_rel_lift": round(p.predicted_rel_lift, 3),
             "expected_revenue": round(p.expected_revenue, 2), "expected_roi": round(p.expected_roi, 2)}
            for p in preds
        ]}

    def forecast_trend(tag: str = "") -> dict:
        # Plain `str` with a "" sentinel rather than `str | None` -- some
        # installed versions of the mcp SDK introspect tool parameters with
        # `issubclass(annotation, Context)`, which raises on a Union/Optional
        # annotation instead of just returning False. Keeping every
        # MCP-registered tool's signature to plain classes avoids depending on
        # exactly which mcp version ends up installed.
        if tag:
            return forecast.forecast_tag(tag)
        return {"rising": forecast.rising_tags(8)}

    def explain_decision(entry_id: int) -> dict:
        return explainer.explain_entry(ledger, engine, entry_id)

    def summarize_customer(customer_id: str) -> dict:
        from context import summarize_customer as _summarize
        row = agent_loop.get_customer(customer_id)
        from config import SEGMENTS
        return _summarize(customer_id, row.first_name, SEGMENTS[row.segment]["label"], shopper_registry, memory)

    def bandit_status() -> dict:
        if bandit is None:
            return {"arms": []}
        return {"arms": bandit.status()}

    def get_active_occasions() -> dict:
        active = O.active_occasions(CLOCK.now())
        return {"now": CLOCK.now().isoformat(), "active": [
            {"key": o.key, "label": o.label, "theme": o.theme, "tags": o.tags} for o in active
        ]}

    def list_demo_customers() -> dict:
        import datagen
        return {"customers": datagen.DEMO_PERSONAS}

    def customer_conversation_signal(customer_id: str) -> dict:
        if signal_registry is None:
            return {"intent": "unknown", "sentiment": "unknown"}
        sig = signal_registry.get(customer_id)
        return {"intent": sig.intent, "sentiment": sig.sentiment, "opt_out": sig.opt_out}

    # ---- cross-channel + workflow tools (drive the real system) ----
    engine_wf = ctx.get("workflow")

    def channel_status() -> dict:
        return {"channels": [{"id": c["id"], "mode": c["mode"]} for c in channels.status_list()]}

    def send_message(channel: str, to: str, body: str) -> dict:
        ch = channels.get_channel(channel)
        if ch is None:
            return {"error": f"unknown channel {channel}"}
        res = ch.send(to, body, meta={"kind": "agent"})
        db.log_channel(channel=ch.id, to_addr=to, body=body,
                       status="sent" if res.ok else "failed",
                       provider_id=res.provider_id, error=res.error, meta={"kind": "agent"})
        return res.as_dict()

    def list_workflows() -> dict:
        return {"templates": [{"id": t["id"], "label": t["label"], "segment": t["segment"],
                               "intervention": t["intervention"], "channel": t["channel"]}
                              for t in workflow_mod.TEMPLATES]}

    def run_workflow(workflow: str = "", segment: str = "", intervention: str = "", channel: str = "") -> dict:
        if engine_wf is None:
            return {"error": "workflow engine unavailable in this context"}
        tmpl = next((t for t in workflow_mod.TEMPLATES if t["id"] == workflow), None)
        params = {
            "workflow": workflow or "custom",
            "segment": segment or (tmpl["segment"] if tmpl else ""),
            "intervention": intervention or (tmpl["intervention"] if tmpl else ""),
            "channel": channel or (tmpl["channel"] if tmpl else "sms"),
        }
        if params["segment"] not in C.SEGMENTS or params["intervention"] not in C.INTERVENTIONS:
            return {
                "error": "invalid segment or intervention",
                "valid_segments": list(C.SEGMENTS.keys()),
                "valid_interventions": list(C.INTERVENTIONS.keys()),
                "templates": [t["id"] for t in workflow_mod.TEMPLATES],
            }
        run = asyncio.run(engine_wf.run(params, _noop))
        s = run.get("summary") or {}
        return {"run_id": run["id"], "status": run["status"], "reach": s.get("reach"),
                "predicted_rel_lift_pct": round((s.get("avg_rel_lift") or 0) * 100, 1),
                "predicted_incr_revenue": s.get("pred_incr_revenue"),
                "winner_copy": s.get("winner_copy"),
                "note": "Paused for human approval — call approve_run(run_id) to send + prove."}

    def approve_run(run_id: int, test_recipient: str = "") -> dict:
        if engine_wf is None:
            return {"error": "workflow engine unavailable in this context"}
        run = asyncio.run(engine_wf.approve(int(run_id), _noop, test_recipient=test_recipient))
        s = run.get("summary") or {}
        return {"run_id": run["id"], "status": run["status"],
                "predicted_rel_lift_pct": round((s.get("avg_rel_lift") or 0) * 100, 1),
                "actual_rel_lift_pct": round((s.get("actual_rel_lift") or 0) * 100, 1),
                "error_pp": s.get("error_pp"), "delivered": s.get("delivered")}

    def reject_run(run_id: int) -> dict:
        if engine_wf is None:
            return {"error": "workflow engine unavailable in this context"}
        run = asyncio.run(engine_wf.reject(int(run_id), _noop))
        return {"run_id": run["id"], "status": run["status"]}

    def list_runs(limit: int = 10) -> dict:
        return {"runs": [{"id": r["id"], "label": r["label"], "status": r["status"],
                          "target": r.get("target"), "channel": r.get("channel"),
                          "error_pp": (r.get("summary") or {}).get("error_pp")}
                         for r in db.list_runs(limit)]}

    store = ctx.get("store")

    def store_status() -> dict:
        if store is None:
            return {"error": "cart-recovery (Link-Up) unavailable"}
        return store.state().get("metrics", {})

    def proof_summary() -> dict:
        runs = [r for r in db.list_runs(50)
                if r["status"] == "proven" and (r.get("summary") or {}).get("actual_rel_lift") is not None]
        if not runs:
            return {"proven_runs": 0}
        errs = [r["summary"]["error_pp"] for r in runs]
        rev = sum(r["summary"].get("pred_incr_revenue", 0) for r in runs)
        return {"proven_runs": len(runs), "mean_error_pp": round(sum(errs) / len(errs), 1),
                "total_predicted_incr_revenue": round(rev, 0)}

    return [
        Tool("predict_uplift", "Predict the lift of every candidate marketing action for one customer by ID.",
             {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
             predict_uplift),
        Tool("forecast_trend",
             "Forecast whether a PRODUCT/STYLE tag's engagement is rising or falling (e.g. 'diwali', 'ipl', "
             "'winter', 'ethnic' -- catalog tags, NOT customer segments like 'bargain_hunter'). "
             "Omit the tag to list the top rising tags overall.",
             {"type": "object", "properties": {"tag": {"type": "string", "description": "A catalog product tag, not a customer segment."}}},
             forecast_trend),
        Tool("explain_decision", "Get the structured factors + plain-English explanation for a specific ledger entry ID.",
             {"type": "object", "properties": {"entry_id": {"type": "integer"}}, "required": ["entry_id"]},
             explain_decision),
        Tool("summarize_customer", "Get an LLM-compacted profile summary of a customer's behavior and conversation history by ID.",
             {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
             summarize_customer),
        Tool("bandit_status", "Get the contextual bandit's learned reliability per (segment, intervention) arm.",
             {"type": "object", "properties": {}}, bandit_status),
        Tool("get_active_occasions", "Get the festivals/seasons/sports currently active on the (virtual) clock.",
             {"type": "object", "properties": {}}, get_active_occasions),
        Tool("list_demo_customers", "List the named demo customer personas available in this environment.",
             {"type": "object", "properties": {}}, list_demo_customers),
        Tool("customer_conversation_signal", "Get a customer's latest chat-derived intent/sentiment signal by ID.",
             {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]},
             customer_conversation_signal),
        Tool("channel_status", "List the delivery channels (sms, whatsapp, slack, email, telegram) and whether each is live, sandbox, or needs a key.",
             {"type": "object", "properties": {}}, channel_status),
        Tool("send_message", "Send a message NOW on a real channel. channel is one of sms/whatsapp/slack; to is a phone number (or Slack channel); body is the text.",
             {"type": "object", "properties": {"channel": {"type": "string"}, "to": {"type": "string"}, "body": {"type": "string"}}, "required": ["channel", "to", "body"]},
             send_message),
        Tool("list_workflows", "List the available campaign workflow templates (id, segment, intervention, channel).",
             {"type": "object", "properties": {}}, list_workflows),
        Tool("run_workflow", "Launch a campaign workflow (predict -> guardrail -> generate -> pre-test -> PAUSE for approval). Pass a template id as 'workflow', OR a 'segment' + 'intervention' (+ optional 'channel'). Returns a run_id awaiting approval.",
             {"type": "object", "properties": {"workflow": {"type": "string"}, "segment": {"type": "string"}, "intervention": {"type": "string"}, "channel": {"type": "string"}}},
             run_workflow),
        Tool("approve_run", "Approve a paused workflow run by id: delivers the creative on its channel (optionally to test_recipient) and resolves predicted-vs-actual proof.",
             {"type": "object", "properties": {"run_id": {"type": "integer"}, "test_recipient": {"type": "string"}}, "required": ["run_id"]},
             approve_run),
        Tool("reject_run", "Reject/cancel a paused workflow run by id.",
             {"type": "object", "properties": {"run_id": {"type": "integer"}}, "required": ["run_id"]},
             reject_run),
        Tool("list_runs", "List recent workflow runs with their status and prediction error.",
             {"type": "object", "properties": {"limit": {"type": "integer"}}}, list_runs),
        Tool("proof_summary", "Summarize proven campaigns: count, mean predicted-vs-actual error (pp), and total predicted incremental revenue.",
             {"type": "object", "properties": {}}, proof_summary),
        Tool("store_status", "Link-Up cart-recovery status: carts acted on, recovered, lost, recovery rate, recovered revenue, and discount spend vs budget.",
             {"type": "object", "properties": {}}, store_status),
    ]
