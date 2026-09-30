"""Intent & risk endpoints, exercising the deterministic fallback (no Gemini key)."""


def test_analyze_intent_commercial(client):
    r = client.post(
        "/ai/analyze-intent", json={"prompt": "Buat video orang ini mempromosikan produk X"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "COMMERCIAL_USE"
    assert body["ai_available"] is False  # fallback path


def test_analyze_intent_alias(client):
    r = client.post(
        "/analyze/intent", json={"prompt": "orang ini mengatakan sesuatu yang tidak pernah"}
    )
    assert r.status_code == 200
    assert r.json()["intent"] == "IMPERSONATION"


def test_risk_endpoint_medium_for_commercial_other(client):
    # Fase 2: consent is not a risk feature (CLAUDE.md bagian 8) and a commercial
    # ad must be able to reach REVIEW -> ALLOW with consent (scenario 4), so the
    # fallback risk for COMMERCIAL_USE is MEDIUM, not HIGH.
    r = client.post(
        "/risk",
        json={"identity_target": "OTHER_REGISTERED", "intent": "COMMERCIAL_USE"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["risk_level"] == "MEDIUM"
    assert 0 <= body["risk_score"] <= 100


def test_risk_low_for_personal(client):
    r = client.post(
        "/analyze/risk",
        json={
            "identity_target": "SELF",
            "intent": "PERSONAL_CREATION",
            "consent": "GRANTED",
        },
    )
    assert r.json()["risk_level"] == "LOW"


def test_risk_never_low_on_unknown_intent_misuse(client):
    # Impersonation must be treated as high/critical even in fallback mode.
    r = client.post(
        "/risk",
        json={
            "identity_target": "OTHER",
            "intent": "IMPERSONATION",
            "consent": "UNKNOWN",
        },
    )
    assert r.json()["risk_level"] in ("HIGH", "CRITICAL")
