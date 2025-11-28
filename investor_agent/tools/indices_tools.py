"""NSE Indices and Classification Utilities

This module handles:
- Loading and caching NSE index constituent data
- Sectoral index mappings
- Market cap classification (Large/Mid/Small)
- Sector mapping from CSV
"""

from pathlib import Path

import pandas as pd

from investor_agent.logger import get_logger

logger = get_logger(__name__)

# Load sector mapping from CSV
_SECTOR_MAP: dict[str, str] | None = None

# Load NSE indices constituents from CSV
_INDICES_DATA: dict[str, pd.DataFrame] | None = None

# Market cap classification cache
_MARKET_CAP_MAP: dict[str, str] | None = None


def _load_sector_map() -> dict[str, str]:
    """
    Load sector mapping from CSV file.
    Cached after first load for performance.
    """
    global _SECTOR_MAP
    if _SECTOR_MAP is not None:
        return _SECTOR_MAP

    sector_file = Path(__file__).parent.parent / "sector_mapping.csv"
    try:
        df = pd.read_csv(sector_file)
        _SECTOR_MAP = dict(zip(df['SYMBOL'], df['SECTOR']))
        logger.info("Loaded %d sector mappings from %s", len(_SECTOR_MAP), sector_file)
        return _SECTOR_MAP
    except (FileNotFoundError, pd.errors.EmptyDataError,
            pd.errors.ParserError, PermissionError):
        logger.exception("Failed to load sector mapping from %s", sector_file)
        # Return empty dict as fallback
        _SECTOR_MAP = {}
        return _SECTOR_MAP


def _load_indices_data() -> dict[str, pd.DataFrame]:
    """
    Load NSE index constituent lists from CSV files.
    Uses latest available data folder. Cached after first load.
    """
    global _INDICES_DATA
    if _INDICES_DATA is not None:
        return _INDICES_DATA

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
        logger.info("Loading index data from %s", latest_folder)

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

        logger.info("Loaded %d indices: %s", len(
          _INDICES_DATA), ", ".join(_INDICES_DATA.keys()))
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

    Returns:
        Dictionary mapping sector category to index name

    Example:
        >>> get_sectoral_indices()
        {'Banking': 'NIFTYBANK', 'IT': 'NIFTYIT', 'Auto': 'NIFTYAUTO', ...}
    """
    return {
        'Banking': 'NIFTYBANK',
        'IT': 'NIFTYIT',
        'Auto': 'NIFTYAUTO',
        'Pharma': 'NIFTYPHARMA',
        'FMCG': 'NIFTYFMCG',
        'Metals': 'NIFTYMETAL',
        'Energy': 'NIFTYOILGAS',
        'Oil & Gas': 'NIFTYOILGAS',
        'Healthcare': 'NIFTYHEALTHCARE',
        'Media': 'NIFTYMEDIA',
        'Realty': 'NIFTYREALTY',
        'Financial Services': 'NIFTYFINANCE',
        'Consumer Durables': 'NIFTYCONSUMERDURABLES',
        'Chemicals': 'NIFTYCHEMICALS',
        'Private Banks': 'NIFTYPRIVATEBANK',
        'PSU Banks': 'NIFTYPSUBANK',
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

    Args:
        sector: Sector name (e.g., 'Banking', 'IT', 'Auto')

    Returns:
        List of stock symbols in the sector
    """
    sector_map = _load_sector_map()
    return [sym for sym, sec in sector_map.items() if sec == sector]
