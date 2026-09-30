def test_register_and_login_flow(client):
    r = client.post("/auth/register", json={"email": "a@b.com", "password": "pass123"})
    assert r.status_code == 201
    assert r.json()["user_id"].startswith("USER-")

    r = client.post("/auth/login", json={"email": "a@b.com", "password": "pass123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"


def test_duplicate_email_rejected(client):
    client.post("/auth/register", json={"email": "dup@b.com", "password": "pass123"})
    r = client.post("/auth/register", json={"email": "dup@b.com", "password": "pass123"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "EMAIL_TAKEN"


def test_bad_login(client):
    client.post("/auth/register", json={"email": "c@b.com", "password": "pass123"})
    r = client.post("/auth/login", json={"email": "c@b.com", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_protected_route_requires_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_error_envelope_shape(client):
    r = client.get("/auth/me")
    body = r.json()
    assert set(body["error"].keys()) >= {"code", "message"}
