"""Semantic Search Tools for News Analysis

This module handles:
- Company name lookup from NSE symbols
- ChromaDB initialization and management
- Semantic search over ingested PDF news
- Date-range based collection loading
"""

import os
from pathlib import Path
from typing import cast
from types import SimpleNamespace

import pandas as pd

from investor_agent.logger import get_logger

logger = get_logger(__name__)

# Lazy-loaded resources for semantic search
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    from dateutil.relativedelta import relativedelta
    _SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    _SEMANTIC_SEARCH_AVAILABLE = False
    logger.warning("chromadb or sentence-transformers not installed - semantic_search will be unavailable")
    # Dummy relativedelta if dateutil not available
    class relativedelta:
        def __init__(self, **kwargs):
            pass

# State for semantic search resources (lazy initialization)
_search_state = SimpleNamespace(collections=[], model=None, initialized=False)

# Cache for symbol-to-name mapping
_SYMBOL_NAME_MAP = None


def get_company_name(symbol: str) -> dict:
    """
    Convert stock symbol to company name using NSE symbol-company mapping.
    
    Args:
        symbol: Stock ticker (e.g., 'RELIANCE', 'TCS', 'SVPGLOB')
    
    Returns:
        Dictionary with symbol, company_name, and whether mapping was found
        
    Example:
        >>> get_company_name('RELIANCE')
        {'symbol': 'RELIANCE', 'company_name': 'Reliance Industries Limited', 'found': True}
        
        >>> get_company_name('UNKNOWN')
        {'symbol': 'UNKNOWN', 'company_name': 'UNKNOWN', 'found': False}
    """
    global _SYMBOL_NAME_MAP
    
    # Load mapping on first call (lazy initialization)
    if _SYMBOL_NAME_MAP is None:
        csv_path = Path(__file__).parent.parent / "nse_symbol_company_mapping.csv"
        
        if not csv_path.exists():
            logger.warning("NSE symbol-company mapping not found at %s", csv_path)
            return {
                "symbol": symbol,
                "company_name": symbol,  # Fallback to symbol
                "found": False,
                "error": "nse_symbol_company_mapping.csv not found"
            }
        
        try:
            # Read CSV and create symbol->name mapping
            df = pd.read_csv(csv_path)
            # Strip whitespace from column names and values
            df.columns = df.columns.str.strip()
            _SYMBOL_NAME_MAP = dict(zip(
                df['SYMBOL'].str.strip().str.upper(),
                df['NAME OF COMPANY'].str.strip()
            ))
            logger.info("Loaded %d symbol-to-name mappings from NSE", len(_SYMBOL_NAME_MAP))
        except Exception as e:
            logger.error("Failed to load NSE symbol-company mapping: %s", e)
            return {
                "symbol": symbol,
                "company_name": symbol,
                "found": False,
                "error": str(e)
            }
    
    # Lookup symbol (case-insensitive)
    symbol_upper = symbol.strip().upper()
    company_name = _SYMBOL_NAME_MAP.get(symbol_upper)
    
    if company_name:
        return {
            "symbol": symbol,
            "company_name": company_name,
            "found": True
        }
    else:
        logger.warning("Symbol '%s' not found in NSE mapping", symbol)
        return {
            "symbol": symbol,
            "company_name": symbol,  # Fallback to symbol itself
            "found": False
        }


def get_monthly_dirs_for_date_range(
    start_date: str,
    end_date: str,
    base_dir: str = "./investor_agent/data/vector-data",
) -> list[str]:
    """Generate list of monthly directory paths for a date range.
    
    Only returns directories that actually exist on disk.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        base_dir: Base directory containing monthly subdirectories
        
    Returns:
        List of existing directory paths (e.g., ['./vector-data/202407', './vector-data/202408'])
        
    Example:
        >>> get_monthly_dirs_for_date_range('2024-07-15', '2024-09-20')
        ['./investor_agent/data/vector-data/202407', './investor_agent/data/vector-data/202408', './investor_agent/data/vector-data/202409']
    """
    from datetime import datetime
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        logger.warning("Invalid date format (%s to %s), using all available months", start_date, end_date)
        return []
    
    # Generate YYYYMM for each month in range
    monthly_dirs = []
    current = start.replace(day=1)  # Start from beginning of month
    end_month = end.replace(day=1)
    
    while current <= end_month:
        month_str = current.strftime("%Y%m")
        dir_path = f"{base_dir}/{month_str}"
        
        # Only include if directory exists
        if Path(dir_path).exists() and Path(dir_path).is_dir():
            monthly_dirs.append(dir_path)
        else:
            logger.debug("Skipping non-existent directory: %s", dir_path)
        
        current += relativedelta(months=1)
    
    if not monthly_dirs:
        logger.warning(
            "No existing directories found for date range %s to %s in %s",
            start_date, end_date, base_dir
        )
    
    return monthly_dirs


