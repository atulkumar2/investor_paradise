from datetime import datetime, timedelta, date
from typing import Optional
import pandas as pd
from investor_agent.data_engine import STORE
from investor_agent.logger import get_logger

logger = get_logger(__name__)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    Safely parse a date string in YYYY-MM-DD format.
    Returns a `date` or `None` if input is None or invalid.
    """
    if not date_str:
        logger.debug("_parse_date: no date_str provided, returning None")
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception as e:
        logger.warning(f"_parse_date: failed to parse '{date_str}': {e}")
        return None

def check_data_availability() -> str:
    """
    Returns the start and end dates of the available data in the database.
    ALWAYS call this first to know what 'Today', 'Yesterday', or 'Last Year' means in the context of this data.
    """
    # Trigger load if not loaded
    _ = STORE.df
    if STORE.min_date and STORE.max_date:
        return f"Data Available From: {STORE.min_date} TO {STORE.max_date}"
    return "No data currently loaded."

def rank_market_performance(start_date: str = None, end_date: str = None, top_n: int = 5) -> str:
    """
    Ranks stocks by performance. 
    IF DATES ARE MISSING, DEFAULTS TO THE LAST 7 DAYS of available data.
    """
    # Ensure data is loaded to get max_date
    _ = STORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    note = ""
    
    # DEFAULT LOGIC: If no dates provided, use last 7 days of DB
    if not s_date or not e_date:
        if STORE.max_date:
            e_date = STORE.max_date
            s_date = e_date - timedelta(days=7)
            note = f"(⚠️ User did not specify dates. Defaulting to last 7 days: {s_date} to {e_date})"
        else:
            return "Error: No data available to calculate defaults."
            
    result = STORE.get_ranked_stocks(s_date, e_date, top_n=top_n)
    return f"{note}\n\n{result}"

def analyze_single_stock(symbol: str) -> str:
    """
    Provides a comprehensive snapshot of a single stock:
    - Latest Price
    - 1 Week Trend
    - Delivery/Accumulation status
    """
    df = STORE.df
    sdf = df[df["SYMBOL"] == symbol.upper()].sort_values("DATE")
    
    if sdf.empty:
        return f"Symbol {symbol} not found."
        
    # Get last 5 days
    recent = sdf.tail(5)
    if recent.empty:
        return "Insufficient history."
        
    latest = recent.iloc[-1]
    week_open = recent.iloc[0]['CLOSE']
    week_close = recent.iloc[-1]['CLOSE']
    week_change = ((week_close - week_open) / week_open) * 100.0
    
    # Handle DELIV_PER column - convert to numeric, handling string/concatenated values
    try:
        # Convert to numeric, coercing errors (strings become NaN)
        deliv_series = pd.to_numeric(recent['DELIV_PER'], errors='coerce')
        # Calculate mean, skipping NaN values
        avg_deliv = deliv_series.mean() if not deliv_series.isna().all() else 0.0
    except (KeyError, AttributeError):
        # DELIV_PER column doesn't exist or is completely unusable
        avg_deliv = 0.0
    
    out = f"### Analysis: {symbol}\n"
    out += f"- **Latest Date:** {latest['DATE']}\n"
    out += f"- **Close:** {latest['CLOSE']}\n"
    out += f"- **Weekly Move:** {week_change:.2f}%\n"
    out += f"- **Avg Delivery (5D):** {avg_deliv:.1f}%\n"
    
    if avg_deliv > 50 and week_change > 0:
        out += "- **Verdict:** Strong Accumulation (High Delivery + Price Up)\n"
    elif week_change < -2:
        out += "- **Verdict:** Short Term Weakness\n"
    else:
        out += "- **Verdict:** Neutral / Consolidation\n"
        
    return out