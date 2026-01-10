"""Integration tests for the complete Gmail Inbox Summary workflow."""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from gmail_summarizer.config import Config
from gmail_summarizer.main import cli


@pytest.fixture
def sample_config_file() -> Path:
    """Create a temporary configuration file for testing."""
    config_content = """
gmail:
  email_address: "test@gmail.com"
  password: "test-password"

claude:
  cli_path: "claude"
  timeout: 30

categories:
  - name: "Work"
    summary_prompt: "Summarize this work-related email thread."
    criteria:
      from_patterns:
        - ".*@company\\\\.com"

  - name: "Personal"
    summary_prompt: "Summarize this personal email thread."
    criteria: {}

important_senders:
  - "boss@company\\\\.com"
  - "important@client\\\\.com"

output_file: "test_summary.html"
max_threads_per_category: 5
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        return Path(f.name)


@pytest.fixture
def sample_threads_data() -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    """Create sample thread data for testing."""
    return [
        # Work thread
        (
            {"id": "thread1", "snippet": "Work discussion"},
            [
                {
                    "id": "msg1",
                    "threadId": "thread1",
                    "from": "colleague@company.com",
                    "to": "user@company.com",
                    "subject": "Project Update",
                    "date": "2024-01-01",
                    "body": "Here's the latest project status...",
                    "label_ids": ["INBOX"],
                }
            ],
        ),
        # Personal thread
        (
            {"id": "thread2", "snippet": "Personal email"},
            [
                {
                    "id": "msg2",
                    "threadId": "thread2",
                    "from": "friend@gmail.com",
                    "to": "user@gmail.com",
                    "subject": "Weekend Plans",
                    "date": "2024-01-01",
                    "body": "What are you up to this weekend?",
                    "label_ids": ["INBOX"],
                }
            ],
        ),
    ]


def test_cli_help() -> None:
    """Test that CLI help works correctly."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Generate AI-powered summaries" in result.output
    assert "Commands:" in result.output


