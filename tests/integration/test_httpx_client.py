"""Integration tests for the HttpxClient adapter.

These tests exercise the real httpx-based client against a local HTTP
server provided by pytest-httpserver. They live at the integration
level (Capítol 9, Nivell 2): no external network involved, but the
adapter does real HTTP over a real socket to a deterministic SUT
substitute.
"""

from __future__ import annotations

from pytest_httpserver import HTTPServer

from gtaakit.adapters.http.httpx_client import HttpxClient
from gtaakit.domain.http import HttpRequest
from gtaakit.ports.http_client import HttpClient


class TestHttpxClientBasicRequests:
    """Basic request/response handling."""

    def test_satisfies_http_client_protocol(self) -> None:
        client = HttpxClient()
        assert isinstance(client, HttpClient)
        client.close()

    def test_sends_get_and_parses_json_body(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request("/pet/1").respond_with_json({"id": 1, "name": "Rex"})

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(method="GET", url=httpserver.url_for("/pet/1"))
            )

        assert response.status_code == 200
        assert response.body == {"id": 1, "name": "Rex"}

    def test_sends_post_with_json_body(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request(
            "/pet", method="POST", json={"name": "Rex"}
        ).respond_with_json({"id": 42, "name": "Rex"}, status=201)

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(
                    method="POST",
                    url=httpserver.url_for("/pet"),
                    body={"name": "Rex"},
                )
            )

        assert response.status_code == 201
        assert response.body == {"id": 42, "name": "Rex"}

    def test_sends_query_params(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request(
            "/pet/findByStatus", query_string={"status": "available"}
        ).respond_with_json([{"id": 1}])

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(
                    method="GET",
                    url=httpserver.url_for("/pet/findByStatus"),
                    query_params={"status": "available"},
                )
            )

        assert response.status_code == 200
        assert response.body == [{"id": 1}]


class TestHttpxClientErrorResponses:
    """Handling of 4xx and 5xx responses (RF1)."""

    def test_handles_404_without_raising(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request("/pet/999").respond_with_json(
            {"error": "not found"}, status=404
        )

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(method="GET", url=httpserver.url_for("/pet/999"))
            )

        assert response.status_code == 404
        assert response.body == {"error": "not found"}

    def test_handles_500_without_raising(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request("/broken").respond_with_data(
            "Internal Server Error", status=500
        )

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(method="GET", url=httpserver.url_for("/broken"))
            )

        assert response.status_code == 500


class TestHttpxClientBodyParsing:
    """Body parsing based on Content-Type."""

    def test_parses_json_content_type(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request("/json").respond_with_json({"ok": True})

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(method="GET", url=httpserver.url_for("/json"))
            )

        assert isinstance(response.body, dict)
        assert response.body == {"ok": True}

    def test_returns_text_when_not_json(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request("/plain").respond_with_data(
            "hello world", content_type="text/plain"
        )

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(method="GET", url=httpserver.url_for("/plain"))
            )

        assert response.body == "hello world"

    def test_falls_back_to_text_on_invalid_json(self, httpserver: HTTPServer) -> None:
        # Server declares JSON content-type but returns invalid JSON.
        httpserver.expect_request("/broken-json").respond_with_data(
            "this is not json", content_type="application/json"
        )

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(method="GET", url=httpserver.url_for("/broken-json"))
            )

        # The client must not raise; it falls back to the raw text.
        assert response.status_code == 200
        assert response.body == "this is not json"


class TestHttpxClientHeaders:
    """Header propagation."""

    def test_sends_custom_headers(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request(
            "/secure",
            headers={"Authorization": "Bearer abc123"},
        ).respond_with_json({"ok": True})

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(
                    method="GET",
                    url=httpserver.url_for("/secure"),
                    headers={"Authorization": "Bearer abc123"},
                )
            )

        assert response.status_code == 200

    def test_default_headers_are_sent(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request(
            "/check",
            headers={"X-Trace": "abc"},
        ).respond_with_json({"ok": True})

        with HttpxClient(default_headers={"X-Trace": "abc"}) as client:
            response = client.send(
                HttpRequest(method="GET", url=httpserver.url_for("/check"))
            )

        assert response.status_code == 200


class TestHttpxClientLifecycle:
    """Resource management: explicit close and context manager."""

    def test_context_manager_releases_resources(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request("/ping").respond_with_json({"ok": True})

        with HttpxClient() as client:
            client.send(HttpRequest(method="GET", url=httpserver.url_for("/ping")))
        # No exception means __exit__ has run cleanly.

    def test_measures_elapsed_time(self, httpserver: HTTPServer) -> None:
        httpserver.expect_request("/quick").respond_with_json({"ok": True})

        with HttpxClient() as client:
            response = client.send(
                HttpRequest(method="GET", url=httpserver.url_for("/quick"))
            )

        assert response.elapsed_seconds > 0
        assert response.elapsed_seconds < 5  # Sanity bound for a local request.
