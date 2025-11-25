"""
Pydantic schemas for structured agent outputs.
Enables reliable data passing between agents in the pipeline.
"""

from typing import Literal

from pydantic import BaseModel, Field


class EntryRouterOutput(BaseModel):
    """Output from Entry/Router Agent - decides how to handle the user query."""

    intent: Literal["greeting", "capability", 
                    "stock_analysis", "out_of_scope", "prompt_injection"] = Field(
        description="Classified intent of user's query"
    )

    should_analyze: bool = Field(
        description="True if query should proceed to stock analysis pipeline, False otherwise"
    )

    direct_response: str | None = Field(
        None,
        description="Direct response for greetings, capabilities, rejections (when should_analyze=False)"
    )

    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen"
    )


class StockPerformance(BaseModel):
    """
    Individual stock performance metrics.
    
    Note: This model is kept for reference/documentation but not used directly
    in schema definitions due to automatic function calling limitations.
    Use dict with these fields instead in list[dict] fields.
    """
    symbol: str = Field(description="Stock ticker symbol (e.g., 'RELIANCE', 'TCS')")
    return_pct: float = Field(description="Percentage return over the analysis period")
    price_start: float = Field(description="Starting price in INR")
    price_end: float = Field(description="Ending price in INR")
    volatility: float = Field(
      description="Daily return standard deviation as percentage")
    delivery_pct: float | None = Field(
      None, description="Average delivery percentage (institutional buying indicator)")


class MarketAnalysisOutput(BaseModel):
    """Structured output from Market Data Agent."""

    # Critical fields for News Agent handoff
    symbols: list[str] = Field(
        description="List of stock symbols analyzed (e.g., ['RELIANCE', 'TCS', 'HDFCBANK'])"
    )
    start_date: str | None = Field(
        None,
        description="Analysis start date in YYYY-MM-DD format (null when skipping analysis)"
    )
    end_date: str | None = Field(
        None,
        description="Analysis end date in YYYY-MM-DD format (null when skipping analysis)"
    )

    # Performance data - flattened to avoid nested schema parsing issues
    top_performers: list = Field(
        description=(
            "List of top performing stocks with metrics. "
            "Each dict contains: symbol (str), return_pct (float), "
            "price_start (float), price_end (float), volatility (float), "
            "delivery_pct (float|null)"
        )
    )

    # Analysis insights
    analysis_summary: str = Field(
        description="Brief summary of key quantitative insights (2-3 sentences)"
    )

    accumulation_patterns: list[str] = Field(
        default=[],
        description="Stocks showing accumulation pattern (high delivery + price up)"
    )

    distribution_patterns: list[str] = Field(
        default=[],
        description="Stocks showing distribution pattern (high delivery + price down)"
    )

    risk_flags: list[str] = Field(
        default=[],
        description="Any anomalies or risks detected (e.g., 'RADIOCITY: 838% return - possible data anomaly')"
    )

    focus_areas: list[str] = Field(
        default=[],
        description="Suggested focus areas for news search (e.g., 'Energy sector strength', 'Banking accumulation')"
    )


class NewsInsight(BaseModel):
    """
    News finding for a single stock.
    
    Note: This model is kept for reference/documentation but not used directly
    in schema definitions due to automatic function calling limitations.
    Use dict with these fields instead in list[dict] fields.
    """
    symbol: str = Field(description="Stock symbol")
    sentiment: str = Field(description="Positive, Negative, or Neutral")
    key_event: str = Field(description="Brief description of the main news event (or 'No significant news')")
    source: str | None = Field(None, description="News source and date")
    correlation: str = Field(
        description="How news correlates with price move: 'Strong Confirmation', 'Divergence', or 'Weak'"
    )


class NewsAnalysisOutput(BaseModel):
    """Structured output from News Agent."""

    news_findings: list = Field(
        description=(
            "News insights for each stock analyzed. "
            "Each dict contains: symbol (str), sentiment (str), "
            "key_event (str), source (str|null), correlation (str)"
        )
    )

    news_driven_stocks: list[str] = Field(
        description="Stocks with strong news catalysts explaining price moves"
    )

    technical_driven_stocks: list[str] = Field(
        description="Stocks moving without clear news (technical/insider activity)"
    )

    overall_sentiment: str = Field(
        description="Overall market sentiment: Bullish, Bearish, or Mixed"
    )

    sector_themes: list[str] = Field(
        default=[],
        description="Broader sector-level themes identified"
    )
