import json

def test_create_content_requires_auth(client):
    resp = client.post("/content/api/create",
                       data=json.dumps({"input_text": "test"}),
                       content_type="application/json")
    assert resp.status_code == 401

def test_list_items(auth_client):
    resp = auth_client.get("/content/api/items")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)

def test_delete_nonexistent(auth_client):
    resp = auth_client.delete("/content/api/9999")
    assert resp.status_code == 404
