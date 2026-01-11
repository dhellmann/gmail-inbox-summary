"""Thread processing and categorization logic."""

import logging
import re
from typing import Any

from .config import Config

logger = logging.getLogger(__name__)


class ThreadProcessor:
    """Process and categorize Gmail threads based on configurable criteria."""

    def __init__(self, config: Config):
        """Initialize thread processor.

        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.categories = config.get_categories()
        self.important_senders = config.get_important_senders()

    def categorize_thread(
        self, thread: dict[str, Any], messages: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Categorize a thread based on configured criteria.

        Args:
            thread: Gmail thread object
            messages: List of message data from the thread

        Returns:
            Category object if match found, None otherwise
        """
        for category in self.categories:
            if self._matches_category(thread, messages, category):
                logger.debug(
                    f"Thread {thread.get('id')} matched category: {category['name']}"
                )
                return category

        return None

    def _matches_category(
        self,
        thread: dict[str, Any],
        messages: list[dict[str, Any]],
        category: dict[str, Any],
    ) -> bool:
        """Check if a thread matches a specific category criteria.

        Args:
            thread: Gmail thread object
            messages: List of message data from the thread
            category: Category configuration

        Returns:
            True if thread matches category criteria
        """
        criteria = category.get("criteria", {})

        # Empty criteria matches everything (catch-all)
        if not criteria:
            return True

        # Criteria with all empty lists/dicts also matches everything (catch-all)
        if self._is_empty_criteria(criteria):
            return True

        # Check each message in the thread
        category_name = category.get("name", "")
        for message in messages:
            if self._message_matches_criteria(message, criteria, category_name):
                return True

        # Log when no messages in thread match this category
        if logger.isEnabledFor(logging.DEBUG):
            subject = (
                messages[0].get("subject", "No Subject") if messages else "No Subject"
            )
            logger.debug(
                f"✗ Thread '{subject[:50]}...' does NOT match category '{category_name}'"
            )

        return False

    def _message_matches_criteria(
        self, message: dict[str, Any], criteria: dict[str, Any], category_name: str = ""
    ) -> bool:
        """Check if a message matches the given criteria.

        Args:
            message: Message data
            criteria: Matching criteria
            category_name: Name of category being tested (for verbose logging)

        Returns:
            True if message matches any criteria (OR logic between criteria types)
        """
        subject = message.get("subject", "No Subject")
        from_address = message.get("from", "")
        to_address = message.get("to", "")
        message_labels = message.get("label_ids", [])

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Message details: Subject='{subject}', From='{from_address}', To='{to_address}', Labels={message_labels}"
            )
            logger.debug(
                f"Testing message '{subject[:50]}...' against category '{category_name}'"
            )

        # Track if any criteria type matches (OR logic)
        any_match = False
        criteria_tested = False

        # Check Gmail labels
        if criteria.get("labels"):
            criteria_tested = True
            required_labels = criteria["labels"]
            match_result = any(label in message_labels for label in required_labels)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"  Labels check: {match_result} (required: {required_labels}, message has: {message_labels})"
                )
            if match_result:
                any_match = True

        # Check sender patterns (From header)
        if criteria.get("from_patterns"):
            criteria_tested = True
            match_result = self._matches_patterns(
                from_address, criteria["from_patterns"]
            )
            if logger.isEnabledFor(logging.DEBUG):
                matched_pattern = self._get_matching_pattern(
                    from_address, criteria["from_patterns"]
                )
                logger.debug(
                    f"  From pattern check: {match_result} ('{from_address}' vs {criteria['from_patterns']}) - matched: {matched_pattern}"
                )
            if match_result:
                any_match = True

        # Check recipient patterns (To header)
        if criteria.get("to_patterns"):
            criteria_tested = True
            to_address = message.get("to", "")
            match_result = self._matches_patterns(to_address, criteria["to_patterns"])
            if logger.isEnabledFor(logging.DEBUG):
                matched_pattern = self._get_matching_pattern(
                    to_address, criteria["to_patterns"]
                )
                logger.debug(
                    f"  To pattern check: {match_result} ('{to_address}' vs {criteria['to_patterns']}) - matched: {matched_pattern}"
                )
            if match_result:
                any_match = True

        # Check subject patterns
        if criteria.get("subject_patterns"):
            criteria_tested = True
            match_result = self._matches_patterns(subject, criteria["subject_patterns"])
            if logger.isEnabledFor(logging.DEBUG):
                matched_pattern = self._get_matching_pattern(
                    subject, criteria["subject_patterns"]
                )
                logger.debug(
                    f"  Subject pattern check: {match_result} ('{subject}' vs {criteria['subject_patterns']}) - matched: {matched_pattern}"
                )
            if match_result:
                any_match = True

        # Check message content patterns
        if criteria.get("content_patterns"):
            criteria_tested = True
            body = message.get("body", "")
            match_result = self._matches_patterns(body, criteria["content_patterns"])
            if logger.isEnabledFor(logging.DEBUG):
                matched_pattern = self._get_matching_pattern(
                    body, criteria["content_patterns"]
                )
                body_preview = (
                    body[:100].replace("\n", " ") + "..." if len(body) > 100 else body
                )
                logger.debug(
                    f"  Content pattern check: {match_result} ('{body_preview}' vs {criteria['content_patterns']}) - matched: {matched_pattern}"
                )
            if match_result:
                any_match = True

        # Check custom headers
        if criteria.get("headers"):
            criteria_tested = True
            headers = message.get("headers", {})
            for header_name, header_pattern in criteria["headers"].items():
                header_value = headers.get(header_name, "")
                match_result = self._matches_pattern(header_value, header_pattern)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"  Header '{header_name}' check: {match_result} ('{header_value}' vs '{header_pattern}')"
                    )
                if match_result:
                    any_match = True
                    break  # Short circuit on first header match

        # If no criteria were specified or tested, return False (shouldn't match catch-all here)
        if not criteria_tested:
            return False

        if logger.isEnabledFor(logging.DEBUG):
            if any_match:
                logger.debug(
                    f"  ✓ Message '{subject[:50]}...' MATCHES category '{category_name}' (OR logic)"
                )
            else:
                logger.debug(
                    f"  ✗ Message '{subject[:50]}...' does NOT match category '{category_name}' (no criteria matched)"
                )

        return any_match

    def _matches_patterns(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any of the given regex patterns.

        Args:
            text: Text to check
            patterns: List of regex patterns

        Returns:
            True if text matches any pattern
        """
        for pattern in patterns:
            if self._matches_pattern(text, pattern):
                return True
        return False

    def _get_matching_pattern(self, text: str, patterns: list[str]) -> str | None:
        """Get the first pattern that matches the given text.

        Args:
            text: Text to check
            patterns: List of regex patterns

        Returns:
            The first matching pattern, or None if no match
        """
        for pattern in patterns:
            if self._matches_pattern(text, pattern):
                return pattern
        return None

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a single regex pattern.

        Args:
            text: Text to check
            pattern: Regex pattern

        Returns:
            True if text matches pattern
        """
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            return False

    def is_important_sender(self, message: dict[str, Any]) -> bool:
        """Check if message is from an important sender.

        Args:
            message: Message data

        Returns:
            True if sender is marked as important
        """
        from_address = message.get("from", "")
        return self._matches_patterns(from_address, self.important_senders)

    def process_threads(
        self, threads_data: list[tuple[dict[str, Any], list[dict[str, Any]]]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Process and categorize multiple threads.

        Args:
            threads_data: List of (thread, messages) tuples

        Returns:
            Dictionary mapping category names to lists of thread data
        """
        categorized_threads: dict[str, list[dict[str, Any]]] = {}

        # Initialize category buckets
        for cat_config in self.categories:
            categorized_threads[cat_config["name"]] = []

        # Process each thread
        for thread, messages in threads_data:
            category = self.categorize_thread(thread, messages)
            if category is not None:
                # Add thread data with additional metadata
                thread_data = {
                    "thread": thread,
                    "messages": messages,
                    "category": category,  # type: ignore[assignment]
                    "has_important_sender": any(
                        self.is_important_sender(msg) for msg in messages
                    ),
                    "subject": self._extract_thread_subject(messages),
                    "participants": self._extract_participants(messages),
                    "message_count": len(messages),
                    "most_recent_date": self._extract_most_recent_date(messages),
                    "gmail_url": self._generate_gmail_url(
                        thread, self._extract_thread_subject(messages), messages
                    ),
                }

                categorized_threads[category["name"]].append(thread_data)
            else:
                logger.warning(f"Thread {thread.get('id')} did not match any category")

        # Limit threads per category if configured
        max_threads = self.config.get_max_threads_per_category()
        if max_threads is not None:
            for category_name in categorized_threads:
                if len(categorized_threads[category_name]) > max_threads:
                    logger.info(
                        f"Limiting category '{category_name}' to {max_threads} threads"
                    )
                    categorized_threads[category_name] = categorized_threads[
                        category_name
                    ][:max_threads]

        return categorized_threads

    def _extract_thread_subject(self, messages: list[dict[str, Any]]) -> str:
        """Extract the main subject from a thread's messages.

        Args:
            messages: List of message data

        Returns:
            Thread subject
        """
        if messages:
            # Use the first message's subject
            return messages[0].get("subject", "No Subject")  # type: ignore[no-any-return]
        return "No Subject"

    def _extract_participants(self, messages: list[dict[str, Any]]) -> list[str]:
        """Extract unique participants from a thread's messages.

        Args:
            messages: List of message data

        Returns:
            List of unique participant email addresses
        """
        participants = set()

        for message in messages:
            from_addr = message.get("from", "")
            to_addr = message.get("to", "")

            if from_addr:
                participants.add(from_addr)
            if to_addr:
                # Handle multiple recipients
                for addr in to_addr.split(","):
                    participants.add(addr.strip())

        return list(participants)

    def _extract_most_recent_date(self, messages: list[dict[str, Any]]) -> int:
        """Extract the most recent message date from a thread.

        Args:
            messages: List of message data

        Returns:
            Most recent internal_date as timestamp (int), or 0 if not found
        """
        most_recent = 0

        for message in messages:
            # Use internal_date (Gmail's timestamp) for accurate sorting
            internal_date = message.get("internal_date")

            if internal_date:
                try:
                    # internal_date is a string timestamp in milliseconds
                    timestamp = int(internal_date)
                    if timestamp > most_recent:
                        most_recent = timestamp
                except (ValueError, TypeError):
                    # Fallback: try to parse Date header
                    date_header = message.get("date", "")
                    if date_header:
                        try:
                            from email.utils import parsedate_to_datetime

                            parsed_date = parsedate_to_datetime(date_header)
                            timestamp = int(
                                parsed_date.timestamp() * 1000
                            )  # Convert to milliseconds
                            if timestamp > most_recent:
                                most_recent = timestamp
                        except Exception:
                            continue
            else:
                # No internal_date, try to parse Date header
                date_header = message.get("date", "")
                if date_header:
                    try:
                        from email.utils import parsedate_to_datetime

                        parsed_date = parsedate_to_datetime(date_header)
                        timestamp = int(
                            parsed_date.timestamp() * 1000
                        )  # Convert to milliseconds
                        if timestamp > most_recent:
                            most_recent = timestamp
                    except Exception:
                        continue

        return most_recent

    def get_category_summary(
        self, categorized_threads: dict[str, list[dict[str, Any]]]
    ) -> dict[str, dict[str, Any]]:
        """Generate summary statistics for categorized threads.

        Args:
            categorized_threads: Output from process_threads

        Returns:
            Summary statistics per category
        """
        summary = {}

        for category_name, threads in categorized_threads.items():
            total_threads = len(threads)
            important_threads = sum(1 for t in threads if t["has_important_sender"])
            total_messages = sum(t["message_count"] for t in threads)

            summary[category_name] = {
                "total_threads": total_threads,
                "important_threads": important_threads,
                "total_messages": total_messages,
                "avg_messages_per_thread": total_messages / total_threads
                if total_threads > 0
                else 0,
            }

        return summary

    def _is_empty_criteria(self, criteria: dict[str, Any]) -> bool:
        """Check if criteria contains only empty lists and dicts (catch-all).

        Args:
            criteria: Category criteria dictionary

        Returns:
            True if all criteria fields are empty
        """
        # Check if all pattern lists are empty
        pattern_fields = [
            "from_patterns",
            "to_patterns",
            "subject_patterns",
            "content_patterns",
            "labels",
        ]
        for field in pattern_fields:
            if criteria.get(field) and len(criteria[field]) > 0:
                return False

        # Check if headers dict is empty
        if criteria.get("headers") and len(criteria["headers"]) > 0:
            return False

        return True

    def _generate_gmail_url(
        self,
        _thread: dict[str, Any],
        subject: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> str:
        """Generate Gmail web interface URL for a thread.

        Since IMAP thread IDs don't map to Gmail web thread IDs, we use search-based URLs.
        Prefers Message-ID search over subject search for accuracy.

        Args:
            _thread: Thread object containing id and messages (unused - kept for API compatibility)
            subject: Thread subject for search-based URLs (fallback)
            messages: List of messages in the thread

        Returns:
            Gmail web URL for viewing the thread
        """
        import urllib.parse

        # Try to get Message-ID from first message for most accurate search
        if messages:
            first_message = messages[0]
            headers = first_message.get("headers", {})
            message_id = (
                headers.get("Message-ID")
                or headers.get("message-id")
                or headers.get("Message-Id")
            )

            if message_id:
                # Remove angle brackets if present
                clean_message_id = message_id.strip("<>")
                # Always URL encode the Message-ID, including forward slashes
                encoded_message_id = urllib.parse.quote(clean_message_id, safe="")
                return f"https://mail.google.com/mail/u/0/#search/rfc822msgid%3A{encoded_message_id}"

        # Fallback to subject search if Message-ID not available
        if subject and subject != "No Subject":
            # Clean up subject for search - remove common reply prefixes
            clean_subject = subject
            for prefix in ["Re:", "RE:", "Fwd:", "FWD:"]:
                if clean_subject.startswith(prefix):
                    clean_subject = clean_subject[len(prefix) :].strip()

            # URL encode the cleaned subject
            encoded_subject = urllib.parse.quote(clean_subject)
            return f"https://mail.google.com/mail/u/0/#search/subject%3A({encoded_subject})"
        else:
            # Final fallback to generic inbox if no identifiers
            return "https://mail.google.com/mail/u/0/#inbox"
