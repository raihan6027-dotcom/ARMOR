"""Fase 6 integration: trusted circle, appeals, disputes, audit chain, dashboard,
notifications, uploads, Media Router, CLI, and rate limits."""

import base64
import json

import pytest

from app import cli
from app.core.config import settings
from app.core.ratelimit import limiter
from app.db.database import SessionLocal
from app.models.audit import AuditLog
from app.models.identity import Identity
from app.models.user import User
from app.services import notify_service
from tests.synthetic import enroll_images, face, image

AD = "Buat iklan produk kopi dengan wajah orang ini."
CONSENT = {"agreed": True, "text_version": "face-v1"}


@pytest.fixture()
def people(make_user, enroll):
    raka_h, raka_uid = make_user("raka@example.com")
    sinta_h, sinta_uid = make_user("sinta@example.com")
    dimas_h, dimas_uid = make_user("dimas@example.com")
    raka_id = enroll(raka_h, "raka")
    return {
        "raka": raka_h,
        "raka_id": raka_id,
        "raka_uid": raka_uid,
        "sinta": sinta_h,
        "sinta_uid": sinta_uid,
        "dimas": dimas_h,
        "dimas_uid": dimas_uid,
    }


def _ask(client, headers, prompt=AD, who="raka"):
    return client.post(
        "/requests", json={"prompt": prompt, "image": image(face(who))}, headers=headers
    ).json()


def _make_reviewer(email):
    with SessionLocal() as db:
        cli.role_grant(db, email, "REVIEWER")


# --- Trusted circle -------------------------------------------------------------------


def test_trusted_circle_member_is_allowed_within_scope(client, people):
    r = client.post(
        "/circle",
        json={
            "identity_id": people["raka_id"],
            "email": "sinta@example.com",
            "intents": ["COMMERCIAL_USE"],
            "media": "FACE",
        },
        headers=people["raka"],
    )
    assert r.status_code == 201
    assert _ask(client, people["sinta"])["decision"]["action"] == "ALLOW"
    assert _ask(client, people["dimas"])["decision"]["action"] == "REVIEW"  # not a member
    # Outside the scope: political use still needs consent.
    assert (
        _ask(client, people["sinta"], "Buat poster kampanye pemilu orang ini.")["decision"][
            "action"
        ]
        == "REVIEW"
    )
    items = client.get(f"/circle?identity_id={people['raka_id']}", headers=people["raka"]).json()[
        "items"
    ]
    assert items[0]["email"] == "sinta@example.com" and items[0]["active"]
    client.delete(f"/circle/{items[0]['member_ref']}", headers=people["raka"])
    assert _ask(client, people["sinta"])["decision"]["action"] == "REVIEW"


def test_trusted_circle_never_overrides_harmful_rules_or_lock(client, people):
    client.post(
        "/circle",
        json={"identity_id": people["raka_id"], "email": "sinta@example.com"},
        headers=people["raka"],
    )
    harmful = _ask(client, people["sinta"], "Buat orang ini memakai baju tahanan dan diborgol.")
    assert harmful["decision"]["action"] == "DENY"
    client.post("/identity/lock", json={"identity_id": people["raka_id"]}, headers=people["raka"])
    assert _ask(client, people["sinta"])["decision"]["action"] == "DENY"


def test_trusted_circle_validation(client, people):
    base = {"identity_id": people["raka_id"]}
    r = client.post("/circle", json={**base, "email": "nobody@example.com"}, headers=people["raka"])
    assert r.status_code == 404
    r = client.post("/circle", json={**base, "email": "raka@example.com"}, headers=people["raka"])
    assert r.json()["error"]["code"] == "CIRCLE_SELF"
    r = client.post(
        "/circle",
        json={**base, "email": "sinta@example.com", "intents": ["DEFAMATION"]},
        headers=people["raka"],
    )
    assert r.json()["error"]["code"] == "INTENT_LOCKED"
    r = client.post("/circle", json={**base, "email": "sinta@example.com"}, headers=people["dimas"])
    assert r.status_code == 403


def test_expired_circle_membership(client, people):
    client.post(
        "/circle",
        json={
            "identity_id": people["raka_id"],
            "email": "sinta@example.com",
            "expires_at": "2020-01-01T00:00:00",
        },
        headers=people["raka"],
    )
    assert _ask(client, people["sinta"])["decision"]["action"] == "REVIEW"


