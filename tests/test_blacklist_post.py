"""Tests del endpoint POST /blacklists."""


def test_post_blacklist_ok(client, auth_header):
    resp = client.post(
        "/blacklists",
        data={
            "email": "lol@uniandes.edu.co",
            "app_uuid": "11111111-1111-1111-1111-111111111111",
            "blocked_reason": "spam masivo",
        },
        headers=auth_header,
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["email"] == "test@uniandes.edu.co"
    assert "id" in body and isinstance(body["id"], int)
    assert "created_at" in body


def test_post_blacklist_without_blocked_reason(client, auth_header):
    resp = client.post(
        "/blacklists",
        data={
            "email": "no-reason@uniandes.edu.co",
            "app_uuid": "22222222-2222-2222-2222-222222222222",
        },
        headers=auth_header,
    )
    assert resp.status_code == 201


def test_post_blacklist_unauthorized_without_token(client):
    resp = client.post(
        "/blacklists",
        data={"email": "x@y.com", "app_uuid": "uuid"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["msg"] == "Unauthorized"


def test_post_blacklist_unauthorized_with_bad_token(client, bad_auth_header):
    resp = client.post(
        "/blacklists",
        data={"email": "x@y.com", "app_uuid": "uuid"},
        headers=bad_auth_header,
    )
    assert resp.status_code == 401


def test_post_blacklist_missing_required_field(client, auth_header):
    resp = client.post(
        "/blacklists",
        data={"email": "missing-uuid@uniandes.edu.co"},
        headers=auth_header,
    )
    assert resp.status_code == 400


def test_post_blacklist_blocked_reason_too_long(client, auth_header):
    resp = client.post(
        "/blacklists",
        data={
            "email": "long-reason@uniandes.edu.co",
            "app_uuid": "33333333-3333-3333-3333-333333333333",
            "blocked_reason": "x" * 256,
        },
        headers=auth_header,
    )
    assert resp.status_code == 400
