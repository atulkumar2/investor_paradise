from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from investor_agent import prompts
from investor_agent import tools
from investor_agent.data_engine import STORE

def create_pipeline(model: Gemini) -> SequentialAgent:
    # 1. Get Data Context String (e.g., "DATA RANGE: 2024-01-01 to 2025-11-18")
    context_str = STORE.get_data_context()
    
    # 2. Market Agent (The Doer)
    market_prompt = prompts.get_market_agent_prompt(context_str)
    market_agent = LlmAgent(
        name="MarketAnalyst",
        model=model,
        instruction=market_prompt,
        # Direct tool access
        tools=[tools.rank_market_performance, tools.analyze_single_stock]
    )

    # 3. News Agent (The Context - Sequential)
    # Runs AFTER Market Agent, sees Market Agent's output in context
    news_agent = LlmAgent(
        name="NewsAnalyst",
        model=model,
        instruction=prompts.NEWS_AGENT_PROMPT
    )

    # 4. Merger Agent (The Writer)
    merger_agent = LlmAgent(
        name="CIO_Synthesizer",
        model=model,
        instruction=prompts.MERGER_AGENT_PROMPT
    )

    # 5. Sequential Pipeline (Stable)
    # Market -> News -> Merger
    root_agent = SequentialAgent(
        name="InvestorCopilot",
        sub_agents=[market_agent, news_agent, merger_agent],
        description="Sequential workflow: Data -> Context -> Report"
    )
    
    return root_agent