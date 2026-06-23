"""The agent loop: Strategist -> Guardrail -> Execution -> (later) Critic.

This replaces the original prototype's "human reads a chart and decides"
product surface with a system that senses an event, decides, checks itself,
acts, and then proves itself once the outcome is known -- the same
anticipate / activate / prove framing Epsilon already uses to describe its
own platform, just running continuously instead of argued in a deck.

Extended to be occasion-aware (the Strategist's product reference and the
drafted copy can reflect whatever festival/season/sport is active on the
virtual clock) and to deliver demo-persona actions into the visible
WhatsApp-skin inbox, not just the abstract ledger channel label.
"""
from __future__ import annotations

import asyncio

import pandas as pd

import catalog
import config as C
import llm
from bandit import ThompsonBandit
from causal import UpliftEngine, ActionPrediction
from ledger import Ledger
from memory import MemoryStore
from signals import ConversationSignal, SignalRegistry


class GuardrailAgent:
    """Responsible-AI layer: frequency caps, budget caps, brand safety."""

    def __init__(self):
        self.action_counts: dict[str, int] = {}
        self.budget_spent = 0.0

    def precheck(self, customer_id: str, cost: float) -> tuple[bool, str]:
        count = self.action_counts.get(customer_id, 0)
        if count >= C.MAX_ACTIONS_PER_CUSTOMER_PER_DAY:
            return False, f"frequency cap reached ({count}/{C.MAX_ACTIONS_PER_CUSTOMER_PER_DAY})"
        if self.budget_spent + cost > C.DAILY_BUDGET_USD:
            return False, "daily budget exhausted"
        return True, "ok"

    def commit(self, customer_id: str, cost: float) -> None:
        self.action_counts[customer_id] = self.action_counts.get(customer_id, 0) + 1
        self.budget_spent += cost

    def brand_safety(self, text: str) -> tuple[bool, str]:
        low = text.lower()
        for w in C.BRAND_UNSAFE_WORDS:
            if w in low:
                return False, f"brand-safety: flagged phrase '{w}'"
        return True, "ok"


class StrategistAgent:
    def __init__(self, engine: UpliftEngine, bandit: ThompsonBandit):
        self.engine = engine
        self.bandit = bandit

    def decide(self, customer_row: pd.Series,
               signal: ConversationSignal | None = None) -> tuple[ActionPrediction | None, str | None]:
        if signal is not None:
            suppress, reason = signal.should_suppress_marketing()
            if suppress:
                return None, reason

        candidates = self.engine.predict_for_customer(customer_row)
        segment = customer_row.segment
        # Contextual-bandit-weighted ranking: the causal model's point estimate
        # sets the baseline, but a sampled per-(segment, intervention) Beta
        # posterior nudges which arm actually gets tried -- arms the bandit is
        # still uncertain about get explored even if their point estimate
        # isn't the top one, instead of permanently favouring day-one winners.
        scored = []
        for c in candidates:
            reliability = self.bandit.sample(segment, c.intervention)
            c.bandit_reliability = reliability
            score = c.expected_roi * (0.5 + reliability)
            scored.append((score, c))
        scored.sort(key=lambda t: t[0], reverse=True)
        best = scored[0][1]
        if best.predicted_rel_lift < C.MIN_REL_LIFT_TO_ACT:
            return None, None
        return best, None


class ExecutionAgent:
    def __init__(self, memory: MemoryStore):
        self.memory = memory

    def draft(self, customer_row: pd.Series, action: ActionPrediction,
               occasion_theme: str | None = None, product_name: str | None = None) -> tuple[str, str]:
        label = C.INTERVENTIONS[action.intervention]["label"]
        channel = C.INTERVENTIONS[action.intervention]["channel"]
        segment_label = C.SEGMENTS[customer_row.segment]["label"]
        text, source = llm.draft_intervention_message(
            action.intervention, label, channel, segment_label, customer_row.first_name,
            action.predicted_rel_lift, occasion_theme=occasion_theme, product_name=product_name,
        )
        return text, source

    def send(self, customer_id: str, channel: str, text: str, meta: dict,
              also_channel: str | None = None) -> None:
        self.memory.append(customer_id, channel=channel, role="agent", text=text, meta=meta)
        if also_channel and also_channel != channel:
            self.memory.append(customer_id, channel=also_channel, role="agent", text=text,
                                meta={**meta, "relayed_from": channel})


class CriticAgent:
    """Closes the loop: compares predicted lift to the ground-truth effect for
    that exact customer + intervention once the outcome 'resolves', then
    nudges the causal engine's correction factor -- the agent's confidence
    self-corrects live instead of being graded once after the fact.
    """

    def __init__(self, engine: UpliftEngine, ledger: Ledger, bandit: ThompsonBandit):
        self.engine = engine
        self.ledger = ledger
        self.bandit = bandit

    def resolve(self, entry_id: int, customer_row: pd.Series, intervention: str) -> dict:
        true_abs = customer_row[f"p1_{intervention}"] - customer_row["p0"]
        true_rel = true_abs / customer_row["p0"] if customer_row["p0"] > 0 else 0.0
        entry = self.ledger.resolve(entry_id, float(true_rel))
        self.engine.apply_correction(intervention, float(true_rel), entry["predicted_rel_lift"])
        self.bandit.update(customer_row.segment, intervention, success=true_rel > 0)
        return entry


