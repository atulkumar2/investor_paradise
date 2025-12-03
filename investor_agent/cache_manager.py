"""Cache management utilities for downloading and refreshing NSE data caches."""

import os
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

# Optional GCS support (for cloud deployments)
try:
    from google.cloud import storage
    _GCS_AVAILABLE = True
except ImportError:
    _GCS_AVAILABLE = False

logger = get_logger(__name__)
console = Console()

# Default cache directory (relative to investor_agent package)
def _get_default_cache_dir() -> Path:
    """Get the default cache directory path relative to the investor_agent package."""
    investor_agent_dir = Path(__file__).parent
    return investor_agent_dir / "data" / "cache"

def _get_default_vector_dir() -> Path:
    """Get the default vector data directory path relative to the investor_agent package."""
    investor_agent_dir = Path(__file__).parent
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


def check_vector_data_exists(vector_dir: Optional[Path] = None) -> bool:
    """Check if vector data exists.

    Args:
        vector_dir: Optional vector data directory path (defaults to investor_agent/data/vector-data)

    Returns:
        True if vector data exists, False otherwise
    """
    if vector_dir is None:
        vector_dir = _get_default_vector_dir()

    return vector_dir.exists() and any(vector_dir.iterdir())


def check_data_exists(cache_dir: Optional[Path] = None, vector_dir: Optional[Path] = None) -> bool:
    """Check if ALL required data exists (cache + vector data).

    This is an all-or-nothing check - both cache AND vector data must exist.

    Args:
        cache_dir: Optional cache directory path (defaults to investor_agent/data/cache)
        vector_dir: Optional vector data directory path (defaults to investor_agent/data/vector-data)

    Returns:
        True if BOTH cache and vector data exist, False if either is missing
    """
    cache_exists = check_cache_exists(cache_dir)
    vector_exists = check_vector_data_exists(vector_dir)

    if cache_exists and vector_exists:
        logger.info("Complete data found (cache + vector data)")
        return True

    if cache_exists and not vector_exists:
        logger.warning("Cache exists but vector data missing")
    elif vector_exists and not cache_exists:
        logger.warning("Vector data exists but cache missing")
    else:
        logger.info("No data found")

    return False


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


def download_all_data_from_github(
    cache_dir: Optional[Path] = None,
    vector_dir: Optional[Path] = None,
    clean_first: bool = True
) -> bool:
    """Download complete dataset from GitHub (cache + vector data).

    Args:
        cache_dir: Optional cache directory path
        vector_dir: Optional vector data directory path
        clean_first: If True, delete existing data folder before downloading

    Returns:
        True if all data downloaded successfully
    """
    import shutil

    if clean_first:
        # Delete entire data folder for clean download
        investor_agent_dir = Path(__file__).parent
        data_dir = investor_agent_dir / "data"
        if data_dir.exists():
            logger.info("Removing existing data directory for clean download...")
            shutil.rmtree(data_dir)

    logger.info("Downloading complete dataset from GitHub...")

    # Download cache files
    cache_success = download_cache_files(cache_dir=cache_dir)
    if not cache_success:
        logger.error("Failed to download cache from GitHub")
        return False

    # Download vector data
    vector_success = download_vector_data(vector_dir=vector_dir)
    if not vector_success:
        logger.warning("Failed to download vector data from GitHub (news search may be limited)")
        # Don't fail completely if vector data fails

    logger.info("Complete data download from GitHub finished")
    return True


# ============================================================================
# GCS Download Functions (for Cloud Deployment)
# ============================================================================

