"""Foresight admin chatbot — talk to the platform over WhatsApp (via Wati).

Only allow-listed admin numbers may use it. It reuses the same tool registry as
the Agent Console: READ tools (proof, runs, cart recovery, channels, predict…)
run automatically to ground every answer; ACTION tools (launch a campaign,
approve/reject a run, send a message/nudge, switch sandbox/live) are never run
silently — the bot proposes the action and waits for a "YES" confirmation.
"""
from __future__ import annotations

import asyncio
import json
import re

import appconfig
import config as C
import db
import llm
import wati
import workflow as workflow_mod
from tools import Tool, build_tools

MAX_STEPS = 8
ACTION_NAMES = {"run_workflow", "approve_run", "reject_run", "send_message", "send_nudge", "set_mode"}
YES = {"yes", "y", "confirm", "ok", "okay", "go", "do it", "yep", "sure", "approve", "send it"}
NO = {"no", "n", "cancel", "stop", "abort", "nope", "nah"}

SYSTEM = (
    "You are the Foresight Admin Assistant, reachable over WhatsApp by the brand's marketing-ops "
    "admins. Foresight is an autonomous cross-channel marketing agent (causal ROI prediction, real "
    "channels, a proof spine, and a Link-Up cart-recovery loop). "
    "ANSWER questions by calling the read tools and grounding every figure in their results — never "
    "invent numbers. When the admin asks you to DO something (launch a campaign, approve/reject a run, "
    "send a message or discount nudge, switch sandbox/live), call the matching action tool; it will be "
    "shown to the admin for a YES confirmation before it actually runs, so just call it. "
    "All monetary amounts are in Indian Rupees — always write ₹, never $. "
    "Reply for WhatsApp: short, scannable, *bold* for key numbers, line breaks between points, minimal emoji."
)

HELP = (
    "👋 *Foresight Admin* — ask me anything about the platform:\n"
    "• _How is the campaign progressing?_\n"
    "• _How many carts did we recover and what revenue?_\n"
    "• _What's our prediction error / calibration?_\n"
    "• _Which channels are live? How much budget is left?_\n\n"
    "I can also *act* (with your confirmation):\n"
    "• _Launch a win-back SMS for bargain hunters_\n"
    "• _Approve run 7_\n"
    "• _Send a discount nudge to +9162…_\n"
    "• _Switch to live mode_"
)

# in-memory per-admin state (fine for a single-instance demo)
_PENDING: dict[str, dict] = {}
_HISTORY: dict[str, list] = {}
_PROCESSED: set = set()       # message ids handled (dedupe webhook vs poller)
_POLL_SEEN: dict[str, set] = {}  # per-admin message ids already observed


def already(key: str) -> bool:
    """True if this message id was already handled (then marks it)."""
    if not key:
        return False
    if key in _PROCESSED:
        return True
    _PROCESSED.add(key)
    if len(_PROCESSED) > 4000:
        _PROCESSED.clear()
    return False


def is_admin(wa_id: str) -> bool:
    raw = appconfig.get("ADMIN_WHATSAPP_NUMBERS", "") or ""
    allow = {wati.normalize(a) for a in raw.split(",") if a.strip()}
    return bool(allow) and wati.normalize(wa_id) in allow


def _capabilities_note() -> str:
    templates = ", ".join(t["id"] for t in workflow_mod.TEMPLATES)
    return ("\nValid run_workflow values — prefer a template id. Templates: " + templates +
            ". Segments: " + ", ".join(C.SEGMENTS.keys()) +
            ". Interventions: " + ", ".join(C.INTERVENTIONS.keys()) +
            ". Never pass values outside these.")


def _wa_format(text: str) -> str:
    """WhatsApp uses *single* asterisks for bold; collapse Markdown **bold** and ### headers."""
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    return text.strip()


def _to_schema(t: Tool) -> dict:
    return {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}


