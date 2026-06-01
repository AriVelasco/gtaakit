"""Command-line interface for gtaakit.

Provides a single entry point to run a gtaakit suite non-interactively,
suitable for CI/CD pipelines (RF3, HU-02). The CLI is a thin wrapper
around pytest: it translates its arguments into environment variables
read by the plugin and into a pytest invocation, and returns pytest's
exit code so the pipeline can react to the global result.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import MutableMapping, Sequence

import pytest


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the gtaakit command."""
    parser = argparse.ArgumentParser(
        prog="gtaakit",
        description="Run a gtaakit API test suite.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the tests to run (file or directory). Defaults to '.'.",
    )
    parser.add_argument(
        "--env",
        default=None,
        help="Name of the configuration environment to select (e.g. dev, prod).",
    )
    parser.add_argument(
        "--report",
        action="append",
        default=None,
        help=(
            "Report format to produce. Repeatable. Accepts 'console' and "
            "'junit', optionally as 'junit:path.xml' to set the output file."
        ),
    )
    return parser


def apply_reports(reports: list[str] | None, env: MutableMapping[str, str]) -> None:
    """Translate --report options into the environment variables the plugin reads."""
    if not reports:
        return

    names: list[str] = []
    for report in reports:
        if report.startswith("junit"):
            names.append("junit")
            # Optional 'junit:path.xml' form sets the output file.
            if ":" in report:
                _, _, path = report.partition(":")
                if path:
                    env["GTAAKIT_REPORT_PATH"] = path
        elif report == "console":
            names.append("console")
        else:
            raise ValueError(f"Unknown report format: {report!r}")

    env["GTAAKIT_REPORTERS"] = ",".join(names)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the gtaakit command.

    Args:
        argv: Argument list (defaults to sys.argv[1:]). Passing an explicit
            list makes the function testable without touching the real argv.

    Returns:
        The exit code returned by pytest (0 on success).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.env is not None:
        os.environ["GTAAKIT_ENV"] = args.env

    apply_reports(args.report, os.environ)

    exit_code = pytest.main([args.path, "-p", "gtaakit"])
    return int(exit_code)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
