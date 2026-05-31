"""Unit tests for the HeaderValidator."""

from __future__ import annotations

import pytest
from gtaakit.adapters.validators.header import HeaderValidator

from gtaakit.domain.http import HttpResponse
from gtaakit.ports.validator import Validator


def _response(headers: dict[str, str]) -> HttpResponse:
    return HttpResponse(status_code=200, headers=headers, elapsed_seconds=0.01)


class TestHeaderValidatorPresence:
    """Presence mode: the header must exist."""

    def test_satisfies_validator_protocol(self) -> None:
        validator = HeaderValidator("Content-Type")
        assert isinstance(validator, Validator)

    def test_passes_when_header_present(self) -> None:
        validator = HeaderValidator("Content-Type")
        result = validator.validate(_response({"Content-Type": "application/json"}))
        assert result.passed is True

    def test_fails_when_header_absent(self) -> None:
        validator = HeaderValidator("Content-Type")
        result = validator.validate(_response({"X-Other": "value"}))
        assert result.passed is False
        assert result.detail is not None
        assert "absent" in result.detail

    def test_lookup_is_case_insensitive(self) -> None:
        validator = HeaderValidator("Content-Type")
        result = validator.validate(_response({"content-type": "application/json"}))
        assert result.passed is True


class TestHeaderValidatorExactValue:
    """Exact value mode."""

    def test_passes_when_value_matches(self) -> None:
        validator = HeaderValidator("Content-Type", expected_value="application/json")
        result = validator.validate(_response({"Content-Type": "application/json"}))
        assert result.passed is True

    def test_fails_when_value_differs(self) -> None:
        validator = HeaderValidator("Content-Type", expected_value="application/json")
        result = validator.validate(_response({"Content-Type": "text/html"}))
        assert result.passed is False
        assert result.detail is not None
        assert "text/html" in result.detail


class TestHeaderValidatorPattern:
    """Regular expression mode."""

    def test_passes_when_pattern_matches(self) -> None:
        validator = HeaderValidator("Content-Type", pattern=r"application/json")
        result = validator.validate(
            _response({"Content-Type": "application/json; charset=utf-8"})
        )
        assert result.passed is True

    def test_fails_when_pattern_does_not_match(self) -> None:
        validator = HeaderValidator("Content-Type", pattern=r"^application/xml")
        result = validator.validate(_response({"Content-Type": "application/json"}))
        assert result.passed is False
        assert result.detail is not None
        assert "does not match" in result.detail


class TestHeaderValidatorConfiguration:
    """Defensive configuration checks."""

    def test_rejects_combined_value_and_pattern(self) -> None:
        with pytest.raises(ValueError):
            HeaderValidator(
                "Content-Type", expected_value="application/json", pattern=r"app.*"
            )
