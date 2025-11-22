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


def get_top_gainers(start_date: Optional[str] = None, end_date: Optional[str] = None, top_n: int = 10) -> dict:
    """
    Get top performing stocks by percentage return over a period.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        top_n: Number of top stocks to return (default 10)
    
    Returns:
        Dictionary with period info, top gainers list, and summary statistics
    
    If dates are not provided, defaults to the last 7 days of available data.
    """
    _ = NSESTORE.df  # Ensure data loaded
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    dates_defaulted = False
    
    # Default to last 7 days if no dates provided
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=7)
            dates_defaulted = True
        else:
            return {"error": "No data available", "gainers": [], "period": {}}
    
    # Get ranked stocks
    ranked = NSESTORE.get_ranked_stocks(s_date, e_date, top_n=top_n, metric="return")
    
    if ranked.empty:
        return {
            "error": f"No data found between {s_date} and {e_date}",
            "gainers": [],
            "period": {"start": str(s_date), "end": str(e_date)}
        }
    
    # Build structured output
    return {
        "tool": "get_top_gainers",
        "period": {
            "start": str(s_date),
            "end": str(e_date),
            "days": int(ranked.iloc[0]['days_count']),
            "dates_defaulted": dates_defaulted
        },
        "gainers": [
            {
                "rank": idx + 1,
                "symbol": row['symbol'],
                "return_pct": round(float(row['return_pct']), 2),
                "price_start": round(float(row['start_price']), 2),
                "price_end": round(float(row['end_price']), 2),
                "volatility": round(float(row['volatility']), 2),
                "delivery_pct": round(float(row['avg_delivery_pct']), 1) if row['avg_delivery_pct'] else None
            }
            for idx, row in ranked.iterrows()
        ],
        "summary": {
            "avg_return": round(float(ranked['return_pct'].mean()), 2),
            "top_symbol": ranked.iloc[0]['symbol'],
            "top_return": round(float(ranked.iloc[0]['return_pct']), 2),
            "count": len(ranked)
        }
    }


def get_top_losers(start_date: Optional[str] = None, end_date: Optional[str] = None, top_n: int = 10) -> dict:
    """
    Get worst performing stocks by percentage return over a period.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        top_n: Number of bottom stocks to return (default 10)
    
    Returns:
        Dictionary with period info, top losers list, and summary statistics
    
    If dates are not provided, defaults to the last 7 days of available data.
    """
    _ = NSESTORE.df  # Ensure data loaded
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    dates_defaulted = False
    
    # Default to last 7 days if no dates provided
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=7)
            dates_defaulted = True
        else:
            return {"error": "No data available", "losers": [], "period": {}}
    
    # Get all ranked stocks and take bottom N
    all_ranked = NSESTORE.get_ranked_stocks(s_date, e_date, top_n=1000, metric="return")
    
    if all_ranked.empty:
        return {
            "error": f"No data found between {s_date} and {e_date}",
            "losers": [],
            "period": {"start": str(s_date), "end": str(e_date)}
        }
    
    # Get bottom performers
    losers = all_ranked.tail(top_n).sort_values("return_pct")
    
    return {
        "tool": "get_top_losers",
        "period": {
            "start": str(s_date),
            "end": str(e_date),
            "days": int(losers.iloc[0]['days_count']),
            "dates_defaulted": dates_defaulted
        },
        "losers": [
            {
                "rank": idx + 1,
                "symbol": row['symbol'],
                "return_pct": round(float(row['return_pct']), 2),
                "price_start": round(float(row['start_price']), 2),
                "price_end": round(float(row['end_price']), 2),
                "volatility": round(float(row['volatility']), 2),
                "delivery_pct": round(float(row['avg_delivery_pct']), 1) if row['avg_delivery_pct'] else None
            }
            for idx, row in losers.iterrows()
        ],
        "summary": {
            "avg_return": round(float(losers['return_pct'].mean()), 2),
            "worst_symbol": losers.iloc[0]['symbol'],
            "worst_return": round(float(losers.iloc[0]['return_pct']), 2),
            "count": len(losers)
        }
    }


