"""
API Key Management Module
Handles secure storage and retrieval of Google API key with multiple fallback strategies.
"""

import os
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()

SERVICE_NAME = "investor-paradise-cli"
KEY_NAME = "google_api_key"


def get_or_prompt_api_key(force_reset: bool = False) -> str:
    """
    Get API key with priority: env var > keyring > config file > prompt.
    
    Args:
        force_reset: If True, ignore stored keys and prompt user
        
    Returns:
        Valid Google API key
        
    Raises:
        ValueError: If no API key is provided
    """
    # 1. Check environment variable first (highest priority, temporary override)
    env_key = os.getenv("GOOGLE_API_KEY")
    if env_key and not force_reset:
        return env_key
    
    # 2. Try system keyring (secure, persistent)
    if not force_reset:
        stored_key = _get_from_keyring()
        if stored_key:
            return stored_key
    
    # 3. Try config file fallback (for systems without keyring)
    if not force_reset:
        file_key = _get_from_config_file()
        if file_key:
            return file_key
    
    # 4. Prompt user for API key
    api_key = _prompt_for_api_key()
    
    # 5. Save for future use (keyring first, fallback to file)
    _save_api_key(api_key)
    
    return api_key


def reset_api_key() -> None:
    """Delete stored API key from all storage locations."""
    deleted_from = []
    
    # Try to delete from keyring
    if _delete_from_keyring():
        deleted_from.append("keyring")
    
    # Try to delete from config file
    if _delete_from_config_file():
        deleted_from.append("config file")
    
    if deleted_from:
        console.print(f"[green]✅ API key removed from {', '.join(deleted_from)}[/green]")
        console.print("[dim]You'll be prompted to enter it again on next run[/dim]")
    else:
        console.print("[yellow]ℹ️  No API key was stored[/yellow]")
        console.print("[dim]Set GOOGLE_API_KEY environment variable or run CLI to configure[/dim]")


def _get_from_keyring() -> Optional[str]:
    """Get API key from system keyring."""
    try:
        import keyring
        key = keyring.get_password(SERVICE_NAME, KEY_NAME)
        return key.strip() if key else None
    except ImportError:
        # keyring not installed, skip silently
        return None
    except Exception:
        # keyring not available on this system
        return None


def _get_from_config_file() -> Optional[str]:
    """Get API key from config file."""
    try:
        config_file = _get_config_file_path()
        if config_file.exists():
            from dotenv import dotenv_values
            config = dotenv_values(config_file)
            return config.get("GOOGLE_API_KEY")
    except Exception:
        pass
    return None


def _prompt_for_api_key() -> str:
    """Prompt user to enter their Google API key."""
    console.print("\n[yellow]⚠️  Google API Key not configured[/yellow]")
    console.print("[cyan]Get your free API key from: https://aistudio.google.com/apikey[/cyan]")
    console.print("[dim]Your key will be securely stored for future use[/dim]\n")
    
    from getpass import getpass
    api_key = console.print("[bold cyan]Enter your Google API Key:[/bold cyan] ", end="")
    api_key = getpass("").strip()
    # api_key = console.input("[bold cyan]Enter your Google API Key:[/bold cyan] ").strip()
    
    if not api_key:
        raise ValueError("API key is required to use Investor Paradise")
    
    return api_key


def _save_api_key(api_key: str) -> None:
    """Save API key to keyring or config file."""
    # Try keyring first (most secure)
    if _save_to_keyring(api_key):
        console.print("[green]✅ API key securely saved to system keyring[/green]")
        console.print("[dim]Run 'investor-paradise-cli --reset-api-key' to change it later[/dim]\n")
        return
    
    # Fallback to config file
    if _save_to_config_file(api_key):
        config_file = _get_config_file_path()
        console.print(f"[green]✅ API key saved to {config_file}[/green]")
        console.print("[dim]Run 'investor-paradise-cli --reset-api-key' to change it later[/dim]\n")
        return
    
    # If both fail, warn user
    console.print("[yellow]⚠️  Could not save API key for future use[/yellow]")
    console.print("[yellow]Set GOOGLE_API_KEY environment variable to persist it[/yellow]\n")


def _save_to_keyring(api_key: str) -> bool:
    """Save API key to system keyring. Returns True if successful."""
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, KEY_NAME, api_key.strip())
        return True
    except ImportError:
        return False
    except Exception:
        return False


def _save_to_config_file(api_key: str) -> bool:
    """Save API key to config file. Returns True if successful."""
    try:
        config_file = _get_config_file_path()
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, "w") as f:
            f.write("# Investor Paradise Configuration\n")
            f.write("# This file stores your Google API key\n")
            f.write("# Keep it private and do not commit to version control\n")
            f.write("# Location: ~/.investor-paradise/config.env\n\n")
            f.write(f"GOOGLE_API_KEY={api_key}\n")
        
        # Set restrictive permissions (owner read/write only)
        config_file.chmod(0o600)
        return True
    except Exception:
        return False


def _delete_from_keyring() -> bool:
    """Delete API key from keyring. Returns True if deleted."""
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, KEY_NAME)
        return True
    except ImportError:
        return False
    except Exception:
        return False


def _delete_from_config_file() -> bool:
    """Delete config file. Returns True if deleted."""
    try:
        config_file = _get_config_file_path()
        if config_file.exists():
            config_file.unlink()
            return True
    except Exception:
        pass
    return False


def _get_config_file_path() -> Path:
    """Get path to config file in user's home directory."""
    return Path.home() / ".investor-paradise" / "config.env"


def show_help() -> None:
    """Display CLI help information."""
    console.print("\n[bold cyan]Investor Paradise CLI - Help[/bold cyan]\n")
    console.print("[bold]Usage:[/bold]")
    console.print("  investor-paradise-cli                 Start the interactive CLI")
    console.print("  investor-paradise-cli --reset-api-key Reset your Google API key")
    console.print("  investor-paradise-cli --help          Show this help message")
    console.print("\n[bold]Commands (in CLI):[/bold]")
    console.print("  exit, quit, bye    Exit the CLI")
    console.print("  clear              Clear current session history")
    console.print("  switch             Switch to a different session")
    console.print("\n[bold]Environment Variables:[/bold]")
    console.print("  GOOGLE_API_KEY     Your Google Gemini API key (overrides stored key)")
    console.print("\n[bold]Examples:[/bold]")
    console.print("  investor-paradise-cli")
    console.print("  GOOGLE_API_KEY=your_key investor-paradise-cli")
    console.print("\n[bold]Get API Key:[/bold]")
    console.print("  https://aistudio.google.com/apikey")
    console.print("\n[bold]Documentation:[/bold]")
    console.print("  https://github.com/atulkumar2/investor_paradise\n")