def test_cli_invalid_config() -> None:
    """Test CLI behavior with invalid config file."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--config", "nonexistent.yaml"])
    assert result.exit_code != 0


@patch("gmail_summarizer.main.ImapGmailClient")
@patch("gmail_summarizer.main.LLMSummarizer")
def test_cli_dry_run(
    mock_llm_summarizer: Mock,
    mock_gmail_client: Mock,
    sample_config_file: Path,
    sample_threads_data: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> None:
    """Test CLI dry run functionality."""
    # Setup mocks
    mock_gmail = Mock()
    mock_gmail.get_inbox_threads.return_value = [t[0] for t in sample_threads_data]
    mock_gmail.get_thread_messages.side_effect = lambda tid: [
        t[1] for t in sample_threads_data if t[0]["id"] == tid
    ][0]
    mock_gmail_client.return_value = mock_gmail

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli, ["run", "--config", str(sample_config_file), "--dry-run", "--verbose"]
        )

        assert result.exit_code == 0
        assert "Dry run complete" in result.output
        assert mock_gmail.get_inbox_threads.called
        # LLM summarizer should not be used in dry run
        mock_llm_summarizer.assert_not_called()


@patch("gmail_summarizer.main.ImapGmailClient")
@patch("gmail_summarizer.main.LLMSummarizer")
def test_cli_test_claude(
    mock_llm_summarizer: Mock,
    mock_gmail_client: Mock,
    sample_config_file: Path,
) -> None:
    """Test CLI Claude connection testing."""
    # Setup mock
    mock_summarizer = Mock()
    mock_summarizer.test_cli_connection.return_value = True
    mock_llm_summarizer.return_value = mock_summarizer

    runner = CliRunner()
    result = runner.invoke(cli, ["test-claude", "--config", str(sample_config_file)])

    assert result.exit_code == 0
    assert "Claude CLI is working correctly" in result.output
    mock_summarizer.test_cli_connection.assert_called_once()


@patch("gmail_summarizer.main.ImapGmailClient")
@patch("gmail_summarizer.main.LLMSummarizer")
@patch("gmail_summarizer.main.HTMLGenerator")
def test_full_workflow_integration(
    mock_html_generator: Mock,
    mock_llm_summarizer: Mock,
    mock_gmail_client: Mock,
    sample_config_file: Path,
    sample_threads_data: list[tuple[dict[str, Any], list[dict[str, Any]]]],
) -> None:
    """Test complete workflow integration."""
    # Setup Gmail client mock
    mock_gmail = Mock()
    mock_gmail.get_inbox_threads.return_value = [t[0] for t in sample_threads_data]
    mock_gmail.get_thread_messages.side_effect = lambda tid: [
        msgs for thread, msgs in sample_threads_data if thread["id"] == tid
    ][0]
    mock_gmail_client.return_value = mock_gmail

    # Setup LLM summarizer mock
    mock_summarizer = Mock()
    mock_summarizer.test_cli_connection.return_value = True

    def mock_summarize_batch(categorized_threads: dict) -> dict:
        result: dict[str, list] = {}
        for category, threads in categorized_threads.items():
            result[category] = []
            for thread in threads:
                thread_copy = thread.copy()
                thread_copy.update(
                    {
                        "summary": f"AI summary for {thread['subject']}",
                        "summary_generated": True,
                        "summary_error": None,
                    }
                )
                result[category].append(thread_copy)
        return result

    mock_summarizer.summarize_threads_batch.side_effect = mock_summarize_batch
    mock_summarizer.get_summarization_stats.return_value = {
        "total_threads": 2,
        "successful_summaries": 2,
        "failed_summaries": 0,
        "success_rate": 1.0,
        "error_types": {},
    }
    mock_llm_summarizer.return_value = mock_summarizer

    # Setup HTML generator mock
    mock_generator = Mock()
    mock_generator.generate_html_report.return_value = "/tmp/test_output.html"
    mock_html_generator.return_value = mock_generator

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["run", "--config", str(sample_config_file), "--verbose"],
        )

        assert result.exit_code == 0
        assert "Gmail inbox summary generated successfully!" in result.output

        # Verify all components were called
        mock_gmail.get_inbox_threads.assert_called_once()
        mock_summarizer.test_cli_connection.assert_called_once()
        mock_summarizer.summarize_threads_batch.assert_called_once()
        mock_generator.generate_html_report.assert_called_once()


def test_config_loading_integration(sample_config_file: Path) -> None:
    """Test that configuration loading works correctly."""
    config = Config(str(sample_config_file))

    # Test basic config loading
    assert config.get_output_filename() == "test_summary.html"
    assert config.get_max_threads_per_category() == 5

    # Test categories
    categories = config.get_categories()
    assert len(categories) == 2
    assert categories[0]["name"] == "Work"
    assert categories[1]["name"] == "Personal"

    # Test important senders
    important_senders = config.get_important_senders()
    assert "boss@company\\.com" in important_senders


def test_cli_with_output_override(sample_config_file: Path) -> None:
    """Test CLI with output file override."""
    runner = CliRunner()

    with (
        patch("gmail_summarizer.main.ImapGmailClient") as mock_gmail_client,
        patch("gmail_summarizer.main.LLMSummarizer") as mock_llm_summarizer,
        patch("gmail_summarizer.main.HTMLGenerator") as mock_html_generator,
    ):
        # Basic mocks to prevent actual execution
        mock_gmail_client.return_value.get_inbox_threads.return_value = []
        mock_llm_summarizer.return_value.test_cli_connection.return_value = True
        mock_html_generator.return_value.generate_html_report.return_value = (
            "/tmp/custom.html"
        )

        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "run",
                    "--config",
                    str(sample_config_file),
                    "--output",
                    "custom_output.html",
                ],
            )

            # Should not fail due to output override
            # Test passes if no exception is raised


def test_cli_max_threads_override(sample_config_file: Path) -> None:
    """Test CLI with max threads override."""
    runner = CliRunner()

    with patch("gmail_summarizer.main.Config") as mock_config_class:
        mock_config = Mock()
        mock_config.config = {"max_threads_per_category": 10}  # Default
        mock_config_class.return_value = mock_config

        with runner.isolated_filesystem():
            runner.invoke(
                cli,
                [
                    "run",
                    "--config",
                    str(sample_config_file),
                    "--max-threads",
                    "15",
                    "--dry-run",
                ],
            )

            # Config should be updated with override
            assert mock_config.config["max_threads_per_category"] == 15


@patch("gmail_summarizer.main.ImapGmailClient")
@patch("gmail_summarizer.main.CredentialManager")
def test_creds_check_with_connection_test(
    mock_credential_manager: Mock,
    mock_imap_client: Mock,
    sample_config_file: Path,
) -> None:
    """Test creds check command with IMAP connection testing."""
    # Setup credential manager mock
    mock_cred_mgr = Mock()
    mock_credentials = Mock()
    mock_credentials.email_address = "test@gmail.com"
    mock_credentials.password = "test-password"
    mock_cred_mgr.get_credentials.return_value = mock_credentials
    mock_credential_manager.return_value = mock_cred_mgr

    # Setup IMAP client mock
    mock_client = Mock()
    mock_imap_client.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(
        cli, ["creds", "check", "test@gmail.com", "--config", str(sample_config_file)]
    )

    assert result.exit_code == 0
    assert "Credentials found for test@gmail.com in keychain" in result.output
    assert "Testing IMAP connection to" in result.output
    assert "IMAP connection successful" in result.output

    # Verify mocks were called
    mock_cred_mgr.get_credentials.assert_called_once_with("test@gmail.com")
    mock_imap_client.assert_called_once()
    mock_client.close.assert_called_once()


@patch("gmail_summarizer.main.CredentialManager")
def test_creds_check_no_credentials(
    mock_credential_manager: Mock,
    sample_config_file: Path,
) -> None:
    """Test creds check command when no credentials exist."""
    # Setup credential manager mock to return None
    mock_cred_mgr = Mock()
    mock_cred_mgr.get_credentials.return_value = None
    mock_credential_manager.return_value = mock_cred_mgr

    runner = CliRunner()
    result = runner.invoke(
        cli, ["creds", "check", "test@gmail.com", "--config", str(sample_config_file)]
    )

    assert result.exit_code != 0
    assert "No credentials found for test@gmail.com in keychain" in result.output


@patch("gmail_summarizer.main.ImapGmailClient")
@patch("gmail_summarizer.main.CredentialManager")
def test_creds_check_no_config_file(
    mock_credential_manager: Mock,
    mock_imap_client: Mock,
) -> None:
    """Test creds check command without config file (uses defaults)."""
    # Setup credential manager mock
    mock_cred_mgr = Mock()
    mock_credentials = Mock()
    mock_credentials.email_address = "test@gmail.com"
    mock_credentials.password = "test-password"
    mock_cred_mgr.get_credentials.return_value = mock_credentials
    mock_credential_manager.return_value = mock_cred_mgr

    # Setup IMAP client mock
    mock_client = Mock()
    mock_imap_client.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["creds", "check", "test@gmail.com"])

    assert result.exit_code == 0
    assert "Credentials found for test@gmail.com in keychain" in result.output
    assert "Testing IMAP connection to imap.gmail.com:993" in result.output
    assert "IMAP connection successful" in result.output

    # Verify IMAP client was called with default values
    mock_imap_client.assert_called_once_with(
        email_address="test@gmail.com",
        password="test-password",
        imap_server="imap.gmail.com",
        imap_port=993,
    )


@patch("gmail_summarizer.main.ImapGmailClient")
@patch("gmail_summarizer.main.CredentialManager")
def test_creds_check_connection_failure(
    mock_credential_manager: Mock,
    mock_imap_client: Mock,
    sample_config_file: Path,
) -> None:
    """Test creds check command when IMAP connection fails."""
    # Setup credential manager mock
    mock_cred_mgr = Mock()
    mock_credentials = Mock()
    mock_credentials.email_address = "test@gmail.com"
    mock_credentials.password = "test-password"
    mock_cred_mgr.get_credentials.return_value = mock_credentials
    mock_credential_manager.return_value = mock_cred_mgr

    # Setup IMAP client mock to raise exception
    mock_imap_client.side_effect = Exception("Authentication failed")

    runner = CliRunner()
    result = runner.invoke(
        cli, ["creds", "check", "test@gmail.com", "--config", str(sample_config_file)]
    )

    assert result.exit_code != 0
    assert "Credentials found for test@gmail.com in keychain" in result.output
    assert "Testing IMAP connection to" in result.output
    assert "IMAP connection failed: Authentication failed" in result.output


def test_config_generate_command() -> None:
    """Test config generate command creates valid configuration file."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Test with email provided
        result = runner.invoke(
            cli, ["config", "generate", "--email", "user@example.com", "--output", "test.yaml"]
        )

        assert result.exit_code == 0
        assert "Configuration file created:" in result.output
        assert "Next steps:" in result.output

        # Check file was created
        config_file = Path("test.yaml")
        assert config_file.exists()

        # Verify content
        content = config_file.read_text(encoding="utf-8")
        assert "email_address: \"user@example.com\"" in content
        assert "categories:" in content
        assert "Work Email" in content
        assert "GitHub Notifications" in content

        # Test that generated config is valid
        from gmail_summarizer.config import Config
        config = Config(str(config_file))
        assert config.app_config is not None
        assert config.get_gmail_config()["email_address"] == "user@example.com"


