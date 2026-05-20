"""Reporter that prints execution events to the console.

Produces a human-readable trace of a suite execution on stdout, with
optional ANSI colours. Colours can be disabled for non-interactive
output such as log files or CI/CD pipelines.
"""

from __future__ import annotations

from gtaakit.domain.events import (
    ExecutionEvent,
    SuiteFinished,
    SuiteStarted,
    TestFailed,
    TestPassed,
    TestSkipped,
    TestStarted,
)


class ConsoleReporter:
    """Reporter that prints a human-readable trace to stdout."""

    _GREEN = "\033[32m"
    _RED = "\033[31m"
    _YELLOW = "\033[33m"
    _BOLD = "\033[1m"
    _RESET = "\033[0m"

    def __init__(self, use_color: bool = True) -> None:
        """Build a ConsoleReporter.

        Args:
            use_color: Whether to emit ANSI colour codes. Set to False
                for non-interactive output (files, CI/CD logs).
        """
        self._use_color = use_color

    def _colorize(self, text: str, color: str) -> str:
        if not self._use_color:
            return text
        return f"{color}{text}{self._RESET}"

    def report(self, event: ExecutionEvent) -> None:
        """Print a line describing the execution event."""
        match event:
            case SuiteStarted():
                header = self._colorize(f"Suite: {event.suite_name}", self._BOLD)
                print(f"{header} ({event.total_tests} tests)")
            case TestStarted():
                print(f"  - {event.test_name} ... ", end="")
            case TestPassed():
                mark = self._colorize("PASSED", self._GREEN)
                print(f"{mark} ({event.elapsed_seconds:.3f}s)")
            case TestFailed():
                mark = self._colorize("FAILED", self._RED)
                print(f"{mark} ({event.elapsed_seconds:.3f}s)")
                print(f"      {event.failure_info}")
                for vr in event.validation_results:
                    if not vr.passed and vr.detail:
                        print(f"      - [{vr.validator_name}] {vr.detail}")
            case TestSkipped():
                mark = self._colorize("SKIPPED", self._YELLOW)
                print(f"{mark} ({event.reason})")
            case SuiteFinished():
                summary = (
                    f"Total: {event.total_tests}  "
                    f"passed: {event.passed}  "
                    f"failed: {event.failed}  "
                    f"skipped: {event.skipped}  "
                    f"({event.elapsed_seconds:.3f}s)"
                )
                color = self._GREEN if event.failed == 0 else self._RED
                print(self._colorize(summary, color))
            case _:
                # Defensive: unknown event subtype. Should not happen with
                # the current event taxonomy, but keeps the reporter robust
                # if new event types are added before this reporter is updated.
                print(f"  [unknown event] {type(event).__name__}")
