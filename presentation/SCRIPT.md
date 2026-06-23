# Foresight — Finale speaker script (≈3:00)

Open `presentation/index.html` in a browser, press **F** for full screen, navigate with **← →**
(or click: right 75% = next, left 25% = back). Total budget is 3:00 — practice to ~2:50 to leave air.

> **Photos:** both headshots are wired in (`presentation/assets/sidhardh.png`, `rochit.png`).
> To replace, just overwrite those two files.

---

## Slide 1 · Team Introduction — 0:30
> "Hi, we're **Team Foresight**. I'm **Sidhardh**, I led the AI and full-stack build, and this is
> **Rochit**, who built out the backend and systems with me. Our project — fittingly — is called
> **Foresight**: an AI that doesn't just personalize marketing, but **anticipates, activates, and
> proves** its impact. Here's the problem we set out to solve."

## Slide 2 · Problem Statement — 0:30
> "Today, marketing **reacts**. Channels are **siloed** — email, SMS, app, and web all act blind to
> each other, even though the customer is one person. Budget is spent on **gut and last-click**, not
> on who a message will actually move. And 'success' is measured in **opens and clicks** — vanity
> metrics, not proven revenue. Theme 2 asks for seamless cross-channel experiences *with clear
> measures of success.* So we built an agent that anticipates, acts across channels, and **proves its
> impact in rupees.**"

## Slide 3 + 4 · Prototype Demonstration — 1:30
*(Slide 3 = the demo map, then SWITCH TO THE LIVE APP for the real demo, return to Slide 4 for the
under-the-hood beat. Or stay on slides if a live demo isn't possible.)*

> "One causal engine drives six working surfaces. **(Dashboard)** Here it's running live — every few
> seconds it evaluates a real customer, the guardrails pass, and it acts. Each decision shows
> **predicted lift versus the actual outcome** — that's our proof spine. Drag the **Time Machine** to
> Diwali and the whole system's behaviour changes.
>
> **(Spend Planner)** Give it a budget and it allocates across segments and channels to maximise
> *incremental* revenue — and it beats a naive even-split by **86%**, validated on a held-out control.
>
> **(Bring Your Own Data)** This isn't just our synthetic demo — you can **upload your own
> experiment CSV**. It trains an uplift model on *your* segments and proves it on a randomized
> holdout. **(Creative Pre-Flight)** It even generates ad variants, pre-tests them on a synthetic
> shopper panel, and ships the winner. And in **WhatsApp and the shop**, the same agent acts and
> remembers across channels, unprompted.
>
> **(Slide 4 — under the hood)** Underneath: a LightGBM **S-learner** causal model, a four-agent
> loop with a Thompson-sampling bandit and live self-correction, an **NVIDIA NIM** model pool with
> Groq fallback, and a tool registry exposed over **MCP**. FastAPI and React over websockets — and
> the same engine scales to any dataset you give it."

## Slide 5 · Closing & Summary — 0:30
> "So — three words, measured at every step. **Anticipate**: we forecast lift per customer before
> spending. **Activate**: an autonomous, guardrailed agent acts across channels. **Prove**:
> predicted-versus-actual incrementality at every level — intervention, portfolio, creative, and your
> own data. That's our clear measure of success. **Foresight doesn't just personalize — it proves it
> worked.** Thank you."

---

## Tomorrow's alignment call — 3-minute overview (problem + solution approach)

**Problem (≈45s):** Marketing teams operate reactively across siloed channels, allocate spend by
gut/last-click rather than causal impact, and measure success with vanity metrics instead of proven
incremental revenue. Theme 2 specifically asks for seamless cross-channel experiences *with clear
measures of success* — the "measures of success" part is where most solutions fall short.

**Solution approach (≈2:15):** Foresight is an AI marketing agent built on three pillars —
**Anticipate, Activate, Prove.**
- **Anticipate** — a LightGBM S-learner estimates each customer's individual treatment effect (CATE),
  so we predict *who a given message will actually move* before any spend.
- **Activate** — a multi-agent loop (Strategist → Guardrail → Execution → Critic) acts autonomously
  and across channels (shop, WhatsApp), with a contextual bandit and live self-correction; a
  portfolio **Spend Planner** turns the model into an optimal, budget-bound media plan.
- **Prove** — every prediction is validated **predicted-vs-actual**: at the intervention level (the
  live ledger), the portfolio level (incrementality holdout, ~96% on synthetic / validated on real
  uploads), and the creative level (synthetic-panel pre-test). A **Bring-Your-Own-CSV** mode runs the
  whole pipeline on a judge's own data, proving generality.

**Why it's credible / differentiated:** real causal ML (not just an LLM wrapper), an honest
predicted-vs-actual proof spine end-to-end, cross-channel memory, NVIDIA NIM + Groq + MCP, and a
working product — six live surfaces, not slides.

**Ask for the call:** confirm whether the 1:30 prototype block is a *live* demo or a recorded
walkthrough, and the exact order so we can pre-stage the Time Machine / BYO-CSV beats.
