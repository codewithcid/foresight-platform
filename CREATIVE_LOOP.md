# The Self-Testing Creative Loop (finals addition)

This is the capability added on top of Foresight for the finals. It closes the
one honest gap in the base build: Foresight *sensed, decided, activated, and
proved* — but the creative it sent was a single, untested line of copy. Now the
agent **generates options, tests them on synthetic shoppers, ships the winner,
and proves the prediction** — extending the original Foresight predicted-vs-actual
spine from the *intervention* all the way to the *creative*.

## The loop

```
Sense ─► Predict lift ─► GENERATE creative ─► PRE-TEST on synthetic shoppers ─► Ship ─► PROVE
(occasion/   (causal        (3 angles: copy      (persona panel scores         (winner   (predicted
 behavior)    S-learner)     + AI ad image)       predicted resonance)          relayed)  vs actual)
```

Every step is **measurable** — which is exactly Theme 2 ("clear measures of success").

## Where it lives

| Piece | File |
|---|---|
| Copy variants (Groq) + AI ad image (Pollinations/FLUX, keyless) | `backend/creative.py` |
| Synthetic-persona panel scoring (Groq + heuristic fallback) | `backend/pre_test.py` |
| Hidden ground-truth resonance + creative proof ledger | `backend/creative_proof.py` |
| API: `POST /api/creative/preflight`, `POST /api/creative/ship`, `GET /api/creative/ledger` | `backend/main.py` |
| Creative Pre-Flight tab (6th tab) | `frontend/src/components/CreativePreflight.tsx` |

## How each step works

- **Generate** — Groq writes three distinct ad-copy angles (Urgency / Value /
  Aspiration), occasion- and segment-aware; each variant gets a matching AI ad
  image from Pollinations.ai (free, keyless, returns a URL the browser loads
  directly — no image quota, nothing stored server-side). Template fallback if
  Groq is unavailable.
- **Pre-test** — a fixed panel of synthetic shoppers (Meena / Aarav / Lakshmi)
  scores each variant's predicted resonance 0-100 and reacts in character. One
  Groq call scores the whole matrix; a deterministic heuristic (per angle ×
  segment fit) is the fallback so the panel never stalls. Winner = highest mean.
- **Ship & prove** — the winner's actual engagement is sampled from a *hidden*
  ground-truth resonance the panel was estimating (deliberately offset from the
  panel's prior so predicted ≠ actual by a realistic margin). Predicted vs actual
  is logged with a running calibration (MAE / accuracy). The proven creative is
  relayed into that segment's demo-persona WhatsApp inbox — **the creative we
  tested is the creative we send.**

## Why Pollinations instead of Gemini image-gen

GenMark (one of the reference projects) used Gemini image generation. On a free
Gemini key, image models return immediate 429 (no image quota). Pollinations.ai
gives real text-to-image with no key and no quota, so the feature stays live and
demo-reliable. Swapping to a paid Gemini/billing key later is a one-line change
in `creative.py`.

## Demo beat (slot into the main 3-min script)

> **Creative Pre-Flight (40s).** "Foresight decided *what* to send. Now watch it
> decide *how*. Pick SMS Discount for Bargain Hunters." Hit **Run pre-flight**.
> "It wrote three angles, generated an ad image for each, and tested them on a
> synthetic shopper panel — the **Value** angle wins, by 30 points, *before we
> spend anything*." Hit **Ship winner & measure**. "And here's the proof:
> predicted resonance 92 versus actual 85 — the same predicted-vs-actual rigor
> from our prototype, now on the creative itself. The winner just landed in the
> customer's WhatsApp." Switch to the WhatsApp tab to show it.

## Honest scope notes

- Ground-truth resonance is synthetic (same philosophy as the rest of Foresight)
  — it's what makes live predicted-vs-actual proof possible without a production
  ad-engagement feed. The mechanism is real; the data it's measured against is
  illustrative.
- The synthetic panel is LLM-simulated personas, not real survey respondents —
  the swap-in point for a real panel is a single function (`pre_test.pretest`).
- "Shipping" relays the creative into the in-app WhatsApp inbox + the proof
  ledger; it is not a real ad-network or WhatsApp Business API push.
