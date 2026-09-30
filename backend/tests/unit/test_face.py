"""Face AI building blocks, tested without the model (synthetic data only)."""

import numpy as np
import pytest

from app.ai import face as face_module
from app.ai.face import (
    FaceAI,
    cosine,
    decode_to_bgr,
    l2_normalize,
    laplacian_variance,
    pose_from_landmarks,
    quality_issues,
)
from app.core.crypto import decrypt_embedding, encrypt_embedding
from app.core.exceptions import ArmorError
from app.services.identity_service import best_match, classify_face
from tests.synthetic import analyze, face, image, person_vec, vec_with_cosine

FRONTAL = np.array([[30, 40], [70, 40], [50, 62], [35, 80], [65, 80]], dtype=float)


def test_laplacian_variance_separates_sharp_from_flat():
    rng = np.random.default_rng(0)
    sharp = rng.integers(0, 255, size=(64, 64))
    flat = np.full((64, 64), 128)
    assert laplacian_variance(sharp) > 1000
    assert laplacian_variance(flat) == 0.0
    assert laplacian_variance(np.zeros((2, 2))) == 0.0  # too small to measure


def test_pose_frontal_is_near_zero():
    yaw, pitch = pose_from_landmarks(FRONTAL)
    assert abs(yaw) < 1
    assert abs(pitch) < 5


def test_pose_turned_head_has_yaw_sign():
    right = FRONTAL.copy()
    right[2, 0] += 12  # nose moves right
    left = FRONTAL.copy()
    left[2, 0] -= 12
    assert pose_from_landmarks(right)[0] > 20
    assert pose_from_landmarks(left)[0] < -20


def test_pose_degenerate_landmarks():
    assert pose_from_landmarks(np.zeros((5, 2))) == (0.0, 0.0)


@pytest.mark.parametrize(
    ("size", "blur", "yaw", "pitch", "expected"),
    [
        (160, 250, 0, 0, []),
        (20, 250, 0, 0, ["FACE_TOO_SMALL"]),
        (160, 1, 0, 0, ["FACE_BLURRY"]),
        (160, 250, 80, 0, ["FACE_TURNED_AWAY"]),
        (160, 250, 0, -60, ["FACE_TURNED_AWAY"]),
    ],
)
def test_quality_issues(size, blur, yaw, pitch, expected):
    assert quality_issues(size, blur, yaw, pitch) == expected


def test_cosine_and_normalize():
    assert cosine(person_vec("a"), person_vec("a")) == pytest.approx(1.0)
    assert abs(cosine(person_vec("a"), person_vec("b"))) < 0.2  # random 512-D vectors
    assert cosine(person_vec("a"), vec_with_cosine("a", 0.37)) == pytest.approx(0.37, abs=1e-5)
    assert np.all(l2_normalize(np.zeros(4)) == 0)


def test_decode_to_bgr_rejects_non_images():
    assert decode_to_bgr(b"not an image") is None


def test_decode_to_bgr_reads_png():
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (4, 3), (255, 0, 0)).save(buf, format="PNG")
    bgr = decode_to_bgr(buf.getvalue())
    assert bgr.shape == (3, 4, 3)
    assert tuple(bgr[0, 0]) == (0, 0, 255)  # red in BGR order


def test_face_ai_reports_unavailable_without_model(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "model_dir", str(tmp_path))
    monkeypatch.setattr(settings, "insightface_model", "definitely-not-a-model")
    ai = FaceAI()
    assert ai.analyze(b"anything") is None
    assert ai.available is False
    assert ai.loaded is False
    assert ai.init_error


def test_face_ai_parses_insightface_faces(monkeypatch):
    """The wrapper around FaceAnalysis.get: geometry, quality and sort order."""
    import io

    from PIL import Image

    class FakeFace:
        def __init__(self, box, vec):
            self.bbox = np.array(box, dtype=float)
            self.normed_embedding = vec
            self.det_score = 0.9
            self.kps = FRONTAL + np.array([box[0], box[1]])

    class FakeApp:
        def get(self, _bgr):
            return [
                FakeFace((0, 0, 40, 40), person_vec("small")),
                FakeFace((10, 10, 170, 170), person_vec("big")),
            ]

    rng = np.random.default_rng(1)
    buf = io.BytesIO()
    Image.fromarray(rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)).save(buf, format="PNG")
    ai = FaceAI()
    ai._tried, ai._app = True, FakeApp()
    faces = ai.analyze(buf.getvalue())
    assert [round(f.size_px) for f in faces] == [160, 40]  # largest first
    assert faces[0].quality_ok
    assert faces[1].issues == ["FACE_TOO_SMALL"]
    assert cosine(faces[0].embedding, person_vec("big")) == pytest.approx(1.0)
    assert ai.analyze(b"garbage") == []


def test_embedding_encryption_round_trip():
    vec = person_vec("raka")
    token = encrypt_embedding(vec)
    assert token.startswith("gAAAA")
    assert np.allclose(decrypt_embedding(token), vec)


def test_embedding_decrypt_with_wrong_key_fails(monkeypatch):
    from cryptography.fernet import Fernet

    from app.core.config import settings

    token = encrypt_embedding(person_vec("raka"))
    monkeypatch.setattr(settings, "armor_embedding_key", Fernet.generate_key().decode())
    with pytest.raises(ArmorError) as exc:
        decrypt_embedding(token)
    assert exc.value.code == "EMBEDDING_DECRYPT_FAILED"


def test_invalid_embedding_key(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "armor_embedding_key", "not-a-fernet-key")
    with pytest.raises(ArmorError) as exc:
        encrypt_embedding(person_vec("raka"))
    assert exc.value.code == "EMBEDDING_KEY_INVALID"


class _Ident:
    def __init__(self, identity_id, user_id, is_child=False):
        self.identity_id, self.user_id, self.is_child = identity_id, user_id, is_child


@pytest.mark.parametrize(
    ("spec", "requester", "expected"),
    [
        (face("raka"), "u-raka", "SELF"),
        (face("raka"), "u-dimas", "OTHER_REGISTERED"),
        (face("raka", cos=0.42), "u-dimas", "UNCLEAR"),  # inside threshold +/- margin
        (face("raka", cos=0.30), "u-dimas", "OTHER_UNREGISTERED"),
        (face("citra"), "u-dimas", "OTHER_UNREGISTERED"),
        (face("raka", blur=2), "u-raka", "UNCLEAR"),  # low quality is never matched
        (face("kid"), "u-raka", "OTHER_REGISTERED"),  # a guardian's child is not SELF
    ],
)
def test_classify_face(spec, requester, expected):
    index = [
        (_Ident("id-raka", "u-raka"), person_vec("raka")),
        (_Ident("id-kid", "u-raka", is_child=True), person_vec("kid")),
    ]
    detected = analyze(__import__("base64").b64decode(image(spec)))[0]
    assert classify_face(detected, requester, index).target.value == expected


def test_best_match_empty_index():
    assert best_match(person_vec("a"), []) == (None, -1.0)


def test_module_exposes_singleton():
    assert isinstance(face_module.face_ai, FaceAI)
