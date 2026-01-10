"""Command-line interface for Gmail Inbox Summary."""

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TextColumn
from rich.prompt import Prompt
from rich.table import Table

from .config import Config
from .credential_manager import CredentialManager
from .html_generator import HTMLGenerator
from .imap_gmail_client import ImapGmailClient
from .llm_summarizer import LLMSummarizer
from .thread_processor import ThreadProcessor

console = Console()


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
    3. Configured categories in config.yaml
    """
    pass


@cli.group()
def creds() -> None:
    """Manage Gmail credentials in keychain."""
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
def check(email: str) -> None:
    """Check if credentials exist for an email address."""
    credential_manager = CredentialManager()
    credential_manager.check_credentials(email)


@creds.command()
@click.argument("email")
def delete(email: str) -> None:
    """Delete credentials from keychain."""
    credential_manager = CredentialManager()
    if not credential_manager.delete_credentials(email):
        raise click.Abort()


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="config.yaml",
    help="Path to configuration file (default: config.yaml)",
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
@click.option(
    "--test-claude",
    is_flag=True,
    help="Test Claude CLI connection and exit",
)
def run(
    config: Path,
    output: Path | None,
    max_threads: int | None,
    dry_run: bool,
    verbose: bool,
    test_claude: bool,
) -> None:
    """Generate AI-powered summaries of Gmail inbox threads.

    Process your Gmail inbox and create an HTML summary report with AI-generated
    thread summaries organized by categories.
    """
    setup_logging(verbose)

    try:
        # Load configuration
        app_config = Config(str(config))
        console.print(f"[green]✓[/green] Loaded configuration from {config}")

        # Override config settings if provided via CLI
        if max_threads:
            app_config.config["max_threads_per_category"] = max_threads

        # Test Claude CLI connection if requested
        if test_claude:
            summarizer = LLMSummarizer(app_config)
            console.print("\n[yellow]Testing Claude CLI connection...[/yellow]")
            if summarizer.test_cli_connection():
                console.print("[green]✓ Claude CLI is working correctly[/green]")
                return
            else:
                console.print("[red]✗ Claude CLI test failed[/red]")
                raise click.Abort()

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
                credentials = None
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
                        credentials = (config_email, config_password)
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
                console=console,
            ) as progress:
                task = progress.add_task("Fetching inbox threads...", total=None)

                # Get threads data
                threads_data = []
                for thread in gmail_client.get_inbox_threads():
                    messages = gmail_client.get_thread_messages(thread["id"])
                    threads_data.append((thread, messages))
                    progress.update(
                        task, description=f"Fetched {len(threads_data)} threads..."
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
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                total_threads = sum(
                    len(threads) for threads in categorized_threads.values()
                )
                task = progress.add_task("Generating summaries...", total=total_threads)

                summarized_threads = summarizer.summarize_threads_batch(
                    categorized_threads
                )
                progress.advance(task, advance=total_threads)

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


if __name__ == "__main__":
    cli()
