def test_default_permissions(client, auth):
    headers, _ = auth
    r = client.get("/permissions", params={"identity_id": "ARMOR-001"}, headers=headers)
    assert r.status_code == 200
    perms = r.json()["permissions"]
    assert perms["personal_creation"] == "ALLOW"
    assert perms["impersonation"] == "DENY"
    assert perms["commercial_use"] == "REVIEW"


def test_override_permission(client, auth):
    headers, _ = auth
    r = client.post("/permissions",
                    json={"identity_id": "ARMOR-001", "action": "commercial_use",
                          "decision": "ALLOW"},
                    headers=headers)
    assert r.status_code == 200

    r = client.get("/permissions", params={"identity_id": "ARMOR-001"}, headers=headers)
    assert r.json()["permissions"]["commercial_use"] == "ALLOW"


def test_permission_invalid_decision_422(client, auth):
    headers, _ = auth
    r = client.post("/permissions",
                    json={"identity_id": "ARMOR-001", "action": "commercial_use",
                          "decision": "PERHAPS"},
                    headers=headers)
    assert r.status_code == 422


def test_permissions_require_auth(client):
    r = client.get("/permissions", params={"identity_id": "ARMOR-001"})
    assert r.status_code == 401
