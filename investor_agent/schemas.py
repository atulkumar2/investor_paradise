"""
Pydantic schemas for structured agent outputs.
Enables reliable data passing between agents in the pipeline.
"""

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field


def strip_markdown_json(text: str) -> dict[str, Any]:
    """
    Strip markdown code fences and parse JSON.

    LLMs sometimes wrap JSON in ```json ... ``` despite instructions.
    This helper strips wrappers before parsing.

    Raises:
        ValueError: If text is empty or not valid JSON
    """
    if not isinstance(text, str):
        return text

    text = text.strip()

    # Handle empty or whitespace-only responses
    if not text:
        raise ValueError(
            "Empty response from LLM - expected JSON output. "
            "Check if the agent returned SKIP pattern or empty string."
        )

    # Pattern matches: ```json ... ``` or ``` ... ```
    pattern = r'^```(?:json)?\s*\n(.*?)\n```\s*$'
    match = re.match(pattern, text, re.DOTALL)

    if match:
        json_str = match.group(1).strip()
        if not json_str:
            raise ValueError("Empty JSON content inside markdown code fences")
        return json.loads(json_str)

    # Try parsing as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON from LLM: {e}. Raw output (first 200 chars): {text[:200]!r}"
        ) from e


class EntryRouterOutput(BaseModel):
    """Output from Entry/Router Agent - decides how to handle the user query."""

    intent: Literal["greeting", "capability",
                    "stock_analysis", "out_of_scope", "prompt_injection"] = Field(
        description="Classified intent of user's query"
    )

    should_analyze: bool = Field(
        description=(
            "True if query should proceed to stock analysis pipeline, "
            "False otherwise"
        )
    )

    direct_response: str | None = Field(
        None,
        description=(
            "Direct response for greetings, capabilities, rejections "
            "(when should_analyze=False)"
        )
    )

    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen"
    )

    @classmethod
    def model_validate_json(cls, json_data: str | bytes, **kwargs):
        """Override to strip markdown before validation."""
        if isinstance(json_data, (str, bytes)):
            try:
                text = json_data.decode() if isinstance(json_data, bytes) else json_data
                data = strip_markdown_json(text)
                return cls.model_validate(data, **kwargs)
            except ValueError as e:
                raise ValueError(f"{cls.__name__} validation failed: {e}") from e
        return super().model_validate_json(json_data, **kwargs)


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
        description=(
            "List of stock symbols analyzed "
            "(e.g., ['RELIANCE', 'TCS', 'HDFCBANK'])"
        )
    )
    start_date: str | None = Field(
        None,
        description=(
            "Analysis start date in YYYY-MM-DD format "
            "(null when skipping analysis)"
        )
    )
    end_date: str | None = Field(
        None,
        description=(
            "Analysis end date in YYYY-MM-DD format "
            "(null when skipping analysis)"
        )
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
        description=(
            "Any anomalies or risks detected "
            "(e.g., 'RADIOCITY: 838% return - possible data anomaly')"
        )
    )

    focus_areas: list[str] = Field(
        default=[],
        description=(
            "Keywords/themes for news search "
            "(e.g., ['Banking sector', 'TCS institutional buying'])"
        )
    )

    @classmethod
    def model_validate_json(cls, json_data: str | bytes, **kwargs):
        """Override to strip markdown and handle edge cases before validation."""
        if isinstance(json_data, (str, bytes)):
            try:
                text = json_data.decode() if isinstance(json_data, bytes) else json_data

                # Handle empty response - return SKIP pattern
                if not text or not text.strip():
                    return cls(
                        symbols=[],
                        start_date=None,
                        end_date=None,
                        top_performers=[],
                        analysis_summary="SKIP - Empty response from LLM",
                        accumulation_patterns=[],
                        distribution_patterns=[],
                        risk_flags=[
                            "⚠️ Agent returned empty response - check routing logic"
                        ],
                        focus_areas=[]
                    )

                data = strip_markdown_json(text)
                return cls.model_validate(data, **kwargs)
            except ValueError as e:
                # Log the error but return SKIP pattern to prevent pipeline crash
                return cls(
                    symbols=[],
                    start_date=None,
                    end_date=None,
                    top_performers=[],
                    analysis_summary=f"SKIP - Validation error: {str(e)[:100]}",
                    accumulation_patterns=[],
                    distribution_patterns=[],
                    risk_flags=[f"⚠️ {cls.__name__} validation failed: {str(e)[:200]}"],
                    focus_areas=[]
                )
        return super().model_validate_json(json_data, **kwargs)


class NewsInsight(BaseModel):
    """
    News finding for a single stock.

    Note: This model is kept for reference/documentation but not used directly
    in schema definitions due to automatic function calling limitations.
    Use dict with these fields instead in list[dict] fields.
    """
    symbol: str = Field(description="Stock symbol")
    sentiment: str = Field(description="Positive, Negative, or Neutral")
    key_event: str = Field(
        description=(
            "Brief description of the main news event "
            "(or 'No significant news')"
        )
    )
    source: str | None = Field(None, description="News source and date")
    correlation: str = Field(
        description=(
            "How news correlates with price move: "
            "'Strong Confirmation', 'Divergence', or 'Weak'"
        )
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
