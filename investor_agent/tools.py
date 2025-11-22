from datetime import datetime, timedelta, date
from typing import Optional
import pandas as pd
from investor_agent.data_engine import NSESTORE
from investor_agent.logger import get_logger

logger = get_logger(__name__)

# Sector mapping for major Indian stocks
# This is a simplified mapping - expand as needed
SECTOR_MAP = {
    # Banking
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", 
    "AXISBANK": "Banking", "KOTAKBANK": "Banking", "INDUSINDBK": "Banking",
    "BANDHANBNK": "Banking", "FEDERALBNK": "Banking", "IDFCFIRSTB": "Banking",
    "PNB": "Banking", "BANKBARODA": "Banking", "CANBK": "Banking",
    
    # IT
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT",
    "TECHM": "IT", "LTIM": "IT", "COFORGE": "IT", "MPHASIS": "IT",
    
    # Auto
    "MARUTI": "Auto", "M&M": "Auto", "TATAMOTORS": "Auto", "BAJAJ-AUTO": "Auto",
    "EICHERMOT": "Auto", "HEROMOTOCO": "Auto", "TVSMOTOR": "Auto",
    
    # Pharma
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma",
    "DIVISLAB": "Pharma", "BIOCON": "Pharma", "AUROPHARMA": "Pharma",
    
    # FMCG
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG", "DABUR": "FMCG", "MARICO": "FMCG",
    
    # Energy & Oil
    "RELIANCE": "Energy", "ONGC": "Energy", "BPCL": "Energy",
    "IOC": "Energy", "HINDPETRO": "Energy", "ADANIGREEN": "Energy",
    
    # Metals
    "TATASTEEL": "Metals", "HINDALCO": "Metals", "JSWSTEEL": "Metals",
    "VEDL": "Metals", "COALINDIA": "Metals", "SAIL": "Metals",
    
    # Telecom
    "BHARTIARTL": "Telecom", "IDEA": "Telecom",
    
    # Financial Services (NBFCs)
    "BAJFINANCE": "Financial Services", "SHRIRAMFIN": "Financial Services",
    "CHOLAFIN": "Financial Services", "MUTHOOTFIN": "Financial Services",
    "LICHSGFIN": "Financial Services", "HDFCLIFE": "Financial Services",
    "SBILIFE": "Financial Services", "ICICIGI": "Financial Services",
}


def get_sector_stocks(sector: str) -> list:
    """Get list of stock symbols for a given sector."""
    sector_upper = sector.upper()
    return [symbol for symbol, sec in SECTOR_MAP.items() if sec.upper() == sector_upper]


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


def get_top_gainers(start_date: str = None, end_date: str = None, top_n: int = 10) -> str:
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
    output += f"\n**Average Return:** {avg_return:+.2f}%\n"
    output += f"**Period:** {ranked.iloc[0]['days_count']} trading days\n"
    
    return output


def get_top_losers(start_date: str = None, end_date: str = None, top_n: int = 10) -> str:
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
    output += f"\n**Average Return:** {avg_return:+.2f}%\n"
    output += f"**Period:** {losers.iloc[0]['days_count']} trading days\n"
    
    return output


