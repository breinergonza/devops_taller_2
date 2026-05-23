"""Tests de la configuracion segura de observabilidad."""


def test_new_relic_status_endpoint_does_not_expose_license(client, monkeypatch):
    monkeypatch.setenv("NEW_RELIC_LICENSE_KEY", "secret-test-key")
    monkeypatch.setenv("NEW_RELIC_APP_NAME", "devops-taller-4-flask-test")
    monkeypatch.setenv("NEW_RELIC_ENVIRONMENT", "test")

    resp = client.get("/observability/newrelic")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["enabled"] is True
    assert body["app_name"] == "devops-taller-4-flask-test"
    assert body["environment"] == "test"
    assert "secret-test-key" not in resp.get_data(as_text=True)


def test_debug_error_endpoint_is_disabled_by_default(client):
    resp = client.get("/debug/newrelic-error")

    assert resp.status_code == 404
