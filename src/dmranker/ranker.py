"""Rank deferred maintenance items by risk per unit of cost."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

REQUIRED = ("id", "building", "description", "condition", "consequence", "cost", "life_safety")


class RankerError(ValueError):
    """Raised when the input file or a row is not valid."""


@dataclass(frozen=True)
class Item:
    """One backlog item with its computed scores."""

    id: str
    building: str
    description: str
    condition: int      # 1 (good) to 5 (failed)
    consequence: int    # 1 (minor) to 5 (severe)
    cost: float
    life_safety: bool
    risk: int = 0
    priority: float = 0.0


def risk_score(condition: int, consequence: int, life_safety: bool) -> int:
    """Return condition x consequence, plus 10 when life safety is involved."""
    return condition * consequence + (10 if life_safety else 0)


def _parse_row(row: dict[str, str], line: int) -> Item:
    try:
        condition = int(row["condition"])
        consequence = int(row["consequence"])
        cost = float(row["cost"])
    except ValueError as exc:
        raise RankerError(f"line {line}: bad number ({exc})") from exc
    if not (1 <= condition <= 5 and 1 <= consequence <= 5):
        raise RankerError(f"line {line}: condition and consequence must be 1 to 5")
    if cost <= 0:
        raise RankerError(f"line {line}: cost must be above zero")
    flag = row["life_safety"].strip().lower()
    if flag not in {"yes", "no"}:
        raise RankerError(f"line {line}: life_safety must be yes or no")
    safety = flag == "yes"
    risk = risk_score(condition, consequence, safety)
    # Priority = risk points per 1,000 dollars, so cheap high-risk fixes rise.
    priority = round(risk / (cost / 1000), 2)
    return Item(row["id"].strip(), row["building"].strip(), row["description"].strip(),
                condition, consequence, cost, safety, risk, priority)


def load_items(path: str | Path) -> list[Item]:
    """Read a backlog CSV and return scored items."""
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise RankerError("missing columns: " + ", ".join(missing))
        return [_parse_row(row, n) for n, row in enumerate(reader, start=2)]


def rank(items: list[Item]) -> list[Item]:
    """Sort by life safety first, then risk, then priority, then cheaper cost."""
    return sorted(items, key=lambda i: (not i.life_safety, -i.risk, -i.priority, i.cost))


def within_budget(ranked: list[Item], budget: float) -> list[Item]:
    """Pick items in rank order while they fit the budget (skips items that do not fit)."""
    chosen: list[Item] = []
    left = budget
    for item in ranked:
        if item.cost <= left:
            chosen.append(item)
            left -= item.cost
    return chosen


def format_table(items: list[Item]) -> str:
    """Return a plain text table."""
    head = f"{'Rank':<5}{'ID':<8}{'Building':<12}{'Risk':>5}{'Cost':>10}  Description"
    lines = [head]
    for n, i in enumerate(items, start=1):
        flag = "*" if i.life_safety else " "
        lines.append(f"{n:<5}{i.id:<8}{i.building:<12}{i.risk:>5}{i.cost:>10,.0f}{flag} {i.description}")
    return "\n".join(lines)
