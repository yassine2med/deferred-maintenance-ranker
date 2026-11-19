import csv

import pytest

from dmranker.__main__ import main
from dmranker.ranker import (Item, RankerError, load_items, rank, risk_score,
                             within_budget)

HEADER = ["id", "building", "description", "condition", "consequence", "cost", "life_safety"]


def write(tmp_path, rows, header=HEADER):
    path = tmp_path / "b.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def test_risk_score_basic():
    assert risk_score(4, 3, False) == 12


def test_risk_score_life_safety_adds_ten():
    assert risk_score(2, 2, True) == 14


def test_load_computes_priority(tmp_path):
    items = load_items(write(tmp_path, [["A1", "B", "x", 4, 5, 10000, "no"]]))
    assert items[0].risk == 20
    assert items[0].priority == 2.0


def test_life_safety_ranks_first(tmp_path):
    p = write(tmp_path, [["A1", "B", "big", 5, 5, 1000, "no"], ["A2", "B", "safe", 1, 1, 1000, "yes"]])
    assert [i.id for i in rank(load_items(p))] == ["A2", "A1"]


def test_ties_prefer_cheaper(tmp_path):
    p = write(tmp_path, [["A1", "B", "x", 2, 2, 9000, "no"], ["A2", "B", "y", 2, 2, 3000, "no"]])
    assert rank(load_items(p))[0].id == "A2"


def test_budget_skips_items_that_do_not_fit():
    items = [Item("1", "B", "a", 5, 5, 8000, False, 25, 3.1),
             Item("2", "B", "b", 4, 4, 9000, False, 16, 1.8),
             Item("3", "B", "c", 3, 3, 1500, False, 9, 6.0)]
    assert [i.id for i in within_budget(items, 10000)] == ["1", "3"]


def test_missing_column(tmp_path):
    p = write(tmp_path, [["A1", "B", "x"]], header=["id", "building", "description"])
    with pytest.raises(RankerError, match="missing columns"):
        load_items(p)


@pytest.mark.parametrize("row", [
    ["A1", "B", "x", 6, 3, 100, "no"],
    ["A1", "B", "x", 3, 3, 0, "no"],
    ["A1", "B", "x", 3, 3, 100, "maybe"],
    ["A1", "B", "x", "abc", 3, 100, "no"],
])
def test_bad_rows_rejected(tmp_path, row):
    with pytest.raises(RankerError):
        load_items(write(tmp_path, [row]))


def test_cli_missing_file_returns_1(capsys):
    assert main(["nope.csv"]) == 1
    assert "error" in capsys.readouterr().err


def test_cli_sample_data(capsys):
    assert main(["data/backlog.csv", "--budget", "20000"]) == 0
    assert "D01" in capsys.readouterr().out