def get_sector_top_performers(
    sector: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    top_n: int = 5
) -> dict:
    """
    Get top performing stocks from a specific sector.
    
    Args:
        sector: Sector name (e.g., 'Banking', 'IT', 'Auto', 'Pharma', 'FMCG', 
                'Energy', 'Metals', 'Telecom', 'Financial Services')
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        top_n: Number of top stocks to return (default 5)
    
    Returns:
        Dictionary with sector performers, period info, and summary statistics
    
    Available sectors: Banking, IT, Auto, Pharma, FMCG, Energy, Metals, 
                      Telecom, Financial Services
    """
    # Get stocks in this sector
    sector_stocks = get_sector_stocks(sector)
    
    if not sector_stocks:
        available_sectors = sorted(set(SECTOR_MAP.values()))
        return {
            "tool": "get_sector_top_performers",
            "error": f"Sector '{sector}' not found. Available: {', '.join(available_sectors)}"
        }
    
    _ = NSESTORE.df
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    dates_defaulted = False
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=30)
            dates_defaulted = True
        else:
            return {"tool": "get_sector_top_performers", "error": "No data available"}
    
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
        return {
            "tool": "get_sector_top_performers",
            "error": f"No data found for {sector} stocks between {s_date} and {e_date}"
        }
    
    # Sort by return percentage
    results.sort(key=lambda x: x['return_pct'], reverse=True)
    results = results[:top_n]
    
    return {
        "tool": "get_sector_top_performers",
        "sector": sector,
        "period": {
            "start": str(s_date),
            "end": str(e_date),
            "days": int(results[0]['days_count']),
            "dates_defaulted": dates_defaulted
        },
        "performers": [
            {
                "rank": idx + 1,
                "symbol": stats['symbol'],
                "return_pct": round(float(stats['return_pct']), 2),
                "price_start": round(float(stats['start_price']), 2),
                "price_end": round(float(stats['end_price']), 2),
                "volatility": round(float(stats['volatility']), 2),
                "delivery_pct": round(float(stats['avg_delivery_pct']), 1) if stats['avg_delivery_pct'] else None
            }
            for idx, stats in enumerate(results)
        ],
        "summary": {
            "sector_avg_return": round(sum(s['return_pct'] for s in results) / len(results), 2),
            "stocks_analyzed": len(results),
            "total_sector_stocks": len(sector_stocks),
            "top_symbol": results[0]['symbol'],
            "top_return": round(float(results[0]['return_pct']), 2)
        }
    }


def analyze_stock(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """
    Comprehensive analysis of a single stock over a period.
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        Dictionary with comprehensive stock analysis including price, technical, risk, and momentum metrics
    
    If dates not provided, analyzes the last 30 days of available data.
    """
    _ = NSESTORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    dates_defaulted = False
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=30)
            dates_defaulted = True
        else:
            return {"tool": "analyze_stock", "error": "No data available"}
    
    # Get stock data
    stock_df = NSESTORE.get_stock_data(symbol.upper(), s_date, e_date)
    
    if stock_df.empty:
        return {
            "tool": "analyze_stock",
            "error": f"No data found for {symbol.upper()} between {s_date} and {e_date}"
        }
    
    # Calculate metrics
    from investor_agent.data_engine import MetricsEngine
    stats = MetricsEngine.calculate_period_stats(stock_df)
    
    if not stats:
        return {"tool": "analyze_stock", "error": f"Insufficient data to analyze {symbol.upper()}"}
    
    # Calculate additional metrics
    price_range_pct = ((stats['period_high'] - stats['period_low']) / stats['start_price'] * 100)
    sma20_distance = ((stats['end_price'] / stats['sma_20'] - 1) * 100) if stats['sma_20'] > 0 else 0
    sma50_distance = ((stats['end_price'] / stats['sma_50'] - 1) * 100) if stats['sma_50'] > 0 else 0
    
    # Determine verdict
    verdict = "Neutral"
    verdict_reason = "Sideways movement, wait for clear trend"
    
    if stats['return_pct'] > 5 and stats['avg_delivery_pct'] > 60:
        verdict = "Strong Accumulation"
        verdict_reason = "High returns with high delivery suggests institutional buying"
    elif stats['return_pct'] > 3 and stats['avg_delivery_pct'] > 50:
        verdict = "Positive Momentum"
        verdict_reason = "Good returns with decent delivery"
    elif stats['return_pct'] < -5 and stats['avg_delivery_pct'] > 60:
        verdict = "Distribution Pattern"
        verdict_reason = "Falling price with high delivery suggests selling pressure"
    elif stats['return_pct'] < -3:
        verdict = "Weakness"
        verdict_reason = "Negative returns, proceed with caution"
    elif stats['volatility'] > 10:
        verdict = "High Volatility"
        verdict_reason = "Significant price swings, suitable for traders not investors"
    
    # Determine trend
    if stats['end_price'] > stats['sma_20'] > stats['sma_50']:
        trend = "UPTREND"
        trend_detail = "Price above both SMAs"
    elif stats['end_price'] < stats['sma_20'] < stats['sma_50']:
        trend = "DOWNTREND"
        trend_detail = "Price below both SMAs"
    else:
        trend = "SIDEWAYS"
        trend_detail = "Mixed signals"
    
    return {
        "tool": "analyze_stock",
        "symbol": symbol.upper(),
        "period": {
            "start": str(s_date),
            "end": str(e_date),
            "days": int(stats['days_count']),
            "dates_defaulted": dates_defaulted
        },
        "price": {
            "start": round(float(stats['start_price']), 2),
            "end": round(float(stats['end_price']), 2),
            "high": round(float(stats['period_high']), 2),
            "low": round(float(stats['period_low']), 2),
            "return_pct": round(float(stats['return_pct']), 2),
            "momentum_pct": round(float(stats['momentum_pct']), 2),
            "range_pct": round(float(price_range_pct), 2)
        },
        "technical": {
            "sma_20": round(float(stats['sma_20']), 2),
            "sma_50": round(float(stats['sma_50']), 2),
            "sma20_distance_pct": round(float(sma20_distance), 1),
            "sma50_distance_pct": round(float(sma50_distance), 1),
            "distance_from_high_pct": round(float(stats['distance_from_high_pct']), 1),
            "distance_from_low_pct": round(float(stats['distance_from_low_pct']), 1)
        },
        "risk": {
            "volatility": round(float(stats['volatility']), 2),
            "max_drawdown": round(float(stats['max_drawdown']), 2),
            "stability": "High" if stats['volatility'] < 2 else "Moderate" if stats['volatility'] < 5 else "Low"
        },
        "momentum": {
            "consecutive_up_days": int(stats['consecutive_ups']),
            "consecutive_down_days": int(stats['consecutive_downs']),
            "volume_trend_pct": round(float(stats['volume_trend_pct']), 1)
        },
        "volume": {
            "avg_daily_volume": int(stats['avg_volume']),
            "avg_delivery_pct": round(float(stats['avg_delivery_pct']), 1)
        },
        "verdict": {
            "signal": verdict,
            "reason": verdict_reason,
            "trend": trend,
            "trend_detail": trend_detail
        }
    }


