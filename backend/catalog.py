"""Synthetic clothing catalog for the storefront, tagged so the
occasion/trend engine and the Strategist can reason about which products
matter right now. Card art is a CSS gradient + emoji, not external images --
deliberate, so the demo never depends on an image CDN being reachable.

Team/club names are fictional (not real IPL/ISL teams) to avoid trademark
issues in a hackathon submission while keeping the "IPL season" / "football
season" awareness fully demonstrable.
"""
from __future__ import annotations

import hashlib

CATEGORIES = ["men", "women", "kids", "unisex"]

PALETTE = ["#e0245e", "#1d9bf0", "#17bf63", "#f5b301", "#7c3aed", "#0ea5e9",
           "#dc2626", "#059669", "#d97706", "#9333ea", "#0891b2", "#be123c"]

_ARCHETYPES = [
    # MEN
    ("Royal Diwali Kurta Set", "men", ["diwali", "ethnic", "festive", "gifting"], "🪔", (1299, 2499)),
    ("Wedding Sherwani — Ivory", "men", ["wedding", "sherwani", "ethnic"], "🤵", (4999, 8999)),
    ("Classic Cotton Shirt", "men", ["summer", "cotton", "casual"], "👔", (799, 1499)),
    ("Pure Linen Shirt", "men", ["summer", "linen", "casual"], "👕", (1199, 1999)),
    ("Mumbai Blues Jersey", "men", ["ipl", "cricket", "jersey", "sports"], "🏏", (899, 1499)),
    ("Chennai Kings Jersey", "men", ["ipl", "cricket", "jersey", "sports"], "🏏", (899, 1499)),
    ("Bangalore Royals Jersey", "men", ["ipl", "cricket", "jersey", "sports"], "🏏", (899, 1499)),
    ("Kolkata United FC Jersey", "men", ["football", "jersey", "sports"], "⚽", (999, 1599)),
    ("Mumbai FC Away Jersey", "men", ["football", "jersey", "sports"], "⚽", (999, 1599)),
    ("Holi Splash White Kurta", "men", ["holi", "white", "festive"], "🎨", (699, 1199)),
    ("Tricolor Republic Polo", "men", ["patriotic", "tricolor", "republic_day"], "🇮🇳", (599, 999)),
    ("Christmas Cable-Knit Sweater", "men", ["christmas", "winter", "party"], "🎄", (1499, 2299)),
    ("Mountain Wool Jacket", "men", ["winter", "wool"], "🧥", (2499, 4499)),
    ("Quick-Dry Monsoon Raincoat", "men", ["monsoon", "quick-dry"], "🌧️", (1099, 1899)),
    ("Nehru Jacket — Maroon Silk", "men", ["wedding", "ethnic"], "🎩", (1999, 3499)),
    ("Performance Track Pants", "men", ["sportswear", "casual"], "🏃", (799, 1299)),
    ("Formal Charcoal Blazer", "men", ["formal", "wedding"], "🧥", (3499, 5999)),
    # WOMEN
    ("Anarkali Set — Emerald", "women", ["diwali", "ethnic", "festive"], "🪔", (1799, 3299)),
    ("Lehenga Choli — Blush Pink", "women", ["wedding", "lehenga", "ethnic"], "👗", (5999, 11999)),
    ("Banarasi Silk Saree", "women", ["wedding", "ethnic", "festive"], "🥻", (3999, 8999)),
    ("Everyday Cotton Kurti", "women", ["summer", "ethnic", "casual"], "👚", (599, 999)),
    ("Breezy Palazzo Set", "women", ["summer", "casual"], "👖", (899, 1499)),
    ("Navratri Chaniya Choli", "women", ["navratri", "garba", "ethnic"], "💃", (1999, 3999)),
    ("Rakhi Gifting Kurti Set", "women", ["rakhi", "ethnic", "gifting"], "🎁", (999, 1799)),
    ("Holi White Co-ord Set", "women", ["holi", "white", "festive"], "🎨", (899, 1399)),
    ("Christmas Velvet Party Dress", "women", ["christmas", "party"], "🎄", (1799, 2999)),
    ("Cozy Knit Shrug", "women", ["winter"], "🧶", (799, 1299)),
    ("Monsoon Rain Poncho", "women", ["monsoon", "quick-dry"], "🌧️", (999, 1599)),
    ("Tricolor Dupatta Set", "women", ["patriotic", "tricolor", "independence_day"], "🇮🇳", (699, 1199)),
    ("Western Jumpsuit — Black", "women", ["western", "party", "newyear"], "🕺", (1499, 2499)),
    ("Office Formal Co-ord", "women", ["formal"], "👩‍💼", (1799, 2999)),
    ("Durga Puja Tant Saree", "women", ["durga_puja", "ethnic", "festive"], "🥻", (2499, 4499)),
    # KIDS
    ("Kids IPL Jersey — Mini Fan", "kids", ["ipl", "cricket", "jersey"], "🏏", (499, 799)),
    ("Kids Football Jersey", "kids", ["football", "jersey"], "⚽", (499, 799)),
    ("Kids Diwali Kurta Set", "kids", ["diwali", "ethnic", "festive"], "🪔", (799, 1299)),
    ("Kids Christmas Costume", "kids", ["christmas", "party"], "🎄", (699, 1099)),
    ("Kids Summer Cotton Tee", "kids", ["summer", "casual"], "👕", (349, 599)),
    ("Kids Puffer Winter Jacket", "kids", ["winter"], "🧥", (999, 1599)),
    ("Kids Holi Splash Tee", "kids", ["holi", "white"], "🎨", (399, 699)),
    ("Kids Navratri Ethnic Set", "kids", ["navratri", "ethnic"], "💃", (799, 1299)),
    ("Kids Everyday Co-ord", "kids", ["casual"], "🧒", (599, 999)),
    ("Kids Rakhi Special Set", "kids", ["rakhi", "ethnic", "gifting"], "🎁", (699, 1099)),
    # UNISEX
    ("Unisex IPL Fan Jersey", "unisex", ["ipl", "cricket", "jersey", "sports"], "🏏", (799, 1299)),
    ("Unisex Football Jersey", "unisex", ["football", "jersey", "sports"], "⚽", (799, 1299)),
    ("Oversized Winter Hoodie", "unisex", ["winter", "casual"], "🧥", (1199, 1899)),
    ("Graphic Streetwear Tee", "unisex", ["casual"], "👕", (599, 999)),
    ("Performance Track Suit", "unisex", ["sportswear"], "🏃", (1499, 2299)),
    ("Packable Monsoon Raincoat", "unisex", ["monsoon", "quick-dry"], "🌧️", (999, 1599)),
    ("Tricolor Pride Tee", "unisex", ["patriotic", "tricolor"], "🇮🇳", (499, 799)),
    ("Festive Linen Kurta", "unisex", ["diwali", "ethnic", "festive"], "🪔", (999, 1599)),
    ("New Year Sequin Shirt", "unisex", ["newyear", "party"], "🎉", (1299, 1999)),
    ("Summer Linen Co-ord Set", "unisex", ["summer", "linen"], "🌞", (1199, 1899)),
]

