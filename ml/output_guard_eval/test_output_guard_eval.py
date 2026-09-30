"""The evaluation counts with the backend's real judge(); faces come from a stub."""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

import guard_eval as evaluate  # noqa: E402

from app.ai.face import DetectedFace, l2_normalize  # noqa: E402
from app.services.output_guard import HELD_REGISTERED, judge  # noqa: E402


def vec(seed: int) -> np.ndarray:
    return l2_normalize(np.random.default_rng(seed).standard_normal(512))


def face(v: np.ndarray) -> DetectedFace:
    return DetectedFace(
        bbox=(0, 0, 200, 200),
        embedding=v.copy(),
        det_score=0.99,
        size_px=200,
        blur_var=500,
        yaw=0,
        pitch=0,
    )


def test_counts_forbidden_and_allowed_outputs():
    people = {"R01": vec(1), "R02": vec(2)}
    index = [
        (SimpleNamespace(identity_id=k, user_id=k, is_child=False), v) for k, v in people.items()
    ]

    # The stub "generator" returns the list of people in the output.
    def generate(prompt, base, inject):
        return [base] + ([inject] if inject else [])

    def analyze(output):
        return [face(people[p]) for p in output]

    trials = [
        ("R01", "R01", "R02"),
        ("R01", "R01", None),
        ("R02", "R02", "R01"),
        ("R02", "R02", None),
    ]
    forbidden, allowed = evaluate.run(trials, generate, analyze, judge, index)
    assert (forbidden.total, forbidden.held) == (2, 2)
    assert forbidden.reasons == {HELD_REGISTERED: 2}
    assert (allowed.total, allowed.held) == (2, 0)


def test_unavailable_face_ai_counts_as_held():
    forbidden, _ = evaluate.run([("R01", b"x", b"y")], lambda *a: b"", lambda _o: None, judge, [])
    assert forbidden.held == 1


def test_report_has_no_numbers_without_runs():
    text = evaluate.report(
        evaluate.Tally(),
        evaluate.Tally(),
        0,
        [],
        SimpleNamespace(face_match_threshold=0.4, face_gray_margin=0.05),
    )
    assert "| 0 | 0 | 0,0% |" in text
