"""Unit tests for execute_case (the pytest-independent case executor)."""

from __future__ import annotations

import pytest

from gtaakit.core.case_execution import execute_case
from gtaakit.domain.http import HttpRequest, HttpResponse
from gtaakit.domain.test_case import TestCase
from gtaakit.domain.validation import ValidationResult


class _StubClient:
    """HttpClient double that returns a canned response and records calls."""

    def __init__(self, response: HttpResponse) -> None:
        self._response = response
        self.sent_requests: list[HttpRequest] = []

    def send(self, request: HttpRequest) -> HttpResponse:
        self.sent_requests.append(request)
        return self._response

    def close(self) -> None:
        pass

    def __enter__(self) -> "_StubClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class _PassingValidator:
    def validate(self, response: HttpResponse) -> ValidationResult:
        return ValidationResult(validator_name="stub_ok", passed=True)


class _FailingValidator:
    def validate(self, response: HttpResponse) -> ValidationResult:
        return ValidationResult(validator_name="stub_bad", passed=False, detail="nope")


def _request(_ctx: dict[str, object]) -> HttpRequest:
    return HttpRequest(method="GET", url="https://example.com/x")


def _ok_response() -> HttpResponse:
    return HttpResponse(status_code=200, elapsed_seconds=0.01)


class TestExecuteCase:
    """Execution of the active part of a test case."""

    def test_returns_validation_results(self) -> None:
        client = _StubClient(_ok_response())
        case = TestCase(
            id="c1",
            name="case 1",
            request_factory=_request,
            validators=[_PassingValidator(), _FailingValidator()],
        )

        results = execute_case(case, client)

        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False

    def test_sends_request_from_factory(self) -> None:
        client = _StubClient(_ok_response())
        case = TestCase(id="c1", name="case 1", request_factory=_request)

        execute_case(case, client)

        assert len(client.sent_requests) == 1
        assert client.sent_requests[0].url == "https://example.com/x"

    def test_setup_context_reaches_request_factory(self) -> None:
        client = _StubClient(_ok_response())
        seen: dict[str, object] = {}

        def setup() -> dict[str, object]:
            return {"token": "secret"}

        def factory(ctx: dict[str, object]) -> HttpRequest:
            seen.update(ctx)
            return HttpRequest(method="GET", url="https://example.com/x")

        case = TestCase(id="c1", name="case 1", request_factory=factory, setup=setup)

        execute_case(case, client)

        assert seen == {"token": "secret"}

    def test_teardown_runs_on_success(self) -> None:
        client = _StubClient(_ok_response())
        torn_down: list[dict[str, object]] = []

        case = TestCase(
            id="c1",
            name="case 1",
            request_factory=_request,
            teardown=lambda ctx: torn_down.append(ctx),
        )

        execute_case(case, client)

        assert len(torn_down) == 1

    def test_teardown_runs_even_when_client_raises(self) -> None:
        torn_down: list[dict[str, object]] = []

        class _RaisingClient:
            def send(self, request: HttpRequest) -> HttpResponse:
                raise ConnectionError("boom")

            def close(self) -> None:
                pass

            def __enter__(self) -> "_RaisingClient":
                return self

            def __exit__(self, *args: object) -> None:
                self.close()

        case = TestCase(
            id="c1",
            name="case 1",
            request_factory=_request,
            teardown=lambda ctx: torn_down.append(ctx),
        )

        with pytest.raises(ConnectionError):
            execute_case(case, _RaisingClient())

        # teardown must still have run despite the exception.
        assert len(torn_down) == 1

    def test_exception_propagates(self) -> None:
        class _RaisingClient:
            def send(self, request: HttpRequest) -> HttpResponse:
                raise ConnectionError("boom")

            def close(self) -> None:
                pass

            def __enter__(self) -> "_RaisingClient":
                return self

            def __exit__(self, *args: object) -> None:
                self.close()

        case = TestCase(id="c1", name="case 1", request_factory=_request)

        with pytest.raises(ConnectionError):
            execute_case(case, _RaisingClient())
