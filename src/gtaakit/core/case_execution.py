"""Active execution of a single TestCase, decoupled from pytest.

This module holds the logic that runs the "active" part of a TestCase:
setup, building the request, sending it, and applying the validators.
Unlike the TestRunner (which captures exceptions so a suite can continue,
RNF7), this function lets exceptions from setup or the HTTP client
propagate, so that the surrounding execution engine (pytest, in the
plugin path) can treat them as errors. Only teardown is guaranteed to
run, via a finally block.
"""

from __future__ import annotations

from gtaakit.domain.test_case import TestCase
from gtaakit.domain.validation import ValidationResult
from gtaakit.ports.http_client import HttpClient


def execute_case(test_case: TestCase, client: HttpClient) -> list[ValidationResult]:
    """Run the active part of a test case and return the validation results.

    Args:
        test_case: The case to execute.
        client: The HTTP client used to send the request.

    Returns:
        The list of ValidationResult produced by the case's validators.

    Raises:
        Any exception raised by setup, the request factory, or the HTTP
        client is allowed to propagate; teardown still runs.
    """
    context: dict[str, object] = {}
    try:
        if test_case.setup is not None:
            context = test_case.setup()

        request = test_case.request_factory(context)
        response = client.send(request)
        return [validator.validate(response) for validator in test_case.validators]
    finally:
        if test_case.teardown is not None:
            test_case.teardown(context)
