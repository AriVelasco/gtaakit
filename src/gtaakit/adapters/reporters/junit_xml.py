"""Reporter that writes execution results as a JUnit XML report.

Produces a machine-readable report in the JUnit XML format, the de
facto standard consumed by CI/CD systems (GitHub Actions, GitLab CI,
Jenkins) to display test results (RF3, RF6).

Unlike the ConsoleReporter, which prints each event as it arrives, this
reporter accumulates the per-test results and writes the complete XML
file when it receives the SuiteFinished event.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from gtaakit.domain.events import (
    ExecutionEvent,
    SuiteFinished,
    TestFailed,
    TestPassed,
    TestSkipped,
)


@dataclass
class _CaseResult:
    """Internal record of a single test result, used to build a <testcase>."""

    name: str
    time: float
    outcome: str  # "passed", "failed" or "skipped"
    message: str = ""
    detail: str = ""


class JUnitXmlReporter:
    """Accumulates execution events and writes a JUnit XML report."""

    def __init__(self, output_path: Path) -> None:
        """Build a JUnitXmlReporter.

        Args:
            output_path: Path of the XML file to write when the suite
                finishes.
        """
        self._output_path = output_path
        self._cases: list[_CaseResult] = []

    def report(self, event: ExecutionEvent) -> None:
        """Consume an execution event.

        Per-test events are accumulated; SuiteFinished triggers writing
        the report. Other events (SuiteStarted, TestStarted) carry no
        information needed for the JUnit report and are ignored.
        """
        match event:
            case TestPassed():
                self._cases.append(
                    _CaseResult(
                        name=event.test_name,
                        time=event.elapsed_seconds,
                        outcome="passed",
                    )
                )
            case TestFailed():
                detail_lines = [
                    f"[{vr.validator_name}] {vr.detail}"
                    for vr in event.validation_results
                    if not vr.passed and vr.detail
                ]
                self._cases.append(
                    _CaseResult(
                        name=event.test_name,
                        time=event.elapsed_seconds,
                        outcome="failed",
                        message=event.failure_info,
                        detail="\n".join(detail_lines),
                    )
                )
            case TestSkipped():
                self._cases.append(
                    _CaseResult(
                        name=event.test_name,
                        time=0.0,
                        outcome="skipped",
                        message=event.reason,
                    )
                )
            case SuiteFinished():
                self._write_report(event)
            case _:
                # SuiteStarted, TestStarted and any other event carry no
                # data for the JUnit report.
                pass

    def _write_report(self, finished: SuiteFinished) -> None:
        """Build the XML tree from the accumulated cases and write it."""
        testsuite = ET.Element(
            "testsuite",
            attrib={
                "name": finished.suite_name,
                "tests": str(finished.total_tests),
                "failures": str(finished.failed),
                "skipped": str(finished.skipped),
                "time": f"{finished.elapsed_seconds:.3f}",
            },
        )

        for case in self._cases:
            testcase = ET.SubElement(
                testsuite,
                "testcase",
                attrib={
                    "name": case.name,
                    "time": f"{case.time:.3f}",
                },
            )
            if case.outcome == "failed":
                failure = ET.SubElement(
                    testcase,
                    "failure",
                    attrib={"message": case.message},
                )
                failure.text = case.detail
            elif case.outcome == "skipped":
                ET.SubElement(
                    testcase,
                    "skipped",
                    attrib={"message": case.message},
                )

        tree = ET.ElementTree(testsuite)
        ET.indent(tree, space="  ")
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(self._output_path, encoding="utf-8", xml_declaration=True)
