def test_help_requires_auth(client):
    resp = client.get("/help/")
    assert resp.status_code == 302

def test_help_loads(auth_client):
    resp = auth_client.get("/help/")
    assert resp.status_code == 200
    assert b"How It All Works" in resp.data or b"help" in resp.data.lower()
