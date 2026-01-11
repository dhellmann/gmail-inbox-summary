# Claude Code Instructions

This document contains instructions for working with the Gmail Inbox Summary project using Claude Code CLI.

## Project Overview

Gmail Inbox Summary is a Python application that generates AI-powered summaries of Gmail inbox threads using configurable categorization and Claude Code CLI integration. The project uses Hatch as its build tool and package manager.

## Development Environment Setup

This project uses Hatch for dependency management and task execution. Always use Hatch commands when working with this project:

```bash
# Install dependencies and create environment
hatch env create

# Enter the development shell
hatch shell
```

## Essential Commands

### Running the Application

Always use `hatch run` to execute the application:

```bash
# Generate email summary
hatch run gmail-summary run

# Run with specific configuration
hatch run gmail-summary run --config settings.yml

# Test Claude CLI connection
hatch run gmail-summary test-claude

# Clear cache (useful when data structures change)
hatch run gmail-summary cache clear
```

### Testing and Quality Assurance

Before making commits, always run linting and tests:

```bash
# Run all linting checks
hatch run lint:all

# Run just the linting (faster)
hatch run lint:check

# Fix linting issues automatically  
hatch run lint:fix

# Format code with Ruff
hatch run ruff format

# Run all tests
hatch run test

# Run tests with coverage
hatch run test-cov
```

### Git Workflow

**ALWAYS run tests and linters before committing**. This project uses pre-commit hooks that will enforce these checks, but run them manually first to catch issues early.

Required steps before committing changes:

1. **Run all linters and tests**:

   ```bash
   # Run all linting checks and tests (required before committing)
   hatch run lint:all
   hatch run test
   ```

2. **Fix any linting issues**:

   ```bash
   # Fix automatic formatting issues
   hatch run lint:fix

   # Manually fix any remaining issues reported by lint:all
   ```

3. **Only add the files you actually modified**:

   ```bash
   git add src/gmail_summarizer/file1.py src/gmail_summarizer/file2.py
   ```

4. **Commit with descriptive messages** following the established pattern.

## Project Structure

```text
gmail-inbox-summary/
├── src/gmail_summarizer/
│   ├── config.py              # Configuration management
│   ├── imap_gmail_client.py   # Gmail IMAP integration
│   ├── credential_manager.py  # Secure keychain credential storage
│   ├── thread_processor.py    # Thread categorization and date extraction
│   ├── llm_summarizer.py      # Claude CLI integration
│   ├── html_generator.py      # HTML report generation and template rendering
│   └── main.py               # CLI interface
├── templates/
│   └── summary.html          # Jinja2 HTML template
├── tests/                    # Comprehensive test suite
├── config/                   # Example configurations
└── pyproject.toml           # Project configuration
```

## Key Implementation Notes

### Thread Processing (`thread_processor.py`)

- **Date Extraction**: The `_extract_most_recent_date()` method extracts timestamps from Gmail message data
- **Data Sources**: Uses Gmail API `internal_date` field first, then falls back to parsing `Date` headers
- **Timestamp Format**: Returns millisecond timestamps as integers for consistent sorting

### HTML Generation (`html_generator.py`)

- **Thread Sorting**: Threads are sorted by importance first, then by most recent date (newest first)
- **Template Context**: The `_prepare_template_context()` method handles data preparation for Jinja2
- **Date Formatting**: Custom `format_date` filter provides smart date formatting (time for today, month/day for this year, full date for older messages)

### Template Rendering (`templates/summary.html`)

- **Responsive Design**: Mobile-friendly layout with collapsible categories
- **Date Display**: Shows formatted dates next to thread titles in the metadata section
- **Interactive Features**: JavaScript for category expansion/collapse and keyboard navigation

## Common Development Tasks

### Adding New Features

1. Identify the appropriate module based on functionality
2. Add tests for new functionality first (TDD approach)
3. Implement the feature
4. Update templates if UI changes are needed
5. Run linting and tests before committing

### Debugging Email Processing Issues

1. Use the `--verbose` flag for detailed logging
2. Use `--dry-run` to test categorization without generating summaries
3. Clear cache if data structures have changed: `hatch run gmail-summary cache clear`
4. Check Gmail API data format in debug logs

### Working with Templates

- Templates use Jinja2 with custom filters defined in `html_generator.py`
- CSS is embedded in the template for self-contained output
- Test template changes by regenerating reports with sample data

## Cache Management

The application uses intelligent caching for performance. When modifying data extraction or processing logic:

```bash
# Clear cache to ensure fresh data extraction
hatch run gmail-summary cache clear
```

This is especially important when:
- Adding new fields to thread or message data
- Changing date extraction logic
- Modifying categorization criteria

## Environment and Dependencies

- **Python Version**: 3.12+ required
- **Package Manager**: Hatch (do not use pip directly)
- **Main Dependencies**: Jinja2, PyYAML, BeautifulSoup4, python-dateutil, Click, Rich, Keyring, Pydantic
- **Development Dependencies**: pytest, pytest-cov, ruff, black, mypy, pre-commit

## Best Practices

1. **Always use Hatch**: Run `hatch run` for all Python commands
2. **Test before commit**: Run `hatch run lint:all` AND `hatch run test` before every commit
3. **Fix all issues**: Address all linting and test failures before committing
4. **Clear cache when needed**: Use `hatch run gmail-summary cache clear` after data structure changes
5. **Follow existing patterns**: Study existing code structure before adding features
6. **Use descriptive commit messages**: Follow the established format with clear descriptions
7. **Only commit modified files**: Use `git add` with specific file paths

## Integration with Claude Code CLI

This project is designed to work seamlessly with Claude Code CLI:

- The application uses Claude Code CLI for generating email summaries
- Configuration includes Claude CLI path and timeout settings
- Test Claude connection with: `hatch run gmail-summary test-claude`

## Recent Changes

### Chronological Sorting and Date Display (Latest)

Recent improvements include:

- **Thread Sorting**: Implemented reverse chronological order (newest first) within categories
- **Date Extraction**: Added robust date parsing from Gmail API data with fallback mechanisms
- **Date Display**: Added formatted date display next to thread titles in HTML output
- **Smart Formatting**: Dates show as time (if today), month/day (if this year), or full date (if older)

This enhancement improves user experience by making it easy to identify recent email activity at a glance.
