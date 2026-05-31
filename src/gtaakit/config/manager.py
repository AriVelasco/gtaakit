"""Configuration Manager: consolidates configuration from multiple sources.

It merges a base YAML file with an optional environment-specific YAML
file, and finally applies overrides from environment variables. The
resulting precedence, from lowest to highest, is:

    base file < environment-specific file < environment variables

(CLI parameters, a further layer, are applied by the command-line entry
point on top of the Configuration produced here.)

Environment variables are the mechanism through which a CI/CD pipeline
injects execution-specific values and, in particular, sensitive data
(credentials, tokens) that must never appear in a versioned file
(RF5). The resulting Configuration is an immutable Pydantic model so
the rest of the system can pass it around safely without defensive
copies.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Configuration(BaseModel):
    """Immutable view of the consolidated configuration."""

    model_config = ConfigDict(frozen=True)

    base_url: str = Field(..., description="Base URL of the SUT.")
    default_headers: dict[str, str] = Field(default_factory=dict)
    default_timeout_seconds: float = Field(default=30.0, gt=0)


# Mapping from environment variable name to (Configuration field, parser).
# Explicit by design: each supported override is declared here, so the
# behaviour is predictable and easy to document. Adding a new override
# (for example a future credential field) is a one-line change.
_ENV_VAR_MAPPING: dict[str, tuple[str, Callable[[str], Any]]] = {
    "GTAAKIT_BASE_URL": ("base_url", str),
    "GTAAKIT_DEFAULT_TIMEOUT_SECONDS": ("default_timeout_seconds", float),
}


class ConfigurationManager:
    """Loads and consolidates configuration from YAML files and env vars."""

    def __init__(self, config_dir: Path) -> None:
        """Build a ConfigurationManager rooted at the given directory.

        Args:
            config_dir: Directory holding the YAML configuration files.
                Must contain at least a `base.yaml` file.
        """
        self._config_dir = config_dir

    def load(
        self,
        environment: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> Configuration:
        """Consolidate configuration and return an immutable Configuration.

        Args:
            environment: Name of the environment-specific file to apply
                on top of the base (e.g., "prod" loads "prod.yaml"). If
                None, only the base file is used.
            env: Mapping of environment variables to read overrides from.
                Defaults to the process environment (os.environ). Passing
                an explicit mapping makes the method deterministic and
                testable without mutating the real environment.

        Returns:
            A Configuration with the merged values.

        Raises:
            FileNotFoundError: If base.yaml is missing.
            ValueError: If any YAML file does not contain a top-level
                mapping, or if an environment variable holds a value that
                cannot be parsed into the expected type.
            yaml.YAMLError: If any YAML file is malformed.
        """
        base_path = self._config_dir / "base.yaml"
        if not base_path.is_file():
            raise FileNotFoundError(f"Base configuration not found: {base_path}")

        merged: dict[str, Any] = self._read_yaml(base_path)

        if environment is not None:
            env_path = self._config_dir / f"{environment}.yaml"
            if env_path.is_file():
                env_data = self._read_yaml(env_path)
                merged = self._merge(merged, env_data)

        source = os.environ if env is None else env
        env_overrides = self._read_env_overrides(source)
        merged = self._merge(merged, env_overrides)

        return Configuration(**merged)

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        """Read a YAML file and return its top-level mapping."""
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected a YAML mapping at the top level of {path}, "
                f"got {type(data).__name__}"
            )
        return data

    @staticmethod
    def _read_env_overrides(source: Mapping[str, str]) -> dict[str, Any]:
        """Extract configuration overrides from environment variables.

        Only the variables declared in the explicit mapping are read. An
        empty value is treated as "not set", so a blank variable never
        erases a valid value coming from a file.
        """
        overrides: dict[str, Any] = {}
        for var_name, (field_name, parser) in _ENV_VAR_MAPPING.items():
            raw = source.get(var_name)
            if raw is None or raw == "":
                continue
            try:
                overrides[field_name] = parser(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Environment variable {var_name} holds an invalid "
                    f"value for {field_name}: {raw!r}"
                ) from exc
        return overrides

    @staticmethod
    def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Shallow merge: keys in override replace keys in base."""
        merged = dict(base)
        merged.update(override)
        return merged
