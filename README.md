# Gmail Inbox Summary

A Python application that generates AI-powered summaries of Gmail inbox threads using configurable categorization and Claude Code CLI integration.

## Features

- **🤖 AI-Powered Summaries**: Uses Claude Code CLI to generate intelligent, context-aware summaries
- **📧 Gmail Integration**: Secure OAuth2 authentication with Gmail API for inbox access
- **⚙️ Configurable Categories**: Define custom thread categories with flexible regex-based matching
- **📊 Rich HTML Reports**: Beautiful, responsive HTML output with statistics and collapsible sections
- **💻 Modern CLI**: Rich command-line interface with progress indicators and colored output
- **🔧 Flexible Configuration**: Support for both unified YAML config files and modular configurations
- **🧪 Comprehensive Testing**: Full test coverage with unit and integration tests

## Quick Start

### 1. Installation

```bash
# Install from PyPI (recommended)
pip install gmail-inbox-summary

# Or install the latest development version from GitHub
pip install git+https://github.com/dhellmann/gmail-inbox-summary.git
```

### 2. Prerequisites Setup

Before using the application, you need:

#### Gmail API Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials file as `credentials.json`

#### Claude Code CLI
1. Install Claude Code CLI: [Installation Instructions](https://claude.ai/code)
2. Authenticate: `claude auth`
3. Test connection: `gmail-summary --test-claude`

### 3. Gmail Setup

1. **Enable Gmail IMAP** (if not already enabled):
   - Go to Gmail Settings → Forwarding and POP/IMAP
   - Enable IMAP access

2. **Create App-Specific Password** (recommended for security):
   - Go to your Google Account settings
   - Navigate to Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"

### 4. Configuration

Create a configuration file `config.yaml`:

```yaml
# Gmail IMAP Configuration
gmail:
  email_address: "your.email@gmail.com"
  password: "your-app-specific-password"

# Claude Code CLI Configuration  
claude:
  cli_path: "claude"
  timeout: 30

# Thread Categories (customize as needed)
categories:
  - name: "Work Email"
    summary_prompt: "Summarize this work-related email focusing on action items, decisions, and deadlines."
    criteria:
      from_patterns:
        - ".*@company\\.com"
        - ".*@client\\.org"
      subject_patterns:
        - "\\[PROJECT\\]"
        - "Meeting:"

  - name: "GitHub Notifications"
    summary_prompt: "Summarize this GitHub notification, focusing on PR status, issues, and code changes."
    criteria:
      from_patterns:
        - "notifications@github\\.com"
      subject_patterns:
        - "\\[.*\\].*Pull Request"
        - "\\[.*\\].*Issue"

  - name: "Personal"
    summary_prompt: "Provide a brief, friendly summary of this personal email."
    criteria: {}  # Catch-all for remaining emails

# Important Senders (highlighted in reports)
important_senders:
  - "boss@company\\.com"
  - "urgent@client\\.org"

# Output Configuration
output_file: "inbox_summary.html"
max_threads_per_category: 20
```

### 4. Basic Usage

```bash
# Test Claude CLI connection
gmail-summary --test-claude

# Generate summary (dry run to test configuration)
gmail-summary --dry-run --verbose

# Generate full HTML report
gmail-summary --config config.yaml

# Customize output location
gmail-summary --output my_summary.html

# Limit threads per category
gmail-summary --max-threads 10
```

## Configuration Guide

### Gmail Configuration

```yaml
gmail:
  credentials_file: "path/to/credentials.json"  # OAuth2 credentials from Google Cloud Console
  token_file: "token.json"                     # Where to store authentication tokens
```

### Claude Configuration

```yaml
claude:
  cli_path: "claude"        # Path to Claude Code CLI executable
  timeout: 30              # Timeout in seconds for each summary request
```

### Category Configuration

Categories define how threads are organized and summarized. Categories are processed in the order they appear in the configuration file - the first matching category wins. Each category supports:

```yaml
categories:
  - name: "Category Name"           # Display name
    summary_prompt: "Custom prompt for this category"
    criteria:
      # Match sender email patterns
      from_patterns:
        - ".*@domain\\.com"
        - "noreply@service\\.net"
      
      # Match recipient patterns  
      to_patterns:
        - "team@company\\.com"
      
      # Match subject line patterns
      subject_patterns:
        - "\\[ALERT\\]"
        - "Daily Report:"
      
      # Match message content
      content_patterns:
        - "invoice.*attached"
      
      # Match custom headers
      headers:
        "List-Id": ".*@lists\\.domain\\.com"
      
      # Match Gmail labels
      labels:
        - "IMPORTANT"
        - "CATEGORY_PROMOTIONS"
```

**Pattern Matching:**
- Use regex patterns with proper escaping: `\\.` for literal dots
- Patterns are case-insensitive by default
- Empty criteria `{}` creates a catch-all category

### Advanced Configuration Options

```yaml
# Highlight important senders
important_senders:
  - "ceo@company\\.com"
  - "alerts@monitoring\\.com"

# Output settings
output_file: "reports/daily_summary.html"
max_threads_per_category: 50

# Rate limiting (optional)
gmail:
  max_requests_per_minute: 100
  batch_size: 10
```

## Command Line Reference

```
Usage: gmail-summary [OPTIONS]

Generate AI-powered summaries of Gmail inbox threads.

Options:
  -c, --config PATH       Configuration file path (default: config.yaml)
  -o, --output PATH       Output HTML file path (overrides config)
  -n, --max-threads INT  Maximum threads per category (overrides config)
  --dry-run              Process threads without generating summaries
  --test-claude          Test Claude CLI connection and exit
  -v, --verbose          Enable verbose logging
  --help                 Show this message and exit
```

## Example Workflows

### Daily Email Summary
```bash
# Morning routine: generate yesterday's email summary
gmail-summary --config daily_config.yaml --output "summaries/$(date +%Y%m%d).html"
```

### Weekly Team Review  
```bash
# Generate summary for team review with more threads
gmail-summary --max-threads 50 --output weekly_team_summary.html
```

### Testing New Configuration
```bash
# Test configuration changes without API calls
gmail-summary --config new_config.yaml --dry-run --verbose
```

## HTML Report Features

The generated HTML reports include:

- **📊 Statistics Dashboard**: Thread counts, summary success rates, processing time
- **🗂️ Collapsible Categories**: Organized sections with expand/collapse functionality  
- **⭐ Priority Highlighting**: Important senders marked with visual indicators
- **📱 Responsive Design**: Mobile-friendly layout that works on all devices
- **🖨️ Print-Friendly**: Clean formatting when printed or saved as PDF
- **♿ Accessibility**: Screen reader support and keyboard navigation

## Development

### Project Structure

```
gmail-inbox-summary/
├── src/gmail_summarizer/
│   ├── config.py           # Configuration management
│   ├── gmail_client.py     # Gmail API integration
│   ├── thread_processor.py # Thread categorization
│   ├── llm_summarizer.py   # Claude CLI integration
│   ├── html_generator.py   # HTML report generation
│   └── main.py            # CLI interface
├── templates/
│   └── summary.html       # Jinja2 HTML template
├── tests/                 # Comprehensive test suite
├── config/               # Example configurations
└── pyproject.toml        # Project configuration
```

### Running Tests

```bash
# Run all tests
hatch run test

# Run with coverage
hatch run test-cov

# Run specific test file
hatch run test tests/test_integration.py

# Run linting
hatch run lint:check
hatch run lint:fix
```

### Building and Distribution

```bash
# Build package for PyPI
hatch build

# Publish to PyPI (maintainers only)
hatch publish

# Install in development mode
hatch run pip install -e .

# Run pre-commit hooks
hatch run pre-commit run --all-files
```

## Troubleshooting

### Common Issues

**Gmail Authentication Errors:**
```
Error: Failed to authenticate with Gmail API
```
- Ensure `credentials.json` exists and is valid
- Check that Gmail API is enabled in Google Cloud Console
- Delete `token.json` to force re-authentication

**Claude CLI Connection Issues:**
```
Error: Claude CLI not available
```
- Install Claude Code CLI: [Installation Guide](https://claude.ai/code)
- Authenticate: `claude auth`
- Check path: `which claude`

**Configuration Syntax Errors:**
```
Error: Invalid YAML syntax
```
- Validate YAML syntax with online tools
- Check regex pattern escaping: use `\\.` for literal dots
- Ensure proper indentation (spaces, not tabs)

**No Threads Found:**
```
Warning: No threads matched any category
```
- Check Gmail label filters
- Verify regex patterns with test data
- Add a catch-all category with empty criteria: `criteria: {}`

### Debug Mode

Enable detailed logging:
```bash
gmail-summary --verbose --config config.yaml --dry-run
```

This shows:
- Configuration loading details
- Thread categorization process
- Pattern matching results
- API call information

### Performance Tips

- Use `max_threads_per_category` to limit processing time
- Test with `--dry-run` first to verify configuration
- Consider running during off-peak hours for large inboxes
- Use specific Gmail labels to pre-filter threads

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for detailed information on:

- Setting up the development environment
- Running tests and linters
- Code style and standards
- Submitting pull requests

Quick start for contributors:
```bash
git clone https://github.com/YOUR-USERNAME/gmail-inbox-summary.git
cd gmail-inbox-summary
hatch env create && hatch shell
hatch run pre-commit install
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/dhellmann/gmail-inbox-summary/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dhellmann/gmail-inbox-summary/discussions)
- **Documentation**: This README and inline code documentation

---

*Generated with ❤️ using Claude Code CLI*