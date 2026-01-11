"""Tests for the cache manager."""

import tempfile
from pathlib import Path

from gmail_summarizer.cache_manager import CacheManager
from gmail_summarizer.cache_manager import get_cache_directory


def test_get_cache_directory() -> None:
    """Test that cache directory is created correctly."""
    cache_dir = get_cache_directory()

    assert isinstance(cache_dir, Path)
    assert cache_dir.exists()
    assert cache_dir.is_dir()
    assert "gmail-summary" in str(cache_dir)
    assert cache_dir.is_absolute()


def test_cache_manager_initialization() -> None:
    """Test cache manager initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "test_cache"
        cache_manager = CacheManager(cache_dir)

        assert cache_manager.cache_dir == cache_dir
        assert cache_dir.exists()
        assert (
            cache_dir / "threads.json"
        ).exists() is False  # Not created until needed
        assert (cache_dir / "summaries.json").exists() is False


def test_thread_content_hashing() -> None:
    """Test thread content hashing for change detection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(Path(temp_dir))

        messages1 = [
            {
                "id": "msg1",
                "subject": "Test Subject",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test message body",
            }
        ]

        messages2 = [
            {
                "id": "msg1",
                "subject": "Test Subject",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test message body",
            }
        ]

        messages3 = [
            {
                "id": "msg1",
                "subject": "Test Subject",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Different message body",  # Changed content
            }
        ]

        hash1 = cache_manager._calculate_thread_hash(messages1)
        hash2 = cache_manager._calculate_thread_hash(messages2)
        hash3 = cache_manager._calculate_thread_hash(messages3)

        assert hash1 == hash2  # Same content = same hash
        assert hash1 != hash3  # Different content = different hash
        assert len(hash1) == 64  # SHA-256 hash length


def test_cache_thread_and_summary() -> None:
    """Test caching thread and summary data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(Path(temp_dir))

        thread_id = "thread_123"
        messages = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test body",
            }
        ]

        thread_data = {
            "thread": {"id": thread_id},
            "messages": messages,
            "subject": "Test",
            "category": {"name": "Test Category"},
        }

        summary_data = {
            "summary": "This is a test summary",
            "summary_generated": True,
            "summary_error": None,
        }

        # Cache the data
        cache_manager.cache_thread_and_summary(
            thread_id, messages, thread_data, summary_data
        )

        # Verify thread is marked as cached
        assert cache_manager.is_thread_cached(thread_id, messages) is True

        # Verify we can retrieve cached summary
        cached_summary = cache_manager.get_cached_summary(thread_id)
        assert cached_summary is not None
        assert cached_summary["summary_data"] == summary_data


def test_thread_change_detection() -> None:
    """Test that thread changes are detected correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(Path(temp_dir))

        thread_id = "thread_123"
        original_messages = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Original body",
            }
        ]

        changed_messages = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Changed body",  # Content changed
            }
        ]

        thread_data = {"thread": {"id": thread_id}, "messages": original_messages}
        summary_data = {"summary": "Test summary"}

        # Cache original data
        cache_manager.cache_thread_and_summary(
            thread_id, original_messages, thread_data, summary_data
        )

        # Verify original is cached
        assert cache_manager.is_thread_cached(thread_id, original_messages) is True

        # Verify changed content is not considered cached
        assert cache_manager.is_thread_cached(thread_id, changed_messages) is False


def test_cache_persistence() -> None:
    """Test that cache persists between manager instances."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)

        thread_id = "thread_123"
        messages = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test",
            }
        ]
        thread_data = {"thread": {"id": thread_id}, "messages": messages}
        summary_data = {"summary": "Test summary"}

        # First manager instance - cache data
        cache_manager1 = CacheManager(cache_dir)
        cache_manager1.cache_thread_and_summary(
            thread_id, messages, thread_data, summary_data
        )
        cache_manager1.save()

        # Second manager instance - should load existing cache
        cache_manager2 = CacheManager(cache_dir)

        assert cache_manager2.is_thread_cached(thread_id, messages) is True
        cached_summary = cache_manager2.get_cached_summary(thread_id)
        assert cached_summary is not None
        assert cached_summary["summary_data"] == summary_data


def test_cache_stats() -> None:
    """Test cache statistics."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(Path(temp_dir))

        stats = cache_manager.get_cache_stats()

        assert "cache_directory" in stats
        assert "cached_threads" in stats
        assert "cached_summaries" in stats
        assert "threads_cache_size_bytes" in stats
        assert "summaries_cache_size_bytes" in stats

        assert stats["cached_threads"] == 0
        assert stats["cached_summaries"] == 0

        # Add some cache data
        thread_id = "thread_123"
        messages = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test",
            }
        ]
        thread_data = {"thread": {"id": thread_id}, "messages": messages}
        summary_data = {"summary": "Test summary"}

        cache_manager.cache_thread_and_summary(
            thread_id, messages, thread_data, summary_data
        )
        cache_manager.save()

        stats_after = cache_manager.get_cache_stats()
        assert stats_after["cached_threads"] == 1
        assert stats_after["cached_summaries"] == 1


