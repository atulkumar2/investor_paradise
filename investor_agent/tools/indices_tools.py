"""NSE Indices and Classification Utilities

This module handles:
- Loading and caching NSE index constituent data
- Sectoral index mappings
- Market cap classification (Large/Mid/Small)
- Sector mapping from CSV
"""

import os
from pathlib import Path

import pandas as pd

from investor_agent.logger import get_logger

logger = get_logger(__name__)

# Cache file paths
_CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
_INDICES_CACHE_FILE = _CACHE_DIR / "nse_indices_cache.parquet"
_SECTOR_CACHE_FILE = _CACHE_DIR / "nse_sector_cache.parquet"

# In-memory caches
_SECTOR_MAP: dict[str, str] | None = None
_INDICES_DATA: dict[str, pd.DataFrame] | None = None
_MARKET_CAP_MAP: dict[str, str] | None = None


def _should_use_sector_cache() -> bool:
    """Check if sector cache exists and is newer than source CSV."""
    if not _SECTOR_CACHE_FILE.exists():
        return False

    sector_file = Path(__file__).parent.parent / "sector_mapping.csv"

    # If CSV source doesn't exist, use cache (distributed cache scenario)
    if not sector_file.exists():
        return True

    cache_mtime = os.path.getmtime(_SECTOR_CACHE_FILE)
    csv_mtime = os.path.getmtime(sector_file)

    if csv_mtime > cache_mtime:
        logger.info("Sector cache stale: CSV is newer")
        return False

    return True


def _save_sector_cache(sector_map: dict[str, str]) -> None:
    """Save sector mapping to parquet cache with validation."""
    if not sector_map:
        logger.warning("Cannot save empty sector map to cache")
        return

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Create DataFrame and normalize data
        df = pd.DataFrame(list(sector_map.items()), columns=['SYMBOL', 'SECTOR'])

        # Strip whitespace from both columns
        df['SYMBOL'] = df['SYMBOL'].str.strip()
        df['SECTOR'] = df['SECTOR'].str.strip()

        # Remove any empty entries
        df = df[df['SYMBOL'].str.len() > 0]
        df = df[df['SECTOR'].str.len() > 0]

        # Sort for consistency
        df = df.sort_values('SYMBOL').reset_index(drop=True)

        # Save to parquet
        df.to_parquet(_SECTOR_CACHE_FILE, index=False)

        logger.info(
            "💾 Saved sector cache: %d entries to %s",
            len(df), _SECTOR_CACHE_FILE
        )
    except Exception as e:
        logger.error("Failed to save sector cache: %s", e)


def _load_sector_map() -> dict[str, str]:
    """
    Load sector mapping from parquet cache or CSV file.
    Cached after first load for performance.
    """
    global _SECTOR_MAP
    if _SECTOR_MAP is not None:
        return _SECTOR_MAP

    # Try loading from parquet cache first
    if _should_use_sector_cache():
        try:
            logger.info("📦 Loading sector mapping from cache...")
            df = pd.read_parquet(_SECTOR_CACHE_FILE)
            _SECTOR_MAP = dict(zip(df['SYMBOL'], df['SECTOR']))
            logger.info("✅ Loaded %d sector mappings from cache", len(_SECTOR_MAP))
            return _SECTOR_MAP
        except Exception as e:
            logger.warning("Failed to load sector cache: %s", e)

    # Load from CSV (only if cache doesn't exist or is invalid)
    sector_file = Path(__file__).parent.parent / "sector_mapping.csv"
    if not sector_file.exists():
        logger.error(
            "Neither sector cache nor CSV file exists. "
            "Cache: %s, CSV: %s",
            _SECTOR_CACHE_FILE, sector_file
        )
        _SECTOR_MAP = {}
        return _SECTOR_MAP

    try:
        logger.info("📂 Loading sector mapping from CSV...")
        df = pd.read_csv(sector_file)
        _SECTOR_MAP = dict(zip(df['SYMBOL'], df['SECTOR']))
        logger.info("✅ Loaded %d sector mappings from CSV", len(_SECTOR_MAP))
        return _SECTOR_MAP
    except (FileNotFoundError, pd.errors.EmptyDataError,
            pd.errors.ParserError, PermissionError):
        logger.exception("Failed to load sector mapping from %s", sector_file)
        # Return empty dict as fallback
        _SECTOR_MAP = {}
        return _SECTOR_MAP


