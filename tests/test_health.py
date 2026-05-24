"""Smoke tests del endpoint de salud."""


def test_health_check_returns_200(client):
    resp = client.get("/ping")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_index_returns_metadata(client):
    resp = client.get("/api/info")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["service"] == "blacklist-microservice"
    assert "/blacklists" in body["endpoints"]
