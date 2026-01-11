"""Thread processing and categorization logic."""

import fnmatch
import logging
from typing import Any

from .config import Config

logger = logging.getLogger(__name__)


class ThreadProcessor:
    """Process and categorize Gmail threads based on Gmail labels with pattern matching support."""

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
            criteria: Matching criteria (only labels are supported)
            category_name: Name of category being tested (for verbose logging)

        Returns:
            True if message has any of the required labels
        """
        subject = message.get("subject", "No Subject")
        message_labels = message.get("label_ids", [])

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Message details: Subject='{subject}', Labels={message_labels}"
            )
            logger.debug(
                f"Testing message '{subject[:50]}...' against category '{category_name}'"
            )

        # Check Gmail labels (only supported criteria type)
        if criteria.get("labels"):
            required_labels = criteria["labels"]
            # Normalize Gmail search syntax (is:important → IMPORTANT)
            normalized_labels = [
                self._normalize_gmail_label(label) for label in required_labels
            ]

            # Check for label matches using fnmatch (handles both exact matches and patterns)
            match_result = False
            matched_labels = []

            for required_label in normalized_labels:
                for message_label in message_labels:
                    # Use fnmatch for all comparisons (handles exact matches when no wildcards)
                    if fnmatch.fnmatch(message_label, required_label):
                        match_result = True
                        matched_labels.append(message_label)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"  Labels check: {match_result} (required: {required_labels} → normalized: {normalized_labels}, message has: {message_labels}, matched: {matched_labels})"
                )

            if logger.isEnabledFor(logging.DEBUG):
                if match_result:
                    logger.debug(
                        f"  ✓ Message '{subject[:50]}...' MATCHES category '{category_name}' (label match)"
                    )
                else:
                    logger.debug(
                        f"  ✗ Message '{subject[:50]}...' does NOT match category '{category_name}' (no label match)"
                    )

            return match_result

        # Empty criteria or no labels specified - this is a catch-all
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"  ✓ Message '{subject[:50]}...' MATCHES category '{category_name}' (catch-all)"
            )
        return True

    def _normalize_gmail_label(self, label: str) -> str:
        """Normalize Gmail search syntax labels to internal format.

        Converts Gmail search syntax like 'is:important' to internal labels like 'IMPORTANT'.

        Args:
            label: Label in Gmail search syntax (e.g., 'is:important')

        Returns:
            Normalized internal label name
        """
        # Gmail search syntax mapping
        gmail_search_map = {
            "is:important": "IMPORTANT",
            "is:starred": "STARRED",
            "is:unread": "UNREAD",
            "is:read": "READ",
            "is:sent": "SENT",
            "is:draft": "DRAFT",
            "is:inbox": "INBOX",
            "is:spam": "SPAM",
            "is:trash": "TRASH",
            "is:chat": "CHAT",
        }

        # Convert to lowercase for case-insensitive matching
        label_lower = label.lower()

        # If it's Gmail search syntax, convert it
        if label_lower in gmail_search_map:
            return gmail_search_map[label_lower]

        # Otherwise return as-is (for custom labels or other formats)
        return label

    def is_important_sender(self, message: dict[str, Any]) -> bool:
        """Check if message is from an important sender.

        Args:
            message: Message data

        Returns:
            True if sender is marked as important
        """
        import re

        from_address = message.get("from", "")

        # Check if sender matches any of the important sender patterns
        for pattern in self.important_senders:
            try:
                if re.search(pattern, from_address, re.IGNORECASE):
                    return True
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                continue

        return False

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
        """Check if criteria contains only empty labels (catch-all).

        Args:
            criteria: Category criteria dictionary

        Returns:
            True if labels field is empty
        """
        # Check if labels list is empty
        labels = criteria.get("labels", [])
        return not labels or len(labels) == 0

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
