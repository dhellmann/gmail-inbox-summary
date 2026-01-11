"""Tests for llm_summarizer module."""

import subprocess
from typing import Any
from unittest.mock import Mock
from unittest.mock import patch

from gmail_summarizer.config import Config
from gmail_summarizer.llm_summarizer import LLMSummarizer


def test_llm_summarizer_initialization() -> None:
    """Test LLMSummarizer initialization."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"cli_path": "claude", "timeout": 30}

    summarizer = LLMSummarizer(config)

    assert summarizer.config == config
    assert summarizer.cli_path == "claude"
    assert summarizer.timeout == 30


def test_prepare_thread_content() -> None:
    """Test thread content preparation."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {}

    summarizer = LLMSummarizer(config)

    thread_data = {
        "subject": "Test Subject",
        "participants": ["user1@example.com", "user2@example.com"],
        "messages": [
            {"from": "user1@example.com", "date": "2024-01-01", "body": "Hello there!"},
            {"from": "user2@example.com", "date": "2024-01-01", "body": "Hi back!"},
        ],
    }

    content = summarizer._prepare_thread_content(thread_data)

    assert "Subject: Test Subject" in content
    assert "user1@example.com, user2@example.com" in content
    assert "Total Messages: 2" in content
    assert "Hello there!" in content
    assert "Hi back!" in content


def test_prepare_thread_content_truncates_long_messages() -> None:
    """Test that very long message bodies are truncated."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {}

    summarizer = LLMSummarizer(config)

    long_body = "A" * 3000  # Longer than 2000 char limit
    thread_data = {
        "subject": "Test",
        "participants": ["user@example.com"],
        "messages": [
            {"from": "user@example.com", "date": "2024-01-01", "body": long_body}
        ],
    }

    content = summarizer._prepare_thread_content(thread_data)

    assert "AAA..." in content
    assert len(content) < len(long_body) + 1000  # Should be significantly shorter


@patch("subprocess.run")
def test_call_claude_cli_success(mock_subprocess: Mock) -> None:
    """Test successful Claude CLI call."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"cli_path": "claude", "timeout": 30}

    summarizer = LLMSummarizer(config)

    # Mock successful subprocess call
    mock_result = Mock()
    mock_result.stdout = "This is a test summary"
    mock_result.returncode = 0
    mock_subprocess.return_value = mock_result

    result = summarizer._call_claude_cli("test content", "test prompt")

    assert result == "This is a test summary"
    mock_subprocess.assert_called_once()

    # Check that the call included the expected arguments
    args, kwargs = mock_subprocess.call_args
    assert args[0][0] == "claude"
    assert args[0][1] == "--print"
    assert "input" in kwargs  # Content is passed via stdin


@patch("subprocess.run")
def test_call_claude_cli_file_not_found(mock_subprocess: Mock) -> None:
    """Test Claude CLI call when CLI is not found."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {
        "cli_path": "nonexistent-claude",
        "timeout": 30,
    }

    summarizer = LLMSummarizer(config)

    mock_subprocess.side_effect = FileNotFoundError("Command not found")

    try:
        summarizer._call_claude_cli("test content", "test prompt")
        raise AssertionError("Expected FileNotFoundError")
    except FileNotFoundError as e:
        assert "Claude CLI not found" in str(e)


@patch("subprocess.run")
def test_call_claude_cli_timeout(mock_subprocess: Mock) -> None:
    """Test Claude CLI call timeout."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"cli_path": "claude", "timeout": 1}

    summarizer = LLMSummarizer(config)

    mock_subprocess.side_effect = subprocess.TimeoutExpired("claude", 1)

    try:
        summarizer._call_claude_cli("test content", "test prompt")
        raise AssertionError("Expected TimeoutExpired")
    except subprocess.TimeoutExpired as e:
        assert "timed out" in str(e)


