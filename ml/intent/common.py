"""Shared helpers for Intent AI training scripts (baseline and IndoBERT).

Both trainers produce the same report format so docs/eval/intent.md can compare
them side by side.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATASET = HERE / "dataset" / "intent_dataset.csv"
PARAPHRASE = HERE / "dataset" / "paraphrase.csv"
MODEL_DIR = REPO / "ml" / "models" / "intent"

LABELS = [
    "PERSONAL_CREATION",
    "PERSONAL_EDITING",
    "SATIRE_PARODY",
    "COMMERCIAL_USE",
    "POLITICAL_USE",
    "IMPERSONATION",
    "DEFAMATION",
    "SEXUAL_EXPLICIT",
    "DECEPTIVE",
    "UNCERTAIN",
]
HARMFUL = ["IMPERSONATION", "DEFAMATION", "SEXUAL_EXPLICIT", "DECEPTIVE"]


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_reviewed(rows: list[dict], allow_unreviewed: bool) -> int:
    """Number of unreviewed rows; raises unless explicitly allowed (experiments)."""
    missing = sum(1 for r in rows if not r["diperiksa_oleh"].strip())
    if missing and not allow_unreviewed:
        raise SystemExit(
            f"{missing} baris belum diperiksa (kolom diperiksa_oleh kosong). "
            "Training final ditolak. Untuk eksperimen, tambahkan --allow-unreviewed."
        )
    return missing


def apply_threshold(proba: np.ndarray, classes: list[str], threshold: float) -> list[str]:
    """argmax, but UNCERTAIN when the top probability is below the threshold."""
    top = proba.argmax(axis=1)
    return [
        "UNCERTAIN" if proba[i, top[i]] < threshold else classes[top[i]] for i in range(len(top))
    ]


def scores(y_true: list[str], y_pred: list[str]) -> dict:
    from sklearn.metrics import confusion_matrix, f1_score, recall_score

    per_class = f1_score(y_true, y_pred, labels=LABELS, average=None, zero_division=0)
    harmful_recall = recall_score(y_true, y_pred, labels=HARMFUL, average=None, zero_division=0)
    return {
        "n": len(y_true),
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)
        ),
        "f1_per_class": {lbl: float(v) for lbl, v in zip(LABELS, per_class, strict=True)},
        "harmful_recall": {lbl: float(v) for lbl, v in zip(HARMFUL, harmful_recall, strict=True)},
        "harmful_recall_mean": float(np.mean(harmful_recall)),
        "confusion": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        "harmful_leak_rate": harmful_leak_rate(y_true, y_pred),
    }


def harmful_leak_rate(y_true: list[str], y_pred: list[str]) -> float | None:
    """Share of harmful prompts predicted as a permissive class (not harmful, not
    UNCERTAIN). These are the misses that can slip through: a harmful prompt that
    becomes UNCERTAIN still ends in REVIEW (fail-safe), but one that becomes
    PERSONAL_CREATION can be ALLOWed."""
    harmful = [(t, p) for t, p in zip(y_true, y_pred, strict=True) if t in HARMFUL]
    if not harmful:
        return None
    leaked = sum(1 for _, p in harmful if p not in HARMFUL and p != "UNCERTAIN")
    return leaked / len(harmful)


def choose_threshold(proba: np.ndarray, classes: list[str], y_val: list[str]) -> tuple[float, list]:
    """Pick the UNCERTAIN threshold on validation data: the value in [0.20, 0.90]
    with the best macro F1; ties go to the lower threshold (fewer needless
    REVIEWs). Returns (threshold, sweep table)."""
    sweep = []
    for t in np.round(np.arange(0.20, 0.91, 0.05), 2):
        s = scores(y_val, apply_threshold(proba, classes, float(t)))
        sweep.append((float(t), s["macro_f1"], s["harmful_recall_mean"]))
    best = max(sweep, key=lambda row: (round(row[1], 4), -row[0]))
    return best[0], sweep


def plot_confusion(conf: list[list[int]], path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m = np.asarray(conf)
    fig, ax = plt.subplots(figsize=(7, 6), dpi=120)
    ax.imshow(m, cmap="Blues")
    short = [lbl.replace("_", "\n") for lbl in LABELS]
    ax.set_xticks(range(len(LABELS)), short, fontsize=6, rotation=90)
    ax.set_yticks(range(len(LABELS)), short, fontsize=6)
    for i in range(len(LABELS)):
        for j in range(len(LABELS)):
            if m[i, j]:
                ax.text(
                    j,
                    i,
                    m[i, j],
                    ha="center",
                    va="center",
                    fontsize=6,
                    color="white" if m[i, j] > m.max() / 2 else "black",
                )
    ax.set_xlabel("Prediksi")
    ax.set_ylabel("Label")
    ax.set_title(title, fontsize=9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def save_report(name: str, payload: dict) -> Path:
    out = MODEL_DIR / f"{name}_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