def get_sector_top_performers(
    sector: str, 
    start_date: str = None, 
    end_date: str = None, 
    top_n: int = 5
) -> str:
    """
    Get top performing stocks from a specific sector.
    
    Args:
        sector: Sector name (e.g., 'Banking', 'IT', 'Auto', 'Pharma', 'FMCG', 
                'Energy', 'Metals', 'Telecom', 'Financial Services')
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        top_n: Number of top stocks to return (default 5)
    
    Returns:
        Formatted table of top performers in the sector
    
    Available sectors: Banking, IT, Auto, Pharma, FMCG, Energy, Metals, 
                      Telecom, Financial Services
    """
    # Get stocks in this sector
    sector_stocks = get_sector_stocks(sector)
    
    if not sector_stocks:
        available_sectors = sorted(set(SECTOR_MAP.values()))
        return f"❌ Sector '{sector}' not found. Available sectors: {', '.join(available_sectors)}"
    
    _ = NSESTORE.df
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    # Default to last 30 days
    note = ""
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=30)
            note = f"⚠️ No dates specified. Using last 30 days: {s_date} to {e_date}\n\n"
        else:
            return "❌ No data available."
    
    # Analyze each stock in the sector
    from investor_agent.data_engine import MetricsEngine
    
    results = []
    for symbol in sector_stocks:
        stock_df = NSESTORE.get_stock_data(symbol, s_date, e_date)
        if not stock_df.empty:
            stats = MetricsEngine.calculate_period_stats(stock_df)
            if stats:
                stats['symbol'] = symbol
                results.append(stats)
    
    if not results:
        return f"❌ No data found for {sector} stocks between {s_date} and {e_date}"
    
    # Sort by return percentage
    results.sort(key=lambda x: x['return_pct'], reverse=True)
    results = results[:top_n]
    
    # Format output
    output = f"{note}### 🏆 Top {top_n} {sector} Stocks ({s_date} to {e_date})\n\n"
    output += "| Rank | Symbol | Return % | Start → End Price | Volatility | Avg Delivery % |\n"
    output += "|------|--------|----------|-------------------|------------|----------------|\n"
    
    for idx, stats in enumerate(results, 1):
        output += (f"| {idx:2d}   | {stats['symbol']:12s} | "
                  f"{stats['return_pct']:+7.2f}% | "
                  f"₹{stats['start_price']:8.2f} → ₹{stats['end_price']:8.2f} | "
                  f"{stats['volatility']:5.2f}% | "
                  f"{stats['avg_delivery_pct']:5.1f}% |\n")
    
    avg_return = sum(s['return_pct'] for s in results) / len(results)
    output += f"\n**Sector Average Return:** {avg_return:+.2f}%\n"
    output += f"**Stocks Analyzed:** {len(results)}/{len(sector_stocks)}\n"
    output += f"**Period:** {results[0]['days_count']} trading days\n"
    
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
    from investor_agent.data_engine import MetricsEngine
    stats = MetricsEngine.calculate_period_stats(stock_df)
    
    if not stats:
        return f"❌ Insufficient data to analyze {symbol.upper()}"
    
    # Build analysis report
    output = f"""### 📊 Analysis: {symbol.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Period:** {stats['start_date']} to {stats['end_date']} ({stats['days_count']} days)

**Price Performance:**
- Starting Price: ₹{stats['start_price']:.2f}
- Ending Price: ₹{stats['end_price']:.2f}
- Return: {stats['return_pct']:+.2f}%
- Momentum: {stats['momentum_pct']:+.2f}%
- High: ₹{stats['period_high']:.2f}
- Low: ₹{stats['period_low']:.2f}
- Range: {((stats['period_high'] - stats['period_low']) / stats['start_price'] * 100):.2f}%

**Technical Levels:**
- 20-Day SMA: ₹{stats['sma_20']:.2f} ({((stats['end_price']/stats['sma_20']-1)*100):+.1f}%)
- 50-Day SMA: ₹{stats['sma_50']:.2f} ({((stats['end_price']/stats['sma_50']-1)*100):+.1f}%)
- Distance from High: {stats['distance_from_high_pct']:.1f}%
- Distance from Low: {stats['distance_from_low_pct']:+.1f}%

**Risk Metrics:**
- Volatility: {stats['volatility']:.2f}%
- Max Drawdown: {stats['max_drawdown']:.2f}%
- Price Stability: {'High' if stats['volatility'] < 2 else 'Moderate' if stats['volatility'] < 5 else 'Low'}

**Momentum Indicators:**
- Consecutive Up Days: {stats['consecutive_ups']}
- Consecutive Down Days: {stats['consecutive_downs']}
- Volume Trend: {stats['volume_trend_pct']:+.1f}%

**Volume & Delivery:**
- Avg Daily Volume: {stats['avg_volume']:,} shares
- Avg Delivery %: {stats['avg_delivery_pct']:.1f}%
"""
    
    # Add verdict based on patterns
    output += "\n**Investment Verdict:**\n"
    
    if stats['return_pct'] > 5 and stats['avg_delivery_pct'] > 60:
        output += "🟢 **Strong Accumulation** - High returns with high delivery suggests institutional buying\n"
    elif stats['return_pct'] > 3 and stats['avg_delivery_pct'] > 50:
        output += "🟢 **Positive Momentum** - Good returns with decent delivery\n"
    elif stats['return_pct'] < -5 and stats['avg_delivery_pct'] > 60:
        output += "🔴 **Distribution Pattern** - Falling price with high delivery suggests selling pressure\n"
    elif stats['return_pct'] < -3:
        output += "🔴 **Weakness** - Negative returns, proceed with caution\n"
    elif stats['volatility'] > 10:
        output += "🟡 **High Volatility** - Significant price swings, suitable for traders not investors\n"
    else:
        output += "🟡 **Neutral/Consolidation** - No clear trend, wait for better signals\n"
    
    # Add trend analysis
    if stats['end_price'] > stats['sma_20'] > stats['sma_50']:
        output += "📈 **Trend:** UPTREND - Price above both SMAs\n"
    elif stats['end_price'] < stats['sma_20'] < stats['sma_50']:
        output += "📉 **Trend:** DOWNTREND - Price below both SMAs\n"
    else:
        output += "➡️ **Trend:** SIDEWAYS - Mixed signals\n"
    
    return output


# ==============================================================================
# PHASE 2: ADVANCED ANALYSIS TOOLS
# ==============================================================================

