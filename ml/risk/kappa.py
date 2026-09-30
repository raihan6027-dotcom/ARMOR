"""Agreement between the two risk annotators, and the final label set.

    python ml/risk/kappa.py

Reads ml/risk/annotations/anotator_A.csv and anotator_B.csv (filled independently,
see docs/risk-annotation-guide.md) and writes:

* ml/risk/data/labels.csv        scenarios both annotators agree on (label = agreed level)
* ml/risk/data/disagreements.csv scenarios to discuss; fill `label_final` after the
                                 discussion and rerun, they are then added to labels.csv
* ml/risk/data/kappa.json        Cohen's kappa (unweighted and quadratic-weighted)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def cohen_kappa(a: list[str], b: list[str], weighted: bool = False) -> float:
    """Cohen's kappa; with weighted=True, quadratic weights for ordinal levels."""
    k = len(LEVELS)
    idx = {lvl: i for i, lvl in enumerate(LEVELS)}
    n = len(a)
    if n == 0:
        raise ValueError("no paired labels")
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        obs[idx[x]][idx[y]] += 1 / n
    pa = [sum(row) for row in obs]
    pb = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i, j):
        return ((i - j) ** 2) / ((k - 1) ** 2) if weighted else float(i != j)

    observed = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k))
    expected = sum(w(i, j) * pa[i] * pb[j] for i in range(k) for j in range(k))
    return 1.0 if expected == 0 else 1.0 - observed / expected


def _read(path: Path) -> dict[str, dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return {r["scenario_id"]: r for r in csv.DictReader(f)}


def merge(a: dict, b: dict, discussed: dict) -> tuple[list[dict], list[dict], list[str], list[str]]:
    agreed, disputed, la, lb = [], [], [], []
    for sid in sorted(set(a) & set(b)):
        x, y = a[sid]["label"].strip().upper(), b[sid]["label"].strip().upper()
        if not x or not y:
            continue
        for v in (x, y):
            if v not in LEVELS:
                raise SystemExit(f"{sid}: label tidak dikenal {v!r} (pakai {LEVELS})")
        la.append(x)
        lb.append(y)
        if x == y:
            agreed.append({"scenario_id": sid, "label": x, "source": "sepakat"})
        else:
            final = discussed.get(sid, {}).get("label_final", "").strip().upper()
            row = {"scenario_id": sid, "label_A": x, "label_B": y, "label_final": final}
            disputed.append(row)
            if final in LEVELS:
                agreed.append({"scenario_id": sid, "label": final, "source": "diskusi"})
    return agreed, disputed, la, lb


def main(annotation_dir: Path = HERE / "annotations", out_dir: Path = HERE / "data") -> int:
    pa, pb = annotation_dir / "anotator_A.csv", annotation_dir / "anotator_B.csv"
    if not (pa.exists() and pb.exists()):
        print("Lembar anotasi belum ada. Jalankan scenarios.py dulu.", file=sys.stderr)
        return 2
    disc_path = out_dir / "disagreements.csv"
    discussed = _read(disc_path) if disc_path.exists() else {}
    agreed, disputed, la, lb = merge(_read(pa), _read(pb), discussed)
    if not la:
        print("Belum ada skenario yang dilabeli kedua anotator.", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "labels.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "label", "source"])
        w.writeheader()
        w.writerows(agreed)
    with disc_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario_id", "label_A", "label_B", "label_final"])
        w.writeheader()
        w.writerows(disputed)
    result = {
        "paired": len(la),
        "agreement_rate": sum(x == y for x, y in zip(la, lb, strict=True)) / len(la),
        "kappa": cohen_kappa(la, lb),
        "kappa_quadratic": cohen_kappa(la, lb, weighted=True),
        "disagreements": len(disputed),
        "resolved_by_discussion": sum(1 for d in disputed if d["label_final"] in LEVELS),
        "annotation_dir": str(annotation_dir.name),
    }
    (out_dir / "kappa.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"{result['paired']} pasangan, kappa {result['kappa']:.3f} "
        f"(kuadratik {result['kappa_quadratic']:.3f}), {result['disagreements']} perlu dibahas"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
