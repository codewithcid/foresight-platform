"""SQLite persistence for Foresight.

Everything that should survive a restart lives here: the proof ledger (every
agent decision + its predicted-vs-actual outcome), workflow runs and their
per-step trace, and the channel delivery log (every real SMS/WhatsApp send).

A single connection is shared process-wide (`check_same_thread=False`) and
guarded by a lock, because FastAPI serves sync routes on a threadpool while the
simulator/agent write from the event-loop thread.

The DB path is `FORESIGHT_DB` if set (so a deployed host can point it at a
persistent disk), else `backend/foresight.db`.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

_DB_PATH = os.environ.get("FORESIGHT_DB") or str(Path(__file__).resolve().parent / "foresight.db")
_LOCK = threading.RLock()
_CONN: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS proof_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, source TEXT DEFAULT 'sandbox', run_id INTEGER,
    status TEXT, customer_id TEXT, first_name TEXT, segment TEXT,
    intervention TEXT, intervention_label TEXT, channel TEXT,
    predicted_rel_lift REAL, predicted_revenue REAL, cost REAL, roi REAL,
    message TEXT, message_source TEXT, reason TEXT,
    actual_rel_lift REAL, error REAL, resolved INTEGER DEFAULT 0,
    product_id TEXT, product_name TEXT, occasion_key TEXT, bandit_reliability REAL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, workflow TEXT, label TEXT, status TEXT,
    target TEXT, channel TEXT, params TEXT, summary TEXT
);
CREATE TABLE IF NOT EXISTS run_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER, idx INTEGER, name TEXT, label TEXT,
    status TEXT, output TEXT, ts REAL
);
CREATE TABLE IF NOT EXISTS channel_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, channel TEXT, to_addr TEXT, body TEXT,
    status TEXT, provider_id TEXT, error TEXT, run_id INTEGER,
    customer_id TEXT, meta TEXT, direction TEXT DEFAULT 'out'
);
CREATE TABLE IF NOT EXISTS links (
    token TEXT PRIMARY KEY, ts REAL, run_id INTEGER, channel TEXT, to_addr TEXT, url TEXT
);
CREATE TABLE IF NOT EXISTS engagement (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, channel TEXT,
    to_addr TEXT, run_id INTEGER, detail TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, value TEXT
);
CREATE TABLE IF NOT EXISTS carts (
    cart_id TEXT PRIMARY KEY, customer_id TEXT, name TEXT, phone TEXT, email TEXT,
    items TEXT, value REAL, currency TEXT DEFAULT 'INR',
    status TEXT, tier INTEGER DEFAULT -1, run_id INTEGER, proof_id INTEGER,
    created_ts REAL, updated_ts REAL, last_push_ts REAL,
    discount_code TEXT, recovered_value REAL
);
CREATE TABLE IF NOT EXISTS discount_codes (
    code TEXT PRIMARY KEY, cart_id TEXT, percent INTEGER, run_id INTEGER, proof_id INTEGER,
    issued_ts REAL, expires_ts REAL, redeemed_ts REAL, redeemed_value REAL
);
CREATE TABLE IF NOT EXISTS journeys (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, template TEXT, name TEXT,
    phone TEXT, email TEXT, steps TEXT, step_idx INTEGER DEFAULT -1, status TEXT,
    goal TEXT, last_step_ts REAL, next_due_ts REAL, touches TEXT
);
"""


def conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
        _CONN.executescript(SCHEMA)
        _CONN.commit()
    return _CONN


def init(*, reset_sandbox: bool = True) -> None:
    """Create tables. By default clears prior *sandbox* proof rows so the live
    feed starts clean each boot — real workflow runs (source='workflow') and
    channel logs persist."""
    with _LOCK:
        c = conn()
        if reset_sandbox:
            c.execute("DELETE FROM proof_entries WHERE source = 'sandbox'")
        # Runs left mid-flight by a prior process can't resume -> mark failed so
        # the runs/proof views stay clean.
        c.execute("UPDATE runs SET status = 'failed' WHERE status = 'running'")
        # Migration: add direction to a channel_logs table created before it existed.
        try:
            c.execute("ALTER TABLE channel_logs ADD COLUMN direction TEXT DEFAULT 'out'")
        except sqlite3.OperationalError:
            pass
        c.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["resolved"] = bool(d.get("resolved"))
    return d


