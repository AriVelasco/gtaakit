"""Validation result domain type.

Represents the outcome of a single validation applied to an HttpResponse
by a Validator. Multiple ValidationResult instances are aggregated by
the Response Evaluator to determine the overall outcome of a test case.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ValidationResult(BaseModel):
    """Immutable outcome of a single validation step.

    Each Validator produces one ValidationResult per response it
    inspects. The Response Evaluator combines them into the overall
    test outcome.
    """

    model_config = ConfigDict(frozen=True)

    validator_name: str = Field(
        ..., description="Identifier of the validator that produced this result."
    )
    passed: bool = Field(..., description="Whether the validation succeeded.")
    detail: str | None = Field(
        default=None,
        description="Optional human-readable explanation, typically used on failure.",
    )