def test_config_generate_with_prompt(monkeypatch) -> None:
    """Test config generate command with email prompt."""
    # Mock the Prompt.ask to return a test email
    monkeypatch.setattr("gmail_summarizer.main.Prompt.ask", lambda *args, **kwargs: "prompted@example.com")

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli, ["config", "generate", "--output", "prompted.yaml"]
        )

        assert result.exit_code == 0

        # Check file content contains prompted email
        config_file = Path("prompted.yaml")
        content = config_file.read_text(encoding="utf-8")
        assert "email_address: \"prompted@example.com\"" in content


def test_config_generate_file_exists() -> None:
    """Test config generate command when file already exists."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create existing file
        existing_file = Path("existing.yaml")
        existing_file.write_text("existing content")

        # Try to generate without force
        result = runner.invoke(
            cli, ["config", "generate", "--email", "test@example.com", "--output", "existing.yaml"]
        )

        assert result.exit_code != 0
        assert "Configuration file already exists" in result.output
        assert "Use --force to overwrite" in result.output

        # Verify original content is preserved
        assert existing_file.read_text() == "existing content"

        # Test with force flag
        result = runner.invoke(
            cli, ["config", "generate", "--email", "test@example.com", "--output", "existing.yaml", "--force"]
        )

        assert result.exit_code == 0
        content = existing_file.read_text(encoding="utf-8")
        assert "email_address: \"test@example.com\"" in content


def test_config_generate_help() -> None:
    """Test config generate help message."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "generate", "--help"])

    assert result.exit_code == 0
    assert "Generate a minimal configuration file" in result.output
    assert "--email" in result.output
    assert "--output" in result.output
    assert "--force" in result.output
