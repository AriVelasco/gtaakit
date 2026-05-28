"""Test Runner: orchestrates the execution of a test suite.

The Runner coordinates the lifecycle of an execution. It receives its
collaborators (an HttpClient and one or more Reporters) by dependency
injection, so it depends only on the ports, never on concrete adapters.

For each test case it runs the setup, builds the request, sends it,
applies the chain of validators, and emits the corresponding execution
events. An unhandled exception in a single case is captured and turned
into a TestFailed event, so the rest of the suite keeps running.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from gtaakit.domain.events import (
    ExecutionEvent,
    SuiteFinished,
    SuiteStarted,
    TestFailed,
    TestPassed,
    TestStarted,
)
from gtaakit.domain.test_case import TestCase, TestSuite
from gtaakit.domain.validation import ValidationResult
from gtaakit.ports.http_client import HttpClient
from gtaakit.ports.reporter import Reporter


class TestRunner:
    """Orchestrates the execution of a TestSuite.

    The Runner is the architectural facade over the execution lifecycle.
    It does not implement HTTP, validation or reporting itself; it
    coordinates the collaborators it receives and emits execution events.
    """

    def __init__(self, http_client: HttpClient, reporters: Sequence[Reporter]) -> None:
        """Build a TestRunner.

        Args:
            http_client: The client used to send requests to the SUT.
            reporters: One or more reporters that consume execution events.
        """
        self._http_client = http_client
        self._reporters = list(reporters)

    def _emit(self, event: ExecutionEvent) -> None:
        """Send an event to every subscribed reporter."""
        for reporter in self._reporters:
            reporter.report(event)

    def run(self, suite: TestSuite) -> SuiteFinished:
        """Run a suite and return the final SuiteFinished event.

        Args:
            suite: The suite to execute.

        Returns:
            The SuiteFinished event summarising the run.
        """
        suite_start = time.perf_counter()
        passed = failed = skipped = 0

        self._emit(
            SuiteStarted(suite_name=suite.name, total_tests=len(suite.test_cases))
        )

        for test_case in suite.test_cases:
            outcome = self._run_case(test_case)
            if outcome == "passed":
                passed += 1
            elif outcome == "failed":
                failed += 1
            else:
                skipped += 1

        suite_elapsed = time.perf_counter() - suite_start
        finished = SuiteFinished(
            suite_name=suite.name,
            total_tests=len(suite.test_cases),
            passed=passed,
            failed=failed,
            skipped=skipped,
            elapsed_seconds=suite_elapsed,
        )
        self._emit(finished)
        return finished

    def _run_case(self, test_case: TestCase) -> str:
        """Run a single test case and emit its events.

        Returns:
            One of "passed", "failed" or "skipped".
        """
        self._emit(TestStarted(test_id=test_case.id, test_name=test_case.name))
        case_start = time.perf_counter()
        context: dict[str, Any] = {}

        try:
            if test_case.setup is not None:
                context = test_case.setup()

            request = test_case.request_factory(context)
            response = self._http_client.send(request)
            results: list[ValidationResult] = [
                validator.validate(response) for validator in test_case.validators
            ]
            case_elapsed = time.perf_counter() - case_start

            if all(result.passed for result in results):
                self._emit(
                    TestPassed(
                        test_id=test_case.id,
                        test_name=test_case.name,
                        elapsed_seconds=case_elapsed,
                        validation_results=results,
                    )
                )
                return "passed"

            first_failure = next(result for result in results if not result.passed)
            self._emit(
                TestFailed(
                    test_id=test_case.id,
                    test_name=test_case.name,
                    elapsed_seconds=case_elapsed,
                    validation_results=results,
                    failure_info=first_failure.detail or "validation failed",
                )
            )
            return "failed"

        except Exception as exc:
            case_elapsed = time.perf_counter() - case_start
            self._emit(
                TestFailed(
                    test_id=test_case.id,
                    test_name=test_case.name,
                    elapsed_seconds=case_elapsed,
                    validation_results=[],
                    failure_info=f"execution error: {type(exc).__name__}: {exc}",
                )
            )
            return "failed"

        finally:
            if test_case.teardown is not None:
                test_case.teardown(context)
