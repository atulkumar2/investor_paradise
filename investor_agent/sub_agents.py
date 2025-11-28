from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search
from typing import Optional
from investor_agent import tools
from investor_agent import schemas
from investor_agent.data_engine import NSESTORE
from investor_agent.logger import get_logger
from investor_agent.prompts import (
    ENTRY_ROUTER_PROMPT,
    get_market_agent_prompt,
    PDF_NEWS_SCOUT_PROMPT,
    WEB_NEWS_RESEARCHER_PROMPT,
    MERGER_AGENT_PROMPT,
)

logger = get_logger(__name__)


def create_analysis_pipeline(
    market_model: Gemini,
    news_model: Gemini,
    merger_model: Gemini
) -> SequentialAgent:
    """
    Creates the analysis sub-pipeline with parallel news gathering.
    
    Architecture:
        Market → [PDF News Scout || Web News Researcher] → CIO
        ├─ Faster (both news agents run simultaneously)
        ├─ PDFNewsScout: Searches in-house PDF database (RAG/semantic search)
        ├─ WebNewsResearcher: Searches real-time web news (Google)
        └─ More efficient use of API quota
    
    Args:
        market_model: Gemini model for market analysis
        news_model: Gemini model for news agents
        merger_model: Gemini model for final synthesis
    """
    logger.info("Creating analysis pipeline with parallel news gathering")
    context_str = NSESTORE.get_data_context()
    
    # Market Agent
    logger.debug("Creating MarketAnalyst agent")
    market_prompt = get_market_agent_prompt(context_str)
    market_agent = LlmAgent(
        name="MarketAnalyst",
        model=market_model,
        instruction=market_prompt,
        output_schema=schemas.MarketAnalysisOutput,
        output_key="market_analysis",
        tools=[
            # Utility Tools
            tools.list_available_tools,
            tools.check_data_availability,
            # Core Analysis Tools
            tools.get_top_gainers,
            tools.get_top_losers,
            tools.get_sector_top_performers,
            tools.analyze_stock,
            # Index & Market Cap Tools (NEW)
            tools.get_index_constituents,
            tools.list_available_indices,
            tools.get_sectoral_indices,
            tools.get_sector_from_index,
            tools.get_stocks_by_sector_index,
            tools.get_stocks_by_market_cap,
            tools.get_market_cap_category,
            tools.get_sector_stocks,
            # Advanced Pattern Detection Tools
            tools.detect_volume_surge,
            tools.compare_stocks,
            tools.get_delivery_momentum,
            tools.detect_breakouts,
            tools.get_52week_high_low,
            tools.analyze_risk_metrics,
            tools.find_momentum_stocks,
            tools.detect_reversal_candidates,
            tools.get_volume_price_divergence
        ]
    )

    # PDF News Scout (Local RAG Search - In-House News Database)
    logger.debug("Creating PDFNewsScout agent")
    pdf_news_scout = LlmAgent(
        name="PDFNewsScout",
        model=news_model,
        instruction=PDF_NEWS_SCOUT_PROMPT,
        tools=[
            tools.get_company_name,
            tools.load_collections_for_date_range,
            tools.semantic_search
        ]  # Symbol-to-name mapping + Date-aware loading + search
    )

    # Web News Researcher (Google Search - Real-time Web News)
    logger.debug("Creating WebNewsResearcher agent")
    web_news_researcher = LlmAgent(
        name="WebNewsResearcher",
        model=news_model,
        instruction=WEB_NEWS_RESEARCHER_PROMPT,
        tools=[google_search]  # Only google_search (infers company names from context)
    )

    # Merger Agent
    logger.debug("Creating CIO_Synthesizer agent")
    merger_agent = LlmAgent(
        name="CIO_Synthesizer",
        model=merger_model,
        instruction=MERGER_AGENT_PROMPT
    )

    # PARALLEL: Both news agents run simultaneously
    news_intelligence_agent = ParallelAgent(
        name="NewsIntelligence",
        sub_agents=[pdf_news_scout, web_news_researcher],
        description="Parallel news gathering: In-house PDF database + Real-time web search"
    )
    
    pipeline = SequentialAgent(
        name="AnalysisPipeline",
        sub_agents=[market_agent, news_intelligence_agent, merger_agent],
        description="Market Analysis → [PDF News Database || Web News Search] → Final Report"
    )
    logger.info("Analysis pipeline created successfully")
    
    return pipeline


def create_entry_router_root(
    entry_model: Gemini,
    market_model: Gemini,
    news_model: Gemini,
    merger_model: Gemini
) -> LlmAgent:
    """
    Creates EntryRouter as root agent with analysis pipeline as a tool.
    
    Architecture:
    EntryRouter (root LlmAgent)
      └── AnalysisPipeline (SequentialAgent)
           ├── MarketAnalyst
           ├── NewsIntelligence (ParallelAgent)
           │    ├── PDFNewsScout (in-house PDF database via RAG)
           │    └── WebNewsResearcher (real-time Google search)
           └── CIO_Synthesizer
    
    Benefits:
    - EventsCompactionConfig works (single LlmAgent root)
    - Cleaner separation: routing vs analysis
    - Can skip pipeline for greetings (faster)
    - Parallel news gathering (25% faster)
    
    Args:
        entry_model: Model for entry router
        market_model: Model for market analysis
        news_model: Model for news agents
        merger_model: Model for final synthesis
    """
    logger.info("Creating EntryRouter as root agent")
    # Create analysis pipeline with parallel news option
    analysis_pipeline = create_analysis_pipeline(
        market_model, 
        news_model, 
        merger_model
    )
    
    # Entry Router with analysis pipeline as sub-agent (not tool)
    # This allows visibility into individual agents and their tool calls
    entry_router = LlmAgent(
        name="EntryRouter",
        model=entry_model,
        instruction=ENTRY_ROUTER_PROMPT,
        sub_agents=[analysis_pipeline]  # Direct sub-agent for visibility
    )
    logger.info("EntryRouter created with AnalysisPipeline as sub-agent")
    
    return entry_router


def create_pipeline(
    model: Optional[Gemini] = "gemini-2.5-flash-lite",
    entry_model: Optional[Gemini] = None,
    market_model: Optional[Gemini] = None,
    news_model: Optional[Gemini] = None,
    merger_model: Optional[Gemini] = None
) -> LlmAgent:
    """
    Creates the agent architecture.
    
    Args:
        model: Default Gemini model for all agents
        entry_model: Optional separate model for Entry/Router Agent
        market_model: Optional separate model for Market Analyst
        news_model: Optional separate model for News Analyst
        merger_model: Optional separate model for CIO/Merger Agent
    
    Returns:
        Root agent (EntryRouter)
    """
    # Use provided models or fall back to default
    entry_model = entry_model or model
    market_model = market_model or model
    news_model = news_model or model
    merger_model = merger_model or model
    

    return create_entry_router_root(entry_model, market_model, news_model, merger_model)