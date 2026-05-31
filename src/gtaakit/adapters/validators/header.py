"""Header validator adapter.

Validates a single response header by one of three modes (RF4):
presence (the header exists), exact value, or regular expression match.
HTTP header names are case-insensitive, so the lookup ignores case.
"""

from __future__ import annotations

import re

from gtaakit.domain.http import HttpResponse
from gtaakit.domain.validation import ValidationResult

_VALIDATOR_NAME = "header"


class HeaderValidator:
    """Validates a single header by presence, exact value, or pattern."""

    def __init__(
        self,
        header_name: str,
        *,
        expected_value: str | None = None,
        pattern: str | None = None,
    ) -> None:
        """Build a HeaderValidator.

        Args:
            header_name: Name of the header to validate (case-insensitive).
            expected_value: If given, the header value must equal this exactly.
            pattern: If given, the header value must match this regular
                expression (using re.search).

        Raises:
            ValueError: If both expected_value and pattern are given, since
                the two modes are mutually exclusive.
        """
        if expected_value is not None and pattern is not None:
            raise ValueError(
                "expected_value and pattern are mutually exclusive; provide at most one"
            )
        self._header_name = header_name
        self._expected_value = expected_value
        self._pattern = re.compile(pattern) if pattern is not None else None

    def validate(self, response: HttpResponse) -> ValidationResult:
        """Validate the configured header against the response."""
        actual_value = self._find_header(response.headers)

        if actual_value is None:
            return ValidationResult(
                validator_name=_VALIDATOR_NAME,
                passed=False,
                detail=f"header '{self._header_name}' is absent",
            )

        # Presence mode: header exists, nothing more to check.
        if self._expected_value is None and self._pattern is None:
            return ValidationResult(validator_name=_VALIDATOR_NAME, passed=True)

        # Exact value mode.
        if self._expected_value is not None:
            if actual_value == self._expected_value:
                return ValidationResult(validator_name=_VALIDATOR_NAME, passed=True)
            return ValidationResult(
                validator_name=_VALIDATOR_NAME,
                passed=False,
                detail=(
                    f"header '{self._header_name}' expected "
                    f"'{self._expected_value}', got '{actual_value}'"
                ),
            )

        # Pattern mode.
        if self._pattern is not None:
            if self._pattern.search(actual_value) is not None:
                return ValidationResult(validator_name=_VALIDATOR_NAME, passed=True)
            return ValidationResult(
                validator_name=_VALIDATOR_NAME,
                passed=False,
                detail=(
                    f"header '{self._header_name}' value '{actual_value}' "
                    f"does not match pattern '{self._pattern.pattern}'"
                ),
            )

        # Unreachable, but keeps the type checker satisfied.
        return ValidationResult(  # pragma: no cover
            validator_name=_VALIDATOR_NAME, passed=True
        )

    def _find_header(self, headers: dict[str, str]) -> str | None:
        """Find a header value case-insensitively, returning None if absent."""
        target = self._header_name.lower()
        for name, value in headers.items():
            if name.lower() == target:
                return value
        return None
