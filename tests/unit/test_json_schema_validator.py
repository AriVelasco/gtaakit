"""Unit tests for the JsonSchemaValidator."""

from __future__ import annotations

from gtaakit.adapters.validators.json_schema import JsonSchemaValidator
from gtaakit.domain.http import HttpResponse
from gtaakit.ports.validator import Validator

_PET_SCHEMA = {
    "type": "object",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
    },
}


def _response(body: object) -> HttpResponse:
    return HttpResponse(status_code=200, body=body, elapsed_seconds=0.01)


class TestJsonSchemaValidator:
    """Structural validation of response bodies against a JSON Schema."""

    def test_satisfies_validator_protocol(self) -> None:
        validator = JsonSchemaValidator(schema=_PET_SCHEMA)
        assert isinstance(validator, Validator)

    def test_passes_when_body_matches_schema(self) -> None:
        validator = JsonSchemaValidator(schema=_PET_SCHEMA)
        result = validator.validate(_response({"id": 1, "name": "Rex"}))
        assert result.passed is True
        assert result.validator_name == "json_schema"

    def test_fails_when_required_field_missing(self) -> None:
        validator = JsonSchemaValidator(schema=_PET_SCHEMA)
        result = validator.validate(_response({"id": 1}))
        assert result.passed is False
        assert result.detail is not None
        assert "name" in result.detail

    def test_fails_when_field_has_wrong_type(self) -> None:
        validator = JsonSchemaValidator(schema=_PET_SCHEMA)
        result = validator.validate(_response({"id": "not-an-int", "name": "Rex"}))
        assert result.passed is False

    def test_validates_array_body(self) -> None:
        array_schema = {"type": "array", "items": {"type": "integer"}}
        validator = JsonSchemaValidator(schema=array_schema)
        result = validator.validate(_response([1, 2, 3]))
        assert result.passed is True

    def test_fails_when_body_is_not_json(self) -> None:
        validator = JsonSchemaValidator(schema=_PET_SCHEMA)
        result = validator.validate(_response("plain text body"))
        assert result.passed is False
        assert result.detail is not None
        assert "not a JSON document" in result.detail

    def test_fails_when_body_is_none(self) -> None:
        validator = JsonSchemaValidator(schema=_PET_SCHEMA)
        result = validator.validate(_response(None))
        assert result.passed is False

    def test_reports_invalid_schema(self) -> None:
        # "type": "nonsense" is not a valid JSON Schema type.
        bad_schema = {"type": "nonsense"}
        validator = JsonSchemaValidator(schema=bad_schema)
        result = validator.validate(_response({"id": 1, "name": "Rex"}))
        assert result.passed is False
        assert result.detail is not None
        assert "invalid schema" in result.detail
