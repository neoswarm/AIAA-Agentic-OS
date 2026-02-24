import json
from unittest.mock import mock_open, patch

import execution.modal_webhook as modal_webhook


def _json_body(response):
    return json.loads(response.body.decode("utf-8"))


def test_export_demo_transcript_json():
    expected = "# Sales Transcript\n\nHello world."

    with patch("builtins.open", mock_open(read_data=expected)) as mocked_open:
        response = modal_webhook.export_demo_transcript.local(name="sales", format="json")

    assert response.status_code == 200
    data = _json_body(response)
    assert data["status"] == "success"
    assert data["name"] == "sales"
    assert data["format"] == "json"
    assert data["content"] == expected
    assert response.headers["content-disposition"] == 'attachment; filename="sales_transcript.json"'
    mocked_open.assert_any_call("/app/demo_sales_call_transcript.md", "r", encoding="utf-8")


def test_export_demo_transcript_markdown():
    expected = "# Kickoff Transcript\n\nLine 1"

    with patch("builtins.open", mock_open(read_data=expected)) as mocked_open:
        response = modal_webhook.export_demo_transcript.local(name="kickoff", format="markdown")

    assert response.status_code == 200
    assert response.body.decode("utf-8") == expected
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == 'attachment; filename="kickoff_transcript.md"'
    mocked_open.assert_any_call("/app/demo_kickoff_call_transcript.md", "r", encoding="utf-8")


def test_export_demo_transcript_invalid_format():
    response = modal_webhook.export_demo_transcript.local(name="sales", format="xml")

    assert response.status_code == 400
    data = _json_body(response)
    assert data["status"] == "error"
    assert "Unsupported format" in data["error"]
    assert data["available_formats"] == ["json", "markdown"]


def test_export_demo_transcript_invalid_name():
    with patch("builtins.open", mock_open(read_data="ignored")) as mocked_open:
        response = modal_webhook.export_demo_transcript.local(name="unknown", format="json")

    assert response.status_code == 400
    data = _json_body(response)
    assert data["status"] == "error"
    assert data["error"] == "Unknown transcript: unknown"
    assert sorted(data["available"]) == ["kickoff", "sales"]
    mocked_open.assert_not_called()