def test_cache_clear() -> None:
    """Test cache clearing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(Path(temp_dir))

        # Add some cache data
        thread_id = "thread_123"
        messages = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test",
            }
        ]
        thread_data = {"thread": {"id": thread_id}, "messages": messages}
        summary_data = {"summary": "Test summary"}

        cache_manager.cache_thread_and_summary(
            thread_id, messages, thread_data, summary_data
        )
        cache_manager.save()

        # Verify data is cached
        assert cache_manager.is_thread_cached(thread_id, messages) is True

        # Clear cache
        cache_manager.clear_cache()

        # Verify cache is empty
        assert cache_manager.is_thread_cached(thread_id, messages) is False
        assert cache_manager.get_cached_summary(thread_id) is None


def test_cache_cleanup_old_entries() -> None:
    """Test cleanup of old cache entries."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(Path(temp_dir))

        # Manually add old entries to cache
        import time

        old_timestamp = time.time() - (40 * 24 * 60 * 60)  # 40 days old

        cache_manager._threads_cache["old_thread"] = {
            "content_hash": "hash123",
            "thread_data": {"test": "data"},
            "cached_at": old_timestamp,
        }

        cache_manager._summaries_cache["old_thread"] = {
            "summary_data": {"summary": "old"},
            "content_hash": "hash123",
            "cached_at": old_timestamp,
        }

        # Add recent entry
        recent_timestamp = time.time() - (10 * 24 * 60 * 60)  # 10 days old
        cache_manager._threads_cache["recent_thread"] = {
            "content_hash": "hash456",
            "thread_data": {"test": "data"},
            "cached_at": recent_timestamp,
        }

        cache_manager._summaries_cache["recent_thread"] = {
            "summary_data": {"summary": "recent"},
            "content_hash": "hash456",
            "cached_at": recent_timestamp,
        }

        # Cleanup entries older than 30 days
        removed_count = cache_manager.cleanup_old_entries(max_age_days=30)

        assert removed_count == 1
        assert "old_thread" not in cache_manager._threads_cache
        assert "old_thread" not in cache_manager._summaries_cache
        assert "recent_thread" in cache_manager._threads_cache
        assert "recent_thread" in cache_manager._summaries_cache


def test_context_manager() -> None:
    """Test cache manager as context manager."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)

        thread_id = "thread_123"
        messages = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test",
            }
        ]
        thread_data = {"thread": {"id": thread_id}, "messages": messages}
        summary_data = {"summary": "Test summary"}

        # Use as context manager
        with CacheManager(cache_dir) as cache_manager:
            cache_manager.cache_thread_and_summary(
                thread_id, messages, thread_data, summary_data
            )

        # Verify cache was saved automatically
        cache_manager2 = CacheManager(cache_dir)
        assert cache_manager2.is_thread_cached(thread_id, messages) is True


def test_invalid_cache_files() -> None:
    """Test handling of corrupted cache files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir)

        # Create corrupted cache files
        (cache_dir / "threads.json").write_text("invalid json", encoding="utf-8")
        (cache_dir / "summaries.json").write_text("invalid json", encoding="utf-8")

        # Should handle corruption gracefully
        cache_manager = CacheManager(cache_dir)

        # Should have empty caches after failing to load corrupted data
        assert len(cache_manager._threads_cache) == 0
        assert len(cache_manager._summaries_cache) == 0


def test_prompt_based_cache_invalidation() -> None:
    """Test that cache is invalidated when prompt changes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(Path(temp_dir))

        # Test data
        thread_id = "thread_123"
        messages = [
            {
                "id": "msg1",
                "subject": "Test Subject",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test message body",
            }
        ]
        thread_data = {"thread": {"id": thread_id}, "messages": messages}
        summary_data = {"summary": "Test summary"}

        # First prompt
        prompt1 = "Summarize this email briefly."

        # Cache with first prompt
        cache_manager.cache_thread_and_summary(
            thread_id, messages, thread_data, summary_data, prompt1
        )

        # Should be cached with the same prompt
        assert cache_manager.is_thread_cached(thread_id, messages, prompt1) is True

        # Should NOT be cached with a different prompt
        prompt2 = "Provide a detailed summary of this email."
        assert cache_manager.is_thread_cached(thread_id, messages, prompt2) is False

        # Cache with second prompt
        summary_data2 = {"summary": "Detailed test summary"}
        cache_manager.cache_thread_and_summary(
            thread_id, messages, thread_data, summary_data2, prompt2
        )

        # Now should be cached with second prompt
        assert cache_manager.is_thread_cached(thread_id, messages, prompt2) is True

        # Still should not be cached with first prompt (overwritten)
        assert cache_manager.is_thread_cached(thread_id, messages, prompt1) is False

        # Verify that the cached summary corresponds to the current prompt
        cached_summary = cache_manager.get_cached_summary(thread_id)
        assert cached_summary is not None
        assert cached_summary["prompt"] == prompt2
        assert cached_summary["summary_data"] == summary_data2


def test_prompt_included_in_hash() -> None:
    """Test that prompt is included in content hash calculation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager(Path(temp_dir))

        messages = [
            {
                "id": "msg1",
                "subject": "Test",
                "from": "test@example.com",
                "date": "2024-01-01",
                "body": "Test",
            }
        ]

        # Same messages, different prompts should produce different hashes
        hash1 = cache_manager._calculate_thread_hash(messages, "Brief summary")
        hash2 = cache_manager._calculate_thread_hash(messages, "Detailed summary")
        hash3 = cache_manager._calculate_thread_hash(messages, "")  # Empty prompt

        # All hashes should be different
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

        # Same messages and prompt should produce same hash
        hash1_repeat = cache_manager._calculate_thread_hash(messages, "Brief summary")
        assert hash1 == hash1_repeat
