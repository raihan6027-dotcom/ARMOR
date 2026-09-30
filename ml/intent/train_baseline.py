"""Intent AI baseline: TF-IDF (word + character n-grams) + Logistic Regression.

    python ml/intent/train_baseline.py                     # final run: every row reviewed
    python ml/intent/train_baseline.py --allow-unreviewed  # EXPERIMENT on unreviewed data

Trains on the frozen train split, picks the UNCERTAIN confidence threshold on
val, reports on test and on the hand-written paraphrase set, and writes:

    ml/models/intent/intent_tfidf_lr.joblib   model (not committed)
    ml/models/intent/active.json              what the backend loads (committed)
    ml/models/intent/baseline_report.json     full metrics (committed)
    docs/eval/intent_confusion_baseline.png   confusion matrix on test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from common import (  # noqa: E402
    DATASET,
    LABELS,
    MODEL_DIR,
    PARAPHRASE,
    REPO,
    apply_threshold,
    check_reviewed,
    choose_threshold,
    plot_confusion,
    read_rows,
    save_report,
    scores,
)

MODEL_FILE = "intent_tfidf_lr.joblib"


def build_pipeline(seed: int = 0):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(ngram_range=(1, 2), lowercase=True, sublinear_tf=True, min_df=1),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(2, 5),
                    lowercase=True,
                    sublinear_tf=True,
                    min_df=2,
                ),
            ),
        ]
    )
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced", random_state=seed)
    return Pipeline([("features", features), ("clf", clf)])


def train(rows: list[dict], paraphrases: list[dict]) -> tuple[object, dict]:
    split = {s: [r for r in rows if r["split"] == s] for s in ("train", "val", "test")}
    model = build_pipeline()
    model.fit([r["prompt"] for r in split["train"]], [r["intent"] for r in split["train"]])
    classes = list(model.classes_)

    def predict(data, threshold):
        proba = model.predict_proba([r["prompt"] for r in data])
        return apply_threshold(proba, classes, threshold), proba

    val_proba = model.predict_proba([r["prompt"] for r in split["val"]])
    threshold, sweep = choose_threshold(val_proba, classes, [r["intent"] for r in split["val"]])
    test_pred, _ = predict(split["test"], threshold)
    para_pred, _ = predict(paraphrases, threshold)
    report = {
        "counts": {k: len(v) for k, v in split.items()} | {"paraphrase": len(paraphrases)},
        "threshold": threshold,
        "threshold_sweep_val": sweep,
        "val": scores(
            [r["intent"] for r in split["val"]], apply_threshold(val_proba, classes, threshold)
        ),
        "test": scores([r["intent"] for r in split["test"]], test_pred),
        "paraphrase": scores([r["intent"] for r in paraphrases], para_pred),
        "paraphrase_errors": [
            {"prompt": r["prompt"], "label": r["intent"], "pred": p}
            for r, p in zip(paraphrases, para_pred, strict=True)
            if r["intent"] != p
        ],
    }
    return model, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--allow-unreviewed", action="store_true")
    args = ap.parse_args()

    import joblib

    rows, paraphrases = read_rows(DATASET), read_rows(PARAPHRASE)
    unreviewed = check_reviewed(rows, args.allow_unreviewed)
    model, report = train(rows, paraphrases)

    data_hash = hashlib.sha256(DATASET.read_bytes()).hexdigest()[:8]
    version = f"intent-tfidf-lr-{date.today():%Y%m%d}-{data_hash}"
    experiment = unreviewed > 0
    report |= {
        "model_version": version,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "experiment_unreviewed_rows": unreviewed,
        "status": "EKSPERIMEN (dataset belum diperiksa)" if experiment else "final",
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_DIR / MODEL_FILE)
    (MODEL_DIR / "active.json").write_text(
        json.dumps(
            {
                "kind": "sklearn",
                "file": MODEL_FILE,
                "model_version": version,
                "threshold": report["threshold"],
                "labels": LABELS,
                "experiment": experiment,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    save_report("baseline", report)
    plot_confusion(
        report["test"]["confusion"],
        REPO / "docs" / "eval" / "intent_confusion_baseline.png",
        f"Intent TF-IDF + LR, set uji ({'EKSPERIMEN' if experiment else 'final'})",
    )
    t, p = report["test"], report["paraphrase"]
    print(
        f"{version}: ambang UNCERTAIN {report['threshold']:.2f} | "
        f"uji macro F1 {t['macro_f1']:.3f}, recall berbahaya {t['harmful_recall_mean']:.3f} | "
        f"parafrase macro F1 {p['macro_f1']:.3f}, recall berbahaya {p['harmful_recall_mean']:.3f}"
        + (" | EKSPERIMEN" if experiment else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
