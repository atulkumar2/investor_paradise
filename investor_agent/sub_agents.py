from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search
from typing import Optional
from investor_agent import prompts
from investor_agent import tools
from investor_agent import schemas
from investor_agent.data_engine import NSESTORE


def create_analysis_pipeline(
    market_model: Gemini,
    news_model: Gemini,
    merger_model: Gemini
) -> SequentialAgent:
    """
    Creates the analysis sub-pipeline (Market → News → CIO).
    This runs only when should_analyze=True.
    """
    context_str = NSESTORE.get_data_context()
    
    # Market Agent
    market_prompt = prompts.get_market_agent_prompt(context_str)
    market_agent = LlmAgent(
        name="MarketAnalyst",
        model=market_model,
        instruction=market_prompt,
        output_schema=schemas.MarketAnalysisOutput,
        output_key="market_analysis",
        tools=[
            tools.list_available_tools,
            tools.check_data_availability,
            tools.get_top_gainers,
            tools.get_top_losers,
            tools.get_sector_top_performers,
            tools.analyze_stock,
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

    # News Agent
    news_agent = LlmAgent(
        name="NewsAnalyst",
        model=news_model,
        instruction=prompts.NEWS_AGENT_PROMPT,
        tools=[google_search]
    )

    # Merger Agent
    merger_agent = LlmAgent(
        name="CIO_Synthesizer",
        model=merger_model,
        instruction=prompts.MERGER_AGENT_PROMPT
    )

    # Sequential Pipeline
    pipeline = SequentialAgent(
        name="AnalysisPipeline",
        sub_agents=[market_agent, news_agent, merger_agent],
        description="Market Analysis → News Context → Final Report"
    )
    
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
      └── run_analysis (AgentTool)
           └── SequentialAgent (Market → News → CIO)
    
    Benefits:
    - EventsCompactionConfig works (single LlmAgent root)
    - Cleaner separation: routing vs analysis
    - Can skip pipeline for greetings (faster)
    """
    # Create analysis pipeline
    analysis_pipeline = create_analysis_pipeline(market_model, news_model, merger_model)
    
    # Entry Router with analysis pipeline as sub-agent (not tool)
    # This allows visibility into individual agents and their tool calls
    entry_router = LlmAgent(
        name="EntryRouter",
        model=entry_model,
        instruction=prompts.ENTRY_ROUTER_PROMPT,
        sub_agents=[analysis_pipeline]  # Direct sub-agent for visibility
    )
    
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
        use_new_architecture: If True, uses EntryRouter-as-root (enables compaction)
    
    Returns:
        Root agent (EntryRouter if new architecture, SequentialAgent if old)
    """
    # Use provided models or fall back to default
    entry_model = entry_model or model
    market_model = market_model or model
    news_model = news_model or model
    merger_model = merger_model or model
    
    return create_entry_router_root(entry_model, market_model, news_model, merger_model)
