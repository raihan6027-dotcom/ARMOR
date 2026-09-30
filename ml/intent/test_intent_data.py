"""Dataset integrity and training helpers (no model training in CI)."""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "dataset"))

from common import (  # noqa: E402
    DATASET,
    LABELS,
    PARAPHRASE,
    apply_threshold,
    check_reviewed,
    harmful_leak_rate,
    read_rows,
)
from generate import FIELDS, build, split_hash  # noqa: E402


def test_schema_and_size():
    rows = read_rows(DATASET)
    assert list(rows[0]) == FIELDS
    assert len(rows) == 3500
    assert Counter(r["intent"] for r in rows) == dict.fromkeys(LABELS, 350)
    assert {r["bahasa"] for r in rows} == {"id", "en"}
    assert {r["media"] for r in rows} == {"IMAGE", "VIDEO", "AUDIO"}
    assert len({r["id"] for r in rows}) == 3500


def test_split_is_stratified_70_15_15():
    rows = read_rows(DATASET)
    for label in LABELS:
        c = Counter(r["split"] for r in rows if r["intent"] == label)
        assert c == {"train": 245, "val": 52, "test": 53}


def test_test_split_is_frozen():
    frozen = json.loads((HERE / "dataset" / "splits.json").read_text(encoding="utf-8"))
    assert split_hash(read_rows(DATASET)) == frozen["test_sha256"]
    r = subprocess.run(
        [sys.executable, str(HERE / "dataset" / "generate.py"), "--check"], capture_output=True
    )
    assert r.returncode == 0


def test_generation_is_deterministic():
    a, b = build(), build()
    assert [r["prompt"] for r in a] == [r["prompt"] for r in b]


def test_paraphrase_set_is_disjoint_from_training_data():
    train = {r["prompt"].lower() for r in read_rows(DATASET)}
    para = read_rows(PARAPHRASE)
    assert len(para) >= 80
    assert not any(p["prompt"].lower() in train for p in para)
    assert {p["intent"] for p in para} == set(LABELS)


def test_final_training_refuses_unreviewed_rows():
    rows = [{"diperiksa_oleh": ""}, {"diperiksa_oleh": "RA"}]
    with pytest.raises(SystemExit):
        check_reviewed(rows, allow_unreviewed=False)
    assert check_reviewed(rows, allow_unreviewed=True) == 1


def test_apply_threshold_and_leak_rate():
    proba = np.array([[0.9, 0.1], [0.55, 0.45]])
    assert apply_threshold(proba, ["DEFAMATION", "PERSONAL_CREATION"], 0.6) == [
        "DEFAMATION",
        "UNCERTAIN",
    ]
    y_true = ["DEFAMATION", "DEFAMATION", "SEXUAL_EXPLICIT", "PERSONAL_CREATION"]
    y_pred = ["DEFAMATION", "UNCERTAIN", "PERSONAL_CREATION", "PERSONAL_CREATION"]
    assert harmful_leak_rate(y_true, y_pred) == pytest.approx(1 / 3)
    assert harmful_leak_rate(["PERSONAL_CREATION"], ["UNCERTAIN"]) is None