@patch("subprocess.run")
def test_call_claude_cli_error(mock_subprocess: Mock) -> None:
    """Test Claude CLI call with process error."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"cli_path": "claude", "timeout": 30}

    summarizer = LLMSummarizer(config)

    mock_subprocess.side_effect = subprocess.CalledProcessError(
        1, ["claude"], stderr="Some error"
    )

    try:
        summarizer._call_claude_cli("test content", "test prompt")
        raise AssertionError("Expected CalledProcessError")
    except subprocess.CalledProcessError:
        pass  # Expected behavior


@patch.object(LLMSummarizer, "_call_claude_cli")
def test_summarize_thread_success(mock_call_cli: Mock) -> None:
    """Test successful thread summarization."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {}

    summarizer = LLMSummarizer(config)
    mock_call_cli.return_value = "Test summary"

    thread_data = {
        "thread": {"id": "thread123"},
        "subject": "Test Subject",
        "participants": ["user@example.com"],
        "messages": [{"from": "user@example.com", "body": "Test"}],
    }

    category = {"summary_prompt": "Summarize this thread"}

    result = summarizer.summarize_thread(thread_data, category)

    assert result["summary"] == "Test summary"
    assert result["summary_generated"] is True
    assert result["summary_error"] is None
    mock_call_cli.assert_called_once()


@patch.object(LLMSummarizer, "_call_claude_cli")
def test_summarize_thread_error(mock_call_cli: Mock) -> None:
    """Test thread summarization with error."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {}

    summarizer = LLMSummarizer(config)
    mock_call_cli.side_effect = Exception("Test error")

    thread_data = {
        "thread": {"id": "thread123"},
        "subject": "Test Subject",
        "participants": ["user@example.com"],
        "messages": [{"from": "user@example.com", "body": "Test"}],
    }

    category = {"summary_prompt": "Summarize this thread"}

    result = summarizer.summarize_thread(thread_data, category)

    assert "Error generating summary" in result["summary"]
    assert result["summary_generated"] is False
    assert result["summary_error"] == "Test error"


def test_summarize_threads_batch() -> None:
    """Test batch summarization of threads."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {}
    config.get_categories.return_value = [
        {"name": "Test Category", "summary_prompt": "Test prompt"}
    ]

    summarizer = LLMSummarizer(config)

    # Mock the summarize_thread method
    def mock_summarize(thread_data: dict, category: dict) -> dict:
        result = thread_data.copy()
        result.update(
            {
                "summary": f"Summary for {thread_data['thread']['id']}",
                "summary_generated": True,
                "summary_error": None,
            }
        )
        return result

    summarizer.summarize_thread = mock_summarize  # type: ignore[method-assign]

    categorized_threads = {
        "Test Category": [
            {
                "thread": {"id": "thread1"},
                "subject": "Test 1",
                "participants": [],
                "messages": [],
            },
            {
                "thread": {"id": "thread2"},
                "subject": "Test 2",
                "participants": [],
                "messages": [],
            },
        ]
    }

    result = summarizer.summarize_threads_batch(categorized_threads)

    assert "Test Category" in result
    assert len(result["Test Category"]) == 2
    assert result["Test Category"][0]["summary"] == "Summary for thread1"
    assert result["Test Category"][1]["summary"] == "Summary for thread2"


def test_get_summarization_stats() -> None:
    """Test summarization statistics generation."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {}

    summarizer = LLMSummarizer(config)

    summarized_threads: dict[str, list[dict[str, Any]]] = {
        "Category1": [
            {"summary_generated": True},
            {"summary_generated": True},
            {"summary_generated": False, "summary_error": "Error 1"},
        ],
        "Category2": [
            {"summary_generated": False, "summary_error": "Error 1"},
            {"summary_generated": False, "summary_error": "Error 2"},
        ],
    }

    stats = summarizer.get_summarization_stats(summarized_threads)

    assert stats["total_threads"] == 5
    assert stats["successful_summaries"] == 2
    assert stats["failed_summaries"] == 3
    assert stats["success_rate"] == 0.4
    assert stats["error_types"]["Error 1"] == 2
    assert stats["error_types"]["Error 2"] == 1


@patch("subprocess.run")
def test_test_cli_connection_success(mock_subprocess: Mock) -> None:
    """Test successful CLI connection test."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"cli_path": "claude"}

    summarizer = LLMSummarizer(config)

    mock_result = Mock()
    mock_result.stdout = "claude version 1.0.0"
    mock_subprocess.return_value = mock_result

    result = summarizer.test_cli_connection()

    assert result is True
    mock_subprocess.assert_called_once_with(
        ["claude", "--version"], capture_output=True, text=True, timeout=10, check=True
    )


