"""Agent prompts organized into modular files."""

from investor_agent.prompts.entry_router_prompt import ENTRY_ROUTER_PROMPT
from investor_agent.prompts.market_agent_prompt import get_market_agent_prompt
from investor_agent.prompts.pdf_news_prompt import PDF_NEWS_SCOUT_PROMPT
from investor_agent.prompts.web_news_prompt import WEB_NEWS_RESEARCHER_PROMPT
from investor_agent.prompts.merger_prompt import MERGER_AGENT_PROMPT

__all__ = [
    "ENTRY_ROUTER_PROMPT",
    "get_market_agent_prompt",
    "PDF_NEWS_SCOUT_PROMPT",
    "WEB_NEWS_RESEARCHER_PROMPT",
    "MERGER_AGENT_PROMPT",
]
