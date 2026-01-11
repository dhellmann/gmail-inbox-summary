"""Secure credential management using system keychain."""

import logging
from typing import NamedTuple

import keyring
from rich.console import Console
from rich.prompt import Prompt

logger = logging.getLogger(__name__)
console = Console()

# Keychain service name for this application
SERVICE_NAME = "gmail-inbox-summary"


class GmailCredentials(NamedTuple):
    """Gmail credentials container."""

    email_address: str
    password: str


class CredentialManager:
    """Manages secure storage and retrieval of Gmail credentials."""

    def __init__(self) -> None:
        """Initialize credential manager."""
        self.service_name = SERVICE_NAME

    def store_credentials(
        self, email_address: str, password: str, update_existing: bool = False
    ) -> bool:
        """Store Gmail credentials in keychain.

        Args:
            email_address: Gmail email address
            password: Gmail password or app-specific password
            update_existing: Whether to update existing credentials

        Returns:
            True if credentials were stored successfully
        """
        try:
            # Check if credentials already exist
            existing_password = keyring.get_password(self.service_name, email_address)
            if existing_password and not update_existing:
                console.print(
                    f"[yellow]Credentials for {email_address} already exist in keychain[/yellow]"
                )
                console.print("Use --update flag to update existing credentials")
                return False

            # Store credentials in keychain
            keyring.set_password(self.service_name, email_address, password)

            action = "Updated" if existing_password else "Stored"
            console.print(
                f"[green]✓ {action} credentials for {email_address} in keychain[/green]"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store credentials in keychain: {e}")
            console.print(f"[red]Error storing credentials: {e}[/red]")
            return False

    def get_credentials(self, email_address: str) -> GmailCredentials | None:
        """Retrieve Gmail credentials from keychain.

        Args:
            email_address: Gmail email address

        Returns:
            GmailCredentials if found, None otherwise
        """
        try:
            password = keyring.get_password(self.service_name, email_address)
            if password:
                logger.debug(f"Retrieved credentials for {email_address} from keychain")
                return GmailCredentials(email_address=email_address, password=password)
            else:
                logger.debug(f"No credentials found for {email_address} in keychain")
                return None

        except Exception as e:
            logger.error(f"Failed to retrieve credentials from keychain: {e}")
            return None

    def delete_credentials(self, email_address: str) -> bool:
        """Delete Gmail credentials from keychain.

        Args:
            email_address: Gmail email address

        Returns:
            True if credentials were deleted successfully
        """
        try:
            # Check if credentials exist
            existing_password = keyring.get_password(self.service_name, email_address)
            if not existing_password:
                console.print(
                    f"[yellow]No credentials found for {email_address} in keychain[/yellow]"
                )
                return False

            # Delete credentials
            keyring.delete_password(self.service_name, email_address)
            console.print(
                f"[green]✓ Deleted credentials for {email_address} from keychain[/green]"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to delete credentials from keychain: {e}")
            console.print(f"[red]Error deleting credentials: {e}[/red]")
            return False

    def list_stored_emails(self) -> list[str]:
        """List email addresses with stored credentials.

        Returns:
            List of email addresses with stored credentials
        """
        # Note: keyring doesn't provide a direct way to list all stored credentials
        # This is a limitation of most keychain systems for security reasons
        # Users will need to remember their email addresses or we could store
        # a list separately (but that reduces security)
        console.print(
            "[yellow]Note: Keychain systems don't support listing stored emails for security.[/yellow]"
        )
        console.print("Please provide the email address you want to check or manage.")
        return []

    def prompt_and_store_credentials(self, email_address: str | None = None) -> bool:
        """Interactive prompt to store credentials.

        Args:
            email_address: Pre-filled email address (optional)

        Returns:
            True if credentials were stored successfully
        """
        try:
            # Get email address
            if not email_address:
                email_address = Prompt.ask(
                    "[cyan]Gmail email address[/cyan]",
                    default="",
                )

            if not email_address:
                console.print("[red]Email address is required[/red]")
                return False

            # Get password
            console.print("\n[cyan]Gmail password or app-specific password:[/cyan]")
            console.print(
                "[dim]App-specific passwords are recommended for better security[/dim]"
            )
            console.print(
                "[dim]Create one at: https://myaccount.google.com/apppasswords[/dim]"
            )

            password = Prompt.ask(
                "[cyan]Password[/cyan]",
                password=True,  # Hide password input
            )

            if not password:
                console.print("[red]Password is required[/red]")
                return False

            # Check if updating existing credentials
            existing = self.get_credentials(email_address)
            update_existing = existing is not None

            if update_existing:
                console.print(
                    f"[yellow]Found existing credentials for {email_address}[/yellow]"
                )
                update = Prompt.ask(
                    "Update existing credentials?", choices=["y", "n"], default="y"
                )
                if update.lower() != "y":
                    console.print("[yellow]Operation cancelled[/yellow]")
                    return False

            # Store credentials
            return self.store_credentials(email_address, password, update_existing)

        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow]")
            return False
        except Exception as e:
            logger.error(f"Error in interactive credential storage: {e}")
            console.print(f"[red]Error: {e}[/red]")
            return False

    def check_credentials(self, email_address: str) -> bool:
        """Check if credentials exist for an email address.

        Args:
            email_address: Gmail email address

        Returns:
            True if credentials exist
        """
        credentials = self.get_credentials(email_address)
        if credentials:
            console.print(
                f"[green]✓ Credentials found for {email_address} in keychain[/green]"
            )
            return True
        else:
            console.print(
                f"[red]✗ No credentials found for {email_address} in keychain[/red]"
            )
            return False

    def get_or_prompt_credentials(self, email_address: str) -> GmailCredentials | None:
        """Get credentials from keychain or prompt user to enter them.

        Args:
            email_address: Gmail email address

        Returns:
            GmailCredentials if available or entered successfully
        """
        # First try to get from keychain
        credentials = self.get_credentials(email_address)
        if credentials:
            return credentials

        # If not found, offer to store them
        console.print(
            f"[yellow]No credentials found for {email_address} in keychain[/yellow]"
        )
        console.print("Would you like to store your credentials securely?")

        store = Prompt.ask(
            "Store credentials in keychain?", choices=["y", "n"], default="y"
        )

        if store.lower() == "y":
            success = self.prompt_and_store_credentials(email_address)
            if success:
                return self.get_credentials(email_address)

        # If user chose not to store, prompt for password this time only
        console.print("\n[cyan]Enter password for this session only:[/cyan]")
        console.print("[dim](Credentials will not be saved)[/dim]")

        password = Prompt.ask("[cyan]Password[/cyan]", password=True)
        if password:
            return GmailCredentials(email_address=email_address, password=password)

        return None