# ==============================================================================
# PHASE 2: ADVANCED ANALYSIS TOOLS
# ==============================================================================

def detect_volume_surge(symbol: str, lookback_days: int = 20) -> dict:
    """
    Detect unusual volume activity by comparing recent volume to historical average.
    
    Args:
        symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')
        lookback_days: Number of days to use for average calculation (default 20)
    
    Returns:
        Dictionary with volume analysis showing if current volume is significantly higher than average
        (indicates potential breakout, news event, or institutional activity)
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return {"tool": "detect_volume_surge", "error": "No data available"}
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=lookback_days + 5)  # Extra buffer
    
    stock_df = NSESTORE.get_stock_data(symbol.upper(), start_date, end_date)
    
    if stock_df.empty or len(stock_df) < 5:
        return {
            "tool": "detect_volume_surge",
            "error": f"Insufficient data for {symbol.upper()}"
        }
    
    # Get recent volume (last 3 days avg)
    recent_vol = stock_df.tail(3)['VOLUME'].mean()
    
    # Get baseline average (exclude last 3 days)
    baseline_vol = stock_df.iloc[:-3]['VOLUME'].mean()
    
    if baseline_vol == 0:
        return {
            "tool": "detect_volume_surge",
            "error": f"Invalid volume data for {symbol.upper()}"
        }
    
    surge_pct = ((recent_vol - baseline_vol) / baseline_vol) * 100
    
    # Determine verdict
    if surge_pct > 100:
        verdict = "EXTREME SURGE"
        interpretation = "Volume doubled! Possible news/event catalyst"
    elif surge_pct > 50:
        verdict = "HIGH SURGE"
        interpretation = "Significant volume increase, watch for breakout"
    elif surge_pct > 20:
        verdict = "MODERATE SURGE"
        interpretation = "Above-average interest"
    elif surge_pct < -20:
        verdict = "LOW VOLUME"
        interpretation = "Below average, consolidation or lack of interest"
    else:
        verdict = "NORMAL"
        interpretation = "Volume within typical range"
    
    return {
        "tool": "detect_volume_surge",
        "symbol": symbol.upper(),
        "period": {
            "lookback_days": lookback_days,
            "end_date": str(end_date)
        },
        "volume": {
            "recent_avg": int(recent_vol),
            "baseline_avg": int(baseline_vol),
            "surge_pct": round(float(surge_pct), 1)
        },
        "verdict": verdict,
        "interpretation": interpretation
    }


def compare_stocks(symbols: list[str], start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """
    Side-by-side comparison of multiple stocks over the same period.
    
    Args:
        symbols: List of stock symbols (e.g., ['RELIANCE', 'TCS', 'HDFCBANK'])
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        Dictionary with comparative analysis of all stocks
        
    If dates not provided, uses last 30 days.
    """
    _ = NSESTORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    dates_defaulted = False
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=30)
            dates_defaulted = True
        else:
            return {"tool": "compare_stocks", "error": "No data available"}
    
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
        return {
            "tool": "compare_stocks",
            "error": f"No data found for any symbols between {s_date} and {e_date}"
        }
    
    # Determine verdict for each stock
    comparisons = []
    for stats in results:
        if stats['return_pct'] > 5:
            verdict = "Strong"
        elif stats['return_pct'] > 0:
            verdict = "Positive"
        elif stats['return_pct'] > -5:
            verdict = "Weak"
        else:
            verdict = "Poor"
        
        comparisons.append({
            "symbol": stats['symbol'],
            "return_pct": round(float(stats['return_pct']), 2),
            "volatility": round(float(stats['volatility']), 2),
            "delivery_pct": round(float(stats['avg_delivery_pct']), 1),
            "price_start": round(float(stats['start_price']), 2),
            "price_end": round(float(stats['end_price']), 2),
            "verdict": verdict
        })
    
    # Find best and worst performers
    best = max(results, key=lambda x: x['return_pct'])
    worst = min(results, key=lambda x: x['return_pct'])
    
    return {
        "tool": "compare_stocks",
        "period": {
            "start": str(s_date),
            "end": str(e_date),
            "days": int(results[0]['days_count']),
            "dates_defaulted": dates_defaulted
        },
        "comparisons": comparisons,
        "summary": {
            "best_performer": best['symbol'],
            "best_return": round(float(best['return_pct']), 2),
            "worst_performer": worst['symbol'],
            "worst_return": round(float(worst['return_pct']), 2),
            "spread": round(float(best['return_pct'] - worst['return_pct']), 2),
            "stocks_compared": len(comparisons)
        }
    }


def get_delivery_momentum(start_date: Optional[str] = None, end_date: Optional[str] = None, min_delivery: float = 50.0) -> str:
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


def get_delivery_momentum(start_date: Optional[str] = None, end_date: Optional[str] = None, min_delivery: float = 50.0) -> dict:
    """
    Find stocks with consistently high delivery percentage (institutional buying).
    
    Args:
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
        min_delivery: Minimum average delivery % threshold (default 50%)
    
    Returns:
        Dictionary with list of stocks showing strong institutional interest
        
    High delivery % (>50%) indicates institutions are taking delivery, not just trading.
    """
    _ = NSESTORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    dates_defaulted = False
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=14)
            dates_defaulted = True
        else:
            return {"tool": "get_delivery_momentum", "error": "No data available"}
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(s_date)) & (df["DATE"] <= pd.Timestamp(e_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return {
            "tool": "get_delivery_momentum",
            "error": f"No data found between {s_date} and {e_date}"
        }
    
    # Calculate average delivery for each stock
    from investor_agent.data_engine import MetricsEngine
    
    results = []
    for symbol, group in filtered.groupby("SYMBOL"):
        stats = MetricsEngine.calculate_period_stats(group)
        if stats and stats['avg_delivery_pct'] >= min_delivery:
            stats['symbol'] = symbol
            results.append(stats)
    
    if not results:
        return {
            "tool": "get_delivery_momentum",
            "error": f"No stocks found with delivery % >= {min_delivery}%"
        }
    
    # Sort by delivery percentage (highest first)
    results.sort(key=lambda x: x['avg_delivery_pct'], reverse=True)
    results = results[:15]  # Top 15
    
    stocks = []
    for idx, stats in enumerate(results, 1):
        # Determine signal
        if stats['return_pct'] > 5 and stats['avg_delivery_pct'] > 60:
            signal = "Strong Buy"
        elif stats['return_pct'] > 0 and stats['avg_delivery_pct'] > 50:
            signal = "Accumulation"
        elif stats['return_pct'] < -5 and stats['avg_delivery_pct'] > 60:
            signal = "Distribution"
        else:
            signal = "Watch"
        
        stocks.append({
            "rank": idx,
            "symbol": stats['symbol'],
            "delivery_pct": round(float(stats['avg_delivery_pct']), 1),
            "return_pct": round(float(stats['return_pct']), 2),
            "price_start": round(float(stats['start_price']), 2),
            "price_end": round(float(stats['end_price']), 2),
            "signal": signal
        })
    
    return {
        "tool": "get_delivery_momentum",
        "period": {
            "start": str(s_date),
            "end": str(e_date),
            "days": int(results[0]['days_count']),
            "dates_defaulted": dates_defaulted
        },
        "min_delivery_threshold": min_delivery,
        "stocks": stocks,
        "summary": {
            "total_found": len(stocks),
            "avg_delivery": round(sum(s['delivery_pct'] for s in stocks) / len(stocks), 1),
            "interpretation": "High delivery % = Institutions taking positions (bullish if price rising)"
        }
    }


def detect_breakouts(start_date: Optional[str] = None, end_date: Optional[str] = None, threshold: float = 10.0) -> dict:
    """
    Detect stocks that are breaking out (hitting new highs with strong momentum).
    
    Args:
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format  
        threshold: Minimum return % to qualify as breakout (default 10%)
    
    Returns:
        Dictionary with list of stocks showing price breakouts and strong momentum
    """
    _ = NSESTORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    dates_defaulted = False
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=7)
            dates_defaulted = True
        else:
            return {"tool": "detect_breakouts", "error": "No data available"}
    
    # Get top gainers
    ranked = NSESTORE.get_ranked_stocks(s_date, e_date, top_n=50, metric="return")
    
    if ranked.empty:
        return {
            "tool": "detect_breakouts",
            "error": f"No data found between {s_date} and {e_date}"
        }
    
    # Filter for breakout candidates (high return + moderate volatility)
    breakouts_df = ranked[
        (ranked['return_pct'] >= threshold) & 
        (ranked['volatility'] < 15)  # Not too volatile (avoid manipulation)
    ].head(10)
    
    if breakouts_df.empty:
        return {
            "tool": "detect_breakouts",
            "error": f"No breakout candidates found (return >= {threshold}%, volatility < 15%)"
        }
    
    breakouts = []
    for idx, (_, row) in enumerate(breakouts_df.iterrows(), 1):
        # Quality score
        if row['avg_delivery_pct'] > 60:
            quality = "High (Institutional)"
        elif row['avg_delivery_pct'] > 40:
            quality = "Medium"
        else:
            quality = "Low (Retail)"
        
        breakouts.append({
            "rank": idx,
            "symbol": row['symbol'],
            "return_pct": round(float(row['return_pct']), 2),
            "volatility": round(float(row['volatility']), 2),
            "delivery_pct": round(float(row['avg_delivery_pct']), 1),
            "price_start": round(float(row['start_price']), 2),
            "price_end": round(float(row['end_price']), 2),
            "quality": quality
        })
    
    return {
        "tool": "detect_breakouts",
        "period": {
            "start": str(s_date),
            "end": str(e_date),
            "days": int(breakouts_df.iloc[0]['days_count']),
            "dates_defaulted": dates_defaulted
        },
        "threshold": threshold,
        "breakouts": breakouts,
        "summary": {
            "total_found": len(breakouts),
            "avg_return": round(sum(b['return_pct'] for b in breakouts) / len(breakouts), 2),
            "strategy": "Look for high delivery % breakouts (institutional backing)"
        }
    }


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

def get_52week_high_low(symbols: Optional[list[str]] = None, top_n: int = 20) -> dict:
    """
    Find stocks near their 52-week highs or lows (critical psychological levels).
    
    Args:
        symbols: Optional list of symbols to check (if None, scans all stocks)
        top_n: Number of stocks to return (default 20)
    
    Returns:
        Dictionary with stocks trading near 52-week highs (breakout candidates) or lows (reversal plays)
        
    Near 52-week high = within 5% of high (bullish breakout)
    Near 52-week low = within 10% of low (potential reversal/value play)
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return {"tool": "get_52week_high_low", "error": "No data available"}
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=365)
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return {"tool": "get_52week_high_low", "error": "Insufficient data for 52-week analysis"}
    
    near_highs = []
    near_lows = []
    
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
            signal = "At High" if dist_from_high >= -1 else "Near High"
            near_highs.append({
                'symbol': symbol,
                'current_price': round(float(current_price), 2),
                'week_52_high': round(float(week_52_high), 2),
                'distance_pct': round(float(dist_from_high), 2),
                'signal': signal
            })
        
        # Near 52-week low (within 10%)
        if dist_from_low <= 10:
            signal = "At Low" if dist_from_low <= 1 else "Near Low"
            near_lows.append({
                'symbol': symbol,
                'current_price': round(float(current_price), 2),
                'week_52_low': round(float(week_52_low), 2),
                'distance_pct': round(float(dist_from_low), 2),
                'signal': signal
            })
    
    # Sort and limit
    near_highs.sort(key=lambda x: x['distance_pct'], reverse=True)
    near_lows.sort(key=lambda x: x['distance_pct'])
    
    return {
        "tool": "get_52week_high_low",
        "period": {
            "start": str(start_date),
            "end": str(end_date),
            "days": 365
        },
        "near_highs": near_highs[:top_n],
        "near_lows": near_lows[:top_n],
        "summary": {
            "stocks_near_high": len(near_highs),
            "stocks_near_low": len(near_lows),
            "strategy": "52W High breakouts need volume confirmation + delivery >50%; 52W Low reversals need positive divergence"
        }
    }


