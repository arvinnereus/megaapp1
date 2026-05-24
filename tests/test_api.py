import json

def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200

def test_contacts_requires_auth(client):
    resp = client.get("/api/contacts")
    assert resp.status_code == 401

def test_contacts_list(auth_client):
    resp = auth_client.get("/api/contacts")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)

def test_create_contact(auth_client):
    resp = auth_client.post("/api/contacts",
                            data=json.dumps({"name": "Test User", "email": "test@test.com"}),
                            content_type="application/json")
    assert resp.status_code == 201 or resp.status_code == 200

def test_dashboard_stats(auth_client):
    resp = auth_client.get("/api/dashboard-stats")
    assert resp.status_code == 200
