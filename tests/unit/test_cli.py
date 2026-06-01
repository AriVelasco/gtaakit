"""Unit tests for the gtaakit CLI argument handling."""

from __future__ import annotations

import pytest

from gtaakit.cli import apply_reports, build_parser


class TestArgumentParser:
    """Parsing of command-line arguments."""

    def test_path_defaults_to_current_dir(self) -> None:
        args = build_parser().parse_args([])
        assert args.path == "."

    def test_path_is_positional(self) -> None:
        args = build_parser().parse_args(["tests/api"])
        assert args.path == "tests/api"

    def test_env_option(self) -> None:
        args = build_parser().parse_args(["--env", "staging"])
        assert args.env == "staging"

    def test_report_is_repeatable(self) -> None:
        args = build_parser().parse_args(["--report", "console", "--report", "junit"])
        assert args.report == ["console", "junit"]


class TestApplyReports:
    """Translation of --report options into environment variables."""

    def test_no_reports_leaves_env_untouched(self) -> None:
        env: dict[str, str] = {}
        apply_reports(None, env)
        assert env == {}

    def test_console_report(self) -> None:
        env: dict[str, str] = {}
        apply_reports(["console"], env)
        assert env["GTAAKIT_REPORTERS"] == "console"

    def test_junit_report_sets_reporter(self) -> None:
        env: dict[str, str] = {}
        apply_reports(["junit"], env)
        assert env["GTAAKIT_REPORTERS"] == "junit"
        assert "GTAAKIT_REPORT_PATH" not in env

    def test_junit_with_path(self) -> None:
        env: dict[str, str] = {}
        apply_reports(["junit:out/report.xml"], env)
        assert env["GTAAKIT_REPORTERS"] == "junit"
        assert env["GTAAKIT_REPORT_PATH"] == "out/report.xml"

    def test_multiple_reports(self) -> None:
        env: dict[str, str] = {}
        apply_reports(["console", "junit"], env)
        assert env["GTAAKIT_REPORTERS"] == "console,junit"

    def test_unknown_report_raises(self) -> None:
        env: dict[str, str] = {}
        with pytest.raises(ValueError):
            apply_reports(["nonsense"], env)

    def test_junit_with_path_then_another_report(self) -> None:
        env: dict[str, str] = {}
        apply_reports(["junit:out.xml", "console"], env)
        assert env["GTAAKIT_REPORTERS"] == "junit,console"
        assert env["GTAAKIT_REPORT_PATH"] == "out.xml"


class TestMain:
    """The main entry point translates arguments and invokes pytest."""

    def test_invokes_pytest_with_path_and_plugin(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}

        def fake_pytest_main(args: list[str]) -> int:
            captured["args"] = args
            return 0

        monkeypatch.setattr("gtaakit.cli.pytest.main", fake_pytest_main)

        from gtaakit.cli import main

        exit_code = main(["examples/petstore", "--report", "console"])

        assert exit_code == 0
        assert captured["args"] == ["examples/petstore", "-p", "gtaakit"]

    def test_returns_pytest_exit_code(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_main(args: list[str]) -> int:
            return 1

        monkeypatch.setattr("gtaakit.cli.pytest.main", fake_main)

        from gtaakit.cli import main

        assert main(["sometests"]) == 1

    def test_env_option_sets_environment_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_main(args: list[str]) -> int:
            return 0

        monkeypatch.setattr("gtaakit.cli.pytest.main", fake_main)
        monkeypatch.delenv("GTAAKIT_ENV", raising=False)

        from gtaakit.cli import main

        main(["tests", "--env", "staging"])

        import os

        assert os.environ.get("GTAAKIT_ENV") == "staging"