def _extra_tools(ctx: dict) -> list[Tool]:
    store = ctx.get("store")
    sim = ctx.get("simulator")

    def send_nudge(phone: str, name: str = "", value: float = 0.0, item: str = "") -> dict:
        if store is None:
            return {"error": "Link-Up unavailable"}
        cart = asyncio.run(store.manual_nudge(name, phone, float(value or 0), item or None))
        return {"cart_id": cart.get("cart_id"), "discount_code": cart.get("discount_code"), "status": cart.get("status")}

    def set_mode(mode: str) -> dict:
        mode = "live" if mode == "live" else "sandbox"
        db.set_setting("MODE", mode)
        if sim:
            sim.pause() if mode == "live" else sim.start()
        return {"mode": mode}

    return [
        Tool("send_nudge", "Send a budget-safe WhatsApp discount nudge to a specific customer NOW (Link-Up). phone is required.",
             {"type": "object", "properties": {"phone": {"type": "string"}, "name": {"type": "string"},
                                               "value": {"type": "number"}, "item": {"type": "string"}}, "required": ["phone"]},
             send_nudge),
        Tool("set_mode", "Switch the platform between 'sandbox' (synthetic traffic) and 'live'.",
             {"type": "object", "properties": {"mode": {"type": "string", "enum": ["sandbox", "live"]}}, "required": ["mode"]},
             set_mode),
    ]


def _tools(ctx: dict):
    all_tools = build_tools(ctx) + _extra_tools(ctx)
    return all_tools, {t.name: t for t in all_tools}


def _summarize(name: str, args: dict) -> str:
    if name == "run_workflow":
        what = args.get("workflow") or f"{args.get('segment','?')} × {args.get('intervention','?')}"
        return f"🚀 Launch campaign *{what}*" + (f" on {args['channel']}" if args.get("channel") else "") + " (pauses for approval)."
    if name == "approve_run":
        return f"✅ Approve & send run *#{args.get('run_id')}* (delivers + proves)."
    if name == "reject_run":
        return f"🗑️ Reject run *#{args.get('run_id')}*."
    if name == "send_message":
        return f"✉️ Send {args.get('channel')} to *{args.get('to')}*: “{(args.get('body') or '')[:80]}”"
    if name == "send_nudge":
        return f"🛒 WhatsApp a discount nudge to *{args.get('phone')}*" + (f" ({args['name']})" if args.get("name") else "") + "."
    if name == "set_mode":
        return f"⚙️ Switch platform to *{args.get('mode')}* mode."
    return f"Run {name} with {args}"


def _format_result(name: str, res: dict) -> str:
    if isinstance(res, dict) and res.get("error"):
        return f"⚠️ {res['error']}"
    if name == "run_workflow":
        return (f"🚀 Launched *run #{res.get('run_id')}* — predicted lift *{res.get('predicted_rel_lift_pct')}%*, "
                f"reach *{res.get('reach')}*. It's awaiting approval; reply _approve run {res.get('run_id')}_ to send.")
    if name == "approve_run":
        return (f"✅ Run *#{res.get('run_id')}* {res.get('status')}. Predicted *{res.get('predicted_rel_lift_pct')}%* vs "
                f"actual *{res.get('actual_rel_lift_pct')}%* (error {res.get('error_pp')}pp). Delivered: {res.get('delivered')}.")
    if name == "send_nudge":
        return f"🛒 Nudge sent — code *{res.get('discount_code')}* (cart {res.get('cart_id')}, {res.get('status')})."
    if name == "set_mode":
        return f"⚙️ Now in *{res.get('mode')}* mode."
    return "✅ Done.\n" + "\n".join(f"• {k}: {v}" for k, v in (res or {}).items())