def detect_volume_surge(symbol: str, lookback_days: int = 20) -> str:
    """
    Detect unusual volume activity by comparing recent volume to historical average.
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')
        lookback_days: Number of days to use for average calculation (default 20)
    
    Returns:
        Analysis showing if current volume is significantly higher than average
        (indicates potential breakout, news event, or institutional activity)
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return "❌ No data available."
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=lookback_days + 5)  # Extra buffer
    
    stock_df = NSESTORE.get_stock_data(symbol.upper(), start_date, end_date)
    
    if stock_df.empty or len(stock_df) < 5:
        return f"❌ Insufficient data for {symbol.upper()}"
    
    # Get recent volume (last 3 days avg)
    recent_vol = stock_df.tail(3)['VOLUME'].mean()
    
    # Get baseline average (exclude last 3 days)
    baseline_vol = stock_df.iloc[:-3]['VOLUME'].mean()
    
    if baseline_vol == 0:
        return f"❌ Invalid volume data for {symbol.upper()}"
    
    surge_pct = ((recent_vol - baseline_vol) / baseline_vol) * 100
    
    output = f"""### 📊 Volume Analysis: {symbol.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Period:** Last {lookback_days} days ending {end_date}

**Volume Metrics:**
- Recent Avg (3 days): {recent_vol:,.0f} shares
- Baseline Avg ({lookback_days} days): {baseline_vol:,.0f} shares
- Surge: {surge_pct:+.1f}%

**Verdict:**
"""
    
    if surge_pct > 100:
        output += "🔥 **EXTREME SURGE** - Volume doubled! Possible news/event catalyst\n"
    elif surge_pct > 50:
        output += "⚡ **HIGH SURGE** - Significant volume increase, watch for breakout\n"
    elif surge_pct > 20:
        output += "🟢 **MODERATE SURGE** - Above-average interest\n"
    elif surge_pct < -20:
        output += "🔵 **LOW VOLUME** - Below average, consolidation or lack of interest\n"
    else:
        output += "🟡 **NORMAL** - Volume within typical range\n"
    
    return output


def compare_stocks(symbols: list, start_date: str = None, end_date: str = None) -> str:
    """
    Side-by-side comparison of multiple stocks over the same period.
    
    Args:
        symbols: List of stock symbols (e.g., ['RELIANCE', 'TCS', 'HDFCBANK'])
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        Comparative table showing relative performance
        
    If dates not provided, uses last 30 days.
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
    
    from investor_agent.data_engine import MetricsEngine
    
    results = []
    for symbol in symbols:
        stock_df = NSESTORE.get_stock_data(symbol.upper(), s_date, e_date)
        if not stock_df.empty:
            stats = MetricsEngine.calculate_period_stats(stock_df)
            if stats:
                stats['symbol'] = symbol.upper()
                results.append(stats)
    
    if not results:
        return f"❌ No data found for any symbols between {s_date} and {e_date}"
    
    # Format comparative table
    output = f"""### 🔄 Stock Comparison ({s_date} to {e_date})

| Symbol | Return % | Volatility | Delivery % | Start Price | End Price | Verdict |
|--------|----------|------------|------------|-------------|-----------|---------|
"""
    
    for stats in results:
        # Simple verdict
        if stats['return_pct'] > 5:
            verdict = "🟢 Strong"
        elif stats['return_pct'] > 0:
            verdict = "🟢 Positive"
        elif stats['return_pct'] > -5:
            verdict = "🟡 Weak"
        else:
            verdict = "🔴 Poor"
        
        output += (f"| {stats['symbol']:10s} | {stats['return_pct']:+7.2f}% | "
                  f"{stats['volatility']:5.2f}% | {stats['avg_delivery_pct']:5.1f}% | "
                  f"₹{stats['start_price']:7.2f} | ₹{stats['end_price']:7.2f} | {verdict} |\n")
    
    # Add insights
    best = max(results, key=lambda x: x['return_pct'])
    worst = min(results, key=lambda x: x['return_pct'])
    
    output += f"\n**Best Performer:** {best['symbol']} ({best['return_pct']:+.2f}%)\n"
    output += f"**Worst Performer:** {worst['symbol']} ({worst['return_pct']:+.2f}%)\n"
    output += f"**Spread:** {best['return_pct'] - worst['return_pct']:.2f}%\n"
    
    return output


