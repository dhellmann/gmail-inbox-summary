# Installation Guide

## Quick Installation

### Option 1: PyPI Installation (Recommended)

```bash
# Install the latest stable release
pip install gmail-inbox-summary

# Verify installation
gmail-summary --help
```

### Option 2: Development Version

```bash
# Install latest development version from GitHub
pip install git+https://github.com/dhellmann/gmail-inbox-summary.git

# Verify installation
gmail-summary --help
```

### Option 3: Development Setup

For contributing or advanced usage:

```bash
# Clone the repository
git clone https://github.com/dhellmann/gmail-inbox-summary.git
cd gmail-inbox-summary

# Install with Hatch for development
hatch env create
hatch shell

# Verify installation
gmail-summary --help
```

## Prerequisites

### 1. Python Requirements

- Python 3.12 or higher
- pip package manager

### 2. Gmail Setup

1. **Enable Gmail IMAP:**
   - Open Gmail in your browser
   - Go to Settings (gear icon) → "See all settings"
   - Navigate to "Forwarding and POP/IMAP" tab
   - Under "IMAP access", select "Enable IMAP"
   - Save changes

2. **Create App-Specific Password (Recommended):**
   - Go to your [Google Account settings](https://myaccount.google.com/)
   - Navigate to Security → 2-Step Verification
   - If not enabled, set up 2-Step Verification first
   - Under "Signing in to Google", click "App passwords"
   - Select "Mail" as the app and generate password
   - Copy the generated password (you'll need it for configuration)

### 3. Claude Code CLI Setup

1. **Install Claude Code CLI:**
   - Visit [Claude Code Installation](https://claude.ai/code)
   - Follow installation instructions for your platform
   - Verify: `claude --version`

2. **Authenticate:**
   ```bash
   claude auth
   ```

3. **Test Connection:**
   ```bash
   gmail-summary --test-claude
   ```

## Configuration

1. **Generate Configuration:**
   ```bash
   gmail-summary config generate --email your.email@gmail.com
   ```

2. **Store Gmail Credentials Securely:**
   ```bash
   gmail-summary creds store --email your.email@gmail.com
   ```
   Enter your app-specific password when prompted.

3. **Customize Configuration (Optional):**
   ```bash
   # Edit with your preferred editor
   nano ~/.config/gmail-inbox-summary/config.yaml
   # or
   code ~/.config/gmail-inbox-summary/config.yaml
   ```

4. **Customize Categories and Performance (Optional):**
   - Modify email patterns to match your inbox
   - Adjust summary prompts for your needs
   - Set appropriate output file location
   - Configure parallel processing: `concurrency: 5` (default) to `concurrency: 10` (faster)

## Verification

Test your installation:

```bash
# Test configuration
gmail-summary --dry-run --verbose

# Test Claude connection
gmail-summary --test-claude

# Generate actual summary (if all tests pass)
gmail-summary

# Test with parallel processing for faster results
gmail-summary --concurrency 8 --max-threads 25
```

## Troubleshooting

### Common Installation Issues

**Python Version:**
```bash
python --version  # Should be 3.12+
```

**Hatch Installation:**
```bash
pip install hatch
```

**Permission Issues:**
```bash
# Use --user flag to install without root privileges:
pip install --user gmail-inbox-summary

# Or use a virtual environment (recommended):
python -m venv gmail-summary-env
source gmail-summary-env/bin/activate  # On Windows: gmail-summary-env\Scripts\activate
pip install gmail-inbox-summary
```

**Gmail API Issues:**
- Ensure Gmail API is enabled in Google Cloud Console
- Check `credentials.json` is in the correct location
- Delete `token.json` and re-authenticate if having auth issues

**Claude CLI Issues:**
```bash
# Check if Claude CLI is in PATH
which claude

# Re-authenticate if needed
claude auth --refresh
```

### Getting Help

If installation fails:

1. Check the [Troubleshooting](README.md#troubleshooting) section in README.md
2. Open an [issue](https://github.com/dhellmann/gmail-inbox-summary/issues) with:
   - Your operating system
   - Python version (`python --version`)
   - Error message (full output)
   - Steps you've tried

## Development Installation

For contributing to the project, please see our comprehensive [Contributing Guide](CONTRIBUTING.md) which covers:

- Development environment setup with Hatch
- Running tests and quality checks
- Code style guidelines
- Submitting pull requests

Quick development setup:
```bash
git clone https://github.com/YOUR-USERNAME/gmail-inbox-summary.git
cd gmail-inbox-summary
hatch env create && hatch shell
hatch run pre-commit install
```

## Next Steps

After successful installation:

1. **Configure Gmail API** (see Prerequisites section)
2. **Set up Claude Code CLI** (see Prerequisites section)  
3. **Customize configuration** (`config.yaml`)
4. **Run first summary** (`gmail-summary --dry-run`)
5. **Generate HTML report** (`gmail-summary`)

See [README.md](README.md) for detailed usage instructions and configuration options.
