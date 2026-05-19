"""HttpClient adapter based on the httpx library.

This adapter wraps an httpx.Client and translates between the domain
types of gtaakit (HttpRequest, HttpResponse) and the corresponding
httpx primitives. It supports a base URL, default headers, and TLS
verification, and it measures the elapsed time of each request.
"""

from __future__ import annotations

import time
from types import TracebackType
from typing import Any

import httpx

from gtaakit.domain.http import HttpRequest, HttpResponse


class HttpxClient:
    """HttpClient adapter built on top of httpx.Client.

    The adapter keeps an httpx.Client instance alive across requests
    to reuse the underlying connection pool. Callers are expected to
    use the context-manager form or to call close() explicitly when
    done.
    """

    def __init__(
        self,
        base_url: str | None = None,
        default_headers: dict[str, str] | None = None,
        verify_tls: bool = True,
    ) -> None:
        """Build an HttpxClient adapter.

        Args:
            base_url: Optional URL prefix used for relative request URLs.
            default_headers: Optional headers attached to every request.
            verify_tls: Whether to verify TLS certificates. Default True;
                set to False only for tests against environments with
                self-signed certificates.
        """
        self._client = httpx.Client(
            base_url=base_url or "",
            headers=default_headers or {},
            verify=verify_tls,
        )

    def send(self, request: HttpRequest) -> HttpResponse:
        """Send an HTTP request and return the response as a domain type."""
        start = time.perf_counter()
        raw = self._client.request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            params=request.query_params,
            json=request.body if isinstance(request.body, (dict, list)) else None,
            content=request.body if isinstance(request.body, (str, bytes)) else None,
            timeout=request.timeout_seconds,
        )
        elapsed = time.perf_counter() - start

        body: Any
        content_type = raw.headers.get("content-type", "").lower()
        if "json" in content_type:
            try:
                body = raw.json()
            except ValueError:
                body = raw.text
        else:
            body = raw.text

        return HttpResponse(
            status_code=raw.status_code,
            headers=dict(raw.headers),
            body=body,
            elapsed_seconds=elapsed,
        )

    def close(self) -> None:
        """Release the underlying httpx.Client connections."""
        self._client.close()

    def __enter__(self) -> HttpxClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
