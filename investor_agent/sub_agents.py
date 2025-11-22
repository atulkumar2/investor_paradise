from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search
from typing import Optional
from investor_agent import prompts
from investor_agent import tools
from investor_agent import schemas
from investor_agent.data_engine import NSESTORE

def create_pipeline(
    model: Optional[Gemini] = "gemini-2.5-flash-lite",
    entry_model: Optional[Gemini] = "gemini-2.5-flash-lite",
    market_model: Optional[Gemini] = "gemini-2.5-flash-lite",
    news_model: Optional[Gemini] = "gemini-2.5-flash-lite",
    merger_model: Optional[Gemini] = "gemini-2.5-flash-lite"
) -> SequentialAgent:
    """
    Creates the full pipeline with Entry Agent as first step.
    
    Args:
        model: Default Gemini model for all agents
        entry_model: Optional separate model for Entry/Router Agent
        market_model: Optional separate model for Market Analyst
        news_model: Optional separate model for News Analyst
        merger_model: Optional separate model for CIO/Merger Agent
    
    Flow:
    1. EntryRouter: Classifies intent, sets routing_decision in context
    2. MarketAnalyst: Checks routing_decision, conditionally analyzes stocks
    3. NewsAnalyst: Checks if market analysis ran, conditionally searches news
    4. CIO_Synthesizer: Returns direct_response or synthesizes analysis
    
    All agents receive context from previous steps via SequentialAgent.
    
    Example:
        # Use same model for all agents
        pipeline = create_pipeline(gemini_flash)
        
        # Use different models for different agents
        pipeline = create_pipeline(
            model=gemini_flash,
            market_model=gemini_pro,  # Use Pro for complex analysis
            merger_model=gemini_pro   # Use Pro for synthesis
        )
    """
    # Use provided models or fall back to default
    entry_model = entry_model or model
    market_model = market_model or model
    news_model = news_model or model
    merger_model = merger_model or model
    
    # 1. Get Data Context String
    context_str = NSESTORE.get_data_context()
    
    # 2. Entry/Router Agent - First point of contact
    entry_agent = LlmAgent(
        name="EntryRouter",
        model=entry_model,
        instruction=prompts.ENTRY_ROUTER_PROMPT,
        output_schema=schemas.EntryRouterOutput,
        output_key="routing_decision",  # Available to all downstream agents
        tools=[]  # No tools needed, just intent classification
    )
    
    # 3. Market Agent - Conditionally analyzes based on routing_decision
    market_prompt = prompts.get_market_agent_prompt(context_str)
    market_agent = LlmAgent(
        name="MarketAnalyst",
        model=market_model,
        instruction=market_prompt,
        output_schema=schemas.MarketAnalysisOutput,
        output_key="market_analysis",
        tools=[
            # Utility
            tools.list_available_tools,
            tools.check_data_availability,
            # Phase 1: Core Analysis Tools
            tools.get_top_gainers,
            tools.get_top_losers,
            tools.analyze_stock,
            tools.get_sector_top_performers,
            # Phase 2: Advanced Analysis Tools
            tools.detect_volume_surge,
            tools.compare_stocks,
            tools.get_delivery_momentum,
            tools.detect_breakouts,
            # Phase 3: Professional Trading Tools
            tools.get_52week_high_low,
            tools.analyze_risk_metrics,
            tools.find_momentum_stocks,
            tools.detect_reversal_candidates,
            tools.get_volume_price_divergence
        ]
    )

    # 4. News Agent - Conditionally searches based on market_analysis
    news_agent = LlmAgent(
        name="NewsAnalyst",
        model=news_model,
        instruction=prompts.NEWS_AGENT_PROMPT,
        tools=[google_search]
    )

    # 5. Merger Agent - Returns direct_response or synthesizes analysis
    merger_agent = LlmAgent(
        name="CIO_Synthesizer",
        model=merger_model,
        instruction=prompts.MERGER_AGENT_PROMPT
    )

    # 6. Sequential Pipeline - Entry → Market → News → Merger
    pipeline = SequentialAgent(
        name="InvestorParadisePipeline",
        sub_agents=[entry_agent, market_agent, news_agent, merger_agent],
        description="Intent Classification → Market Analysis → News Context → Final Report"
    )
    
    return pipeline