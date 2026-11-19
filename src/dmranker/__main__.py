"""Command line: python -m dmranker backlog.csv [--budget N]."""
from __future__ import annotations

import argparse
import sys

from .ranker import RankerError, format_table, load_items, rank, within_budget


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dmranker", description=__doc__)
    parser.add_argument("csv_file")
    parser.add_argument("--budget", type=float, help="show only items that fit this budget")
    args = parser.parse_args(argv)
    try:
        ranked = rank(load_items(args.csv_file))
    except (RankerError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.budget is not None:
        ranked = within_budget(ranked, args.budget)
    print(format_table(ranked))
    print(f"\n{len(ranked)} items, total cost {sum(i.cost for i in ranked):,.0f} (* = life safety)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
