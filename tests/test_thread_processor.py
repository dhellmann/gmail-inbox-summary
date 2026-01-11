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


def test_gmail_url_generation() -> None:
    """Test Gmail URL generation for different thread ID formats."""
    config = Mock(spec=Config)
    config.get_categories.return_value = []
    config.get_important_senders.return_value = []
    processor = ThreadProcessor(config)

    # Test IMAP-style thread ID without subject (fallback to inbox)
    imap_thread = {"id": "thread_12345"}
    imap_url = processor._generate_gmail_url(imap_thread)
    assert imap_url == "https://mail.google.com/mail/u/0/#inbox"

    # Test IMAP-style thread ID with subject
    imap_url_with_subject = processor._generate_gmail_url(imap_thread, "Test Subject")
    assert (
        imap_url_with_subject
        == "https://mail.google.com/mail/u/0/#search/subject:Test%20Subject"
    )

    # Test Gmail API thread ID
    api_thread = {"id": "1234567890abcdef"}
    api_url = processor._generate_gmail_url(api_thread)
    assert api_url == "https://mail.google.com/mail/u/0/#inbox/1234567890abcdef"

    # Test empty thread ID
    empty_thread = {"id": ""}
    empty_url = processor._generate_gmail_url(empty_thread)
    assert empty_url == "https://mail.google.com/mail/u/0/#inbox/"

    # Test thread without ID
    no_id_thread: dict[str, str] = {}
    no_id_url = processor._generate_gmail_url(no_id_thread)
    assert no_id_url == "https://mail.google.com/mail/u/0/#inbox/"


def test_process_threads_includes_gmail_url() -> None:
    """Test that process_threads includes Gmail URL in thread data."""
    config = Mock(spec=Config)
    config.get_categories.return_value = [
        {
            "name": "Important",
            "criteria": {"labels": ["IMPORTANT"]},
            "summary_prompt": "Test prompt",
        }
    ]
    config.get_important_senders.return_value = ["boss@company.com"]
    config.get_max_threads_per_category.return_value = 50
    processor = ThreadProcessor(config)

    threads_data = [
        (
            {"id": "thread_12345"},
            [
                {
                    "label_ids": ["IMPORTANT"],
                    "from": "boss@company.com",
                    "subject": "Test Subject",
                }
            ],
        )
    ]

    result = processor.process_threads(threads_data)

    # Get the processed thread
    processed_thread = result["Important"][0]

    # Verify Gmail URL is included
    assert "gmail_url" in processed_thread
    assert (
        processed_thread["gmail_url"]
        == "https://mail.google.com/mail/u/0/#search/subject:Test%20Subject"
    )


def test_default_everything_category_matches_all() -> None:
    """Test that the default 'Everything' category matches all emails."""
    config = Mock(spec=Config)
    # Set up config with default "Everything" category (empty criteria)
    config.get_categories.return_value = [
        {
            "name": "Everything",
            "criteria": {
                "from_patterns": [],
                "to_patterns": [],
                "subject_patterns": [],
                "content_patterns": [],
                "headers": {},
                "labels": [],
            },
            "summary_prompt": "Provide a brief summary of this email thread.",
        }
    ]
    config.get_important_senders.return_value = []
    config.get_max_threads_per_category.return_value = 50
    processor = ThreadProcessor(config)

    # Test various types of threads
    threads_data = [
        (
            {"id": "thread1"},
            [
                {
                    "label_ids": ["INBOX"],
                    "from": "user1@example.com",
                    "subject": "Random subject",
                }
            ],
        ),
        (
            {"id": "thread2"},
            [
                {
                    "label_ids": ["IMPORTANT", "WORK"],
                    "from": "boss@company.com",
                    "subject": "[URGENT] Meeting tomorrow",
                }
            ],
        ),
        (
            {"id": "thread3"},
            [
                {
                    "label_ids": ["CATEGORY_PROMOTIONS"],
                    "from": "noreply@newsletter.com",
                    "subject": "Weekly newsletter",
                }
            ],
        ),
    ]

    result = processor.process_threads(threads_data)

    # All threads should be categorized under "Everything"
    assert "Everything" in result
    assert len(result["Everything"]) == 3

    # Verify all threads are in the Everything category
    subjects = [thread["subject"] for thread in result["Everything"]]
    assert "Random subject" in subjects
    assert "[URGENT] Meeting tomorrow" in subjects
    assert "Weekly newsletter" in subjects


def test_is_empty_criteria() -> None:
    """Test the _is_empty_criteria method correctly identifies catch-all criteria."""
    config = Mock(spec=Config)
    config.get_categories.return_value = []
    config.get_important_senders.return_value = []
    processor = ThreadProcessor(config)

    # Test empty dict
    assert processor._is_empty_criteria({}) is True

    # Test criteria with all empty lists
    empty_criteria: dict[str, list[str] | dict[str, str]] = {
        "from_patterns": [],
        "to_patterns": [],
        "subject_patterns": [],
        "content_patterns": [],
        "headers": {},
        "labels": [],
    }
    assert processor._is_empty_criteria(empty_criteria) is True

    # Test criteria with some fields missing (should still be empty)
    partial_empty: dict[str, list[str]] = {
        "from_patterns": [],
        "labels": [],
    }
    assert processor._is_empty_criteria(partial_empty) is True

    # Test criteria with non-empty from_patterns
    non_empty_from = {
        "from_patterns": ["test@example.com"],
        "to_patterns": [],
        "subject_patterns": [],
        "content_patterns": [],
        "headers": {},
        "labels": [],
    }
    assert processor._is_empty_criteria(non_empty_from) is False

    # Test criteria with non-empty labels
    non_empty_labels = {
        "from_patterns": [],
        "to_patterns": [],
        "subject_patterns": [],
        "content_patterns": [],
        "headers": {},
        "labels": ["IMPORTANT"],
    }
    assert processor._is_empty_criteria(non_empty_labels) is False

    # Test criteria with non-empty headers
    non_empty_headers = {
        "from_patterns": [],
        "to_patterns": [],
        "subject_patterns": [],
        "content_patterns": [],
        "headers": {"List-Id": "test@example.com"},
        "labels": [],
    }
    assert processor._is_empty_criteria(non_empty_headers) is False
