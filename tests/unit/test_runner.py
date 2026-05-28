"""Unit tests for the TestRunner.

The Runner is tested in isolation using test doubles: a stub HttpClient
that returns predefined responses, and a spy Reporter that records the
events it receives. This is made possible by the dependency injection
of the Runner (ADR-004).
"""

from __future__ import annotations

from typing import Any

from gtaakit.core.runner import TestRunner
from gtaakit.domain.events import (
    ExecutionEvent,
    SuiteFinished,
    SuiteStarted,
    TestFailed,
    TestPassed,
    TestStarted,
)
from gtaakit.domain.http import HttpRequest, HttpResponse
from gtaakit.domain.test_case import TestCase, TestSuite
from gtaakit.domain.validation import ValidationResult


class StubHttpClient:
    """An HttpClient stub that returns a fixed response.

    Records the requests it receives so tests can inspect them.
    """

    def __init__(self, response: HttpResponse) -> None:
        self._response = response
        self.sent_requests: list[HttpRequest] = []
        self.closed = False

    def send(self, request: HttpRequest) -> HttpResponse:
        self.sent_requests.append(request)
        return self._response

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> StubHttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class RaisingHttpClient:
    """An HttpClient stub that always raises, to test error handling."""

    def send(self, request: HttpRequest) -> HttpResponse:
        raise ConnectionError("simulated network failure")

    def close(self) -> None:
        pass

    def __enter__(self) -> RaisingHttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        pass


class SpyReporter:
    """A Reporter spy that records every event it receives."""

    def __init__(self) -> None:
        self.events: list[ExecutionEvent] = []

    def report(self, event: ExecutionEvent) -> None:
        self.events.append(event)


def _passing_validator_response() -> HttpResponse:
    return HttpResponse(status_code=200, elapsed_seconds=0.01)


class _AlwaysPasses:
    def validate(self, response: HttpResponse) -> ValidationResult:
        return ValidationResult(validator_name="always_passes", passed=True)


class _AlwaysFails:
    def validate(self, response: HttpResponse) -> ValidationResult:
        return ValidationResult(
            validator_name="always_fails", passed=False, detail="deliberate failure"
        )


def _build_request(_context: dict[str, Any]) -> HttpRequest:
    return HttpRequest(method="GET", url="https://example.com/resource")


class TestRunnerHappyPath:
    """A suite where every case passes."""

    def test_passing_case_emits_test_passed(self) -> None:
        client = StubHttpClient(_passing_validator_response())
        spy = SpyReporter()
        runner = TestRunner(http_client=client, reporters=[spy])

        suite = TestSuite(
            name="ok suite",
            test_cases=[
                TestCase(
                    id="c1",
                    name="A passing case",
                    request_factory=_build_request,
                    validators=[_AlwaysPasses()],
                )
            ],
        )
        result = runner.run(suite)

        assert result.passed == 1
        assert result.failed == 0
        event_types = [type(e) for e in spy.events]
        assert SuiteStarted in event_types
        assert TestStarted in event_types
        assert TestPassed in event_types
        assert SuiteFinished in event_types


class TestRunnerValidationFailure:
    """A suite where a case fails validation."""

    def test_failing_validation_emits_test_failed(self) -> None:
        client = StubHttpClient(_passing_validator_response())
        spy = SpyReporter()
        runner = TestRunner(http_client=client, reporters=[spy])

        suite = TestSuite(
            name="failing suite",
            test_cases=[
                TestCase(
                    id="c1",
                    name="A failing case",
                    request_factory=_build_request,
                    validators=[_AlwaysFails()],
                )
            ],
        )
        result = runner.run(suite)

        assert result.failed == 1
        failed_events = [e for e in spy.events if isinstance(e, TestFailed)]
        assert len(failed_events) == 1
        assert "deliberate failure" in failed_events[0].failure_info


class TestRunnerExecutionError:
    """A suite where sending the request raises an unhandled exception."""

    def test_execution_error_is_captured_as_failure(self) -> None:
        client = RaisingHttpClient()
        spy = SpyReporter()
        runner = TestRunner(http_client=client, reporters=[spy])

        suite = TestSuite(
            name="error suite",
            test_cases=[
                TestCase(
                    id="c1",
                    name="A case that errors",
                    request_factory=_build_request,
                    validators=[_AlwaysPasses()],
                )
            ],
        )
        result = runner.run(suite)

        assert result.failed == 1
        failed_events = [e for e in spy.events if isinstance(e, TestFailed)]
        assert len(failed_events) == 1
        assert "execution error" in failed_events[0].failure_info
        assert "ConnectionError" in failed_events[0].failure_info


class TestRunnerTeardown:
    """Teardown is always executed, even on failure."""

    def test_teardown_runs_on_success(self) -> None:
        client = StubHttpClient(_passing_validator_response())
        spy = SpyReporter()
        runner = TestRunner(http_client=client, reporters=[spy])

        teardown_calls: list[dict[str, Any]] = []

        suite = TestSuite(
            name="teardown suite",
            test_cases=[
                TestCase(
                    id="c1",
                    name="With teardown",
                    request_factory=_build_request,
                    validators=[_AlwaysPasses()],
                    setup=lambda: {"created_id": 42},
                    teardown=lambda ctx: teardown_calls.append(ctx),
                )
            ],
        )
        runner.run(suite)

        assert len(teardown_calls) == 1
        assert teardown_calls[0] == {"created_id": 42}

    def test_teardown_runs_on_execution_error(self) -> None:
        client = RaisingHttpClient()
        spy = SpyReporter()
        runner = TestRunner(http_client=client, reporters=[spy])

        teardown_calls: list[dict[str, Any]] = []

        suite = TestSuite(
            name="teardown error suite",
            test_cases=[
                TestCase(
                    id="c1",
                    name="Errors but has teardown",
                    request_factory=_build_request,
                    validators=[_AlwaysPasses()],
                    teardown=lambda ctx: teardown_calls.append(ctx),
                )
            ],
        )
        runner.run(suite)

        assert len(teardown_calls) == 1


class TestRunnerMultipleReporters:
    """Every reporter receives every event."""

    def test_all_reporters_receive_events(self) -> None:
        client = StubHttpClient(_passing_validator_response())
        spy_a = SpyReporter()
        spy_b = SpyReporter()
        runner = TestRunner(http_client=client, reporters=[spy_a, spy_b])

        suite = TestSuite(
            name="multi reporter suite",
            test_cases=[
                TestCase(
                    id="c1",
                    name="A case",
                    request_factory=_build_request,
                    validators=[_AlwaysPasses()],
                )
            ],
        )
        runner.run(suite)

        assert len(spy_a.events) == len(spy_b.events)
        assert len(spy_a.events) > 0


class TestRunnerSuiteContinuesAfterFailure:
    """A failing case does not stop the rest of the suite (RNF7)."""

    def test_suite_runs_all_cases_despite_failure(self) -> None:
        client = RaisingHttpClient()
        spy = SpyReporter()
        runner = TestRunner(http_client=client, reporters=[spy])

        suite = TestSuite(
            name="resilient suite",
            test_cases=[
                TestCase(
                    id="c1",
                    name="First (errors)",
                    request_factory=_build_request,
                    validators=[_AlwaysPasses()],
                ),
                TestCase(
                    id="c2",
                    name="Second (errors)",
                    request_factory=_build_request,
                    validators=[_AlwaysPasses()],
                ),
            ],
        )
        result = runner.run(suite)

        assert result.total_tests == 2
        assert result.failed == 2
        started_events = [e for e in spy.events if isinstance(e, TestStarted)]
        assert len(started_events) == 2
