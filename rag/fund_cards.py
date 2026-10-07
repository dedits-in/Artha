"""Load fund detail cards from the scheme files in data/raw for display."""

from __future__ import annotations

import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
GUIDANCE_FILES = {"fund_knowledge.txt", "fund_category_guide.txt"}
SHOW_KEYS = ("fund name", "fund house", "scheme category")
EXTRA_KEY_PATTERN = re.compile(r"nav|return|year|cagr|expense|risk", re.IGNORECASE)


def _bucket(category: str) -> str | None:
    c = category.lower()
    if any(k in c for k in ("hybrid", "balanced", "asset allocation", "arbitrage")):
        return "Hybrid"
    if any(k in c for k in ("debt", "bond", "liquid", "duration", "gilt", "money market", "credit risk")):
        return "Debt"
    if any(k in c for k in ("equity", "elss", "cap fund", "flexi")):
        return "Equity"
    return None


def _parse(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and value.strip():
            fields.setdefault(key.strip(), value.strip())
    return fields


def load_fund_cards(per_bucket: int = 6) -> dict[str, list[dict]]:
    """Return {'Equity': [...], 'Debt': [...], 'Hybrid': [...]} of display rows."""
    cards: dict[str, list[dict]] = {"Equity": [], "Debt": [], "Hybrid": []}
    if not RAW_DIR.exists():
        return cards
    seen = set()
    for path in sorted(RAW_DIR.glob("*.txt")):
        if path.name in GUIDANCE_FILES:
            continue
        try:
            fields = _parse(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        lowered = {k.lower(): k for k in fields}
        name = fields.get(lowered.get("fund name", ""), "")
        category = fields.get(lowered.get("scheme category", ""), "")
        bucket = _bucket(category)
        if not name or not bucket or name in seen or len(cards[bucket]) >= per_bucket:
            continue
        seen.add(name)
        row = {"Fund": name, "Fund house": fields.get(lowered.get("fund house", ""), ""), "Category": category}
        for key, value in fields.items():
            if key.lower() not in SHOW_KEYS and EXTRA_KEY_PATTERN.search(key):
                row[key] = value
        cards[bucket].append(row)
    return cards