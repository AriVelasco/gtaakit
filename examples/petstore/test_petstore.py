"""Example gtaakit suite against the public Swagger Petstore API.

This file demonstrates the declarative use of gtaakit through the pytest
plugin. It declares a list of TestCase objects in GTAAKIT_CASES; the
plugin discovers them and generates one pytest test per case. Each case
is executed by execute_case using the gtaakit_client fixture, and the
host test fails (in pytest terms) if any validator does not pass.

Run it from the repository root with:

    pytest examples/petstore -p gtaakit -v

The Petstore API is occasionally unstable (sporadic 500s); the cases are
chosen to exercise the three validation types against its most stable
endpoints.
"""

from __future__ import annotations

import pytest

from gtaakit.adapters.validators.header import HeaderValidator
from gtaakit.adapters.validators.json_schema import JsonSchemaValidator
from gtaakit.adapters.validators.status_code import StatusCodeValidator
from gtaakit.core.case_execution import execute_case
from gtaakit.domain.http import HttpRequest
from gtaakit.domain.test_case import TestCase

_BASE = "https://petstore3.swagger.io/api/v3"

_PET_SCHEMA = {
    "type": "object",
    "required": ["id", "name"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
    },
}


def _get_pet_2(_ctx: dict[str, object]) -> HttpRequest:
    return HttpRequest(method="GET", url=f"{_BASE}/pet/2")


def _get_pet_invalid_id(_ctx: dict[str, object]) -> HttpRequest:
    return HttpRequest(method="GET", url=f"{_BASE}/pet/abc")


def _get_unknown_route(_ctx: dict[str, object]) -> HttpRequest:
    return HttpRequest(method="GET", url=f"{_BASE}/nonexistent")


GTAAKIT_CASES = [
    TestCase(
        id="get_pet_by_id",
        name="GET /pet/2 returns a valid pet",
        request_factory=_get_pet_2,
        validators=[
            StatusCodeValidator(expected=200),
            JsonSchemaValidator(schema=_PET_SCHEMA),
            HeaderValidator("Content-Type", pattern=r"application/json"),
        ],
    ),
    TestCase(
        id="get_pet_invalid_id",
        name="GET /pet/abc returns 400 for a non-numeric id",
        request_factory=_get_pet_invalid_id,
        validators=[
            StatusCodeValidator(expected=400),
        ],
    ),
    TestCase(
        id="get_unknown_route",
        name="GET an unknown route returns 404",
        request_factory=_get_unknown_route,
        validators=[
            StatusCodeValidator(expected=404),
        ],
    ),
]


def test_gtaakit(gtaakit_case: TestCase, gtaakit_client: object) -> None:
    """Host test: execute one gtaakit case and fail if any validator fails."""
    results = execute_case(gtaakit_case, gtaakit_client)  # type: ignore[arg-type]
    failures = [r for r in results if not r.passed]
    if failures:
        details = "; ".join(f"[{r.validator_name}] {r.detail}" for r in failures)
        pytest.fail(f"validation failed: {details}", pytrace=False)
