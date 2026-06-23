# Foresight — AI/ML Services Reference

One-page index of every AI/ML component in the build, what it is, and where it lives.

| # | Service | Technique | Library/Model | File | What it does |
|---|---|---|---|---|---|
| 1 | Causal uplift model | S-learner, gradient-boosted trees (supervised ML) | LightGBM | `backend/causal.py` | Predicts each customer's individual treatment effect (CATE) per intervention; validated against held-out ground truth. |
| 2 | Contextual bandit | Thompson sampling, Beta-Bernoulli posterior | NumPy | `backend/bandit.py` | Learns reliability per (segment, intervention) arm; the Strategist samples it to decide what to try, not just what the causal model predicts. |
| 3 | Self-correction | Exponentially-weighted moving average | Plain Python | `backend/causal.py` (`apply_correction`) | Nudges the causal model's trust in each intervention toward observed outcomes, live. |
| 4 | Product recommender | Content-based, feature-vector embeddings + cosine similarity | NumPy | `backend/recommender.py` | Builds a taste vector per customer (weighted centroid of viewed/carted/wishlisted items) and ranks all products by similarity. |
| 5 | Trend forecasting | Linear regression on time series | NumPy (`polyfit`) | `backend/forecast.py` | Projects each tag's engagement 7 days out from 30 days of history; classifies rising/falling/flat. |
| 6 | Generative AI (8 call sites) | LLM chat completion | Groq, Llama 3.1 8B Instant (default; 3.3 70B optional, lower rate limit) | `backend/llm.py` | Drafts marketing copy, concierge replies, proactive outreach, customer summaries, campaign copy, decision explanations, styling rationale, and tool-calling. |
| 7 | Intent/sentiment classifier | Structured-output NLP classification + regex fallback | Groq (JSON mode) | `backend/nlp.py` | Classifies every inbound chat message (intent + sentiment); feeds a suppression check the Strategist reads before acting. |
| 8 | AI Stylist | ML (recommender) + generative AI composition | Recommender + Groq | `backend/stylist.py` | Composes a hero+layer+accessory look per customer/occasion with an LLM-written rationale. |
| 9 | Multi-agent pipeline | Sequential agent orchestration | Custom (Python) | `backend/agent.py` | Strategist → Guardrail → Execution → Critic; each step is a distinct agent with a defined responsibility. |
| 10 | Supervisor agent | ReAct-style tool-calling loop | Groq function-calling | `backend/supervisor.py` | Takes a free-form business question, autonomously selects and chains tool calls, grounds its answer in real data. |
| 11 | MCP server | Model Context Protocol tool exposure | `mcp` SDK (FastMCP) | `backend/mcp_server.py` | Exposes the same tool registry to any external MCP client (e.g. Claude Desktop). |
| 12 | Policy-grounded support drafting | Generative AI + retrieval-style policy matching | Groq | `backend/policies.py`, `backend/support.py` | Matches each support case to a specific policy and drafts a reply grounded only in that policy's text. |
| 13 | Support Copilot | Same Supervisor/tool-calling loop as #10, context-prefixed | Groq function-calling | `frontend/src/components/SupportCopilot.tsx`, `/api/support/copilot/ask` | Floating widget letting a support rep ask about a customer's history without leaving the inbox. |
| 14 | Creative generation | Multi-angle LLM copywriting + text-to-image | Groq (copy) + Pollinations/FLUX (image) | `backend/creative.py` | For a chosen intervention+segment+occasion, generates 3 distinct ad-copy angles (Urgency/Value/Aspiration) each with a matching AI ad image. |
| 15 | Synthetic-persona pre-test | Simulated-panel evaluation (LLM persona reactions) | Groq JSON + heuristic fallback | `backend/pre_test.py` | A fixed panel of synthetic shoppers scores each variant's predicted resonance (0-100) and reacts; the winner is picked before spend. Inspired by AdWise. |
| 16 | Creative proof | Predicted-vs-actual calibration | Plain Python (hidden ground-truth resonance) | `backend/creative_proof.py` | Samples the shipped winner's actual engagement from hidden ground truth and logs predicted-vs-actual error — Foresight's proof spine, now at the creative level. |

## The self-testing creative loop (services 14-16)
`POST /api/creative/preflight` runs **generate (14) → pre-test (15)**; `POST /api/creative/ship`
runs **prove (16)** and relays the proven winner into the segment's demo-persona WhatsApp inbox.
Surfaced in the **Creative Pre-Flight** tab. This is the finals addition on top of Foresight:
the agent doesn't just draft one untested line — it generates options, tests them on synthetic
shoppers, ships the winner, and proves the prediction.

## Shared tool registry (consumed by #10, #11, and #13 identically)
`backend/tools.py` — 12 tools: `predict_uplift`, `forecast_trend`, `draft_campaign`, `explain_decision`,
`summarize_customer`, `recommend_look`, `bandit_status`, `get_active_occasions`, `list_demo_customers`,
`customer_conversation_signal`, `search_catalog`, `get_support_cases`.

## Deliberately not AI/ML
Occasion calendar (`occasions.py`) — hardcoded date rules. Guardrails (`agent.py`) — plain conditionals
(frequency cap, budget cap, brand-safety keyword filter). Memory store, event simulator, synthetic data
generator — bookkeeping and statistical simulation, not models. Product photography (`backend/images.py`)
— real photo retrieval + color-distance ranking against named colors is data lookup/sorting, not a model.
Theme system, icon set, and chart components (`frontend/src`) — UI/UX, not AI/ML.

## Honest design notes
The intent/sentiment classifier and the product "embeddings" are pragmatic choices for a hackathon
timeline (LLM-based classification rather than a fine-tuned model; hand-built feature vectors rather than
a learned neural embedding) — both are explicitly swap-in points if extended. The bandit operates per
segment, not per individual customer, for sample-efficiency in a short demo window. Trend forecasting
runs on synthetic 30-day history; the forecasting mechanism is real, the data it's fit to is illustrative.
