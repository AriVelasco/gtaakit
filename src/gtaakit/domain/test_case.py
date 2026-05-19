"""TestCase and TestSuite domain types.

A TestCase is the minimal executable unit: it produces an HTTP request,
sends it through an HttpClient, and validates the response with a chain
of validators. Optional setup and teardown callbacks support test
isolation and cleanup (e.g. creating an entity before the test and
removing it afterwards).

A TestSuite is a logical grouping of TestCase instances that share
configuration and lifecycle.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from gtaakit.domain.http import HttpRequest
from gtaakit.ports.validator import Validator


class TestCase(BaseModel):
    """Definition of a single test case against an API endpoint.

    The request is built lazily through a factory so that values
    produced by the setup callback (for instance, an authentication
    token or a freshly created resource ID) can be incorporated into
    the request at execution time.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str = Field(
        ..., description="Unique identifier of the test case within its suite."
    )
    name: str = Field(..., description="Human-readable name shown in reports.")
    tags: list[str] = Field(
        default_factory=list, description="Labels used for filtering at execution time."
    )
    request_factory: Callable[[dict[str, Any]], HttpRequest] = Field(
        ...,
        description="Callable that builds the HttpRequest from a context dict produced by setup.",
    )
    validators: list[Validator] = Field(
        default_factory=list,
        description="Validators applied to the response in the order of the list.",
    )
    setup: Callable[[], dict[str, Any]] | None = Field(
        default=None,
        description="Optional callback executed before the request; returns the context dict.",
    )
    teardown: Callable[[dict[str, Any]], None] | None = Field(
        default=None,
        description="Optional callback executed after the test; receives the same context dict.",
    )


class TestSuite(BaseModel):
    """Logical grouping of test cases that share configuration and lifecycle."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Name of the suite shown in reports.")
    description: str | None = Field(default=None)
    tags: list[str] = Field(
        default_factory=list,
        description="Suite-level tags inherited by all its test cases.",
    )
    test_cases: list[TestCase] = Field(default_factory=list)
