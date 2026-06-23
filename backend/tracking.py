"""Short-link tracking: every outbound message can carry a /r/{token} link.
A click hits this server, gets logged as a real engagement (feeding the proof),
then 302-redirects on. Turns 'modeled lift' into 'measured clicks'.
"""
from __future__ import annotations

import os
import secrets

import db

# The publicly reachable base. Render injects RENDER_EXTERNAL_URL automatically.
PUBLIC_BASE = (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "http://localhost:8011").rstrip("/")

# Where a tracked click ultimately lands (the live product, by default).
DEFAULT_DEST = PUBLIC_BASE + "/"


def make_tracked_link(url: str | None, run_id: int | None, channel: str, to_addr: str) -> str:
    """Create a short tracked link and return its absolute URL."""
    token = secrets.token_urlsafe(6)
    db.create_link(token, url or DEFAULT_DEST, run_id, channel, to_addr)
    return f"{PUBLIC_BASE}/r/{token}"


def append_link(body: str, run_id: int | None, channel: str, to_addr: str, url: str | None = None) -> str:
    """Append a tracked CTA link to a message body."""
    link = make_tracked_link(url, run_id, channel, to_addr)
    return f"{body} {link}"
