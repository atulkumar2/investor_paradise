from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search
from investor_agent import prompts
from investor_agent import tools
from investor_agent import schemas
from investor_agent.data_engine import STORE

def create_pipeline(model: Gemini) -> SequentialAgent:
    """
    Creates the full pipeline with Entry Agent as first step.
    
    Flow:
    1. EntryRouter: Classifies intent, sets routing_decision in context
    2. MarketAnalyst: Checks routing_decision, conditionally analyzes stocks
    3. NewsAnalyst: Checks if market analysis ran, conditionally searches news
    4. CIO_Synthesizer: Returns direct_response or synthesizes analysis
    
    All agents receive context from previous steps via SequentialAgent.
    """
    # 1. Get Data Context String
    context_str = STORE.get_data_context()
    
    # 2. Entry/Router Agent - First point of contact
    entry_agent = LlmAgent(
        name="EntryRouter",
        model=model,
        instruction=prompts.ENTRY_ROUTER_PROMPT,
        output_schema=schemas.EntryRouterOutput,
        output_key="routing_decision",  # Available to all downstream agents
        tools=[]  # No tools needed, just intent classification
    )
    
    # 3. Market Agent - Conditionally analyzes based on routing_decision
    market_prompt = prompts.get_market_agent_prompt(context_str)
    market_agent = LlmAgent(
        name="MarketAnalyst",
        model=model,
        instruction=market_prompt,
        output_schema=schemas.MarketAnalysisOutput,
        output_key="market_analysis",
        tools=[
            tools.check_data_availability, 
            tools.get_top_gainers,
            tools.get_top_losers,
            tools.analyze_stock
        ]
    )

    # 4. News Agent - Conditionally searches based on market_analysis
    news_agent = LlmAgent(
        name="NewsAnalyst",
        model=model,
        instruction=prompts.NEWS_AGENT_PROMPT,
        tools=[google_search]
    )

    # 5. Merger Agent - Returns direct_response or synthesizes analysis
    merger_agent = LlmAgent(
        name="CIO_Synthesizer",
        model=model,
        instruction=prompts.MERGER_AGENT_PROMPT
    )

    # 6. Sequential Pipeline - Entry → Market → News → Merger
    pipeline = SequentialAgent(
        name="InvestorParadisePipeline",
        sub_agents=[entry_agent, market_agent, news_agent, merger_agent],
        description="Intent Classification → Market Analysis → News Context → Final Report"
    )
    
    return pipeline