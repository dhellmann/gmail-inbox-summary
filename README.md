# Gmail Inbox Summary

A Python application that generates AI-powered summaries of Gmail inbox threads using configurable categorization and Claude Code CLI integration.

> **🔒 Security Enhancement**: This application uses secure keychain storage for Gmail credentials. Your credentials are protected using your system's native credential manager (macOS Keychain, Windows Credential Manager, or Linux Secret Service).
>
## Features

- **🤖 AI-Powered Summaries**: Uses Claude Code CLI to generate intelligent, context-aware summaries
- **⚡ Parallel Processing**: Configurable concurrent summarization for 5x faster processing
- **📧 Gmail Integration**: Secure IMAP access with keychain credential storage for inbox access
- **⚙️ Configurable Categories**: Define custom thread categories using Gmail labels with pattern matching support
- **📊 Rich HTML Reports**: Beautiful, responsive HTML output with statistics and collapsible sections
- **💻 Modern CLI**: Rich command-line interface with progress indicators and colored output
- **🔧 Flexible Configuration**: YAML configuration files with comprehensive validation
- **🚀 Smart Caching**: Content-aware caching with automatic change detection for faster subsequent runs
- **🔒 Secure Credentials**: Cross-platform keychain storage for Gmail passwords with system integration
- **✅ Configuration Validation**: Automatic validation of config files with clear error messages
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

#### Gmail IMAP Access

1. **Enable Gmail IMAP** (if not already enabled):
   - Go to Gmail Settings → Forwarding and POP/IMAP
   - Enable IMAP access

2. **Create App-Specific Password** (recommended for security):
   - Go to your Google Account settings
   - Navigate to Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"

3. **Store Credentials Securely**:

   ```bash
   gmail-summary creds store --email your.email@gmail.com
   ```

   This will prompt for your password and store it securely in your system keychain.

#### Claude Code CLI