def get_delivery_momentum(start_date: str = None, end_date: str = None, min_delivery: float = 50.0) -> str:
    """
    Find stocks with consistently high delivery percentage (institutional buying).
    
    Args:
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
        min_delivery: Minimum average delivery % threshold (default 50%)
    
    Returns:
        List of stocks showing strong institutional interest
        
    High delivery % (>50%) indicates institutions are taking delivery, not just trading.
    """
    _ = NSESTORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    # Default to last 14 days
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=14)
        else:
            return "❌ No data available."
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(s_date)) & (df["DATE"] <= pd.Timestamp(e_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return f"❌ No data found between {s_date} and {e_date}"
    
    # Calculate average delivery for each stock
    from investor_agent.data_engine import MetricsEngine
    
    results = []
    for symbol, group in filtered.groupby("SYMBOL"):
        stats = MetricsEngine.calculate_period_stats(group)
        if stats and stats['avg_delivery_pct'] >= min_delivery:
            stats['symbol'] = symbol
            results.append(stats)
    
    if not results:
        return f"❌ No stocks found with delivery % >= {min_delivery}%"
    
    # Sort by delivery percentage (highest first)
    results.sort(key=lambda x: x['avg_delivery_pct'], reverse=True)
    results = results[:15]  # Top 15
    
    output = f"""### 🏦 High Delivery Momentum ({s_date} to {e_date})

Stocks with avg delivery ≥ {min_delivery}% (institutional conviction)

| Rank | Symbol | Delivery % | Return % | Price Trend | Signal |
|------|--------|------------|----------|-------------|--------|
"""
    
    for idx, stats in enumerate(results, 1):
        # Determine signal
        if stats['return_pct'] > 5 and stats['avg_delivery_pct'] > 60:
            signal = "🟢 Strong Buy"
        elif stats['return_pct'] > 0 and stats['avg_delivery_pct'] > 50:
            signal = "🟢 Accumulation"
        elif stats['return_pct'] < -5 and stats['avg_delivery_pct'] > 60:
            signal = "🔴 Distribution"
        else:
            signal = "🟡 Watch"
        
        output += (f"| {idx:2d}   | {stats['symbol']:10s} | "
                  f"{stats['avg_delivery_pct']:5.1f}% | {stats['return_pct']:+6.2f}% | "
                  f"₹{stats['start_price']:.2f}→₹{stats['end_price']:.2f} | {signal} |\n")
    
    output += f"\n**Total stocks with high delivery:** {len(results)}\n"
    output += "**Interpretation:** High delivery % = Institutions taking positions (bullish if price rising)\n"
    
    return output


def detect_breakouts(start_date: str = None, end_date: str = None, threshold: float = 10.0) -> str:
    """
    Detect stocks that are breaking out (hitting new highs with strong momentum).
    
    Args:
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format  
        threshold: Minimum return % to qualify as breakout (default 10%)
    
    Returns:
        List of stocks with price breakouts and strong momentum
    """
    _ = NSESTORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    # Default to last 7 days
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=7)
        else:
            return "❌ No data available."
    
    # Get top gainers
    ranked = NSESTORE.get_ranked_stocks(s_date, e_date, top_n=50, metric="return")
    
    if ranked.empty:
        return f"❌ No data found between {s_date} and {e_date}"
    
    # Filter for breakout candidates (high return + moderate volatility)
    breakouts = ranked[
        (ranked['return_pct'] >= threshold) & 
        (ranked['volatility'] < 15)  # Not too volatile (avoid manipulation)
    ].head(10)
    
    if breakouts.empty:
        return f"❌ No breakout candidates found (return >= {threshold}%, volatility < 15%)"
    
    output = f"""### ⚡ Breakout Candidates ({s_date} to {e_date})

Stocks with return ≥ {threshold}% and controlled volatility

| Rank | Symbol | Return % | Volatility | Delivery % | Breakout Quality |
|------|--------|----------|------------|------------|------------------|
"""
    
    for idx, (_, row) in enumerate(breakouts.iterrows(), 1):
        # Quality score
        if row['avg_delivery_pct'] > 60:
            quality = "🟢 High (Institutional)"
        elif row['avg_delivery_pct'] > 40:
            quality = "🟡 Medium"
        else:
            quality = "🔴 Low (Retail)"
        
        output += (f"| {idx:2d}   | {row['symbol']:10s} | "
                  f"{row['return_pct']:+6.2f}% | {row['volatility']:5.2f}% | "
                  f"{row['avg_delivery_pct']:5.1f}% | {quality} |\n")
    
    output += f"\n**Breakouts found:** {len(breakouts)}\n"
    output += "**Strategy:** Look for high delivery % breakouts (institutional backing)\n"
    
    return output


def list_available_tools() -> str:
    """
    Lists all available analysis tools with brief descriptions.
    Use this when user asks 'what can you do?' or 'what tools do you have?'
    
    Returns:
        Formatted list of all available tools and their purposes
    """
    return """### 🛠️ Available Analysis Tools

**PHASE 1: Core Stock Analysis**

1️⃣ **check_data_availability()**
   └─ Get date range and database statistics
   
2️⃣ **get_top_gainers(start_date, end_date, top_n)**
   └─ Find best performing stocks by return %
   
3️⃣ **get_top_losers(start_date, end_date, top_n)**
   └─ Find worst performing stocks by return %
   
4️⃣ **get_sector_top_performers(sector, start_date, end_date, top_n)** 🆕
   └─ Get top stocks from specific sector (Banking, IT, Auto, Pharma, FMCG, etc.)
   
5️⃣ **analyze_stock(symbol, start_date, end_date)**
   └─ Deep-dive analysis of individual stock with comprehensive metrics

**PHASE 2: Advanced Pattern Detection**

6️⃣ **detect_volume_surge(symbol, lookback_days)**
   └─ Identify unusual volume activity (potential breakouts/news events)
   
7️⃣ **compare_stocks(symbols, start_date, end_date)**
   └─ Side-by-side comparison of multiple stocks
   
8️⃣ **get_delivery_momentum(start_date, end_date, min_delivery)**
   └─ Find stocks with high institutional buying (delivery %)
   
9️⃣ **detect_breakouts(start_date, end_date, threshold)**
   └─ Identify momentum stocks breaking out with strong signals

**PHASE 3: Professional Trading Tools**

🔟 **get_52week_high_low(symbols, top_n)**
   └─ Find stocks near 52-week highs (breakouts) or lows (reversals)
   
1️⃣1️⃣ **analyze_risk_metrics(symbol, start_date, end_date)**
   └─ Advanced risk analysis: max drawdown, Sharpe ratio, volatility trends
   
1️⃣2️⃣ **find_momentum_stocks(min_return, min_consecutive_days, top_n)**
   └─ Find stocks with strong upward momentum (consecutive up days)
   
1️⃣3️⃣ **detect_reversal_candidates(lookback_days, top_n)**
   └─ Find oversold stocks showing early reversal signals
   
1️⃣4️⃣ **get_volume_price_divergence(min_divergence, top_n)**
   └─ Detect bearish/bullish divergence between price and volume

**NEWS & SYNTHESIS**

1️⃣5️⃣ **google_search(query)** [News Agent]
   └─ Search financial news to correlate with price movements

**AVAILABLE SECTORS FOR FILTERING:**
🏦 Banking, 💻 IT, 🚗 Auto, 💊 Pharma, 🛒 FMCG, 
⚡ Energy, 🏭 Metals, 📱 Telecom, 💰 Financial Services

**ADVANCED METRICS AVAILABLE:**
📊 Max Drawdown, Sharpe Ratio, Win Rate
📈 Moving Averages (20-day, 50-day SMA)
🎯 52-Week High/Low, Support/Resistance Levels
⚡ Momentum Indicators, Consecutive Days Streaks
📉 Volume-Price Divergence, Volume Trends
🔍 Risk-Adjusted Returns, Downside Volatility

**DATA COVERAGE:**
📅 NSE stock data with OHLCV + delivery metrics
📊 Multiple years of historical data for trend analysis
🔬 Real-time pattern detection with professional trading algorithms

**TIP:** Always start with check_data_availability() to understand the date range!
"""


# ==============================================================================
# PHASE 3: PROFESSIONAL TRADING TOOLS
# ==============================================================================

def get_52week_high_low(symbols: list = None, top_n: int = 20) -> str:
    """
    Find stocks near their 52-week highs or lows (critical psychological levels).
    
    Args:
        symbols: Optional list of symbols to check (if None, scans all stocks)
        top_n: Number of stocks to return (default 20)
    
    Returns:
        Stocks trading near 52-week highs (breakout candidates) or lows (reversal plays)
        
    Near 52-week high = within 5% of high (bullish breakout)
    Near 52-week low = within 10% of low (potential reversal/value play)
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return "❌ No data available."
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=365)
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return "❌ Insufficient data for 52-week analysis"
    
    results_high = []
    results_low = []
    
    symbols_to_check = symbols if symbols else filtered['SYMBOL'].unique()
    
    for symbol in symbols_to_check:
        stock_df = filtered[filtered['SYMBOL'] == symbol]
        if stock_df.empty:
            continue
        
        week_52_high = stock_df['HIGH'].max()
        week_52_low = stock_df['LOW'].min()
        current_price = stock_df.iloc[-1]['CLOSE']
        
        # Distance from 52-week high/low
        dist_from_high = ((current_price - week_52_high) / week_52_high) * 100
        dist_from_low = ((current_price - week_52_low) / week_52_low) * 100
        
        # Near 52-week high (within 5%)
        if dist_from_high >= -5:
            results_high.append({
                'symbol': symbol,
                'current': current_price,
                'week_52_high': week_52_high,
                'distance': dist_from_high
            })
        
        # Near 52-week low (within 10%)
        if dist_from_low <= 10:
            results_low.append({
                'symbol': symbol,
                'current': current_price,
                'week_52_low': week_52_low,
                'distance': dist_from_low
            })
    
    # Sort and limit
    results_high.sort(key=lambda x: x['distance'], reverse=True)
    results_low.sort(key=lambda x: x['distance'])
    
    output = f"### 🎯 52-Week High/Low Analysis\n\n"
    
    # Near Highs
    output += "**📈 NEAR 52-WEEK HIGHS (Breakout Candidates)**\n\n"
    if results_high:
        output += "| Symbol | Current | 52W High | Distance | Signal |\n"
        output += "|--------|---------|----------|----------|--------|\n"
        
        for item in results_high[:top_n]:
            signal = "🔥 At High" if item['distance'] >= -1 else "⚡ Near High"
            output += (f"| {item['symbol']:10s} | ₹{item['current']:.2f} | "
                      f"₹{item['week_52_high']:.2f} | {item['distance']:+.1f}% | {signal} |\n")
    else:
        output += "_No stocks near 52-week highs_\n"
    
    output += "\n**📉 NEAR 52-WEEK LOWS (Value/Reversal Plays)**\n\n"
    if results_low:
        output += "| Symbol | Current | 52W Low | Distance | Signal |\n"
        output += "|--------|---------|---------|----------|--------|\n"
        
        for item in results_low[:top_n]:
            signal = "🔴 At Low" if item['distance'] <= 2 else "🟡 Near Low"
            output += (f"| {item['symbol']:10s} | ₹{item['current']:.2f} | "
                      f"₹{item['week_52_low']:.2f} | {item['distance']:+.1f}% | {signal} |\n")
    else:
        output += "_No stocks near 52-week lows_\n"
    
    output += "\n**Strategy:**\n"
    output += "- 52W High breakouts: Look for volume confirmation + delivery % >50%\n"
    output += "- 52W Low reversals: Check for positive divergence in delivery/volume\n"
    
    return output


def analyze_risk_metrics(symbol: str, start_date: str = None, end_date: str = None) -> str:
    """
    Advanced risk analysis for a stock: max drawdown, Sharpe-like metrics, volatility trends.
    
    Args:
        symbol: Stock symbol
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        Comprehensive risk assessment with max drawdown, volatility analysis, and risk-adjusted returns
    """
    _ = NSESTORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    # Default to last 90 days for risk analysis
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=90)
        else:
            return "❌ No data available."
    
    stock_df = NSESTORE.get_stock_data(symbol.upper(), s_date, e_date)
    
    if stock_df.empty or len(stock_df) < 10:
        return f"❌ Insufficient data for {symbol.upper()}"
    
    from investor_agent.data_engine import MetricsEngine
    stats = MetricsEngine.calculate_period_stats(stock_df)
    
    if not stats:
        return f"❌ Unable to calculate metrics for {symbol.upper()}"
    
    # Calculate additional risk metrics
    daily_returns = stock_df['CLOSE'].pct_change().dropna()
    
    # Sharpe-like ratio (return / volatility)
    risk_adjusted_return = stats['return_pct'] / stats['volatility'] if stats['volatility'] > 0 else 0
    
    # Downside volatility (only negative returns)
    downside_returns = daily_returns[daily_returns < 0]
    downside_volatility = downside_returns.std() * 100 if len(downside_returns) > 0 else 0
    
    # Win rate (percentage of positive days)
    positive_days = len(daily_returns[daily_returns > 0])
    win_rate = (positive_days / len(daily_returns) * 100) if len(daily_returns) > 0 else 0
    
    output = f"""### ⚠️ Risk Analysis: {symbol.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Period:** {stats['start_date']} to {stats['end_date']} ({stats['days_count']} days)

**RETURN METRICS:**
- Total Return: {stats['return_pct']:+.2f}%
- Momentum: {stats['momentum_pct']:+.2f}%
- Risk-Adjusted Return: {risk_adjusted_return:.2f}x

**RISK METRICS:**
- Max Drawdown: {stats['max_drawdown']:.2f}% ⚠️
- Volatility (Overall): {stats['volatility']:.2f}%
- Downside Volatility: {downside_volatility:.2f}%
- Win Rate: {win_rate:.1f}% ({positive_days}/{len(daily_returns)} days)

**TECHNICAL POSITION:**
- Current Price: ₹{stats['end_price']:.2f}
- 20-Day SMA: ₹{stats['sma_20']:.2f} ({((stats['end_price']/stats['sma_20']-1)*100):+.1f}%)
- 50-Day SMA: ₹{stats['sma_50']:.2f} ({((stats['end_price']/stats['sma_50']-1)*100):+.1f}%)
- Distance from High: {stats['distance_from_high_pct']:.1f}%
- Distance from Low: {stats['distance_from_low_pct']:+.1f}%

**MOMENTUM INDICATORS:**
- Consecutive Up Days: {stats['consecutive_ups']}
- Consecutive Down Days: {stats['consecutive_downs']}
- Volume Trend: {stats['volume_trend_pct']:+.1f}%

**RISK VERDICT:**
"""
    
    # Risk assessment
    if abs(stats['max_drawdown']) > 20:
        output += "🔴 **HIGH RISK** - Severe drawdowns observed (>20%)\n"
    elif abs(stats['max_drawdown']) > 10:
        output += "🟡 **MODERATE RISK** - Significant volatility (10-20% drawdown)\n"
    else:
        output += "🟢 **LOW RISK** - Stable performance (<10% drawdown)\n"
    
    # Sharpe interpretation
    if risk_adjusted_return > 1.5:
        output += "🟢 **EXCELLENT** risk-reward ratio (>1.5x)\n"
    elif risk_adjusted_return > 0.8:
        output += "🟢 **GOOD** risk-reward ratio (0.8-1.5x)\n"
    elif risk_adjusted_return > 0:
        output += "🟡 **FAIR** risk-reward ratio (0-0.8x)\n"
    else:
        output += "🔴 **POOR** risk-reward - losses exceed volatility\n"
    
    # Trend assessment
    if stats['end_price'] > stats['sma_20'] > stats['sma_50']:
        output += "🟢 **UPTREND** - Price above both 20-day and 50-day SMA\n"
    elif stats['end_price'] < stats['sma_20'] < stats['sma_50']:
        output += "🔴 **DOWNTREND** - Price below both SMAs\n"
    else:
        output += "🟡 **MIXED TREND** - Consolidation phase\n"
    
    return output


def find_momentum_stocks(min_return: float = 5.0, min_consecutive_days: int = 3, top_n: int = 15) -> str:
    """
    Find stocks with strong momentum (consecutive up days + positive returns).
    
    Args:
        min_return: Minimum return % over last 10 days (default 5%)
        min_consecutive_days: Minimum consecutive up days (default 3)
        top_n: Number of stocks to return (default 15)
    
    Returns:
        Stocks showing sustained upward momentum
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return "❌ No data available."
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=15)  # Extra buffer
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return "❌ No data for momentum analysis"
    
    from investor_agent.data_engine import MetricsEngine
    
    results = []
    for symbol, group in filtered.groupby("SYMBOL"):
        if len(group) < 5:
            continue
        
        stats = MetricsEngine.calculate_period_stats(group)
        if not stats:
            continue
        
        # Filter by criteria
        if stats['return_pct'] >= min_return and stats['consecutive_ups'] >= min_consecutive_days:
            stats['symbol'] = symbol
            results.append(stats)
    
    if not results:
        return f"❌ No momentum stocks found (return >={min_return}%, consecutive days >={min_consecutive_days})"
    
    # Sort by combination of return and consecutive days
    results.sort(key=lambda x: (x['consecutive_ups'], x['return_pct']), reverse=True)
    results = results[:top_n]
    
    output = f"""### 🚀 Momentum Stocks (Last 10-15 Days)

**Criteria:** Return ≥ {min_return}% + Consecutive Up Days ≥ {min_consecutive_days}

| Rank | Symbol | Return % | Streak | Volume Trend | SMA Status |
|------|--------|----------|--------|--------------|------------|
"""
    
    for idx, stats in enumerate(results, 1):
        # SMA status
        if stats['end_price'] > stats['sma_20']:
            sma_status = "🟢 Above SMA"
        else:
            sma_status = "🔴 Below SMA"
        
        output += (f"| {idx:2d}   | {stats['symbol']:10s} | {stats['return_pct']:+6.2f}% | "
                  f"{stats['consecutive_ups']}📈 | {stats['volume_trend_pct']:+5.1f}% | {sma_status} |\n")
    
    output += f"\n**Total momentum stocks:** {len(results)}\n"
    output += "**Strategy:** Look for volume confirmation + price above SMA for continuation\n"
    
    return output