def init_search_resources(
    persist_dir: str | None = None,
    collection_name: str = "pdf_chunks",
    model_name: str = "intfloat/multilingual-e5-base",
) -> None:
    """Initialize ChromaDB collections and embedding model for semantic search.
    
    Supports loading multiple monthly collections (e.g., 202407, 202408, 202409).
    
    Args:
        persist_dir: Comma or colon-separated list of directories containing ChromaDB data.
                    Can be single directory or multiple (e.g., "./investor_agent/data/vector-data/202407,./investor_agent/data/vector-data/202408").
                    If None, uses NEWS_PERSIST_DIR environment variable or defaults to './investor_agent/data/vector-data'
        collection_name: Name of the ChromaDB collection to load (default: 'pdf_chunks')
        model_name: SentenceTransformer model name for embeddings (default: 'intfloat/multilingual-e5-base')
    """
    if not _SEMANTIC_SEARCH_AVAILABLE:
        logger.error("Cannot initialize search resources - dependencies not installed")
        return
    
    # Allow reinitialization if persist_dir is explicitly provided (dynamic loading)
    if _search_state.initialized and persist_dir is None:
        logger.debug("Search resources already initialized, skipping")
        return
    
    if persist_dir is None:
        persist_dir = os.environ.get("NEWS_PERSIST_DIR", "./investor_agent/data/vector-data")
    
    # Split on comma and os.pathsep (':'), strip empties
    raw_parts = []
    for segment in persist_dir.split(","):
        raw_parts.extend(segment.split(os.pathsep))
    dirs = [p.strip() for p in raw_parts if p.strip()]
    if not dirs:
        dirs = ["./vector-data"]
    
    logger.info("Loading ChromaDB collections from %d director%s: %s", 
                len(dirs), "y" if len(dirs) == 1 else "ies", ", ".join(dirs))
    
    # Load collections from all directories
    collections = []
    for d in dirs:
        try:
            persistent_client = chromadb.PersistentClient(path=d)
            collection = persistent_client.get_collection(collection_name)
            collections.append(collection)
            logger.info(
                "✓ Loaded collection '%s' from '%s' (count=%d)",
                collection_name,
                d,
                collection.count(),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("✗ Skipping '%s' due to load error: %s", d, e)
    
    if not collections:
        logger.error("❌ No collections loaded from provided directories: %s", dirs)
        return
    
    _search_state.collections = collections
    _search_state.model = SentenceTransformer(model_name)
    _search_state.initialized = True
    logger.info("✅ News search resources initialized (model=%s, collections=%d)", model_name, len(collections))


def semantic_search(
    query: str,
    n_results: int = 5,
    min_similarity: float = 0.3,
) -> list[dict]:
    """Performs semantic search on ingested news PDFs and returns matching documents.

    This function searches through locally stored PDF chunks (Economic Times, etc.)
    using sentence embeddings. It's designed to be used as a tool by the NewsAnalyst
    agent to find relevant news for stock analysis.

    Args:
        query: The search query string (e.g., "RELIANCE earnings November 2025").
        n_results: Number of results to return. Defaults to 5.
        min_similarity: Minimum similarity threshold (0-1).
            Defaults to 0.3. Lower threshold = more results but less relevant.

    Returns:
        list[dict]: List of dictionaries, each containing:
            - 'document' (str): The document text content (PDF chunk)
            - 'metadata' (dict): Metadata including source file and chunk index
            - 'similarity' (float): Similarity score (0-1, higher is better)

    Example:
        >>> results = semantic_search("TCS quarterly results", n_results=3)
        >>> for result in results:
        ...     print(f"Similarity: {result['similarity']}")
        ...     print(f"Source: {result['metadata']['source']}")
        ...     print(f"Content: {result['document'][:200]}...")
    """
    if not _SEMANTIC_SEARCH_AVAILABLE:
        logger.error("semantic_search called but dependencies not installed")
        return []
    
    # Ensure resources are initialized
    if not _search_state.initialized:
        init_search_resources()
    
    if not _search_state.collections or _search_state.model is None:
        logger.error("semantic_search called but resources not initialized")
        return []

    # Add query prefix required by multilingual-e5-base model
    prefixed_query = f"query: {query}"
    query_embedding = _search_state.model.encode(prefixed_query)
    # Convert to plain list[float] if needed for Chroma types
    if hasattr(query_embedding, 'tolist'):
        query_embedding = query_embedding.tolist()
    qe_list = cast(list[float], query_embedding)

    # Perform semantic search across all collections
    aggregate_results = []
    for col in _search_state.collections:
        results = col.query(query_embeddings=[qe_list], n_results=n_results)
        if not results or not results.get("documents"):
            continue
        documents = results["documents"][0]  # type: ignore[index]
        metadatas = results["metadatas"][0]  # type: ignore[index]
        scores_or_distances = results.get("distances",
                  results.get("scores", [[]]))[0]  # type: ignore[index]
        for doc, meta, score in zip(
            documents,
            metadatas,
            scores_or_distances,
        ):
            if "scores" in results:
                similarity = score
            elif "distances" in results:
                similarity = 1 - score
            else:
                similarity = None
            if similarity is not None and similarity >= min_similarity:
                aggregate_results.append(
                    {
                        "document": doc,
                        "metadata": meta,
                        "similarity": round(similarity, 4),
                    }
                )
    # Sort combined results by similarity desc and truncate
    aggregate_results.sort(key=lambda r: r["similarity"], reverse=True)
    return aggregate_results[:n_results]


def load_collections_for_date_range(
    start_date: str,
    end_date: str,
    base_dir: str = "./investor_agent/data/vector-data",
    collection_name: str = "pdf_chunks",
) -> bool:
    """Dynamically load collections for specific date range.
    
    This function determines which monthly directories to load based on the
    query date range and reinitializes the search resources.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        base_dir: Base directory containing monthly subdirectories (default: ./investor_agent/data/vector-data)
                 Can be overridden via NEWS_BASE_DIR environment variable
        collection_name: ChromaDB collection name
        
    Returns:
        True if collections loaded successfully, False otherwise
        
    Example:
        >>> load_collections_for_date_range('2024-07-01', '2024-09-30')
        # Loads ./investor_agent/data/vector-data/202407, ./investor_agent/data/vector-data/202408, ./investor_agent/data/vector-data/202409
    """
    if not _SEMANTIC_SEARCH_AVAILABLE:
        logger.error("Semantic search dependencies not available")
        return False
    
    # Allow override via environment variable
    base_dir = os.environ.get("NEWS_BASE_DIR", base_dir)
    
    # Get monthly directories for date range (only existing ones)
    monthly_dirs = get_monthly_dirs_for_date_range(start_date, end_date, base_dir)
    
    if not monthly_dirs:
        logger.error("No existing directories found for date range %s to %s in %s", 
                    start_date, end_date, base_dir)
        return False
    
    logger.info("📅 Loading collections for date range %s to %s", start_date, end_date)
    logger.info("   Directories: %s", ", ".join([os.path.basename(d) for d in monthly_dirs]))
    
    # Clear existing state to force reinitialization
    _search_state.initialized = False
    _search_state.collections = []
    _search_state.model = None
    
    # Load collections from the determined directories
    collections = []
    for dir_path in monthly_dirs:
        try:
            persistent_client = chromadb.PersistentClient(path=dir_path)
            collection = persistent_client.get_collection(collection_name)
            collections.append(collection)
            logger.info(
                "   ✓ Loaded '%s' from %s (count=%d)",
                collection_name,
                os.path.basename(dir_path),
                collection.count(),
            )
        except Exception as e:
            logger.warning("   ✗ Failed to load from %s: %s", dir_path, e)
    
    if not collections:
        logger.error("❌ No collections loaded successfully")
        return False
    
    # Initialize the model (only once)
    if _search_state.model is None:
        try:
            _search_state.model = SentenceTransformer("intfloat/multilingual-e5-base")
            logger.info("   ✓ Loaded embedding model: intfloat/multilingual-e5-base")
        except Exception as e:
            logger.error("   ✗ Failed to load embedding model: %s", e)
            return False
    
    # Update state
    _search_state.collections = collections
    _search_state.initialized = True
    
    logger.info("✅ Successfully loaded %d collection(s)", len(collections))
    return True
