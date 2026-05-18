"""Execution event domain types.

These types model the events emitted by the Test Runner during the
lifecycle of a test execution. The Reporter consumes them as an
observable stream. Each subtype carries only the data relevant to
its event.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from gtaakit.domain.validation import ValidationResult


class ExecutionEvent(BaseModel):
    """Base type for all execution events.

    Concrete events extend this base with their own specific fields.
    The base itself is not intended to be instantiated directly.
    """

    model_config = ConfigDict(frozen=True)


class SuiteStarted(ExecutionEvent):
    """Emitted when a test suite execution begins."""

    suite_name: str = Field(..., description="Name of the suite being started.")
    total_tests: int = Field(
        ..., ge=0, description="Total number of tests in the suite."
    )


class TestStarted(ExecutionEvent):
    """Emitted when an individual test case begins execution."""

    test_id: str = Field(..., description="Unique identifier of the test case.")
    test_name: str = Field(..., description="Human-readable name of the test case.")


class TestPassed(ExecutionEvent):
    """Emitted when an individual test case completes successfully."""

    test_id: str
    test_name: str
    elapsed_seconds: float = Field(..., ge=0)
    validation_results: list[ValidationResult] = Field(default_factory=list)


class TestFailed(ExecutionEvent):
    """Emitted when an individual test case fails."""

    test_id: str
    test_name: str
    elapsed_seconds: float = Field(..., ge=0)
    validation_results: list[ValidationResult] = Field(default_factory=list)
    failure_info: str = Field(
        ..., description="Human-readable explanation of the failure."
    )


class TestSkipped(ExecutionEvent):
    """Emitted when an individual test case is skipped."""

    test_id: str
    test_name: str
    reason: str = Field(..., description="Why the test was skipped.")


class SuiteFinished(ExecutionEvent):
    """Emitted when a test suite execution ends."""

    suite_name: str
    total_tests: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    skipped: int = Field(..., ge=0)
    elapsed_seconds: float = Field(..., ge=0)