# --- Appeals ---------------------------------------------------------------------------


def test_appeal_relabel_lets_the_policy_decide_again(client, people):
    _make_reviewer("sinta@example.com")
    denied = _ask(
        client, people["dimas"], "Buat orang ini memakai baju tahanan untuk film.", who="citra"
    )
    assert denied["decision"]["action"] == "DENY"
    r = client.post(
        "/cases",
        json={"request_id": denied["request_id"], "note": "Ini kostum untuk film pendek sekolah."},
        headers=people["dimas"],
    )
    assert r.status_code == 201
    case_id = r.json()["case_id"]
    assert r.json()["timeline"][0]["label"] == "Diajukan"

    # Reviewer console: only assigned cases, no media, target types and scores.
    listed = client.get("/cases", headers=people["sinta"]).json()["items"]
    assert [c["case_id"] for c in listed] == [case_id]
    detail = client.get(f"/cases/{case_id}", headers=people["sinta"]).json()
    assert detail["request"]["reason_code"] == "HARMFUL_DEFAMATION"
    assert detail["request"]["targets"][0]["target_type"] == "OTHER_UNREGISTERED"
    assert any(a["event"] == "DECISION" for a in detail["audit"])

    client.post(f"/cases/{case_id}/review", headers=people["sinta"])
    r = client.post(
        f"/cases/{case_id}/resolve",
        json={
            "outcome": "RELABEL",
            "corrected_intent": "PERSONAL_CREATION",
            "corrected_risk": "LOW",
            "note": "Kostum film, bukan tuduhan.",
        },
        headers=people["sinta"],
    )
    assert r.status_code == 200
    after = client.get(f"/requests/{denied['request_id']}", headers=people["dimas"]).json()
    assert after["decision"]["action"] == "ALLOW"  # decided by the policy, not by the reviewer
    mine = client.get(f"/cases/{case_id}", headers=people["dimas"]).json()
    assert [e["label"] for e in mine["timeline"]] == ["Diajukan", "Ditinjau", "Selesai"]
    assert "request" not in mine  # reporter view
    kinds = {
        n["kind"] for n in client.get("/notifications", headers=people["dimas"]).json()["items"]
    }
    assert {"CASE_STATUS", "REQUEST_UPDATED"} <= kinds


def test_appeal_uphold_and_rules(client, people):
    _make_reviewer("sinta@example.com")
    denied = _ask(client, people["dimas"], "Buat orang ini memakai baju tahanan.", who="citra")
    case_id = client.post(
        "/cases",
        json={"request_id": denied["request_id"], "note": "tolong ditinjau"},
        headers=people["dimas"],
    ).json()["case_id"]
    again = client.post(
        "/cases", json={"request_id": denied["request_id"], "note": "lagi"}, headers=people["dimas"]
    )
    assert again.json()["error"]["code"] == "APPEAL_EXISTS"
    r = client.post(
        f"/cases/{case_id}/resolve", json={"outcome": "RELABEL"}, headers=people["sinta"]
    )
    assert r.json()["error"]["code"] == "RELABEL_NEEDS_LABEL"
    r = client.post(
        f"/cases/{case_id}/resolve", json={"outcome": "UPHOLD"}, headers=people["sinta"]
    )
    assert r.json()["status"] == "RESOLVED"
    assert (
        client.get(f"/requests/{denied['request_id']}", headers=people["dimas"]).json()["decision"][
            "action"
        ]
        == "DENY"
    )
    # Only DENY can be appealed; only assigned reviewers act.
    allowed = _ask(client, people["dimas"], "buat avatar kartun saya", who="dimas")
    r = client.post(
        "/cases",
        json={"request_id": allowed["request_id"], "note": "x x x"},
        headers=people["dimas"],
    )
    assert r.json()["error"]["code"] == "APPEAL_NOT_APPLICABLE"
    assert client.post(f"/cases/{case_id}/review", headers=people["dimas"]).status_code == 403


# --- Disputes --------------------------------------------------------------------------