@patch("subprocess.run")
def test_test_cli_connection_failure(mock_subprocess: Mock) -> None:
    """Test CLI connection test failure."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"cli_path": "nonexistent-claude"}

    summarizer = LLMSummarizer(config)

    mock_subprocess.side_effect = FileNotFoundError("Command not found")

    result = summarizer.test_cli_connection()

    assert result is False


def test_estimate_token_count() -> None:
    """Test token count estimation."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {}

    summarizer = LLMSummarizer(config)

    # Test with known text
    text = "Hello world"  # 11 characters
    tokens = summarizer._estimate_token_count(text)

    assert tokens == 2  # 11 // 4 = 2


def test_truncate_content_if_needed() -> None:
    """Test content truncation."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {}

    summarizer = LLMSummarizer(config)

    # Test with short content (no truncation needed)
    short_content = "This is short content"
    result = summarizer._truncate_content_if_needed(short_content, max_tokens=1000)
    assert result == short_content

    # Test with long content (truncation needed)
    long_content = "A" * 10000
    result = summarizer._truncate_content_if_needed(long_content, max_tokens=100)
    assert len(result) < len(long_content)
    assert "[Content truncated due to length...]" in result


def test_parallel_summarization_initialization() -> None:
    """Test that LLMSummarizer initializes with concurrency setting."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {
        "cli_path": "claude",
        "timeout": 30,
        "concurrency": 10,
    }

    summarizer = LLMSummarizer(config)

    assert summarizer.concurrency == 10


