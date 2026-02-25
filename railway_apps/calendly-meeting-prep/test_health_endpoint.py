from datetime import datetime


def test_health_endpoint_returns_healthy_payload(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "calendly-meeting-prep"
    assert "timestamp" in payload


def test_health_endpoint_timestamp_is_isoformat(client):
    response = client.get("/health")

    payload = response.get_json()
    datetime.fromisoformat(payload["timestamp"])
