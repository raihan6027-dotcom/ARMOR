"""Tests for the evaluation math (synthetic numbers only, no volunteer data)."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metrics import (  # noqa: E402
    eer,
    enrollment_scores,
    pair_scores,
    recommend,
    roc,
    tar_at_far,
    threshold_at_far,
)


def test_pair_scores_split_genuine_and_impostor():
    e = np.array([[1, 0], [1, 0.01], [0, 1]], dtype=float)
    g, i = pair_scores(e, ["a", "a", "b"])
    assert len(g) == 1 and g[0] == pytest.approx(1.0, abs=1e-3)
    assert len(i) == 2 and np.all(i < 0.1)


def test_perfect_separation():
    genuine = np.array([0.9, 0.8, 0.85])
    impostor = np.array([0.1, 0.2, 0.05, 0.15])
    curve = roc(genuine, impostor)
    tar, thr = tar_at_far(curve, 0.0)
    assert tar == 1.0 and 0.2 < thr <= 0.8
    e, _ = eer(curve)
    assert e == 0.0


def test_far_is_measured_not_derived_from_tar():
    # Half the impostors score high: FAR at the TAR=100% point is 0.5, not 1 - TAR.
    genuine = np.array([0.9, 0.9])
    impostor = np.array([0.95, 0.1])
    curve = roc(genuine, impostor)
    idx = np.where(curve.thresholds <= 0.9)[0][0]
    assert curve.tar[idx] == 1.0
    assert curve.far[idx] == 0.5


def test_threshold_at_far_is_conservative():
    genuine = np.linspace(0.5, 1.0, 100)
    impostor = np.linspace(0.0, 0.6, 1000)
    curve = roc(genuine, impostor)
    t = threshold_at_far(curve, 0.01)
    assert (impostor >= t).mean() <= 0.01


def test_eer_symmetric_case():
    genuine = np.array([0.6, 0.7, 0.8, 0.9])
    impostor = np.array([0.1, 0.2, 0.3, 0.65])
    e, _ = eer(roc(genuine, impostor))
    assert e == pytest.approx(0.25)


def test_enrollment_scores_uses_templates():
    rng = np.random.default_rng(0)
    a, b = rng.standard_normal(8), rng.standard_normal(8)
    enroll = {"A": np.stack([a, a]), "B": np.stack([b, b])}
    g, i = enrollment_scores(enroll, np.stack([a, b]), ["A", "B"])
    assert np.allclose(g, 1.0)
    assert len(i) == 2


def test_recommendation_has_floor_margin():
    genuine = np.array([0.9, 0.95])
    impostor = np.array([0.1, 0.2])
    rec = recommend(roc(genuine, impostor))
    assert rec.gray_margin >= 0.02
    assert 0.2 < rec.threshold <= 0.9


def test_roc_needs_both_classes():
    with pytest.raises(ValueError):
        roc(np.array([]), np.array([0.1]))
