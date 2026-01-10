"""Tests for html_generator module."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from gmail_summarizer.config import Config
from gmail_summarizer.html_generator import HTMLGenerator


def test_html_generator_initialization() -> None:
    """Test HTMLGenerator initialization."""
    config = Mock(spec=Config)
    generator = HTMLGenerator(config)

    assert generator.config == config
    assert generator.template_dir == Path("templates")
    assert generator.jinja_env is not None


def test_custom_filters() -> None:
    """Test custom Jinja2 filters."""
    config = Mock(spec=Config)
    generator = HTMLGenerator(config)

    # Test truncate_text filter
    truncate_filter = generator.jinja_env.filters['truncate_text']
    assert truncate_filter("Short text") == "Short text"
    assert truncate_filter("A" * 150, 100) == "A" * 97 + "..."

    # Test format_email filter
    format_email_filter = generator.jinja_env.filters['format_email']
    assert format_email_filter("user@example.com") == "user@example.com"
    assert format_email_filter("John Doe <user@example.com>") == "user@example.com"
    assert format_email_filter("Invalid email") == "Invalid email"

    # Test domain_from_email filter
    domain_filter = generator.jinja_env.filters['domain_from_email']
    assert domain_filter("user@example.com") == "example.com"
    assert domain_filter("John Doe <user@example.com>") == "example.com"


def test_template_context_preparation() -> None:
    """Test template context preparation."""
    config = Mock(spec=Config)
    config.get_categories.return_value = [
        {"name": "Work", "order": 1},
        {"name": "Personal", "order": 2}
    ]
    config.get_max_threads_per_category.return_value = 10
    config.get_important_senders.return_value = ["boss@company.com"]

    generator = HTMLGenerator(config)

    summarized_threads = {
        "Work": [
            {
                "subject": "Project Update",
                "has_important_sender": True,
                "participants": ["user@company.com", "boss@company.com"]
            },
            {
                "subject": "Meeting Notes",
                "has_important_sender": False,
                "participants": ["user@company.com", "colleague@company.com"]
            }
        ],
        "Personal": [
            {
                "subject": "Weekend Plans",
                "has_important_sender": False,
                "participants": ["user@gmail.com", "friend@gmail.com"]
            }
        ]
    }

    stats = {
        "successful_summaries": 3,
        "failed_summaries": 0,
        "success_rate": 1.0,
        "error_types": {}
    }

    context = generator._prepare_template_context(summarized_threads, stats)

    # Check basic structure
    assert "categorized_threads" in context
    assert "total_threads" in context
    assert "generated_date" in context

    # Check thread counts
    assert context["total_threads"] == 3
    assert context["important_threads"] == 1

    # Check category ordering (Work should come before Personal)
    categories = list(context["categorized_threads"].keys())
    assert categories == ["Work", "Personal"]

    # Check thread sorting within categories (important first, then alphabetical)
    work_threads = context["categorized_threads"]["Work"]
    assert work_threads[0]["subject"] == "Project Update"  # Important first
    assert work_threads[1]["subject"] == "Meeting Notes"


def test_generate_html_report() -> None:
    """Test HTML report generation."""
    config = Mock(spec=Config)
    config.get_output_filename.return_value = "test_output.html"
    config.get_categories.return_value = [{"name": "Test", "order": 1}]
    config.get_max_threads_per_category.return_value = 10
    config.get_important_senders.return_value = []

    # Create temporary templates directory
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = Path(temp_dir) / "templates"
        templates_dir.mkdir()

        # Create a simple test template
        template_file = templates_dir / "summary.html"
        template_file.write_text("""
<!DOCTYPE html>
<html>
<head><title>Test Template</title></head>
<body>
    <h1>Total Threads: {{ total_threads }}</h1>
    <p>Success Rate: {{ (success_rate * 100) | round(1) }}%</p>
    {% for category_name, threads in categorized_threads.items() %}
        <h2>{{ category_name }}</h2>
        {% for thread in threads %}
            <div>{{ thread.subject }}</div>
        {% endfor %}
    {% endfor %}