def _impostor_setup(client, make_user, enroll):
    """An impostor enrolled the face of `victim` first; the victim disputes."""
    impostor_h, _ = make_user("impostor@example.com")
    identity_id = enroll(impostor_h, "victim")
    victim_h, victim_uid = make_user("victim@example.com")
    return impostor_h, victim_h, victim_uid, identity_id


def _dispute(client, headers, who="victim"):
    return client.post(
        "/cases/dispute",
        json={"images": enroll_images(who), "consent": CONSENT, "note": "Ini wajah saya."},
        headers=headers,
    )


def test_dispute_freeze_and_transfer(client, make_user, enroll):
    reviewer_h, _ = make_user("reviewer@example.com")
    _make_reviewer("reviewer@example.com")
    impostor_h, victim_h, victim_uid, identity_id = _impostor_setup(client, make_user, enroll)
    r = _dispute(client, victim_h)
    assert r.status_code == 201
    case_id = r.json()["case_id"]
    assert "identity_id" not in json.dumps(r.json())

    client.post(f"/cases/{case_id}/freeze", headers=reviewer_h)
    r = client.post("/identity/lock", json={"identity_id": identity_id}, headers=impostor_h)
    assert r.status_code == 423  # owner controls paused
    # Protection still works while frozen.
    detail = client.get(f"/cases/{case_id}", headers=reviewer_h).json()
    assert detail["dispute"]["identity_frozen"] is True
    assert detail["dispute"]["verification_score"] > 0.9

    r = client.post(f"/cases/{case_id}/resolve", json={"outcome": "TRANSFER"}, headers=reviewer_h)
    assert r.status_code == 200
    with SessionLocal() as db:
        ident = db.query(Identity).filter_by(identity_id=identity_id).one()
        assert (ident.user_id, ident.frozen) == (victim_uid, False)
    assert client.get("/identity/profile", headers=victim_h).json()["identity_id"] == identity_id
    assert client.get("/identity/profile", headers=impostor_h).status_code == 404
    events = {
        a["event"] for a in client.get(f"/cases/{case_id}", headers=reviewer_h).json()["audit"]
    }
    assert {"CASE_OPENED", "IDENTITY_FROZEN", "CASE_RESOLVED"} <= events


def test_dispute_delete_enrollment_lets_the_real_owner_enroll(client, make_user, enroll):
    reviewer_h, _ = make_user("reviewer@example.com")
    _make_reviewer("reviewer@example.com")
    _, victim_h, _, _ = _impostor_setup(client, make_user, enroll)
    # Enrolling first is refused and opens a dispute automatically.
    r = client.post(
        "/identity/enroll",
        json={"images": enroll_images("victim"), "consent": CONSENT},
        headers=victim_h,
    )
    assert r.status_code == 409
    case_id = r.json()["error"]["details"]["case_id"]
    assert client.get("/cases", headers=reviewer_h).json()["items"][0]["case_id"] == case_id
    client.post(
        f"/cases/{case_id}/resolve", json={"outcome": "DELETE_ENROLLMENT"}, headers=reviewer_h
    )
    r = client.post(
        "/identity/enroll",
        json={"images": enroll_images("victim"), "consent": CONSENT},
        headers=victim_h,
    )
    assert r.status_code == 201


def test_dispute_without_a_matching_enrollment(client, make_user):
    h, _ = make_user("nobody@example.com")
    r = _dispute(client, h, who="stranger")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "NO_MATCHING_ENROLLMENT"


def test_dispute_reject_unfreezes(client, make_user, enroll):
    reviewer_h, _ = make_user("reviewer@example.com")
    _make_reviewer("reviewer@example.com")
    _, victim_h, _, identity_id = _impostor_setup(client, make_user, enroll)
    case_id = _dispute(client, victim_h).json()["case_id"]
    client.post(f"/cases/{case_id}/freeze", headers=reviewer_h)
    client.post(f"/cases/{case_id}/resolve", json={"outcome": "REJECT"}, headers=reviewer_h)
    with SessionLocal() as db:
        assert db.query(Identity).filter_by(identity_id=identity_id).one().frozen is False


# --- Audit chain ------------------------------------------------------------------------


