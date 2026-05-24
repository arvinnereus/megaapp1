def test_content_index_requires_auth(client):
    resp = client.get("/content/")
    assert resp.status_code == 302

def test_content_index_loads(auth_client):
    resp = auth_client.get("/content/")
    assert resp.status_code == 200

def test_content_create_page_loads(auth_client):
    resp = auth_client.get("/content/create")
    assert resp.status_code == 200

def test_content_detail_404(auth_client):
    resp = auth_client.get("/content/9999")
    assert resp.status_code == 404