class AgentLoop:
    def __init__(self, engine: UpliftEngine, memory: MemoryStore, ledger: Ledger, customers: pd.DataFrame,
                 bandit: ThompsonBandit | None = None, signal_registry: SignalRegistry | None = None):
        self.engine = engine
        self.memory = memory
        self.ledger = ledger
        self.customers = customers.set_index("customer_id", drop=False)
        self.bandit = bandit or ThompsonBandit()
        self.signal_registry = signal_registry
        self.strategist = StrategistAgent(engine, self.bandit)
        self.guardrail = GuardrailAgent()
        self.execution = ExecutionAgent(memory)
        self.critic = CriticAgent(engine, ledger, self.bandit)

    def get_customer(self, customer_id: str) -> pd.Series:
        return self.customers.loc[customer_id]

    async def handle_event(self, customer_id: str, event: str, broadcast,
                            product_id: str | None = None, occasion_key: str | None = None,
                            occasion_theme: str | None = None) -> None:
        row = self.get_customer(customer_id)
        seg_label = C.SEGMENTS[row.segment]["label"]
        is_demo = str(customer_id).startswith("DEMO_")
        product = catalog.PRODUCTS_BY_ID.get(product_id) if product_id else None
        product_name = product["name"] if product else None

        if event == "reached_purchase":
            entry = self.ledger.record_hold(
                customer_id=customer_id, first_name=row.first_name, segment=seg_label,
                reason="already converted -- no action needed", intervention=None, channel=None,
                predicted_rel_lift=0.0, predicted_revenue=0.0, cost=0.0, message=None, message_source=None,
                product_id=product_id, product_name=product_name, occasion_key=occasion_key,
            )
            await broadcast({"type": "decision", "entry": entry})
            return

        signal = self.signal_registry.get(customer_id) if self.signal_registry else None
        action, suppress_reason = self.strategist.decide(row, signal)
        if action is None:
            reason = suppress_reason or "predicted lift below action threshold -- holding to avoid fatigue"
            entry = self.ledger.record_hold(
                customer_id=customer_id, first_name=row.first_name, segment=seg_label,
                reason=reason,
                intervention=None, channel=None, predicted_rel_lift=0.0, predicted_revenue=0.0,
                cost=0.0, message=None, message_source=None,
                product_id=product_id, product_name=product_name, occasion_key=occasion_key,
            )
            await broadcast({"type": "decision", "entry": entry})
            return

        ok, reason = self.guardrail.precheck(customer_id, action.cost)
        if not ok:
            entry = self.ledger.record_hold(
                customer_id=customer_id, first_name=row.first_name, segment=seg_label,
                reason=f"guardrail blocked: {reason}", intervention=action.intervention,
                channel=C.INTERVENTIONS[action.intervention]["channel"],
                predicted_rel_lift=action.predicted_rel_lift, predicted_revenue=action.expected_revenue,
                cost=action.cost, message=None, message_source=None,
                product_id=product_id, product_name=product_name, occasion_key=occasion_key,
            )
            await broadcast({"type": "decision", "entry": entry})
            return

        text, source = self.execution.draft(row, action, occasion_theme=occasion_theme, product_name=product_name)
        safe, reason2 = self.guardrail.brand_safety(text)
        if not safe:
            entry = self.ledger.record_hold(
                customer_id=customer_id, first_name=row.first_name, segment=seg_label,
                reason=f"guardrail blocked: {reason2}", intervention=action.intervention,
                channel=C.INTERVENTIONS[action.intervention]["channel"],
                predicted_rel_lift=action.predicted_rel_lift, predicted_revenue=action.expected_revenue,
                cost=action.cost, message=text, message_source=source,
                product_id=product_id, product_name=product_name, occasion_key=occasion_key,
            )
            await broadcast({"type": "decision", "entry": entry})
            return

        channel = C.INTERVENTIONS[action.intervention]["channel"]
        self.guardrail.commit(customer_id, action.cost)
        # Demo personas have exactly one visible inbox in this build (the
        # WhatsApp-skin tab) -- relay the action there regardless of the
        # "official" marketing channel label, which still drives the ledger.
        also_channel = "whatsapp" if is_demo else None
        self.execution.send(customer_id, channel, text, meta={
            "intervention": action.intervention, "product_id": product_id, "occasion_key": occasion_key,
        }, also_channel=also_channel)
        entry = self.ledger.record_decision(
            customer_id=customer_id, first_name=row.first_name, segment=seg_label,
            intervention=action.intervention,
            intervention_label=C.INTERVENTIONS[action.intervention]["label"],
            channel=channel, predicted_rel_lift=action.predicted_rel_lift,
            predicted_revenue=action.expected_revenue, cost=action.cost, roi=action.expected_roi,
            message=text, message_source=source,
            product_id=product_id, product_name=product_name, occasion_key=occasion_key,
            bandit_reliability=round(action.bandit_reliability, 3),
        )
        await broadcast({"type": "decision", "entry": entry})

        async def resolve_later():
            await asyncio.sleep(3.5)  # simulated time-to-outcome
            resolved = self.critic.resolve(entry["id"], row, action.intervention)
            await broadcast({"type": "resolution", "entry": resolved, "calibration": self.ledger.calibration()})

        asyncio.create_task(resolve_later())
