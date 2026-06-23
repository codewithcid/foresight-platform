"""The context layer: per-shopper behavior profile (cart/wishlist/views ->
taste tags), a centralized registry so every agent reads the same picture of
a customer, a cross-customer trend analyzer (tag engagement x active
occasion), and an LLM-backed context summarizer that compacts raw logs into
a short profile other agents consume instead of replaying the whole history.
"""
from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

import catalog
import llm
import occasions as O
from clock import CLOCK
from memory import MemoryStore


@dataclass
class ShopperProfile:
    customer_id: str
    cart: dict[str, int] = field(default_factory=dict)
    wishlist: set[str] = field(default_factory=set)
    viewed: list[tuple[str, float]] = field(default_factory=list)
    tag_counter: Counter = field(default_factory=Counter)
    events: list[dict] = field(default_factory=list)

    def _touch_tags(self, product_id: str, weight: float = 1.0) -> None:
        p = catalog.PRODUCTS_BY_ID.get(product_id)
        if not p:
            return
        for t in p["tags"]:
            self.tag_counter[t] += weight

    def record(self, event_type: str, product_id: str | None) -> None:
        self.events.append({"type": event_type, "product_id": product_id, "ts": time.time()})
        if product_id is None:
            return
        if event_type == "view":
            self.viewed.append((product_id, time.time()))
            self._touch_tags(product_id, 0.5)
        elif event_type == "add_to_cart":
            self.cart[product_id] = self.cart.get(product_id, 0) + 1
            self._touch_tags(product_id, 2.0)
        elif event_type == "remove_from_cart":
            self.cart.pop(product_id, None)
        elif event_type == "wishlist_add":
            self.wishlist.add(product_id)
            self._touch_tags(product_id, 1.5)
        elif event_type == "wishlist_remove":
            self.wishlist.discard(product_id)
        elif event_type == "checkout":
            self._touch_tags(product_id, 3.0)
            self.cart.clear()

    def taste_tags(self, top_n: int = 6) -> list[str]:
        return [t for t, _ in self.tag_counter.most_common(top_n)]

    def cart_products(self) -> list[dict]:
        return [catalog.PRODUCTS_BY_ID[pid] for pid in self.cart if pid in catalog.PRODUCTS_BY_ID]

    def wishlist_products(self) -> list[dict]:
        return [catalog.PRODUCTS_BY_ID[pid] for pid in self.wishlist if pid in catalog.PRODUCTS_BY_ID]

    def behavior_lines(self) -> list[str]:
        lines = []
        for e in self.events[-15:]:
            p = catalog.PRODUCTS_BY_ID.get(e["product_id"]) if e["product_id"] else None
            pname = p["name"] if p else ""
            lines.append(f"{e['type']} {pname}".strip())
        return lines


class ShopperRegistry:
    def __init__(self):
        self._profiles: dict[str, ShopperProfile] = {}

    def get(self, customer_id: str) -> ShopperProfile:
        if customer_id not in self._profiles:
            self._profiles[customer_id] = ShopperProfile(customer_id=customer_id)
        return self._profiles[customer_id]

    def all(self) -> dict[str, ShopperProfile]:
        return self._profiles


def summarize_customer(customer_id: str, first_name: str, segment_label: str,
                        registry: ShopperRegistry, memory: MemoryStore) -> dict:
    profile = registry.get(customer_id)
    behavior_lines = profile.behavior_lines()
    conv_lines = [f"[{m.channel}] {m.role}: {m.text}" for m in memory.history(customer_id, limit=15)]
    text, source = llm.summarize_context(first_name, segment_label, behavior_lines, conv_lines)
    return {
        "summary": text, "source": source,
        "taste_tags": profile.taste_tags(), "cart": profile.cart_products(),
        "wishlist": profile.wishlist_products(),
    }


class TrendAnalyzer:
    """Cross-customer trend score per tag = synthetic population baseline
    interest + live shopper behavior, boosted by whatever occasion is active
    right now on the (virtual) clock. This is what backs both the
    storefront's 'Trending now' rail and the CRM campaign audience sizing.
    """

    def __init__(self, customers: pd.DataFrame, registry: ShopperRegistry):
        self.customers = customers
        self.registry = registry

    def active_occasions(self) -> list[O.Occasion]:
        return O.active_occasions(CLOCK.now())

    def tag_scores(self) -> dict[str, float]:
        scores: Counter = Counter()
        for tags_str in self.customers.get("preferred_tags", []):
            if not tags_str:
                continue
            for t in tags_str.split(","):
                scores[t] += 1.0
        for profile in self.registry.all().values():
            for t, w in profile.tag_counter.items():
                scores[t] += w * 3.0  # live behavior weighs more than static taste
        active = self.active_occasions()
        active_tags = {t for o in active for t in o.tags}
        for t in list(scores.keys()):
            if t in active_tags:
                scores[t] *= 1.8
        return dict(scores)

    def trending(self, limit: int = 8) -> list[dict]:
        scores = self.tag_scores()
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        out = []
        for tag, score in ranked:
            products = catalog.by_tags({tag}, limit=3)
            out.append({"tag": tag, "score": round(score, 1), "products": products})
        return out

    def audience_size(self, tags: list[str]) -> int:
        tagset = set(tags)
        count = 0
        for tags_str in self.customers.get("preferred_tags", []):
            if tags_str and tagset & set(tags_str.split(",")):
                count += 1
        for profile in self.registry.all().values():
            if tagset & set(profile.tag_counter.keys()):
                count += 1
        return count