</body>
</html>
        """)

        generator = HTMLGenerator(config, str(templates_dir))

        summarized_threads = {
            "Test": [
                {"subject": "Test Thread", "has_important_sender": False}
            ]
        }
        stats = {
            "successful_summaries": 1,
            "failed_summaries": 0,
            "success_rate": 1.0,
            "error_types": {}
        }

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir) / "test.html"
            result_path = generator.generate_html_report(
                summarized_threads, stats, str(output_path)
            )

            assert result_path == str(output_path.absolute())
            assert output_path.exists()

            # Check generated content
            content = output_path.read_text()
            assert "Total Threads: 1" in content
            assert "Success Rate: 100.0%" in content
            assert "Test Thread" in content


def test_category_summary_generation() -> None:
    """Test category summary statistics generation."""
    config = Mock(spec=Config)
    generator = HTMLGenerator(config)

    categorized_threads = {
        "Work": [
            {
                "message_count": 3,
                "has_important_sender": True,
                "summary_generated": True,
                "participants": ["user@company.com", "boss@company.com", "hr@company.com"]
            },
            {
                "message_count": 1,
                "has_important_sender": False,
                "summary_generated": True,
                "participants": ["user@company.com", "colleague@company.com"]
            }
        ],
        "Personal": [
            {
                "message_count": 2,
                "has_important_sender": False,
                "summary_generated": False,
                "participants": ["user@gmail.com", "friend@gmail.com"]
            }
        ],
        "Empty": []
    }

    summary = generator.generate_category_summary(categorized_threads)

    # Work category
    assert "Work" in summary
    work_stats = summary["Work"]
    assert work_stats["thread_count"] == 2
    assert work_stats["total_messages"] == 4
    assert work_stats["avg_messages_per_thread"] == 2.0
    assert work_stats["important_threads"] == 1
    assert work_stats["successful_summaries"] == 2
    assert work_stats["unique_domains"] == 1  # Only company.com (unique domains)

    # Personal category
    assert "Personal" in summary
    personal_stats = summary["Personal"]
    assert personal_stats["thread_count"] == 1
    assert personal_stats["important_threads"] == 0
    assert personal_stats["successful_summaries"] == 0

    # Empty category should not be in summary
    assert "Empty" not in summary


def test_template_validation() -> None:
    """Test template validation functionality."""
    config = Mock(spec=Config)

    # Create temporary templates directory with valid template
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = Path(temp_dir) / "templates"
        templates_dir.mkdir()

        # Valid template
        template_file = templates_dir / "summary.html"
        template_file.write_text("""
<html>
<body>
    <h1>{{ total_threads }} threads</h1>
    <p>Success rate: {{ success_rate }}</p>
</body>
</html>
        """)

        generator = HTMLGenerator(config, str(templates_dir))
        assert generator.validate_template("summary.html") is True


def test_template_validation_invalid() -> None:
    """Test template validation with invalid template."""
    config = Mock(spec=Config)

    # Create temporary templates directory with invalid template
    with tempfile.TemporaryDirectory() as temp_dir:
        templates_dir = Path(temp_dir) / "templates"
        templates_dir.mkdir()

        # Invalid template (bad Jinja syntax)
        template_file = templates_dir / "invalid.html"
        template_file.write_text("""
<html>
<body>
    <h1>{{ unclosed_variable </h1>
</body>
</html>
        """)

        generator = HTMLGenerator(config, str(templates_dir))
        assert generator.validate_template("invalid.html") is False


def test_get_template_path() -> None:
    """Test template path resolution."""
    config = Mock(spec=Config)
    generator = HTMLGenerator(config, "custom_templates")

    path = generator.get_template_path("summary.html")
    assert path == Path("custom_templates") / "summary.html"

    path = generator.get_template_path()  # Default
    assert path == Path("custom_templates") / "summary.html"


def test_create_static_css() -> None:
    """Test static CSS file creation."""
    config = Mock(spec=Config)
    generator = HTMLGenerator(config)

    with tempfile.TemporaryDirectory() as temp_dir:
        css_path = generator.create_static_css(temp_dir)

        assert css_path == str(Path(temp_dir) / "static" / "style.css")
        assert Path(css_path).exists()

        # Check CSS content
        content = Path(css_path).read_text()
        assert "Gmail Inbox Summary - Standalone CSS" in content
        assert "font-family:" in content
        assert ".container" in content
