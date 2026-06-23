"""The Supervisor agent: a business user asks a free-form question, and Groq
decides which of Foresight's tools (backend/tools.py) to call, in what order,
to answer it -- a real ReAct-style tool-calling loop, not a hardcoded
if/elif router. This is what powers the 4th tab ("Agent Ops"); the same tool
registry is also reachable externally via backend/mcp_server.py.
"""
from __future__ import annotations

import json

import llm
from tools import Tool

MAX_STEPS = 5

SYSTEM_PROMPT = (
    "You are the Foresight Supervisor, an autonomous marketing-ops agent for an Indian fashion brand. "
    "You can not only ANSWER questions but ACT: launch campaign workflows (run_workflow), approve or "
    "reject paused runs (approve_run/reject_run), send real messages on live channels "
    "(send_message via sms/whatsapp/slack), and report proof. You also have analytical tools: predict "
    "uplift per customer, forecast trends, explain past decisions, summarize customers, check the "
    "contextual bandit, list channels (channel_status), list/inspect runs, and proof_summary. "
    "Workflows PAUSE for human approval after pre-testing — when a user asks you to run a campaign, "
    "call run_workflow and report the predicted lift + reach, then tell them the run_id is awaiting "
    "approval (only call approve_run if they explicitly approve). Ground every answer in tool results; "
    "never invent numbers. Be concise and action-oriented, citing the specific figures your tools returned."
)


def _to_schema(tool: Tool) -> dict:
    return {"type": "function", "function": {
        "name": tool.name, "description": tool.description, "parameters": tool.parameters,
    }}


def ask(tools: list[Tool], question: str) -> dict:
    by_name = {t.name: t for t in tools}
    schemas = [_to_schema(t) for t in tools]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": question}]
    trace = []

    if not llm.has_key():
        return {
            "answer": "Groq key not configured -- the Supervisor needs LLM tool-calling to reason "
                      "across tools. Add GROQ_API_KEY to backend/.env.",
            "trace": [],
        }

    for step in range(MAX_STEPS):
        resp = llm.chat_with_tools(messages, schemas)
        if resp is None:
            return {"answer": "The Supervisor couldn't reach Groq right now -- try again.", "trace": trace}
        choice = resp["choices"][0]
        msg = choice["message"]

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return {"answer": msg.get("content") or "(no answer produced)", "trace": trace}

        messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": tool_calls})
        for tc in tool_calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except Exception:
                args = {}
            tool = by_name.get(name)
            if tool is None:
                result = {"error": f"unknown tool {name}"}
            else:
                try:
                    result = tool.fn(**args)
                except Exception as exc:  # noqa: BLE001
                    result = {"error": str(exc)}
            trace.append({"step": step + 1, "tool": name, "args": args, "result": result})
            messages.append({
                "role": "tool", "tool_call_id": tc["id"], "name": name,
                "content": json.dumps(result, default=str),
            })

    return {"answer": "Reached the reasoning step limit -- here's what was gathered so far.", "trace": trace}
