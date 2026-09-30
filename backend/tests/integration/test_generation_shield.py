"""Fase 8: generator -> Output Guard -> ARMOR Shield, and public verification."""

import base64
import io
import json

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from app.core.config import settings
from app.db.database import SessionLocal
from app.generation import GeneratedImage, GeneratorUnavailable, set_generator
from app.generation import _build as build_generator
from app.generation.diffusers_adapter import DiffusersAdapter
from app.models.notification import Notification
from app.models.shield import ShieldRecord
from app.services import shield_service
from tests.synthetic import face, image, image_bytes

AD = "Buat iklan produk kopi dengan wajah orang ini."


@pytest.fixture()
def people(make_user, enroll):
    a_h, _ = make_user("raka@example.com")
    b_h, b_user = make_user("sinta@example.com")
    enroll(a_h, "raka")
    enroll(b_h, "sinta")
    return {"A": a_h, "B": b_h, "B_user": b_user}


class FixedGenerator:
    name = "mock"

    def __init__(self, png=None, error=None):
        self.png, self.error = png, error

    def available(self):
        return self.error is None

    def generate(self, prompt, image):
        if self.error:
            raise self.error
        return GeneratedImage(png=self.png, generator="test-generator", simulated=True)


def ask(client, headers, prompt, img=None):
    body = {"prompt": prompt, **({"image": img} if img else {})}
    return client.post("/requests", json=body, headers=headers).json()


def gen(client, headers, request_id, img=None):
    return client.post(
        f"/requests/{request_id}/generate", json={"image": img} if img else {}, headers=headers
    )


def decode(b64: str) -> Image.Image:
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    img.load()
    return img


def b64(img: Image.Image, fmt="PNG", **kw) -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **kw)
    return base64.b64encode(buf.getvalue()).decode()


# --- Generating after ALLOW -----------------------------------------------------------


def test_self_edit_is_delivered_with_shield(client, people):
    img = image(face("raka"))
    d = ask(client, people["A"], "Buatkan avatar kartun dari wajah saya.", img)
    r = gen(client, people["A"], d["request_id"], img)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "DELIVERED"
    assert set(out["timing_ms"]) == {"generate", "output_guard", "shield"}

    png = decode(out["image"])
    manifest = json.loads(png.text[shield_service.MANIFEST_KEY])
    assert manifest["decision_id"] == d["request_id"]
    assert manifest["permission_status"] == "POLICY_ALLOWED"
    assert manifest["assertions"][0]["data"]["actions"][0]["digitalSourceType"].endswith(
        "trainedAlgorithmicMedia"
    )
    assert shield_service._valid_signature(manifest)
    assert manifest["pixel_sha256"] == shield_service.pixel_sha256(png)
    with SessionLocal() as db:
        rec = db.query(ShieldRecord).one()
        assert rec.shield_id == out["shield"]["shield_id"] and rec.simulated is True
        assert len(rec.phash) == 16


def test_visible_label_changes_the_corner_pixels():
    base = Image.new("RGB", (400, 300), (250, 250, 250))
    labelled = shield_service.draw_label(base)
    corner = labelled.crop((200, 250, 400, 300))
    assert corner.getcolors(10000) and len(corner.getcolors(10000)) > 2
    assert labelled.crop((0, 0, 100, 100)).getcolors() == [(10000, (250, 250, 250))]


def test_text_only_request_generates_without_media(client, people):
    d = ask(client, people["A"], "Buat ilustrasi pemandangan gunung saat pagi.")
    assert d["decision"]["action"] == "ALLOW"
    assert gen(client, people["A"], d["request_id"]).json()["status"] == "DELIVERED"
    r = gen(client, people["A"], d["request_id"], image(face("raka")))
    assert r.status_code == 409 and r.json()["error"]["code"] == "MEDIA_MISMATCH"


def test_swapping_the_checked_image_is_refused(client, people):
    d = ask(client, people["A"], "Cerahkan foto saya ini.", image(face("raka")))
    for other in (image(face("sinta")), None):
        r = gen(client, people["A"], d["request_id"], other)
        assert r.status_code == 409 and r.json()["error"]["code"] == "MEDIA_MISMATCH"


def test_only_final_allow_can_be_generated(client, people):
    denied = ask(client, people["A"], "Buat orang ini memakai baju tahanan dan diborgol.", image(face("citra")))
    held = ask(client, people["A"], AD, image(face("sinta")))
    assert denied["decision"]["action"] == "DENY" and held["status"] == "HELD"
    for d, img in ((denied, image(face("citra"))), (held, image(face("sinta")))):
        r = gen(client, people["A"], d["request_id"], img)
        assert r.status_code == 409 and r.json()["error"]["code"] == "REQUEST_NOT_ALLOWED"


def test_someone_elses_request_is_not_found(client, people):
    img = image(face("raka"))
    d = ask(client, people["A"], "Cerahkan foto saya ini.", img)
    assert gen(client, people["B"], d["request_id"], img).status_code == 404


def test_generator_down_is_reported(client, people):
    img = image(face("raka"))
    d = ask(client, people["A"], "Cerahkan foto saya ini.", img)
    set_generator(FixedGenerator(error=GeneratorUnavailable("down")))
    r = gen(client, people["A"], d["request_id"], img)
    assert r.status_code == 503 and r.json()["error"]["code"] == "GENERATOR_UNAVAILABLE"
    set_generator(FixedGenerator(png=b"not an image"))
    assert gen(client, people["A"], d["request_id"], img).status_code == 503


