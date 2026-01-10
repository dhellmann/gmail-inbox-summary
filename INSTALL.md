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

### 2. Gmail API Setup

1. **Google Cloud Project Setup:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Gmail API in the API Library

2. **OAuth2 Credentials:**
   - Go to "Credentials" in the sidebar
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the JSON file as `credentials.json`
   - Place it in your project directory

3. **First-time Authentication:**
   ```bash
   # Run any command - it will trigger OAuth flow
   gmail-summary --test-claude
   ```
   - Browser will open for Google authentication
   - Grant permissions to access Gmail
   - `token.json` will be created automatically

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

1. **Copy Example Configuration:**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **Edit Configuration:**
   ```bash
   # Edit with your preferred editor
   nano config.yaml
   # or
   code config.yaml
   ```

3. **Customize Categories:**
   - Modify email patterns to match your inbox
   - Adjust summary prompts for your needs
   - Set appropriate output file location

## Verification

Test your installation:

```bash
# Test configuration
gmail-summary --dry-run --verbose

# Test Claude connection
gmail-summary --test-claude

# Generate actual summary (if all tests pass)
gmail-summary
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