def detect_reversal_candidates(lookback_days: int = 30, top_n: int = 15) -> str:
    """
    Find oversold stocks showing early reversal signs (for contrarian plays).
    
    Args:
        lookback_days: Period for analysis (default 30 days)
        top_n: Number of candidates to return (default 15)
    
    Returns:
        Stocks that dropped significantly but showing reversal signals
        
    Reversal signals: Large decline + recent consecutive up days + volume increase
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return "❌ No data available."
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=lookback_days + 5)
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return "❌ No data for reversal analysis"
    
    from investor_agent.data_engine import MetricsEngine
    
    results = []
    for symbol, group in filtered.groupby("SYMBOL"):
        if len(group) < 10:
            continue
        
        stats = MetricsEngine.calculate_period_stats(group)
        if not stats:
            continue
        
        # Reversal criteria:
        # 1. Overall negative return (oversold)
        # 2. Recent consecutive up days (reversal starting)
        # 3. Volume increasing (accumulation)
        # 4. Not at 52-week low (avoid falling knives)
        
        if (stats['return_pct'] < -5 and 
            stats['consecutive_ups'] >= 2 and 
            stats['volume_trend_pct'] > 10 and
            stats['distance_from_low_pct'] > 5):
            
            stats['symbol'] = symbol
            results.append(stats)
    
    if not results:
        return f"❌ No reversal candidates found (last {lookback_days} days)"
    
    # Sort by combination of oversold + reversal strength
    results.sort(key=lambda x: (x['consecutive_ups'], -x['return_pct']), reverse=True)
    results = results[:top_n]
    
    output = f"""### 🔄 Reversal Candidates (Last {lookback_days} Days)

