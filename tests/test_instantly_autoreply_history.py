import execution.instantly_autoreply as instantly_autoreply


class _MockResponse:
    def __init__(self, status_code=200, items=None):
        self.status_code = status_code
        self._items = items or []

    def json(self):
        return {"items": self._items}


def test_get_conversation_history_clamps_limit_and_trims_items(monkeypatch):
    captured = {}

    def fake_get(url, headers, params, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        captured["timeout"] = timeout

        items = []
        for i in range(30):
            items.append(
                {
                    "from_address_email": f"person{i}@example.com",
                    "timestamp": f"2026-02-24T00:00:{i:02d}Z",
                    "body": {"text": f"email body {i}", "html": "<p>ignored</p>"},
                    "unused": "drop-this",
                }
            )

        return _MockResponse(status_code=200, items=items)

    monkeypatch.setenv("INSTANTLY_API_KEY", "test-key")
    monkeypatch.setattr(instantly_autoreply.requests, "get", fake_get)

    history = instantly_autoreply.get_conversation_history("lead@example.com", limit=999)

    assert captured["params"]["limit"] == instantly_autoreply.MAX_HISTORY_API_LIMIT
    assert len(history) == instantly_autoreply.MAX_HISTORY_API_LIMIT

    first = history[0]
    assert set(first.keys()) == {"from_address_email", "body_text", "timestamp"}
    assert first["body_text"] == "email body 0"


def test_get_conversation_history_returns_empty_without_lead_email(monkeypatch):
    called = {"value": False}

    def fake_get(*args, **kwargs):
        called["value"] = True
        return _MockResponse()

    monkeypatch.setenv("INSTANTLY_API_KEY", "test-key")
    monkeypatch.setattr(instantly_autoreply.requests, "get", fake_get)

    assert instantly_autoreply.get_conversation_history("", limit=10) == []
    assert called["value"] is False


def test_build_history_context_applies_total_char_budget():
    conversation_history = []
    for i in range(10):
        conversation_history.append(
            {
                "from_address_email": f"person{i}@example.com",
                "body_text": f"msg{i}-" + ("x" * 600),
            }
        )

    context = instantly_autoreply.build_history_context(conversation_history)

    assert "msg0-" in context
    assert "msg1-" in context
    assert "msg2-" in context
    assert "msg3-" in context
    assert "msg4-" not in context
    assert context.count("From:") == 4
