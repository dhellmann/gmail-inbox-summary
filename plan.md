# Gmail Inbox Summary Application Implementation Plan

## Project Structure (Hatch-based)

```
gmail-inbox-summary/
├── src/
│   └── gmail_summarizer/
│       ├── __init__.py
│       ├── main.py              # CLI entry point
│       ├── gmail_client.py      # Gmail API integration
│       ├── thread_processor.py  # Configurable thread categorization
│       ├── llm_summarizer.py    # Claude Code CLI integration
│       ├── html_generator.py    # HTML output generation
│       └── config.py           # Configuration management
├── templates/
│   └── summary.html            # Jinja2 template for output
├── static/
│   └── style.css              # CSS styling
├── tests/
│   ├── __init__.py
│   ├── test_thread_processor.py
│   ├── test_llm_summarizer.py
│   └── fixtures/
├── config/
│   ├── settings.yaml          # Main configuration
│   └── categories.yaml        # Category definitions
├── pyproject.toml             # Hatch project configuration
├── README.md
└── .gitignore
```

## Implementation Phases

### Phase 1: Project Setup with Hatch

1. Initialize Hatch project structure
2. Configure `pyproject.toml` with:
   - Project metadata and dependencies
   - Build system configuration
   - Entry points for CLI
   - Development dependencies
   - Testing and linting tools
3. Set up development environment with Hatch
4. Commit the changes.

### Phase 2: Gmail API Integration

1. Set up Gmail API authentication (OAuth2)
2. Implement `gmail_client.py` with methods to:
   - Authenticate with Gmail API
   - Fetch all threads from inbox
   - Retrieve thread details and messages
   - Handle pagination for large inboxes
3. Commit the changes.

### Phase 3: Configurable Thread Processing

1. Create `thread_processor.py` with:
   - Dynamic category loader from configuration
   - Flexible message matching engine supporting:
     - Gmail labels, sender/recipient patterns
     - Subject line patterns, message content patterns
     - Message headers, date ranges
   - Priority-based categorization
   - Special sender highlighting
2. Commit the changes.

### Phase 4: LLM-Powered Summarization

1. Implement `llm_summarizer.py` with:
   - Claude Code CLI integration
   - Custom prompt handling per category
   - Error handling and batch processing
2. Commit the changes.

### Phase 5: HTML Generation & CLI

1. Design responsive HTML template
2. Implement `html_generator.py` using Jinja2
3. Create CLI interface in `main.py` with click/typer
4. Commit the changes.

### Phase 6: Testing & Quality Assurance

1. Implement comprehensive test suite with pytest
2. Set up pre-commit hooks with ruff, black, mypy
3. Add CI/CD configuration
4. Commit the changes.

## Hatch Configuration (pyproject.toml)

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "gmail-inbox-summary"
dynamic = ["version"]
description = "Generate AI-powered summaries of Gmail inbox threads"
readme = "README.md"
requires-python = ">=3.9"
license = "MIT"
authors = [
    { name = "Your Name", email = "your.email@example.com" },
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "google-api-python-client>=2.0.0",
    "google-auth-httplib2>=0.1.0",
    "google-auth-oauthlib>=0.8.0",
    "jinja2>=3.1.0",
    "pyyaml>=6.0",
    "beautifulsoup4>=4.12.0",
    "python-dateutil>=2.8.0",
    "click>=8.0.0",
    "rich>=13.0.0",
]

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
    "pre-commit>=3.0.0",
]

[project.urls]
Documentation = "https://github.com/username/gmail-inbox-summary#readme"
Issues = "https://github.com/username/gmail-inbox-summary/issues"
Source = "https://github.com/username/gmail-inbox-summary"

[project.scripts]
gmail-summary = "gmail_summarizer.main:cli"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/gmail_summarizer/_version.py"

[tool.hatch.envs.default]
dependencies = [
    "coverage[toml]>=6.5",
    "pytest",
]

[tool.hatch.envs.default.scripts]
test = "pytest {args:tests}"
test-cov = "coverage run -m pytest {args:tests}"
cov-report = [
    "- coverage combine",
    "coverage report",
]
cov = [
    "test-cov",
    "cov-report",
]

[tool.hatch.envs.lint]
detached = true
dependencies = [
    "black>=23.1.0",
    "mypy>=1.0.0",
    "ruff>=0.0.243",
]

[tool.hatch.envs.lint.scripts]
typing = "mypy --install-types --non-interactive {args:src/gmail_summarizer tests}"
style = [
    "ruff {args:.}",
    "black --check --diff {args:.}",
]
fmt = [
    "black {args:.}",
    "ruff --fix {args:.}",
    "style",
]
all = [
    "style",
    "typing",
]

[tool.ruff]
target-version = "py39"
line-length = 88
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.coverage.run]
source_pkgs = ["gmail_summarizer", "tests"]
branch = true
parallel = true
omit = [
    "src/gmail_summarizer/__about__.py",
]

[tool.coverage.report]
exclude_lines = [
    "no cov",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Key Benefits of Hatch Structure

- **Isolated environments**: Separate environments for dev, test, lint
- **Standardized build**: Modern Python packaging with pyproject.toml
- **Dependency management**: Clear separation of runtime vs dev dependencies
- **CLI integration**: Automatic entry point generation
- **Testing framework**: Built-in pytest integration with coverage
- **Code quality**: Pre-configured ruff, black, and mypy
- **Reproducible builds**: Version management and environment isolation

This structure follows modern Python best practices and provides a solid foundation for a maintainable, distributable application.

The project uses hatch-vcs for automatic version management from git tags, eliminating the need for manual version tracking.
