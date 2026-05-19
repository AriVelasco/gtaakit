"""HttpClient port.

An HttpClient sends an HttpRequest and returns the resulting
HttpResponse. Concrete implementations live in the adapters subpackage
(for instance, an adapter on top of the httpx library, or a stub for
unit tests). The port also exposes resource-management methods so that
the Runner can release connections when a suite finishes.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, runtime_checkable

from gtaakit.domain.http import HttpRequest, HttpResponse


@runtime_checkable
class HttpClient(Protocol):
    """Protocol for HTTP clients used by the Test Runner.

    Implementations may keep state (connection pools, default headers,
    base URL) and are expected to be reusable across many requests.
    The protocol supports both explicit close() and the context-manager
    protocol so that callers can choose the lifecycle they prefer.
    """

    def send(self, request: HttpRequest) -> HttpResponse:
        """Send an HTTP request and return the response.

        Args:
            request: The HttpRequest to send.

        Returns:
            The HttpResponse produced by the system under test, including
            the elapsed time measured by the implementation.
        """
        ...

    def close(self) -> None:
        """Release any resources held by the client.

        After calling close(), the client must not be used to send
        further requests.
        """
        ...

    def __enter__(self) -> HttpClient:
        """Enter the runtime context and return self."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the runtime context, releasing resources."""
        ...
