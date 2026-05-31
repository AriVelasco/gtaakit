"""JSON Schema validator adapter.

Validates the body of an HttpResponse against a JSON Schema. This is the
structural verification required by RF4: it checks that the response body
has the expected shape (required fields, types, nested structure) beyond
the mere status code.
"""

from __future__ import annotations

from typing import Any

import jsonschema

from gtaakit.domain.http import HttpResponse
from gtaakit.domain.validation import ValidationResult

_VALIDATOR_NAME = "json_schema"


class JsonSchemaValidator:
    """Validates a response body against a JSON Schema."""

    def __init__(self, schema: dict[str, Any]) -> None:
        """Build a JsonSchemaValidator.

        Args:
            schema: A JSON Schema (as a Python dict) describing the
                expected structure of the response body.
        """
        self._schema = schema

    def validate(self, response: HttpResponse) -> ValidationResult:
        """Validate the response body against the configured schema.

        A body that is not a JSON document (for example plain text or
        None) cannot be validated against a schema and is reported as a
        failure with an explanatory detail, rather than raising.
        """
        body = response.body
        if not isinstance(body, (dict, list)):
            return ValidationResult(
                validator_name=_VALIDATOR_NAME,
                passed=False,
                detail=(
                    f"body is not a JSON document "
                    f"(got {type(body).__name__}), cannot validate against schema"
                ),
            )

        try:
            jsonschema.validate(instance=body, schema=self._schema)
        except jsonschema.ValidationError as exc:
            return ValidationResult(
                validator_name=_VALIDATOR_NAME,
                passed=False,
                detail=f"schema validation failed: {exc.message}",
            )
        except jsonschema.SchemaError as exc:
            return ValidationResult(
                validator_name=_VALIDATOR_NAME,
                passed=False,
                detail=f"invalid schema: {exc.message}",
            )

        return ValidationResult(validator_name=_VALIDATOR_NAME, passed=True)