def test_parallel_summarization_without_cache() -> None:
    """Test parallel summarization without cache manager."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"concurrency": 2}
    config.get_categories.return_value = [
        {"name": "Test Category", "summary_prompt": "Test prompt"}
    ]

    summarizer = LLMSummarizer(config)

    # Mock the summarize_thread method to simulate processing
    call_count = 0

    def mock_summarize(thread_data: dict, category: dict) -> dict:
        nonlocal call_count
        call_count += 1
        result = thread_data.copy()
        result.update(
            {
                "summary": f"Summary for {thread_data['thread']['id']}",
                "summary_generated": True,
                "summary_error": None,
            }
        )
        return result

    summarizer.summarize_thread = mock_summarize  # type: ignore[method-assign]

    categorized_threads = {
        "Test Category": [
            {
                "thread": {"id": "thread1"},
                "subject": "Test 1",
                "participants": [],
                "messages": [{"id": "msg1", "body": "content1"}],
            },
            {
                "thread": {"id": "thread2"},
                "subject": "Test 2",
                "participants": [],
                "messages": [{"id": "msg2", "body": "content2"}],
            },
        ]
    }

    # Track progress calls
    progress_calls = []

    def mock_progress(completed: int, description: str) -> None:
        progress_calls.append((completed, description))

    result = summarizer.summarize_threads_parallel(
        categorized_threads, None, mock_progress
    )

    # Verify results
    assert "Test Category" in result
    assert len(result["Test Category"]) == 2
    assert result["Test Category"][0]["summary"] == "Summary for thread1"
    assert result["Test Category"][1]["summary"] == "Summary for thread2"

    # Verify all threads were processed
    assert call_count == 2

    # Verify progress was called
    assert len(progress_calls) == 2
    assert progress_calls[-1][0] == 2  # Final count


def test_parallel_summarization_with_cache() -> None:
    """Test parallel summarization with cache manager."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"concurrency": 2}
    config.get_categories.return_value = [
        {"name": "Test Category", "summary_prompt": "Test prompt"}
    ]

    summarizer = LLMSummarizer(config)

    # Mock cache manager
    cache_manager = Mock()
    cache_manager.is_thread_cached.side_effect = [
        True,
        False,
    ]  # First cached, second not
    cache_manager.get_cached_summary.return_value = {
        "summary_data": {
            "thread": {"id": "thread1"},
            "summary": "Cached summary for thread1",
            "summary_generated": True,
            "summary_error": None,
        }
    }

    # Mock the summarize_thread method for non-cached threads
    def mock_summarize(thread_data: dict, category: dict) -> dict:
        result = thread_data.copy()
        result.update(
            {
                "summary": f"New summary for {thread_data['thread']['id']}",
                "summary_generated": True,
                "summary_error": None,
            }
        )
        return result

    summarizer.summarize_thread = mock_summarize  # type: ignore[method-assign]

    categorized_threads = {
        "Test Category": [
            {
                "thread": {"id": "thread1"},
                "subject": "Test 1",
                "participants": [],
                "messages": [{"id": "msg1", "body": "content1"}],
            },
            {
                "thread": {"id": "thread2"},
                "subject": "Test 2",
                "participants": [],
                "messages": [{"id": "msg2", "body": "content2"}],
            },
        ]
    }

    result = summarizer.summarize_threads_parallel(categorized_threads, cache_manager)

    # Verify results
    assert "Test Category" in result
    assert len(result["Test Category"]) == 2
    assert result["Test Category"][0]["summary"] == "Cached summary for thread1"
    assert result["Test Category"][1]["summary"] == "New summary for thread2"

    # Verify cache operations
    assert cache_manager.is_thread_cached.call_count == 2
    cache_manager.cache_thread_and_summary.assert_called_once()  # Only for non-cached thread


def test_parallel_summarization_error_handling() -> None:
    """Test parallel summarization error handling."""
    config = Mock(spec=Config)
    config.get_claude_config.return_value = {"concurrency": 2}
    config.get_categories.return_value = [
        {"name": "Test Category", "summary_prompt": "Test prompt"}
    ]

    summarizer = LLMSummarizer(config)

    # Mock the summarize_thread method to raise an error for the first thread
    def mock_summarize(thread_data: dict, category: dict) -> dict:
        if thread_data["thread"]["id"] == "thread1":
            raise ValueError("Test error for thread1")

        result = thread_data.copy()
        result.update(
            {
                "summary": f"Summary for {thread_data['thread']['id']}",
                "summary_generated": True,
                "summary_error": None,
            }
        )
        return result

    summarizer.summarize_thread = mock_summarize  # type: ignore[method-assign]

    categorized_threads = {
        "Test Category": [
            {
                "thread": {"id": "thread1"},
                "subject": "Test 1",
                "participants": [],
                "messages": [{"id": "msg1", "body": "content1"}],
            },
            {
                "thread": {"id": "thread2"},
                "subject": "Test 2",
                "participants": [],
                "messages": [{"id": "msg2", "body": "content2"}],
            },
        ]
    }

    result = summarizer.summarize_threads_parallel(categorized_threads)

    # Verify results - both threads should be present, one with error
    assert "Test Category" in result
    assert len(result["Test Category"]) == 2

    # Check that error was handled properly
    thread1_result = next(
        t for t in result["Test Category"] if t["thread"]["id"] == "thread1"
    )
    thread2_result = next(
        t for t in result["Test Category"] if t["thread"]["id"] == "thread2"
    )

    assert "Error generating summary" in thread1_result["summary"]
    assert thread1_result["summary_generated"] is False
    assert "Test error for thread1" in thread1_result["summary_error"]

    assert thread2_result["summary"] == "Summary for thread2"
    assert thread2_result["summary_generated"] is True