def _should_use_indices_cache() -> bool:
    """Check if indices cache exists and is newer than source CSV files."""
    if not _INDICES_CACHE_FILE.exists():
        return False

    indices_dir = Path(__file__).parent.parent / "data" / "NSE_indices_list"

    # If CSV source directory doesn't exist, use cache (distributed cache scenario)
    if not indices_dir.exists():
        return True

    cache_mtime = os.path.getmtime(_INDICES_CACHE_FILE)

    # Check all CSV files in latest date folder
    date_folders = sorted([d for d in indices_dir.iterdir() if d.is_dir()], reverse=True)
    if not date_folders:
        # No CSV folders, use cache
        return True

    latest_folder = date_folders[0]
    csv_files = list(latest_folder.glob("*.csv"))
    if not csv_files:
        # No CSV files, use cache
        return True

    for csv_file in csv_files:
        if os.path.getmtime(csv_file) > cache_mtime:
            logger.info("Indices cache stale: %s is newer", csv_file.name)
            return False

    return True


def _save_indices_cache(indices_data: dict[str, pd.DataFrame]) -> None:
    """Save indices data to parquet cache."""
    if not indices_data:
        return

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Combine all indices into single DataFrame with index_name column
        frames = []
        for index_name, df in indices_data.items():
            df_copy = df.copy()
            df_copy['INDEX_NAME'] = index_name
            frames.append(df_copy)

        combined_df = pd.concat(frames, ignore_index=True)
        combined_df.to_parquet(_INDICES_CACHE_FILE, index=False)
        logger.info("💾 Saved indices cache to %s", _INDICES_CACHE_FILE)
    except Exception as e:
        logger.error("Failed to save indices cache: %s", e)


def _load_indices_data() -> dict[str, pd.DataFrame]:
    """
    Load NSE index constituent lists from parquet cache or CSV files.
    Uses latest available data folder. Cached after first load.
    """
    global _INDICES_DATA
    if _INDICES_DATA is not None:
        return _INDICES_DATA

    # Try loading from parquet cache first
    if _should_use_indices_cache():
        try:
            logger.info("📦 Loading indices data from cache...")
            combined_df = pd.read_parquet(_INDICES_CACHE_FILE)

            # Split back into individual index DataFrames
            _INDICES_DATA = {}
            for index_name, group in combined_df.groupby('INDEX_NAME'):
                # Remove INDEX_NAME column and keep original data
                df = group.drop(columns=['INDEX_NAME']).reset_index(drop=True)
                _INDICES_DATA[index_name] = df

            logger.info(
                "✅ Loaded %d indices from cache: %s",
                len(_INDICES_DATA),
                ", ".join(_INDICES_DATA.keys()),
            )
            return _INDICES_DATA
        except Exception as e:
            logger.warning("Failed to load indices cache: %s, loading from CSV", e)

    # Load from CSV files
    indices_dir = Path(__file__).parent.parent / "data" / "NSE_indices_list"

    try:
        # Find latest dated folder
        date_folders = sorted([d for d in indices_dir.iterdir() if d.is_dir()],
                              reverse=True)
        if not date_folders:
            logger.warning("No index data folders found in %s", indices_dir)
            _INDICES_DATA = {}
            return _INDICES_DATA

        latest_folder = date_folders[0]
        logger.info("📂 Loading index data from %s", latest_folder)

        _INDICES_DATA = {}
        for csv_file in latest_folder.glob("*.csv"):
            # Extract index name from filename (e.g., ind_nifty50list.csv -> NIFTY50)
            index_name = csv_file.stem.replace("ind_", "").replace(
              "list", "").replace("_", "").upper()
            try:
                df = pd.read_csv(csv_file)
                # Standardize column names
                if 'Symbol' in df.columns:
                    df.rename(columns={'Symbol': 'SYMBOL'}, inplace=True)
                _INDICES_DATA[index_name] = df
            except Exception as e:
                logger.warning("Failed to load %s: %s", csv_file.name, e)
                continue

        logger.info(
            "✅ Loaded %d indices: %s",
            len(_INDICES_DATA),
            ", ".join(_INDICES_DATA.keys()),
        )

        # Save to cache for next time
        _save_indices_cache(_INDICES_DATA)

        return _INDICES_DATA

    except Exception as e:
        logger.exception("Failed to load indices data: %s", e)
        _INDICES_DATA = {}
        return _INDICES_DATA


def get_index_constituents(index_name: str) -> list[str]:
    """
    Get list of stock symbols in a given NSE index.

    Args:
        index_name: Index name (e.g., "NIFTY50", "NIFTY100", "NIFTYBANK")

    Returns:
        List of stock symbols in the index

    Example:
        >>> get_index_constituents("NIFTY50")
        ['RELIANCE', 'TCS', 'HDFCBANK', ...]
    """
    indices_data = _load_indices_data()
    index_key = index_name.upper().replace(" ", "").replace("-", "").replace("_", "")

    if index_key not in indices_data:
        # Try common variations
        variations = [
            index_key,
            f"NIFTY{index_key}",
            index_key.replace("NIFTY", ""),
        ]
        for var in variations:
            if var in indices_data:
                index_key = var
                break
        else:
            logger.warning("Index '%s' not found. Available: %s",
                           index_name, list(indices_data.keys()))
            return []

    df = indices_data[index_key]
    if 'SYMBOL' in df.columns:
        return df['SYMBOL'].tolist()
    return []


