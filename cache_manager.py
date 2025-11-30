"""Cache management utilities for downloading and refreshing NSE data caches."""

from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from investor_agent.logger import get_logger

logger = get_logger(__name__)
console = Console()

# GitHub release URLs for cache files
CACHE_FILES = {
    "combined_data.parquet": "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/combined_data.parquet",
    "nse_indices_cache.parquet": "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_indices_cache.parquet",
    "nse_sector_cache.parquet": "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_sector_cache.parquet",
    "nse_symbol_company_mapping.parquet": "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_symbol_company_mapping.parquet",
}


def check_cache_exists(cache_dir: Optional[Path] = None) -> bool:
    """Check if all required cache files exist.

    Args:
        cache_dir: Optional cache directory path (defaults to investor_agent/data/cache)

    Returns:
        True if all cache files exist, False otherwise
    """
    if cache_dir is None:
        cache_dir = Path("investor_agent/data/cache")

    if not cache_dir.exists():
        return False

    for filename in CACHE_FILES.keys():
        file_path = cache_dir / filename
        if not file_path.exists():
            logger.debug("Missing cache file: %s", filename)
            return False

    return True


def download_file_with_progress(url: str, dest_path: Path) -> bool:
    """Download a file from URL with progress bar.

    Args:
        url: URL to download from
        dest_path: Destination file path

    Returns:
        True if download successful, False otherwise
    """
    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))

            with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Downloading {dest_path.name}", total=total
                )

                with open(dest_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

        logger.info("Successfully downloaded: %s", dest_path.name)
        return True

    except Exception as e:
        logger.error("Failed to download %s: %s", dest_path.name, e)
        console.print(f"[red]❌ Failed to download {dest_path.name}: {e}[/red]")
        return False


def download_cache_files(
    cache_dir: Optional[Path] = None, force: bool = False
) -> bool:
    """Download all required cache files from GitHub releases.

    Args:
        cache_dir: Optional cache directory path (defaults to investor_agent/data/cache)
        force: If True, re-download even if files exist

    Returns:
        True if all downloads successful, False otherwise
    """
    if cache_dir is None:
        cache_dir = Path("investor_agent/data/cache")

    # Create cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Check if cache already exists and we're not forcing refresh
    if not force and check_cache_exists(cache_dir):
        console.print("[green]✅ All cache files already exist[/green]")
        logger.info("Cache files already exist, skipping download")
        return True

    console.print("\n[bold cyan]📦 Downloading NSE data cache files...[/bold cyan]")
    logger.info("Starting cache file downloads")

    success = True
    for filename, url in CACHE_FILES.items():
        dest_path = cache_dir / filename

        # Skip if file exists and we're not forcing refresh
        if not force and dest_path.exists():
            console.print(f"[dim]⏭️  Skipping {filename} (already exists)[/dim]")
            continue

        console.print(f"\n[cyan]📥 Downloading {filename}...[/cyan]")
        if not download_file_with_progress(url, dest_path):
            success = False
            break

    if success:
        console.print("\n[bold green]✅ All cache files downloaded successfully![/bold green]")
        logger.info("All cache files downloaded successfully")
    else:
        console.print("\n[bold red]❌ Some cache files failed to download[/bold red]")
        logger.error("Cache download failed")

    return success


def refresh_cache(cache_dir: Optional[Path] = None) -> bool:
    """Force refresh all cache files by re-downloading.

    Args:
        cache_dir: Optional cache directory path (defaults to investor_agent/data/cache)

    Returns:
        True if refresh successful, False otherwise
    """
    console.print("[yellow]🔄 Refreshing cache files...[/yellow]")
    logger.info("Forcing cache refresh")
    return download_cache_files(cache_dir=cache_dir, force=True)


def ensure_cache_available(cache_dir: Optional[Path] = None) -> bool:
    """Ensure cache files are available, downloading if necessary.

    This is the main function to call at startup to ensure data is ready.

    Args:
        cache_dir: Optional cache directory path (defaults to investor_agent/data/cache)

    Returns:
        True if cache is available (either already existed or successfully downloaded)
    """
    if check_cache_exists(cache_dir):
        return True

    console.print(
        "[yellow]⚠️  Cache files not found. Downloading from GitHub...[/yellow]"
    )
    return download_cache_files(cache_dir=cache_dir)
