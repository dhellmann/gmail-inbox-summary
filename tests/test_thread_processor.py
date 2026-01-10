"""Tests for thread_processor module."""

from unittest.mock import Mock

from gmail_summarizer.config import Config
from gmail_summarizer.thread_processor import ThreadProcessor


def test_thread_processor_initialization() -> None:
    """Test ThreadProcessor initialization."""
    config = Mock(spec=Config)
    config.get_categories.return_value = [
        {
            "name": "Test Category",
            "criteria": {"labels": ["IMPORTANT"]},
            "summary_prompt": "Test prompt",
        }
    ]
    config.get_important_senders.return_value = ["boss@company.com"]

    processor = ThreadProcessor(config)

    assert processor.config == config
    assert len(processor.categories) == 1
    assert processor.important_senders == ["boss@company.com"]


def test_categorize_thread_with_label_match() -> None:
    """Test thread categorization with label matching."""
    config = Mock(spec=Config)
    config.get_categories.return_value = [
        {
            "name": "Important",
            "criteria": {"labels": ["IMPORTANT"]},
            "summary_prompt": "Test prompt",
        }
    ]
    config.get_important_senders.return_value = []

    processor = ThreadProcessor(config)

    thread = {"id": "thread123"}
    messages = [
        {
            "id": "msg1",
            "label_ids": ["INBOX", "IMPORTANT"],
            "from": "user@example.com",
            "subject": "Test Subject",
        }
    ]

    category = processor.categorize_thread(thread, messages)

    assert category is not None
    assert category["name"] == "Important"


def test_categorize_thread_with_from_pattern_match() -> None:
    """Test thread categorization with sender pattern matching."""
    config = Mock(spec=Config)
    config.get_categories.return_value = [
        {
            "name": "Jira",
            "criteria": {"from_patterns": ["jira@.*"]},
            "summary_prompt": "Test prompt",
        }
    ]
    config.get_important_senders.return_value = []

    processor = ThreadProcessor(config)

    thread = {"id": "thread123"}
    messages = [
        {
            "id": "msg1",
            "label_ids": ["INBOX"],
            "from": "jira@company.com",
            "subject": "[JIRA] Ticket Update",
        }
    ]

    category = processor.categorize_thread(thread, messages)

    assert category is not None
    assert category["name"] == "Jira"


def test_categorize_thread_no_match() -> None:
    """Test thread categorization when no criteria match."""
    config = Mock(spec=Config)
    config.get_categories.return_value = [
        {
            "name": "Important",
            "criteria": {"labels": ["IMPORTANT"]},
            "summary_prompt": "Test prompt",
        }
    ]
    config.get_important_senders.return_value = []

    processor = ThreadProcessor(config)

    thread = {"id": "thread123"}
    messages = [
        {
            "id": "msg1",
            "label_ids": ["INBOX"],
            "from": "user@example.com",
            "subject": "Regular Email",
        }
    ]

    category = processor.categorize_thread(thread, messages)

    assert category is None


def test_is_important_sender() -> None:
    """Test important sender detection."""
    config = Mock(spec=Config)
    config.get_categories.return_value = []
    config.get_important_senders.return_value = ["boss@company.com", ".*@alerts\\..*"]

    processor = ThreadProcessor(config)

    # Test exact match
    message1 = {"from": "boss@company.com"}
    assert processor.is_important_sender(message1) is True

    # Test regex match
    message2 = {"from": "system@alerts.company.com"}
    assert processor.is_important_sender(message2) is True

    # Test no match
    message3 = {"from": "user@example.com"}
    assert processor.is_important_sender(message3) is False


def test_extract_thread_subject() -> None:
    """Test thread subject extraction."""
    config = Mock(spec=Config)
    config.get_categories.return_value = []
    config.get_important_senders.return_value = []

    processor = ThreadProcessor(config)

    messages = [
        {"subject": "Original Subject"},
        {"subject": "Re: Original Subject"},
    ]

    subject = processor._extract_thread_subject(messages)
    assert subject == "Original Subject"


def test_extract_participants() -> None:
    """Test participant extraction from thread."""
    config = Mock(spec=Config)
    config.get_categories.return_value = []
    config.get_important_senders.return_value = []

    processor = ThreadProcessor(config)

    messages = [
        {"from": "user1@example.com", "to": "user2@example.com"},
        {"from": "user2@example.com", "to": "user1@example.com, user3@example.com"},
    ]

    participants = processor._extract_participants(messages)

    # Should have unique participants
    assert len(participants) == 3
    assert "user1@example.com" in participants
    assert "user2@example.com" in participants
    assert "user3@example.com" in participants


def test_process_threads() -> None:
    """Test processing multiple threads."""
    config = Mock(spec=Config)
    config.get_categories.return_value = [
        {
            "name": "Important",
            "criteria": {"labels": ["IMPORTANT"]},
            "summary_prompt": "Test prompt",
        },
        {
            "name": "Everything Else",
            "criteria": {},
            "summary_prompt": "Default prompt",
        },
    ]
    config.get_important_senders.return_value = ["boss@company.com"]
    config.get_max_threads_per_category.return_value = 50

    processor = ThreadProcessor(config)

    threads_data = [
        (
            {"id": "thread1"},
            [
                {
                    "label_ids": ["IMPORTANT"],
                    "from": "boss@company.com",
                    "subject": "Important",
                }
            ],
        ),
        (
            {"id": "thread2"},
            [
                {
                    "label_ids": ["INBOX"],
                    "from": "user@example.com",
                    "subject": "Regular",
                }
            ],
        ),
    ]

    result = processor.process_threads(threads_data)

    assert "Important" in result
    assert "Everything Else" in result
    assert len(result["Important"]) == 1
    assert len(result["Everything Else"]) == 1

    # Check that important sender is detected
    important_thread = result["Important"][0]
    assert important_thread["has_important_sender"] is True

    regular_thread = result["Everything Else"][0]
    assert regular_thread["has_important_sender"] is False
