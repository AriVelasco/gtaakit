"""Validator port.

A Validator inspects an HttpResponse and produces a ValidationResult.
Concrete validators (status code, headers, JSON schema, body content)
live in the adapters subpackage as classes that satisfy this protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gtaakit.domain.http import HttpResponse
from gtaakit.domain.validation import ValidationResult


@runtime_checkable
class Validator(Protocol):
    """Protocol for response validators.

    Any class with a `validate(response)` method returning a
    ValidationResult satisfies this protocol, regardless of explicit
    inheritance. This enables loose coupling between the core and
    concrete validator implementations.
    """

    def validate(self, response: HttpResponse) -> ValidationResult:
        """Inspect a response and return the validation outcome.

        Args:
            response: The HttpResponse to validate.

        Returns:
            A ValidationResult indicating whether the response passed
            this validator's criteria and, optionally, why it failed.
        """
        ...