1. Install Claude Code CLI: [Installation Instructions](https://claude.ai/code)
2. Authenticate: `claude auth`
3. Test connection: `gmail-summary test-claude`

### 3. Configuration

Create a configuration file using the built-in generator, or manually create one at the default location:

**Quick Start:**
```bash
gmail-summary config generate --email your.email@gmail.com
```

**Manual Configuration:**
The configuration file is automatically placed in the platform-specific config directory:
- **macOS/Linux**: `~/.config/gmail-summary/settings.yml`
- **Windows**: `%APPDATA%/gmail-summary/settings.yml`

Example configuration:

```yaml
# Gmail IMAP Configuration
gmail:
  email_address: "your.email@gmail.com"  # Email stored in keychain
  imap_server: "imap.gmail.com"          # Optional, defaults to imap.gmail.com
  imap_port: 993                         # Optional, defaults to 993

# Claude Code CLI Configuration
claude:
  cli_path: "claude"
  timeout: 30
  concurrency: 5  # Number of concurrent summarization tasks (1-20)

# Thread Categories (customize as needed)
# Categories are now organized by Gmail labels only for simpler and more reliable categorization
categories:
  - name: "Important Messages"
    summary_prompt: "Summarize this important email, highlighting urgency and required actions."
    criteria:
      labels:
        - "is:important"  # Gmail's important label
        - "is:starred"    # Starred emails

  - name: "Meeting Invitations"
    summary_prompt: "Summarize this meeting invitation, including meeting purpose, time, and participants."
    criteria:
      labels:
        - "meeting-invitation"  # Custom label for meeting invitations

  - name: "Code"
    summary_prompt: "Summarize this development-related notification, focusing on code changes, PR status, issues, and deployments."
    criteria:
      labels:
        - "github"      # GitHub notifications
        - "gitlab"      # GitLab notifications
        - "gitlab-*"    # GitLab project-specific labels (pattern matching)

  - name: "General Email"
    summary_prompt: "Provide a brief, friendly summary of this email."
    criteria: {}  # Empty criteria = catch all remaining emails

# Important Senders (highlighted in reports)
important_senders:
  - "boss@company\\.com"
  - "urgent@client\\.org"

# Output Configuration
output_file: "inbox_summary.html"
# max_threads_per_category: null  # null for unlimited (default), or set a number like 50
```

### 4. Basic Usage

```bash
# Generate a configuration file (first time setup)
gmail-summary config generate --email your.email@gmail.com

# Store credentials securely
gmail-summary creds store --email your.email@gmail.com

# Test Claude CLI connection
gmail-summary test-claude

# Generate summary (dry run to test configuration)
gmail-summary run --dry-run --verbose

# Generate full HTML report
gmail-summary run --config config.yaml

# Customize output location
gmail-summary run --output my_summary.html

# Limit threads per category
gmail-summary run --max-threads 10

# Control parallel processing (faster processing)
gmail-summary run --concurrency 10

# Combine options for optimal performance
gmail-summary run --concurrency 8 --max-threads 50 --output daily_report.html
```

### Credential Management

```bash
# Store new credentials
gmail-summary creds store --email your.email@gmail.com

# Update existing credentials
gmail-summary creds store --email your.email@gmail.com --update

# Check if credentials exist and test IMAP connection
gmail-summary creds check your.email@gmail.com

# Check with custom config (for non-Gmail IMAP servers)
gmail-summary creds check your.email@company.com --config config.yaml

# Delete stored credentials
gmail-summary creds delete your.email@gmail.com
```

## Configuration Guide

### Gmail Configuration

```yaml
gmail:
  email_address: "your.email@gmail.com"  # Required: Gmail address (password stored in keychain)
  imap_server: "imap.gmail.com"          # Optional: IMAP server (default: imap.gmail.com)
  imap_port: 993                         # Optional: IMAP port (default: 993 for SSL)

  # Legacy support (not recommended - use keychain instead)
  password: "your-app-password"          # Will warn users to use keychain storage
```

**Security Note**: Store passwords in the system keychain using `gmail-summary creds store` instead of putting them in configuration files.

**Convenience Feature**: The `creds check` command can work without a configuration file for Gmail accounts, using default IMAP settings (imap.gmail.com:993). For custom IMAP servers, provide a configuration file with the `--config` option.

**Configuration Validation**: All configuration files are automatically validated using Pydantic models. Invalid configurations will show clear error messages with specific validation failures, including invalid email formats, out-of-range values, and unknown fields.

### Claude Configuration

```yaml
claude:
  cli_path: "claude"        # Path to Claude Code CLI executable
  timeout: 30              # Timeout in seconds for each summary request
  concurrency: 5           # Number of concurrent summarization tasks (1-20)
```

**Performance Configuration**: The `concurrency` setting controls how many email threads are summarized in parallel:

- **Default: 5** - Good balance of speed and resource usage
- **Range: 1-20** - Configurable based on your system and needs
- **Higher values** = Faster processing but more system resources
- **Lower values** = Slower but more conservative resource usage

**Performance Benefits**:
- **5x faster** with default settings compared to sequential processing
- **Scalable** up to 20 concurrent tasks for large inboxes
- **Cache-optimized** for instant retrieval of existing summaries

### Category Configuration

Categories define how threads are organized and summarized. Categories are processed in the order they appear in the configuration file - the first matching category wins.

**Default Behavior**: If no categories are defined in the configuration, a default "Everything" category is automatically created that matches all emails.

Each category supports:

```yaml
categories:
  - name: "Category Name"           # Display name
    summary_prompt: "Custom prompt for this category"
    criteria:
      # Match Gmail labels (only supported criteria type)
      labels:
        - "is:important"     # Gmail search syntax (recommended)
        - "is:starred"       # Gmail search syntax (recommended)
        - "IMPORTANT"        # Internal label format (also supported)
        - "custom-label"     # Your custom labels
        - "project-*"        # Pattern matching with wildcards
```

**Label-Only Categorization:**

- **Simplified Configuration**: Categories now only use Gmail labels for more reliable matching
- **Pattern Support**: Use wildcard patterns like `project-*` to match multiple related labels (e.g., `project-alpha`, `project-beta`)
- **Gmail Search Syntax**: Use familiar Gmail syntax like `is:important`, `is:starred`, `is:unread`
- **Custom Labels**: Apply custom labels to emails in Gmail and reference them in your configuration
- Empty criteria `{}` creates a catch-all category that matches all remaining emails

**Gmail Label Syntax and Pattern Matching:**

- **Gmail Search Syntax**: Use familiar Gmail syntax like `is:important`, `is:starred`, `is:unread`
- **Custom Labels**: Reference any custom labels you've applied in Gmail (e.g., `project-alpha`, `work-urgent`)
- **Pattern Matching**: Use wildcard patterns to match multiple related labels:
  - `gitlab-*` matches `gitlab-project1`, `gitlab-project2`, etc.
  - `meeting-*` matches `meeting-urgent`, `meeting-weekly`, etc.
  - Standard Unix filename patterns are supported (`*`, `?`, `[abc]`)
- **Internal Label Format**: Also supports Gmail's internal format like `IMPORTANT`, `STARRED`, `UNREAD`
- **Automatic Conversion**: The tool automatically converts Gmail search syntax to internal format
- **Supported Gmail Search Labels**:
  - `is:important` → `IMPORTANT`
  - `is:starred` → `STARRED`
  - `is:unread` → `UNREAD`
  - `is:read` → `READ`
  - `is:sent` → `SENT`
  - `is:draft` → `DRAFT`
  - `is:inbox` → `INBOX`
  - `is:spam` → `SPAM`
  - `is:trash` → `TRASH`
  - `is:chat` → `CHAT`

### Advanced Configuration Options

```yaml
# Highlight important senders
important_senders:
  - "ceo@company\\.com"
  - "alerts@monitoring\\.com"

# Output settings
output_file: "reports/daily_summary.html"
max_threads_per_category: 50  # Or use null for unlimited processing

# Rate limiting (optional)
gmail:
  max_requests_per_minute: 100
  batch_size: 10
```

## Command Line Reference

```
Usage: gmail-summary [OPTIONS] COMMAND [ARGS]...

Generate AI-powered summaries of Gmail inbox threads.

Commands:
  config       Manage configuration files.
  creds        Manage Gmail credentials in keychain.
  run          Generate AI-powered summaries of Gmail inbox threads.
  test-claude  Test Claude CLI connection.

Main Command:
  gmail-summary run [OPTIONS]

  Options:
    -c, --config PATH       Configuration file path (default: platform-specific)
    -o, --output PATH       Output HTML file path (overrides config)
    -n, --max-threads INT  Maximum threads per category (overrides config)
    -j, --concurrency INT  Number of concurrent summarization tasks (1-20, overrides config)
    --dry-run              Process threads without generating summaries
    -v, --verbose          Enable verbose logging
    --help                 Show this message and exit

Test Command:
  gmail-summary test-claude [OPTIONS]

  Options:
    -c, --config PATH      Configuration file path (default: platform-specific)
    -v, --verbose         Enable verbose logging
    --help                Show this message and exit

Credential Management:
  gmail-summary creds store [OPTIONS]
    -e, --email TEXT       Gmail email address
    --update              Update existing credentials

  gmail-summary creds check <EMAIL> [OPTIONS]    # Check credentials and test IMAP connection
    -c, --config PATH      Configuration file (optional, uses Gmail defaults)
    -v, --verbose         Enable verbose logging
  gmail-summary creds delete <EMAIL>    # Delete stored credentials

Configuration Management:
  gmail-summary config generate [OPTIONS]  # Generate example configuration file
    -e, --email TEXT       Gmail email address to use in config
    -o, --output PATH      Configuration file output path (default: platform-specific)
    -f, --force            Overwrite existing configuration file
```

## Example Workflows

### Daily Email Summary

```bash
# Morning routine: generate yesterday's email summary
gmail-summary run --config daily_config.yaml --output "summaries/$(date +%Y%m%d).html"
```

### Weekly Team Review

```bash
# Generate summary for team review with more threads and faster processing
gmail-summary run --max-threads 50 --concurrency 10 --output weekly_team_summary.html
```

### Performance Optimization

```bash
# Fast processing for large inboxes
gmail-summary run --concurrency 15 --max-threads 100

# Conservative processing for limited resources
gmail-summary run --concurrency 2 --max-threads 20

# Balanced approach for daily use
gmail-summary run --concurrency 8 --max-threads 50
```

### Testing New Configuration

```bash
# Test configuration changes without generating summaries
gmail-summary run --config new_config.yaml --dry-run --verbose
```

### First-Time Setup Workflow

```bash
# 1. Generate configuration file
gmail-summary config generate --email your.email@gmail.com

# 2. Store credentials securely
gmail-summary creds store --email your.email@gmail.com

# 3. Test Claude CLI connection
gmail-summary test-claude

# 4. Test configuration with dry run
gmail-summary run --dry-run --verbose

# 5. Generate actual summary
gmail-summary run
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
│   ├── config.py              # Configuration management
│   ├── imap_gmail_client.py   # Gmail IMAP integration
│   ├── credential_manager.py  # Secure keychain credential storage
│   ├── thread_processor.py    # Thread categorization
│   ├── llm_summarizer.py      # Claude CLI integration
│   ├── html_generator.py      # HTML report generation
│   └── main.py               # CLI interface
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
Error: Gmail credentials not found
```

- Store credentials: `gmail-summary creds store --email your.email@gmail.com`
- Ensure Gmail IMAP is enabled in your Gmail settings
- Use app-specific password, not your regular Gmail password
- Test stored credentials: `gmail-summary creds check your.email@gmail.com`

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
- Ensure proper indentation (spaces, not tabs)
- Check label names and pattern syntax

**Configuration Validation Errors:**

```
Error: Invalid configuration: 1 validation error
  gmail.email_address
    Invalid email address format
```

Common validation issues:
- Invalid email format (missing @ symbol)
- Port numbers outside valid range (1-65535)
- Timeout values outside valid range (1-600 seconds)
- Empty category names or prompts
- Duplicate category names
- Unknown configuration fields

**No Threads Found:**

```
Warning: No threads matched any category
```

- Check Gmail label filters in your configuration
- Verify that emails have the labels you're looking for
- Use wildcard patterns like `project-*` to match multiple labels
- Add a catch-all category with empty criteria: `criteria: {}`

### Debug Mode

Enable detailed logging:

```bash
gmail-summary run --verbose --config config.yaml --dry-run
```

This shows:

- Configuration loading details
- Thread categorization process
- Pattern matching results
- API call information

### Performance Tips

**Parallel Processing**:
- **Increase concurrency** for faster processing: `--concurrency 10-15` for large inboxes
- **Default concurrency (5)** works well for most users
- **Lower concurrency (1-3)** for systems with limited resources or API rate limits
- **Cache benefits**: Second runs are much faster due to intelligent caching

**Other Optimizations**:
- Use `max_threads_per_category` to limit processing time (or set to `null` for unlimited processing)
- Test with `--dry-run` first to verify configuration
- Consider running during off-peak hours for large inboxes
- Use specific Gmail labels to pre-filter threads
- Combine settings: `--concurrency 8 --max-threads 50` for balanced performance

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