def download_from_gcs_bucket(
    bucket_name: str,
    source_prefix: str,
    destination_dir: Path,
    force: bool = False
) -> bool:
    """Download files from GCS bucket to local directory.

    Args:
        bucket_name: Name of the GCS bucket (e.g., "investor-paradise-data")
        source_prefix: Prefix/folder in bucket (e.g., "data/cache" or "data/vector-data")
        destination_dir: Local directory to download to
        force: If True, re-download even if files exist

    Returns:
        True if download successful, False otherwise
    """
    if not _GCS_AVAILABLE:
        logger.error("google-cloud-storage not available. Install with: pip install google-cloud-storage")
        console.print("[red]❌ google-cloud-storage package not installed[/red]")
        return False

    try:
        # Create destination directory
        destination_dir.mkdir(parents=True, exist_ok=True)

        # Initialize GCS client (uses Application Default Credentials in cloud)
        client = storage.Client()
        bucket = client.bucket(bucket_name)

        # List all blobs with the prefix
        blobs = list(bucket.list_blobs(prefix=source_prefix))

        if not blobs:
            logger.warning("No files found in GCS bucket %s with prefix %s", bucket_name, source_prefix)
            console.print(f"[yellow]⚠️  No files found in gs://{bucket_name}/{source_prefix}[/yellow]")
            return False

        console.print(f"\n[cyan]☁️  Downloading from GCS bucket: gs://{bucket_name}/{source_prefix}[/cyan]")
        logger.info("Downloading %d files from GCS", len(blobs))

        success_count = 0
        for blob in blobs:
            # Skip directory markers
            if blob.name.endswith('/'):
                continue

            # Calculate relative path and destination
            relative_path = blob.name.replace(source_prefix, "").lstrip('/')
            if not relative_path:  # Skip if empty (happens with prefix-only blobs)
                continue

            dest_file = destination_dir / relative_path

            # Skip if file exists and not forcing
            if not force and dest_file.exists():
                logger.debug("Skipping %s (already exists)", relative_path)
                continue

            # Create parent directories
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            console.print(f"[dim]  ⬇️  {relative_path} ({blob.size / 1024 / 1024:.1f} MB)[/dim]")
            blob.download_to_filename(str(dest_file))
            success_count += 1
            logger.debug("Downloaded: %s", relative_path)

        console.print(f"[green]✅ Downloaded {success_count} files from GCS[/green]")
        logger.info("Successfully downloaded %d files from GCS", success_count)
        return True

    except Exception as e:
        logger.error("Failed to download from GCS: %s", e)
        console.print(f"[red]❌ GCS download failed: {e}[/red]")
        return False


def ensure_cache_from_gcs(
    bucket_name: str = "investor-paradise-data",
    cache_dir: Optional[Path] = None
) -> bool:
    """Ensure cache is available from GCS bucket (for cloud deployment).

    This is the main function to call in cloud environments where data is stored in GCS.
    Falls back to local cache if GCS download fails.

    Args:
        bucket_name: GCS bucket name
        cache_dir: Local cache directory (defaults to investor_agent/data/cache)

    Returns:
        True if cache is available
    """
    if cache_dir is None:
        cache_dir = _get_default_cache_dir()

    # Check if cache already exists locally
    if check_cache_exists(cache_dir):
        console.print("[green]✅ Cache found locally[/green]")
        logger.info("Using existing local cache")
        return True

    # Try downloading from GCS
    console.print("[yellow]📥 Cache not found locally, downloading from GCS...[/yellow]")
    return download_from_gcs_bucket(
        bucket_name=bucket_name,
        source_prefix="data/cache",
        destination_dir=cache_dir
    )


def ensure_vector_data_from_gcs(
    bucket_name: str = "investor-paradise-data",
    vector_dir: Optional[Path] = None
) -> bool:
    """Ensure vector data is available from GCS bucket (for cloud deployment).

    Args:
        bucket_name: GCS bucket name
        vector_dir: Local vector data directory (defaults to investor_agent/data/vector-data)

    Returns:
        True if vector data is available
    """
    if vector_dir is None:
        vector_dir = _get_default_vector_dir()

    # Check if vector data already exists locally
    if vector_dir.exists() and any(vector_dir.iterdir()):
        console.print("[green]✅ Vector data found locally[/green]")
        logger.info("Using existing local vector data")
        return True

    # Try downloading from GCS
    console.print("[yellow]📥 Vector data not found locally, downloading from GCS...[/yellow]")
    return download_from_gcs_bucket(
        bucket_name=bucket_name,
        source_prefix="data/vector-data",
        destination_dir=vector_dir
    )


def download_all_data_from_gcs(
    bucket_name: str = "investor-paradise-data",
    cache_dir: Optional[Path] = None,
    vector_dir: Optional[Path] = None,
    clean_first: bool = True
) -> bool:
    """Download complete dataset from GCS bucket (cache + vector data).

    Args:
        bucket_name: GCS bucket name
        cache_dir: Optional cache directory path
        vector_dir: Optional vector data directory path
        clean_first: If True, delete existing data folder before downloading

    Returns:
        True if all data downloaded successfully
    """
    import shutil

    if clean_first:
        # Delete entire data folder for clean download
        investor_agent_dir = Path(__file__).parent
        data_dir = investor_agent_dir / "data"
        if data_dir.exists():
            logger.info("Removing existing data directory for clean download...")
            shutil.rmtree(data_dir)

    logger.info("Downloading complete dataset from GCS bucket: %s", bucket_name)

    # Download cache files
    cache_success = ensure_cache_from_gcs(bucket_name=bucket_name, cache_dir=cache_dir)
    if not cache_success:
        logger.error("Failed to download cache from GCS")
        return False

    # Download vector data
    vector_success = ensure_vector_data_from_gcs(bucket_name=bucket_name, vector_dir=vector_dir)
    if not vector_success:
        logger.warning("Failed to download vector data from GCS (news search may be limited)")
        # Don't fail completely if vector data fails

    logger.info("Complete data download from GCS finished")
    return True

