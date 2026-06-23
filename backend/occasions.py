"""Indian occasion calendar: festivals, regional events, sports seasons, and
weather seasons, each mapped to product tags + a merchandising theme.

Dates are illustrative (month/day, year-independent) for demo purposes -- this
is intentionally not a precise lunar-calendar implementation (Eid, for
instance, shifts every year); the point being demonstrated is that the whole
system's behaviour is *driven by a date*, which the Time Machine lets you
move freely. Swapping in a real festival-calendar API later is integration
work, not a design change.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Occasion:
    key: str
    label: str
    start: tuple[int, int]  # (month, day)
    end: tuple[int, int]
    tags: list[str]
    theme: str
    kind: str  # "festival" | "sport" | "season" | "national" | "wedding" | "party"


OCCASIONS: list[Occasion] = [
    Occasion("republic_day", "Republic Day", (1, 18), (1, 26), ["patriotic", "tricolor", "republic_day"],
              "Patriotic Edit — Tricolor & Khadi", "national"),
    Occasion("holi", "Holi", (3, 1), (3, 12), ["holi", "white", "colorful"],
              "Holi Whites & Colour-Splash Tees", "festival"),
    Occasion("ipl_season", "IPL Season", (3, 15), (5, 31), ["ipl", "cricket", "jersey", "sports"],
              "IPL Fan Gear — Team Jerseys & Caps", "sport"),
    Occasion("summer", "Summer", (3, 1), (6, 15), ["summer", "cotton", "linen", "light"],
              "Summer Cottons & Linen", "season"),
    Occasion("eid", "Eid", (3, 28), (4, 6), ["eid", "ethnic", "festive", "gifting"],
              "Eid Ethnic Edit (illustrative date)", "festival"),
    Occasion("wedding_summer", "Wedding Season", (4, 1), (6, 30), ["wedding", "sherwani", "lehenga", "sangeet"],
              "Wedding Season Edit", "wedding"),
    Occasion("monsoon", "Monsoon", (6, 16), (9, 15), ["monsoon", "quick-dry", "raincoat"],
              "Monsoon-Ready Fits", "season"),
    Occasion("rakhi", "Raksha Bandhan", (8, 15), (8, 24), ["rakhi", "ethnic", "gifting"],
              "Raksha Bandhan Gifting Edit", "festival"),
    Occasion("independence_day", "Independence Day", (8, 9), (8, 16), ["patriotic", "tricolor"],
              "Independence Day Tricolor Edit", "national"),
    Occasion("ganesh_chaturthi", "Ganesh Chaturthi", (8, 25), (9, 15), ["festive", "ethnic", "maharashtra"],
              "Ganesh Chaturthi Festive Edit", "festival"),
    Occasion("football_season", "Football Season (ISL)", (9, 1), (12, 31), ["football", "jersey", "sports"],
              "Football Season Jerseys", "sport"),
    Occasion("football_season_2", "Football Season (ISL)", (1, 1), (3, 31), ["football", "jersey", "sports"],
              "Football Season Jerseys", "sport"),
    Occasion("navratri_durga_puja", "Navratri & Durga Puja", (9, 20), (10, 15),
              ["navratri", "durga_puja", "garba", "ethnic"], "Navratri & Durga Puja Edit", "festival"),
    Occasion("diwali", "Diwali", (10, 16), (11, 5), ["diwali", "ethnic", "festive", "gifting", "lights"],
              "Diwali Festive Edit", "festival"),
    Occasion("wedding_winter", "Wedding Season", (11, 1), (2, 15), ["wedding", "sherwani", "lehenga"],
              "Wedding Season Edit", "wedding"),
    Occasion("winter", "Winter", (11, 1), (2, 15), ["winter", "wool", "jacket"],
              "Winter Layers", "season"),
    Occasion("christmas", "Christmas", (12, 15), (12, 26), ["christmas", "party", "winter"],
              "Christmas Party Edit", "party"),
    Occasion("new_year", "New Year", (12, 27), (1, 3), ["newyear", "party"],
              "New Year Party Edit", "party"),
]

ALL_TAGS = sorted({t for o in OCCASIONS for t in o.tags})


def _in_range(md: tuple[int, int], start: tuple[int, int], end: tuple[int, int]) -> bool:
    if start <= end:
        return start <= md <= end
    return md >= start or md <= end  # wraps over year boundary (e.g. Dec -> Jan)


def active_occasions(dt: datetime) -> list[Occasion]:
    md = (dt.month, dt.day)
    return [o for o in OCCASIONS if _in_range(md, o.start, o.end)]


# When multiple occasions are active at once (e.g. football season runs
# Sep-Mar and overlaps Diwali in late Oct), this decides which one "wins" for
# a single headline message/banner -- festivals are the most story-worthy,
# broad seasons the least.
KIND_PRIORITY = {"festival": 0, "national": 1, "party": 2, "sport": 3, "wedding": 4, "season": 5}


def headline(active: list[Occasion], product_tags: set[str] | None = None) -> Occasion | None:
    if not active:
        return None
    if product_tags:
        scored = [(len(set(o.tags) & product_tags), -KIND_PRIORITY.get(o.kind, 9), o) for o in active]
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        if scored[0][0] > 0:
            return scored[0][2]
    return sorted(active, key=lambda o: KIND_PRIORITY.get(o.kind, 9))[0]


def next_occurrence(month: int, day: int, after: date) -> date:
    candidate = date(after.year, month, day)
    if candidate < after:
        candidate = date(after.year + 1, month, day)
    return candidate


def quick_jump_targets(reference: date | None = None) -> list[dict]:
    reference = reference or date.today()
    seen = set()
    out = []
    for o in OCCASIONS:
        if o.key in seen:
            continue
        seen.add(o.key)
        target = next_occurrence(*o.start, after=reference)
        out.append({"key": o.key, "label": o.label, "date": target.isoformat(), "theme": o.theme, "kind": o.kind})
    out.sort(key=lambda x: x["date"])
    return out
