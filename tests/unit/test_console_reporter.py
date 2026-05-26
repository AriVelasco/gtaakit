"""Unit tests for the ConsoleReporter."""

from __future__ import annotations

import pytest

from gtaakit.adapters.reporters.console import ConsoleReporter
from gtaakit.domain.events import (
    SuiteFinished,
    SuiteStarted,
    TestFailed,
    TestPassed,
    TestSkipped,
    TestStarted,
)
from gtaakit.domain.validation import ValidationResult
from gtaakit.ports.reporter import Reporter


@pytest.fixture
def reporter() -> ConsoleReporter:
    """A ConsoleReporter with colours disabled for readable assertions."""
    return ConsoleReporter(use_color=False)


class TestConsoleReporter:
    """Output produced by the console reporter for each event type."""

    def test_satisfies_reporter_protocol(self, reporter: ConsoleReporter) -> None:
        assert isinstance(reporter, Reporter)

    def test_suite_started_shows_name_and_count(
        self, reporter: ConsoleReporter, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reporter.report(SuiteStarted(suite_name="My suite", total_tests=3))
        out = capsys.readouterr().out
        assert "My suite" in out
        assert "3" in out

    def test_test_passed_shows_passed_mark(
        self, reporter: ConsoleReporter, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reporter.report(TestStarted(test_id="t1", test_name="A test"))
        reporter.report(
            TestPassed(test_id="t1", test_name="A test", elapsed_seconds=0.123)
        )
        out = capsys.readouterr().out
        assert "A test" in out
        assert "PASSED" in out

    def test_test_failed_shows_failure_info_and_validator_detail(
        self, reporter: ConsoleReporter, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reporter.report(
            TestFailed(
                test_id="t2",
                test_name="A failing test",
                elapsed_seconds=0.2,
                validation_results=[
                    ValidationResult(
                        validator_name="status_code",
                        passed=False,
                        detail="expected 200, got 404",
                    )
                ],
                failure_info="Status mismatch",
            )
        )
        out = capsys.readouterr().out
        assert "FAILED" in out
        assert "Status mismatch" in out
        assert "status_code" in out
        assert "expected 200, got 404" in out

    def test_test_skipped_shows_reason(
        self, reporter: ConsoleReporter, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reporter.report(
            TestSkipped(test_id="t3", test_name="Skipped test", reason="no credentials")
        )
        out = capsys.readouterr().out
        assert "SKIPPED" in out
        assert "no credentials" in out

    def test_suite_finished_shows_summary_counts(
        self, reporter: ConsoleReporter, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reporter.report(
            SuiteFinished(
                suite_name="My suite",
                total_tests=5,
                passed=3,
                failed=1,
                skipped=1,
                elapsed_seconds=1.5,
            )
        )
        out = capsys.readouterr().out
        assert "passed: 3" in out
        assert "failed: 1" in out
        assert "skipped: 1" in out

    def test_color_codes_present_when_enabled(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        colored = ConsoleReporter(use_color=True)
        colored.report(
            TestPassed(test_id="t1", test_name="A test", elapsed_seconds=0.1)
        )
        out = capsys.readouterr().out
        # ANSI escape sequences start with the ESC character (\x1b == \033).
        assert "\x1b[" in out

    def test_color_codes_absent_when_disabled(
        self, reporter: ConsoleReporter, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reporter.report(
            TestPassed(test_id="t1", test_name="A test", elapsed_seconds=0.1)
        )
        out = capsys.readouterr().out
        assert "\x1b[" not in out
