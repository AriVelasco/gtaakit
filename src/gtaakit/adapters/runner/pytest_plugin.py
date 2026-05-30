"""Pytest adapter for the gtaakit Test Runner.

This plugin makes pytest the execution engine of the gtaakit Runner:
pytest handles discovery, isolation and timing of each test case, while
the plugin translates pytest's lifecycle hooks into gtaakit
ExecutionEvents emitted to the configured Reporters.

Reporters are read from a YAML configuration file ('gtaakit.yaml') in
the current working directory; later commits will replace this with a
call to the ConfigurationManager once it is feature-complete.

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

    event = SuiteStarted(suite_name=suite_name, total_tests=0)
    for reporter in reporters:
        reporter.report(event)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Emit SuiteFinished when the pytest session ends."""
    from gtaakit.domain.events import SuiteFinished

    reporters: list[Reporter] = _session_state.get("reporters", [])
    suite_name: str = _session_state.get("suite_name", "gtaakit session")
    start_time: float = _session_state.get("start_time", time.perf_counter())

    elapsed = time.perf_counter() - start_time
    total = session.testscollected
    if exitstatus == 0:
        passed, failed, skipped = total, 0, 0
    else:
        passed, failed, skipped = 0, total, 0

    event = SuiteFinished(
        suite_name=suite_name,
        total_tests=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        elapsed_seconds=elapsed,
    )
    for reporter in reporters:
        reporter.report(event)

    _session_state.clear()
