"""Unit tests for the HTTP domain types (HttpRequest, HttpResponse)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from gtaakit.domain.http import HttpRequest, HttpResponse


class TestHttpRequest:
    """Construction and validation of HttpRequest."""

    def test_minimal_request_uses_defaults(self) -> None:
        request = HttpRequest(method="GET", url="https://example.com")
        assert request.method == "GET"
        assert request.url == "https://example.com"
        assert request.headers == {}
        assert request.query_params == {}
        assert request.body is None
        assert request.timeout_seconds == 30.0

    def test_accepts_full_specification(self) -> None:
        request = HttpRequest(
            method="POST",
            url="https://example.com/items",
            headers={"Authorization": "Bearer token"},
            query_params={"page": "1"},
            body={"name": "thing"},
            timeout_seconds=5.0,
        )
        assert request.headers["Authorization"] == "Bearer token"
        assert request.query_params["page"] == "1"
        assert request.body == {"name": "thing"}
        assert request.timeout_seconds == 5.0

    def test_rejects_non_positive_timeout(self) -> None:
        with pytest.raises(ValidationError):
            HttpRequest(method="GET", url="https://example.com", timeout_seconds=0.0)

    def test_is_immutable(self) -> None:
        request = HttpRequest(method="GET", url="https://example.com")
        with pytest.raises(ValidationError):
            request.method = "POST"  # type: ignore[misc]


class TestHttpResponse:
    """Construction and validation of HttpResponse."""

    def test_minimal_response(self) -> None:
        response = HttpResponse(status_code=200, elapsed_seconds=0.1)
        assert response.status_code == 200
        assert response.headers == {}
        assert response.body is None
        assert response.elapsed_seconds == 0.1

    def test_rejects_status_code_below_range(self) -> None:
        with pytest.raises(ValidationError):
            HttpResponse(status_code=99, elapsed_seconds=0.1)

    def test_rejects_status_code_above_range(self) -> None:
        with pytest.raises(ValidationError):
            HttpResponse(status_code=600, elapsed_seconds=0.1)

    def test_rejects_negative_elapsed(self) -> None:
        with pytest.raises(ValidationError):
            HttpResponse(status_code=200, elapsed_seconds=-1.0)

    def test_is_immutable(self) -> None:
        response = HttpResponse(status_code=200, elapsed_seconds=0.1)
        with pytest.raises(ValidationError):
            response.status_code = 404  # type: ignore[misc]
