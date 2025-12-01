"""Investor Paradise Agent - ADK-based stock market analysis agent."""

# Lazy import: only load agent module when explicitly accessed
# This prevents GOOGLE_API_KEY validation when just using CLI tools
def __getattr__(name):
    if name == "agent":
        import importlib
        agent_module = importlib.import_module("investor_agent.agent")
        globals()["agent"] = agent_module
        return agent_module
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["agent"]