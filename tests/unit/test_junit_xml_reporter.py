"""Unit tests for the JUnitXmlReporter."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from gtaakit.adapters.reporters.junit_xml import JUnitXmlReporter
from gtaakit.domain.events import (
    SuiteFinished,
    SuiteStarted,
    TestFailed,
    TestPassed,
    TestSkipped,
)
from gtaakit.domain.validation import ValidationResult
from gtaakit.ports.reporter import Reporter


def _finished(passed: int, failed: int, skipped: int) -> SuiteFinished:
    total = passed + failed + skipped
    return SuiteFinished(
        suite_name="My suite",
        total_tests=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        elapsed_seconds=1.5,
    )


class TestJUnitXmlReporter:
    """Generation of a JUnit XML report from execution events."""

    def test_satisfies_reporter_protocol(self, tmp_path: Path) -> None:
        reporter = JUnitXmlReporter(tmp_path / "report.xml")
        assert isinstance(reporter, Reporter)

    def test_writes_file_on_suite_finished(self, tmp_path: Path) -> None:
        output = tmp_path / "report.xml"
        reporter = JUnitXmlReporter(output)

        reporter.report(SuiteStarted(suite_name="My suite", total_tests=1))
        reporter.report(
            TestPassed(test_id="t1", test_name="A test", elapsed_seconds=0.1)
        )
        reporter.report(_finished(passed=1, failed=0, skipped=0))

        assert output.is_file()

    def test_testsuite_attributes_reflect_counts(self, tmp_path: Path) -> None:
        output = tmp_path / "report.xml"
        reporter = JUnitXmlReporter(output)

        reporter.report(TestPassed(test_id="t1", test_name="ok", elapsed_seconds=0.1))
        reporter.report(
            TestFailed(
                test_id="t2",
                test_name="bad",
                elapsed_seconds=0.2,
                failure_info="boom",
            )
        )
        reporter.report(_finished(passed=1, failed=1, skipped=0))

        root = ET.parse(output).getroot()
        assert root.tag == "testsuite"
        assert root.attrib["name"] == "My suite"
        assert root.attrib["tests"] == "2"
        assert root.attrib["failures"] == "1"
        assert root.attrib["skipped"] == "0"

    def test_passed_case_has_no_children(self, tmp_path: Path) -> None:
        output = tmp_path / "report.xml"
        reporter = JUnitXmlReporter(output)

        reporter.report(TestPassed(test_id="t1", test_name="ok", elapsed_seconds=0.1))
        reporter.report(_finished(passed=1, failed=0, skipped=0))

        root = ET.parse(output).getroot()
        testcase = root.find("testcase")
        assert testcase is not None
        assert testcase.attrib["name"] == "ok"
        assert list(testcase) == []  # no <failure> or <skipped> children

    def test_failed_case_has_failure_child(self, tmp_path: Path) -> None:
        output = tmp_path / "report.xml"
        reporter = JUnitXmlReporter(output)

        reporter.report(
            TestFailed(
                test_id="t1",
                test_name="bad",
                elapsed_seconds=0.2,
                validation_results=[
                    ValidationResult(
                        validator_name="status_code",
                        passed=False,
                        detail="expected 200, got 404",
                    )
                ],
                failure_info="status mismatch",
            )
        )
        reporter.report(_finished(passed=0, failed=1, skipped=0))

        root = ET.parse(output).getroot()
        failure = root.find("testcase/failure")
        assert failure is not None
        assert failure.attrib["message"] == "status mismatch"
        assert failure.text is not None
        assert "status_code" in failure.text

    def test_skipped_case_has_skipped_child(self, tmp_path: Path) -> None:
        output = tmp_path / "report.xml"
        reporter = JUnitXmlReporter(output)

        reporter.report(
            TestSkipped(test_id="t1", test_name="later", reason="no credentials")
        )
        reporter.report(_finished(passed=0, failed=0, skipped=1))

        root = ET.parse(output).getroot()
        skipped = root.find("testcase/skipped")
        assert skipped is not None
        assert skipped.attrib["message"] == "no credentials"

    def test_creates_output_directory_if_missing(self, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "dir" / "report.xml"
        reporter = JUnitXmlReporter(output)

        reporter.report(_finished(passed=0, failed=0, skipped=0))

        assert output.is_file()

    def test_produces_valid_parseable_xml(self, tmp_path: Path) -> None:
        output = tmp_path / "report.xml"
        reporter = JUnitXmlReporter(output)

        reporter.report(TestPassed(test_id="t1", test_name="ok", elapsed_seconds=0.1))
        reporter.report(_finished(passed=1, failed=0, skipped=0))

        # Parsing without raising confirms the XML is well-formed.
        tree = ET.parse(output)
        assert tree.getroot() is not None
