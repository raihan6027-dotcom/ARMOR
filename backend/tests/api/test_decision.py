"""Direct /decision endpoint (stateless policy evaluation)."""


def test_decision_allow(client):
    r = client.post(
        "/decision",
        json={
            "risk_level": "LOW",
            "consent": "GRANTED",
            "permission": "ALLOW",
            "identity_target": "SELF",
            "identity_verified": True,
            "intent": "PERSONAL_CREATION",
        },
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "ALLOW"


def test_decision_review(client):
    r = client.post(
        "/decision",
        json={
            "risk_level": "HIGH",
            "consent": "UNKNOWN",
            "permission": "REVIEW",
            "identity_target": "OTHER",
            "intent": "COMMERCIAL_USE",
        },
    )
    assert r.json()["decision"] == "REVIEW"


def test_decision_deny(client):
    r = client.post(
        "/decision",
        json={
            "risk_level": "CRITICAL",
            "consent": "DENIED",
            "permission": "DENY",
            "identity_target": "OTHER",
            "intent": "IMPERSONATION",
        },
    )
    body = r.json()
    assert body["decision"] == "DENY"
    assert body["reason_code"]
    assert body["reason"]
