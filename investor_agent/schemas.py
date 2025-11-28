"""
Pydantic schemas for structured agent outputs.
Enables reliable data passing between agents in the pipeline.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class EntryRouterOutput(BaseModel):
    """Output from Entry/Router Agent - decides how to handle the user query."""
    
    intent: Literal["greeting", "capability", "stock_analysis", "out_of_scope", "prompt_injection"] = Field(
        description="Classified intent of user's query"
    )
    
    should_analyze: bool = Field(
        description="True if query should proceed to stock analysis pipeline, False otherwise"
    )
    
    direct_response: Optional[str] = Field(
        None,
        description="Direct response for greetings, capabilities, rejections (when should_analyze=False)"
    )
    
    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen"
    )


class StockPerformance(BaseModel):
    """Individual stock performance metrics."""
    symbol: str = Field(description="Stock ticker symbol (e.g., 'RELIANCE', 'TCS')")
    return_pct: float = Field(description="Percentage return over the analysis period")
    price_start: float = Field(description="Starting price in INR")
    price_end: float = Field(description="Ending price in INR")
    volatility: Optional[float] = Field(None, description="Daily return standard deviation as percentage (None if not calculated)")
    delivery_pct: Optional[float] = Field(None, description="Average delivery percentage (institutional buying indicator)")


class MarketAnalysisOutput(BaseModel):
    """Structured output from Market Data Agent."""
    
    # Critical fields for News Agent handoff
    symbols: List[str] = Field(
        description="List of stock symbols analyzed (e.g., ['RELIANCE', 'TCS', 'HDFCBANK'])"
    )
    start_date: Optional[str] = Field(
        None,
        description="Analysis start date in YYYY-MM-DD format (null when skipping analysis)"
    )
    end_date: Optional[str] = Field(
        None,
        description="Analysis end date in YYYY-MM-DD format (null when skipping analysis)"
    )
    
    # Performance data
    top_performers: List[StockPerformance] = Field(
        default=[],
        description="List of top performing stocks with metrics (empty when skipping analysis)"
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
    event_type: Optional[str] = Field(
        None,
        description="Category of event: 'Earnings', 'M&A', 'Block Deal', 'SEBI Action', 'Corporate Action', 'Analyst Rating', 'Sector', 'Macro', 'Circuit', or 'None'"
    )
    news_date: Optional[str] = Field(
        None,
        description="Exact date of news event in YYYY-MM-DD format (if found)"
    )
    corporate_action: Optional[str] = Field(
        None,
        description="Corporate action details if applicable (e.g., '2:1 Bonus', '1:10 Split', 'Rs 5 Dividend')"
    )
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