**Criteria:** Oversold (<-5%) + Recent Up Days (≥2) + Volume Surge (>10%)

| Rank | Symbol | Overall Return | Up Streak | Vol Trend | From Low | Signal |
|------|--------|----------------|-----------|-----------|----------|--------|
"""
    
    for idx, stats in enumerate(results, 1):
        # Reversal strength
        if stats['consecutive_ups'] >= 3 and stats['volume_trend_pct'] > 30:
            signal = "🟢 Strong"
        elif stats['consecutive_ups'] >= 2 and stats['volume_trend_pct'] > 15:
            signal = "🟡 Moderate"
        else:
            signal = "⚪ Weak"
        
        output += (f"| {idx:2d}   | {stats['symbol']:10s} | {stats['return_pct']:+6.2f}% | "
                  f"{stats['consecutive_ups']}📈 | {stats['volume_trend_pct']:+5.1f}% | "
                  f"{stats['distance_from_low_pct']:+5.1f}% | {signal} |\n")
    
    output += f"\n**Total candidates:** {len(results)}\n"
    output += "**⚠️ Risk:** Reversal trades are counter-trend. Wait for confirmation before entry.\n"
    output += "**Strategy:** Look for 3+ consecutive up days + delivery % >40% for confirmation\n"
    
    return output


def get_volume_price_divergence(min_divergence: float = 20.0, top_n: int = 15) -> str:
    """
    Detect volume-price divergence (price up but volume down = weak rally, and vice versa).
    
    Args:
        min_divergence: Minimum divergence % between price and volume trends (default 20%)
        top_n: Number of stocks to return (default 15)
    
    Returns:
        Stocks showing significant volume-price divergence (warning signals)
        
    Bearish divergence: Price rising but volume declining (rally losing steam)
    Bullish divergence: Price falling but volume increasing (accumulation)
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return "❌ No data available."
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=20)
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return "❌ No data for divergence analysis"
    
    from investor_agent.data_engine import MetricsEngine
    
    bearish_div = []  # Price up, volume down
    bullish_div = []  # Price down, volume up
    
    for symbol, group in filtered.groupby("SYMBOL"):
        if len(group) < 10:
            continue
        
        stats = MetricsEngine.calculate_period_stats(group)
        if not stats:
            continue
        
        # Calculate divergence
        divergence = stats['return_pct'] + stats['volume_trend_pct']
        
        # Bearish: Price positive, volume negative (or vice versa with threshold)
        if stats['return_pct'] > 3 and stats['volume_trend_pct'] < -min_divergence:
            bearish_div.append({
                **stats,
                'divergence': abs(stats['return_pct'] + stats['volume_trend_pct'])
            })
        
        # Bullish: Price negative, volume positive
        if stats['return_pct'] < -3 and stats['volume_trend_pct'] > min_divergence:
            bullish_div.append({
                **stats,
                'divergence': abs(stats['return_pct'] - stats['volume_trend_pct'])
            })
    
    output = f"### ⚠️ Volume-Price Divergence Analysis\n\n"
    
    # Bearish divergences
    output += "**🔴 BEARISH DIVERGENCE (Price ↑ but Volume ↓)**\n"
    output += "_Rally losing steam - potential reversal_\n\n"
    
    if bearish_div:
        bearish_div.sort(key=lambda x: x['divergence'], reverse=True)
        output += "| Symbol | Price Return | Volume Trend | Divergence | Risk |\n"
        output += "|--------|--------------|--------------|------------|------|\n"
        
        for item in bearish_div[:top_n]:
            risk = "🔴 High" if item['divergence'] > 40 else "🟡 Moderate"
            output += (f"| {item['symbol']:10s} | {item['return_pct']:+6.2f}% | "
                      f"{item['volume_trend_pct']:+6.2f}% | {item['divergence']:.1f}% | {risk} |\n")
    else:
        output += "_No bearish divergences found_\n"
    
    output += "\n**🟢 BULLISH DIVERGENCE (Price ↓ but Volume ↑)**\n"
    output += "_Accumulation during decline - potential reversal_\n\n"
    
    if bullish_div:
        bullish_div.sort(key=lambda x: x['divergence'], reverse=True)
        output += "| Symbol | Price Return | Volume Trend | Divergence | Opportunity |\n"
        output += "|--------|--------------|--------------|------------|-------------|\n"
        
        for item in bullish_div[:top_n]:
            opp = "🟢 High" if item['divergence'] > 40 else "🟡 Moderate"
            output += (f"| {item['symbol']:10s} | {item['return_pct']:+6.2f}% | "
                      f"{item['volume_trend_pct']:+6.2f}% | {item['divergence']:.1f}% | {opp} |\n")
    else:
        output += "_No bullish divergences found_\n"
    
    output += "\n**Trading Implications:**\n"
    output += "- Bearish divergence: Consider taking profits or tightening stops\n"
    output += "- Bullish divergence: Potential accumulation - watch for price reversal confirmation\n"
    
    return output