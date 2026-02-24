#!/usr/bin/env python3
"""Integration test for interrupted event stream resume behavior."""

import pytest

import app_legacy


@pytest.fixture(autouse=True)
def reset_event_state():
    """Reset shared in-memory event state for isolated tests."""
    with app_legacy.events_lock:
        app_legacy.events_log.clear()
        app_legacy.event_id_counter = 0


@pytest.fixture()
def auth_client():
    """Authenticated Flask test client for legacy app routes."""
    app_legacy.app.config["TESTING"] = True
    client = app_legacy.app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testadmin"
    return client


def test_interrupted_stream_resume_returns_only_missed_events(auth_client):
    """Client can resume after interruption using the last seen event ID."""
    app_legacy.log_event("test", "success", {"chunk": "A"}, source="test")
    app_legacy.log_event("test", "success", {"chunk": "B"}, source="test")

    initial = auth_client.get("/api/events")
    assert initial.status_code == 200
    initial_events = initial.get_json()
    assert [event["id"] for event in initial_events] == [2, 1]

    # Simulate disconnect after the client received event ID 2.
    last_seen_id = initial_events[0]["id"]

    app_legacy.log_event("test", "success", {"chunk": "C"}, source="test")
    app_legacy.log_event("test", "success", {"chunk": "D"}, source="test")

    resumed = auth_client.get(
        "/api/events",
        headers={"Last-Event-ID": str(last_seen_id)},
    )
    assert resumed.status_code == 200

    resumed_events = resumed.get_json()
    assert [event["id"] for event in resumed_events] == [3, 4]
    assert [event["data"]["chunk"] for event in resumed_events] == ["C", "D"]
