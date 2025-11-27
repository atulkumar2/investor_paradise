# Conversation Logging Quickstart

This quickstart has moved into the `conversations/` folder.

## Summary

Conversation logging is available with different levels of support:

### CLI Mode (Real-Time) ✅ Recommended
- How: Logged automatically to `conversations/conversation_history.jsonl`
- Use: `python cli.py`
- Status: Fully working and tested

### ADK Web Mode (Experimental) ⚠️
- How: ADK sessions DB exists, but events may not be persisted
- Use: `python conversations/export_adk_sessions.py`
- Status: Not guaranteed to capture conversation content
- Workaround: Use CLI mode for reliable logging
