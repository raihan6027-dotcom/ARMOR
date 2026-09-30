"""CLAUDE.md Lampiran A, skenario 15 dan 16 (the full suite of 20 is Fase 11).

A (raka) and B (sinta) are registered; C (citra) is not. Faces come from the
synthetic camera; the generator is the real generator_mock app, in-process.
"""

import base64
import io
import json

import pytest
from PIL import Image

from app.db.database import SessionLocal
from app.generation import GeneratedImage, set_generator
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.request import Request
from tests.synthetic import face, image, image_bytes


@pytest.fixture()
def people(make_user, enroll):
    a_h, a_id = make_user("raka@example.com")
    b_h, b_id = make_user("sinta@example.com")
    enroll(a_h, "raka")
    enroll(b_h, "sinta")
    return {"A": a_h, "B": b_h, "A_user": a_id, "B_user": b_id}


class InjectingGenerator:
    """Stands in for generator_mock's test mode `inject_face` (which pastes a face
    photo into every output): with the synthetic camera, the injected face is
    encoded as B's face in the output image."""

    name = "mock"

    def __init__(self, *faces):
        self.faces = faces

    def available(self) -> bool:
        return True

    def generate(self, prompt, image):
        return GeneratedImage(
            png=image_bytes(*self.faces), generator="armor-generator-mock mock-1", simulated=True
        )


def ask(client, headers, prompt, img=None):
    body = {"prompt": prompt}
    if img:
        body["image"] = img
    r = client.post("/requests", json=body, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_scenario_15_safe_prompt_but_output_has_face_b_is_held(client, people):
    img = image(face("raka"))
    decision = ask(client, people["A"], "Cerahkan foto saya ini.", img)
    assert decision["decision"]["action"] == "ALLOW"

    set_generator(InjectingGenerator(face("raka"), face("sinta")))
    r = client.post(
        f"/requests/{decision['request_id']}/generate", json={"image": img}, headers=people["A"]
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "HELD"
    assert out["image"] is None and out["shield"] is None
    assert "Output Guard" in out["message"]
    assert "sinta" not in json.dumps(out)  # the requester is not told who

    with SessionLocal() as db:
        row = db.query(Request).filter_by(request_id=decision["request_id"]).one()
        assert row.output_status == "HELD"
        audit = db.query(AuditLog).filter_by(event="OUTPUT_HELD").one()
        assert "OUTPUT_REGISTERED_NOT_ALLOWED" in audit.data
        notes = db.query(Notification).filter_by(user_id=people["B_user"]).all()
        assert [n.kind for n in notes] == ["OUTPUT_GUARD"]
        # A is not notified about their own face.
        assert (
            db.query(Notification).filter_by(user_id=people["A_user"], kind="OUTPUT_GUARD").count()
            == 0
        )


def test_scenario_16_output_of_scenario_3_is_verified_publicly(client, people):
    img = image(face("citra"))
    decision = ask(client, people["A"], "Buat karikatur superhero dari foto ini.", img)
    assert decision["decision"]["action"] == "ALLOW"
    assert decision["decision"]["label_required"] is True

    out = client.post(
        f"/requests/{decision['request_id']}/generate", json={"image": img}, headers=people["A"]
    ).json()
    assert out["status"] == "DELIVERED"
    assert out["shield"]["label"] == "Dibuat dengan AI · ARMOR"
    assert out["generator"]["simulated"] is True

    # Public verification: no login.
    v = client.post("/shield/verify", json={"image": out["image"]})
    assert v.status_code == 200, v.text
    body = v.json()
    assert body["verified"] is True and body["method"] == "METADATA" and body["exact"] is True
    assert body["permission_status"] == "POLICY_ALLOWED"
    assert body["created_at"] == out["shield"]["created_at"]
    # Never the prompt, the requester, or who is in the image.
    text = json.dumps(body)
    assert "karikatur" not in text and "raka" not in text and decision["request_id"] not in text

    # Still verified after the metadata is stripped and after lossy re-compression.
    shielded = Image.open(io.BytesIO(base64.b64decode(out["image"])))
    stripped = io.BytesIO()
    shielded.save(stripped, format="PNG")
    v2 = client.post(
        "/shield/verify", json={"image": base64.b64encode(stripped.getvalue()).decode()}
    )
    assert v2.json()["verified"] is True and v2.json()["method"] == "HASH"

    jpeg = io.BytesIO()
    shielded.convert("RGB").resize((shielded.width * 3 // 4, shielded.height * 3 // 4)).save(
        jpeg, format="JPEG", quality=70
    )
    v3 = client.post("/shield/verify", json={"image": base64.b64encode(jpeg.getvalue()).decode()})
    assert v3.json()["verified"] is True and v3.json()["method"] == "PERCEPTUAL"
    assert v3.json()["exact"] is False
