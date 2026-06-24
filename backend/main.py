"""Foresight API.

On startup: generate the synthetic journey + event timeline, train the causal
brain once, and wire up the agent loop (Strategist / Guardrail / Execution /
Critic), the cross-channel memory store, the live simulator, the storefront
catalog + shopper registry, the occasion/trend engine, and the Time Machine.
A websocket streams every autonomous decision + resolution to the frontend's
Mission Control feed; REST endpoints serve the storefront, the WhatsApp-skin
concierge, the CRM campaign drafts, and explainability.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import byocsv
import catalog
import channels
import config as C
import db
import creative
import creative_proof
import datagen
import model_card as model_card_mod
import pre_test
import spend_planner
import explainer
import forecast
import images
import llm
import nlp
import occasions as O
import seed
import supervisor
import tracking
import workflow as workflow_mod
from agent import AgentLoop
from bandit import ThompsonBandit
from causal import UpliftEngine
from clock import CLOCK
from context import ShopperRegistry, TrendAnalyzer
from ledger import Ledger
from memory import MemoryStore
from signals import SignalRegistry
from simulator import LiveSimulator
from tools import build_tools

STATE: dict = {}
_SOCKETS: set[WebSocket] = set()
_PENDING_ABANDON: dict[str, asyncio.Task] = {}


async def broadcast(payload: dict) -> None:
    dead = []
    for ws in _SOCKETS:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _SOCKETS.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    customers = datagen.generate_customers()
    demo_personas = datagen.make_demo_personas()
    timeline = datagen.build_event_timeline(customers)  # synthetic-only replay
    all_customers = pd.concat([customers, demo_personas], ignore_index=True)

    engine = UpliftEngine(customers)  # trained on the synthetic population only
    engine.train()

    memory = MemoryStore()
    ledger = Ledger()
    bandit = ThompsonBandit()
    signal_registry = SignalRegistry()
    agent_loop = AgentLoop(engine, memory, ledger, all_customers, bandit=bandit, signal_registry=signal_registry)
    simulator = LiveSimulator(agent_loop, timeline, broadcast, speed=4.0)
    shopper_registry = ShopperRegistry()
    trend_analyzer = TrendAnalyzer(customers, shopper_registry)

    STATE["customers"] = customers
    STATE["all_customers"] = all_customers
    STATE["engine"] = engine
    STATE["memory"] = memory
    STATE["ledger"] = ledger
    STATE["agent_loop"] = agent_loop
    STATE["simulator"] = simulator
    STATE["shopper_registry"] = shopper_registry
    STATE["trend_analyzer"] = trend_analyzer
    STATE["bandit"] = bandit
    STATE["signal_registry"] = signal_registry

    STATE["creative_ledger"] = creative_proof.CreativeLedger()
    STATE["workflow"] = workflow_mod.WorkflowEngine(STATE)
    seeded = seed.seed_if_empty()  # populate Proof/Command on a fresh DB

    STATE["tools"] = build_tools(STATE)

    photo_count = images.attach_images(catalog.PRODUCTS) if images.has_key() else 0
    print(f"[foresight] ready: {len(customers):,} customers, {len(timeline):,} timeline events, "
          f"{len(catalog.PRODUCTS)} products ({photo_count} with real photos), {len(STATE['tools'])} agent tools, "
          f"llm={'groq' if llm.has_key() else 'template-fallback'}, images={'pexels' if images.has_key() else 'illustrated'}")
    simulator.start()
    yield
    simulator.pause()
    STATE.clear()


app = FastAPI(title="Foresight API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(KeyError)
async def _unknown_id_handler(request: Request, exc: KeyError):
    # Looking up an unknown customer_id raises KeyError deep in pandas'
    # .loc -- surface that as a clean 404 instead of a raw 500/stack trace.
    return JSONResponse(status_code=404, content={"detail": f"not found: {exc}"})


class SpeedRequest(BaseModel):
    speed: float


class ScheduleRequest(BaseModel):
    scheduled_for: str | None = None


class PreflightRequest(BaseModel):
    intervention: str
    segment: str  # segment key
    product_id: str | None = None


class ShipRequest(BaseModel):
    intervention: str
    segment: str  # segment key
    variant_id: str
    angle: str
    copy: str
    image_url: str = ""
    predicted_resonance: float


def _active_occasion_context(product_id: str | None = None) -> tuple[str | None, str | None]:
    active = O.active_occasions(CLOCK.now())
    product_tags = set(catalog.PRODUCTS_BY_ID[product_id]["tags"]) if product_id in catalog.PRODUCTS_BY_ID else None
    occ = O.headline(active, product_tags)
    if occ is None:
        return None, None
    return occ.key, occ.theme


# --------------------------------------------------------------------- core
@app.get("/api/health")
def health():
    return {"status": "ok", "ready": "engine" in STATE}


@app.get("/api/meta")
def meta():
    return {
        "segments": [{"key": k, "label": v["label"]} for k, v in C.SEGMENTS.items()],
        "interventions": [{"key": k, **v} for k, v in C.INTERVENTIONS.items()],
        "concierge_channels": C.CONCIERGE_CHANNELS,
        "guardrails": {
            "max_actions_per_day": C.MAX_ACTIONS_PER_CUSTOMER_PER_DAY,
            "daily_budget_usd": C.DAILY_BUDGET_USD,
            "min_rel_lift_to_act": C.MIN_REL_LIFT_TO_ACT,
        },
        "llm_mode": "groq" if llm.has_key() else "template-fallback",
    }


@app.post("/api/creative/preflight")
def creative_preflight(req: PreflightRequest):
    """Self-testing creative loop: generate ad variants for this
    intervention+segment+occasion, then pre-test them on a synthetic persona
    panel and return the ranked results + winner -- all before anything sends."""
    if req.intervention not in C.INTERVENTION_KEYS:
        raise HTTPException(400, f"unknown intervention {req.intervention!r}")
    if req.segment not in C.SEGMENTS:
        raise HTTPException(400, f"unknown segment {req.segment!r}")
    seg_label = C.SEGMENTS[req.segment]["label"]
    product = catalog.PRODUCTS_BY_ID.get(req.product_id) if req.product_id else None
    product_name = product["name"] if product else None
    occ_key, occ_theme = _active_occasion_context(req.product_id)

    variants = creative.generate_variants(
        req.intervention, C.INTERVENTIONS[req.intervention]["label"], seg_label,
        occasion_theme=occ_theme, product_name=product_name, n=3,
    )
    pt = pre_test.pretest(variants, seg_label, occasion_theme=occ_theme)
    return {
        "intervention": req.intervention,
        "intervention_label": C.INTERVENTIONS[req.intervention]["label"],
        "segment": req.segment, "segment_label": seg_label,
        "occasion_key": occ_key, "occasion_theme": occ_theme,
        "product_id": req.product_id, "product_name": product_name,
        "variants": variants, "pretest": pt,
    }


@app.post("/api/creative/ship")
def creative_ship(req: ShipRequest):
    """Ship the pre-tested winner and measure it: samples the creative's actual
    engagement from hidden ground truth and logs predicted-vs-actual resonance --
    the creative-level proof. Returns the resolved entry + running calibration."""
    if req.segment not in C.SEGMENTS:
        raise HTTPException(400, f"unknown segment {req.segment!r}")
    seg_label = C.SEGMENTS[req.segment]["label"]
    entry = STATE["creative_ledger"].ship(
        intervention=req.intervention,
        intervention_label=C.INTERVENTIONS.get(req.intervention, {}).get("label", req.intervention),
        segment=req.segment, segment_label=seg_label,
        variant_id=req.variant_id, angle=req.angle, copy=req.copy, image_url=req.image_url,
        predicted_resonance=req.predicted_resonance,
    )
    # Close the loop: relay the proven winning creative into a real channel --
    # the demo persona for this segment receives it in the WhatsApp inbox, so
    # the creative the agent *tested* is the creative it actually *ships*.
    persona = next((p for p in datagen.DEMO_PERSONAS if p["segment"] == req.segment), None)
    if persona:
        STATE["memory"].append(
            persona["customer_id"], channel="whatsapp", role="agent", text=req.copy,
            meta={"creative_proof": True, "angle": req.angle, "intervention": req.intervention,
                  "predicted_resonance": entry["predicted_resonance"]},
        )
    entry["relayed_to"] = persona["first_name"] if persona else None
    return {"entry": entry, "calibration": STATE["creative_ledger"].calibration()}


@app.get("/api/creative/ledger")
def creative_ledger(limit: int = 20):
    led = STATE["creative_ledger"]
    return {"entries": led.list(limit), "calibration": led.calibration()}


class PlannerRequest(BaseModel):
    budget: float


@app.get("/api/planner/defaults")
def planner_defaults():
    """A sensible starting budget (half the max-useful spend) so the UI opens
    with a meaningful plan already on screen."""
    res = spend_planner.optimize(STATE["engine"], budget=0)
    return {"max_useful_budget": res["max_useful_budget"],
            "suggested_budget": round(res["max_useful_budget"] * 0.5, 2),
            "aov": res["aov"]}


@app.post("/api/planner/optimize")
def planner_optimize(req: PlannerRequest):
    """Allocate a budget across segment x intervention to maximize predicted
    incremental revenue; returns the plan, the saturation curve, and the
    incrementality (held-out) proof."""
    return spend_planner.optimize(STATE["engine"], budget=req.budget)


@app.get("/api/planner/analyst")
def planner_analyst(budget: float):
    """Executive narrative of the optimized plan, written by the NVIDIA 120B
    pool (Groq fallback). The strategic, plain-English read a CMO wants."""
    res = spend_planner.optimize(STATE["engine"], budget)
    lines = "; ".join(
        f"{p['segment_label']} via {p['intervention_label']} (reach {p['reach_funded']:,}, {p['roi']:.0f}x ROAS)"
        for p in res["plan"][:6])
    bl, inc = res["baselines"], res["incrementality"]
    system = (
        "You are a senior marketing strategist briefing a CMO. Write a crisp, confident executive "
        "summary in 3-4 sentences. No markdown, no bullet points, no preamble or sign-off. Use the "
        "numbers provided; never invent figures."
    )
    user = (
        f"Budget Rs{res['budget']:,.0f} across a 5,00,000-customer addressable base.\n"
        f"Optimized plan: {lines}.\n"
        f"Predicted incremental revenue Rs{res['pred_incr_revenue']:,.0f} at {res['blended_roi']:.0f}x blended ROAS, "
        f"+{res['pred_incr_conversions']:,.0f} conversions.\n"
        f"This beats an even-split allocation by {bl['uplift_vs_even_pct']}% (Rs{bl['uplift_vs_even_abs']:,.0f} more for the same spend).\n"
        f"On a randomized held-out control, the plan's predicted lift was {inc['accuracy']}% accurate.\n"
        f"Returns saturate near Rs{res['max_useful_budget']:,.0f}."
    )
    text, model = llm.chat_advanced(system, user, max_tokens=420, temperature=0.5)
    return {"text": text or "", "model": model}


# ------------------------------------------------------------ bring-your-own-CSV
@app.get("/api/byocsv/sample")
def byocsv_sample():
    """A ready-to-upload sample experiment CSV (arbitrary taxonomy + a known
    injected uplift) so a user can try the feature without their own data."""
    return Response(
        content=byocsv.sample_csv(), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=foresight_sample_experiment.csv"},
    )


@app.post("/api/byocsv/analyze")
async def byocsv_analyze(
    file: UploadFile = File(...),
    control_label: str | None = Form(None),
    aov: float | None = Form(None),
):
    """Run Foresight's uplift engine on a user-uploaded marketing-experiment CSV:
    trains an S-learner on their data, validates predicted-vs-observed lift on a
    randomized holdout, and returns an optimized spend plan over their segments."""
    content = await file.read()
    if not content:
        raise HTTPException(400, "empty file")
    try:
        res = byocsv.analyze(content, control_label=control_label, aov_override=aov)
    except ValueError as e:
        raise HTTPException(400, str(e))
    # Cache the planner context so the budget slider can re-optimize without re-upload.
    STATE["byo_last"] = res.pop("planner_ctx")
    return res


@app.post("/api/byocsv/replan")
def byocsv_replan(req: PlannerRequest):
    ctx = STATE.get("byo_last")
    if not ctx:
        raise HTTPException(400, "no dataset uploaded yet — analyze a CSV first")
    return spend_planner.optimize(None, req.budget, cells=ctx["cells"], aov=ctx["aov"], sigma=ctx["sigma"])


@app.get("/api/model/card")
def model_card_endpoint():
    return model_card_mod.model_card(STATE["engine"])


@app.get("/api/model/qini")
def model_qini(intervention: str = "cart_recovery_push"):
    if intervention not in C.INTERVENTION_KEYS:
        raise HTTPException(400, f"unknown intervention {intervention!r}")
    return model_card_mod.qini_curve(STATE["engine"], intervention)


@app.get("/api/ledger")
def ledger(limit: int = 60):
    return {"entries": STATE["ledger"].recent(limit), "calibration": STATE["ledger"].calibration()}


@app.get("/api/calibration")
def calibration():
    led = STATE["ledger"]
    return {
        **led.calibration(),
        "total_spent": led.total_spent(),
        "total_projected_revenue": led.total_projected_revenue(),
        "correction_factors": STATE["engine"].correction,
    }


@app.get("/api/dashboard/brief")
def dashboard_brief():
    """A live 2-3 sentence situation brief over the agent's current activity,
    written by the NVIDIA 120B pool. The 'what's happening right now' read."""
    led = STATE["ledger"]
    cal = led.calibration()
    recent = led.recent(10)
    acted = [e for e in recent if e.get("status") != "held"]
    top = {}
    for e in acted:
        if e.get("intervention_label"):
            top[e["intervention_label"]] = top.get(e["intervention_label"], 0) + 1
    top_intv = max(top, key=lambda k: top[k]) if top else "none"
    mae = cal.get("mae")
    system = (
        "You are an autonomous marketing-ops lead giving a CMO a live situation brief in 2-3 sentences. "
        "Plain prose, no markdown, no preamble. Use the numbers; never invent figures."
    )
    user = (
        f"Right now: {cal.get('acted', 0)} actions taken, {cal.get('held', 0)} held by guardrails. "
        f"Calibration error {f'{mae*100:.1f}pp' if mae is not None else 'still warming up'}. "
        f"Spend Rs{led.total_spent():,.0f}, projected incremental revenue Rs{led.total_projected_revenue():,.0f}. "
        f"Most-used intervention: {top_intv}. "
        f"Recent decisions: " + "; ".join(
            f"{e['first_name']} ({e['segment']}) {'held' if e.get('status')=='held' else e.get('intervention_label','acted')}"
            for e in recent[:5]) + "."
    )
    text, model = llm.chat_advanced(system, user, max_tokens=220, temperature=0.5)
    return {"text": text or "", "model": model}