# --------------------------------------------------------------- generic JSON
def _dumps(v) -> str:
    return json.dumps(v, default=str)


def _loads(s):
    if s in (None, ""):
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s


# ------------------------------------------------------------ proof entries
_PROOF_COLS = [
    "ts", "source", "run_id", "status", "customer_id", "first_name", "segment",
    "intervention", "intervention_label", "channel", "predicted_rel_lift",
    "predicted_revenue", "cost", "roi", "message", "message_source", "reason",
    "actual_rel_lift", "error", "resolved", "product_id", "product_name",
    "occasion_key", "bandit_reliability",
]


def insert_proof(fields: dict) -> dict:
    with _LOCK:
        c = conn()
        cols = [k for k in _PROOF_COLS if k in fields]
        placeholders = ", ".join("?" for _ in cols)
        cur = c.execute(
            f"INSERT INTO proof_entries ({', '.join(cols)}) VALUES ({placeholders})",
            [fields[k] for k in cols],
        )
        c.commit()
        return get_proof(cur.lastrowid)


def update_proof(entry_id: int, fields: dict) -> dict:
    with _LOCK:
        c = conn()
        sets = ", ".join(f"{k} = ?" for k in fields)
        c.execute(f"UPDATE proof_entries SET {sets} WHERE id = ?", [*fields.values(), entry_id])
        c.commit()
        return get_proof(entry_id)


def get_proof(entry_id: int) -> dict:
    with _LOCK:
        row = conn().execute("SELECT * FROM proof_entries WHERE id = ?", (entry_id,)).fetchone()
    return _row_to_dict(row) if row else {}


def recent_proof(limit: int = 60) -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM proof_entries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_row_to_dict(r) for r in rows]


def all_proof() -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM proof_entries ORDER BY id ASC").fetchall()
    return [_row_to_dict(r) for r in rows]


# ----------------------------------------------------------------- runs
def insert_run(workflow: str, label: str, target: str, channel: str, params: dict) -> int:
    with _LOCK:
        c = conn()
        cur = c.execute(
            "INSERT INTO runs (ts, workflow, label, status, target, channel, params, summary) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (time.time(), workflow, label, "running", target, channel, _dumps(params), _dumps({})),
        )
        c.commit()
        return cur.lastrowid


def update_run(run_id: int, *, status: str | None = None, summary: dict | None = None) -> None:
    with _LOCK:
        c = conn()
        if status is not None:
            c.execute("UPDATE runs SET status = ? WHERE id = ?", (status, run_id))
        if summary is not None:
            c.execute("UPDATE runs SET summary = ? WHERE id = ?", (_dumps(summary), run_id))
        c.commit()


def add_step(run_id: int, idx: int, name: str, label: str, status: str, output: dict) -> int:
    with _LOCK:
        c = conn()
        cur = c.execute(
            "INSERT INTO run_steps (run_id, idx, name, label, status, output, ts) VALUES (?,?,?,?,?,?,?)",
            (run_id, idx, name, label, status, _dumps(output), time.time()),
        )
        c.commit()
        return cur.lastrowid


def update_step(step_id: int, *, status: str | None = None, output: dict | None = None) -> None:
    with _LOCK:
        c = conn()
        if status is not None:
            c.execute("UPDATE run_steps SET status = ? WHERE id = ?", (status, step_id))
        if output is not None:
            c.execute("UPDATE run_steps SET output = ? WHERE id = ?", (_dumps(output), step_id))
        c.commit()


def get_run(run_id: int) -> dict | None:
    with _LOCK:
        r = conn().execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not r:
            return None
        run = dict(r)
        run["params"] = _loads(run.get("params"))
        run["summary"] = _loads(run.get("summary"))
        steps = conn().execute("SELECT * FROM run_steps WHERE run_id = ? ORDER BY idx ASC", (run_id,)).fetchall()
    run["steps"] = [{**dict(s), "output": _loads(dict(s).get("output"))} for s in steps]
    return run


def list_runs(limit: int = 50) -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["params"] = _loads(d.get("params"))
        d["summary"] = _loads(d.get("summary"))
        out.append(d)
    return out