def test_audit_chain_verifies_and_detects_tampering(client, people, make_user):
    _ask(client, people["dimas"])
    admin_h, _ = make_user("admin@example.com")
    with SessionLocal() as db:
        cli.role_grant(db, "admin@example.com", "ADMIN")
    ok = client.get("/audit/verify", headers=admin_h).json()
    assert ok["ok"] and ok["count"] >= 3
    assert client.get("/audit/verify", headers=people["dimas"]).status_code == 403
    with SessionLocal() as db:
        row = db.query(AuditLog).filter_by(event="DECISION").first()
        row.data = row.data.replace("REVIEW", "ALLOW")
        db.commit()
        broken_at = row.seq
    bad = client.get("/audit/verify", headers=admin_h).json()
    assert bad == {**bad, "ok": False, "broken_at": broken_at}


def test_audit_never_contains_prompt_or_embeddings(client, people):
    _ask(client, people["dimas"], "Rahasia: buat iklan kopi ini")
    with SessionLocal() as db:
        blob = " ".join(r.data for r in db.query(AuditLog).all())
    assert "Rahasia" not in blob and "gAAAA" not in blob


# --- Dashboard and notifications ------------------------------------------------------------


def test_dashboard_counts_and_sender_privacy(client, people):
    client.post(
        "/identity/lock",
        json={"identity_id": people["raka_id"], "level": "COMMERCIAL_POLITICAL"},
        headers=people["raka"],
    )
    _ask(client, people["dimas"])  # DENY (locked for ads)
    held = _ask(client, people["sinta"], "Buat parodi karikatur orang ini.")  # REVIEW
    client.post(
        "/consent/request", json={"request_id": held["request_id"]}, headers=people["sinta"]
    )
    _ask(client, people["raka"], "buat avatar kartun saya")  # SELF: not an attempt
    d = client.get("/dashboard/activity", headers=people["raka"]).json()
    assert d["this_week"] == {**d["this_week"], "attempts": 2, "blocked": 1, "pending": 1}
    senders = {e["decision"]: e["sender"] for e in d["recent"]}
    assert senders["DENY"] == "Pengirim tidak diketahui"
    assert senders["REVIEW"] == "sinta@example.com"
    blocked = client.get("/notifications?unread=true", headers=people["raka"]).json()
    assert any(n["kind"] == "USE_BLOCKED" for n in blocked["items"])
    marked = client.post("/notifications/read", json={}, headers=people["raka"]).json()["marked"]
    assert marked == blocked["unread"]
    assert client.get("/notifications", headers=people["raka"]).json()["unread"] == 0


def test_email_is_sent_only_when_enabled_and_opted_in(client, people, monkeypatch):
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda to, s, b: sent.append(to) or True)
    held = _ask(client, people["dimas"])
    client.post(
        "/consent/request", json={"request_id": held["request_id"]}, headers=people["dimas"]
    )
    assert sent == []  # EMAIL_ENABLED is off by default
    monkeypatch.setattr(settings, "email_enabled", True)
    client.patch("/auth/me", json={"email_notifications": True}, headers=people["raka"])
    held = _ask(client, people["dimas"], "Buat poster kampanye pemilu orang ini.")
    client.post(
        "/consent/request", json={"request_id": held["request_id"]}, headers=people["dimas"]
    )
    assert sent == ["raka@example.com"]


def test_account_settings(client, people):
    r = client.patch(
        "/auth/me",
        json={"display_name": "Raka Pratama", "email_notifications": True},
        headers=people["raka"],
    )
    assert (r.json()["display_name"], r.json()["email_notifications"], r.json()["role"]) == (
        "Raka Pratama",
        True,
        "USER",
    )


# --- Uploads and Media Router ------------------------------------------------------------------


def test_upload_type_is_checked_from_content(client, people):
    fake_png = base64.b64encode(b"MZ\x90\x00 not really an image").decode()
    r = client.post(
        "/requests", json={"prompt": "edit", "image": fake_png}, headers=people["dimas"]
    )
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    # A PNG sent as audio is refused too.
    r = client.post(
        "/requests", json={"prompt": "narasi", "audio": image(face("x"))}, headers=people["dimas"]
    )
    assert r.status_code == 415


def test_upload_size_limit(client, people, monkeypatch):
    monkeypatch.setattr(settings, "max_image_mb", 0.0001)
    r = client.post(
        "/requests", json={"prompt": "edit", "image": image(face("x"))}, headers=people["dimas"]
    )
    assert r.status_code == 413