def test_output_check_unavailable_holds_output(client, people, monkeypatch):
    img = image(face("raka"))
    d = ask(client, people["A"], "Cerahkan foto saya ini.", img)
    from app.ai.face import face_ai

    monkeypatch.setattr(face_ai, "analyze", lambda _b: None)
    assert gen(client, people["A"], d["request_id"], img).json()["status"] == "HELD"


def test_unclear_face_in_output_is_held_without_notifying_anyone(client, people):
    img = image(face("raka"))
    d = ask(client, people["A"], "Cerahkan foto saya ini.", img)
    set_generator(FixedGenerator(png=image_bytes(face("sinta", cos=0.40))))
    assert gen(client, people["A"], d["request_id"], img).json()["status"] == "HELD"
    with SessionLocal() as db:
        assert db.query(Notification).filter_by(kind="OUTPUT_GUARD").count() == 0


def test_unregistered_face_in_output_passes(client, people):
    img = image(face("raka"))
    d = ask(client, people["A"], "Cerahkan foto saya ini.", img)
    set_generator(FixedGenerator(png=image_bytes(face("raka"), face("citra"))))
    assert gen(client, people["A"], d["request_id"], img).json()["status"] == "DELIVERED"


def test_owner_who_consented_may_appear_in_output(client, people):
    img = image(face("sinta"))
    d = ask(client, people["A"], AD, img)
    client.post("/consent/request", json={"request_id": d["request_id"]}, headers=people["A"])
    cid = client.get("/consent/inbox?status=pending", headers=people["B"]).json()["items"][0]["consent_id"]
    client.post(f"/consent/{cid}/respond", json={"action": "APPROVE"}, headers=people["B"])
    assert client.get(f"/requests/{d['request_id']}", headers=people["A"]).json()["decision"]["action"] == "ALLOW"

    set_generator(FixedGenerator(png=image_bytes(face("sinta"))))
    out = gen(client, people["A"], d["request_id"], img).json()
    assert out["status"] == "DELIVERED"
    assert out["shield"]["permission_status"] == "OWNER_PERMITTED"


def test_data_export_lists_shield_records(client, people):
    img = image(face("raka"))
    d = ask(client, people["A"], "Cerahkan foto saya ini.", img)
    gen(client, people["A"], d["request_id"], img)
    data = client.get("/me/data", headers=people["A"]).json()
    assert len(data["shield_records"]) == 1
    assert data["requests"][0]["output_status"] == "DELIVERED"


# --- Public verification --------------------------------------------------------------


@pytest.fixture()
def delivered(client, people):
    img = image(face("raka"))
    d = ask(client, people["A"], "Cerahkan foto saya ini.", img)
    return gen(client, people["A"], d["request_id"], img).json()


def test_unrelated_image_is_not_verified(client, delivered):
    other = Image.new("RGB", (300, 300), (10, 200, 30))
    body = client.post("/shield/verify", json={"image": b64(other)}).json()
    assert body["verified"] is False and body["method"] == "NONE"
    assert "tidak membuktikan" in body["message"]


def test_forged_manifest_is_detected(client, delivered):
    png = decode(delivered["image"])
    manifest = json.loads(png.text[shield_service.MANIFEST_KEY])
    manifest["permission_status"] = "OWNER_PERMITTED"  # tampered, signature no longer matches

    info = PngInfo()
    info.add_itxt(shield_service.MANIFEST_KEY, json.dumps(manifest))
    same_pixels = client.post("/shield/verify", json={"image": b64(png, pnginfo=info)}).json()
    # The pixels are still ARMOR's, so the hash matches, but the metadata is flagged.
    assert same_pixels["verified"] is True and same_pixels["method"] == "HASH"
    assert same_pixels["metadata_found"] and not same_pixels["metadata_valid"]
    assert same_pixels["permission_status"] == "POLICY_ALLOWED"  # from the registry

    fake = Image.new("RGB", (300, 300), (200, 30, 30))
    body = client.post("/shield/verify", json={"image": b64(fake, pnginfo=info)}).json()
    assert body["verified"] is False and "dipalsukan" in body["message"]


def test_edited_pixels_with_valid_metadata_are_not_exact(client, delivered):
    png = decode(delivered["image"]).convert("RGB")
    png.putpixel((5, 5), (0, 0, 0))
    info = PngInfo()
    info.add_itxt(shield_service.MANIFEST_KEY, decode(delivered["image"]).text[shield_service.MANIFEST_KEY])
    body = client.post("/shield/verify", json={"image": b64(png, pnginfo=info)}).json()
    assert body["verified"] is True and body["method"] == "PERCEPTUAL" and body["exact"] is False


def test_verify_rejects_non_images_and_is_rate_limited(client, delivered, monkeypatch):
    bad = base64.b64encode(b"hello").decode()
    assert client.post("/shield/verify", json={"image": bad}).status_code == 415
    monkeypatch.setattr(settings, "public_verify_per_minute", 2)
    other = b64(Image.new("RGB", (64, 64)))
    codes = [client.post("/shield/verify", json={"image": other}).status_code for _ in range(3)]
    assert codes[-1] == 429


# --- Adapter selection ----------------------------------------------------------------


def test_generator_selection(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "generator_model_dir", str(tmp_path))
    monkeypatch.setattr(settings, "generator", "auto")
    assert build_generator().name == "mock"  # no weights, no GPU -> mock
    monkeypatch.setattr(settings, "generator", "diffusers")
    local = build_generator()
    assert local.name == "diffusers" and local.available() is False
    with pytest.raises(GeneratorUnavailable):
        local.generate("x", None)
    monkeypatch.setattr(settings, "generator", "gemini")
    with pytest.raises(ValueError):
        build_generator()


def test_diffusers_needs_model_index(tmp_path):
    assert DiffusersAdapter(str(tmp_path)).available() is False