# ------------------------------------------------------------- channel logs
def log_channel(channel: str, to_addr: str, body: str, status: str,
                provider_id: str = "", error: str = "", run_id: int | None = None,
                customer_id: str = "", meta: dict | None = None, direction: str = "out") -> int:
    with _LOCK:
        c = conn()
        cur = c.execute(
            "INSERT INTO channel_logs (ts, channel, to_addr, body, status, provider_id, error, run_id, customer_id, meta, direction) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), channel, to_addr, body, status, provider_id, error, run_id, customer_id, _dumps(meta or {}), direction),
        )
        c.commit()
        return cur.lastrowid


def recent_channel_logs(limit: int = 50) -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM channel_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{**dict(r), "meta": _loads(dict(r).get("meta"))} for r in rows]


def find_channel_log_by_provider(provider_id: str) -> dict | None:
    if not provider_id:
        return None
    with _LOCK:
        r = conn().execute("SELECT * FROM channel_logs WHERE provider_id = ? ORDER BY id DESC LIMIT 1", (provider_id,)).fetchone()
    return dict(r) if r else None


# ------------------------------------------------------------- links + engagement
def create_link(token: str, url: str, run_id: int | None, channel: str, to_addr: str) -> None:
    with _LOCK:
        c = conn()
        c.execute("INSERT OR REPLACE INTO links (token, ts, run_id, channel, to_addr, url) VALUES (?,?,?,?,?,?)",
                  (token, time.time(), run_id, channel, to_addr, url))
        c.commit()


def get_link(token: str) -> dict | None:
    with _LOCK:
        r = conn().execute("SELECT * FROM links WHERE token = ?", (token,)).fetchone()
    return dict(r) if r else None


def record_engagement(kind: str, channel: str, to_addr: str = "", run_id: int | None = None, detail: str = "") -> int:
    with _LOCK:
        c = conn()
        cur = c.execute(
            "INSERT INTO engagement (ts, kind, channel, to_addr, run_id, detail) VALUES (?,?,?,?,?,?)",
            (time.time(), kind, channel, to_addr, run_id, detail))
        c.commit()
        return cur.lastrowid


def set_setting(key: str, value: str) -> None:
    with _LOCK:
        c = conn()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        c.commit()


def get_setting(key: str) -> str | None:
    with _LOCK:
        r = conn().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return r["value"] if r else None


def all_settings() -> dict:
    with _LOCK:
        rows = conn().execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def recent_engagement(limit: int = 40) -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM engagement ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- cart recovery
_CART_COLS = ["cart_id", "customer_id", "name", "phone", "email", "items", "value",
              "currency", "status", "tier", "run_id", "proof_id", "created_ts",
              "updated_ts", "last_push_ts", "discount_code", "recovered_value"]


def _cart_row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["items"] = _loads(d.get("items")) or []
    return d


def cart_get(cart_id: str) -> dict | None:
    with _LOCK:
        r = conn().execute("SELECT * FROM carts WHERE cart_id = ?", (cart_id,)).fetchone()
    return _cart_row(r) if r else None


def cart_upsert(cart_id: str, fields: dict) -> dict:
    """Insert or merge a cart row; items is stored as JSON."""
    with _LOCK:
        c = conn()
        existing = c.execute("SELECT * FROM carts WHERE cart_id = ?", (cart_id,)).fetchone()
        cur = dict(existing) if existing else {col: None for col in _CART_COLS}
        cur["cart_id"] = cart_id
        for k, v in fields.items():
            if k == "items":
                v = _dumps(v)
            cur[k] = v
        now = time.time()
        if not existing:
            cur["created_ts"] = now
        cur["updated_ts"] = fields.get("updated_ts", now)
        c.execute(
            f"INSERT OR REPLACE INTO carts ({','.join(_CART_COLS)}) VALUES ({','.join('?' for _ in _CART_COLS)})",
            tuple(cur.get(col) for col in _CART_COLS))
        c.commit()
    return cart_get(cart_id)


def cart_update(cart_id: str, **fields) -> None:
    if not fields:
        return
    with _LOCK:
        c = conn()
        sets = ", ".join(f"{k} = ?" for k in fields)
        c.execute(f"UPDATE carts SET {sets} WHERE cart_id = ?", (*fields.values(), cart_id))
        c.commit()


def carts_list(limit: int = 100) -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM carts ORDER BY updated_ts DESC LIMIT ?", (limit,)).fetchall()
    return [_cart_row(r) for r in rows]