def list_available_indices() -> dict[str, int]:
    """
    List all available NSE indices and their constituent counts.

    Returns:
        Dictionary mapping index name to number of constituents

    Example:
        >>> list_available_indices()
        {'NIFTY50': 50, 'NIFTY100': 100, 'NIFTYBANK': 12, ...}
    """
    indices_data = _load_indices_data()
    return {name: len(df) for name, df in indices_data.items()}


def get_sectoral_indices() -> dict[str, str]:
    """
    Get mapping of sectors to their NSE sectoral index names.

    Note: Only sectors with dedicated NSE indices are mapped here.
    Other sectors (like Construction Materials, Textiles, etc.) are supported
    through CSV-based sector_mapping and will work with get_sector_stocks().

    Returns:
        Dictionary mapping sector category to index name

    Example:
        >>> get_sectoral_indices()
        {'Banking': 'NIFTYBANK', 'IT': 'NIFTYIT', 'Auto': 'NIFTYAUTO', ...}
    """
    return {
        # Banking & Financial
        'Banking': 'NIFTYBANK',
        'Financial Services': 'NIFTYFINANCE',
        'Private Banks': 'NIFTYPRIVATEBANK',
        'PSU Banks': 'NIFTYPSUBANK',

        # Technology
        'IT': 'NIFTYIT',

        # Auto & Manufacturing
        'Automobile': 'NIFTYAUTO',
        'Auto': 'NIFTYAUTO',

        # Pharma & Healthcare
        'Pharma': 'NIFTYPHARMA',
        'Healthcare': 'NIFTYHEALTHCARE',

        # Consumer
        'FMCG': 'NIFTYFMCG',
        'Consumer Durables': 'NIFTYCONSUMERDURABLES',

        # Infrastructure & Materials
        'Metals & Mining': 'NIFTYMETAL',
        'Metals': 'NIFTYMETAL',

        # Energy & Oil
        'Energy': 'NIFTYOILGAS',
        'Oil Gas & Consumable Fuels': 'NIFTYOILGAS',
        'Oil & Gas': 'NIFTYOILGAS',

        # Media & Telecom
        'Media': 'NIFTYMEDIA',
        'Telecom': 'NIFTYIT',  # Telecom often grouped with IT in NSE indices

        # Realty & Construction
        'Realty': 'NIFTYREALTY',

        # Chemicals
        'Chemicals': 'NIFTYCHEMICALS',

        # Note: The following sectors don't have dedicated NSE indices
        # but are fully supported via CSV sector mapping:
        # - Construction Materials (includes Cement companies)
        # - Capital Goods
        # - Construction
        # - Textiles
        # - Services
        # - Consumer Services
        # - Consumer Goods
        # - Power
        # - Petrochemicals
        # - Forest Materials
        # - Fertilizers
        # - Biotechnology
        # - Auto Ancillary
        # - Agri
        # - Diversified
        # - Utilities
    }


def get_sector_from_index(sector: str) -> str | None:
    """
    Get the sectoral index name for a given sector.

    Args:
        sector: Sector name (e.g., 'Banking', 'IT', 'Auto')

    Returns:
        Index name if sector has a dedicated index, None otherwise

    Example:
        >>> get_sector_from_index('Banking')
        'NIFTYBANK'
    """
    sectoral_map = get_sectoral_indices()
    return sectoral_map.get(sector)


def get_stocks_by_sector_index(sector: str) -> list[str]:
    """
    Get stock symbols from a sector's NSE sectoral index.
    This provides authoritative sector classification from NSE.

    Args:
        sector: Sector name (e.g., 'Banking', 'IT', 'Auto', 'Pharma')

    Returns:
        List of stock symbols in the sectoral index

    Example:
        >>> get_stocks_by_sector_index('Banking')
        ['HDFCBANK', 'ICICIBANK', 'AXISBANK', ...]
    """
    index_name = get_sector_from_index(sector)
    if not index_name:
        logger.warning("No sectoral index found for '%s'", sector)
        return []

    return get_index_constituents(index_name)


