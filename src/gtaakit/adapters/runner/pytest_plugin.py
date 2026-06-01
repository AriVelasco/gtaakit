"""Pytest adapter for the gtaakit Test Runner.

This plugin makes pytest the execution engine of the gtaakit Runner:
pytest handles discovery, isolation and timing of each test case, while
the plugin translates pytest's lifecycle hooks into gtaakit
ExecutionEvents emitted to the configured Reporters.

Reporters are read from a YAML configuration file ('gtaakit.yaml') in
the current working directory; later iterations will replace this with
a call to the ConfigurationManager once it is feature-complete.

Note: gtaakit imports are deferred to function bodies to avoid eager
loading of the package before pytest-cov has started measuring. This
keeps the coverage report accurate when this plugin is active.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from gtaakit.domain.events import ExecutionEvent
    from gtaakit.ports.reporter import Reporter


PLUGIN_NAME = "gtaakit"
CONFIG_FILENAME = "gtaakit.yaml"

_session_state: dict[str, Any] = {}


def _load_plugin_config(rootpath: Path) -> dict[str, Any]:
    """Read the plugin's YAML configuration file, if present."""
    config_path = rootpath / CONFIG_FILENAME
    if not config_path.is_file():
        return {}
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _build_reporter(name: str, report_path: Path | None = None) -> Reporter:
    """Build a Reporter from its short name as written in the config.

    Args:
        name: Short reporter name ("console" or "junit").
        report_path: Output path for reporters that write a file (junit).
            Defaults to "gtaakit-report.xml" if not given.
    """
    from gtaakit.adapters.reporters.console import ConsoleReporter
    from gtaakit.adapters.reporters.junit_xml import JUnitXmlReporter

    if name == "console":
        return ConsoleReporter()
    if name == "junit":
        path = report_path if report_path is not None else Path("gtaakit-report.xml")
        return JUnitXmlReporter(path)
    raise ValueError(f"Unknown reporter '{name}'")


def _emit(event: ExecutionEvent) -> None:
    """Send an event to every reporter registered for this session."""
    reporters: list[Reporter] = _session_state.get("reporters", [])
    for reporter in reporters:
        reporter.report(event)


def _short_name(nodeid: str) -> str:
    """Extract a human-readable test name from a pytest nodeid."""
    return nodeid.rsplit("::", 1)[-1]


@pytest.fixture
def gtaakit_client() -> Any:
    """Provide an HttpClient to gtaakit test cases, closed on teardown.

    The client is built from the plugin configuration. For now it uses a
    minimal configuration; a later iteration will source it from the
    ConfigurationManager. Defined as a fixture so pytest manages its
    lifecycle: it is created per test and closed afterwards.
    """
    from gtaakit.adapters.http.httpx_client import HttpxClient

    config = _load_plugin_config(Path.cwd())
    base_url = config.get("base_url")

    client = HttpxClient(base_url=base_url) if base_url else HttpxClient()
    try:
        yield client
    finally:
        client.close()


