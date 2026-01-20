"""Configuration module for Graphiti Influxer.

Environment variables take precedence over config file values.
Config file is stored in ~/.influxer/config.toml
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

# Default configuration values
DEFAULT_MCP_URL = "https://graphiti.marakanda.biz/mcp"
DEFAULT_GROUP_ID = "main"
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_OCR_LANGUAGE = "eng+deu+spa"
DEFAULT_OCR_DPI = 300
DEFAULT_MCP_TIMEOUT = 60  # seconds

# Paths
CONFIG_DIR = Path.home() / ".influxer"
CONFIG_FILE_PATH = CONFIG_DIR / "config.toml"
STATE_DB_PATH = CONFIG_DIR / "state.db"


def _get_env(key: str, default: str | int | None = None) -> str | int | None:
    """Get environment variable with optional default."""
    value = os.getenv(key)
    if value is None:
        return default
    # Try to convert to int if default is int
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    return value


# Configuration values with environment variable overrides
GRAPHITI_MCP_URL: str = str(_get_env("INFLUXER_MCP_URL", DEFAULT_MCP_URL))
GROUP_ID: str = str(_get_env("INFLUXER_GROUP_ID", DEFAULT_GROUP_ID))
CHUNK_SIZE: int = int(_get_env("INFLUXER_CHUNK_SIZE", DEFAULT_CHUNK_SIZE) or DEFAULT_CHUNK_SIZE)
CHUNK_OVERLAP: int = int(
    _get_env("INFLUXER_CHUNK_OVERLAP", DEFAULT_CHUNK_OVERLAP) or DEFAULT_CHUNK_OVERLAP
)
OCR_LANGUAGE: str = str(_get_env("INFLUXER_OCR_LANGUAGE", DEFAULT_OCR_LANGUAGE))
OCR_DPI: int = int(_get_env("INFLUXER_OCR_DPI", DEFAULT_OCR_DPI) or DEFAULT_OCR_DPI)
MCP_TIMEOUT: int = int(_get_env("INFLUXER_MCP_TIMEOUT", DEFAULT_MCP_TIMEOUT) or DEFAULT_MCP_TIMEOUT)


def ensure_config_dir() -> Path:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> dict[str, Any]:
    """Load configuration from TOML file, merged with environment variables.

    Priority: CLI flag > env var > config file > default
    """
    config: dict[str, Any] = {
        "mcp_url": DEFAULT_MCP_URL,
        "group_id": DEFAULT_GROUP_ID,
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
        "ocr_language": DEFAULT_OCR_LANGUAGE,
        "ocr_dpi": DEFAULT_OCR_DPI,
        "mcp_timeout": DEFAULT_MCP_TIMEOUT,
        "state_db_path": str(STATE_DB_PATH),
    }

    # Load from config file if exists
    if CONFIG_FILE_PATH.exists():
        with CONFIG_FILE_PATH.open("rb") as f:
            file_config = tomllib.load(f)
            config.update(file_config)

    # Override with environment variables
    if url := os.getenv("INFLUXER_MCP_URL"):
        config["mcp_url"] = url
    if group_id := os.getenv("INFLUXER_GROUP_ID"):
        config["group_id"] = group_id
    if chunk_size := os.getenv("INFLUXER_CHUNK_SIZE"):
        config["chunk_size"] = int(chunk_size)
    if chunk_overlap := os.getenv("INFLUXER_CHUNK_OVERLAP"):
        config["chunk_overlap"] = int(chunk_overlap)
    if ocr_lang := os.getenv("INFLUXER_OCR_LANGUAGE"):
        config["ocr_language"] = ocr_lang
    if ocr_dpi := os.getenv("INFLUXER_OCR_DPI"):
        config["ocr_dpi"] = int(ocr_dpi)
    if timeout := os.getenv("INFLUXER_MCP_TIMEOUT"):
        config["mcp_timeout"] = int(timeout)
    if state_db := os.getenv("INFLUXER_STATE_DB"):
        config["state_db_path"] = state_db

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to TOML file."""
    ensure_config_dir()
    with CONFIG_FILE_PATH.open("wb") as f:
        tomli_w.dump(config, f)


def get_config() -> dict[str, Any]:
    """Get all config values with environment overrides.

    This is the main entry point for getting configuration.
    """
    return load_config()


def get_state_db_path() -> Path:
    """Get the state database path, ensuring the directory exists."""
    config = load_config()
    path = Path(config["state_db_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def is_first_run() -> bool:
    """Check if this is the first run (no config file exists)."""
    return not CONFIG_FILE_PATH.exists()
