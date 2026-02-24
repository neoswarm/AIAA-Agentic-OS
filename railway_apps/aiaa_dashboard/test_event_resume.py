#!/usr/bin/env python3
"""Tests for event resume behavior in app_legacy /api/events."""

import pytest

import app_legacy


@pytest.fixture(autouse=True)
def reset_event_state():
    """Reset shared in-memory event state between tests."""
    with app_legacy.events_lock:
        app_legacy.events_log.clear()
        app_legacy.event_id_counter = 0


@pytest.fixture
def auth_client():
    """Authenticated Flask test client."""
    app_legacy.app.config["TESTING"] = True
    client = app_legacy.app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "test"
    return client


def test_log_event_ids_remain_monotonic_after_buffer_rollover():
    for i in range(510):
        app_legacy.log_event("test", "success", {"index": i}, source="test")

    with app_legacy.events_lock:
        ids = [event["id"] for event in app_legacy.events_log]

    assert len(ids) == 500
    assert len(set(ids)) == 500
    assert ids[0] == 510
    assert ids[-1] == 11


def test_api_events_resume_with_last_event_id_query(auth_client):
    app_legacy.log_event("test", "success", {"index": 1}, source="test")
    app_legacy.log_event("test", "success", {"index": 2}, source="test")
    app_legacy.log_event("test", "success", {"index": 3}, source="test")

    response = auth_client.get("/api/events?last_event_id=1")

    assert response.status_code == 200
    ids = [event["id"] for event in response.get_json()]
    assert ids == [2, 3]


def test_api_events_resume_with_last_event_id_header(auth_client):
    app_legacy.log_event("test", "success", {"index": 1}, source="test")
    app_legacy.log_event("test", "success", {"index": 2}, source="test")
    app_legacy.log_event("test", "success", {"index": 3}, source="test")

    response = auth_client.get("/api/events", headers={"Last-Event-ID": "2"})

    assert response.status_code == 200
    ids = [event["id"] for event in response.get_json()]
    assert ids == [3]


def test_api_events_invalid_last_event_id_returns_400(auth_client):
    app_legacy.log_event("test", "success", {"index": 1}, source="test")

    response = auth_client.get("/api/events?last_event_id=abc")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid last_event_id"


def test_api_events_without_last_event_id_preserves_current_order(auth_client):
    app_legacy.log_event("test", "success", {"index": 1}, source="test")
    app_legacy.log_event("test", "success", {"index": 2}, source="test")
    app_legacy.log_event("test", "success", {"index": 3}, source="test")

    response = auth_client.get("/api/events")

    assert response.status_code == 200
    ids = [event["id"] for event in response.get_json()]
    assert ids == [3, 2, 1]
