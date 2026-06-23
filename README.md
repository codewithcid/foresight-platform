# ◎ Foresight — anticipate · activate · prove

[![CI](https://github.com/codewithcid/foresight-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/codewithcid/foresight-platform/actions/workflows/ci.yml)

**▶ Live demo: https://foresight-kp1g.onrender.com** &nbsp;·&nbsp; *(free tier — first load can take ~50s to wake)*

**Epsilon TeXpedition · Theme 2** — *How can we use AI to deliver seamless customer
experiences across channels while defining clear measures of success?*

Foresight is an **autonomous, cross-channel marketing agent** with a causal core. It
doesn't just personalize — it predicts who a message will move, acts across **real**
channels, and **proves the lift** predicted-vs-actual on every campaign.

> **Theme 2, taken literally.**
> - **Seamless cross-channel** → one agent + shared memory delivering over **real** SMS,
>   WhatsApp and Slack (not skins), orchestrated by visible workflows.
> - **Clear measures of success** → a persisted **predicted-vs-actual proof ledger** +
>   incrementality on every run. Success is *quantified, not claimed.*

---

## What it does (7 surfaces)
| Surface | What it is |
|---|---|
| **Command** | Live agent feed + KPIs (acted/held, calibration, spend, projected revenue). |
| **Workflows** | The centerpiece. Build a campaign → Predict (CATE) → Guardrail → Generate creative → Pre-test → **human Approve** → Deliver on a real channel → **Prove**. Live node graph. |
| **Spend Planner** | Budget → causal-optimal segment×channel allocation, beats naive even-split, with an incrementality holdout. |
| **Audience & Uplift** | Bring-Your-Own-CSV: train an uplift model on *your* experiment, validate on a randomized holdout. |
| **Creative Pre-Flight** | Generate ad variants → pre-test on a synthetic shopper panel → ship the winner. |
| **Channels** | Real integrations (SMS · WhatsApp · Slack live; Email/Telegram one key away) with status + test-send + delivery log. |
| **Proof** | The predicted-vs-actual ledger across all proven campaigns — mean error, incremental revenue. |
| **Agent Console** | An autonomous Supervisor (NVIDIA NIM tool-calling) that can *answer and act*: "launch a win-back SMS campaign for bargain hunters." Same tools exposed over **MCP**. |

## How it works
- **Causal core** — a LightGBM **S-learner** estimates each customer's treatment effect
  (CATE); `agent.py` runs a Strategist → Guardrail → Execution → Critic loop with a
  Thompson-sampling bandit and live self-correction.
- **Workflow engine** (`workflow.py`) composes those modules into one orchestrated run,
  pausing for human approval, delivering via the channel adapters, and writing a proof entry.
- **Real channels** (`channels/`) — Twilio SMS/WhatsApp + Slack behind one interface; a
  registry reports live/sandbox/needs-key.
- **Persistence** — SQLite (`db.py`): proof entries, runs + per-step traces, channel logs.
- **LLMs** — NVIDIA NIM pool (Qwen3-80B · Llama-3.3-70B · GPT-OSS/Nemotron-120B) for
  generation + tool-calling, with Groq fallback. Everything degrades to deterministic
  templates if no key is set, so it never hard-fails.

**Stack:** FastAPI + websockets · React + Vite + TypeScript + Tailwind v4 (shadcn-style UI) ·
LightGBM/scikit-learn · SQLite.

## Quick start (local)
```bash
# one-time
./setup.ps1                 # Python venv + backend deps + frontend deps
cp backend/.env.example backend/.env   # then fill in keys (all optional; see below)

# run (two terminals)
./run-backend.ps1           # FastAPI on http://127.0.0.1:8011
./run-frontend.ps1          # Vite on  http://localhost:5173  (proxies /api + /ws)
```
Open http://localhost:5173. With no keys it runs fully on synthetic data + template copy.

### Try the full loop
**Workflows** → set Channel **whatsapp**, Test recipient = your (sandbox-joined) number →
**Run workflow** → approve → the AI-drafted creative hits your real WhatsApp → **Proof**
logs predicted vs. actual.

## Configuration
See `backend/.env.example`. Highlights: `GROQ_API_KEY` + `NVIDIA_API_KEY_*` (LLM),
`TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`/`TWILIO_SMS_FROM` (SMS+WhatsApp),
`SLACK_BOT_TOKEN`/`SLACK_CHANNEL` (approvals). Twilio **trial accounts send only to
verified numbers**; WhatsApp uses the free sandbox (recipient must join once).

## Deploy (single host)
FastAPI serves the built SPA + API + websocket from one origin — no CORS/cross-origin WS.

- **Docker:** `docker build -t foresight . && docker run -p 8011:8011 --env-file backend/.env foresight`
- **Render:** push to GitHub → New Web Service → it picks up `render.yaml` (Docker). Set the
  secret env vars in the dashboard. The 1 GB disk persists the SQLite proof ledger across
  redeploys (drop the `disk:` block on the free tier — SQLite just resets on redeploy).

## Webhooks — two-way replies + real attribution
Outbound messages carry a tracked `/r/{token}` link; a click is logged as real engagement
and 302-redirects on. Inbound replies are read against cross-channel memory and answered by
the agent. Point each provider at the deployed base URL:

| Provider | Where to set it | URL |
|---|---|---|
| **Telegram** | `setWebhook` API | `…/api/webhooks/telegram` |
| **Twilio** | number → *A message comes in* (SMS + WhatsApp sandbox) | `…/api/webhooks/twilio` |
| **Slack** | app → *Event Subscriptions* (subscribe `message.channels`) | `…/api/webhooks/slack` |
| **Slack buttons** | app → *Interactivity* → Request URL | `…/api/slack/interact` |
| **Resend** | dashboard → *Webhooks* (`email.opened`, `email.clicked`) | `…/api/webhooks/resend` |

## MCP
`python backend/mcp_server.py` exposes the same tool registry over the Model Context
Protocol, so an external client (e.g. Claude Desktop) can call Foresight's causal model,
forecaster, explainer, and bandit directly.

## Repo layout
```
backend/   FastAPI app, causal engine, agent loop, workflow engine, channels/, db, tools/MCP
frontend/  React SPA (src/components surfaces, src/ui/dash.tsx shadcn primitives, src/landing)
Dockerfile render.yaml   single-host deploy
```