def _run(ctx: dict, text: str, history: list) -> dict:
    if not llm.has_key():
        return {"reply": "⚠️ The reasoning model isn't configured on the server."}
    all_tools, by_name = _tools(ctx)
    schemas = [_to_schema(t) for t in all_tools]
    messages = [{"role": "system", "content": SYSTEM + _capabilities_note()}, *history, {"role": "user", "content": text}]

    for step in range(MAX_STEPS):
        # On the final step, drop the tools so the model MUST answer with the data gathered.
        resp = llm.chat_with_tools(messages, schemas if step < MAX_STEPS - 1 else [])
        if resp is None:
            return {"reply": "⚠️ Couldn't reach the model just now — try again."}
        msg = resp["choices"][0]["message"]
        tcs = msg.get("tool_calls") or []
        if not tcs:
            return {"reply": (msg.get("content") or "I didn't catch that — try _help_.").strip()}

        action_tc = next((tc for tc in tcs if tc["function"]["name"] in ACTION_NAMES), None)
        if action_tc:
            name = action_tc["function"]["name"]
            try:
                args = json.loads(action_tc["function"]["arguments"] or "{}")
            except Exception:
                args = {}
            return {"reply": f"{_summarize(name, args)}\n\nReply *YES* to confirm or *NO* to cancel.",
                    "pending": {"name": name, "args": args}}

        messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": tcs})
        for tc in tcs:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except Exception:
                args = {}
            tool = by_name.get(name)
            try:
                result = tool.fn(**args) if tool else {"error": f"unknown tool {name}"}
            except Exception as exc:  # noqa: BLE001
                result = {"error": str(exc)}
            messages.append({"role": "tool", "tool_call_id": tc["id"], "name": name,
                             "content": json.dumps(result, default=str)})
    return {"reply": "Hmm, that took too many steps — try a more specific question."}


def handle(ctx: dict, wa_id: str, text: str) -> str:
    """Main entry. Returns the WhatsApp reply text. Run me in a worker thread."""
    tl = text.strip().lower()
    pend = _PENDING.get(wa_id)
    if pend:
        if tl in YES:
            _PENDING.pop(wa_id, None)
            _, by_name = _tools(ctx)
            tool = by_name.get(pend["name"])
            try:
                res = tool.fn(**pend["args"]) if tool else {"error": "action unavailable"}
            except Exception as exc:  # noqa: BLE001
                res = {"error": str(exc)}
            return _wa_format(_format_result(pend["name"], res))
        if tl in NO:
            _PENDING.pop(wa_id, None)
            return "👍 Cancelled — nothing was changed."
        _PENDING.pop(wa_id, None)  # anything else = a new request

    if tl in {"help", "hi", "hello", "hey", "start", "menu", "/help", "/start"}:
        return HELP

    out = _run(ctx, text, _HISTORY.get(wa_id, []))
    reply = _wa_format(out["reply"])
    _HISTORY[wa_id] = (_HISTORY.get(wa_id, []) + [
        {"role": "user", "content": text}, {"role": "assistant", "content": reply}])[-8:]
    if out.get("pending"):
        _PENDING[wa_id] = out["pending"]
    return reply


async def poll_loop(ctx: dict) -> None:
    """Inbound fallback: pull new messages from Wati and reply — no webhook needed.
    Runs forever; no-ops until Wati is configured. On first sight of a contact it
    marks existing messages as seen so we don't reply to history."""
    while True:
        await asyncio.sleep(6)
        try:
            if not wati.configured():
                continue
            raw = appconfig.get("ADMIN_WHATSAPP_NUMBERS", "") or ""
            admins = [wati.normalize(a) for a in raw.split(",") if a.strip()]
            for num in admins:
                msgs = await asyncio.to_thread(wati.get_messages, num, 10)
                ids = [str(m.get("whatsappMessageId") or m.get("id") or m.get("created")) for m in msgs]
                first_time = num not in _POLL_SEEN
                seen = _POLL_SEEN.setdefault(num, set())
                if first_time:
                    seen.update(ids)  # don't reply to pre-existing history
                    continue
                # oldest -> newest so multi-message bursts reply in order
                for m in reversed(msgs):
                    mid = str(m.get("whatsappMessageId") or m.get("id") or m.get("created"))
                    if mid in seen:
                        continue
                    seen.add(mid)
                    inbound = (not m.get("owner")) and m.get("type") == "text" and (m.get("text") or "").strip()
                    if not inbound or already(f"wati:{mid}"):
                        continue
                    text = (m.get("text") or "").strip()
                    reply = await asyncio.to_thread(handle, ctx, num, text)
                    await asyncio.to_thread(wati.send_session_message, num, reply)
        except Exception as e:  # noqa: BLE001 - never let the loop die
            print("[wati] poll error:", str(e)[:120])
