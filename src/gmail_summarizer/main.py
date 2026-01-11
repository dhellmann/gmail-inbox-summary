"""Command-line interface for Gmail Inbox Summary."""

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import BarColumn
from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TextColumn
from rich.progress import TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table

from .cache_manager import CacheManager
from .config import Config
from .config import get_default_config_path
from .credential_manager import CredentialManager
from .credential_manager import GmailCredentials
from .html_generator import HTMLGenerator
from .imap_gmail_client import ImapGmailClient
from .llm_summarizer import LLMSummarizer
from .thread_processor import ThreadProcessor

console = Console()
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Set up logging with Rich formatting."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )

    # Suppress noisy third-party loggers
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)


@click.group()
@click.version_option()
def cli() -> None:
    """Generate AI-powered summaries of Gmail inbox threads.

    This tool reads your Gmail inbox, categorizes threads based on configurable
    criteria, generates AI summaries using Claude Code CLI, and outputs a
    beautiful HTML report.

    Before running, ensure you have:
    1. Set up Gmail IMAP access and stored credentials securely
    2. Installed Claude Code CLI and authenticated
    3. Created configuration file (use: gmail-summary config generate)
    """
    pass


@cli.group()
def creds() -> None:
    """Manage Gmail credentials in keychain."""
    pass


@cli.group()
def cache() -> None:
    """Manage cache for email threads and summaries."""
    pass


@creds.command()
@click.option("--email", "-e", help="Gmail email address")
@click.option(
    "--update",
    is_flag=True,
    help="Update existing credentials",
)
def store(email: str | None, update: bool) -> None:
    """Store Gmail credentials in keychain."""
    credential_manager = CredentialManager()

    if not email:
        email = Prompt.ask("[cyan]Gmail email address[/cyan]")

    if not email:
        console.print("[red]Email address is required[/red]")
        raise click.Abort()

    # Get password
    console.print("\n[cyan]Gmail password or app-specific password:[/cyan]")
    console.print(
        "[dim]App-specific passwords are recommended for better security[/dim]"
    )
    console.print("[dim]Create one at: https://myaccount.google.com/apppasswords[/dim]")

    password = Prompt.ask("[cyan]Password[/cyan]", password=True)

    if not password:
        console.print("[red]Password is required[/red]")
        raise click.Abort()

    success = credential_manager.store_credentials(email, password, update)
    if not success:
        raise click.Abort()


@creds.command()
@click.argument("email")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file (optional)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def check(email: str, config: Path | None, verbose: bool) -> None:
    """Check credentials and test IMAP connection."""
    setup_logging(verbose)
    credential_manager = CredentialManager()

    # First check if credentials exist in keychain
    credentials = credential_manager.get_credentials(email)
    if not credentials:
        console.print(f"[red]✗ No credentials found for {email} in keychain[/red]")
        raise click.Abort()

    console.print(f"[green]✓ Credentials found for {email} in keychain[/green]")

    # Test IMAP connection
    try:
        # Get IMAP settings from config file or use defaults
        if config:
            app_config = Config(str(config))
            gmail_config = app_config.get_gmail_config()
            imap_server = gmail_config.get("imap_server", "imap.gmail.com")
            imap_port = gmail_config.get("imap_port", 993)
        else:
            # Use defaults when no config file is provided
            imap_server = "imap.gmail.com"
            imap_port = 993

        console.print(
            f"\n[yellow]Testing IMAP connection to {imap_server}:{imap_port}...[/yellow]"
        )

        # Create IMAP client and test connection
        gmail_client = ImapGmailClient(
            email_address=credentials.email_address,
            password=credentials.password,
            imap_server=imap_server,
            imap_port=imap_port,
        )

        # If we got here without exception, connection worked
        console.print("[green]✓ IMAP connection successful[/green]")

        # Clean up connection
        gmail_client.close()

    except Exception as e:
        console.print(f"[red]✗ IMAP connection failed: {e}[/red]")
        if verbose:
            console.print_exception()
        raise click.Abort() from e


@creds.command()
@click.argument("email")
def delete(email: str) -> None:
    """Delete credentials from keychain."""
    credential_manager = CredentialManager()
    if not credential_manager.delete_credentials(email):
        raise click.Abort()


