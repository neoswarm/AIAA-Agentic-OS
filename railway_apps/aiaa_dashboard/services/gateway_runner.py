"""
Gateway-backed chat runner implementing the existing runner interface contract.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping

from services.agent_runner import (
    AgentRunner,
    RunnerError,
    _redact_token_like_text,
    _utc_now_iso,
)
from services.gateway_client import GatewayClient

__all__ = ["GatewayRunner", "RunnerError"]


logger = logging.getLogger(__name__)


class GatewayRunner(AgentRunner):
    """Drop-in runner implementation for gateway-based chat execution."""

    RESPONSES_PATH = "/v1/responses"

    def __init__(
        self,
        cwd: str | None,
        token_provider,
        allowed_tools: list[str] | None = None,
        permission_mode: str = "acceptEdits",
        session_store: Any | None = None,
        cwd_allowlist: list[str] | None = None,
        gateway_client: GatewayClient | None = None,
        gateway_base_url: str | None = None,
        gateway_api_key: str | None = None,
    ) -> None:
        super().__init__(
            cwd=cwd,
            token_provider=token_provider,
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            session_store=session_store,
            cwd_allowlist=cwd_allowlist,
        )
        self._gateway_base_url = (gateway_base_url or os.getenv("GATEWAY_BASE_URL", "")).strip()
        self._gateway_api_key = (gateway_api_key or os.getenv("GATEWAY_API_KEY", "")).strip()
        self._gateway_client = gateway_client

    def _resolve_gateway_client(self) -> GatewayClient:
        if self._gateway_client is not None:
            return self._gateway_client
        if not self._gateway_base_url:
            raise RunnerError("GATEWAY_BASE_URL is not configured")
        self._gateway_client = GatewayClient(
            self._gateway_base_url,
            api_key=self._gateway_api_key or None,
        )
        return self._gateway_client

    @staticmethod
    def _extract_gateway_error(payload: Mapping[str, Any]) -> str:
        error_obj = payload.get("error")
        if isinstance(error_obj, Mapping):
            message = error_obj.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()

        status = str(payload.get("status") or "").strip().lower()
        if status in {"failed", "error"}:
            return "Gateway response reported failure"
        return ""

    @staticmethod
    def _extract_gateway_text(payload: Mapping[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str):
            return output_text

        output = payload.get("output")
        if not isinstance(output, list):
            return ""

        chunks: list[str] = []
        for item in output:
            if not isinstance(item, Mapping):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, Mapping):
                    continue
                if str(block.get("type", "")).strip().lower() not in {
                    "output_text",
                    "text",
                }:
                    continue
                text = block.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "".join(chunks)

    def _run_agent(self, session_id: str, user_message: str) -> None:
        q = self._get_queue_or_raise(session_id)

        try:
            self._record_run_started(session_id)
            token = (self._token_provider() or "").strip()
            if not token:
                raise RunnerError("Claude token is not configured")

            client = self._resolve_gateway_client()
            response = client.post_json(
                self.RESPONSES_PATH,
                payload={"input": user_message, "stream": False},
                headers={"X-Anthropic-Api-Key": token},
            )

            if not isinstance(response, dict):
                raise RunnerError("Gateway response body must be a JSON object")

            error_message = self._extract_gateway_error(response)
            if error_message:
                raise RunnerError(error_message)

            result_text = self._extract_gateway_text(response)
            if result_text:
                event = {
                    "type": "result",
                    "content": result_text,
                    "timestamp": _utc_now_iso(),
                }
                self._record_first_event_latency(session_id)
                q.put(event)
                self._persist_event(session_id, event)
                self._append_assistant_message(session_id, result_text)

            self._set_session_state(session_id, status="idle", last_error=None)
            q.put(
                {
                    "type": "done",
                    "timestamp": _utc_now_iso(),
                    "metrics": self._record_total_runtime(session_id),
                }
            )
        except Exception as exc:  # pragma: no cover - runtime safety path
            message = _redact_token_like_text(str(exc) or "Gateway execution failed")
            logger.exception("Gateway run failed for session %s: %s", session_id, message)
            self._set_session_state(session_id, status="error", last_error=message)
            q.put(
                {
                    "type": "error",
                    "content": message,
                    "timestamp": _utc_now_iso(),
                    "metrics": self._record_total_runtime(session_id),
                }
            )
