"""Reporter port.

A Reporter consumes ExecutionEvents emitted by the Test Runner during
a suite execution. Concrete reporters (console output, JUnit XML file,
HTML report, ...) live in the adapters subpackage and may coexist:
multiple reporters can be subscribed to the same event stream so that,
for instance, an execution produces both a human-readable console
trace and a machine-readable JUnit XML file consumable by a CI/CD
pipeline.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gtaakit.domain.events import ExecutionEvent


@runtime_checkable
class Reporter(Protocol):
    """Protocol for execution event reporters.

    A reporter receives every ExecutionEvent emitted by the Runner and
    decides what to do with it. The protocol is intentionally minimal:
    a single method receives the event, and the concrete reporter is
    free to dispatch internally on the event subtype if it needs to
    react differently to each.
    """

    def report(self, event: ExecutionEvent) -> None:
        """Consume an execution event.

        Args:
            event: The ExecutionEvent emitted by the Runner. Can be any
                of its concrete subtypes (SuiteStarted, TestStarted,
                TestPassed, TestFailed, TestSkipped, SuiteFinished).
        """
        ...