# Accessories -- added so the AI Stylist can compose a genuine hero + layer +
# accessory look instead of recommending a single item in isolation.
_ACCESSORY_ARCHETYPES = [
    ("IPL Fan Cap — Team Colors", "unisex", ["ipl", "cricket", "sports"], "🧢", (299, 499)),
    ("Football Scarf — Club Colors", "unisex", ["football", "sports"], "🧣", (349, 599)),
    ("Festive Juttis — Embroidered", "women", ["wedding", "diwali", "ethnic", "festive"], "👡", (799, 1499)),
    ("Men's Mojari Footwear", "men", ["wedding", "ethnic", "festive"], "👞", (899, 1599)),
    ("Statement Jhumka Earrings", "women", ["wedding", "diwali", "ethnic", "festive", "navratri"], "💎", (399, 899)),
    ("Aviator Sunglasses", "unisex", ["summer", "casual"], "🕶️", (599, 1199)),
    ("Printed Silk Stole", "women", ["wedding", "ethnic", "winter", "festive"], "🧣", (499, 999)),
    ("Leather Belt — Formal", "men", ["formal", "wedding"], "👔", (699, 1299)),
    ("Knit Beanie", "unisex", ["winter", "casual"], "🧢", (299, 549)),
    ("Party Clutch — Sequin", "women", ["newyear", "party", "christmas"], "👛", (799, 1499)),
]

_LAYER_KEYWORDS = ["jacket", "sweater", "poncho", "raincoat", "shrug", "blazer", "hoodie", "coat"]


def _slug(name: str) -> str:
    return "p_" + hashlib.sha1(name.encode()).hexdigest()[:10]


def _build() -> list[dict]:
    out = []
    combined = [(*a, "hero") for a in _ARCHETYPES] + [(*a, "accessory") for a in _ACCESSORY_ARCHETYPES]
    for i, (name, category, tags, emoji, price_range, default_slot) in enumerate(combined):
        color = PALETTE[i % len(PALETTE)]
        lo, hi = price_range
        price = lo + ((hi - lo) * ((i * 37) % 100) // 100)
        popularity = round(0.35 + ((i * 17) % 50) / 100, 2)
        slot = default_slot
        if default_slot == "hero" and any(k in name.lower() for k in _LAYER_KEYWORDS):
            slot = "layer"
        out.append({
            "id": _slug(name),
            "name": name,
            "category": category,
            "tags": tags,
            "emoji": emoji,
            "color": color,
            "price_inr": price,
            "popularity": popularity,
            "slot": slot,
        })
    return out


PRODUCTS: list[dict] = _build()
PRODUCTS_BY_ID: dict[str, dict] = {p["id"]: p for p in PRODUCTS}


def by_tags(tags: set[str], limit: int = 8) -> list[dict]:
    scored = []
    for p in PRODUCTS:
        overlap = len(set(p["tags"]) & tags)
        if overlap > 0:
            scored.append((overlap + p["popularity"], p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]


def by_category(category: str) -> list[dict]:
    if category == "all":
        return PRODUCTS
    return [p for p in PRODUCTS if p["category"] == category]


def by_slot_and_tags(slot: str, tags: set[str], limit: int = 5) -> list[dict]:
    scored = []
    for p in PRODUCTS:
        if p["slot"] != slot:
            continue
        overlap = len(set(p["tags"]) & tags)
        scored.append((overlap + p["popularity"], p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]
