"""Validator that checks the HTTP status code of a response."""

from __future__ import annotations

from collections.abc import Iterable

from gtaakit.domain.http import HttpResponse
from gtaakit.domain.validation import ValidationResult


class StatusCodeValidator:
    """Validates that an HTTP response has an expected status code.

    Accepts either a single expected status code or a collection of
    acceptable codes. A response passes the validation if its status
    code matches any of the expected values.
    """

    def __init__(self, expected: int | Iterable[int]) -> None:
        """Build a StatusCodeValidator.

        Args:
            expected: A single int (e.g. 200) or an iterable of ints
                (e.g. [200, 201]) listing acceptable status codes.
        """
        if isinstance(expected, int):
            self._expected: frozenset[int] = frozenset({expected})
        else:
            self._expected = frozenset(expected)
        if not self._expected:
            raise ValueError("StatusCodeValidator requires at least one expected code.")

    def validate(self, response: HttpResponse) -> ValidationResult:
        """Compare the response status code to the expected set."""
        passed = response.status_code in self._expected
        if passed:
            detail: str | None = None
        else:
            expected_str = ", ".join(str(c) for c in sorted(self._expected))
            detail = f"expected status code in {{{expected_str}}}, got {response.status_code}"
        return ValidationResult(
            validator_name="status_code",
            passed=passed,
            detail=detail,
        )
