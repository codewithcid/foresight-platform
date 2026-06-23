"""Real product photography via the Pexels API, attached once at startup.

Pexels is the right source for this: free, explicitly licensed for
commercial/demo use, nothing scraped from a retailer's own catalog.

Three deliberate upgrades over a naive "search and take result #1" approach,
each fixing a specific failure mode a visual review caught:

1. Curated per-garment query phrases (not a generic formula) -- Pexels'
   library is Western-stock-photography-heavy, so "nehru jacket indian men"
   finds something real where a generic "jacket men's" search wandered off
   into unrelated photos.
2. Colour-aware ranking -- fetch several candidates per query and pick the
   one whose actual average colour (Pexels returns this per photo) is
   closest to the colour named in the product, instead of trusting text
   relevance alone (this is what fixed "Charcoal Blazer" returning pink).
3. Diversity by construction -- multiple products legitimately share a
   query (five different cricket jerseys, for instance). Round-robin
   assigning across several fetched candidates means they get *different*
   real photos instead of all five caching to the same single image.
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

import config as C

load_dotenv(C.ROOT / "backend" / ".env")

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PEXELS_URL = "https://api.pexels.com/v1/search"
CANDIDATES_PER_QUERY = 15  # covers the largest same-query sibling group (jerseys, 9-wide) with headroom

_search_cache: dict[tuple[str, str], list[dict]] = {}


def has_key() -> bool:
    return bool(PEXELS_API_KEY)


# Curated query phrase per garment noun -- checked against the product NAME,
# longest/most-specific terms first so "nehru jacket" wins over plain
# "jacket". Hand-tuned, not formulaic, because generic formulas produced
# off-theme results for anything Pexels' library covers thinly.
_GARMENT_QUERY: list[tuple[str, str]] = [
    ("nehru jacket", "nehru jacket indian men"),
    ("sherwani", "sherwani indian groom wedding"),
    ("lehenga", "lehenga choli indian bride"),
    ("chaniya choli", "chaniya choli garba dance"),
    ("anarkali", "anarkali suit indian woman"),
    ("kurti", "kurti indian woman ethnic"),
    ("kurta", "kurta indian men ethnic"),
    ("saree", "saree indian woman silk"),
    ("dupatta", "dupatta indian woman"),
    ("palazzo", "palazzo pants indian fashion"),
    ("jersey", "sports jersey athlete"),
    ("raincoat", "raincoat model rain"),
    ("poncho", "poncho rain fashion"),
    ("sweater", "sweater fashion model"),
    ("hoodie", "hoodie streetwear fashion"),
    ("blazer", "blazer formal fashion model"),
    ("jacket", "jacket fashion model"),
    ("shrug", "cardigan shrug fashion woman"),
    ("jumpsuit", "jumpsuit fashion model"),
    ("co-ord", "co-ord set fashion"),
    ("track suit", "tracksuit fashion model"),
    ("track pants", "joggers fashion model"),
    ("dress", "dress fashion model"),
    ("costume", "costume kids party"),
    ("t-shirt", "tshirt fashion model"),
    ("tshirt", "tshirt fashion model"),
    ("tee", "tshirt fashion model"),
    ("polo", "polo shirt fashion model"),
    ("set", "fashion outfit set"),
    ("stole", "silk shawl wrap woman"),
    ("juttis", "juttis indian footwear"),
    ("mojari", "mojari indian footwear"),
    ("earrings", "earrings jewelry fashion"),
    ("sunglasses", "sunglasses fashion model"),
    ("belt", "leather belt fashion"),
    ("beanie", "beanie hat fashion"),
    ("clutch", "clutch purse fashion"),
    ("scarf", "scarf fashion model"),
    ("cap", "cap hat fashion model"),
    ("shirt", "shirt fashion model"),
]

_GENDER_WORD = {"men": "men", "women": "women", "kids": "kids", "unisex": ""}

# Approximate target RGB per colour word, used to rank Pexels candidates by
# how close their actual average colour is to what the product names.
_COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "ivory": (255, 250, 240), "emerald": (0, 120, 90), "blush": (235, 180, 185),
    "black": (25, 25, 25), "maroon": (100, 30, 40), "charcoal": (70, 70, 75),
    "pink": (235, 130, 170), "blue": (50, 90, 180), "red": (190, 35, 35),
    "green": (40, 120, 60), "yellow": (230, 200, 50), "white": (245, 245, 245),
    "gold": (200, 165, 60), "silver": (190, 190, 195), "navy": (25, 35, 75),
    "beige": (220, 200, 170), "cream": (240, 230, 200), "purple": (110, 60, 140),
    "sequin": (200, 195, 180), "velvet": (90, 25, 45), "silk": (200, 190, 170),
    "cyan": (50, 180, 190), "grey": (130, 130, 130), "gray": (130, 130, 130),
    "orange": (220, 110, 40), "brown": (90, 55, 35), "olive": (95, 100, 55),
}
_COLOR_WORDS = set(_COLOR_RGB.keys())


def _extract_color(name: str) -> str:
    if "—" not in name:
        return ""
    suffix = name.split("—")[-1].strip().lower()
    return " ".join(w for w in suffix.split() if w in _COLOR_WORDS)


def _extract_garment(name: str) -> tuple[str, str]:
    """Returns (matched_term, query_phrase)."""
    lower = name.lower()
    for term, phrase in _GARMENT_QUERY:
        if term in lower:
            return term, phrase
    return "", ""


def query_for_product(product: dict) -> str:
    _, phrase = _extract_garment(product["name"])
    color = _extract_color(product["name"])
    if phrase:
        return f"{color} {phrase}".strip()
    gender = _GENDER_WORD.get(product["category"], "")
    tag = product["tags"][0] if product["tags"] else "fashion"
    return f"{gender} {tag} clothing".strip()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _orientation_for(product: dict) -> str:
    return "square" if product.get("slot") == "accessory" else "portrait"


def search_candidates(query: str, orientation: str) -> list[dict]:
    key = (query, orientation)
    if key in _search_cache:
        return _search_cache[key]
    if not PEXELS_API_KEY:
        return []
    try:
        resp = requests.get(
            PEXELS_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": CANDIDATES_PER_QUERY, "orientation": orientation},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos") or []
        candidates = [{"url": p["src"]["medium"], "avg_color": p.get("avg_color") or "#888888"} for p in photos]
        _search_cache[key] = candidates
        return candidates
    except Exception as exc:  # noqa: BLE001 - demo must never crash on image lookup
        print(f"[images] Pexels lookup failed for {query!r}: {exc}")
        _search_cache[key] = []
        return []


def attach_images(products: list[dict]) -> int:
    """Mutates each product dict in place with an 'image_url' key.

    Groups products by (query, orientation) so siblings sharing a query
    (e.g. several cricket jerseys) draw from the same candidate pool but get
    *different* photos via round-robin, ranked by colour match first.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for p in products:
        key = (query_for_product(p), _orientation_for(p))
        groups.setdefault(key, []).append(p)

    found = 0
    for (query, orientation), members in groups.items():
        candidates = search_candidates(query, orientation)
        if not candidates:
            for p in members:
                p["image_url"] = None
            continue

        for i, p in enumerate(members):
            target_color = _extract_color(p["name"])
            pool = candidates
            if target_color:
                target_rgb = _COLOR_RGB.get(target_color.split()[0])
                if target_rgb:
                    pool = sorted(candidates, key=lambda c: _color_distance(_hex_to_rgb(c["avg_color"]), target_rgb))
            chosen = pool[i % len(pool)]
            p["image_url"] = chosen["url"]
            found += 1
    return found
