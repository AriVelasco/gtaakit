"""Manual end-to-end run using the TestRunner against Petstore.

This script builds a suite of TestCase definitions, configures the
adapters, and delegates execution to the TestRunner. It demonstrates
the full system in action against a real public API.

Run with:  python examples/manual_run.py
"""

from __future__ import annotations

from typing import Any

from gtaakit.adapters.http.httpx_client import HttpxClient
from gtaakit.adapters.reporters.console import ConsoleReporter
from gtaakit.adapters.validators.status_code import StatusCodeValidator
from gtaakit.core.runner import TestRunner
from gtaakit.domain.http import HttpRequest
from gtaakit.domain.test_case import TestCase, TestSuite

PETSTORE_BASE = "https://petstore3.swagger.io/api/v3"


def build_get_pet_1(_context: dict[str, Any]) -> HttpRequest:
    return HttpRequest(method="GET", url=f"{PETSTORE_BASE}/pet/1")


def build_get_missing_pet(_context: dict[str, Any]) -> HttpRequest:
    return HttpRequest(method="GET", url=f"{PETSTORE_BASE}/pet/999999999")


def build_suite() -> TestSuite:
    return TestSuite(
        name="Petstore smoke tests",
        description="End-to-end demonstration",
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


def main() -> int:
    """Configure the adapters, build the suite, and run it.

    Returns:
        An exit code: 0 if every test passed, 1 otherwise.
    """
    suite = build_suite()
    reporter = ConsoleReporter()
    with HttpxClient() as client:
        runner = TestRunner(http_client=client, reporters=[reporter])
        result = runner.run(suite)
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
