"""HTML report generation using Jinja2 templates."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import select_autoescape

try:
    from jinja2 import Markup
except ImportError:
    # For newer versions of Jinja2, Markup is in markupsafe
    from markupsafe import Markup

from .config import Config

logger = logging.getLogger(__name__)


class HTMLGenerator:
    """Generate HTML reports from summarized thread data."""

    def __init__(self, config: Config, template_dir: str = "templates"):
        """Initialize HTML generator.

        Args:
            config: Configuration manager instance
            template_dir: Directory containing Jinja2 templates
        """
        self.config = config
        self.template_dir = Path(template_dir)

        # Set up Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self._add_custom_filters()

    def _add_custom_filters(self) -> None:
        """Add custom Jinja2 filters."""

        def truncate_text(text: str, max_length: int = 100) -> str:
            """Truncate text to specified length."""
            if len(text) <= max_length:
                return text
            return text[: max_length - 3] + "..."

        def format_email(email: str) -> str:
            """Format email address for display."""
            if "<" in email and ">" in email:
                # Extract just the email from "Name <email@domain.com>" format
                start = email.rfind("<")
                end = email.rfind(">")
                if start != -1 and end != -1:
                    return email[start + 1 : end]
            return email

        def domain_from_email(email: str) -> str:
            """Extract domain from email address."""
            clean_email = format_email(email)
            if "@" in clean_email:
                return clean_email.split("@")[1]
            return clean_email

        def format_date(timestamp: int) -> str:
            """Format timestamp to readable date."""
            if timestamp == 0:
                return ""
            try:
                # Convert milliseconds to seconds for datetime
                dt = datetime.fromtimestamp(timestamp / 1000)
                now = datetime.now()

                # If today, show time only
                if dt.date() == now.date():
                    return dt.strftime("%I:%M %p")

                # If this year, show month/day
                if dt.year == now.year:
                    return dt.strftime("%b %d")

                # Otherwise show month/day/year
                return dt.strftime("%b %d, %Y")
            except (ValueError, OSError):
                return ""

        def markdown_to_html(text: str | None) -> Markup:
            """Convert markdown text to HTML."""
            if not text:
                return Markup("")
            try:
                html = markdown.markdown(text, extensions=["nl2br"])
                return Markup(html)
            except Exception as e:
                logger.warning(f"Failed to convert markdown to HTML: {e}")
                # Fall back to escaped text if markdown conversion fails
                return Markup(text.replace("\n", "<br>"))

        self.jinja_env.filters["truncate_text"] = truncate_text
        self.jinja_env.filters["format_email"] = format_email
        self.jinja_env.filters["domain_from_email"] = domain_from_email
        self.jinja_env.filters["format_date"] = format_date
        self.jinja_env.filters["markdown"] = markdown_to_html

    def generate_html_report(
        self,
        summarized_threads: dict[str, list[dict[str, Any]]],
        stats: dict[str, Any],
        output_path: str | None = None,
    ) -> str:
        """Generate HTML report from summarized threads.

        Args:
            summarized_threads: Output from LLMSummarizer.summarize_threads_batch
            stats: Statistics from LLMSummarizer.get_summarization_stats
            output_path: Output file path (uses config if None)

        Returns:
            Path to generated HTML file
        """
        if output_path is None:
            output_path = self.config.get_output_filename()

        # Prepare template context
        context = self._prepare_template_context(summarized_threads, stats)

        try:
            # Load and render template
            template = self.jinja_env.get_template("summary.html")
            html_content = template.render(**context)

            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"Generated HTML report: {output_file.absolute()}")
            return str(output_file.absolute())

        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            raise

    def _prepare_template_context(
        self, summarized_threads: dict[str, list[dict[str, Any]]], stats: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare context data for Jinja2 template.

        Args:
            summarized_threads: Categorized and summarized threads
            stats: Summarization statistics

        Returns:
            Template context dictionary
        """
        # Preserve category order as defined in configuration
        categories_order = [cat["name"] for cat in self.config.get_categories()]

        # Sort threads data by configuration file order
        sorted_threads = {}
        for category_name in categories_order:
            if category_name in summarized_threads:
                threads = summarized_threads[category_name]
                if threads:  # Only include categories with threads
                    # Sort threads within category by importance and then by most recent date (newest first)
                    sorted_threads_in_category = sorted(
                        threads,
                        key=lambda t: (
                            not t.get(
                                "has_important_sender", False
                            ),  # Important first (False < True)
                            -t.get(
                                "most_recent_date", 0
                            ),  # Newest first (negative for reverse order)
                        ),
                    )
                    sorted_threads[category_name] = sorted_threads_in_category

        # Calculate additional statistics
        total_threads = sum(len(threads) for threads in sorted_threads.values())
        important_threads = sum(
            sum(1 for t in threads if t.get("has_important_sender", False))
            for threads in sorted_threads.values()
        )

        context = {
            # Main data
            "categorized_threads": sorted_threads,
            # Statistics
            "total_threads": total_threads,
            "successful_summaries": stats.get("successful_summaries", 0),
            "failed_summaries": stats.get("failed_summaries", 0),
            "success_rate": stats.get("success_rate", 0),
            "important_threads": important_threads,
            # Metadata
            "generated_date": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            "generated_timestamp": datetime.now().isoformat(),
            # Configuration
            "max_threads_per_category": self.config.get_max_threads_per_category(),
            "important_senders": self.config.get_important_senders(),
            # Error details (if any)
            "error_types": stats.get("error_types", {}),
        }

        return context

    def generate_category_summary(
        self, categorized_threads: dict[str, list[dict[str, Any]]]
    ) -> dict[str, dict[str, Any]]:
        """Generate summary statistics for each category.

        Args:
            categorized_threads: Categorized thread data

        Returns:
            Category summary statistics
        """
        category_summaries = {}

        for category_name, threads in categorized_threads.items():
            if not threads:
                continue

            total_messages = sum(t.get("message_count", 0) for t in threads)
            important_count = sum(
                1 for t in threads if t.get("has_important_sender", False)
            )
            successful_summaries = sum(
                1 for t in threads if t.get("summary_generated", False)
            )

            # Extract unique domains from participants
            domains = set()
            for thread in threads:
                for participant in thread.get("participants", []):
                    if "@" in participant:
                        domains.add(participant.split("@")[1])

            category_summaries[category_name] = {
                "thread_count": len(threads),
                "total_messages": total_messages,
                "avg_messages_per_thread": total_messages / len(threads)
                if threads
                else 0,
                "important_threads": important_count,
                "successful_summaries": successful_summaries,
                "unique_domains": len(domains),
                "top_domains": sorted(domains)[:5],
            }

        return category_summaries

    def create_static_css(self, output_dir: str = "static") -> str:
        """Create standalone CSS file for the HTML report.

        Args:
            output_dir: Directory to create CSS file in

        Returns:
            Path to created CSS file
        """
        css_content = """/* Gmail Inbox Summary - Standalone CSS */
/* This file is auto-generated and can be referenced separately */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f8f9fa;
}

/* Add all the other CSS rules here if needed for external reference */
.container { max-width: 1200px; margin: 0 auto; }
.header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
/* ... rest of styles would go here ... */
"""

        output_path = Path(output_dir) / "static" / "style.css"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(css_content)

        logger.info(f"Created CSS file: {output_path.absolute()}")
        return str(output_path.absolute())

    def validate_template(self, template_name: str = "summary.html") -> bool:
        """Validate that the template exists and is syntactically correct.

        Args:
            template_name: Name of template to validate

        Returns:
            True if template is valid, False otherwise
        """
        try:
            template = self.jinja_env.get_template(template_name)

            # Try to render with dummy data to check for syntax errors
            dummy_context = {
                "categorized_threads": {},
                "total_threads": 0,
                "successful_summaries": 0,
                "failed_summaries": 0,
                "success_rate": 0,
                "generated_date": "Test",
                "error_types": {},
            }

            template.render(**dummy_context)
            logger.info(f"Template '{template_name}' is valid")
            return True

        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return False

    def get_template_path(self, template_name: str = "summary.html") -> Path:
        """Get the full path to a template file.

        Args:
            template_name: Name of template

        Returns:
            Path to template file
        """
        return self.template_dir / template_name
