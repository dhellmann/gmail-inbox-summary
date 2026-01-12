"""IMAP Gmail client for fetching inbox threads and messages."""

import email
import imaplib
import logging
import re
import time
from collections import defaultdict
from collections.abc import Iterator
from email.header import decode_header
from email.message import Message
from typing import Any

logger = logging.getLogger(__name__)


class ImapGmailClient:
    """IMAP Gmail client for accessing inbox threads and messages."""

    def __init__(
        self,
        email_address: str,
        password: str,
        imap_server: str = "imap.gmail.com",
        imap_port: int = 993,
    ):
        """Initialize IMAP Gmail client.

        Args:
            email_address: Gmail email address
            password: Gmail password or app-specific password (recommended)
            imap_server: IMAP server hostname
            imap_port: IMAP server port (993 for SSL)
        """
        self.email_address = email_address
        self.password = password
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.imap: imaplib.IMAP4_SSL | None = None
        self.gmail_extensions = False
        self._connect()

    def _connect(self) -> None:
        """Connect and authenticate with IMAP server."""
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.imap.login(self.email_address, self.password)

            # Check for Gmail extensions
            if hasattr(self.imap, "capabilities"):
                # capabilities can be either a tuple or callable depending on implementation
                if callable(self.imap.capabilities):
                    capabilities = self.imap.capabilities()
                else:
                    capabilities = self.imap.capabilities

                # Check for Gmail extensions - handle both bytes and string formats
                if b"X-GM-EXT-1" in capabilities or "X-GM-EXT-1" in capabilities:
                    self.gmail_extensions = True
                    logger.info("Gmail IMAP extensions detected")

            logger.info("Successfully connected to Gmail via IMAP")
        except Exception as e:
            logger.error(f"Failed to connect to Gmail IMAP: {e}")
            raise

    def _ensure_connected(self) -> None:
        """Ensure IMAP connection is active, reconnect if needed."""
        try:
            if self.imap is None:
                self._connect()
                return

            # Test connection with NOOP
            self.imap.noop()
        except Exception:
            logger.warning("IMAP connection lost, reconnecting...")
            self._connect()

    def get_inbox_message_count(self) -> int:
        """Get the total number of messages in inbox.

        Returns:
            Total number of messages in inbox
        """
        self._ensure_connected()
        if self.imap is None:
            raise RuntimeError("IMAP connection not established")

        try:
            # Select inbox folder
            self.imap.select("INBOX")

            # Search for all messages in inbox
            _, message_ids = self.imap.search(None, "ALL")
            msg_ids = message_ids[0].split()

            return len(msg_ids)
        except Exception as e:
            logger.error(f"Error getting inbox message count: {e}")
            return 0

    def get_inbox_threads(
        self, max_results: int | None = None
    ) -> Iterator[dict[str, Any]]:
        """Fetch all threads from inbox.

        Args:
            max_results: Maximum number of threads to fetch (None for all)

        Yields:
            Thread objects with full message details
        """
        self._ensure_connected()
        if self.imap is None:
            raise RuntimeError("IMAP connection not established")

        try:
            # Select inbox folder
            self.imap.select("INBOX")

            # Search for all messages in inbox
            _, message_ids = self.imap.search(None, "ALL")
            msg_ids = message_ids[0].split()

            if not msg_ids:
                logger.info("No messages found in inbox")
                return

            # Limit results if specified
            if max_results:
                msg_ids = msg_ids[:max_results]

            logger.info(f"Found {len(msg_ids)} messages in inbox")

            # Group messages by thread using X-GM-THRID if available
            threads = self._group_messages_by_thread(msg_ids)

            threads_yielded = 0
            for thread_id, thread_msg_ids in threads.items():
                if max_results and threads_yielded >= max_results:
                    break

                thread = self._build_thread_object(thread_id, thread_msg_ids)
                if thread:
                    yield thread
                    threads_yielded += 1

        except Exception as e:
            logger.error(f"Error fetching inbox threads: {e}")
            raise

    def _group_messages_by_thread(self, msg_ids: list[bytes]) -> dict[str, list[bytes]]:
        """Group message IDs by thread ID using X-GM-THRID.

        Args:
            msg_ids: List of message IDs

        Returns:
            Dictionary mapping thread IDs to lists of message IDs
        """
        threads: dict[str, list[bytes]] = defaultdict(list)

        if not self.gmail_extensions:
            # Improved fallback: group by subject line patterns instead of individual threads
            logger.info("Gmail extensions not available, using subject-based threading")
            return self._group_by_subject_patterns(msg_ids)

        # Use Gmail thread ID extension
        for msg_id in msg_ids:
            try:
                if self.imap is None:
                    continue

                _, data = self.imap.fetch(msg_id.decode(), "(X-GM-THRID)")
                if data and data[0]:
                    # Parse thread ID from response
                    response_item = data[0]
                    if isinstance(response_item, tuple):
                        response = (
                            response_item[1].decode()
                            if isinstance(response_item[1], bytes)
                            else str(response_item[1])
                        )
                    else:
                        response = (
                            response_item.decode()
                            if isinstance(response_item, bytes)
                            else str(response_item)
                        )
                    match = re.search(r"X-GM-THRID ([A-Za-z0-9]+)", response)
                    if match:
                        thread_id = match.group(1)
                    else:
                        thread_id = f"thread_{msg_id.decode()}"
                else:
                    thread_id = f"thread_{msg_id.decode()}"

                threads[thread_id].append(msg_id)
            except Exception as e:
                logger.warning(
                    f"Error getting thread ID for message {msg_id.decode()}: {e}"
                )
                # Fallback to individual thread
                thread_id = f"thread_{msg_id.decode()}"
                threads[thread_id].append(msg_id)

        return dict(threads)

    def _group_by_subject_patterns(
        self, msg_ids: list[bytes]
    ) -> dict[str, list[bytes]]:
        """Group messages by normalized subject patterns when Gmail threading isn't available.

        This method attempts to reconstruct conversation threads by:
        1. Removing common reply/forward prefixes from subjects
        2. Grouping messages with identical normalized subjects
        3. Special handling for common notification patterns (JIRA, GitLab, etc.)

        Args:
            msg_ids: List of message IDs

        Returns:
            Dictionary mapping thread IDs to lists of message IDs
        """
        if self.imap is None:
            return {}

        # First, fetch basic headers for all messages to get subjects and message-ids
        message_info: dict[bytes, dict[str, str]] = {}

        for msg_id in msg_ids:
            try:
                _, data = self.imap.fetch(msg_id.decode(), "(RFC822.HEADER)")
                if data and data[0]:
                    # Parse the headers
                    if isinstance(data[0], tuple):
                        headers_raw = data[0][1]
                    else:
                        headers_raw = data[0]

                    if isinstance(headers_raw, bytes):
                        headers_text = headers_raw.decode("utf-8", errors="ignore")
                    else:
                        headers_text = str(headers_raw)

                    # Parse email headers
                    msg_obj = email.message_from_string(headers_text)
                    subject = self._decode_header(msg_obj.get("Subject", ""))
                    message_id = msg_obj.get("Message-ID", "")
                    in_reply_to = msg_obj.get("In-Reply-To", "")
                    references = msg_obj.get("References", "")

                    message_info[msg_id] = {
                        "subject": subject,
                        "message_id": message_id,
                        "in_reply_to": in_reply_to,
                        "references": references,
                    }

            except Exception as e:
                logger.warning(
                    f"Error fetching headers for message {msg_id.decode()}: {e}"
                )
                # Create minimal info for failed messages
                message_info[msg_id] = {
                    "subject": f"Message {msg_id.decode()}",
                    "message_id": "",
                    "in_reply_to": "",
                    "references": "",
                }

        # Group by normalized subject
        threads: dict[str, list[bytes]] = defaultdict(list)

        for msg_id, info in message_info.items():
            normalized_subject = self._normalize_subject(info["subject"])

            # Create a thread ID based on normalized subject
            if normalized_subject:
                # Use a hash of the normalized subject for thread ID
                import hashlib

                thread_id = f"subject_{hashlib.md5(normalized_subject.encode('utf-8')).hexdigest()[:8]}"
            else:
                # Fallback for messages with no/empty subject
                thread_id = f"thread_{msg_id.decode()}"

            threads[thread_id].append(msg_id)

        # Log threading results
        thread_count = len(threads)
        message_count = len(msg_ids)
        logger.info(
            f"Subject-based threading: grouped {message_count} messages into {thread_count} threads"
        )

        # Log some examples for debugging
        for thread_id, msgs in list(threads.items())[:5]:  # Show first 5 threads
            if len(msgs) > 1:
                subjects = [
                    message_info[msg_id]["subject"][:50] + "..." for msg_id in msgs[:3]
                ]
                logger.debug(f"Thread {thread_id}: {len(msgs)} messages - {subjects}")

        return dict(threads)

    def _normalize_subject(self, subject: str) -> str:
        """Normalize email subject for threading by removing reply/forward prefixes.

        Args:
            subject: Original email subject

        Returns:
            Normalized subject suitable for thread grouping
        """
        if not subject:
            return ""

        # Remove common prefixes (case insensitive)
        normalized = subject.strip()

        # Remove reply/forward prefixes - keep removing until no more found
        while True:
            original = normalized
            # Common patterns to remove
            patterns = [
                r"^(Re|RE|re):\s*",  # Re:
                r"^(Fwd|FWD|fwd):\s*",  # Fwd:
                r"^(Fw|FW|fw):\s*",  # Fw:
                r"^\[.*?\]\s*",  # [EXTERNAL] or similar
                r"^\(.*?\)\s*",  # (EXTERNAL) or similar
                r"^(AW|Aw|aw):\s*",  # German: Antwort
                r"^(SV|Sv|sv):\s*",  # Swedish: Svar
                r"^(VS|Vs|vs):\s*",  # Dutch: Verstuur
            ]

            for pattern in patterns:
                normalized = re.sub(
                    pattern, "", normalized, flags=re.IGNORECASE
                ).strip()

            # If no change, we're done
            if normalized == original:
                break

        # Additional normalization for common notification patterns

        # JIRA ticket updates - normalize to base ticket number
        jira_match = re.search(
            r"\[RH JIRA\].*?(RHAISTRAT-\d+|AIPCC-\d+|RHAIENG-\d+|RHAIRFE-\d+)",
            normalized,
        )
        if jira_match:
            return f"[RH JIRA] {jira_match.group(1)}"

        # GitLab merge request notifications
        gitlab_match = re.search(r"Re: (.+) \| (.+) \(![0-9]+\)", normalized)
        if gitlab_match:
            return f"{gitlab_match.group(1)} | {gitlab_match.group(2)}"

        # GitHub pull request notifications
        github_match = re.search(r"\[([^/]+/[^]]+)\] (.+) \(PR #(\d+)\)", normalized)
        if github_match:
            return f"[{github_match.group(1)}] {github_match.group(2)} (PR #{github_match.group(3)})"

        return normalized

    def _build_thread_object(
        self, thread_id: str, msg_ids: list[bytes]
    ) -> dict[str, Any] | None:
        """Build a thread object compatible with Gmail API format.

        Args:
            thread_id: Thread identifier
            msg_ids: List of message IDs in the thread

        Returns:
            Thread object or None if error
        """
        try:
            messages = []
            for msg_id in msg_ids:
                message_data = self._fetch_message_data(msg_id)
                if message_data:
                    messages.append(message_data)

            if not messages:
                return None

            # Create thread object compatible with Gmail API format
            return {
                "id": thread_id,
                "messages": messages,
                "historyId": str(int(time.time())),  # Use timestamp as history ID
                "snippet": messages[0].get("snippet", ""),
            }
        except Exception as e:
            logger.error(f"Error building thread object: {e}")
            return None

    def _fetch_message_data(self, msg_id: bytes) -> dict[str, Any] | None:
        """Fetch complete message data including headers, body, and labels.

        Args:
            msg_id: Message ID

        Returns:
            Message data dictionary or None if error
        """
        if self.imap is None:
            return None

        try:
            # Fetch message with headers and full body using PEEK to avoid marking as read
            fetch_items = "(BODY.PEEK[] INTERNALDATE"
            if self.gmail_extensions:
                fetch_items += " X-GM-LABELS X-GM-THRID X-GM-MSGID)"
            else:
                fetch_items += ")"

            _, data = self.imap.fetch(msg_id.decode(), fetch_items)

            if not data or not data[0]:
                return None

            # Parse the response
            return self._parse_message_response(msg_id.decode(), data)

        except Exception as e:
            logger.error(
                f"Error fetching message {msg_id.decode() if isinstance(msg_id, bytes) else msg_id}: {e}"
            )
            return None

    def _parse_message_response(self, msg_id: str, data: list[Any]) -> dict[str, Any]:
        """Parse IMAP message response into Gmail API compatible format.

        Args:
            msg_id: Message ID
            data: IMAP fetch response data

        Returns:
            Parsed message data
        """
        # Initialize message data
        message_data = {
            "id": msg_id,
            "thread_id": f"thread_{msg_id}",
            "label_ids": ["INBOX"],  # Default labels
            "snippet": "",
            "internal_date": "",
            "headers": {},
            "subject": "",
            "from": "",
            "to": "",
            "date": "",
            "body": "",
        }

        try:
            # Parse the fetch response - with BODY.PEEK[], data[0][1] contains the full message
            raw_message = None
            response_line = ""

            if data and isinstance(data[0], tuple) and len(data[0]) == 2:
                response_line = (
                    data[0][0].decode()
                    if isinstance(data[0][0], bytes)
                    else str(data[0][0])
                )
                raw_message = data[0][1]

            if raw_message is None:
                return message_data

            # Parse email message from the complete message data
            msg = email.message_from_bytes(raw_message)

            # Extract headers
            message_data["headers"] = dict(msg.items())
            message_data["subject"] = self._decode_header(msg.get("Subject", ""))
            message_data["from"] = self._decode_header(msg.get("From", ""))
            message_data["to"] = self._decode_header(msg.get("To", ""))
            message_data["date"] = msg.get("Date", "")

            # Extract body
            body = self._extract_body(msg)
            message_data["body"] = body
            message_data["snippet"] = self._create_snippet(body)

            # Parse Gmail-specific data from response line
            if response_line:
                # Extract Gmail labels
                labels_match = re.search(r"X-GM-LABELS \(([^)]+)\)", response_line)
                if labels_match:
                    labels_str = labels_match.group(1)
                    message_data["label_ids"] = self._parse_gmail_labels(labels_str)

                # Extract Gmail thread ID (can be numeric or alphanumeric hash)
                thread_match = re.search(r"X-GM-THRID ([A-Za-z0-9]+)", response_line)
                if thread_match:
                    message_data["thread_id"] = thread_match.group(1)

                # Extract Gmail message ID
                msgid_match = re.search(r"X-GM-MSGID ([A-Za-z0-9]+)", response_line)
                if msgid_match:
                    message_data["gmail_message_id"] = msgid_match.group(1)

        except Exception as e:
            logger.error(f"Error parsing message response: {e}")

        return message_data

    def _decode_header(self, header_value: str) -> str:
        """Decode email header value handling encoding.

        Args:
            header_value: Raw header value

        Returns:
            Decoded header string
        """
        if not header_value:
            return ""

        try:
            decoded_parts = decode_header(header_value)
            result = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        result += part.decode(encoding, errors="ignore")
                    else:
                        result += part.decode("utf-8", errors="ignore")
                else:
                    result += str(part)
            return result
        except Exception:
            return str(header_value)

    def _parse_gmail_labels(self, labels_str: str) -> list[str]:
        """Parse Gmail labels from X-GM-LABELS response.

        Args:
            labels_str: Raw labels string from X-GM-LABELS

        Returns:
            List of normalized label names
        """
        labels = []

        # Handle quoted labels and escape sequences
        # For quoted strings, capture what's inside the quotes
        # For unquoted strings, capture the whole string
        label_parts = re.findall(r'"([^"]*)"|(\S+)', labels_str)
        # Flatten the tuple results and filter out empty strings
        label_parts = [match for group in label_parts for match in group if match]

        for label in label_parts:
            # Remove quotes and handle escapes
            if label.startswith('"') and label.endswith('"'):
                label = label[1:-1]

            # Convert Gmail IMAP label format to API format
            if label.startswith("\\"):
                # System labels - handle both single and double backslash formats
                system_label_map = {
                    "\\Inbox": "INBOX",
                    "\\Sent": "SENT",
                    "\\Drafts": "DRAFT",
                    "\\Spam": "SPAM",
                    "\\Trash": "TRASH",
                    "\\Important": "IMPORTANT",
                    "\\Starred": "STARRED",
                    # Double backslash variants (in case they occur)
                    "\\\\Inbox": "INBOX",
                    "\\\\Sent": "SENT",
                    "\\\\Drafts": "DRAFT",
                    "\\\\Spam": "SPAM",
                    "\\\\Trash": "TRASH",
                    "\\\\Important": "IMPORTANT",
                    "\\\\Starred": "STARRED",
                }
                label = system_label_map.get(label, label.lstrip("\\"))

            labels.append(label)

        return labels if labels else ["INBOX"]

    def _extract_body(self, msg: Message[str]) -> str:
        """Extract message body from email message.

        Args:
            msg: Email message object

        Returns:
            Message body text
        """
        body = ""

        try:
            if msg.is_multipart():
                # Handle multipart messages
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset() or "utf-8"
                            body += payload.decode(charset, errors="ignore")
                    elif content_type == "text/html" and not body:
                        # Use HTML as fallback if no plain text
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset() or "utf-8"
                            html_body = payload.decode(charset, errors="ignore")
                            # Basic HTML to text conversion
                            body = re.sub(r"<[^>]+>", " ", html_body)
                            body = re.sub(r"\s+", " ", body).strip()
            else:
                # Handle single-part messages
                payload = msg.get_payload(decode=True)
                if payload and isinstance(payload, bytes):
                    charset = msg.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="ignore")

        except Exception as e:
            logger.warning(f"Error extracting message body: {e}")

        return body.strip()

    def _create_snippet(self, body: str, max_length: int = 150) -> str:
        """Create a short snippet from message body.

        Args:
            body: Full message body
            max_length: Maximum snippet length

        Returns:
            Message snippet
        """
        if not body:
            return ""

        # Clean up whitespace
        snippet = re.sub(r"\s+", " ", body.strip())

        # Truncate to max length
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(" ", 1)[0] + "..."

        return snippet

    def get_thread_details(self, thread_id: str) -> dict[str, Any] | None:
        """Get detailed information for a specific thread.

        Args:
            thread_id: Thread identifier

        Returns:
            Thread object with full message details or None if error
        """
        # For IMAP implementation, threads are already built with full details
        # This method is kept for API compatibility
        logger.warning(
            "get_thread_details called - threads already contain full details"
        )
        return None

    def extract_message_data(self, message: dict[str, Any]) -> dict[str, Any]:
        """Extract key data from a message (for API compatibility).

        Args:
            message: Message object

        Returns:
            Extracted message data (returns input as-is since already processed)
        """
        return message

    def get_thread_messages(self, thread: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and process all messages from a thread.

        Args:
            thread: Thread object

        Returns:
            List of processed message data
        """
        messages: list[dict[str, Any]] = thread.get("messages", [])
        return messages

    def close(self) -> None:
        """Close IMAP connection."""
        if self.imap:
            try:
                # Only close mailbox if one is currently selected
                try:
                    # Check if we're in SELECTED state
                    state = getattr(self.imap, "state", None)
                    if state == "SELECTED":
                        self.imap.close()
                except Exception:
                    # If we can't check state or close fails, just continue to logout
                    pass

                self.imap.logout()
            except Exception as e:
                logger.warning(f"Error closing IMAP connection: {e}")
            finally:
                self.imap = None

        logger.info("IMAP connection closed")

    def __enter__(self) -> "ImapGmailClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
