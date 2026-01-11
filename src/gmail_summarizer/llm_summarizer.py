"""LLM-powered thread summarization using Claude Code CLI."""

import logging
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from typing import Any

from .config import Config

logger = logging.getLogger(__name__)


class LLMSummarizer:
    """Generate AI-powered summaries using Claude Code CLI."""

    def __init__(self, config: Config):
        """Initialize LLM summarizer.

        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.claude_config = config.get_claude_config()
        self.cli_path = self.claude_config.get("cli_path", "claude")
        self.timeout = self.claude_config.get("timeout", 30)
        self.concurrency = self.claude_config.get("concurrency", 5)

    def summarize_thread(
        self, thread_data: dict[str, Any], category: dict[str, Any]
    ) -> dict[str, Any]:
        """Summarize a single thread using Claude Code CLI.

        Args:
            thread_data: Thread data from ThreadProcessor
            category: Category configuration containing summary prompt

        Returns:
            Thread data with added summary and metadata
        """
        try:
            # Extract thread content for summarization
            thread_content = self._prepare_thread_content(thread_data)

            # Get category-specific prompt
            prompt = category.get(
                "summary_prompt", "Provide a brief summary of this email thread."
            )

            # Generate summary using Claude Code CLI
            summary = self._call_claude_cli(thread_content, prompt)

            # Add summary to thread data
            result = thread_data.copy()
            result.update(
                {
                    "summary": summary,
                    "summary_generated": True,
                    "summary_error": None,
                }
            )

            logger.debug(
                f"Generated summary for thread {thread_data['thread'].get('id')}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to summarize thread {thread_data['thread'].get('id')}: {e}"
            )

            # Return thread data with error information
            result = thread_data.copy()
            result.update(
                {
                    "summary": f"Error generating summary: {str(e)}",
                    "summary_generated": False,
                    "summary_error": str(e),
                }
            )
            return result

    def _prepare_thread_content(self, thread_data: dict[str, Any]) -> str:
        """Prepare thread content for LLM input.

        Args:
            thread_data: Thread data from ThreadProcessor

        Returns:
            Formatted thread content for summarization
        """
        messages = thread_data["messages"]
        subject = thread_data["subject"]
        participants = thread_data["participants"]

        # Build structured content
        content_parts = [
            f"Subject: {subject}",
            f"Participants: {', '.join(participants)}",
            f"Total Messages: {len(messages)}",
            "",
            "Thread Messages:",
            "=" * 50,
        ]

        for i, message in enumerate(messages, 1):
            from_addr = message.get("from", "Unknown")
            date = message.get("date", "Unknown date")
            body = message.get("body", "").strip()

            # Truncate very long message bodies
            if len(body) > 2000:
                body = body[:1997] + "..."

            content_parts.extend(
                [
                    f"\nMessage {i}:",
                    f"From: {from_addr}",
                    f"Date: {date}",
                    f"Content: {body}",
                    "-" * 30,
                ]
            )

        return "\n".join(content_parts)

    def _call_claude_cli(self, content: str, prompt: str) -> str:
        """Call Claude Code CLI to generate summary.

        Args:
            content: Thread content to summarize
            prompt: Summary prompt/instructions

        Returns:
            Generated summary text

        Raises:
            subprocess.CalledProcessError: If CLI call fails
            subprocess.TimeoutExpired: If CLI call times out
            FileNotFoundError: If CLI tool not found
        """
        # Create full prompt
        full_prompt = f"{prompt}\n\nThread content:\n{content}"

        try:
            # Call Claude Code CLI with content via stdin
            result = subprocess.run(
                [self.cli_path, "--print"],
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True,
            )

            summary = result.stdout.strip()

            if not summary:
                raise ValueError("Claude CLI returned empty response")

            return summary

        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Claude CLI not found at '{self.cli_path}'. Please install Claude Code CLI."
            ) from e
        except subprocess.TimeoutExpired as e:
            raise subprocess.TimeoutExpired(
                e.cmd, e.timeout, f"Claude CLI timed out after {self.timeout} seconds"
            ) from e
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else "Unknown error"
            raise subprocess.CalledProcessError(
                e.returncode, e.cmd, f"Claude CLI failed: {error_msg}"
            ) from e

    def summarize_threads_batch(
        self, categorized_threads: dict[str, list[dict[str, Any]]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Summarize all threads in batches per category.

        Args:
            categorized_threads: Output from ThreadProcessor.process_threads

        Returns:
            Categorized threads with summaries added
        """
        summarized_threads: dict[str, list[dict[str, Any]]] = {}

        for category_name, threads in categorized_threads.items():
            logger.info(
                f"Summarizing {len(threads)} threads in category '{category_name}'"
            )
            summarized_threads[category_name] = []

            # Find category configuration
            category_config = None
            for cat in self.config.get_categories():
                if cat["name"] == category_name:
                    category_config = cat
                    break

            if not category_config:
                logger.warning(f"No category config found for '{category_name}'")
                # Use default prompt
                category_config = {
                    "summary_prompt": "Provide a brief summary of this email thread."
                }

            # Process each thread in the category
            for thread_data in threads:
                summarized_thread = self.summarize_thread(thread_data, category_config)
                summarized_threads[category_name].append(summarized_thread)

        return summarized_threads

    def summarize_threads_parallel(
        self,
        categorized_threads: dict[str, list[dict[str, Any]]],
        cache_manager: Any = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Summarize all threads in parallel with configurable concurrency.

        Args:
            categorized_threads: Output from ThreadProcessor.process_threads
            cache_manager: Cache manager instance for checking/storing summaries
            progress_callback: Optional callback function for progress updates

        Returns:
            Categorized threads with summaries added
        """
        summarized_threads: dict[str, list[dict[str, Any]]] = {}

        # Prepare all tasks with their metadata
        tasks = []
        for category_name, threads in categorized_threads.items():
            summarized_threads[category_name] = [None] * len(threads)  # type: ignore[list-item]  # Pre-allocate

            # Find category configuration
            category_config = None
            for cat in self.config.get_categories():
                if cat["name"] == category_name:
                    category_config = cat
                    break

            if not category_config:
                logger.warning(f"No category config found for '{category_name}'")
                category_config = {
                    "summary_prompt": "Provide a brief summary of this email thread."
                }

            # Create tasks for each thread
            for thread_index, thread_data in enumerate(threads):
                thread_id = thread_data["thread"]["id"]
                messages = thread_data["messages"]

                # Check cache first if cache manager available
                cached_summary = None
                prompt = category_config.get(
                    "summary_prompt", "Provide a brief summary of this email thread."
                )
                if cache_manager and cache_manager.is_thread_cached(
                    thread_id, messages, prompt
                ):
                    cached_summary = cache_manager.get_cached_summary(thread_id)

                tasks.append(
                    {
                        "category_name": category_name,
                        "thread_index": thread_index,
                        "thread_data": thread_data,
                        "category_config": category_config,
                        "thread_id": thread_id,
                        "messages": messages,
                        "cached_summary": cached_summary,
                        "prompt": prompt,
                    }
                )

        total_tasks = len(tasks)
        completed_tasks = 0

        def summarize_single_task(task_info: dict[str, Any]) -> dict[str, Any]:
            """Process a single summarization task."""
            # Use cached summary if available
            if task_info["cached_summary"]:
                logger.debug(
                    f"Using cached summary for thread {task_info['thread_id']}"
                )
                return {
                    **task_info,
                    "result": task_info["cached_summary"]["summary_data"],
                    "from_cache": True,
                }

            # Generate new summary
            summarized_thread = self.summarize_thread(
                task_info["thread_data"], task_info["category_config"]
            )

            # Cache the new summary if cache manager available
            if cache_manager:
                cache_manager.cache_thread_and_summary(
                    task_info["thread_id"],
                    task_info["messages"],
                    task_info["thread_data"],
                    summarized_thread,
                    task_info["prompt"],
                )

            return {
                **task_info,
                "result": summarized_thread,
                "from_cache": False,
            }

        # Process tasks in parallel
        logger.info(
            f"Processing {total_tasks} threads with {self.concurrency} concurrent workers"
        )

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(summarize_single_task, task): task for task in tasks
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_task):
                try:
                    completed_task = future.result()

                    # Store result in correct position
                    category_name = completed_task["category_name"]
                    thread_index = completed_task["thread_index"]
                    summarized_threads[category_name][thread_index] = completed_task[
                        "result"
                    ]

                    completed_tasks += 1

                    # Call progress callback if provided
                    if progress_callback:
                        cache_status = (
                            " (cached)" if completed_task["from_cache"] else ""
                        )
                        progress_callback(
                            completed_tasks,
                            f"Generating summaries ({completed_tasks}/{total_tasks}){cache_status}",
                        )

                    logger.debug(
                        f"Completed task {completed_tasks}/{total_tasks} - "
                        f"Thread {completed_task['thread_id']} in category {category_name}"
                    )

                except Exception as e:
                    task = future_to_task[future]
                    logger.error(f"Task failed for thread {task['thread_id']}: {e}")

                    # Create error result
                    error_result = task["thread_data"].copy()
                    error_result.update(
                        {
                            "summary": f"Error generating summary: {str(e)}",
                            "summary_generated": False,
                            "summary_error": str(e),
                        }
                    )

                    # Store error result
                    category_name = task["category_name"]
                    thread_index = task["thread_index"]
                    summarized_threads[category_name][thread_index] = error_result

                    completed_tasks += 1
                    if progress_callback:
                        progress_callback(
                            completed_tasks,
                            f"Generating summaries ({completed_tasks}/{total_tasks}) - Error",
                        )

        logger.info(f"Completed parallel summarization of {total_tasks} threads")
        return summarized_threads

    def get_summarization_stats(
        self, summarized_threads: dict[str, list[dict[str, Any]]]
    ) -> dict[str, Any]:
        """Generate statistics about the summarization process.

        Args:
            summarized_threads: Output from summarize_threads_batch

        Returns:
            Statistics about successful/failed summaries
        """
        total_threads = 0
        successful_summaries = 0
        failed_summaries = 0
        error_types: dict[str, int] = {}

        for _category_name, threads in summarized_threads.items():
            for thread in threads:
                total_threads += 1

                if thread.get("summary_generated", False):
                    successful_summaries += 1
                else:
                    failed_summaries += 1
                    error = thread.get("summary_error", "Unknown error")
                    error_types[error] = error_types.get(error, 0) + 1

        return {
            "total_threads": total_threads,
            "successful_summaries": successful_summaries,
            "failed_summaries": failed_summaries,
            "success_rate": successful_summaries / total_threads
            if total_threads > 0
            else 0,
            "error_types": error_types,
        }

    def test_cli_connection(self) -> bool:
        """Test if Claude Code CLI is available and working.

        Returns:
            True if CLI is available and responds, False otherwise
        """
        try:
            result = subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            logger.info(f"Claude CLI version: {result.stdout.strip()}")
            return True

        except (
            FileNotFoundError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as e:
            logger.error(f"Claude CLI test failed: {e}")
            return False

    def _estimate_token_count(self, text: str) -> int:
        """Rough estimation of token count for text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4

    def _truncate_content_if_needed(self, content: str, max_tokens: int = 8000) -> str:
        """Truncate content if it's too long for the LLM.

        Args:
            content: Input content
            max_tokens: Maximum token limit

        Returns:
            Potentially truncated content
        """
        estimated_tokens = self._estimate_token_count(content)

        if estimated_tokens <= max_tokens:
            return content

        # Calculate approximate character limit
        char_limit = max_tokens * 4
        truncated = content[: char_limit - 100]  # Leave some margin

        # Try to cut at a reasonable boundary
        last_message_boundary = truncated.rfind("\nMessage ")
        if last_message_boundary > char_limit // 2:  # Don't cut too early
            truncated = truncated[:last_message_boundary]

        return truncated + "\n\n[Content truncated due to length...]"
