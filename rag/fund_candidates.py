"""Extract example scheme names from the project's locally maintained guidance file."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_local_fund_examples() -> dict[str, list[str]]:
    """Return names explicitly listed as examples, grouped by broad asset class."""
    source = PROJECT_ROOT / "data" / "raw" / "fund_knowledge.txt"
    candidates: dict[str, list[str]] = {"Equity": [], "Debt": [], "Hybrid": []}
    if not source.exists():
        return candidates
    content = source.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^===\s*(.*?)\s*===$", content)
    for heading, body in zip(blocks[1::2], blocks[2::2]):
        normalized = heading.lower()
        if any(x in normalized for x in ("large cap", "mid cap", "small cap", "elss", "equity", "flexi cap")):
            bucket = "Equity"
        elif "debt" in normalized:
            bucket = "Debt"
        elif "hybrid" in normalized or "balanced advantage" in normalized:
            bucket = "Hybrid"
        else:
            continue
        match = re.search(r"(?im)^Examples:\s*(.+)$", body)
        if match:
            for name in (item.strip().rstrip(".") for item in match.group(1).split(",")):
                if name and name not in candidates[bucket]:
                    candidates[bucket].append(name)
    return candidates
