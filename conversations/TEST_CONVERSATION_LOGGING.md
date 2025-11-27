# Testing Conversation Logging

## Quick Test: CLI Mode

```bash
python cli.py
# Ask a question, then exit
python conversations/view_conversations.py
```

## Testing ADK Web Mode

```bash
adk web investor_agent --port=8000
# Use web UI, then stop
python conversations/export_adk_sessions.py
python conversations/view_conversations.py
```
