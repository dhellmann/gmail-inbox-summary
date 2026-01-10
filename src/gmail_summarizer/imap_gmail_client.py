"""IMAP Gmail client for fetching inbox threads and messages."""

import email
import imaplib
import logging
import re
import time
from collections import defaultdict
from collections.abc import Iterator
from email.header import decode_header
from email.message import EmailMessage
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

                if b"X-GM-EXT-1" in capabilities:
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
            # Fallback: each message is its own thread
            for msg_id in msg_ids:
                thread_id = f"thread_{msg_id.decode()}"
                threads[thread_id].append(msg_id)
            return dict(threads)

        # Use Gmail thread ID extension
        for msg_id in msg_ids:
            try:
                if self.imap is None:
                    continue

                _, data = self.imap.fetch(msg_id, "(X-GM-THRID)")
                if data and data[0]:
                    # Parse thread ID from response
                    response = data[0].decode()
                    match = re.search(r"X-GM-THRID (\d+)", response)
                    if match:
                        thread_id = match.group(1)
                    else:
                        thread_id = f"thread_{msg_id.decode()}"
                else:
                    thread_id = f"thread_{msg_id.decode()}"

                threads[thread_id].append(msg_id)
            except Exception as e:
                logger.warning(f"Error getting thread ID for message {msg_id}: {e}")
                # Fallback to individual thread
                thread_id = f"thread_{msg_id.decode()}"
                threads[thread_id].append(msg_id)

        return dict(threads)

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
            # Fetch message with headers, labels, and thread ID
            fetch_items = "(RFC822.HEADER RFC822.TEXT INTERNALDATE"
            if self.gmail_extensions:
                fetch_items += " X-GM-LABELS X-GM-THRID X-GM-MSGID)"
            else:
                fetch_items += ")"

            _, data = self.imap.fetch(msg_id, fetch_items)

            if not data or not data[0]:
                return None

            # Parse the response
            return self._parse_message_response(msg_id, data)

        except Exception as e:
            logger.error(f"Error fetching message {msg_id}: {e}")
            return None

    def _parse_message_response(self, msg_id: bytes, data: list[Any]) -> dict[str, Any]:
        """Parse IMAP message response into Gmail API compatible format.

        Args:
            msg_id: Message ID
            data: IMAP fetch response data

        Returns:
            Parsed message data
        """
        # Initialize message data
        message_data = {
            "id": msg_id.decode(),
            "thread_id": f"thread_{msg_id.decode()}",
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
            # Parse the fetch response
            response_parts = []
            for item in data:
                if isinstance(item, tuple) and len(item) == 2:
                    response_parts.append(item[1])
                elif isinstance(item, bytes):
                    response_parts.append(item)

            # Join response parts
            raw_response = b"".join(response_parts)

            # Split into header and body parts
            header_end = raw_response.find(b"\r\n\r\n")
            if header_end != -1:
                header_data = raw_response[:header_end]
                body_data = raw_response[header_end + 4 :]
            else:
                header_data = raw_response
                body_data = b""

            # Parse email message
            msg = email.message_from_bytes(header_data + b"\r\n\r\n" + body_data)

            # Extract headers
            message_data["headers"] = dict(msg.items())
            message_data["subject"] = self._decode_header(msg.get("Subject", ""))
            message_data["from"] = self._decode_header(msg.get("From", ""))
            message_data["to"] = self._decode_header(msg.get("To", ""))
            message_data["date"] = msg.get("Date", "")

            # Extract body
            message_data["body"] = self._extract_body(msg)
            message_data["snippet"] = self._create_snippet(message_data["body"])

            # Parse Gmail-specific data from first response item if available
            if data and isinstance(data[0], tuple):
                response_line = (
                    data[0][0].decode()
                    if isinstance(data[0][0], bytes)
                    else str(data[0][0])
                )

                # Extract Gmail labels
                labels_match = re.search(r"X-GM-LABELS \(([^)]+)\)", response_line)
                if labels_match:
                    labels_str = labels_match.group(1)
                    message_data["label_ids"] = self._parse_gmail_labels(labels_str)

                # Extract Gmail thread ID
                thread_match = re.search(r"X-GM-THRID (\d+)", response_line)
                if thread_match:
                    message_data["thread_id"] = thread_match.group(1)

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
        label_parts = re.findall(r'"([^"]*)"|\S+', labels_str)

        for label in label_parts:
            # Remove quotes and handle escapes
            if label.startswith('"') and label.endswith('"'):
                label = label[1:-1]

            # Convert Gmail IMAP label format to API format
            if label.startswith("\\"):
                # System labels
                system_label_map = {
                    "\\Inbox": "INBOX",
                    "\\Sent": "SENT",
                    "\\Drafts": "DRAFT",
                    "\\Spam": "SPAM",
                    "\\Trash": "TRASH",
                    "\\Important": "IMPORTANT",
                    "\\Starred": "STARRED",
                }
                label = system_label_map.get(label, label[1:])

            labels.append(label)

        return labels if labels else ["INBOX"]

    def _extract_body(self, msg: EmailMessage) -> str:
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
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body += payload.decode(charset, errors="ignore")
                    elif content_type == "text/html" and not body:
                        # Use HTML as fallback if no plain text
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            html_body = payload.decode(charset, errors="ignore")
                            # Basic HTML to text conversion
                            body = re.sub(r"<[^>]+>", " ", html_body)
                            body = re.sub(r"\s+", " ", body).strip()
            else:
                # Handle single-part messages
                payload = msg.get_payload(decode=True)
                if payload:
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
        return thread.get("messages", [])

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

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
