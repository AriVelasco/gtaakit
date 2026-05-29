"""Pytest adapter for the gtaakit Test Runner.

This plugin makes pytest the execution engine of the Runner: pytest
handles discovery, isolation and timing of each test case, while the
plugin translates pytest's lifecycle hooks into gtaakit ExecutionEvents
emitted to the configured Reporters.

This file currently sets up the skeleton of the plugin. Subsequent
commits will add the hooks that emit SuiteStarted/SuiteFinished events
and that generate one pytest test per gtaakit TestCase.
"""

from __future__ import annotations

import pytest

PLUGIN_NAME = "gtaakit"


def pytest_configure(config: pytest.Config) -> None:
    """Pytest hook called once at the start of the session.

    For now it only records that the plugin has been loaded, by adding
    a custom INI option header. Later commits will use this hook to
    initialise the bridge between pytest and the gtaakit Runner.
    """
    config.addinivalue_line(
        "markers",
        "gtaakit: marks tests generated from gtaakit TestCase definitions.",
    )
