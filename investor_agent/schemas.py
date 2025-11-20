"""
Pydantic schemas for structured agent outputs.
Enables reliable data passing between agents in the pipeline.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class StockPerformance(BaseModel):
    """Individual stock performance metrics."""
    symbol: str = Field(description="Stock ticker symbol (e.g., 'RELIANCE', 'TCS')")
    return_pct: float = Field(description="Percentage return over the analysis period")
    price_start: float = Field(description="Starting price")
    price_end: float = Field(description="Ending price")
    volatility: float = Field(description="Volatility metric")
    delivery_pct: Optional[float] = Field(None, description="Delivery percentage (if available)")


class MarketAnalysisOutput(BaseModel):
    """Structured output from Market Data Agent."""
    
    # Critical fields for News Agent handoff
    symbols: List[str] = Field(
        description="List of stock symbols analyzed (e.g., ['RELIANCE', 'TCS', 'HDFCBANK'])"
    )
    start_date: str = Field(
        description="Analysis start date in YYYY-MM-DD format"
    )
    end_date: str = Field(
        description="Analysis end date in YYYY-MM-DD format"
    )
    
    # Performance data
    top_performers: List[StockPerformance] = Field(
        description="List of top performing stocks with metrics"
    )
    
    # Analysis insights
    analysis_summary: str = Field(
        description="Brief summary of key quantitative insights (2-3 sentences)"
    )
    
    accumulation_patterns: List[str] = Field(
        default=[],
        description="Stocks showing accumulation pattern (high delivery + price up)"
    )
    
    distribution_patterns: List[str] = Field(
        default=[],
        description="Stocks showing distribution pattern (high delivery + price down)"
    )
    
    risk_flags: List[str] = Field(
        default=[],
        description="Any anomalies or risks detected (e.g., 'RADIOCITY: 838% return - possible data anomaly')"
    )
    
    focus_areas: List[str] = Field(
        default=[],
        description="Suggested focus areas for news search (e.g., 'Energy sector strength', 'Banking accumulation')"
    )


class NewsInsight(BaseModel):
    """News finding for a single stock."""
    symbol: str = Field(description="Stock symbol")
    sentiment: str = Field(description="Positive, Negative, or Neutral")
    key_event: str = Field(description="Brief description of the main news event (or 'No significant news')")
    source: Optional[str] = Field(None, description="News source and date")
    correlation: str = Field(
        description="How news correlates with price move: 'Strong Confirmation', 'Divergence', or 'Weak'"
    )


class NewsAnalysisOutput(BaseModel):
    """Structured output from News Agent."""
    
    news_findings: List[NewsInsight] = Field(
        description="News insights for each stock analyzed"
    )
    
    news_driven_stocks: List[str] = Field(
        description="Stocks with strong news catalysts explaining price moves"
    )
    
    technical_driven_stocks: List[str] = Field(
        description="Stocks moving without clear news (technical/insider activity)"
    )
    
    overall_sentiment: str = Field(
        description="Overall market sentiment: Bullish, Bearish, or Mixed"
    )
    
    sector_themes: List[str] = Field(
        default=[],
        description="Broader sector-level themes identified"
    )