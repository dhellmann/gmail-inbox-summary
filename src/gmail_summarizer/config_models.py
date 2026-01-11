"""Pydantic models for configuration validation."""

import re
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class GmailConfig(BaseModel):
    """Gmail IMAP configuration."""

    email_address: str = Field(..., description="Gmail email address")
    password: str | None = Field(
        None, description="Gmail password (optional if using keychain)"
    )
    imap_server: str = Field(
        default="imap.gmail.com", description="IMAP server hostname"
    )
    imap_port: int = Field(default=993, description="IMAP server port")

    @field_validator("email_address")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email address format."""
        if not v or "@" not in v:
            raise ValueError("Invalid email address format")
        return v

    @field_validator("imap_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate IMAP port range."""
        if not 1 <= v <= 65535:
            raise ValueError("IMAP port must be between 1 and 65535")
        return v


class ClaudeConfig(BaseModel):
    """Claude CLI configuration."""

    cli_path: str = Field(default="claude", description="Path to Claude CLI executable")
    timeout: int = Field(
        default=30, description="Timeout in seconds for each summary request"
    )
    concurrency: int = Field(
        default=5, description="Number of concurrent summarization tasks"
    )

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout range."""
        if not 1 <= v <= 600:
            raise ValueError("Timeout must be between 1 and 600 seconds")
        return v

    @field_validator("concurrency")
    @classmethod
    def validate_concurrency(cls, v: int) -> int:
        """Validate concurrency range."""
        if not 1 <= v <= 20:
            raise ValueError("Concurrency must be between 1 and 20")
        return v


class CategoryCriteria(BaseModel):
    """Thread categorization criteria."""

    from_patterns: list[str] = Field(
        default_factory=list, description="Sender email patterns"
    )
    to_patterns: list[str] = Field(
        default_factory=list, description="Recipient patterns"
    )
    subject_patterns: list[str] = Field(
        default_factory=list, description="Subject line patterns"
    )
    content_patterns: list[str] = Field(
        default_factory=list, description="Message content patterns"
    )
    headers: dict[str, str] = Field(
        default_factory=dict, description="Custom header patterns"
    )
    labels: list[str] = Field(default_factory=list, description="Gmail labels")

    @field_validator(
        "from_patterns", "to_patterns", "subject_patterns", "content_patterns"
    )
    @classmethod
    def validate_regex_patterns(cls, v: list[str]) -> list[str]:
        """Validate regex patterns."""
        for pattern in v:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e
        return v

    @field_validator("headers")
    @classmethod
    def validate_header_patterns(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate header regex patterns."""
        for header, pattern in v.items():
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(
                    f"Invalid regex pattern for header '{header}': {e}"
                ) from e
        return v


class Category(BaseModel):
    """Thread category configuration."""

    name: str = Field(..., description="Category display name")
    summary_prompt: str = Field(..., description="AI summary prompt for this category")
    criteria: CategoryCriteria = Field(
        default_factory=CategoryCriteria, description="Matching criteria"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate category name."""
        if not v.strip():
            raise ValueError("Category name cannot be empty")
        return v.strip()

    @field_validator("summary_prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate summary prompt."""
        if not v.strip():
            raise ValueError("Summary prompt cannot be empty")
        return v.strip()


class AppConfig(BaseModel):
    """Main application configuration."""

    gmail: GmailConfig = Field(
        default_factory=GmailConfig, description="Gmail configuration"
    )
    claude: ClaudeConfig = Field(
        default_factory=ClaudeConfig, description="Claude CLI configuration"
    )
    categories: list[Category] = Field(
        default_factory=list, description="Thread categories"
    )
    important_senders: list[str] = Field(
        default_factory=list, description="Important sender patterns"
    )
    output_file: str = Field(
        default="inbox_summary.html", description="Output HTML filename"
    )
    max_threads_per_category: int | None = Field(
        default=None, description="Maximum threads per category (None for unlimited)"
    )

    @field_validator("important_senders")
    @classmethod
    def validate_sender_patterns(cls, v: list[str]) -> list[str]:
        """Validate important sender regex patterns."""
        for pattern in v:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid sender pattern '{pattern}': {e}") from e
        return v

    @field_validator("max_threads_per_category")
    @classmethod
    def validate_max_threads(cls, v: int | None) -> int | None:
        """Validate max threads range."""
        if v is None:
            return None  # None means unlimited
        if not isinstance(v, int) or not 1 <= v <= 1000:
            raise ValueError(
                "max_threads_per_category must be between 1 and 1000, or None for unlimited"
            )
        return v

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[Category]) -> list[Category]:
        """Validate categories list."""
        # Check for duplicate names
        if v:
            names = [cat.name for cat in v]
            if len(names) != len(set(names)):
                raise ValueError("Category names must be unique")

        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to create default categories if empty."""
        if not self.categories:
            self.categories = [
                Category(
                    name="Everything",
                    summary_prompt="Provide a brief summary of this email thread.",
                    criteria=CategoryCriteria(),
                )
            ]

    model_config = {"extra": "forbid"}  # Reject unknown fields
