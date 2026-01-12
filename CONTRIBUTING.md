# Contributing to Gmail Inbox Summary

Thank you for your interest in contributing to Gmail Inbox Summary! This guide will help you get started with development and ensure your contributions follow our standards.

## Quick Start for Contributors

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/gmail-inbox-summary.git
cd gmail-inbox-summary

# Add upstream remote for staying up-to-date
git remote add upstream https://github.com/dhellmann/gmail-inbox-summary.git
```

### 2. Development Environment Setup

We use [Hatch](https://hatch.pypa.io/) for development environment management:

```bash
# Install Hatch if you don't have it
pip install hatch

# Create and enter the development environment
hatch env create
hatch shell

# Verify the setup
gmail-summary --help
```

### 3. Install Pre-commit Hooks

```bash
# Install pre-commit hooks for code quality
hatch run pre-commit install

# Test the hooks
hatch run pre-commit run --all-files
```

## Development Workflow

### Creating a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a new feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### Running the Application Locally

```bash
# Activate the development environment
hatch shell

# Run with development code
gmail-summary --help
gmail-summary --test-claude
gmail-summary --dry-run --verbose
```

### Code Quality and Testing

#### Running Tests

```bash
# Run the full test suite
hatch run test

# Run tests with coverage reporting
hatch run test-cov

# Run specific test files
hatch run test tests/test_integration.py
hatch run test tests/test_html_generator.py

# Run tests for a specific function
hatch run test -k test_cli_dry_run
```

#### Code Linting and Formatting

```bash
# Check code quality (linting + formatting)
hatch run lint:check

# Auto-fix formatting issues
hatch run lint:fix

# Run all quality checks (includes type checking)
hatch run lint:all

# Run only type checking
hatch run lint:typing
```

#### Individual Tools

```bash
# Ruff linting
hatch run ruff check .

# Ruff formatting
hatch run ruff format .

# MyPy type checking
hatch run mypy src/gmail_summarizer tests

# Pre-commit hooks (runs all checks)
hatch run pre-commit run --all-files
```

## Project Structure

```
gmail-inbox-summary/
├── src/gmail_summarizer/           # Main application code
│   ├── __init__.py                # Package initialization
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Configuration management
│   ├── gmail_client.py            # Gmail API integration
│   ├── thread_processor.py        # Thread categorization
│   ├── llm_summarizer.py         # Claude CLI integration
│   └── html_generator.py         # HTML report generation
├── templates/                      # Jinja2 templates
│   └── summary.html              # Main HTML report template
├── tests/                         # Test suite
│   ├── test_config.py            # Configuration tests
│   ├── test_gmail_client.py      # Gmail API tests
│   ├── test_thread_processor.py  # Thread processing tests
│   ├── test_llm_summarizer.py    # LLM integration tests
│   ├── test_html_generator.py    # HTML generation tests
│   └── test_integration.py       # End-to-end tests
├── config/                        # Example configurations
├── docs/                          # Documentation
├── pyproject.toml                 # Project configuration
├── README.md                      # User documentation
├── INSTALL.md                     # Installation guide
└── CONTRIBUTING.md                # This file
```

## Code Standards

### Python Code Style

We use modern Python practices with the following tools:

- **Python 3.12+**: Use modern union syntax (`str | None` instead of `Optional[str]`)
- **Ruff**: For linting and formatting (replaces Black, isort, and many flake8 plugins)
- **MyPy**: For static type checking
- **Type hints**: Required for all functions and methods

#### Example Code Style

```python
from typing import Any

def process_threads(
    self,
    categorized_threads: dict[str, list[dict[str, Any]]]
) -> dict[str, list[dict[str, Any]]]:
    """Process threads and return categorized results.

    Args:
        categorized_threads: Dictionary mapping category names to thread lists

    Returns:
        Processed categorized threads

    Raises:
        ProcessingError: If thread processing fails
    """
    # Implementation here
    pass
```

### Testing Standards

- **100% test coverage** for new code
- **Unit tests** for individual components
- **Integration tests** for end-to-end workflows
- **Mocking** for external dependencies (Gmail API, Claude CLI)

#### Test Example

```python
import pytest
from unittest.mock import Mock, patch

def test_feature_functionality():
    """Test feature with proper mocking."""
    # Arrange
    mock_config = Mock()
    mock_config.get_setting.return_value = "test_value"

    # Act
    result = your_function(mock_config)

    # Assert
    assert result == expected_value
    mock_config.get_setting.assert_called_once_with("setting_name")