def analyze_risk_metrics(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> dict:
    """
    Advanced risk analysis for a stock: max drawdown, Sharpe-like metrics, volatility trends.
    
    Args:
        symbol: Stock symbol
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        Dictionary with comprehensive risk assessment including max drawdown, volatility analysis, and risk-adjusted returns
    """
    _ = NSESTORE.df
    
    s_date = _parse_date(start_date)
    e_date = _parse_date(end_date)
    
    dates_defaulted = False
    if not s_date or not e_date:
        if NSESTORE.max_date:
            e_date = NSESTORE.max_date
            s_date = e_date - timedelta(days=90)
            dates_defaulted = True
        else:
            return {"tool": "analyze_risk_metrics", "error": "No data available"}
    
    stock_df = NSESTORE.get_stock_data(symbol.upper(), s_date, e_date)
    
    if stock_df.empty or len(stock_df) < 10:
        return {
            "tool": "analyze_risk_metrics",
            "error": f"Insufficient data for {symbol.upper()}"
        }
    
    from investor_agent.data_engine import MetricsEngine
    stats = MetricsEngine.calculate_period_stats(stock_df)
    
    if not stats:
        return {
            "tool": "analyze_risk_metrics",
            "error": f"Unable to calculate metrics for {symbol.upper()}"
        }
    
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
    
    # Risk verdict
    if abs(stats['max_drawdown']) > 20:
        risk_level = "HIGH RISK"
        risk_detail = "Severe drawdowns observed (>20%)"
    elif abs(stats['max_drawdown']) > 10:
        risk_level = "MODERATE RISK"
        risk_detail = "Significant volatility (10-20% drawdown)"
    else:
        risk_level = "LOW RISK"
        risk_detail = "Stable performance (<10% drawdown)"
    
    # Sharpe interpretation
    if risk_adjusted_return > 1.5:
        sharpe_rating = "EXCELLENT"
        sharpe_detail = "risk-reward ratio (>1.5x)"
    elif risk_adjusted_return > 0.8:
        sharpe_rating = "GOOD"
        sharpe_detail = "risk-reward ratio (0.8-1.5x)"
    elif risk_adjusted_return > 0:
        sharpe_rating = "FAIR"
        sharpe_detail = "risk-reward ratio (0-0.8x)"
    else:
        sharpe_rating = "POOR"
        sharpe_detail = "losses exceed volatility"
    
    # Trend assessment
    if stats['end_price'] > stats['sma_20'] > stats['sma_50']:
        trend = "UPTREND"
        trend_detail = "Price above both 20-day and 50-day SMA"
    elif stats['end_price'] < stats['sma_20'] < stats['sma_50']:
        trend = "DOWNTREND"
        trend_detail = "Price below both SMAs"
    else:
        trend = "MIXED TREND"
        trend_detail = "Consolidation phase"
    
    return {
        "tool": "analyze_risk_metrics",
        "symbol": symbol.upper(),
        "period": {
            "start": str(s_date),
            "end": str(e_date),
            "days": int(stats['days_count']),
            "dates_defaulted": dates_defaulted
        },
        "returns": {
            "total_return_pct": round(float(stats['return_pct']), 2),
            "momentum_pct": round(float(stats['momentum_pct']), 2),
            "risk_adjusted_return": round(float(risk_adjusted_return), 2)
        },
        "risk": {
            "max_drawdown": round(float(stats['max_drawdown']), 2),
            "volatility": round(float(stats['volatility']), 2),
            "downside_volatility": round(float(downside_volatility), 2),
            "win_rate": round(float(win_rate), 1),
            "positive_days": int(positive_days),
            "total_days": len(daily_returns)
        },
        "technical": {
            "current_price": round(float(stats['end_price']), 2),
            "sma_20": round(float(stats['sma_20']), 2),
            "sma_50": round(float(stats['sma_50']), 2),
            "sma20_distance_pct": round(((stats['end_price']/stats['sma_20']-1)*100), 1) if stats['sma_20'] > 0 else 0,
            "sma50_distance_pct": round(((stats['end_price']/stats['sma_50']-1)*100), 1) if stats['sma_50'] > 0 else 0,
            "distance_from_high_pct": round(float(stats['distance_from_high_pct']), 1),
            "distance_from_low_pct": round(float(stats['distance_from_low_pct']), 1)
        },
        "momentum": {
            "consecutive_up_days": int(stats['consecutive_ups']),
            "consecutive_down_days": int(stats['consecutive_downs']),
            "volume_trend_pct": round(float(stats['volume_trend_pct']), 1)
        },
        "verdict": {
            "risk_level": risk_level,
            "risk_detail": risk_detail,
            "sharpe_rating": sharpe_rating,
            "sharpe_detail": sharpe_detail,
            "trend": trend,
            "trend_detail": trend_detail
        }
    }


def find_momentum_stocks(min_return: float = 5.0, min_consecutive_days: int = 3, top_n: int = 15) -> dict:
    """
    Find stocks with strong momentum (consecutive up days + positive returns).
    
    Args:
        min_return: Minimum return % over last 10 days (default 5%)
        min_consecutive_days: Minimum consecutive up days (default 3)
        top_n: Number of stocks to return (default 15)
    
    Returns:
        Dictionary with stocks showing sustained upward momentum
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return {"tool": "find_momentum_stocks", "error": "No data available"}
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=15)  # Extra buffer
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return {"tool": "find_momentum_stocks", "error": "No data for momentum analysis"}
    
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
        return {
            "tool": "find_momentum_stocks",
            "error": f"No momentum stocks found (return >={min_return}%, consecutive days >={min_consecutive_days})"
        }
    
    # Sort by combination of return and consecutive days
    results.sort(key=lambda x: (x['consecutive_ups'], x['return_pct']), reverse=True)
    results = results[:top_n]
    
    stocks = []
    for idx, stats in enumerate(results, 1):
        # SMA status
        sma_status = "Above SMA" if stats['end_price'] > stats['sma_20'] else "Below SMA"
        
        stocks.append({
            "rank": idx,
            "symbol": stats['symbol'],
            "return_pct": round(float(stats['return_pct']), 2),
            "consecutive_up_days": int(stats['consecutive_ups']),
            "volume_trend_pct": round(float(stats['volume_trend_pct']), 1),
            "sma_status": sma_status,
            "price_end": round(float(stats['end_price']), 2),
            "sma_20": round(float(stats['sma_20']), 2)
        })
    
    return {
        "tool": "find_momentum_stocks",
        "period": {
            "start": str(start_date),
            "end": str(end_date),
            "days": int(results[0]['days_count'])
        },
        "criteria": {
            "min_return": min_return,
            "min_consecutive_days": min_consecutive_days
        },
        "stocks": stocks,
        "summary": {
            "total_found": len(stocks),
            "strategy": "Look for volume confirmation + price above SMA for continuation"
        }
    }


def detect_reversal_candidates(lookback_days: int = 30, top_n: int = 15) -> dict:
    """
    Find oversold stocks showing early reversal signs (for contrarian plays).
    
    Args:
        lookback_days: Period for analysis (default 30 days)
        top_n: Number of candidates to return (default 15)
    
    Returns:
        Dictionary with stocks that dropped significantly but showing reversal signals
        
    Reversal signals: Large decline + recent consecutive up days + volume increase
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return {"tool": "detect_reversal_candidates", "error": "No data available"}
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=lookback_days + 5)
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return {"tool": "detect_reversal_candidates", "error": "No data for reversal analysis"}
    
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
        return {
            "tool": "detect_reversal_candidates",
            "error": f"No reversal candidates found (last {lookback_days} days)"
        }
    
    # Sort by combination of oversold + reversal strength
    results.sort(key=lambda x: (x['consecutive_ups'], -x['return_pct']), reverse=True)
    results = results[:top_n]
    
    candidates = []
    for idx, stats in enumerate(results, 1):
        # Reversal strength
        if stats['consecutive_ups'] >= 3 and stats['volume_trend_pct'] > 30:
            signal = "Strong"
        elif stats['consecutive_ups'] >= 2 and stats['volume_trend_pct'] > 15:
            signal = "Moderate"
        else:
            signal = "Weak"
        
        candidates.append({
            "rank": idx,
            "symbol": stats['symbol'],
            "overall_return_pct": round(float(stats['return_pct']), 2),
            "consecutive_up_days": int(stats['consecutive_ups']),
            "volume_trend_pct": round(float(stats['volume_trend_pct']), 1),
            "distance_from_low_pct": round(float(stats['distance_from_low_pct']), 1),
            "signal": signal,
            "price_current": round(float(stats['end_price']), 2)
        })
    
    return {
        "tool": "detect_reversal_candidates",
        "period": {
            "lookback_days": lookback_days,
            "start": str(start_date),
            "end": str(end_date)
        },
        "criteria": {
            "min_decline": -5.0,
            "min_up_days": 2,
            "min_volume_surge": 10.0
        },
        "candidates": candidates,
        "summary": {
            "total_found": len(candidates),
            "risk_warning": "Reversal trades are counter-trend. Wait for confirmation before entry.",
            "strategy": "Look for 3+ consecutive up days + delivery % >40% for confirmation"
        }
    }


