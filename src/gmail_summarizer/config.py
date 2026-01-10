"""Configuration management for gmail_summarizer."""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for gmail_summarizer."""

    def __init__(self, config_path: str = "config"):
        """Initialize configuration manager.

        Args:
            config_path: Directory containing configuration files or direct config file path
        """
        config_path_obj = Path(config_path)
        
        # If it's a file, load it directly as a unified config
        if config_path_obj.is_file():
            self.config_file = config_path_obj
            self.config_dir = config_path_obj.parent
            self.unified_config = True
        else:
            # It's a directory with separate files
            self.config_dir = config_path_obj
            self.config_file = None
            self.unified_config = False
            
        self.settings: dict[str, Any] = {}
        self.categories: list[dict[str, Any]] = []
        self.config: dict[str, Any] = {}  # For unified config
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from YAML files."""
        if self.unified_config and self.config_file:
            # Load from unified config file
            with open(self.config_file) as f:
                self.config = yaml.safe_load(f) or {}
            
            # Extract settings and categories from unified config
            self.settings = self.config
            self.categories = self.config.get("categories", [])
            
        else:
            # Load from separate files (legacy format)
            # Load main settings
            settings_file = self.config_dir / "settings.yaml"
            if settings_file.exists():
                with open(settings_file) as f:
                    self.settings = yaml.safe_load(f) or {}
            else:
                logger.warning(f"Settings file not found: {settings_file}")
                self._create_default_settings()

            # Load category definitions
            categories_file = self.config_dir / "categories.yaml"
            if categories_file.exists():
                with open(categories_file) as f:
                    categories_data = yaml.safe_load(f) or {}
                    self.categories = categories_data.get("categories", [])
            else:
                logger.warning(f"Categories file not found: {categories_file}")
            self._create_default_categories()

    def _create_default_settings(self) -> None:
        """Create default settings configuration."""
        self.settings = {
            "gmail": {
                "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
                "credentials_file": "credentials.json",
                "token_file": "token.json",
            },
            "claude": {"cli_path": "claude", "timeout": 30},
            "highlighting": {"important_senders": []},
            "output": {
                "filename": "inbox_summary.html",
                "max_threads_per_category": 50,
            },
        }

        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)

        # Write default settings
        settings_file = self.config_dir / "settings.yaml"
        with open(settings_file, "w") as f:
            yaml.dump(self.settings, f, default_flow_style=False, indent=2)

        logger.info(f"Created default settings file: {settings_file}")

    def _create_default_categories(self) -> None:
        """Create default category configuration."""
        self.categories = [
            {
                "name": "Important Messages",
                "order": 1,
                "criteria": {"labels": ["IMPORTANT"]},
                "summary_prompt": "Summarize this important email thread, highlighting key action items and decisions.",
            },
            {
                "name": "Jira Updates",
                "order": 2,
                "criteria": {
                    "from_patterns": [".*@atlassian\\.net", "jira@.*"],
                    "subject_patterns": ["\\[JIRA\\]", "\\[.*-\\d+\\]"],
                },
                "summary_prompt": "Summarize this Jira ticket thread, focusing on status changes, assignments, and key updates.",
            },
            {
                "name": "Code Reviews",
                "order": 3,
                "criteria": {
                    "from_patterns": ["noreply@github\\.com", "gitlab@.*"],
                    "subject_patterns": ["\\[.*\\] Pull Request", "Merge Request"],
                },
                "summary_prompt": "Summarize this code review thread, noting merge status, feedback, and any blocking issues.",
            },
            {
                "name": "Mailing Lists",
                "order": 4,
                "criteria": {
                    "to_patterns": [".*@lists\\.", ".*@groups\\."],
                    "headers": {"List-Id": ".*"},
                },
                "summary_prompt": "Summarize this mailing list discussion, highlighting main topics and conclusions.",
            },
            {
                "name": "Everything Else",
                "order": 999,
                "criteria": {},
                "summary_prompt": "Provide a brief summary of this email thread.",
            },
        ]

        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)

        # Write default categories
        categories_file = self.config_dir / "categories.yaml"
        categories_data = {"categories": self.categories}
        with open(categories_file, "w") as f:
            yaml.dump(categories_data, f, default_flow_style=False, indent=2)

        logger.info(f"Created default categories file: {categories_file}")

    def get_gmail_config(self) -> dict[str, Any]:
        """Get Gmail API configuration."""
        return self.settings.get("gmail", {})  # type: ignore[no-any-return]

    def get_claude_config(self) -> dict[str, Any]:
        """Get Claude CLI configuration."""
        # Handle unified config format
        if self.unified_config and "claude" in self.config:
            return self.config["claude"]  # type: ignore[no-any-return]
        # Handle legacy format
        return self.settings.get("claude", {})  # type: ignore[no-any-return]

    def get_highlighting_config(self) -> dict[str, Any]:
        """Get sender highlighting configuration."""
        return self.settings.get("highlighting", {})  # type: ignore[no-any-return]

    def get_output_config(self) -> dict[str, Any]:
        """Get output configuration."""
        return self.settings.get("output", {})  # type: ignore[no-any-return]

    def get_categories(self) -> list[dict[str, Any]]:
        """Get thread categorization rules."""
        return sorted(self.categories, key=lambda x: x.get("order", 999))

    def get_important_senders(self) -> list[str]:
        """Get list of important sender patterns."""
        # Handle unified config format
        if self.unified_config and "important_senders" in self.config:
            return self.config["important_senders"]  # type: ignore[no-any-return]
        # Handle legacy format
        return self.get_highlighting_config().get("important_senders", [])  # type: ignore[no-any-return]

    def get_max_threads_per_category(self) -> int:
        """Get maximum threads to process per category."""
        # Handle unified config format
        if self.unified_config and "max_threads_per_category" in self.config:
            return self.config["max_threads_per_category"]  # type: ignore[no-any-return]
        # Handle legacy format
        return self.get_output_config().get("max_threads_per_category", 50)  # type: ignore[no-any-return]

    def get_output_filename(self) -> str:
        """Get output HTML filename."""
        # Handle unified config format
        if self.unified_config and "output_file" in self.config:
            return self.config["output_file"]  # type: ignore[no-any-return]
        # Handle legacy format
        return self.get_output_config().get("filename", "inbox_summary.html")  # type: ignore[no-any-return]
