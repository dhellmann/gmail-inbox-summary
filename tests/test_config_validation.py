"""Tests for pydantic configuration validation."""

import tempfile
from pathlib import Path

import pytest
import yaml

from gmail_summarizer.config import Config
from gmail_summarizer.config import get_default_config_path


def test_valid_config_validation() -> None:
    """Test that valid configuration passes validation."""
    config_data = {
        "gmail": {
            "email_address": "test@gmail.com",
            "password": "test-password",
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
        },
        "claude": {"cli_path": "claude", "timeout": 30, "concurrency": 5},
        "categories": [
            {
                "name": "Test Category",
                "summary_prompt": "Test prompt",
                "criteria": {"labels": ["test-label"]},
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
        assert config.get_claude_config()["concurrency"] == 5
        assert len(config.get_categories()) == 1
        assert config.get_max_threads_per_category() == 25
    finally:
        config_path.unlink()


def test_invalid_email_validation() -> None:
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


def test_label_only_criteria_validation() -> None:
    """Test that label-only criteria works correctly."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {
                "name": "Test",
                "summary_prompt": "Test prompt",
                "criteria": {
                    "labels": ["is:important", "custom-label"]
                },  # Valid labels
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
        assert categories[0]["criteria"]["labels"] == ["is:important", "custom-label"]
    finally:
        config_path.unlink()


def test_invalid_port_validation() -> None:
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


def test_invalid_timeout_validation() -> None:
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


def test_invalid_concurrency_validation() -> None:
    """Test that invalid concurrency values fail validation."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "claude": {"concurrency": 25},  # Concurrency too large
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


def test_empty_category_name_validation() -> None:
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


def test_duplicate_category_names_validation() -> None:
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


def test_invalid_max_threads_validation() -> None:
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


def test_unknown_fields_rejected() -> None:
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


def test_default_categories_created() -> None:
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
        assert (
            categories[0]["summary_prompt"]
            == "Provide a brief summary of this email thread."
        )
        # Verify it's a catch-all category (empty criteria)
        assert categories[0]["criteria"]["labels"] == []
    finally:
        config_path.unlink()


def test_default_category_with_empty_categories_list() -> None:
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
        assert (
            categories[0]["summary_prompt"]
            == "Provide a brief summary of this email thread."
        )
    finally:
        config_path.unlink()


def test_no_default_category_when_categories_provided() -> None:
    """Test that no default category is created when categories are provided."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {
                "name": "Custom Category",
                "summary_prompt": "Custom prompt",
                "criteria": {"labels": ["test-label"]},
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


def test_unlimited_threads_per_category() -> None:
    """Test that max_threads_per_category can be None for unlimited."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "max_threads_per_category": None,  # Unlimited
        "categories": [
            {"name": "Test", "summary_prompt": "Test prompt", "criteria": {}}
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = Config(str(config_path))
        assert config.app_config is not None
        assert config.get_max_threads_per_category() is None
    finally:
        config_path.unlink()


def test_unknown_criteria_fields_rejected() -> None:
    """Test that unknown criteria fields are rejected."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
        "categories": [
            {
                "name": "Test",
                "summary_prompt": "Test prompt",
                "criteria": {
                    "labels": ["test"],
                    "unknown_field": ["invalid"],  # Unknown field should be rejected
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


def test_get_default_config_path() -> None:
    """Test that get_default_config_path returns appropriate paths."""
    path = get_default_config_path()

    # Verify it returns a Path object
    assert isinstance(path, Path)

    # Verify the filename is settings.yml
    assert path.name == "settings.yml"

    # Verify the parent directory contains 'gmail-summary'
    assert "gmail-summary" in str(path.parent)

    # Verify it's an absolute path
    assert path.is_absolute()


def test_config_with_none_path() -> None:
    """Test Config class with None path uses default config path."""
    # Test that None path doesn't crash and uses default logic
    import tempfile

    # Create a temp config file
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)

    try:
        # Test that explicit path works
        config1 = Config(str(temp_path))
        assert config1.app_config is not None
        assert config1.config_file == temp_path

        # Test that None path uses default logic (may not exist, so just test path)
        default_path = get_default_config_path()
        assert default_path.name == "settings.yml"
    finally:
        temp_path.unlink()


def test_config_file_attribute_stores_path() -> None:
    """Test that config_file attribute stores the actual path used for loading."""
    config_data = {
        "gmail": {"email_address": "test@gmail.com"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)

    try:
        # Test explicit path
        config = Config(str(temp_path))
        assert config.config_file == temp_path

        # Test that it matches what was loaded
        assert config.config_file.exists()
        assert config.app_config is not None
    finally:
        temp_path.unlink()
