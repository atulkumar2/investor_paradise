from datetime import date, datetime, timedelta
from typing import Optional

from investor_agent.data_engine import NSESTORE, MetricsEngine
from investor_agent.logger import get_logger

logger = get_logger(__name__)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """
    Safely parse a date string in YYYY-MM-DD format.
    Returns a date or None if input is None or invalid.
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
    ALWAYS call this FIRST to understand what data is available.

    This tells you:
    - What 'Today', 'Yesterday', or 'Last Week' means in context of this data
    - The actual date range you can query
    """
    # Trigger load if not loaded
    _ = NSESTORE.df

    if NSESTORE.min_date and NSESTORE.max_date:
        return f"""Data Availability Report:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Start Date: {NSESTORE.min_date}
📅 End Date:   {NSESTORE.max_date}
📊 Total Symbols: {NSESTORE.total_symbols:,}
📈 Total Records: {len(NSESTORE.df):,}

Use these dates as reference for all queries.
For 'latest week', use the 7 days ending on {NSESTORE.max_date}."""

    return "⚠️ No data currently loaded."


def get_top_gainers(
  start_date: str = None, end_date: str = None, top_n: int = 10) -> str:
    """
    Get top performing stocks by percentage return over a period.

    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        top_n: Number of top stocks to return (default 10)

    Returns:
        Formatted table of top gainers with returns, prices, and delivery %

    If dates are not provided, defaults to the last 7 days of available data.
    """
    _ = NSESTORE.df  # Ensure data loaded

    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)

    note = ""

    # Default to last 7 days if no dates provided
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=7)
            note = f"⚠️ No dates specified. Using last 7 days: {s_date} to {e_date}\n\n"
        else:
            return "❌ No data available."

    # Get ranked stocks
    ranked = NSESTORE.get_ranked_stocks(s_date, e_date, top_n=top_n, metric="return")

    if ranked.empty:
        return f"❌ No data found between {s_date} and {e_date}"

    # Format output
    output = f"{note}### 📈 Top {top_n} Gainers ({s_date} to {e_date})\n\n"
    output += "| Rank | Symbol | Return % | Start → End Price | Volatility | Avg Delivery % |\n"
    output += "|------|--------|----------|-------------------|------------|----------------|\n"

    for idx, row in ranked.iterrows():
        output += (f"| {idx+1:2d}   | {row['symbol']:12s} | "
                  f"{row['return_pct']:+7.2f}% | "
                  f"₹{row['start_price']:8.2f} → ₹{row['end_price']:8.2f} | "
                  f"{row['volatility']:5.2f}% | "
                  f"{row['avg_delivery_pct']:5.1f}% |\n")

    # Add summary insights
    avg_return = ranked['return_pct'].mean()
    output += f"\n*Average Return:* {avg_return:+.2f}%\n"
    output += f"*Period:* {ranked.iloc[0]['days_count']} trading days\n"

    return output


def get_top_losers(
  start_date: str = None, end_date: str = None, top_n: int = 10) -> str:
    """
    Get worst performing stocks by percentage return over a period.

    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        top_n: Number of bottom stocks to return (default 10)

    Returns:
        Formatted table of top losers with returns, prices, and delivery %

    If dates are not provided, defaults to the last 7 days of available data.
    """
    _ = NSESTORE.df  # Ensure data loaded

    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)

    note = ""

    # Default to last 7 days if no dates provided
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=7)
            note = f"⚠️ No dates specified. Using last 7 days: {s_date} to {e_date}\n\n"
        else:
            return "❌ No data available."

    # Get all ranked stocks and take bottom N
    all_ranked = NSESTORE.get_ranked_stocks(s_date, e_date, top_n=1000, metric="return")

    if all_ranked.empty:
        return f"❌ No data found between {s_date} and {e_date}"

    # Get bottom performers
    losers = all_ranked.tail(top_n).sort_values("return_pct")

    # Format output
    output = f"{note}### 📉 Top {top_n} Losers ({s_date} to {e_date})\n\n"
    output += "| Rank | Symbol | Return % | Start → End Price | Volatility | Avg Delivery % |\n"
    output += "|------|--------|----------|-------------------|------------|----------------|\n"

    for idx, row in losers.iterrows():
        output += (f"| {idx+1:2d}   | {row['symbol']:12s} | "
                  f"{row['return_pct']:+7.2f}% | "
                  f"₹{row['start_price']:8.2f} → ₹{row['end_price']:8.2f} | "
                  f"{row['volatility']:5.2f}% | "
                  f"{row['avg_delivery_pct']:5.1f}% |\n")

    # Add summary insights
    avg_return = losers['return_pct'].mean()
    output += f"\n*Average Return:* {avg_return:+.2f}%\n"
    output += f"*Period:* {losers.iloc[0]['days_count']} trading days\n"

    return output


def analyze_stock(symbol: str, start_date: str = None, end_date: str = None) -> str:
    """
    Comprehensive analysis of a single stock over a period.

    Args:
        symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format

    Returns:
        Detailed analysis including returns, volatility, delivery patterns, and verdict

    If dates not provided, analyzes the last 30 days of available data.
    """
    _ = NSESTORE.df

    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)

    # Default to last 30 days
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=30)
        else:
            return "❌ No data available."

    # Get stock data
    stock_df = NSESTORE.get_stock_data(symbol.upper(), s_date, e_date)

    if stock_df.empty:
        return f"❌ No data found for {symbol.upper()} between {s_date} and {e_date}"

    # Calculate metrics
    stats = MetricsEngine.calculate_period_stats(stock_df)

    if not stats:
        return f"❌ Insufficient data to analyze {symbol.upper()}"

    # Build analysis report
    output = f"""### 📊 Analysis: {symbol.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

*Period:* {stats['start_date']} to {stats['end_date']} ({stats['days_count']} days)

*Price Performance:*
- Starting Price: ₹{stats['start_price']:.2f}
- Ending Price: ₹{stats['end_price']:.2f}
- Return: {stats['return_pct']:+.2f}%
- High: ₹{stats['period_high']:.2f}
- Low: ₹{stats['period_low']:.2f}
- Range: {((stats['period_high'] - stats['period_low']) / stats['start_price'] * 100):.2f}%

*Risk Metrics:*
- Volatility: {stats['volatility']:.2f}%
- Price Stability: {'High' if stats['volatility'] < 2 else 'Moderate' if stats['volatility'] < 5 else 'Low'}

*Volume & Delivery:*
- Avg Daily Volume: {stats['avg_volume']:,} shares
- Avg Delivery %: {stats['avg_delivery_pct']:.1f}%
"""

    # Add verdict based on patterns
    output += "\n*Investment Verdict:*\n"

    if stats['return_pct'] > 5 and stats['avg_delivery_pct'] > 60:
        output += "🟢 *Strong Accumulation* - High returns with high delivery suggests institutional buying\n"
    elif stats['return_pct'] > 3 and stats['avg_delivery_pct'] > 50:
        output += "🟢 *Positive Momentum* - Good returns with decent delivery\n"
    elif stats['return_pct'] < -5 and stats['avg_delivery_pct'] > 60:
        output += "🔴 *Distribution Pattern* - Falling price with high delivery suggests selling pressure\n"
    elif stats['return_pct'] < -3:
        output += "🔴 *Weakness* - Negative returns, proceed with caution\n"
    elif stats['volatility'] > 10:
        output += "🟡 *High Volatility* - Significant price swings, suitable for traders not investors\n"
    else:
        output += "🟡 *Neutral/Consolidation* - No clear trend, wait for better signals\n"

    return output