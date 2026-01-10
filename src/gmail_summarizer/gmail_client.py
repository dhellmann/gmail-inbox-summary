"""Gmail API client for fetching inbox threads and messages."""

import logging
import pickle
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request  # type: ignore[import-untyped]
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    """Gmail API client for accessing inbox threads and messages."""

    def __init__(
        self, credentials_path: str = "credentials.json", token_path: str = "token.json"
    ):
        """Initialize Gmail client.

        Args:
            credentials_path: Path to OAuth2 credentials JSON file
            token_path: Path to store/load access tokens
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.service: Any = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2."""
        creds = None

        # Load existing token if available
        if self.token_path.exists():
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        # If there are no valid credentials available, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    creds = None

            if not creds:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Gmail API credentials file not found: {self.credentials_path}. "
                        "Please download from Google Cloud Console and save as credentials.json"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_path, "wb") as token:
                pickle.dump(creds, token)

        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Successfully authenticated with Gmail API")

    def get_inbox_threads(
        self, max_results: int | None = None
    ) -> Iterator[dict[str, Any]]:
        """Fetch all threads from inbox.

        Args:
            max_results: Maximum number of threads to fetch (None for all)

        Yields:
            Thread objects with full message details
        """
        try:
            page_token = None
            threads_fetched = 0

            while True:
                # Get list of thread IDs
                request_params = {"userId": "me", "labelIds": ["INBOX"]}
                if page_token:
                    request_params["pageToken"] = page_token

                # Limit page size if max_results specified
                if max_results:
                    remaining = max_results - threads_fetched
                    if remaining <= 0:
                        break
                    request_params["maxResults"] = min(100, remaining)  # type: ignore[assignment]

                result = self.service.users().threads().list(**request_params).execute()  # type: ignore[attr-defined]
                threads = result.get("threads", [])

                if not threads:
                    break

                # Fetch detailed thread information
                for thread_info in threads:
                    thread_id = thread_info["id"]
                    thread = self.get_thread_details(thread_id)
                    if thread:
                        yield thread
                        threads_fetched += 1

                        if max_results and threads_fetched >= max_results:
                            return

                page_token = result.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as error:
            logger.error(f"An error occurred fetching inbox threads: {error}")
            raise

    def get_thread_details(self, thread_id: str) -> dict[str, Any] | None:
        """Get detailed information for a specific thread.

        Args:
            thread_id: Gmail thread ID

        Returns:
            Thread object with full message details or None if error
        """
        try:
            thread = (
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )  # type: ignore[attr-defined]
            return thread  # type: ignore[no-any-return]

        except HttpError as error:
            logger.error(f"An error occurred fetching thread {thread_id}: {error}")
            return None

    def extract_message_data(self, message: dict[str, Any]) -> dict[str, Any]:
        """Extract key data from a Gmail message.

        Args:
            message: Gmail message object

        Returns:
            Extracted message data with headers, body, etc.
        """
        headers = {
            h["name"]: h["value"] for h in message.get("payload", {}).get("headers", [])
        }

        # Extract message body
        body = self._extract_body(message.get("payload", {}))

        return {
            "id": message.get("id"),
            "thread_id": message.get("threadId"),
            "label_ids": message.get("labelIds", []),
            "snippet": message.get("snippet", ""),
            "internal_date": message.get("internalDate"),
            "headers": headers,
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body,
        }

    def _extract_body(self, payload: dict[str, Any]) -> str:
        """Extract message body from Gmail payload.

        Args:
            payload: Gmail message payload

        Returns:
            Message body text
        """
        body = ""

        if "body" in payload and payload["body"].get("data"):
            import base64

            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                "utf-8", errors="ignore"
            )

        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get(
                    "data"
                ):
                    import base64

                    body += base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8", errors="ignore"
                    )
                elif (
                    part.get("mimeType") == "text/html"
                    and not body
                    and part.get("body", {}).get("data")
                ):
                    import base64

                    html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8", errors="ignore"
                    )
                    # TODO: Convert HTML to text using BeautifulSoup
                    body = html_body
                elif "parts" in part:
                    # Recursive call for nested parts
                    body += self._extract_body(part)

        return body.strip()

    def get_thread_messages(self, thread: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and process all messages from a thread.

        Args:
            thread: Gmail thread object

        Returns:
            List of processed message data
        """
        messages = []

        for message in thread.get("messages", []):
            message_data = self.extract_message_data(message)
            messages.append(message_data)

        return messages
