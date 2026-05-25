"""Unit tests for the StatusCodeValidator."""

from __future__ import annotations

import pytest

from gtaakit.adapters.validators.status_code import StatusCodeValidator
from gtaakit.domain.http import HttpResponse
from gtaakit.ports.validator import Validator


def _response(status_code: int) -> HttpResponse:
    """Build a minimal HttpResponse with the given status code."""
    return HttpResponse(status_code=status_code, elapsed_seconds=0.0)


class TestStatusCodeValidator:
    """Behaviour of the status code validator."""

    def test_satisfies_validator_protocol(self) -> None:
        validator = StatusCodeValidator(expected=200)
        assert isinstance(validator, Validator)

    def test_passes_when_status_matches_single_expected(self) -> None:
        validator = StatusCodeValidator(expected=200)
        result = validator.validate(_response(200))
        assert result.passed is True
        assert result.detail is None

    def test_fails_when_status_does_not_match(self) -> None:
        validator = StatusCodeValidator(expected=200)
        result = validator.validate(_response(404))
        assert result.passed is False
        assert result.detail is not None
        assert "404" in result.detail
        assert "200" in result.detail

    def test_passes_when_status_in_collection(self) -> None:
        validator = StatusCodeValidator(expected=[200, 201])
        assert validator.validate(_response(200)).passed is True
        assert validator.validate(_response(201)).passed is True

    def test_fails_when_status_outside_collection(self) -> None:
        validator = StatusCodeValidator(expected=[200, 201])
        result = validator.validate(_response(500))
        assert result.passed is False

    def test_deduplicates_repeated_expected_codes(self) -> None:
        # Passing duplicates must not change behaviour.
        validator = StatusCodeValidator(expected=[200, 200, 200])
        assert validator.validate(_response(200)).passed is True
        assert validator.validate(_response(404)).passed is False

    def test_result_carries_validator_name(self) -> None:
        validator = StatusCodeValidator(expected=200)
        result = validator.validate(_response(200))
        assert result.validator_name == "status_code"

    def test_raises_when_expected_is_empty(self) -> None:
        with pytest.raises(ValueError):
            StatusCodeValidator(expected=[])
