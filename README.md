# Gmail Inbox Summary

A Python application that generates AI-powered summaries of Gmail inbox threads using configurable categorization and Claude Code CLI integration.

## Features

- **Configurable categorization**: Define custom thread categories with flexible matching criteria
- **AI-powered summaries**: Uses Claude Code CLI to generate intelligent summaries for each thread
- **Gmail API integration**: Securely accesses Gmail inbox using OAuth2 authentication
- **HTML output**: Generates responsive HTML reports with collapsible sections
- **Modern Python tooling**: Built with Hatch for dependency management and development workflows

## Installation

This project uses Hatch for development. Install dependencies:

```bash
hatch env create
```

## Development

Run tests:
```bash
hatch run test
```

Run linting and formatting:
```bash
hatch run lint:all
```

## Usage

```bash
gmail-summary --help
```

## Configuration

See `config/` directory for example configuration files.