"""Configuration Manager: consolidates configuration from multiple sources.

For this initial implementation it merges a base YAML file with an
optional environment-specific YAML file. Later commits will add the
remaining sources defined in Capítol 7.2.1 (environment variables and
CLI parameters), following the precedence:

    CLI > env vars > environment-specific file > base file

The resulting Configuration is an immutable Pydantic model so the
rest of the system can pass it around safely without defensive copies.
"""

from __future__ import annotations

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


class ConfigurationManager:
    """Loads and consolidates configuration from YAML files."""

    def __init__(self, config_dir: Path) -> None:
        """Build a ConfigurationManager rooted at the given directory.

        Args:
            config_dir: Directory holding the YAML configuration files.
                Must contain at least a `base.yaml` file.
        """
        self._config_dir = config_dir

    def load(self, environment: str | None = None) -> Configuration:
        """Consolidate configuration and return an immutable Configuration.

        Args:
            environment: Name of the environment-specific file to apply
                on top of the base (e.g., "prod" loads "prod.yaml"). If
                None, only the base file is used.

        Returns:
            A Configuration with the merged values.

        Raises:
            FileNotFoundError: If base.yaml is missing.
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
    def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Shallow merge: keys in override replace keys in base."""
        merged = dict(base)
        merged.update(override)
        return merged
