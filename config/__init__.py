"""Configuration loader for the Startup Research data collection system."""

import os
import re
import logging
from pathlib import Path

import yaml
from dotenv import load_dotenv

_logger = logging.getLogger(__name__)

_config_cache = None
_PROJECT_ROOT = Path(__file__).parent.parent


def get_project_root() -> Path:
    return _PROJECT_ROOT


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} patterns with environment variable values."""
    if not isinstance(value, str):
        return value

    def replacer(match):
        var_name = match.group(1)
        env_val = os.environ.get(var_name, "")
        if env_val == "" and var_name in ("BLS_API_KEY", "CRUNCHBASE_API_KEY", "CB_INSIGHTS_API_KEY"):
            _logger.debug("No value for %s — API key not configured", var_name)
        return env_val

    return re.sub(r"\$\{(\w+)\}", replacer, value)


def _resolve_dict(d: dict) -> dict:
    """Recursively resolve env vars in all string values of a dict."""
    resolved = {}
    for key, value in d.items():
        if isinstance(value, str):
            resolved[key] = _resolve_env_vars(value)
        elif isinstance(value, dict):
            resolved[key] = _resolve_dict(value)
        elif isinstance(value, list):
            resolved[key] = [
                _resolve_env_vars(item) if isinstance(item, str)
                else _resolve_dict(item) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            resolved[key] = value
    return resolved


def load_config(config_path: str | None = None) -> dict:
    """Load and return the merged configuration.

    Args:
        config_path: Override path to settings.yaml. If None, uses default.

    Returns:
        Resolved configuration dictionary.
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    # Load .env from project root
    load_dotenv(_PROJECT_ROOT / ".env")

    # Load settings.yaml
    if config_path is None:
        config_path = _PROJECT_ROOT / "config" / "settings.yaml"

    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    _config_cache = _resolve_dict(raw_config)
    return _config_cache


def setup_logging(config_path: str | None = None):
    """Configure logging from logging.yaml."""
    if config_path is None:
        config_path = _PROJECT_ROOT / "config" / "logging.yaml"

    # Ensure log directory exists
    log_dir = _PROJECT_ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Update file handler path to be absolute
    import logging.config
    with open(config_path, "r") as f:
        log_config = yaml.safe_load(f)

    # Make file handler path absolute
    if "handlers" in log_config and "file" in log_config["handlers"]:
        log_config["handlers"]["file"]["filename"] = str(
            _PROJECT_ROOT / "data" / "logs" / "collector.log"
        )

    logging.config.dictConfig(log_config)
