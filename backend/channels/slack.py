"""Real Slack channel via the Web API (chat.postMessage).

Used for two things: ops notifications, and human-in-the-loop **approval**
requests (the agent posts "approve this campaign?" with Block Kit buttons).
Sending only needs a bot token + a channel; interactive button callbacks need
a public URL (wired automatically once deployed in Phase 6).
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

import config as C
from .base import Channel, DeliveryResult

load_dotenv(C.ROOT / "backend" / ".env")

API = "https://slack.com/api/chat.postMessage"


def _token() -> str:
    return os.environ.get("SLACK_BOT_TOKEN", "")


def _channel() -> str:
    return os.environ.get("SLACK_CHANNEL", "")


def _post(blocks: list | None = None, text: str = "") -> tuple[bool, str, str]:
    if not (_token() and _channel()):
        return False, "", "Slack not configured (SLACK_BOT_TOKEN / SLACK_CHANNEL)."
    try:
        payload: dict = {"channel": _channel(), "text": text or " "}
        if blocks:
            payload["blocks"] = blocks
        r = requests.post(API, json=payload,
                          headers={"Authorization": f"Bearer {_token()}"}, timeout=15)
        data = r.json()
        if data.get("ok"):
            return True, data.get("ts", ""), ""
        return False, "", data.get("error", "slack error")
    except Exception as e:
        return False, "", f"Slack request failed: {e}"


class Slack(Channel):
    id = "slack"
    label = "Slack"
    kind = "chat"
    icon = "ri-slack-line"
    needs = ["SLACK_BOT_TOKEN", "SLACK_CHANNEL"]
    hint = "Add a Slack bot token + channel for ops alerts and approvals."

    def configured(self) -> bool:
        return bool(_token() and _channel())

    def send(self, to: str, body: str, meta: dict | None = None) -> DeliveryResult:
        ok, ts, err = _post(text=body)
        return DeliveryResult(ok=ok, channel=self.id, to=to or _channel(), provider_id=ts, error=err)

    def status(self) -> dict:
        return {**super().status(), "hint": self.hint}


def notify_approval(run_label: str, segment: str, intervention: str, channel: str,
                    reach: int, predicted_rev: float, run_id: int) -> tuple[bool, str]:
    """Post a campaign approval card to Slack. Returns (ok, error)."""
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "🟡 Foresight — approval needed"}},
        {"type": "section", "text": {"type": "mrkdwn", "text":
            f"*{run_label}*\nSegment: *{segment}*  ·  Action: *{intervention}*  ·  Channel: *{channel}*\n"
            f"Reach: *{reach:,}*  ·  Predicted incremental revenue: *₹{predicted_rev:,.0f}*  ·  Run *#{run_id}*"}},
        {"type": "actions", "block_id": f"wf_{run_id}", "elements": [
            {"type": "button", "style": "primary", "action_id": "wf_approve",
             "text": {"type": "plain_text", "text": "Approve & send"}, "value": str(run_id)},
            {"type": "button", "style": "danger", "action_id": "wf_reject",
             "text": {"type": "plain_text", "text": "Reject"}, "value": str(run_id)},
        ]},
        {"type": "context", "elements": [{"type": "mrkdwn", "text":
            "Approve here, or in the Foresight Workflow Studio."}]},
    ]
    ok, _ts, err = _post(blocks=blocks, text=f"Approval needed for run #{run_id}")
    return ok, err


def notify(text: str) -> None:
    """Fire-and-forget ops note; silently ignores if Slack isn't configured."""
    _post(text=text)
