"""Tests del endpoint GET /blacklists/<email>."""


def _add_email(client, auth_header, email, reason="spam"):
    return client.post(
        "/blacklists",
        data={
            "email": email,
            "app_uuid": "44444444-4444-4444-4444-444444444444",
            "blocked_reason": reason,
        },
        headers=auth_header,
    )


def test_get_blacklist_found(client, auth_header):
    _add_email(client, auth_header, "found@uniandes.edu.co", reason="fraude")

    resp = client.get(
        "/blacklists/found@uniandes.edu.co",
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["in_blacklist"] is True
    assert body["blocked_reason"] == "fraude"


def test_get_blacklist_not_found(client, auth_header):
    resp = client.get(
        "/blacklists/nope@uniandes.edu.co",
        headers=auth_header,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["in_blacklist"] is False
    assert body["blocked_reason"] is None


def test_get_blacklist_unauthorized(client):
    resp = client.get("/blacklists/whatever@x.com")
    assert resp.status_code == 401


def test_get_blacklist_returns_latest_reason(client, auth_header):
    """Si un email se inserta dos veces, el GET devuelve el motivo mas reciente."""
    _add_email(client, auth_header, "dup@uniandes.edu.co", reason="primera")
    _add_email(client, auth_header, "dup@uniandes.edu.co", reason="segunda")

    resp = client.get(
        "/blacklists/dup@uniandes.edu.co",
        headers=auth_header,
    )
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["in_blacklist"] is True
    assert body["blocked_reason"] == "segunda"
