"""Learning loop: retrain Intent AI (and Risk AI) with reviewed feedback, behind an
evaluation gate, with versioning and rollback (Fase 6b).

    python -m app.cli feedback export                 # from backend/: writes ml/feedback/feedback.csv
    # the team reviews the CSV and fills diperiksa_oleh
    python ml/retrain.py intent                       # retrain + gate + report
    python ml/retrain.py risk                         # same for Risk AI (needs human risk labels)
    python ml/retrain.py history --component intent
    python ml/retrain.py rollback --component intent --to <model_version>

Rules:
* Only feedback rows with diperiksa_oleh filled are used, never media.
* The frozen test set (intent: ml/intent/dataset/splits.json; risk: ml/risk/data/test_split.json)
  never receives feedback; feedback whose prompt equals a test prompt is dropped.
* Gate: the new model replaces the active one only if, on the frozen test set,
  macro F1 does not go down AND the recall of the harmful classes does not go down
  (intent: IMPERSONATION, DEFAMATION, SEXUAL_EXPLICIT, DECEPTIVE; risk: HIGH, CRITICAL).
* Every candidate, accepted or rejected, is recorded in <model dir>/versions.json and
  in docs/eval/retrain.md. Model files are kept, so any accepted version can be
  restored with `rollback`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE / "intent"))
sys.path.insert(0, str(HERE / "intent" / "dataset"))
sys.path.insert(0, str(HERE / "risk"))
sys.path.insert(0, str(REPO / "backend"))

FEEDBACK_CSV = HERE / "feedback" / "feedback.csv"
REPORT = REPO / "docs" / "eval" / "retrain.md"
EPS = 1e-9


# --- Gate -------------------------------------------------------------------------------


def gate(current: dict | None, candidate: dict) -> tuple[bool, list[str]]:
    """Both metric dicts need macro_f1 and harmful_recall_mean (frozen test set)."""
    if current is None:
        return True, ["belum ada model aktif untuk dibandingkan"]
    reasons, ok = [], True
    for key, label in (("macro_f1", "macro F1"), ("harmful_recall_mean", "recall kelas berbahaya")):
        if candidate[key] + EPS < current[key]:
            ok = False
            reasons.append(f"{label} turun: {current[key]:.3f} -> {candidate[key]:.3f}")
        else:
            reasons.append(f"{label} tidak turun: {current[key]:.3f} -> {candidate[key]:.3f}")
    return ok, reasons


# --- Version registry ---------------------------------------------------------------------


@dataclass
class Registry:
    model_dir: Path
    versions: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, model_dir: Path) -> Registry:
        path = model_dir / "versions.json"
        versions = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        return cls(model_dir, versions)

    def save(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        (self.model_dir / "versions.json").write_text(
            json.dumps(self.versions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def active(self) -> dict | None:
        path = self.model_dir / "active.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def activate(self, meta: dict) -> None:
        (self.model_dir / "active.json").write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8"
        )

    def rollback(self, version: str) -> dict:
        match = [v for v in self.versions if v["model_version"] == version and v["accepted"]]
        if not match:
            raise SystemExit(f"Versi {version} tidak ada atau tidak pernah lolos gerbang.")
        entry = match[-1]
        if not (self.model_dir / entry["active"]["file"]).exists():
            raise SystemExit(f"Berkas model {entry['active']['file']} sudah tidak ada.")
        self.activate(entry["active"])
        self.versions.append(
            {
                "model_version": version,
                "event": "rollback",
                "at": _stamp(),
                "accepted": True,
                "active": entry["active"],
            }
        )
        self.save()
        return entry["active"]


def _stamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --- Feedback ------------------------------------------------------------------------------


def read_feedback(path: Path) -> tuple[list[dict], int]:
    """Reviewed rows only; returns (rows, number of unreviewed rows skipped)."""
    if not path.exists():
        return [], 0
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    reviewed = [r for r in rows if r.get("diperiksa_oleh", "").strip()]
    return reviewed, len(rows) - len(reviewed)


# --- Intent -----------------------------------------------------------------------------------


def _intent_metrics(model, threshold: float, rows: list[dict]) -> dict:
    from common import apply_threshold, scores

    proba = model.predict_proba([r["prompt"] for r in rows])
    return scores(
        [r["intent"] for r in rows], apply_threshold(proba, list(model.classes_), threshold)
    )


def retrain_intent(
    dataset: Path,
    feedback: Path,
    model_dir: Path,
    paraphrase: Path | None = None,
    splits: Path | None = None,
    allow_unreviewed_base: bool = False,
) -> dict:
    import joblib
    from common import LABELS, check_reviewed, choose_threshold, read_rows
    from generate import split_hash
    from train_baseline import build_pipeline

    rows = read_rows(dataset)
    if splits is not None and splits.exists():
        frozen = json.loads(splits.read_text(encoding="utf-8"))["test_sha256"]
        if split_hash(rows) != frozen:
            raise SystemExit("Set uji beku berubah. Retrain dibatalkan.")
    unreviewed_base = check_reviewed(rows, allow_unreviewed_base)
    test = [r for r in rows if r["split"] == "test"]
    val = [r for r in rows if r["split"] == "val"]
    train = [r for r in rows if r["split"] == "train"]
    test_prompts = {r["prompt"].strip().lower() for r in test}

    fb_rows, fb_unreviewed = read_feedback(feedback)
    fb_used, fb_dropped = [], 0
    for r in fb_rows:
        if r["intent_final"] not in LABELS or r["prompt"].strip().lower() in test_prompts:
            fb_dropped += 1
            continue
        fb_used.append({"prompt": r["prompt"], "intent": r["intent_final"]})

    model = build_pipeline()
    model.fit([r["prompt"] for r in train + fb_used], [r["intent"] for r in train + fb_used])
    val_proba = model.predict_proba([r["prompt"] for r in val])
    threshold, _ = choose_threshold(val_proba, list(model.classes_), [r["intent"] for r in val])
    candidate = _intent_metrics(model, threshold, test)
    para_rows = read_rows(paraphrase) if paraphrase and paraphrase.exists() else []
    candidate_para = _intent_metrics(model, threshold, para_rows) if para_rows else None

    model_dir.mkdir(parents=True, exist_ok=True)
    reg = Registry.load(model_dir)
    active = reg.active()
    current = None
    if active and active.get("kind") == "sklearn" and (model_dir / active["file"]).exists():
        current = _intent_metrics(
            joblib.load(model_dir / active["file"]), active["threshold"], test
        )
    ok, reasons = gate(current, candidate)

    fb_hash = hashlib.sha256(json.dumps(fb_used, sort_keys=True).encode()).hexdigest()[:8]
    version = f"intent-tfidf-lr-{date.today():%Y%m%d}-fb{len(fb_used)}-{fb_hash}"
    file = f"{version}.joblib"
    meta = {
        "kind": "sklearn",
        "file": file,
        "model_version": version,
        "threshold": threshold,
        "labels": LABELS,
        "experiment": bool(unreviewed_base),
    }
    if ok:
        joblib.dump(model, model_dir / file)
        reg.activate(meta)
    entry = {
        "model_version": version,
        "event": "retrain",
        "at": _stamp(),
        "accepted": ok,
        "reasons": reasons,
        "feedback_used": len(fb_used),
        "feedback_unreviewed_skipped": fb_unreviewed,
        "feedback_dropped": fb_dropped,
        "previous": active["model_version"] if active else None,
        "test_current": _short(current),
        "test_candidate": _short(candidate),
        "paraphrase_candidate": _short(candidate_para),
        "active": meta if ok else (active or {}),
    }
    reg.versions.append(entry)
    reg.save()
    return entry


def _short(m: dict | None) -> dict | None:
    if m is None:
        return None
    return {k: m[k] for k in ("n", "macro_f1", "harmful_recall_mean") if k in m} | (
        {"harmful_leak_rate": m["harmful_leak_rate"]} if "harmful_leak_rate" in m else {}
    )


# --- Risk -------------------------------------------------------------------------------------

RISK_HARMFUL = ["HIGH", "CRITICAL"]


def _risk_metrics(model, X: np.ndarray, y: np.ndarray) -> dict:
    from sklearn.metrics import f1_score, recall_score

    pred = model.predict(X)
    levels = [lvl for lvl in ("LOW", "MEDIUM", "HIGH", "CRITICAL") if lvl in set(y)]
    harmful = [lvl for lvl in RISK_HARMFUL if lvl in set(y)]
    return {
        "n": len(y),
        "macro_f1": float(f1_score(y, pred, labels=levels, average="macro", zero_division=0)),
        "harmful_recall_mean": float(
            np.mean(recall_score(y, pred, labels=harmful, average=None, zero_division=0))
        )
        if harmful
        else 0.0,
    }


def retrain_risk(
    scenarios: Path, labels: Path, feedback: Path, model_dir: Path, test_split: Path
) -> dict:
    import joblib
    from train import _features, candidates, load_xy

    from app.ai.risk_features import RiskFeatures, feature_names, vectorize

    if not labels.exists():
        raise SystemExit(
            "Belum ada label risiko dari dua anotator (lihat docs/risk-annotation-guide.md)."
        )
    with labels.open(newline="", encoding="utf-8") as f:
        lab = list(csv.DictReader(f))
    # Freeze the risk test set the first time (20%, stratified, fixed seed).
    if not test_split.exists():
        from sklearn.model_selection import train_test_split

        ids = [r["scenario_id"] for r in lab]
        _, test_ids = train_test_split(
            ids, test_size=0.2, random_state=20260930, stratify=[r["label"] for r in lab]
        )
        test_split.write_text(json.dumps(sorted(test_ids), indent=1) + "\n", encoding="utf-8")
    test_ids = set(json.loads(test_split.read_text(encoding="utf-8")))
    X_all, y_all = load_xy(scenarios, labels)
    mask = np.array([r["scenario_id"] in test_ids for r in lab])
    X_train, y_train, X_test, y_test = X_all[~mask], y_all[~mask], X_all[mask], y_all[mask]

    fb_rows, fb_unreviewed = read_feedback(feedback)
    extra_X, extra_y = [], []
    for r in fb_rows:
        if r.get("risk_final") in ("LOW", "MEDIUM", "HIGH", "CRITICAL") and r.get("features"):
            feats = json.loads(r["features"])
            if set(feats) >= set(RiskFeatures.__dataclass_fields__):
                extra_X.append(vectorize(_features(feats)))
                extra_y.append(r["risk_final"])
    if extra_X:
        X_train = np.vstack([X_train, np.array(extra_X)])
        y_train = np.concatenate([y_train, np.array(extra_y)])

    model_dir.mkdir(parents=True, exist_ok=True)
    reg = Registry.load(model_dir)
    active = reg.active()
    algorithm = (active or {}).get("algorithm", "random_forest")
    model = candidates()[algorithm].fit(X_train, y_train)
    candidate = _risk_metrics(model, X_test, y_test)
    current = None
    if active and not active.get("synthetic", True) and (model_dir / active["file"]).exists():
        current = _risk_metrics(joblib.load(model_dir / active["file"]), X_test, y_test)
    ok, reasons = gate(current, candidate)
    version = f"risk-{algorithm.replace('_', '-')}-{date.today():%Y%m%d}-fb{len(extra_y)}"
    meta = {
        "kind": "sklearn",
        "file": f"{version}.joblib",
        "model_version": version,
        "algorithm": algorithm,
        "synthetic": False,
        "feature_names": feature_names(),
        "trained_at": _stamp(),
    }
    if ok:
        joblib.dump(model, model_dir / meta["file"])
        reg.activate(meta)
    entry = {
        "model_version": version,
        "event": "retrain",
        "at": _stamp(),
        "accepted": ok,
        "reasons": reasons,
        "feedback_used": len(extra_y),
        "feedback_unreviewed_skipped": fb_unreviewed,
        "previous": active["model_version"] if active else None,
        "test_current": current,
        "test_candidate": candidate,
        "active": meta if ok else (active or {}),
    }
    reg.versions.append(entry)
    reg.save()
    return entry


# --- Report --------------------------------------------------------------------------------------


def append_report(component: str, entry: dict, report: Path = REPORT) -> None:
    def fmt(m, key):
        return "-" if not m or key not in m else f"{m[key]:.3f}"

    if not report.exists():
        report.write_text(
            "# Loop pembelajaran: riwayat retrain\n\n"
            "Setiap baris adalah satu percobaan retrain dengan feedback yang sudah diperiksa. "
            "Model baru hanya dipakai jika macro F1 dan recall kelas berbahaya pada set uji beku "
            "tidak turun. Dibuat oleh `python ml/retrain.py`.\n\n"
            "| Waktu | Komponen | Versi kandidat | Feedback dipakai | Macro F1 (aktif -> kandidat) | "
            "Recall berbahaya (aktif -> kandidat) | Hasil |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n",
            encoding="utf-8",
        )
    cur, cand = entry.get("test_current"), entry.get("test_candidate")
    status = "DIPAKAI" if entry["accepted"] else "DITOLAK"
    with report.open("a", encoding="utf-8") as f:
        f.write(
            f"| {entry['at']} | {component} | `{entry['model_version']}` | {entry['feedback_used']} | "
            f"{fmt(cur, 'macro_f1')} -> {fmt(cand, 'macro_f1')} | "
            f"{fmt(cur, 'harmful_recall_mean')} -> {fmt(cand, 'harmful_recall_mean')} | {status} |\n"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("intent")
    pi.add_argument("--feedback", type=Path, default=FEEDBACK_CSV)
    pi.add_argument("--allow-unreviewed-base", action="store_true")
    pr = sub.add_parser("risk")
    pr.add_argument("--feedback", type=Path, default=FEEDBACK_CSV)
    ph = sub.add_parser("history")
    ph.add_argument("--component", choices=("intent", "risk"), required=True)
    pb = sub.add_parser("rollback")
    pb.add_argument("--component", choices=("intent", "risk"), required=True)
    pb.add_argument("--to", required=True)
    args = ap.parse_args(argv)

    models = {c: REPO / "ml" / "models" / c for c in ("intent", "risk")}
    if args.cmd == "intent":
        entry = retrain_intent(
            HERE / "intent" / "dataset" / "intent_dataset.csv",
            args.feedback,
            models["intent"],
            HERE / "intent" / "dataset" / "paraphrase.csv",
            HERE / "intent" / "dataset" / "splits.json",
            args.allow_unreviewed_base,
        )
        append_report("intent", entry)
    elif args.cmd == "risk":
        entry = retrain_risk(
            HERE / "risk" / "data" / "scenarios.csv",
            HERE / "risk" / "data" / "labels.csv",
            args.feedback,
            models["risk"],
            HERE / "risk" / "data" / "test_split.json",
        )
        append_report("risk", entry)
    elif args.cmd == "history":
        for v in Registry.load(models[args.component]).versions:
            print(
                f"{v['at']}  {v['event']:8}  {'OK ' if v['accepted'] else 'NO '}  {v['model_version']}"
            )
        return 0
    else:
        meta = Registry.load(models[args.component]).rollback(args.to)
        print(f"Model aktif {args.component}: {meta['model_version']}. Mulai ulang backend.")
        return 0
    print(
        f"{entry['model_version']}: {'DIPAKAI' if entry['accepted'] else 'DITOLAK'}; "
        + "; ".join(entry["reasons"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