def carts_by_status(status: str) -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM carts WHERE status = ?", (status,)).fetchall()
    return [_cart_row(r) for r in rows]


def discount_create(code: str, cart_id: str, percent: int, run_id: int | None,
                    proof_id: int | None, expires_ts: float) -> None:
    with _LOCK:
        c = conn()
        c.execute("INSERT OR REPLACE INTO discount_codes "
                  "(code, cart_id, percent, run_id, proof_id, issued_ts, expires_ts) VALUES (?,?,?,?,?,?,?)",
                  (code, cart_id, percent, run_id, proof_id, time.time(), expires_ts))
        c.commit()


def discount_get(code: str) -> dict | None:
    with _LOCK:
        r = conn().execute("SELECT * FROM discount_codes WHERE code = ?", (code,)).fetchone()
    return dict(r) if r else None


def discount_redeem(code: str, value: float) -> None:
    with _LOCK:
        c = conn()
        c.execute("UPDATE discount_codes SET redeemed_ts = ?, redeemed_value = ? WHERE code = ?",
                  (time.time(), value, code))
        c.commit()


def discounts_issued_since(ts: float) -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM discount_codes WHERE issued_ts >= ?", (ts,)).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- journeys
_JOURNEY_COLS = ["id", "ts", "template", "name", "phone", "email", "steps", "step_idx",
                 "status", "goal", "last_step_ts", "next_due_ts", "touches"]


def _journey_row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["steps"] = _loads(d.get("steps")) or []
    d["touches"] = _loads(d.get("touches")) or []
    return d


def journey_create(template: str, name: str, phone: str, email: str, steps: list, goal: str) -> int:
    with _LOCK:
        c = conn()
        cur = c.execute(
            "INSERT INTO journeys (ts, template, name, phone, email, steps, step_idx, status, goal, touches) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (time.time(), template, name, phone, email, _dumps(steps), -1, "active", goal, _dumps([])))
        c.commit()
        return cur.lastrowid


def journey_get(jid: int) -> dict | None:
    with _LOCK:
        r = conn().execute("SELECT * FROM journeys WHERE id = ?", (jid,)).fetchone()
    return _journey_row(r) if r else None


def journey_update(jid: int, **fields) -> None:
    if "steps" in fields:
        fields["steps"] = _dumps(fields["steps"])
    if "touches" in fields:
        fields["touches"] = _dumps(fields["touches"])
    with _LOCK:
        c = conn()
        sets = ", ".join(f"{k} = ?" for k in fields)
        c.execute(f"UPDATE journeys SET {sets} WHERE id = ?", (*fields.values(), jid))
        c.commit()


def journeys_list(limit: int = 60) -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM journeys ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_journey_row(r) for r in rows]


def journeys_active() -> list[dict]:
    with _LOCK:
        rows = conn().execute("SELECT * FROM journeys WHERE status = 'active'").fetchall()
    return [_journey_row(r) for r in rows]


def engagement_for(to_addr: str, since_ts: float = 0.0) -> list[dict]:
    with _LOCK:
        rows = conn().execute(
            "SELECT * FROM engagement WHERE to_addr = ? AND ts >= ? ORDER BY id DESC", (to_addr, since_ts)).fetchall()
    return [dict(r) for r in rows]


def channel_logs_for(to_addr: str, limit: int = 100) -> list[dict]:
    with _LOCK:
        rows = conn().execute(
            "SELECT * FROM channel_logs WHERE to_addr = ? ORDER BY id DESC LIMIT ?", (to_addr, limit)).fetchall()
    return [dict(r) for r in rows]


def clear_store() -> None:
    """Wipe cart-recovery state (carts, codes, and its proof rows) for a clean demo."""
    with _LOCK:
        c = conn()
        c.execute("DELETE FROM carts")
        c.execute("DELETE FROM discount_codes")
        c.execute("DELETE FROM proof_entries WHERE source = 'cart_recovery'")
        c.commit()


def engagement_summary() -> dict:
    with _LOCK:
        rows = conn().execute("SELECT kind, COUNT(*) n FROM engagement GROUP BY kind").fetchall()
    out = {r["kind"]: r["n"] for r in rows}
    with _LOCK:
        sent = conn().execute("SELECT COUNT(*) n FROM channel_logs WHERE status='sent' AND direction='out'").fetchone()["n"]
    out["sent"] = sent
    return out
