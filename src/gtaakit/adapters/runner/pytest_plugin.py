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


def _build_reporter(name: str) -> Reporter:
    """Build a Reporter from its short name as written in the config."""
    from gtaakit.adapters.reporters.console import ConsoleReporter

    if name == "console":
        return ConsoleReporter()
    raise ValueError(f"Unknown reporter '{name}'")


def _emit(event: ExecutionEvent) -> None:
    """Send an event to every reporter registered for this session."""
    reporters: list[Reporter] = _session_state.get("reporters", [])
    for reporter in reporters:
        reporter.report(event)


def _short_name(nodeid: str) -> str:
    """Extract a human-readable test name from a pytest nodeid."""
    return nodeid.rsplit("::", 1)[-1]


def pytest_configure(config: pytest.Config) -> None:
    """Pytest hook called once at the start of the session."""
    config.addinivalue_line(
        "markers",
        "gtaakit: marks tests generated from gtaakit TestCase definitions.",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Emit SuiteStarted when the pytest session begins."""
    from gtaakit.domain.events import SuiteStarted

    plugin_config = _load_plugin_config(Path(session.config.rootpath))
    suite_name = plugin_config.get("suite_name", "gtaakit session")
    reporter_names = plugin_config.get("reporters", [])

    reporters: list[Reporter] = [_build_reporter(name) for name in reporter_names]
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
