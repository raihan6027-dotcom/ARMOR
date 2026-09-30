"""End-to-end through POST /requests (the ARMOR gateway), fully offline.

Faces come from the synthetic camera; the client never names who is in the media.
Scenario numbers refer to CLAUDE.md Lampiran A (the full suite is Fase 11).
"""

import pytest

from app.db.database import SessionLocal
from app.models.request import Request
from app.models.request_target import RequestTarget
from tests.synthetic import face, image


@pytest.fixture()
def people(make_user, enroll):
    """A (raka) and B (sinta) are registered; C (citra) is not."""
    a_h, _ = make_user("raka@example.com")
    b_h, _ = make_user("sinta@example.com")
    a_id = enroll(a_h, "raka")
    b_id = enroll(b_h, "sinta")
    return {"A": a_h, "B": b_h, "A_id": a_id, "B_id": b_id}


def ask(client, headers, prompt, *faces, **extra):
    body = {"prompt": prompt, **extra}
    if faces:
        body["image"] = image(*faces)
    r = client.post("/requests", json=body, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_scenario_1_brighten_own_photo(client, people):
    r = ask(client, people["A"], "Cerahkan foto saya ini.", face("raka"))
    assert r["identity"]["target"] == "SELF"
    assert r["decision"]["action"] == "ALLOW"


def test_scenario_2_cartoon_avatar_of_self(client, people):
    r = ask(client, people["A"], "Buatkan avatar kartun dari wajah saya.", face("raka"))
    assert r["decision"]["action"] == "ALLOW"
    assert r["intent"]["label"] == "PERSONAL_CREATION"


def test_scenario_3_superhero_caricature_of_unregistered(client, people):
    r = ask(client, people["A"], "Buat karikatur superhero dari foto ini.", face("citra"))
    assert r["identity"]["target"] == "OTHER"
    assert r["decision"]["action"] == "ALLOW"
    assert r["decision"]["label_required"] is True


def test_scenario_6_prisoner_outfit_denied_with_suggestion(client, people):
    r = ask(client, people["A"], "Buat orang ini memakai baju tahanan dan diborgol.", face("citra"))
    assert r["decision"]["action"] == "DENY"
    assert r["decision"]["reason_code"] == "HARMFUL_DEFAMATION"
    assert "tahanan" in r["decision"]["reason"]
    assert r["decision"]["suggestion"] == "Buat karikatur superhero dari foto ini."


def test_scenario_8_light_edit_of_locked_face_denied(client, people):
    client.post("/identity/lock", json={"identity_id": people["B_id"]}, headers=people["B"])
    r = ask(client, people["A"], "Edit ringan, perbaiki pencahayaan foto ini.", face("sinta"))
    assert r["decision"]["action"] == "DENY"
    assert r["decision"]["reason_code"] == "NOT_PERMITTED"  # never "locked"


def test_scenario_9_disguised_face_is_reviewed(client, people):
    # Sunglasses / blur push the score into the gray zone -> UNCLEAR -> REVIEW.
    r = ask(
        client, people["A"], "Buat iklan produk kopi dengan wajah ini.", face("sinta", cos=0.40)
    )
    assert r["decision"]["action"] == "REVIEW"


def test_blurry_face_is_unclear(client, people):
    r = ask(client, people["A"], "Buat iklan produk kopi.", face("citra", blur=3))
    assert r["identity"]["people"][0]["quality_ok"] is False
    assert r["decision"]["action"] == "REVIEW"


def test_scenario_10_two_faces_strictest_wins(client, people):
    r = ask(
        client,
        people["A"],
        "Buat iklan produk kopi dengan foto ini.",
        face("raka"),
        face("sinta"),
    )
    assert r["decision"]["action"] == "REVIEW"
    assert sorted(p["target"] for p in r["identity"]["people"]) == ["OTHER", "SELF"]
    with SessionLocal() as db:
        rows = db.query(RequestTarget).filter_by(request_id=r["request_id"]).all()
        assert sorted(t.target_type for t in rows) == ["OTHER_REGISTERED", "SELF"]


def test_client_cannot_name_a_target(client, people):
    # The old identity_id field is gone; the only way in is the media itself.
    r = client.post(
        "/requests",
        json={"prompt": "Buat iklan", "identity_id": people["B_id"]},
        headers=people["A"],
    )
    assert r.status_code == 200
    assert r.json()["identity"]["target"] == "NONE"
    with SessionLocal() as db:
        assert db.query(RequestTarget).filter_by(request_id=r.json()["request_id"]).count() == 0


def test_no_face_in_image(client, people):
    r = ask(client, people["A"], "Buat ilustrasi pemandangan gunung.", image=image())
    assert r["identity"] == {"target": "NONE", "people": []}
    assert r["decision"]["action"] == "ALLOW"


def test_face_model_down_fails_safe(client, people, face_model_down):
    r = ask(client, people["A"], "Buatkan avatar kartun.", face("raka"))
    assert r["decision"]["action"] == "REVIEW"
    assert r["decision"]["reason_code"] == "CHECK_UNAVAILABLE"
    assert r["checks_unavailable"] == ["face"]


def test_registered_and_unregistered_look_the_same(client, people):
    prompt = "Buat iklan produk kopi dengan wajah orang ini."
    registered = ask(client, people["A"], prompt, face("sinta"))
    unregistered = ask(client, people["A"], prompt, face("citra"))
    for key in ("identity", "decision", "intent", "risk"):
        assert registered[key] == unregistered[key], key
    assert people["B_id"] not in str(registered)


def test_unregistered_embedding_is_not_stored(client, people):
    r = ask(client, people["A"], "Buat karikatur superhero dari foto ini.", face("citra"))
    with SessionLocal() as db:
        target = db.query(RequestTarget).filter_by(request_id=r["request_id"]).one()
        assert (target.target_type, target.identity_id, target.score) == (
            "OTHER_UNREGISTERED",
            None,
            None,
        )
        assert db.query(Request).filter_by(request_id=r["request_id"]).one().prompt


def test_history_records_requests(client, auth):
    headers, _ = auth
    ask(client, headers, "buat avatar kartun")
    ask(client, headers, "promosikan produk ini")
    body = client.get("/requests", headers=headers).json()
    assert body["total"] == 2
    assert body["items"][0]["decision"] in ("ALLOW", "REVIEW", "DENY")


def test_requests_require_auth(client):
    r = client.post("/requests", json={"prompt": "hi"})
    assert r.status_code == 401
