"""Manual end-to-end run of the gtaakit pieces, without the Runner.

This script wires together the adapters by hand to demonstrate the full
flow: build a request, send it, validate the response, and report the
outcome. It simulates what the Test Runner will eventually orchestrate.

Run with:  python examples/manual_run.py
"""

from __future__ import annotations

import time
from typing import Any

from gtaakit.adapters.http.httpx_client import HttpxClient
from gtaakit.adapters.reporters.console import ConsoleReporter
from gtaakit.adapters.validators.status_code import StatusCodeValidator
from gtaakit.domain.events import (
    SuiteFinished,
    SuiteStarted,
    TestFailed,
    TestPassed,
    TestStarted,
)
from gtaakit.domain.http import HttpRequest
from gtaakit.domain.test_case import TestCase, TestSuite
from gtaakit.domain.validation import ValidationResult

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"


def build_get_pet_1(_context: dict[str, Any]) -> HttpRequest:
    return HttpRequest(method="GET", url=f"{PETSTORE_BASE}/pet/1")


def build_get_missing_pet(_context: dict[str, Any]) -> HttpRequest:
    return HttpRequest(method="GET", url=f"{PETSTORE_BASE}/pet/999999999")


def build_suite() -> TestSuite:
    return TestSuite(
        name="Petstore smoke tests",
        description="Manual end-to-end demonstration",
        test_cases=[
            TestCase(
                id="get_pet_1",
                name="Get pet by id 1",
                tags=["pet", "smoke"],
                request_factory=build_get_pet_1,
                validators=[StatusCodeValidator(expected=200)],
            ),
            TestCase(
                id="get_missing_pet",
                name="Get nonexistent pet (expected to fail)",
                tags=["pet"],
                request_factory=build_get_missing_pet,
                validators=[StatusCodeValidator(expected=200)],
            ),
        ],
    )


def run(suite: TestSuite) -> None:
    """Simulate what the Test Runner will eventually do."""
    reporter = ConsoleReporter()
    suite_start = time.perf_counter()

    passed = failed = skipped = 0

    reporter.report(
        SuiteStarted(suite_name=suite.name, total_tests=len(suite.test_cases))
    )

    with HttpxClient() as client:
        for tc in suite.test_cases:
            reporter.report(TestStarted(test_id=tc.id, test_name=tc.name))

            context = tc.setup() if tc.setup else {}
            request = tc.request_factory(context)
            case_start = time.perf_counter()

            try:
                response = client.send(request)
                results: list[ValidationResult] = [
                    v.validate(response) for v in tc.validators
                ]
                case_elapsed = time.perf_counter() - case_start

                if all(r.passed for r in results):
                    passed += 1
                    reporter.report(
                        TestPassed(
                            test_id=tc.id,
                            test_name=tc.name,
                            elapsed_seconds=case_elapsed,
                            validation_results=results,
                        )
                    )
                else:
                    failed += 1
                    first_failure = next(r for r in results if not r.passed)
                    reporter.report(
                        TestFailed(
                            test_id=tc.id,
                            test_name=tc.name,
                            elapsed_seconds=case_elapsed,
                            validation_results=results,
                            failure_info=first_failure.detail or "validation failed",
                        )
                    )
            finally:
                if tc.teardown:
                    tc.teardown(context)

    suite_elapsed = time.perf_counter() - suite_start
    reporter.report(
        SuiteFinished(
            suite_name=suite.name,
            total_tests=len(suite.test_cases),
            passed=passed,
            failed=failed,
            skipped=skipped,
            elapsed_seconds=suite_elapsed,
        )
    )


if __name__ == "__main__":
    run(build_suite())
