"""Configuration management for gmail_summarizer."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .config_models import AppConfig

logger = logging.getLogger(__name__)


def get_default_config_path() -> Path:
    """Get the default configuration file path following platform conventions.

    Returns:
        Path to the default configuration file in the appropriate config directory
    """
    # Determine the config directory based on platform
    if os.name == "nt":  # Windows
        config_dir = (
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            / "gmail-summary"
        )
    elif os.environ.get("XDG_CONFIG_HOME"):  # Linux/Unix with XDG
        config_dir = Path(os.environ["XDG_CONFIG_HOME"]) / "gmail-summary"
    else:  # macOS and Linux/Unix without XDG
        config_dir = Path.home() / ".config" / "gmail-summary"

    return config_dir / "settings.yml"


class Config:
    """Configuration manager for gmail_summarizer."""

    def __init__(self, config_path: str | None = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to the configuration YAML file. If None, uses platform-specific default.
        """
        if config_path is None:
            self.config_file = get_default_config_path()
        else:
            self.config_file = Path(config_path)
        self.app_config: AppConfig | None = None  # Validated pydantic model
        self._load_config()

    def _load_config(self) -> None:
        """Load and validate configuration from YAML file."""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_file}"
                )

            # Load from config file
            with open(self.config_file) as f:
                raw_config = yaml.safe_load(f) or {}

            # Validate with pydantic
            self.app_config = AppConfig.model_validate(raw_config)

        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}") from e
        except Exception as e:
            logger.error(f"Failed to load configuration from {self.config_file}: {e}")
            raise

    def get_gmail_config(self) -> dict[str, Any]:
        """Get Gmail IMAP configuration."""
        if not self.app_config:
            raise RuntimeError("Configuration not loaded")
        return self.app_config.gmail.model_dump()

    def get_claude_config(self) -> dict[str, Any]:
        """Get Claude CLI configuration."""
        if not self.app_config:
            raise RuntimeError("Configuration not loaded")
        return self.app_config.claude.model_dump()

    def get_highlighting_config(self) -> dict[str, Any]:
        """Get sender highlighting configuration."""
        if not self.app_config:
            raise RuntimeError("Configuration not loaded")
        return {"important_senders": self.app_config.important_senders}

    def get_output_config(self) -> dict[str, Any]:
        """Get output configuration."""
        if not self.app_config:
            raise RuntimeError("Configuration not loaded")
        return {
            "filename": self.app_config.output_file,
            "max_threads_per_category": self.app_config.max_threads_per_category,
        }

    def get_categories(self) -> list[dict[str, Any]]:
        """Get thread categorization rules.

        Categories are returned in the order they appear in the configuration file.
        The first matching category wins when categorizing threads.
        """
        if not self.app_config:
            raise RuntimeError("Configuration not loaded")
        return [cat.model_dump() for cat in self.app_config.categories]

    def get_important_senders(self) -> list[str]:
        """Get list of important sender patterns."""
        if not self.app_config:
            raise RuntimeError("Configuration not loaded")
        return self.app_config.important_senders

    def get_max_threads_per_category(self) -> int:
        """Get maximum threads to process per category."""
        if not self.app_config:
            raise RuntimeError("Configuration not loaded")
        return self.app_config.max_threads_per_category

    def get_output_filename(self) -> str:
        """Get output HTML filename."""
        if not self.app_config:
            raise RuntimeError("Configuration not loaded")
        return self.app_config.output_file