def collect_cases(module: object) -> list[Any]:
    """Find the list of gtaakit TestCase objects declared in a test module.

    Looks for a module-level variable named GTAAKIT_CASES. Returns an empty
    list if the variable is absent. Validates that every element is a
    TestCase, raising a clear error otherwise so a misdeclared list fails
    loudly rather than silently producing no tests.
    """
    from gtaakit.domain.test_case import TestCase

    cases = getattr(module, "GTAAKIT_CASES", None)
    if cases is None:
        return []
    if not isinstance(cases, list):
        raise TypeError(f"GTAAKIT_CASES must be a list, got {type(cases).__name__}")
    for index, case in enumerate(cases):
        if not isinstance(case, TestCase):
            raise TypeError(
                f"GTAAKIT_CASES[{index}] must be a TestCase, got {type(case).__name__}"
            )
    return cases


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize host tests with the TestCase objects of their module.

    A test function that requests the 'gtaakit_case' fixture is treated as
    a host: the plugin looks up GTAAKIT_CASES in the test's module and
    parametrizes the test once per case, using each case's id as the
    parameter id so it appears as a distinct test in the report. Tests that
    do not request 'gtaakit_case' are left untouched.
    """
    if "gtaakit_case" not in metafunc.fixturenames:
        return

    cases = collect_cases(metafunc.module)
    metafunc.parametrize(
        "gtaakit_case",
        cases,
        ids=[case.id for case in cases],
    )


def pytest_configure(config: pytest.Config) -> None:
    """Pytest hook called once at the start of the session."""
    config.addinivalue_line(
        "markers",
        "gtaakit: marks tests generated from gtaakit TestCase definitions.",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Emit SuiteStarted when the pytest session begins.

    Reporters come from the gtaakit.yaml file, but the GTAAKIT_REPORTERS
    environment variable (a comma-separated list) takes precedence when
    set, so the CLI can drive the reporter selection. The output path for
    file-based reporters is read from GTAAKIT_REPORT_PATH.
    """
    import os

    from gtaakit.domain.events import SuiteStarted

    plugin_config = _load_plugin_config(Path(session.config.rootpath))
    suite_name = plugin_config.get("suite_name", "gtaakit session")

    env_reporters = os.environ.get("GTAAKIT_REPORTERS", "")
    if env_reporters:
        reporter_names = [n.strip() for n in env_reporters.split(",") if n.strip()]
    else:
        reporter_names = plugin_config.get("reporters", [])

    report_path_env = os.environ.get("GTAAKIT_REPORT_PATH", "")
    report_path = Path(report_path_env) if report_path_env else None

    reporters: list[Reporter] = [
        _build_reporter(name, report_path) for name in reporter_names
    ]
    _session_state["reporters"] = reporters
    _session_state["suite_name"] = suite_name
    _session_state["start_time"] = time.perf_counter()
    _session_state["counts"] = {"passed": 0, "failed": 0, "skipped": 0}
    _session_state["started_tests"] = set()

    event = SuiteStarted(suite_name=suite_name, total_tests=0)
    _emit(event)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Translate per-test pytest reports into gtaakit events."""
    from gtaakit.domain.events import TestFailed, TestPassed, TestSkipped, TestStarted

    nodeid = report.nodeid
    name = _short_name(nodeid)
    started_tests: set[str] = _session_state.get("started_tests", set())

    # Emit TestStarted only once per test, at the setup phase.
    if report.when == "setup" and nodeid not in started_tests:
        started_tests.add(nodeid)
        _emit(TestStarted(test_id=nodeid, test_name=name))

    # The 'call' phase carries the verdict; 'setup' with outcome 'skipped'
    # is also a verdict (the test never reached the call phase).
    if report.when == "call":
        if report.outcome == "passed":
            _session_state["counts"]["passed"] += 1
            _emit(
                TestPassed(
                    test_id=nodeid,
                    test_name=name,
                    elapsed_seconds=report.duration,
                )
            )
        elif report.outcome == "failed":
            _session_state["counts"]["failed"] += 1
            _emit(
                TestFailed(
                    test_id=nodeid,
                    test_name=name,
                    elapsed_seconds=report.duration,
                    validation_results=[],
                    failure_info=str(report.longrepr)
                    if report.longrepr
                    else "test failed",
                )
            )
    elif report.when == "setup" and report.outcome == "skipped":
        _session_state["counts"]["skipped"] += 1
        reason = "skipped"
        if report.longrepr:
            # longrepr for skipped tests is a tuple (file, line, reason).
            if isinstance(report.longrepr, tuple) and len(report.longrepr) >= 3:
                reason = str(report.longrepr[2])
            else:
                reason = str(report.longrepr)
        _emit(TestSkipped(test_id=nodeid, test_name=name, reason=reason))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Emit SuiteFinished when the pytest session ends."""
    from gtaakit.domain.events import SuiteFinished

    suite_name: str = _session_state.get("suite_name", "gtaakit session")
    start_time: float = _session_state.get("start_time", time.perf_counter())
    counts: dict[str, int] = _session_state.get(
        "counts", {"passed": 0, "failed": 0, "skipped": 0}
    )

    elapsed = time.perf_counter() - start_time
    total = session.testscollected

    event = SuiteFinished(
        suite_name=suite_name,
        total_tests=total,
        passed=counts["passed"],
        failed=counts["failed"],
        skipped=counts["skipped"],
        elapsed_seconds=elapsed,
    )
    _emit(event)

    _session_state.clear()
