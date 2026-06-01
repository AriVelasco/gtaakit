"""Unit tests for collect_cases (gtaakit TestCase discovery in a module)."""

from __future__ import annotations

import types

import pytest

from gtaakit.adapters.runner.pytest_plugin import collect_cases
from gtaakit.domain.http import HttpRequest
from gtaakit.domain.test_case import TestCase


def _make_module(**attrs: object) -> types.ModuleType:
    """Build a throwaway module object with the given attributes."""
    module = types.ModuleType("fake_test_module")
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def _a_case(case_id: str) -> TestCase:
    return TestCase(
        id=case_id,
        name=f"case {case_id}",
        request_factory=lambda _ctx: HttpRequest(
            method="GET", url="https://example.com/x"
        ),
    )


class TestCollectCases:
    """Discovery of GTAAKIT_CASES in a test module."""

    def test_returns_empty_when_variable_absent(self) -> None:
        module = _make_module()
        assert collect_cases(module) == []

    def test_returns_the_declared_cases(self) -> None:
        cases = [_a_case("c1"), _a_case("c2")]
        module = _make_module(GTAAKIT_CASES=cases)

        result = collect_cases(module)

        assert len(result) == 2
        assert [c.id for c in result] == ["c1", "c2"]

    def test_raises_when_not_a_list(self) -> None:
        module = _make_module(GTAAKIT_CASES="not a list")
        with pytest.raises(TypeError):
            collect_cases(module)

    def test_raises_when_element_is_not_a_testcase(self) -> None:
        module = _make_module(GTAAKIT_CASES=[_a_case("c1"), "not a case"])
        with pytest.raises(TypeError):
            collect_cases(module)
