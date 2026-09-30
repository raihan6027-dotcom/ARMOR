"""Risk AI training: Logistic Regression vs Random Forest, picked by macro F1.

Real run (after two annotators labeled the scenarios and kappa.py merged them):

    python ml/risk/train.py
      -> ml/models/risk/risk_model.joblib (not committed), ml/models/risk/active.json,
         docs/eval/risk.md, docs/eval/risk_importance.png

Smoke run with SYNTHETIC annotators (rule-based pseudo-annotators plus noise), only
to prove the pipeline runs end to end:

    python ml/risk/train.py --synthetic
      -> ml/models/risk/synthetic/ (never loaded by the backend), docs/eval/synthetic/risk-smoke.md

Evaluation: stratified 5-fold cross-validation on the agreed labels (macro F1 and F1
per level); the chosen model is then refit on all labels. Features come from
backend/app/ai/risk_features.py, the exact code the backend uses at inference.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(HERE))

from kappa import LEVELS  # noqa: E402
from kappa import main as run_kappa  # noqa: E402
from scenarios import FIELDS, build, write_csv  # noqa: E402

from app.ai.risk_features import (  # noqa: E402
    HIGH,
    RiskFeatures,
    feature_group,
    feature_names,
    vectorize,
)

MODEL_DIR = REPO / "ml" / "models" / "risk"


def _features(row: dict) -> RiskFeatures:
    return RiskFeatures(
        intent=row["intent"],
        confidence=float(row["confidence"]),
        target_type=row["target_type"],
        media=row["media"],
        realism=float(row["realism"]),
        manipulation=float(row["manipulation"]),
        sensitive_context=int(row["sensitive_context"]),
        synthetic_voice=int(row["synthetic_voice"]),
    )


def load_xy(scenarios: Path, labels: Path) -> tuple[np.ndarray, np.ndarray]:
    with scenarios.open(newline="", encoding="utf-8") as f:
        by_id = {r["scenario_id"]: r for r in csv.DictReader(f)}
    with labels.open(newline="", encoding="utf-8") as f:
        lab = list(csv.DictReader(f))
    X = np.array([vectorize(_features(by_id[r["scenario_id"]])) for r in lab])
    y = np.array([r["label"] for r in lab])
    return X, y


def candidates(seed: int = 0) -> dict:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression

    return {
        "logistic_regression": LogisticRegression(
            max_iter=3000, C=1.0, class_weight="balanced", random_state=seed
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced", random_state=seed
        ),
    }


def evaluate(X: np.ndarray, y: np.ndarray, seed: int = 0) -> dict:
    from sklearn.base import clone
    from sklearn.metrics import confusion_matrix, f1_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    n_splits = max(2, min(5, int(min(np.unique(y, return_counts=True)[1]))))
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    out = {}
    for name, model in candidates(seed).items():
        pred = cross_val_predict(clone(model), X, y, cv=cv)
        present = [lvl for lvl in LEVELS if lvl in set(y)]
        out[name] = {
            "cv_folds": n_splits,
            "macro_f1": float(f1_score(y, pred, labels=present, average="macro", zero_division=0)),
            "f1_per_level": dict(
                zip(
                    present,
                    map(float, f1_score(y, pred, labels=present, average=None, zero_division=0)),
                    strict=True,
                )
            ),
            "confusion": confusion_matrix(y, pred, labels=LEVELS).tolist(),
        }
    return out


def importance(name: str, model) -> list[tuple[str, float]]:
    names = feature_names()
    if name == "logistic_regression":
        vals = np.abs(model.coef_).mean(axis=0)
    else:
        vals = model.feature_importances_
    return sorted(zip(names, map(float, vals), strict=True), key=lambda kv: kv[1], reverse=True)


def plot_importance(items: list[tuple[str, float]], path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = items[:15][::-1]
    fig, ax = plt.subplots(figsize=(6, 5), dpi=120)
    ax.barh([k for k, _ in top], [v for _, v in top], color="#4FB8F5")
    ax.set_title(title, fontsize=9)
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def report_md(
    results: dict, chosen: str, kappa: dict, n: int, imp, png: str, synthetic: bool
) -> str:
    head = (
        "# Evaluasi Risk AI (SINTETIS, BUKAN HASIL)\n\nLabel berasal dari dua anotator SINTETIS (aturan + derau), "
        "hanya untuk memastikan pipeline berjalan. Angka di bawah TIDAK BOLEH dipakai di proposal atau "
        "RINGKASAN.md, dan model ini tidak pernah dimuat backend.\n"
        if synthetic
        else "# Evaluasi Risk AI\n\nLabel berasal dari dua anotator manusia yang bekerja terpisah "
        "(docs/risk-annotation-guide.md). Skenario yang tidak disepakati dibahas dulu sebelum dipakai.\n"
    )
    lines = [
        head,
        f"- Tanggal: {date.today().isoformat()}",
        f"- Skenario berlabel: {n}",
        f"- Kesepakatan anotator: {kappa['agreement_rate']:.1%}; Cohen's kappa {kappa['kappa']:.3f} "
        f"(berbobot kuadratik {kappa['kappa_quadratic']:.3f}); {kappa['disagreements']} tidak sepakat, "
        f"{kappa['resolved_by_discussion']} selesai lewat diskusi",
        "- Cara mereproduksi: `python ml/risk/kappa.py` lalu `python ml/risk/train.py"
        + (" --synthetic`" if synthetic else "`"),
        "",
        "| Model | Macro F1 (CV) | F1 LOW | F1 MEDIUM | F1 HIGH | F1 CRITICAL |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, r in results.items():
        f = r["f1_per_level"]
        lines.append(
            f"| {name}{' (dipilih)' if name == chosen else ''} | {r['macro_f1']:.3f} | "
            + " | ".join(f"{f.get(lvl, float('nan')):.3f}" for lvl in LEVELS)
            + " |"
        )
    lines += [
        "",
        f"Validasi silang berstrata {results[chosen]['cv_folds']} lipatan. Model terpilih lalu dilatih ulang dengan semua label.",
        "",
        "## Fitur paling berpengaruh (model terpilih)",
        "",
        "| Fitur | Bobot |",
        "| --- | --- |",
        *[f"| {k} | {v:.3f} |" for k, v in imp[:10]],
        "",
        f"![Importance]({png})",
        "",
        "Consent dan izin sengaja bukan fitur (CLAUDE.md bagian 8).",
    ]
    return "\n".join(lines) + "\n"


# --- Synthetic annotators ------------------------------------------------------------

_BASE = {
    "PERSONAL_CREATION": 10,
    "PERSONAL_EDITING": 5,
    "SATIRE_PARODY": 22,
    "COMMERCIAL_USE": 35,
    "POLITICAL_USE": 45,
    "IMPERSONATION": 75,
    "DEFAMATION": 80,
    "SEXUAL_EXPLICIT": 90,
    "DECEPTIVE": 78,
    "UNCERTAIN": 40,
}


def pseudo_label(row: dict, rng: random.Random, flip: float) -> str:
    s = _BASE[row["intent"]]
    s += {"SELF": -15, "NONE": -10, "OTHER_REGISTERED": 8, "OTHER_UNREGISTERED": 8, "UNCLEAR": 5}[
        row["target_type"]
    ]
    s += 12 * (float(row["realism"]) == HIGH) + 10 * (float(row["manipulation"]) == HIGH)
    s += 10 * int(row["sensitive_context"]) + 8 * int(row["synthetic_voice"])
    lvl = 0 if s < 30 else 1 if s < 60 else 2 if s < 85 else 3
    if rng.random() < flip:
        lvl = min(3, max(0, lvl + rng.choice((-1, 1))))
    return LEVELS[lvl]


def synthetic_setup() -> tuple[Path, Path, Path]:
    base = HERE / "synthetic"
    rows = build()
    write_csv(base / "data" / "scenarios.csv", FIELDS, rows)
    for who, flip, seed in (("anotator_A", 0.10, 1), ("anotator_B", 0.15, 2)):
        rng = random.Random(seed)
        write_csv(
            base / "annotations" / f"{who}.csv",
            ["scenario_id", "deskripsi", "label", "catatan"],
            [
                {
                    "scenario_id": r["scenario_id"],
                    "deskripsi": r["deskripsi"],
                    "label": pseudo_label(r, rng, flip),
                    "catatan": "SINTETIS",
                }
                for r in rows
            ],
        )
    run_kappa(base / "annotations", base / "data")
    return (
        base / "data" / "scenarios.csv",
        base / "data" / "labels.csv",
        base / "data" / "kappa.json",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args()

    import joblib

    if args.synthetic:
        scen, labels, kappa_path = synthetic_setup()
        model_dir, doc_dir, name = (
            MODEL_DIR / "synthetic",
            REPO / "docs" / "eval" / "synthetic",
            "risk-smoke",
        )
    else:
        scen, labels, kappa_path = (
            HERE / "data" / "scenarios.csv",
            HERE / "data" / "labels.csv",
            HERE / "data" / "kappa.json",
        )
        if not labels.exists():
            print(
                "Belum ada label. Isi lembar anotasi, jalankan kappa.py (lihat README.md).",
                file=sys.stderr,
            )
            return 2
        model_dir, doc_dir, name = MODEL_DIR, REPO / "docs" / "eval", "risk"

    X, y = load_xy(scen, labels)
    results = evaluate(X, y)
    chosen = max(results, key=lambda k: results[k]["macro_f1"])
    model = candidates()[chosen].fit(X, y)
    imp = importance(chosen, model)

    version = f"risk-{chosen.replace('_', '-')}-{date.today():%Y%m%d}" + (
        "-synthetic" if args.synthetic else ""
    )
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "risk_model.joblib")
    (model_dir / ("synthetic.json" if args.synthetic else "active.json")).write_text(
        json.dumps(
            {
                "kind": "sklearn",
                "file": "risk_model.joblib",
                "model_version": version,
                "algorithm": chosen,
                "synthetic": args.synthetic,
                "feature_names": feature_names(),
                "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "labels": len(y),
                "cv": {k: {"macro_f1": v["macro_f1"]} for k, v in results.items()},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    kappa = json.loads(kappa_path.read_text(encoding="utf-8"))
    png = doc_dir / f"{name}_importance.png"
    plot_importance(imp, png, f"Risk AI {chosen}" + (" (SINTETIS)" if args.synthetic else ""))
    (doc_dir / f"{name}.md").write_text(
        report_md(results, chosen, kappa, len(y), imp, png.name, args.synthetic), encoding="utf-8"
    )
    groups = sorted({feature_group(k) for k, _ in imp[:5]})
    print(f"{version}: macro F1 CV {results[chosen]['macro_f1']:.3f}; fitur utama {groups}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
