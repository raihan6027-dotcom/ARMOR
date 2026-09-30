"""Optional: runs the real InsightFace pipeline if the model is installed locally.

Skipped automatically in CI and on machines without insightface and the
buffalo_l pack under MODEL_DIR (see ml/models/README.md for the download step).
"""

import io
import os
from pathlib import Path

import numpy as np
import pytest

from app.core.config import REPO_ROOT

MODEL_ROOT = Path(os.environ.get("ARMOR_REAL_MODEL_DIR", REPO_ROOT / "ml" / "models"))

insightface = pytest.importorskip("insightface", reason="insightface not installed")

pytestmark = pytest.mark.model


@pytest.mark.skipif(
    not (MODEL_ROOT / "models" / "buffalo_l").exists(),
    reason="buffalo_l model pack not downloaded to ml/models/models/buffalo_l",
)
def test_real_model_loads_and_finds_no_face_in_noise(monkeypatch):
    from PIL import Image

    from app.ai.face import FaceAI
    from app.core.config import settings

    monkeypatch.setattr(settings, "model_dir", str(MODEL_ROOT))
    ai = FaceAI()
    assert ai.available, ai.init_error
    rng = np.random.default_rng(0)
    buf = io.BytesIO()
    Image.fromarray(rng.integers(0, 255, (320, 320, 3), dtype=np.uint8)).save(buf, format="PNG")
    faces = ai.analyze(buf.getvalue())
    assert faces == []
