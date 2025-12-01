"""Cache management utilities for downloading and refreshing NSE data caches."""

import zipfile
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

# Default cache directory (relative to investor_agent package)
def _get_default_cache_dir() -> Path:
    """Get the default cache directory path relative to the investor_agent package."""
    investor_agent_dir = Path(__file__).parent / "investor_agent"
    return investor_agent_dir / "data" / "cache"

def _get_default_vector_dir() -> Path:
    """Get the default vector data directory path relative to the investor_agent package."""
    investor_agent_dir = Path(__file__).parent / "investor_agent"
    return investor_agent_dir / "data" / "vector-data"

# GitHub release URLs for cache files
CACHE_FILES = {
    "combined_data.parquet": "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/combined_data.parquet",
    "nse_indices_cache.parquet": "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_indices_cache.parquet",
    "nse_sector_cache.parquet": "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_sector_cache.parquet",
    "nse_symbol_company_mapping.parquet": "https://github.com/atulkumar2/investor_agent_data/releases/download/nsedata_parquet_20251128/nse_symbol_company_mapping.parquet",
}

# GitHub release URLs for vector data files (zip archives)
VECTOR_DATA = {
    "https://github.com/atulkumar2/investoragentdata_news1/releases/download/newsdata_202506_202508/202506.zip",
    "https://github.com/atulkumar2/investoragentdata_news1/releases/download/newsdata_202506_202508/202507.zip",
    "https://github.com/atulkumar2/investoragentdata_news1/releases/download/newsdata_202506_202508/202508.zip",
    "https://github.com/atulkumar2/investoragentdata_news1/releases/download/newsdata_202511/202509.zip",
    "https://github.com/atulkumar2/investoragentdata_news1/releases/download/newsdata_202511/202510.zip",
    "https://github.com/atulkumar2/investoragentdata_news1/releases/download/newsdata_202511/202511.zip",
}


def check_cache_exists(cache_dir: Optional[Path] = None) -> bool:
    """Check if all required cache files exist.

    Args:
        cache_dir: Optional cache directory path (defaults to investor_agent/data/cache)

    Returns:
        True if all cache files exist, False otherwise
    """
    if cache_dir is None:
        cache_dir = _get_default_cache_dir()

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


def unzip_file(zip_path: Path, extract_to: Path) -> bool:
    """Unzip a file to the specified directory.

    Args:
        zip_path: Path to the zip file
        extract_to: Directory to extract files to

    Returns:
        True if extraction successful, False otherwise
    """
    try:
        console.print(f"[cyan]📦 Extracting {zip_path.name}...[/cyan]")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        logger.info("Successfully extracted: %s", zip_path.name)
        # Remove the zip file after extraction
        zip_path.unlink()
        console.print(f"[green]✅ Extracted and cleaned up {zip_path.name}[/green]")
        return True
    except Exception as e:
        logger.error("Failed to extract %s: %s", zip_path.name, e)
        console.print(f"[red]❌ Failed to extract {zip_path.name}: {e}[/red]")
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
        cache_dir = _get_default_cache_dir()

    # Create cache directory if it doesn't exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Check if cache already exists and we're not forcing refresh
    if not force and check_cache_exists(cache_dir):
        console.print("[green]✅ All cache files already exist[/green]")
        logger.info("Cache files already exist, skipping download")
        return True

    console.print("\n[bold yellow]⚠️  Starting download of latest NSE market data cache (2019-2025)[/bold yellow]")
    console.print("[yellow]📊 This could take a minute (size ~50MB)[/yellow]")
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


def download_vector_data(vector_dir: Optional[Path] = None, force: bool = False) -> bool:
    """Download and extract vector data files from GitHub releases.

    Args:
        vector_dir: Optional vector data directory path (defaults to investor_agent/data/vector-data)
        force: If True, re-download even if files exist

    Returns:
        True if all downloads and extractions successful, False otherwise
    """
    if vector_dir is None:
        vector_dir = _get_default_vector_dir()

    # Create vector directory if it doesn't exist
    vector_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold yellow]⚠️  Starting download of Economic Times news articles (last 6 months)[/bold yellow]")
    console.print("[yellow]📰 This could take a few minutes (download ~580MB, disk space ~1.2GB after extraction)[/yellow]")
    logger.info("Starting vector data downloads")

    success = True
    for url in VECTOR_DATA:
        filename = url.split("/")[-1]  # Extract filename from URL (e.g., "202506.zip")
        folder_name = filename.replace(".zip", "")  # Folder name without .zip
        folder_path = vector_dir / folder_name
        zip_path = vector_dir / filename

        # Skip if folder already exists and we're not forcing refresh
        if not force and folder_path.exists():
            console.print(f"[dim]⏭️  Skipping {folder_name} (already exists)[/dim]")
            continue

        console.print(f"\n[cyan]📥 Downloading {filename}...[/cyan]")
        if not download_file_with_progress(url, zip_path):
            success = False
            break

        # Extract the zip file
        if not unzip_file(zip_path, vector_dir):
            success = False
            break

    if success:
        console.print("\n[bold green]✅ All vector data files downloaded and extracted successfully![/bold green]")
        logger.info("All vector data files processed successfully")
    else:
        console.print("\n[bold red]❌ Some vector data files failed to download or extract[/bold red]")
        logger.error("Vector data download/extraction failed")

    return success


def ensure_cache_available(cache_dir: Optional[Path] = None) -> bool:
    """Ensure cache files are available, downloading if necessary.

    This is the main function to call at startup to ensure data is ready.

    Args:
        cache_dir: Optional cache directory path (defaults to investor_agent/data/cache)

    Returns:
        True if cache is available (either already existed or successfully downloaded)
    """
    if check_cache_exists(cache_dir):
        console.print("[green]✅ Market data cache found[/green]")
        return True

    return download_cache_files(cache_dir=cache_dir)


def ensure_vector_data_available(vector_dir: Optional[Path] = None) -> bool:
    """Ensure vector data files are available, downloading if necessary.

    Args:
        vector_dir: Optional vector data directory path (defaults to investor_agent/data/vector-data)

    Returns:
        True if vector data is available (either already existed or successfully downloaded)
    """
    if vector_dir is None:
        vector_dir = _get_default_vector_dir()

    # Check if any vector data folders exist
    if vector_dir.exists() and any(vector_dir.iterdir()):
        console.print("[green]✅ News vector data found[/green]")
        logger.info("Vector data already exists, skipping download")
        return True

    return download_vector_data(vector_dir=vector_dir)
