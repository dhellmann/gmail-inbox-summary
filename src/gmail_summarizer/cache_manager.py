"""Cache manager for storing email thread content and summaries."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_cache_directory() -> Path:
    """Get platform-specific cache directory for the application.

    Returns:
        Path to cache directory (created if it doesn't exist)
    """
    import os
    import platform

    system = platform.system().lower()

    if system in ("darwin", "linux"):
        # macOS and Linux: use ~/.cache/gmail-summary
        cache_base = Path.home() / ".cache"
    elif system == "windows":
        # Windows: use %LOCALAPPDATA%/gmail-summary
        cache_base = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
    else:
        # Fallback: use ~/.cache
        cache_base = Path.home() / ".cache"

    cache_dir = cache_base / "gmail-summary"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


class CacheManager:
    """Manages caching of email thread content and summaries."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize cache manager.

        Args:
            cache_dir: Custom cache directory (uses platform default if None)
        """
        self.cache_dir = cache_dir or get_cache_directory()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache file paths
        self.threads_cache_file = self.cache_dir / "threads.json"
        self.summaries_cache_file = self.cache_dir / "summaries.json"

        # In-memory caches
        self._threads_cache: dict[str, dict[str, Any]] = {}
        self._summaries_cache: dict[str, dict[str, Any]] = {}

        self._load_caches()

        logger.info(f"Cache directory: {self.cache_dir}")

    def _load_caches(self) -> None:
        """Load existing cache data from disk."""
        try:
            if self.threads_cache_file.exists():
                with open(self.threads_cache_file, encoding="utf-8") as f:
                    self._threads_cache = json.load(f)
                logger.info(f"Loaded {len(self._threads_cache)} threads from cache")

            if self.summaries_cache_file.exists():
                with open(self.summaries_cache_file, encoding="utf-8") as f:
                    self._summaries_cache = json.load(f)
                logger.info(f"Loaded {len(self._summaries_cache)} summaries from cache")

        except Exception as e:
            logger.warning(f"Failed to load cache files: {e}")
            self._threads_cache = {}
            self._summaries_cache = {}

    def _save_caches(self) -> None:
        """Save cache data to disk."""
        try:
            with open(self.threads_cache_file, "w", encoding="utf-8") as f:
                json.dump(self._threads_cache, f, indent=2, ensure_ascii=False)

            with open(self.summaries_cache_file, "w", encoding="utf-8") as f:
                json.dump(self._summaries_cache, f, indent=2, ensure_ascii=False)

            logger.debug("Cache files saved successfully")

        except Exception as e:
            logger.error(f"Failed to save cache files: {e}")

    def _calculate_thread_hash(self, messages: list[dict[str, Any]]) -> str:
        """Calculate hash of thread content for change detection.

        Args:
            messages: List of message data from the thread

        Returns:
            SHA-256 hash of thread content
        """
        # Create a stable representation of thread content
        content_parts = []

        for msg in messages:
            # Include key message fields that would affect summary
            msg_content = {
                "id": msg.get("id", ""),
                "subject": msg.get("subject", ""),
                "from": msg.get("from", ""),
                "date": msg.get("date", ""),
                "body": msg.get("body", ""),
            }
            content_parts.append(json.dumps(msg_content, sort_keys=True))

        # Create hash of all message content
        combined_content = "\n".join(content_parts)
        return hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

    def is_thread_cached(self, thread_id: str, messages: list[dict[str, Any]]) -> bool:
        """Check if thread is cached and content hasn't changed.

        Args:
            thread_id: Unique thread identifier
            messages: Current thread messages

        Returns:
            True if thread is cached and content unchanged
        """
        if thread_id not in self._threads_cache:
            return False

        current_hash = self._calculate_thread_hash(messages)
        cached_hash = self._threads_cache[thread_id].get("content_hash")

        return current_hash == cached_hash

    def get_cached_summary(self, thread_id: str) -> dict[str, Any] | None:
        """Get cached summary for a thread.

        Args:
            thread_id: Unique thread identifier

        Returns:
            Cached summary data or None if not found
        """
        return self._summaries_cache.get(thread_id)

    def cache_thread_and_summary(
        self,
        thread_id: str,
        messages: list[dict[str, Any]],
        thread_data: dict[str, Any],
        summary_data: dict[str, Any],
    ) -> None:
        """Cache thread content and summary.

        Args:
            thread_id: Unique thread identifier
            messages: Thread messages for hash calculation
            thread_data: Complete thread data to cache
            summary_data: Generated summary data to cache
        """
        content_hash = self._calculate_thread_hash(messages)

        # Cache thread content with hash
        self._threads_cache[thread_id] = {
            "content_hash": content_hash,
            "thread_data": thread_data,
            "cached_at": self._get_current_timestamp(),
        }

        # Cache summary
        self._summaries_cache[thread_id] = {
            "summary_data": summary_data,
            "content_hash": content_hash,  # Link to content hash
            "cached_at": self._get_current_timestamp(),
        }

        logger.debug(f"Cached thread {thread_id} with hash {content_hash[:8]}...")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_directory": str(self.cache_dir),
            "cached_threads": len(self._threads_cache),
            "cached_summaries": len(self._summaries_cache),
            "threads_cache_file_exists": self.threads_cache_file.exists(),
            "summaries_cache_file_exists": self.summaries_cache_file.exists(),
            "threads_cache_size_bytes": self.threads_cache_file.stat().st_size
            if self.threads_cache_file.exists()
            else 0,
            "summaries_cache_size_bytes": self.summaries_cache_file.stat().st_size
            if self.summaries_cache_file.exists()
            else 0,
        }

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._threads_cache.clear()
        self._summaries_cache.clear()

        # Remove cache files
        try:
            if self.threads_cache_file.exists():
                self.threads_cache_file.unlink()
            if self.summaries_cache_file.exists():
                self.summaries_cache_file.unlink()
            logger.info("Cache cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear cache files: {e}")

    def cleanup_old_entries(self, max_age_days: int = 30) -> int:
        """Remove cache entries older than specified age.

        Args:
            max_age_days: Maximum age in days for cache entries

        Returns:
            Number of entries removed
        """
        import time

        current_time = time.time()
        cutoff_time = current_time - (max_age_days * 24 * 60 * 60)

        removed_count = 0

        # Clean threads cache
        threads_to_remove = []
        for thread_id, data in self._threads_cache.items():
            cached_at = data.get("cached_at", 0)
            if cached_at < cutoff_time:
                threads_to_remove.append(thread_id)

        for thread_id in threads_to_remove:
            del self._threads_cache[thread_id]
            if thread_id in self._summaries_cache:
                del self._summaries_cache[thread_id]
            removed_count += 1

        if removed_count > 0:
            self._save_caches()
            logger.info(f"Removed {removed_count} old cache entries")

        return removed_count

    def save(self) -> None:
        """Save current cache state to disk."""
        self._save_caches()

    def _get_current_timestamp(self) -> float:
        """Get current timestamp."""
        import time

        return time.time()

    def __enter__(self) -> "CacheManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - save caches."""
        self._save_caches()