@cli.command("test-claude")
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    help="Path to configuration file (default: platform-specific config directory)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def test_claude(config: Path | None, verbose: bool) -> None:
    """Test Claude CLI connection."""
    setup_logging(verbose)

    try:
        # Load configuration
        app_config = Config(str(config) if config else None)
        console.print(
            f"[green]✓[/green] Loaded configuration from {app_config.config_file}"
        )

        # Test Claude CLI connection
        summarizer = LLMSummarizer(app_config)
        console.print("\n[yellow]Testing Claude CLI connection...[/yellow]")
        if summarizer.test_cli_connection():
            console.print("[green]✓ Claude CLI is working correctly[/green]")
        else:
            console.print("[red]✗ Claude CLI test failed[/red]")
            raise click.Abort()

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise click.Abort() from None
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise click.Abort() from e


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(path_type=Path),
    help="Path to configuration file (default: platform-specific config directory)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output HTML file path (overrides config setting)",
)
@click.option(
    "--max-threads",
    "-n",
    type=int,
    help="Maximum threads per category (overrides config setting)",
)
@click.option(
    "--concurrency",
    "-j",
    type=click.IntRange(1, 20),
    help="Number of concurrent summarization tasks (overrides config setting, default: 5)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Process threads without generating summaries",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def run(
    config: Path | None,
    output: Path | None,
    max_threads: int | None,
    concurrency: int | None,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Generate AI-powered summaries of Gmail inbox threads.

    Process your Gmail inbox and create an HTML summary report with AI-generated
    thread summaries organized by categories.
    """
    setup_logging(verbose)

    try:
        # Load configuration
        app_config = Config(str(config) if config else None)
        console.print(
            f"[green]✓[/green] Loaded configuration from {app_config.config_file}"
        )

        # Override config settings if provided via CLI
        if max_threads and app_config.app_config:
            app_config.app_config.max_threads_per_category = max_threads
        if concurrency and app_config.app_config:
            app_config.app_config.claude.concurrency = concurrency

        # Initialize components
        gmail_client = None
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                # Gmail client
                task = progress.add_task("Connecting to Gmail via IMAP...", total=1)
                gmail_config = app_config.get_gmail_config()

                # Get credentials from keychain or config
                credential_manager = CredentialManager()
                email_address = gmail_config.get("email_address")

                # Try keychain first, fall back to config for backward compatibility
                credentials: GmailCredentials | tuple[str, str] | None = None
                if email_address:
                    credentials = credential_manager.get_credentials(email_address)

                if not credentials:
                    # Fall back to config file credentials (legacy)
                    config_email = gmail_config.get("email_address")
                    config_password = gmail_config.get("password")

                    if config_email and config_password:
                        console.print(
                            "[yellow]Warning: Using credentials from config file[/yellow]"
                        )
                        console.print(
                            "[yellow]Consider storing them securely: gmail-summary creds store[/yellow]"
                        )
                        credentials = (config_email, config_password)  # type: ignore
                    else:
                        console.print("[red]Error: Gmail credentials not found[/red]")
                        console.print(
                            "Store credentials securely: [cyan]gmail-summary creds store[/cyan]"
                        )
                        console.print(
                            "Or set email_address in config and store password in keychain"
                        )
                        raise click.Abort()

                # Handle both credential sources
                if isinstance(credentials, tuple):
                    email_address, password = credentials
                else:
                    # credentials is a GmailCredentials object
                    assert isinstance(credentials, GmailCredentials)
                    email_address = credentials.email_address
                    password = credentials.password

                gmail_client = ImapGmailClient(
                    email_address=email_address,
                    password=password,
                    imap_server=gmail_config.get("imap_server", "imap.gmail.com"),
                    imap_port=gmail_config.get("imap_port", 993),
                )
                progress.advance(task)

                # Thread processor
                task = progress.add_task("Setting up thread processor...", total=1)
                processor = ThreadProcessor(app_config)
                progress.advance(task)

                # Cache manager
                task = progress.add_task("Initializing cache...", total=1)
                cache_manager = CacheManager()
                progress.advance(task)

                # LLM summarizer (skip if dry run)
                if not dry_run:
                    task = progress.add_task(
                        "Testing Claude CLI connection...", total=1
                    )
                    summarizer = LLMSummarizer(app_config)
                    if not summarizer.test_cli_connection():
                        console.print("[red]Error: Claude CLI not available[/red]")
                        raise click.Abort()
                    progress.advance(task)

                # HTML generator
                task = progress.add_task("Setting up HTML generator...", total=1)
                html_generator = HTMLGenerator(app_config)
                progress.advance(task)

            console.print("[green]✓ All components initialized successfully[/green]")

            # Fetch and process threads
            console.print("\n[yellow]Fetching Gmail threads...[/yellow]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                "•",
                "[cyan]{task.completed}[/cyan] threads fetched",
                "•",
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Fetching inbox threads", total=None)

                # Get threads data
                threads_data = []
                for thread in gmail_client.get_inbox_threads():
                    messages = gmail_client.get_thread_messages(thread)
                    threads_data.append((thread, messages))

                    # Update progress with current count
                    progress.update(
                        task,
                        completed=len(threads_data),
                        description="Fetching inbox threads",
                    )

                    # Stop if we have enough for testing
                    if len(threads_data) >= 100:  # Reasonable limit for testing
                        break

            console.print(f"[green]✓ Fetched {len(threads_data)} threads[/green]")

            # Process and categorize threads
            console.print("\n[yellow]Categorizing threads...[/yellow]")
            categorized_threads = processor.process_threads(threads_data)

            # Display categorization summary
            _display_categorization_summary(categorized_threads)

            if dry_run:
                console.print(
                    "\n[yellow]Dry run complete - skipping summarization[/yellow]"
                )
                return

            # Generate summaries
            console.print("\n[yellow]Generating AI summaries...[/yellow]")

            # Calculate total threads for progress tracking
            total_threads = sum(
                len(threads) for threads in categorized_threads.values()
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                MofNCompleteColumn(),
                "•",
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Generating summaries", total=total_threads)

                # Define progress callback for parallel processing
                def update_progress(completed: int, description: str) -> None:
                    progress.update(task, completed=completed, description=description)

                # Use parallel summarization
                summarized_threads = summarizer.summarize_threads_parallel(
                    categorized_threads, cache_manager, update_progress
                )

            # Generate statistics
            stats = summarizer.get_summarization_stats(summarized_threads)
            _display_summarization_stats(stats)

            # Generate HTML report
            console.print("\n[yellow]Generating HTML report...[/yellow]")
            output_path = output or app_config.get_output_filename()
            html_file = html_generator.generate_html_report(
                summarized_threads, stats, str(output_path)
            )

            # Success message
            console.print(
                Panel(
                    f"[green]✓ Gmail inbox summary generated successfully![/green]\n\n"
                    f"📧 Processed: {stats['total_threads']} threads\n"
                    f"✨ Summarized: {stats['successful_summaries']} threads\n"
                    f"📄 Report: {html_file}\n\n"
                    f"[dim]Open the HTML file in your browser to view the summary.[/dim]",
                    title="Summary Complete",
                    border_style="green",
                )
            )

            # Save cache and cleanup
            cache_manager.save()
            cache_manager.cleanup_old_entries(max_age_days=30)

        finally:
            # Ensure Gmail client connection is closed
            if gmail_client:
                gmail_client.close()

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise click.Abort() from None
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        raise click.Abort() from e


def _display_categorization_summary(categorized_threads: dict[str, list]) -> None:
    """Display categorization results in a table."""
    table = Table(title="Thread Categorization Summary")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Threads", justify="right", style="magenta")
    table.add_column("Important", justify="right", style="red")

    total_threads = 0
    total_important = 0

    for category_name, threads in categorized_threads.items():
        if threads:  # Only show categories with threads
            thread_count = len(threads)
            important_count = sum(
                1 for t in threads if t.get("has_important_sender", False)
            )

            table.add_row(
                category_name,
                str(thread_count),
                str(important_count) if important_count > 0 else "-",
            )

            total_threads += thread_count
            total_important += important_count

    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_threads}[/bold]",
        f"[bold]{total_important}[/bold]",
    )

    console.print(table)


def _display_summarization_stats(stats: dict) -> None:
    """Display summarization statistics."""
    table = Table(title="Summarization Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")

    table.add_row("Total Threads", str(stats["total_threads"]))
    table.add_row("Successful Summaries", str(stats["successful_summaries"]))
    table.add_row("Failed Summaries", str(stats["failed_summaries"]))
    table.add_row("Success Rate", f"{stats['success_rate']:.1%}")

    if stats["error_types"]:
        table.add_section()
        for error_type, count in stats["error_types"].items():
            table.add_row(f"Error: {error_type[:30]}...", str(count))

    console.print(table)


@cli.group()
def config() -> None:
    """Manage configuration files."""
    pass


@config.command()
@click.option("--email", "-e", help="Gmail email address to use in the configuration")
@click.option(
    "--output",
    "-o",
    type=click.Path(exists=False),
    help="Output file path (default: platform-specific config directory)",
)
@click.option(
    "--force", "-f", is_flag=True, help="Overwrite existing configuration file"
)
def generate(email: str | None, output: str | None, force: bool) -> None:
    """Generate a minimal configuration file with example content.

    Creates a sample configuration file with sensible defaults and example
    categories. You can customize the Gmail email address and output location.
    """
    output_path = Path(output) if output else get_default_config_path()

    # Check if file exists and not forced
    if output_path.exists() and not force:
        console.print(f"[red]Configuration file already exists at {output_path}[/red]")
        console.print(
            "[yellow]Use --force to overwrite or specify a different --output path[/yellow]"
        )
        raise click.Abort()

    # Get email address if not provided
    if not email:
        email = Prompt.ask(
            "[cyan]Gmail email address[/cyan]", default="your.email@gmail.com"
        )

    # Generate configuration content
    config_content = _generate_config_template(email)

    try:
        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write configuration file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        console.print(
            f"[green]✓ Configuration file created: {output_path.absolute()}[/green]"
        )
        console.print("\n[yellow]Next steps:[/yellow]")
        console.print(
            f"1. Store your Gmail credentials: [cyan]gmail-summary creds store --email {email}[/cyan]"
        )
        console.print(
            "2. Test Claude CLI connection: [cyan]gmail-summary test-claude[/cyan]"
        )
        console.print("3. Review and customize the configuration file")
        console.print("4. Run a test summary: [cyan]gmail-summary run --dry-run[/cyan]")

    except Exception as e:
        console.print(f"[red]Error creating configuration file: {e}[/red]")
        raise click.Abort() from e


def _generate_config_template(email: str) -> str:
    """Generate configuration file template with example content.

    Args:
        email: Gmail email address to use in the configuration

    Returns:
        Configuration file content as YAML string
    """
    template = f"""# Gmail Inbox Summary Configuration
# Improved configuration with better category matching rules based on actual email patterns

# Gmail IMAP Configuration
gmail:
  email_address: "{email}"
  # password is stored securely in keychain - run: gmail-summary creds store
  imap_server: "imap.gmail.com"
  imap_port: 993

# Claude Code CLI Configuration
claude:
  cli_path: "claude"
  timeout: 30

# Thread Categories - processed in order, first match wins
# Categories are now organized by Gmail labels only for simpler and more reliable categorization
categories:
  # Important/urgent emails - checked first for highest priority
  - name: "Important Messages"
    summary_prompt: "Summarize this important email, highlighting urgency and required actions."
    criteria:
      labels:
        - "is:important"  # Gmail's important label
        - "is:starred"    # Starred emails

  # Meeting invitations and calendar events
  - name: "Meeting Invitations"
    summary_prompt: "Summarize this meeting-related message concisely. For new invitations: include who invited me, meeting purpose, and time. For accept/decline responses: only mention the response unless a reason for declining was given."
    criteria:
      labels:
        - "meeting-invitation"  # Custom label for meeting invitations

  # Community discussions (Python, technical forums, etc.)
  - name: "Community"
    summary_prompt: "Summarize this community discussion, focusing on technical topics, questions, and community announcements."
    criteria:
      labels:
        - "List/python-discuss"  # Python mailing list discussions

  # Development notifications (GitHub, GitLab, etc.) - renamed from "Development" to "Code"
  - name: "Code"
    summary_prompt: "Summarize this development-related notification, focusing on code changes, PR status, issues, and deployments."
    criteria:
      labels:
        - "github"      # GitHub notifications
        - "github-*"    # GitHub project-specific labels (uses fnmatch pattern matching)
        - "gitlab"      # GitLab notifications
        - "gitlab-*"    # GitLab project-specific labels (uses fnmatch pattern matching)

  # JIRA tickets and issue tracking
  - name: "JIRA"
    summary_prompt: "Summarize this JIRA ticket notification, highlighting the current status of the ticket, any status changes, priority updates, and required actions."
    criteria:
      labels:
        - "jira"  # JIRA ticket notifications

  # Google Docs and collaboration notifications - new category
  - name: "Documents"
    summary_prompt: "Summarize this document notification, focusing on what changed and any required actions."
    criteria:
      labels:
        - "google-docs"  # Google Docs notifications

  # Everything else (catch-all category)
  - name: "General Email"
    summary_prompt: "Provide a brief, friendly summary of this email."
    criteria: {{}}  # Empty criteria = catch all remaining emails

# Highlight emails from important senders
important_senders:
  - "boss@company\\\\.com"
  - "ceo@company\\\\.com"
  - "alerts@monitoring\\\\.com"
  - "noreply@important-service\\\\.com"

# Output Configuration
output_file: "inbox_summary.html"
# max_threads_per_category: null  # null/None for unlimited (default), or set a number like 50
"""
    return template


# Cache management commands


@cache.command("status")
def cache_status() -> None:
    """Show cache status and statistics."""
    setup_logging()

    try:
        cache_manager = CacheManager()
        stats = cache_manager.get_cache_stats()

        console.print("\n[bold]Cache Status[/bold]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting")
        table.add_column("Value")

        table.add_row("Cache Directory", str(stats["cache_directory"]))
        table.add_row("Cached Threads", str(stats["cached_threads"]))
        table.add_row("Cached Summaries", str(stats["cached_summaries"]))

        # Convert bytes to human readable
        threads_size = stats["threads_cache_size_bytes"]
        summaries_size = stats["summaries_cache_size_bytes"]
        total_size = threads_size + summaries_size

        def format_bytes(bytes_val: int) -> str:
            if bytes_val < 1024:
                return f"{bytes_val} B"
            elif bytes_val < 1024 * 1024:
                return f"{bytes_val / 1024:.1f} KB"
            else:
                return f"{bytes_val / (1024 * 1024):.1f} MB"

        table.add_row("Threads Cache Size", format_bytes(threads_size))
        table.add_row("Summaries Cache Size", format_bytes(summaries_size))
        table.add_row("Total Cache Size", format_bytes(total_size))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error checking cache status: {e}[/red]")
        raise click.Abort() from e


@cache.command("clear")
@click.option("--force", "-f", is_flag=True, help="Clear cache without confirmation")
def cache_clear(force: bool) -> None:
    """Clear all cached data."""
    setup_logging()

    if not force:
        if not click.confirm("Are you sure you want to clear all cached data?"):
            console.print("[yellow]Cache clear cancelled[/yellow]")
            return

    try:
        cache_manager = CacheManager()
        stats_before = cache_manager.get_cache_stats()

        cache_manager.clear_cache()

        console.print(
            f"[green]✓ Cache cleared successfully[/green]\n"
            f"Removed {stats_before['cached_threads']} threads "
            f"and {stats_before['cached_summaries']} summaries"
        )

    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/red]")
        raise click.Abort() from e


@cache.command("cleanup")
@click.option(
    "--max-age",
    "-a",
    type=int,
    default=30,
    help="Maximum age in days for cache entries (default: 30)",
)
def cache_cleanup(max_age: int) -> None:
    """Remove old cache entries."""
    setup_logging()

    try:
        cache_manager = CacheManager()
        removed_count = cache_manager.cleanup_old_entries(max_age_days=max_age)

        if removed_count > 0:
            console.print(
                f"[green]✓ Removed {removed_count} old cache entries[/green]\n"
                f"Entries older than {max_age} days have been cleaned up"
            )
        else:
            console.print(
                f"[blue]No cache entries older than {max_age} days found[/blue]"
            )

    except Exception as e:
        console.print(f"[red]Error cleaning up cache: {e}[/red]")
        raise click.Abort() from e


if __name__ == "__main__":
    cli()