@app.get("/api/explain/{entry_id}")
def explain(entry_id: int):
    result = explainer.explain_entry(STATE["ledger"], STATE["engine"], entry_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.get("/api/bandit/status")
def bandit_status():
    return {"arms": STATE["bandit"].status()}


@app.get("/api/trends/forecast")
def trends_forecast():
    return {"rising": forecast.rising_tags(8)}


class AgentOpsRequest(BaseModel):
    question: str


@app.post("/api/agent_ops/ask")
def agent_ops_ask(req: AgentOpsRequest):
    return supervisor.ask(STATE["tools"], req.question)


# ------------------------------------------------------------------ channels
class TestSendRequest(BaseModel):
    to: str
    body: str | None = None


@app.get("/api/channels")
def channels_list():
    return {"channels": channels.status_list()}


@app.get("/api/channels/logs")
def channels_logs(limit: int = 30):
    return {"logs": db.recent_channel_logs(limit)}


@app.post("/api/channels/{channel_id}/test")
def channels_test(channel_id: str, req: TestSendRequest):
    ch = channels.get_channel(channel_id)
    if ch is None:
        raise HTTPException(404, f"no such channel: {channel_id}")
    base = req.body or f"Foresight test via {ch.label} — see your personalized picks:"
    # Carry a tracked link so a click is logged as a real engagement.
    body = tracking.append_link(base, None, ch.id, req.to)
    result = ch.send(req.to, body, meta={"kind": "test"})
    db.log_channel(
        channel=ch.id, to_addr=req.to, body=body,
        status="sent" if result.ok else "failed",
        provider_id=result.provider_id, error=result.error,
        meta={"kind": "test", "sandbox": result.sandbox},
    )
    # Remember the outbound so an inbound reply has cross-channel context.
    if result.ok and req.to:
        STATE["memory"].append(req.to, ch.id, "agent", body, meta={"kind": "test"})
    return result.as_dict()


# ---------------------------------------------------- tracked links + engagement
@app.get("/r/{token}")
def tracked_redirect(token: str):
    """A tracked short link: log the click as a real engagement, then 302 on."""
    link = db.get_link(token)
    if not link:
        return RedirectResponse(tracking.DEFAULT_DEST, status_code=302)
    db.record_engagement("click", link.get("channel", ""), link.get("to_addr", ""),
                         run_id=link.get("run_id"), detail="link click")
    return RedirectResponse(link.get("url") or tracking.DEFAULT_DEST, status_code=302)


@app.get("/api/engagement")
def engagement(limit: int = 40):
    return {"events": db.recent_engagement(limit), "summary": db.engagement_summary()}


@app.post("/api/webhooks/resend")
async def webhook_resend(request: Request):
    """Resend email open/click webhook -> real engagement tied to the email send."""
    try:
        body = await request.json()
    except Exception:
        return {"ok": False}
    etype = body.get("type", "")
    email_id = (body.get("data") or {}).get("email_id") or (body.get("data") or {}).get("id") or ""
    kind = "open" if "opened" in etype else "click" if "clicked" in etype else ""
    if kind:
        log = db.find_channel_log_by_provider(email_id)
        run_id = log.get("run_id") if log else None
        to_addr = log.get("to_addr") if log else ""
        db.record_engagement(kind, "email", to_addr or "", run_id=run_id, detail=etype)
    return {"ok": True}


# -------------------------------------------------------------- inbound replies
def _handle_inbound(channel: str, sender: str, text: str) -> str:
    """Customer replied on a channel: log it, read cross-channel memory, draft a
    reply with the concierge, and persist both sides. Returns the reply text."""
    memory = STATE["memory"]
    memory.append(sender, channel, "customer", text)
    db.log_channel(channel=channel, to_addr=sender, body=text, status="received", direction="in")
    db.record_engagement("reply", channel, sender, detail=text[:140])
    ctx = memory.context_summary(sender)
    reply, source = llm.concierge_reply("there", "valued customer", channel, ctx, text, history=None)
    memory.append(sender, channel, "agent", reply, meta={"source": source, "inbound_reply": True})
    db.log_channel(channel=channel, to_addr=sender, body=reply, status="sent", direction="out",
                   meta={"source": source, "inbound_reply": True})
    return reply


@app.post("/api/webhooks/twilio")
async def webhook_twilio(request: Request):
    """Inbound SMS / WhatsApp (Twilio messaging webhook). Replies via TwiML."""
    form = await request.form()
    sender = str(form.get("From", ""))
    text = str(form.get("Body", "")).strip()
    channel = "whatsapp" if sender.startswith("whatsapp:") else "sms"
    reply = _handle_inbound(channel, sender, text) if text else "Sorry, I didn't catch that."
    safe = reply.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    xml = f"<?xml version='1.0' encoding='UTF-8'?><Response><Message>{safe}</Message></Response>"
    return Response(content=xml, media_type="application/xml")


@app.post("/api/webhooks/telegram")
async def webhook_telegram(request: Request):
    """Inbound Telegram (bot webhook). Replies via the Telegram API."""
    try:
        update = await request.json()
    except Exception:
        return {"ok": False}
    msg = update.get("message") or update.get("edited_message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = (msg.get("text") or "").strip()
    if chat_id and text:
        reply = _handle_inbound("telegram", chat_id, text)
        ch = channels.get_channel("telegram")
        if ch:
            ch.send(chat_id, reply, meta={"inbound_reply": True})
    return {"ok": True}


@app.post("/api/webhooks/slack")
async def webhook_slack(request: Request):
    """Slack Events API: URL-verification handshake + inbound message replies."""
    try:
        body = await request.json()
    except Exception:
        return {"ok": False}
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge", "")}
    # Ignore Slack's automatic retries to avoid duplicate replies.
    if request.headers.get("x-slack-retry-num"):
        return {"ok": True}
    event = body.get("event") or {}
    if event.get("type") == "message" and not event.get("bot_id") and not event.get("subtype"):
        text = (event.get("text") or "").strip()
        if text:
            reply = _handle_inbound("slack", event.get("channel", ""), text)
            ch = channels.get_channel("slack")
            if ch:
                ch.send("", reply, meta={"inbound_reply": True})
    return {"ok": True}


@app.post("/api/slack/interact")
async def slack_interact(request: Request):
    """Slack interactive components: the Approve/Reject buttons on the approval card."""
    import json as _json
    form = await request.form()
    try:
        payload = _json.loads(form.get("payload", "{}"))
    except Exception:
        return Response(status_code=200)
    action = (payload.get("actions") or [{}])[0]
    action_id = action.get("action_id", "")
    run_id = int(action.get("value", 0) or 0)
    response_url = payload.get("response_url", "")

    if action_id == "wf_approve":
        run = await STATE["workflow"].approve(run_id, broadcast)
        s = run.get("summary") or {}
        msg = (f"✅ *Approved* — run #{run_id} sent & proven: predicted "
               f"{(s.get('avg_rel_lift') or 0)*100:.1f}% vs actual {(s.get('actual_rel_lift') or 0)*100:.1f}% lift.")
    elif action_id == "wf_reject":
        await STATE["workflow"].reject(run_id, broadcast)
        msg = f"🛑 *Rejected* — run #{run_id} was not sent."
    else:
        msg = "Unknown action."

    # Replace the original card so the buttons can't be clicked twice.
    if response_url:
        try:
            import requests as _rq
            _rq.post(response_url, json={"text": msg, "replace_original": True}, timeout=8)
        except Exception:
            pass
    return Response(status_code=200)


# ------------------------------------------------------------------ workflows
class WorkflowRunRequest(BaseModel):
    workflow: str | None = None
    segment: str = ""
    intervention: str = ""
    channel: str = "sms"
    budget: float | None = None
    test_recipient: str | None = None
    label: str | None = None
    copy: str | None = None   # a specific creative to run (e.g. from Creative Pre-Flight)
    angle: str | None = None
    auto: bool | None = None  # let the Strategist pick the segment/action itself


class AutopilotRequest(BaseModel):
    goal: str | None = None
    budget: float | None = None


class ApproveRequest(BaseModel):
    test_recipient: str | None = None


@app.get("/api/workflows")
def workflows_list():
    return {
        "templates": workflow_mod.TEMPLATES,
        "steps": workflow_mod.STEP_DEFS,
        "segments": [{"key": k, "label": v["label"]} for k, v in C.SEGMENTS.items()],
        "interventions": [{"key": k, "label": v["label"], "channel": v["channel"]} for k, v in C.INTERVENTIONS.items()],
        "channels": [c["id"] for c in channels.status_list() if c["configured"]],
    }


@app.get("/api/workflows/runs")
def workflows_runs(limit: int = 30):
    return {"runs": db.list_runs(limit)}


@app.get("/api/workflows/runs/{run_id}")
def workflows_run(run_id: int):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "no such run")
    return run


@app.post("/api/workflows/run")
async def workflows_run_start(req: WorkflowRunRequest):
    params = req.model_dump()
    if params.get("budget") is None:
        params.pop("budget")
    return await STATE["workflow"].run(params, broadcast)


@app.post("/api/workflows/runs/{run_id}/approve")
async def workflows_approve(run_id: int, req: ApproveRequest):
    return await STATE["workflow"].approve(run_id, broadcast, test_recipient=req.test_recipient or "")


@app.post("/api/workflows/runs/{run_id}/reject")
async def workflows_reject(run_id: int):
    return await STATE["workflow"].reject(run_id, broadcast)


@app.post("/api/agent/autopilot")
async def agent_autopilot(req: AutopilotRequest):
    budget = float(req.budget or C.DAILY_BUDGET_USD)
    return await STATE["workflow"].autopilot(req.goal or "", budget, broadcast)


# ------------------------------------------------------------------- sim ctl
@app.get("/api/sim/status")
def sim_status():
    return STATE["simulator"].status()


@app.post("/api/sim/start")
def sim_start():
    STATE["simulator"].start()
    return STATE["simulator"].status()


@app.post("/api/sim/pause")
def sim_pause():
    STATE["simulator"].pause()
    return STATE["simulator"].status()


@app.post("/api/sim/speed")
def sim_speed(req: SpeedRequest):
    STATE["simulator"].set_speed(req.speed)
    return STATE["simulator"].status()


# ----------------------------------------------------------------- websocket
@app.websocket("/ws/feed")
async def ws_feed(websocket: WebSocket):
    await websocket.accept()
    _SOCKETS.add(websocket)
    try:
        backlog = STATE["ledger"].recent(30)
        await websocket.send_json({"type": "backlog", "entries": backlog, "calibration": STATE["ledger"].calibration()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _SOCKETS.discard(websocket)


# --------------------------------------------------------- static frontend
# Single-host deploy: serve the built SPA. Mounted LAST so /api + /ws win.
_DIST = C.ROOT / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
