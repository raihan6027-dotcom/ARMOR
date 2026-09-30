"""Kappa math, label merging, and scenario generation (no human labels needed)."""

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from kappa import cohen_kappa, merge  # noqa: E402
from scenarios import FIELDS, build  # noqa: E402


def test_kappa_perfect_and_chance():
    a = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] * 5
    assert cohen_kappa(a, a) == pytest.approx(1.0)
    assert cohen_kappa(a, a, weighted=True) == pytest.approx(1.0)
    # Textbook example: 2 raters, agreement 0.7, chance 0.5 -> kappa 0.4
    x = ["LOW"] * 35 + ["LOW"] * 15 + ["HIGH"] * 15 + ["HIGH"] * 35
    y = ["LOW"] * 35 + ["HIGH"] * 15 + ["LOW"] * 15 + ["HIGH"] * 35
    assert cohen_kappa(x, y) == pytest.approx(0.4)


def test_weighted_kappa_penalizes_far_disagreement_more():
    base = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] * 10
    near = ["MEDIUM" if v == "LOW" else v for v in base]
    far = ["CRITICAL" if v == "LOW" else v for v in base]
    assert cohen_kappa(base, near, weighted=True) > cohen_kappa(base, far, weighted=True)


def test_merge_agreed_disputed_and_discussed():
    a = {"S1": {"label": "LOW"}, "S2": {"label": "HIGH"}, "S3": {"label": ""}}
    b = {"S1": {"label": "low"}, "S2": {"label": "CRITICAL"}, "S3": {"label": "LOW"}}
    agreed, disputed, la, _ = merge(a, b, {})
    assert agreed == [{"scenario_id": "S1", "label": "LOW", "source": "sepakat"}]
    assert disputed[0]["scenario_id"] == "S2" and len(la) == 2
    agreed, _, _, _ = merge(a, b, {"S2": {"label_final": "CRITICAL"}})
    assert {r["scenario_id"]: r["source"] for r in agreed} == {"S1": "sepakat", "S2": "diskusi"}


def test_merge_rejects_unknown_label():
    with pytest.raises(SystemExit):
        merge({"S1": {"label": "PANIC"}}, {"S1": {"label": "LOW"}}, {})


def test_scenarios_are_deterministic_unique_and_consistent():
    rows = build(200)
    assert rows == build(200)
    keys = {tuple(r[k] for k in FIELDS[1:9]) for r in rows}
    assert len(keys) == 200
    for r in rows:
        assert not (r["synthetic_voice"] and r["media"] in ("IMAGE", "TEXT_ONLY"))
        assert "consent" not in r