def get_volume_price_divergence(min_divergence: float = 20.0, top_n: int = 15) -> dict:
    """
    Detect volume-price divergence (price up but volume down = weak rally, and vice versa).
    
    Args:
        min_divergence: Minimum divergence % between price and volume trends (default 20%)
        top_n: Number of stocks to return (default 15)
    
    Returns:
        Dictionary with stocks showing significant volume-price divergence (warning signals)
        
    Bearish divergence: Price rising but volume declining (rally losing steam)
    Bullish divergence: Price falling but volume increasing (accumulation)
    """
    _ = NSESTORE.df
    
    if not NSESTORE.max_date:
        return {"tool": "get_volume_price_divergence", "error": "No data available"}
    
    end_date = NSESTORE.max_date
    start_date = end_date - timedelta(days=20)
    
    df = NSESTORE.df
    mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
    filtered = df[mask].copy()
    
    if filtered.empty:
        return {"tool": "get_volume_price_divergence", "error": "No data for divergence analysis"}
    
    from investor_agent.data_engine import MetricsEngine
    
    bearish_div = []  # Price up, volume down
    bullish_div = []  # Price down, volume up
    
    for symbol, group in filtered.groupby("SYMBOL"):
        if len(group) < 10:
            continue
        
        stats = MetricsEngine.calculate_period_stats(group)
        if not stats:
            continue
        
        # Bearish: Price positive, volume negative (or vice versa with threshold)
        if stats['return_pct'] > 3 and stats['volume_trend_pct'] < -min_divergence:
            divergence_value = abs(stats['return_pct'] + stats['volume_trend_pct'])
            risk = "High" if divergence_value > 40 else "Moderate"
            bearish_div.append({
                "symbol": stats['symbol'],
                "price_return_pct": round(float(stats['return_pct']), 2),
                "volume_trend_pct": round(float(stats['volume_trend_pct']), 2),
                "divergence": round(float(divergence_value), 1),
                "risk": risk
            })
        
        # Bullish: Price negative, volume positive
        if stats['return_pct'] < -3 and stats['volume_trend_pct'] > min_divergence:
            divergence_value = abs(stats['return_pct'] - stats['volume_trend_pct'])
            opportunity = "High" if divergence_value > 40 else "Moderate"
            bullish_div.append({
                "symbol": stats['symbol'],
                "price_return_pct": round(float(stats['return_pct']), 2),
                "volume_trend_pct": round(float(stats['volume_trend_pct']), 2),
                "divergence": round(float(divergence_value), 1),
                "opportunity": opportunity
            })
    
    # Sort by divergence strength
    bearish_div.sort(key=lambda x: x['divergence'], reverse=True)
    bullish_div.sort(key=lambda x: x['divergence'], reverse=True)
    
    return {
        "tool": "get_volume_price_divergence",
        "period": {
            "start": str(start_date),
            "end": str(end_date),
            "days": 20
        },
        "min_divergence_threshold": min_divergence,
        "bearish_divergence": {
            "description": "Price rising but volume declining - rally losing steam, potential reversal",
            "stocks": bearish_div[:top_n]
        },
        "bullish_divergence": {
            "description": "Price falling but volume increasing - accumulation during decline, potential reversal",
            "stocks": bullish_div[:top_n]
        },
        "summary": {
            "bearish_count": len(bearish_div),
            "bullish_count": len(bullish_div),
            "interpretation": "Divergences indicate potential trend reversals - confirm with delivery % and price action"
        }
    }