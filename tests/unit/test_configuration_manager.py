"""Unit tests for the ConfigurationManager."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from gtaakit.config.manager import Configuration, ConfigurationManager


def _write_yaml(path: Path, data: dict[str, object]) -> None:
    """Helper to dump a Python dict as a YAML file."""
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


class TestConfigurationManagerBaseFile:
    """Loading from the base file only."""

    def test_loads_base_file(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base.yaml",
            {
                "base_url": "https://api.example.com",
                "default_headers": {"X-Trace": "abc"},
                "default_timeout_seconds": 10.0,
            },
        )
        manager = ConfigurationManager(tmp_path)

        config = manager.load()

        assert config.base_url == "https://api.example.com"
        assert config.default_headers == {"X-Trace": "abc"}
        assert config.default_timeout_seconds == 10.0

    def test_applies_defaults_when_fields_missing(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base.yaml", {"base_url": "https://api.example.com"})
        manager = ConfigurationManager(tmp_path)

        config = manager.load()

        assert config.base_url == "https://api.example.com"
        assert config.default_headers == {}
        assert config.default_timeout_seconds == 30.0

    def test_raises_when_base_missing(self, tmp_path: Path) -> None:
        manager = ConfigurationManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            manager.load()

    def test_raises_when_base_url_missing(self, tmp_path: Path) -> None:
        # base_url is a required field of Configuration.
        _write_yaml(tmp_path / "base.yaml", {"default_timeout_seconds": 5.0})
        manager = ConfigurationManager(tmp_path)
        with pytest.raises(ValidationError):
            manager.load()


class TestConfigurationManagerEnvironmentOverride:
    """Environment-specific file overrides the base."""

    def test_env_file_overrides_base_fields(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base.yaml",
            {
                "base_url": "https://api.example.com",
                "default_timeout_seconds": 30.0,
            },
        )
        _write_yaml(
            tmp_path / "prod.yaml",
            {
                "base_url": "https://api.prod.example.com",
                "default_timeout_seconds": 60.0,
            },
        )
        manager = ConfigurationManager(tmp_path)

        config = manager.load(environment="prod")

        assert config.base_url == "https://api.prod.example.com"
        assert config.default_timeout_seconds == 60.0

    def test_env_file_partial_override_keeps_base_values(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base.yaml",
            {
                "base_url": "https://api.example.com",
                "default_timeout_seconds": 30.0,
            },
        )
        _write_yaml(tmp_path / "dev.yaml", {"default_timeout_seconds": 5.0})
        manager = ConfigurationManager(tmp_path)

        config = manager.load(environment="dev")

        # base_url comes from base.yaml; timeout from dev.yaml.
        assert config.base_url == "https://api.example.com"
        assert config.default_timeout_seconds == 5.0

    def test_missing_env_file_falls_back_to_base(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base.yaml",
            {"base_url": "https://api.example.com"},
        )
        manager = ConfigurationManager(tmp_path)

        config = manager.load(environment="nonexistent")

        assert config.base_url == "https://api.example.com"


class TestConfigurationManagerYamlEdgeCases:
    """Defensive handling of malformed YAML."""

    def test_empty_base_file_raises_validation_error(self, tmp_path: Path) -> None:
        (tmp_path / "base.yaml").write_text("", encoding="utf-8")
        manager = ConfigurationManager(tmp_path)
        # An empty file becomes {}, which then fails Configuration validation
        # because base_url is required.
        with pytest.raises(ValidationError):
            manager.load()

    def test_non_mapping_yaml_raises_value_error(self, tmp_path: Path) -> None:
        (tmp_path / "base.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")
        manager = ConfigurationManager(tmp_path)
        with pytest.raises(ValueError):
            manager.load()


class TestConfigurationIsImmutable:
    """The returned Configuration cannot be mutated."""

    def test_configuration_is_frozen(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base.yaml", {"base_url": "https://api.example.com"})
        manager = ConfigurationManager(tmp_path)
        config = manager.load()

        with pytest.raises(ValidationError):
            config.base_url = "https://other.example.com"  # type: ignore[misc]


class TestConfigurationDirectConstruction:
    """The Configuration model itself can be built directly."""

    def test_direct_construction(self) -> None:
        config = Configuration(base_url="https://api.example.com")
        assert config.base_url == "https://api.example.com"
        assert config.default_timeout_seconds == 30.0

    def test_rejects_non_positive_timeout(self) -> None:
        with pytest.raises(ValidationError):
            Configuration(base_url="https://api.example.com", default_timeout_seconds=0)


class TestConfigurationManagerEnvironmentVariables:
    """Environment variables override file-based configuration."""

    def test_env_var_overrides_base_url(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base.yaml", {"base_url": "https://api.example.com"})
        manager = ConfigurationManager(tmp_path)

        config = manager.load(env={"GTAAKIT_BASE_URL": "https://from.env.example.com"})

        assert config.base_url == "https://from.env.example.com"

    def test_env_var_overrides_timeout_with_type_conversion(
        self, tmp_path: Path
    ) -> None:
        _write_yaml(
            tmp_path / "base.yaml",
            {"base_url": "https://api.example.com", "default_timeout_seconds": 30.0},
        )
        manager = ConfigurationManager(tmp_path)

        config = manager.load(env={"GTAAKIT_DEFAULT_TIMEOUT_SECONDS": "5.5"})

        assert config.default_timeout_seconds == 5.5

    def test_env_var_takes_precedence_over_env_file(self, tmp_path: Path) -> None:
        _write_yaml(
            tmp_path / "base.yaml",
            {"base_url": "https://api.example.com"},
        )
        _write_yaml(
            tmp_path / "prod.yaml",
            {"base_url": "https://api.prod.example.com"},
        )
        manager = ConfigurationManager(tmp_path)

        config = manager.load(
            environment="prod",
            env={"GTAAKIT_BASE_URL": "https://api.override.example.com"},
        )

        # env var wins over both base and prod files.
        assert config.base_url == "https://api.override.example.com"

    def test_empty_env_var_is_ignored(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base.yaml", {"base_url": "https://api.example.com"})
        manager = ConfigurationManager(tmp_path)

        config = manager.load(env={"GTAAKIT_BASE_URL": ""})

        # An empty variable must not erase the file value.
        assert config.base_url == "https://api.example.com"

    def test_unrelated_env_vars_are_ignored(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base.yaml", {"base_url": "https://api.example.com"})
        manager = ConfigurationManager(tmp_path)

        config = manager.load(
            env={"PATH": "/usr/bin", "HOME": "/home/user", "SHELL": "/bin/bash"}
        )

        # No GTAAKIT_ variables present: configuration unchanged.
        assert config.base_url == "https://api.example.com"

    def test_invalid_timeout_env_var_raises_value_error(self, tmp_path: Path) -> None:
        _write_yaml(tmp_path / "base.yaml", {"base_url": "https://api.example.com"})
        manager = ConfigurationManager(tmp_path)

        with pytest.raises(ValueError):
            manager.load(env={"GTAAKIT_DEFAULT_TIMEOUT_SECONDS": "not-a-number"})

    def test_no_env_arg_reads_process_environment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_yaml(tmp_path / "base.yaml", {"base_url": "https://api.example.com"})
        manager = ConfigurationManager(tmp_path)

        monkeypatch.setenv("GTAAKIT_BASE_URL", "https://from.process.example.com")
        config = manager.load()

        assert config.base_url == "https://from.process.example.com"
