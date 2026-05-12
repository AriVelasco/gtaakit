"""HTTP request and response domain types.

These types model HTTP requests and responses as plain data, without
any logic tied to a specific HTTP client implementation. They are the
vocabulary used by the HttpClient port and its adapters.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HttpRequest(BaseModel):
    """Immutable representation of an HTTP request.

    Models the data of a single HTTP request to be sent to a system
    under test, independently of the HTTP client implementation that
    will eventually send it.
    """

    model_config = ConfigDict(frozen=True)

    method: str = Field(..., description="HTTP method (GET, POST, PUT, ...).")
    url: str = Field(..., description="Absolute URL of the request.")
    headers: dict[str, str] = Field(default_factory=dict)
    query_params: dict[str, str] = Field(default_factory=dict)
    body: Any | None = Field(default=None)
    timeout_seconds: float = Field(default=30.0, gt=0)


class HttpResponse(BaseModel):
    """Immutable representation of an HTTP response.

    Models the data of a single HTTP response received from a system
    under test, plus the elapsed time. Independent of the HTTP client
    implementation that produced it.
    """

    model_config = ConfigDict(frozen=True)

    status_code: int = Field(..., ge=100, le=599)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any | None = Field(default=None)
    elapsed_seconds: float = Field(..., ge=0)