def _build_market_cap_map() -> dict[str, str]:
    """
    Build market cap classification map based on NSE indices.
    Large Cap: NIFTY50, NIFTY100 (excluding midcap/smallcap indices)
    Mid Cap: NIFTYMIDCAP indices
    Small Cap: NIFTYSMALLCAP indices
    """
    global _MARKET_CAP_MAP
    if _MARKET_CAP_MAP is not None:
        return _MARKET_CAP_MAP

    indices_data = _load_indices_data()
    _MARKET_CAP_MAP = {}

    # Large cap: Nifty 50 and Nifty Next 50
    for idx in ['NIFTY50', 'NIFTYNEXT50']:
        if idx in indices_data:
            for symbol in indices_data[idx]['SYMBOL'].tolist():
                _MARKET_CAP_MAP[symbol] = 'LARGE'

    # Mid cap: All midcap indices
    for idx in ['NIFTYMIDCAP50', 'NIFTYMIDCAP100',
                'NIFTYMIDCAP150', 'NIFTYMIDCAPSELECT']:
        if idx in indices_data:
            for symbol in indices_data[idx]['SYMBOL'].tolist():
                if symbol not in _MARKET_CAP_MAP:  # Don't override large cap
                    _MARKET_CAP_MAP[symbol] = 'MID'

    # Small cap: All smallcap indices
    for idx in ['NIFTYSMALLCAP50', 'NIFTYSMALLCAP100',
                'NIFTYSMALLCAP250', 'NIFTYMICROCAP250']:
        if idx in indices_data:
            for symbol in indices_data[idx]['SYMBOL'].tolist():
                if symbol not in _MARKET_CAP_MAP:  # Don't override large/mid cap
                    _MARKET_CAP_MAP[symbol] = 'SMALL'

    logger.info(
        "Built market cap map: %d large, %d mid, %d small cap stocks",
        sum(1 for v in _MARKET_CAP_MAP.values() if v == 'LARGE'),
        sum(1 for v in _MARKET_CAP_MAP.values() if v == 'MID'),
        sum(1 for v in _MARKET_CAP_MAP.values() if v == 'SMALL')
    )
    return _MARKET_CAP_MAP


def get_stocks_by_market_cap(market_cap: str) -> list[str]:
    """
    Get list of stocks by market cap category.

    Args:
        market_cap: Category - "LARGE", "MID", or "SMALL"

    Returns:
        List of stock symbols in the category

    Example:
        >>> get_stocks_by_market_cap("SMALL")
        ['SYMBOL1', 'SYMBOL2', ...]
    """
    cap_map = _build_market_cap_map()
    cap_upper = market_cap.upper()

    if cap_upper not in ['LARGE', 'MID', 'SMALL']:
        logger.warning("Invalid market cap '%s'. Use LARGE, MID, or SMALL", market_cap)
        return []

    return [symbol for symbol, cap in cap_map.items() if cap == cap_upper]


def get_market_cap_category(symbol: str) -> str | None:
    """
    Get market cap category for a stock symbol.

    Args:
        symbol: Stock symbol

    Returns:
        "LARGE", "MID", "SMALL", or None if not classified
    """
    cap_map = _build_market_cap_map()
    return cap_map.get(symbol.upper())


def get_sector_stocks(sector: str) -> list[str]:
    """
    Get list of stock symbols belonging to a sector (using CSV mapping).
    Case-insensitive sector matching.

    Args:
        sector: Sector name (e.g., 'Banking', 'IT', 'Auto', 'FMCG')

    Returns:
        List of stock symbols in the sector
    """
    sector_map = _load_sector_map()

    # Case-insensitive matching
    sector_lower = sector.lower()

    # First try exact match (case-insensitive)
    for sym, sec in sector_map.items():
        if sec.lower() == sector_lower:
            # Found exact match, now get all stocks with this sector (using original case from map)
            target_sector = sec
            return [s for s, sect in sector_map.items() if sect == target_sector]

    # No match found
    return []


def get_stocks_by_sector_and_cap(sector: str, market_cap: str) -> list[str]:
    """
    Get list of stock symbols filtered by both sector AND market cap.

    Args:
        sector: Sector name (e.g., 'Banking', 'IT', 'Automobile', 'Pharma')
        market_cap: Market cap category - "LARGE", "MID", or "SMALL"

    Returns:
        List of stock symbols matching both criteria

    Example:
        >>> get_stocks_by_sector_and_cap('Automobile', 'LARGE')
        ['MARUTI', 'TATAMOTORS', 'M&M', ...]
    """
    # Get all stocks in the sector
    sector_stocks = get_sector_stocks(sector)

    # Get market cap classification
    cap_map = _build_market_cap_map()
    cap_upper = market_cap.upper()

    if cap_upper not in ['LARGE', 'MID', 'SMALL']:
        logger.warning(
            "Invalid market cap '%s'. Use LARGE, MID, or SMALL",
            market_cap
        )
        return []

    # Filter sector stocks by market cap
    filtered = [
        symbol for symbol in sector_stocks
        if cap_map.get(symbol) == cap_upper
    ]

    logger.info(
        "Found %d %s cap stocks in %s sector (out of %d total in sector)",
        len(filtered), cap_upper, sector, len(sector_stocks)
    )

    return filtered
