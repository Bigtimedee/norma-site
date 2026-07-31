"""
Tests for the NORMA agent's configuration handling.

Regression coverage for the 31 Jul 2026 incident: the scheduled agent raised an
unhandled `EnvironmentError` (which prints as `OSError`) when its secrets were
absent, failing the job on every scheduled run. Absent configuration must now
be reported clearly and exit 78 (EX_CONFIG) rather than crash.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

from config import (  # noqa: E402
    REQUIRED_ENV,
    SECRETS_LOCATION,
    Config,
    ConfigurationError,
)

EX_CONFIG = 78


@pytest.fixture
def clean_env(monkeypatch):
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("NORMA_SPORT", raising=False)
    return monkeypatch


def set_all(monkeypatch, value="x"):
    for name in REQUIRED_ENV:
        monkeypatch.setenv(name, value)


# ── the specific defect that caused the incident ────────────────────────────
def test_configuration_error_is_not_an_oserror():
    """
    The incident surfaced as `OSError: Missing required env vars: ...` because
    `EnvironmentError` is an alias of `OSError` in Python 3, making a config
    problem read like an I/O fault.
    """
    assert EnvironmentError is OSError          # documents why the old type was wrong
    assert not issubclass(ConfigurationError, OSError)
    assert issubclass(ConfigurationError, Exception)


def test_missing_env_reports_without_raising(clean_env):
    assert Config.missing_env() == list(REQUIRED_ENV)
    assert Config.is_configured() is False


def test_empty_string_counts_as_missing(clean_env):
    """An unset GitHub Actions secret interpolates to '', not absence."""
    for name in REQUIRED_ENV:
        clean_env.setenv(name, "")
    assert Config.missing_env() == list(REQUIRED_ENV)


def test_whitespace_only_counts_as_missing(clean_env):
    for name in REQUIRED_ENV:
        clean_env.setenv(name, "   ")
    assert Config.missing_env() == list(REQUIRED_ENV)


def test_partial_configuration_names_only_the_gaps(clean_env):
    set_all(clean_env)
    clean_env.delenv("ODDS_API_KEY")
    clean_env.setenv("TWITTER_BEARER_TOKEN", "")
    assert set(Config.missing_env()) == {"ODDS_API_KEY", "TWITTER_BEARER_TOKEN"}


def test_from_env_raises_configuration_error_listing_missing(clean_env):
    with pytest.raises(ConfigurationError) as exc:
        Config.from_env()
    assert exc.value.missing == list(REQUIRED_ENV)
    for name in REQUIRED_ENV:
        assert name in str(exc.value)


def test_from_env_succeeds_when_complete(clean_env):
    set_all(clean_env)
    cfg = Config.from_env()
    assert cfg.twitter_api_key == "x"
    assert cfg.odds_api_key == "x"
    assert Config.is_configured() is True


def test_sports_property_parses_and_strips(clean_env):
    set_all(clean_env)
    clean_env.setenv("NORMA_SPORT", " americanfootball_nfl , basketball_nba ,, ")
    assert Config.from_env().sports == ["americanfootball_nfl", "basketball_nba"]


def test_every_required_var_documents_its_source():
    """The operator reading a failure log should not have to guess."""
    for name, source in REQUIRED_ENV.items():
        assert source and source.strip(), f"{name} has no documented source"
    assert "Settings" in SECRETS_LOCATION and "Actions" in SECRETS_LOCATION


# ── end to end: the process must skip, not crash ────────────────────────────
def _run_agent(args, env_overrides=None):
    import os
    env = {k: v for k, v in os.environ.items() if k not in REQUIRED_ENV}
    env.update(env_overrides or {})
    return subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=AGENT_DIR, env=env, capture_output=True, text=True, timeout=60,
    )


def test_unconfigured_run_exits_78_without_traceback():
    proc = _run_agent(["app_highlight"])
    assert proc.returncode == EX_CONFIG, proc.stderr
    assert "Traceback" not in proc.stderr
    assert "OSError" not in proc.stderr


def test_unconfigured_run_explains_where_to_fix_it():
    out = _run_agent(["app_highlight"]).stderr
    assert "not configured" in out.lower()
    assert "Settings" in out and "Actions" in out
    for name in REQUIRED_ENV:
        assert name in out


def test_check_config_flag_reports_status():
    proc = _run_agent(["--check-config"])
    assert proc.returncode == EX_CONFIG
    assert "Traceback" not in proc.stderr


def test_check_config_passes_when_configured():
    proc = _run_agent(["--check-config"], {k: "x" for k in REQUIRED_ENV})
    assert proc.returncode == 0, proc.stderr
    assert "required secrets are set" in proc.stderr
