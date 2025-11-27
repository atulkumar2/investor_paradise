"""
Animated Spinner for Agent Progress Tracking

Provides smooth Braille spinner animation with real-time status updates
for agent and tool execution.
"""

import asyncio
from rich.live import Live
from cli_helpers import console, AGENT_STATUS, TOOL_STATUS


async def process_query_with_spinner(runner, user_id, session_id, user_message,
                                     spinner_frames, tracker, token_tracker,
                                     displayed_agents, displayed_tools):
    """Process a query with animated spinner showing agent and tool progress.
    
    Args:
        runner: ADK Runner instance
        user_id: User identifier
        session_id: Session identifier
        user_message: User's message content
        spinner_frames: List of spinner animation frames (e.g., Braille patterns)
        tracker: AgentProgressTracker instance
        token_tracker: TokenTracker instance
        displayed_agents: Set to track which agents have been shown
        displayed_tools: Set to track which tools have been shown
    
    Returns:
        str: The final response text from the agent
    """
    spinner_index = [0]  # Use list to allow modification in nested function
    spinner = spinner_frames[0]
    current_status = ["🧭 Understanding your request"]  # Use list for mutation
    final_text = ""
    should_analyze = True
    animation_running = [True]  # Use list for mutation in nested function
    
    async def animate_spinner(live):
        """Background task to keep spinner animated at 10 FPS."""
        while animation_running[0]:
            spinner_index[0] = (spinner_index[0] + 1) % len(spinner_frames)
            spinner = spinner_frames[spinner_index[0]]
            live.update(f"[bold cyan]{spinner}[/bold cyan] [dim]{current_status[0]}...[/dim]")
            await asyncio.sleep(0.1)  # 10 FPS = smooth animation
    
    with Live(console=console, refresh_per_second=10, transient=True) as live:
        # Start with initial spinner
        live.update(f"[bold cyan]{spinner}[/bold cyan] [dim]{current_status[0]}...[/dim]")
        
        # Start background animation task for smooth continuous animation
        animation_task = asyncio.create_task(animate_spinner(live))
        
        try:
            # Run the full pipeline with live status updates
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message
            ):
                # Track token usage per model
                if hasattr(event, 'usage_metadata') and event.usage_metadata:
                    usage = event.usage_metadata
                    
                    # Get model name from agent (use 'author' field)
                    model_name = "unknown"
                    if hasattr(event, 'author') and event.author:
                        model_name = token_tracker.get_model_from_agent(event.author)
                    
                    # Track usage
                    if hasattr(usage, 'prompt_token_count') and hasattr(usage, 'candidates_token_count'):
                        token_tracker.add_usage(
                            model_name,
                            usage.prompt_token_count,
                            usage.candidates_token_count
                        )
                
                # Update status message based on agent
                if hasattr(event, 'author') and event.author and event.author not in displayed_agents:
                    displayed_agents.add(event.author)
                    
                    # Use centralized agent messages from cli_helpers
                    if event.author in AGENT_STATUS:
                        msg, _ = AGENT_STATUS[event.author]
                        current_status[0] = msg
                    else:
                        current_status[0] = f"⚙️ {event.author}"
                    tracker.start_agent(event.author)
                
                # Detect compaction events for logging
                if hasattr(event, 'actions') and event.actions and hasattr(event.actions, 'compaction'):
                    if event.actions.compaction is not None:
                        console.print(f"\n[dim yellow]📦 Context compacted: {event.actions.compaction.start_timestamp:.2f} → {event.actions.compaction.end_timestamp:.2f}[/dim yellow]")
                
                # Detect function calls (tools) in event content
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            func_call = part.function_call
                            tool_name = func_call.name if hasattr(func_call, 'name') else str(func_call)
                            
                            tracker.add_tool(tool_name)
                            
                            # Show tool-specific messages (only once per tool)
                            if tool_name not in displayed_tools:
                                displayed_tools.add(tool_name)
                                # Print tool message outside Live display so it persists
                                if tool_name in TOOL_STATUS:
                                    msg, color = TOOL_STATUS[tool_name]
                                    console.print(f"  [dim {color}]→ {msg}[/dim {color}]")
                                    current_status[0] = msg
                                # else:
                                #     console.print(f"  [dim]→ 🔧 Using {tool_name}[/dim]")
                                #     current_status[0] = f"🔧 Using {tool_name}"
                
                # Detect content and check for analysis type
                if event.content and event.content.parts:
                    content = event.content.parts[0].text
                    if content and content.strip():
                        final_text = content
                        
                        # Detect if this is a greeting/capability response (no markdown report)
                        if "# 🚀 Investor Paradise" not in content:
                            should_analyze = False
                        else:
                            should_analyze = True
                
                # Handle early exit
                if event.is_final_response():
                    # If this is a non-analysis response (greeting, capability), stop here
                    if hasattr(event, 'author') and event.author == "EntryRouter":
                        if should_analyze is False:
                            break
                    # For stock analysis, wait for completion
                    elif should_analyze is True:
                        break
        finally:
            # Stop animation
            animation_running[0] = False
            animation_task.cancel()
            try:
                await animation_task
            except asyncio.CancelledError:
                pass
    
    return final_text
