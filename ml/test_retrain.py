"""Fase 6b: the evaluation gate rejects a worse model; versions and rollback work.

Uses a small dataset built on the fly (template prompts from the real generator)
so the test runs in seconds and never touches ml/models/.
"""

import csv
import json
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "intent" / "dataset"))

from generate import FIELDS  # noqa: E402

import retrain  # noqa: E402

HARMFUL = ["IMPERSONATION", "DEFAMATION", "SEXUAL_EXPLICIT", "DECEPTIVE"]


def test_gate_rejects_lower_macro_f1_or_harmful_recall():
    cur = {"macro_f1": 0.80, "harmful_recall_mean": 0.90}
    assert retrain.gate(cur, {"macro_f1": 0.85, "harmful_recall_mean": 0.90})[0] is True
    assert retrain.gate(cur, {"macro_f1": 0.80, "harmful_recall_mean": 0.90})[0] is True
    ok, reasons = retrain.gate(cur, {"macro_f1": 0.79, "harmful_recall_mean": 0.95})
    assert ok is False and "macro F1 turun" in reasons[0]
    ok, reasons = retrain.gate(cur, {"macro_f1": 0.95, "harmful_recall_mean": 0.85})
    assert ok is False and "recall kelas berbahaya turun" in reasons[1]
    assert retrain.gate(None, {"macro_f1": 0.1, "harmful_recall_mean": 0.1})[0] is True


@pytest.fixture()
def small(tmp_path):
    """60 rows per class, reviewed, with a fixed split."""
    from generate import build

    rng = random.Random(0)
    by_class = {}
    for r in build():
        by_class.setdefault(r["intent"], []).append(r)
    rows = []
    for items in by_class.values():
        rng.shuffle(items)
        for k, r in enumerate(items[:60]):
            rows.append(
                r
                | {
                    "split": "train" if k < 40 else "val" if k < 50 else "test",
                    "diperiksa_oleh": "UJI",
                }
            )
    path = tmp_path / "dataset.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return path, rows, tmp_path / "models"


def _feedback(tmp_path, rows):
    path = tmp_path / "feedback.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "feedback_id",
                "prompt",
                "intent_final",
                "risk_final",
                "features",
                "diperiksa_oleh",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    return path


def test_poisoned_feedback_is_rejected_and_clean_feedback_accepted(small, tmp_path):
    dataset, rows, model_dir = small
    first = retrain.retrain_intent(dataset, tmp_path / "none.csv", model_dir)
    assert first["accepted"] is True  # nothing to compare with yet
    active = json.loads((model_dir / "active.json").read_text())
    assert active["model_version"] == first["model_version"]

    # Poison: harmful training prompts relabeled as harmless, many times over.
    harmful_train = [r for r in rows if r["split"] == "train" and r["intent"] in HARMFUL]
    poison = [
        {
            "feedback_id": f"P{i}",
            "prompt": r["prompt"] + suffix,
            "intent_final": "PERSONAL_CREATION",
            "risk_final": "",
            "features": "",
            "diperiksa_oleh": "UJI",
        }
        for i, (r, suffix) in enumerate(
            (r, s) for r in harmful_train for s in ("", " ya", " tolong", " dong")
        )
    ]
    worse = retrain.retrain_intent(dataset, _feedback(tmp_path, poison), model_dir)
    assert worse["accepted"] is False
    assert any("turun" in reason for reason in worse["reasons"])
    # The active model did not change and the rejected file was not written.
    assert (
        json.loads((model_dir / "active.json").read_text())["model_version"]
        == first["model_version"]
    )
    assert not (model_dir / f"{worse['model_version']}.joblib").exists()

    clean = [
        {
            "feedback_id": f"C{i}",
            "prompt": r["prompt"] + " sekarang",
            "intent_final": r["intent"],
            "risk_final": "",
            "features": "",
            "diperiksa_oleh": "UJI",
        }
        for i, r in enumerate(rows)
        if r["split"] == "train"
    ][:40]
    better = retrain.retrain_intent(dataset, _feedback(tmp_path, clean), model_dir)
    assert better["accepted"] is True
    assert (
        json.loads((model_dir / "active.json").read_text())["model_version"]
        == better["model_version"]
    )

    # Rollback to the first version.
    reg = retrain.Registry.load(model_dir)
    reg.rollback(first["model_version"])
    assert (
        json.loads((model_dir / "active.json").read_text())["model_version"]
        == first["model_version"]
    )
    events = [v["event"] for v in retrain.Registry.load(model_dir).versions]
    assert events == ["retrain", "retrain", "retrain", "rollback"]
    with pytest.raises(SystemExit):
        reg.rollback(worse["model_version"])  # rejected versions cannot be restored

    report = tmp_path / "retrain.md"
    retrain.append_report("intent", worse, report)
    assert "DITOLAK" in report.read_text(encoding="utf-8")


def test_unreviewed_and_test_set_feedback_are_never_used(small, tmp_path):
    dataset, rows, model_dir = small
    test_prompt = next(r["prompt"] for r in rows if r["split"] == "test")
    fb = _feedback(
        tmp_path,
        [
            {
                "feedback_id": "U1",
                "prompt": "unreviewed prompt",
                "intent_final": "DEFAMATION",
                "risk_final": "",
                "features": "",
                "diperiksa_oleh": "",
            },
            {
                "feedback_id": "T1",
                "prompt": test_prompt,
                "intent_final": "UNCERTAIN",
                "risk_final": "",
                "features": "",
                "diperiksa_oleh": "UJI",
            },
            {
                "feedback_id": "B1",
                "prompt": "label aneh",
                "intent_final": "NOT_A_CLASS",
                "risk_final": "",
                "features": "",
                "diperiksa_oleh": "UJI",
            },
        ],
    )
    entry = retrain.retrain_intent(dataset, fb, model_dir)
    assert (
        entry["feedback_used"],
        entry["feedback_unreviewed_skipped"],
        entry["feedback_dropped"],
    ) == (0, 1, 2)


def test_changed_frozen_test_set_aborts(small, tmp_path):
    dataset, _, model_dir = small
    splits = tmp_path / "splits.json"
    splits.write_text(json.dumps({"test_sha256": "0" * 64}))
    with pytest.raises(SystemExit):
        retrain.retrain_intent(dataset, tmp_path / "none.csv", model_dir, splits=splits)


def test_risk_retrain_needs_human_labels(tmp_path):
    with pytest.raises(SystemExit):
        retrain.retrain_risk(
            tmp_path / "s.csv",
            tmp_path / "labels.csv",
            tmp_path / "f.csv",
            tmp_path,
            tmp_path / "t.json",
        )
