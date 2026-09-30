"""Direct /decision endpoint (stateless policy evaluation, Fase 2 contract)."""


def test_decision_allow_self(client):
    r = client.post(
        "/decision",
        json={
            "intent": "PERSONAL_CREATION",
            "risk_level": "LOW",
            "targets": [{"source": "FACE", "target_type": "SELF"}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "ALLOW"
    assert body["reason_code"] == "SELF_ALLOWED"


def test_decision_review_registered_without_consent(client):
    r = client.post(
        "/decision",
        json={
            "intent": "COMMERCIAL_USE",
            "risk_level": "MEDIUM",
            "targets": [{"target_type": "OTHER_REGISTERED", "identity_id": "B"}],
        },
    )
    body = r.json()
    assert body["decision"] == "REVIEW"
    assert body["reason_code"] == "CONSENT_REQUIRED"
    assert body["requester_code"] == "NEEDS_REVIEW"
    assert body["per_target_detail"][0]["identity_id"] == "B"


def test_decision_deny_with_explanation_and_suggestion(client):
    r = client.post(
        "/decision",
        json={
            "intent": "DEFAMATION",
            "risk_level": "CRITICAL",
            "prompt": "buat dia pakai baju tahanan dan diborgol",
            "targets": [{"target_type": "OTHER_UNREGISTERED"}],
        },
    )
    body = r.json()
    assert body["decision"] == "DENY"
    assert body["reason_code"] == "HARMFUL_DEFAMATION"
    assert "tahanan" in body["reason"]
    assert body["suggestion"] == "Buat karikatur superhero dari foto ini."


def test_decision_multi_target_strictest(client):
    r = client.post(
        "/decision",
        json={
            "intent": "COMMERCIAL_USE",
            "risk_level": "MEDIUM",
            "targets": [
                {"target_type": "SELF"},
                {"target_type": "OTHER_REGISTERED", "lock_level": "COMMERCIAL_POLITICAL"},
            ],
        },
    )
    assert r.json()["decision"] == "DENY"


def test_decision_rejects_legacy_flat_body(client):
    r = client.post(
        "/decision",
        json={
            "risk_level": "LOW",
            "consent": "GRANTED",
            "permission": "ALLOW",
            "identity_target": "SELF",
            "intent": "PERSONAL_CREATION",
        },
    )
    assert r.status_code == 422
