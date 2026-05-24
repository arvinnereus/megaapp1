def test_login_page_loads(client):
    resp = client.get("/admin/login")
    assert resp.status_code == 200

def test_login_success(client):
    resp = client.post("/admin/login", data={"username": "admin", "password": "admin"}, follow_redirects=True)
    assert resp.status_code == 200

def test_login_fail(client):
    resp = client.post("/admin/login", data={"username": "wrong", "password": "wrong"}, follow_redirects=True)
    assert resp.status_code == 200

def test_dashboard_requires_auth(client):
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 302  # redirect to login

def test_logout(auth_client):
    resp = auth_client.get("/admin/logout", follow_redirects=True)
    assert resp.status_code == 200
