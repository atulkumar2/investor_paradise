"""Core Stock Analysis Tools

This module contains fundamental stock analysis functions:
- Data availability checking
- Top gainers/losers discovery
- Sector-specific analysis
- Individual stock deep-dive analysis
- Stock comparison
"""

from datetime import datetime, timedelta, date
from typing import Optional

from investor_agent.data_engine import NSESTORE
from investor_agent.logger import get_logger
from investor_agent.tools.indices_tools import get_sector_stocks

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