def test_one_media_only(client, people):
    wav = base64.b64encode(b"RIFF\x00\x00\x00\x00WAVEfmt ").decode()
    r = client.post(
        "/requests", json={"prompt": "x", "image": image(), "audio": wav}, headers=people["dimas"]
    )
    assert r.json()["error"]["code"] == "ONE_MEDIA_ONLY"


@pytest.mark.parametrize(
    ("field", "payload", "missing"),
    [
        ("audio", b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 32, ["voice"]),
        ("video", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32, ["face_video", "voice"]),
    ],
)
def test_router_marks_missing_checks_and_fails_safe(client, people, field, payload, missing):
    r = client.post(
        "/requests",
        json={"prompt": "Buatkan avatar kartun saya.", field: base64.b64encode(payload).decode()},
        headers=people["dimas"],
    ).json()
    assert r["checks_unavailable"] == missing
    assert r["decision"]["action"] == "REVIEW"
    assert r["decision"]["reason_code"] == "CHECK_UNAVAILABLE"


def test_stage_timings_are_reported(client, people):
    r = _ask(client, people["dimas"])
    assert {"router", "face", "intent", "risk", "policy", "persist"} <= set(r["timing_ms"])


def test_gateway_rate_limit(client, people, monkeypatch):
    limiter.reset()
    monkeypatch.setattr(settings, "gateway_requests_per_minute", 2)
    codes = [
        client.post(
            "/requests", json={"prompt": "buat avatar"}, headers=people["dimas"]
        ).status_code
        for _ in range(3)
    ]
    assert codes == [200, 200, 429]
    limiter.reset()


# --- CLI ------------------------------------------------------------------------------------


def test_cli_roles_and_platform(client, people):
    with SessionLocal() as db:
        assert "REVIEWER" in cli.role_grant(db, "dimas@example.com", "REVIEWER")
        assert db.query(User).filter_by(email="dimas@example.com").one().role == "REVIEWER"
        cli.role_revoke(db, "dimas@example.com")
        assert db.query(User).filter_by(email="dimas@example.com").one().role == "USER"
        cli.platform_create(db, "dev@platform.example", "a-long-password-123")
        assert db.query(User).filter_by(email="dev@platform.example").one().role == "PLATFORM"
        with pytest.raises(SystemExit):
            cli.role_grant(db, "dimas@example.com", "PLATFORM")
        with pytest.raises(SystemExit):
            cli.platform_create(db, "x@platform.example", "short")


def test_registration_cannot_pick_a_role(client):
    client.post(
        "/auth/register",
        json={"email": "sneaky@example.com", "password": "secret123", "role": "ADMIN"},
    )
    with SessionLocal() as db:
        assert db.query(User).filter_by(email="sneaky@example.com").one().role == "USER"


def test_cli_purge_old_logs_keeps_the_chain_valid(client, people):
    from datetime import timedelta

    from app.core.timeutil import now
    from app.models.request import Request
    from app.services import audit_service

    old = _ask(client, people["dimas"])["request_id"]
    _ask(client, people["dimas"], "buat avatar kartun saya", who="dimas")
    with SessionLocal() as db:
        db.query(Request).filter_by(request_id=old).one().created_at = now() - timedelta(days=100)
        for row in db.query(AuditLog).order_by(AuditLog.seq).limit(2):
            row.created_at = now() - timedelta(days=100)
        db.commit()
        # Rewriting timestamps changed the hashed content: re-seal for this test only.
        rows = db.query(AuditLog).order_by(AuditLog.seq).all()
        prev = audit_service.GENESIS
        for r in rows:
            r.prev_hash = prev
            r.hash = audit_service._hash(
                prev, audit_service._canonical(r.event, r.actor_id, r.data, r.created_at)
            )
            prev = r.hash
        db.commit()
        counts = cli.purge_logs(db, 90)
        assert counts["requests"] == 1 and counts["audit"] == 2
        assert db.query(Request).filter_by(request_id=old).count() == 0
        assert audit_service.verify(db)["ok"] is True
        assert db.query(AuditLog).order_by(AuditLog.seq.desc()).first().event == "LOG_PURGED"


def test_cli_main_entrypoint(client, people):
    assert cli.main(["audit", "verify"]) == 0
