"""Tests for pydantic configuration validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from gmail_summarizer.config import Config


def test_valid_config_validation():
    """Test that valid configuration passes validation."""
    config_data = {
        "gmail": {
            "email_address": "test@gmail.com",
            "password": "test-password",
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
        },
        "claude": {"cli_path": "claude", "timeout": 30},
        "categories": [
            {
                "name": "Test Category",
                "summary_prompt": "Test prompt",
                "criteria": {"from_patterns": [".*@test\\.com"]},
            }
        ],
        "important_senders": ["important@test\\.com"],
        "output_file": "test.html",
        "max_threads_per_category": 25,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = Config(str(config_path))
        assert config.app_config is not None
        assert config.get_gmail_config()["email_address"] == "test@gmail.com"
        assert config.get_claude_config()["timeout"] == 30
        assert len(config.get_categories()) == 1
        assert config.get_max_threads_per_category() == 25
    finally:
        config_path.unlink()


def test_invalid_email_validation():
    """Test that invalid email address fails validation."""
    config_data = {
        "gmail": {"email_address": "invalid-email"},  # Missing @
        "categories": [
            {"name": "Test", "summary_prompt": "Test prompt", "criteria": {}}
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()


def test_invalid_regex_pattern_validation():
    """Test that invalid regex patterns fail validation."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {
                "name": "Test",
                "summary_prompt": "Test prompt",
                "criteria": {"from_patterns": ["[invalid_regex"]},  # Invalid regex
            }
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()


def test_invalid_port_validation():
    """Test that invalid port numbers fail validation."""
    config_data = {
        "gmail": {
            "email_address": "test@gmail.com",
            "imap_port": 70000,  # Port out of range
        },
        "categories": [
            {"name": "Test", "summary_prompt": "Test prompt", "criteria": {}}
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()


def test_invalid_timeout_validation():
    """Test that invalid timeout values fail validation."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "claude": {"timeout": 700},  # Timeout too large
        "categories": [
            {"name": "Test", "summary_prompt": "Test prompt", "criteria": {}}
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()


def test_empty_category_name_validation():
    """Test that empty category names fail validation."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {
                "name": "  ",
                "summary_prompt": "Test prompt",
                "criteria": {},
            }  # Empty name
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()


def test_duplicate_category_names_validation():
    """Test that duplicate category names fail validation."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {"name": "Test", "summary_prompt": "Test prompt 1", "criteria": {}},
            {
                "name": "Test",
                "summary_prompt": "Test prompt 2",
                "criteria": {},
            },  # Duplicate
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()


def test_invalid_max_threads_validation():
    """Test that invalid max threads values fail validation."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "max_threads_per_category": 0,  # Too small
        "categories": [
            {"name": "Test", "summary_prompt": "Test prompt", "criteria": {}}
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()


def test_unknown_fields_rejected():
    """Test that unknown configuration fields are rejected."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {"name": "Test", "summary_prompt": "Test prompt", "criteria": {}}
        ],
        "unknown_field": "should be rejected",  # Unknown field
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()


def test_default_categories_created():
    """Test that default categories are created when none provided."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        # No categories provided
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = Config(str(config_path))
        categories = config.get_categories()
        assert len(categories) == 1
        assert categories[0]["name"] == "Everything"
        assert categories[0]["summary_prompt"] == "Provide a brief summary of this email thread."
        # Verify it's a catch-all category (empty criteria)
        assert categories[0]["criteria"]["from_patterns"] == []
        assert categories[0]["criteria"]["to_patterns"] == []
        assert categories[0]["criteria"]["subject_patterns"] == []
        assert categories[0]["criteria"]["content_patterns"] == []
        assert categories[0]["criteria"]["headers"] == {}
        assert categories[0]["criteria"]["labels"] == []
    finally:
        config_path.unlink()


def test_default_category_with_empty_categories_list():
    """Test that default category is created when categories list is explicitly empty."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [],  # Explicitly empty categories list
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = Config(str(config_path))
        categories = config.get_categories()
        assert len(categories) == 1
        assert categories[0]["name"] == "Everything"
        assert categories[0]["summary_prompt"] == "Provide a brief summary of this email thread."
    finally:
        config_path.unlink()


def test_no_default_category_when_categories_provided():
    """Test that no default category is created when categories are provided."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {
                "name": "Custom Category",
                "summary_prompt": "Custom prompt",
                "criteria": {"from_patterns": ["test@example.com"]},
            }
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = Config(str(config_path))
        categories = config.get_categories()
        assert len(categories) == 1
        assert categories[0]["name"] == "Custom Category"
        assert categories[0]["summary_prompt"] == "Custom prompt"
        # No "Everything" category should be created
        assert all(cat["name"] != "Everything" for cat in categories)
    finally:
        config_path.unlink()


def test_header_pattern_validation():
    """Test that header patterns are properly validated."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {
                "name": "Test",
                "summary_prompt": "Test prompt",
                "criteria": {
                    "headers": {"List-Id": "[invalid_regex"}  # Invalid regex in header
                },
            }
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid configuration"):
            Config(str(config_path))
    finally:
        config_path.unlink()
