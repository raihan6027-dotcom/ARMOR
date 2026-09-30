"""Fase 6b: human outcomes become labels only when the requester opted in."""

import csv

import pytest

from app import cli
from app.db.database import SessionLocal
from app.models.feedback import Feedback
from app.services import feedback_service
from tests.synthetic import face, image

AD = "Buat iklan produk kopi dengan wajah orang ini."


@pytest.fixture()
def people(make_user, enroll):
    raka_h, _ = make_user("raka@example.com")
    dimas_h, _ = make_user("dimas@example.com")
    reviewer_h, _ = make_user("reviewer@example.com")
    with SessionLocal() as db:
        cli.role_grant(db, "reviewer@example.com", "REVIEWER")
    enroll(raka_h, "raka")
    return {"owner": raka_h, "req": dimas_h, "reviewer": reviewer_h}


def _held(client, headers, allow_training):
    r = client.post(
        "/requests",
        json={"prompt": AD, "image": image(face("raka")), "allow_training": allow_training},
        headers=headers,
    ).json()
    client.post("/consent/request", json={"request_id": r["request_id"]}, headers=headers)
    return r["request_id"]


def _approve(client, owner):
    cid = client.get("/consent/inbox?status=pending", headers=owner).json()["items"][0][
        "consent_id"
    ]
    client.post(f"/consent/{cid}/respond", json={"action": "APPROVE"}, headers=owner)


def test_consent_and_resolved_review_become_labels_when_opted_in(client, people):
    request_id = _held(client, people["req"], allow_training=True)
    _approve(client, people["owner"])
    with SessionLocal() as db:
        rows = db.query(Feedback).filter_by(request_id=request_id).all()
        assert sorted(r.source for r in rows) == ["CONSENT_GRANTED", "REVIEW_RESOLVED"]
        assert all(r.intent_final == "COMMERCIAL_USE" and r.prompt == AD for r in rows)
        assert all("realism" in r.features for r in rows)  # content features, no media


def test_no_labels_without_opt_in(client, people):
    _held(client, people["req"], allow_training=False)
    _approve(client, people["owner"])
    with SessionLocal() as db:
        assert db.query(Feedback).count() == 0


def test_appeal_relabel_is_recorded_with_the_corrected_label(client, people):
    denied = client.post(
        "/requests",
        json={
            "prompt": "Buat orang ini memakai baju tahanan untuk film.",
            "image": image(face("citra")),
            "allow_training": True,
        },
        headers=people["req"],
    ).json()
    case_id = client.post(
        "/cases",
        json={"request_id": denied["request_id"], "note": "kostum film"},
        headers=people["req"],
    ).json()["case_id"]
    client.post(
        f"/cases/{case_id}/resolve",
        json={
            "outcome": "RELABEL",
            "corrected_intent": "PERSONAL_CREATION",
            "corrected_risk": "LOW",
        },
        headers=people["reviewer"],
    )
    with SessionLocal() as db:
        row = db.query(Feedback).filter_by(source="APPEAL_RELABEL").one()
        assert (row.intent_final, row.risk_final) == ("PERSONAL_CREATION", "LOW")


def test_export_keeps_reviewer_marks(client, people, tmp_path):
    _held(client, people["req"], allow_training=True)
    _approve(client, people["owner"])
    out = tmp_path / "feedback.csv"
    with SessionLocal() as db:
        n = feedback_service.export_csv(db, out)
    assert n == 2
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert all(r["diperiksa_oleh"] == "" for r in rows)
    rows[0]["diperiksa_oleh"] = "RA"
    rows[0]["intent_final"] = "POLITICAL_USE"  # a reviewer correction
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=feedback_service.EXPORT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    with SessionLocal() as db:
        feedback_service.export_csv(db, out)
    again = {r["feedback_id"]: r for r in csv.DictReader(out.open(encoding="utf-8"))}
    kept = again[rows[0]["feedback_id"]]
    assert (kept["diperiksa_oleh"], kept["intent_final"]) == ("RA", "POLITICAL_USE")


def test_cli_feedback_export(client, people, tmp_path):
    out = tmp_path / "fb.csv"
    assert cli.main(["feedback", "export", "--out", str(out)]) == 0
    assert out.exists()
