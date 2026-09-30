"""Verification metrics for Face AI (and Voice AI): pure numpy, no model needed.

Definitions used in docs/eval/face.md:

* genuine pair: two embeddings of the same person; impostor pair: different people.
* at threshold t, a pair is "accepted" when cosine(a, b) >= t.
* TAR(t) = accepted genuine / all genuine;  FAR(t) = accepted impostor / all impostor.
* FAR is measured from real impostor attempts. It is NOT 100% - TAR (the old
  notebook's mistake, CLAUDE.md bagian 12).
* EER: the point where FAR equals FRR (= 1 - TAR).
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np


def l2n(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    n[n == 0] = 1.0
    return x / n


def pair_scores(embeddings: np.ndarray, labels: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """All genuine and impostor cosine scores among the given embeddings."""
    e = l2n(embeddings)
    sim = e @ e.T
    genuine, impostor = [], []
    for i, j in combinations(range(len(labels)), 2):
        (genuine if labels[i] == labels[j] else impostor).append(sim[i, j])
    return np.asarray(genuine), np.asarray(impostor)


def enrollment_scores(
    enroll: dict[str, np.ndarray], probes: np.ndarray, probe_labels: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Scores of probe photos against each person's enrollment template (mean of
    their enrollment embeddings), the way the gateway actually matches."""
    names = sorted(enroll)
    templates = l2n(np.stack([l2n(enroll[n]).mean(axis=0) for n in names]))
    sim = l2n(probes) @ templates.T
    genuine, impostor = [], []
    for row, label in zip(sim, probe_labels, strict=True):
        for col, name in enumerate(names):
            (genuine if name == label else impostor).append(row[col])
    return np.asarray(genuine), np.asarray(impostor)


@dataclass
class RocCurve:
    thresholds: np.ndarray  # descending
    tar: np.ndarray
    far: np.ndarray


def roc(genuine: np.ndarray, impostor: np.ndarray) -> RocCurve:
    if len(genuine) == 0 or len(impostor) == 0:
        raise ValueError("need at least one genuine and one impostor score")
    thresholds = np.unique(np.concatenate([genuine, impostor, [1.0 + 1e-9, -1.0 - 1e-9]]))[::-1]
    tar = np.array([(genuine >= t).mean() for t in thresholds])
    far = np.array([(impostor >= t).mean() for t in thresholds])
    return RocCurve(thresholds, tar, far)


def threshold_at_far(curve: RocCurve, target_far: float) -> float:
    """Lowest threshold whose FAR does not exceed target_far."""
    ok = curve.far <= target_far
    return float(curve.thresholds[ok][-1]) if ok.any() else float(curve.thresholds[0])


def tar_at_far(curve: RocCurve, target_far: float) -> tuple[float, float]:
    """(TAR, threshold) at the operating point FAR <= target_far."""
    t = threshold_at_far(curve, target_far)
    idx = int(np.where(curve.thresholds == t)[0][0])
    return float(curve.tar[idx]), t


def eer(curve: RocCurve) -> tuple[float, float]:
    """(EER, threshold) where FAR and FRR cross (nearest grid point)."""
    frr = 1.0 - curve.tar
    idx = int(np.argmin(np.abs(curve.far - frr)))
    return float((curve.far[idx] + frr[idx]) / 2.0), float(curve.thresholds[idx])


@dataclass
class Recommendation:
    threshold: float
    gray_margin: float
    rationale: str


def recommend(
    curve: RocCurve, strict_far: float = 0.001, loose_far: float = 0.01
) -> Recommendation:
    """Threshold at FAR <= 0.1% (a stranger is almost never taken for a registered
    person); gray margin = half the gap to the FAR <= 1% threshold, floored at 0.02,
    so borderline scores go to REVIEW instead of a silent decision."""
    t_strict = threshold_at_far(curve, strict_far)
    t_loose = threshold_at_far(curve, loose_far)
    margin = max(0.02, abs(t_strict - t_loose) / 2.0)
    return Recommendation(
        threshold=round(t_strict, 3),
        gray_margin=round(margin, 3),
        rationale=(
            f"threshold at FAR<={strict_far:.1%} = {t_strict:.3f}; "
            f"at FAR<={loose_far:.0%} = {t_loose:.3f}; margin = max(0.02, gap/2)"
        ),
    )
