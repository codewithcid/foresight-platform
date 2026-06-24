"""Novu integration — open-source notification orchestration.

Foresight triggers a Novu *workflow* (event) with the recipient + a payload;
Novu fans out to whatever providers you've configured in its dashboard
(WhatsApp, SMS, email, push, in-app). This keeps Foresight provider-agnostic:
to change how a nudge is delivered, you edit the workflow in Novu, not the code.

Setup (once, in the Novu dashboard):
  1. Create a workflow; note its trigger identifier (default we use: ``foresight-nudge``).
  2. Add a channel step (Chat/WhatsApp, SMS, Email …) with body template ``{{body}}``
     (richer payload also available: {{name}} {{percent}} {{code}} {{link}} {{item}}).
  3. Connect a provider for that channel.
  4. Paste your Novu API key into Foresight → Settings → Connections.
"""
from __future__ import annotations

import requests

import appconfig

DEFAULT_WORKFLOW = "foresight-nudge"


def base_url() -> str:
    # api.novu.co (US) or eu.api.novu.co (EU) or a self-hosted URL.
    return (appconfig.get("NOVU_BASE_URL") or "https://api.novu.co").rstrip("/")


def workflow_id() -> str:
    return appconfig.get("NOVU_WORKFLOW_ID") or DEFAULT_WORKFLOW


def configured() -> bool:
    return bool(appconfig.get("NOVU_API_KEY"))


def trigger(subscriber_id: str, payload: dict, *, phone: str | None = None,
            email: str | None = None, workflow: str | None = None) -> tuple[bool, str, str]:
    """Fire a Novu workflow. Returns (ok, transaction_id, error)."""
    key = appconfig.get("NOVU_API_KEY")
    if not key:
        return False, "", "Novu not configured (NOVU_API_KEY)."
    to: dict = {"subscriberId": subscriber_id or "foresight-user"}
    if phone:
        to["phone"] = phone
    if email:
        to["email"] = email
    body = {"name": workflow or workflow_id(), "to": to, "payload": payload}
    try:
        r = requests.post(f"{base_url()}/v1/events/trigger", json=body,
                          headers={"Authorization": f"ApiKey {key}", "Content-Type": "application/json"},
                          timeout=15)
    except requests.RequestException as e:
        return False, "", f"Novu request failed: {e}"
    if r.status_code in (200, 201):
        data = (r.json() or {}).get("data", {})
        if data.get("acknowledged", True) and data.get("status") not in ("trigger_not_active", "no_workflow_active_steps_defined"):
            return True, data.get("transactionId", ""), ""
        return False, "", f"Novu: {data.get('status', 'not acknowledged')}"
    return False, "", f"Novu {r.status_code}: {r.text[:200]}"