```

### Documentation Standards

- **Docstrings**: Google-style docstrings for all public functions
- **Type hints**: Complete type annotations
- **README updates**: Update user documentation for new features
- **Code comments**: Explain complex logic, not obvious operations

## Making Changes

### 1. Implement Your Changes

- Follow the existing code style and patterns
- Add comprehensive tests for new functionality
- Update documentation as needed
- Ensure all existing tests still pass

### 2. Test Your Changes

```bash
# Run full test suite
hatch run test

# Check code quality
hatch run lint:all

# Test the CLI manually
hatch shell
gmail-summary --dry-run --verbose
```

### 3. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add new email filtering feature

- Add regex pattern support for email filtering
- Update configuration schema to support new patterns
- Add comprehensive tests for filter functionality
- Update documentation with examples

Closes #123"
```

### Commit Message Format

We use conventional commits:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions or modifications
- `refactor:` - Code refactoring
- `style:` - Formatting, no code changes
- `chore:` - Maintenance tasks

### 4. Submit a Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create a pull request on GitHub
```

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass (`hatch run test`)
- [ ] Code quality checks pass (`hatch run lint:all`)
- [ ] Pre-commit hooks pass (`hatch run pre-commit run --all-files`)
- [ ] Documentation is updated (if applicable)
- [ ] New functionality includes tests
- [ ] CHANGELOG.md is updated (for significant changes)

### Pull Request Description

Include in your PR description:

1. **Summary**: Brief description of changes
2. **Motivation**: Why this change is needed
3. **Changes**: List of specific changes made
4. **Testing**: How you tested the changes
5. **Breaking Changes**: Any breaking changes (if applicable)

#### Example PR Description

```markdown
## Summary
Add pattern matching support for Gmail label filtering

## Motivation
Users needed ability to match multiple related labels using wildcard patterns (e.g., "project-*" to match "project-alpha", "project-beta").

## Changes
- Added fnmatch pattern support to label matching in thread_processor.py
- Updated configuration documentation with pattern examples
- Added comprehensive tests for pattern matching functionality
- Updated examples to show label-based categorization

## Testing
- Added unit tests for pattern matching logic
- Added integration test for end-to-end label pattern filtering
- Tested manually with various Gmail label pattern configurations
- All existing tests continue to pass

## Breaking Changes
None - this is backward compatible with existing exact label matches.
```

## Development Tips

### Environment Management

```bash
# List all available environments
hatch env show

# Remove and recreate environment (if needed)
hatch env prune
hatch env create

# Run commands in specific environments
hatch run lint:check
hatch run test
```

### Debugging

```bash
# Run with verbose output
gmail-summary --verbose --dry-run

# Use Python debugger
python -m pdb -m gmail_summarizer.main --help

# Run specific tests with debugging
hatch run python -m pytest tests/test_integration.py -v -s
```

### Working with Configuration

```bash
# Generate and test with sample configuration
gmail-summary config generate --email test@example.com --output test_config.yaml
gmail-summary --config test_config.yaml --dry-run
```

### Performance Testing

```bash
# Profile the application
hatch run python -m cProfile -s cumtime -m gmail_summarizer.main --dry-run

# Memory profiling (install memory_profiler first)
hatch run pip install memory_profiler
hatch run python -m memory_profiler -m gmail_summarizer.main --dry-run
```

## Getting Help

### Resources

- **Documentation**: [README.md](README.md) for user guide
- **Installation**: [INSTALL.md](INSTALL.md) for setup help
- **Issues**: [GitHub Issues](https://github.com/dhellmann/gmail-inbox-summary/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dhellmann/gmail-inbox-summary/discussions)

### Common Issues

**Environment Issues:**
```bash
# Reset the development environment
hatch env prune
hatch env create
hatch shell
```

**Test Failures:**
```bash
# Run tests with more verbose output
hatch run test -v -s

# Run a specific failing test
hatch run test tests/test_integration.py::test_specific_function -v
```

**Import Errors:**
```bash
# Ensure you're in the development environment
hatch shell

# Check the package is installed correctly
pip list | grep gmail-inbox-summary
```

## Code Review Process

1. **Automated Checks**: CI will run tests and quality checks
2. **Manual Review**: Maintainers will review code and design
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, your PR will be merged

### Review Criteria

- Code follows established patterns and style
- Comprehensive test coverage
- Clear, maintainable code
- Good performance characteristics
- Proper error handling
- Updated documentation

## Release Process

For maintainers:

```bash
# Build the package
hatch build

# Publish to PyPI
hatch publish

# Tag the release
git tag v1.0.0
git push origin v1.0.0
```

## Community

- Be respectful and constructive in all interactions
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- Help others in discussions and issues
- Share knowledge and best practices

Thank you for contributing to Gmail Inbox Summary! 🎉
