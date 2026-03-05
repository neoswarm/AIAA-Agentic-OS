"""Gateway HTTP client with typed JSON wrappers and retry/backoff support."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from collections.abc import Generator
from typing import Any, Callable, Mapping, Protocol, TypeVar

import requests


JSONBody = dict[str, Any] | list[Any]
RequestPayload = Mapping[str, Any] | list[Any] | None
QueryParams = Mapping[str, str | int | float | bool] | None
ParsedT = TypeVar("ParsedT")


class RequestSession(Protocol):
    """Protocol for request-compatible sessions."""

    def request(
        self,
        method: str,
        url: str,
        *,
        params: QueryParams = None,
        json: RequestPayload = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        stream: bool | None = None,
    ) -> requests.Response:
        """Execute an HTTP request."""


@dataclass(frozen=True)
class RetryConfig:
    """Retry policy for gateway requests."""

    max_attempts: int = 3
    base_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 8.0
    retryable_status_codes: tuple[int, ...] = (408, 425, 429, 500, 502, 503, 504)

    def backoff_for_attempt(self, attempt: int) -> float:
        """Return backoff delay for a failed attempt (1-indexed)."""
        delay = self.base_backoff_seconds * (2 ** max(0, attempt - 1))
        return min(delay, self.max_backoff_seconds)


class GatewayClientError(RuntimeError):
    """Base gateway client error."""


class GatewayHTTPError(GatewayClientError):
    """Gateway request returned an HTTP error."""

    def __init__(self, status_code: int, message: str, response_text: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class GatewayDecodeError(GatewayClientError):
    """Gateway response could not be parsed as expected JSON."""


class GatewayClient:
    """Small HTTP client for gateway calls with retry/backoff."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        timeout_seconds: float = 10.0,
        retry_config: RetryConfig | None = None,
        session: RequestSession | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        normalized = (base_url or "").strip().rstrip("/")
        if not normalized:
            raise ValueError("base_url is required")

        self.base_url = normalized
        self.timeout_seconds = timeout_seconds
        self.retry_config = retry_config or RetryConfig()
        self._session = session or requests.Session()
        self._sleep = sleep
        self._base_headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            self._base_headers["Authorization"] = f"Bearer {api_key}"

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: QueryParams = None,
        payload: RequestPayload = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> JSONBody:
        """Execute an HTTP request and return parsed JSON body."""
        request_timeout = (
            self.timeout_seconds if timeout_seconds is None else timeout_seconds
        )
        max_attempts = max(1, int(self.retry_config.max_attempts))
        url = self._build_url(path)
        merged_headers = dict(self._base_headers)
        if headers:
            merged_headers.update(headers)

        for attempt in range(1, max_attempts + 1):
            try:
                response = self._session.request(
                    method.upper(),
                    url,
                    params=params,
                    json=payload,
                    headers=merged_headers,
                    timeout=request_timeout,
                )
            except requests.RequestException as exc:
                if not self._should_retry_exception(exc, attempt, max_attempts):
                    raise GatewayClientError(
                        f"Gateway request failed after {attempt} attempt(s): {exc}"
                    ) from exc
                self._sleep(self.retry_config.backoff_for_attempt(attempt))
                continue

            if response.status_code >= 400:
                error = GatewayHTTPError(
                    response.status_code,
                    f"Gateway returned HTTP {response.status_code} for {method.upper()} {url}",
                    response_text=response.text,
                )
                if self._should_retry_status(
                    response.status_code, attempt, max_attempts
                ):
                    self._sleep(self.retry_config.backoff_for_attempt(attempt))
                    continue
                raise error

            try:
                body = response.json()
            except ValueError as exc:
                raise GatewayDecodeError(
                    f"Gateway returned non-JSON response for {method.upper()} {url}"
                ) from exc

            if not isinstance(body, (dict, list)):
                raise GatewayDecodeError(
                    f"Gateway JSON body must be an object or list, got {type(body).__name__}"
                )
            return body

        raise GatewayClientError("Gateway request failed unexpectedly")

    def request_typed(
        self,
        method: str,
        path: str,
        *,
        parser: Callable[[JSONBody], ParsedT],
        params: QueryParams = None,
        payload: RequestPayload = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> ParsedT:
        """Execute request and parse JSON into a typed result."""
        body = self.request_json(
            method,
            path,
            params=params,
            payload=payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )
        return parser(body)

    def get_json(
        self,
        path: str,
        *,
        params: QueryParams = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> JSONBody:
        """Typed wrapper for GET JSON requests."""
        return self.request_json(
            "GET",
            path,
            params=params,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )

    def post_json(
        self,
        path: str,
        *,
        payload: RequestPayload = None,
        params: QueryParams = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> JSONBody:
        """Typed wrapper for POST JSON requests."""
        return self.request_json(
            "POST",
            path,
            params=params,
            payload=payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )

    def post_stream(
        self,
        path: str,
        *,
        payload: RequestPayload = None,
        params: QueryParams = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Execute a streaming POST request and yield parsed SSE JSON events.

        Only `data:` lines containing JSON objects are yielded. `[DONE]` and
        other non-JSON payload lines are ignored.
        """
        request_timeout = (
            self.timeout_seconds if timeout_seconds is None else timeout_seconds
        )
        url = self._build_url(path)
        merged_headers = dict(self._base_headers)
        merged_headers.setdefault("Accept", "text/event-stream")
        if headers:
            merged_headers.update(headers)

        try:
            response = self._session.request(
                "POST",
                url,
                params=params,
                json=payload,
                headers=merged_headers,
                timeout=request_timeout,
                stream=True,
            )
        except requests.RequestException as exc:
            raise GatewayClientError(
                f"Gateway stream request failed for POST {url}: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise GatewayHTTPError(
                response.status_code,
                f"Gateway returned HTTP {response.status_code} for POST {url}",
                response_text=response.text,
            )

        try:
            for raw_line in response.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                line = str(raw_line).strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    parsed = json.loads(data)
                except ValueError:
                    continue
                if isinstance(parsed, dict):
                    yield parsed
        finally:
            response.close()

    def get_typed(
        self,
        path: str,
        *,
        parser: Callable[[JSONBody], ParsedT],
        params: QueryParams = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> ParsedT:
        """Typed wrapper for GET requests with response parsing."""
        return self.request_typed(
            "GET",
            path,
            parser=parser,
            params=params,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )

    def post_typed(
        self,
        path: str,
        *,
        parser: Callable[[JSONBody], ParsedT],
        payload: RequestPayload = None,
        params: QueryParams = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> ParsedT:
        """Typed wrapper for POST requests with response parsing."""
        return self.request_typed(
            "POST",
            path,
            parser=parser,
            params=params,
            payload=payload,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.base_url}{normalized}"

    def _should_retry_status(
        self, status_code: int, attempt: int, max_attempts: int
    ) -> bool:
        return (
            attempt < max_attempts
            and status_code in self.retry_config.retryable_status_codes
        )

    def _should_retry_exception(
        self,
        exc: requests.RequestException,
        attempt: int,
        max_attempts: int,
    ) -> bool:
        if attempt >= max_attempts:
            return False
        return isinstance(exc, (requests.Timeout, requests.ConnectionError))
