import os
import asyncio
from dotenv import load_dotenv
import httpx
from rich.panel import Panel
from rich.markdown import Markdown

# --- SSL Patch (Required for your environment) ---
original_init = httpx.AsyncClient.__init__
def patched_init(self, *args, **kwargs):
    kwargs['verify'] = False
    original_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = patched_init
# -------------------------------------------------

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.apps.app import App, EventsCompactionConfig
from google.genai import types

from investor_agent.sub_agents import create_pipeline
from investor_agent.data_engine import NSESTORE
from cli_helpers import (
    AgentProgressTracker,
    TokenTracker,
    get_or_create_user_id,
    console,
    select_or_create_session,
)
from custom_session_service import FixedDatabaseSessionService
from spinner import process_query_with_spinner


async def main():
    console.print("\n[bold cyan]🚀 Initializing Investor Paradise...[/bold cyan]")
    
    # 1. Pre-load Data with spinner
    with console.status("[bold blue]📂 Loading NSE stock data...[/bold blue]", spinner="dots"):
        _ = NSESTORE.df
    
    console.print(f"[green]✅ Data loaded: {len(NSESTORE.df):,} rows[/green]")
    console.print(f"[cyan]📅 Database Context: {NSESTORE.get_data_context()}[/cyan]")

    # 2. Initialize Models
    model = Gemini(model="gemini-2.5-flash-lite", api_key=API_KEY)
    flash_model = Gemini(model="gemini-2.5-flash", api_key=API_KEY)
    pro_model = Gemini(model="gemini-2.5-pro", api_key=API_KEY)

    # Create pipeline with multiple models for different agents
    root_agent = create_pipeline(
        entry_model=model,        # Flash-Lite for Entry (simple classification)
        market_model=flash_model, # Flash for Market (complex analysis with tools)
        news_model=model,         # Flash-Lite for News (simple google search)
        merger_model=flash_model # Flash for Merger (report synthesis)
    )
    
    # Override root_agent's module to fix session resume issues
    root_agent.__module__ = "cli"

    # 3. Create App with EventsCompactionConfig
    app = App(
        name="investor_agent",  # Must match directory name
        root_agent=root_agent,
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=3,  # Compact history every 3 turns
            overlap_size=1          # Keep last turn for context
        )
    )

    # 4. Setup Session Service & Runner
    db_path = "investor_agent/data/sessions.db"
    
    db_url = f"sqlite+aiosqlite:///{db_path}"
    # Use custom session service that fixes EventCompaction deserialization
    session_service = FixedDatabaseSessionService(db_url=db_url)
    
    runner = Runner(
        app=app,  # Use App instead of agent directly
        session_service=session_service
    )
    
    # 5. Get persistent user_id (not session_id)
    user_id = get_or_create_user_id()
    console.print(f"[cyan]👤 User ID: {user_id[:8]}...[/cyan]")
    
    # 6. Interactive session selection (sessions stored in DatabaseSessionService)
    session_id = await select_or_create_session(session_service, "investor_agent", user_id)

    console.print("\n[bold green]💬 Ready! Ask me about NSE stocks or just say hi![/bold green]")
    console.print(f"[dim]Session: {session_id[:8]}... | Commands: 'exit', 'clear', 'switch'[/dim]\n")
    
    query_count = 0
    
    while True:
        try:
            user_input = console.input("\n[bold cyan]💭 You:[/bold cyan] ")
            
            if user_input.lower() in ["exit", "quit", "bye"]: 
                console.print("[yellow]👋 Goodbye! Happy investing![/yellow]")
                break
            
            # Handle switch command - change to different session
            if user_input.lower() == "switch":
                session_id = await select_or_create_session(session_service, "investor_agent", user_id)
                query_count = 0
                # Reset root_agent module to fix session app name mismatch
                root_agent.__module__ = "cli"
                console.print(f"[green]✅ Switched to session: {session_id[:8]}...[/green]")
                console.print(f"[dim]Session: {session_id[:8]}... | Commands: 'exit', 'clear', 'switch'[/dim]\n")
                continue
            
            # Handle clear command - reset current session
            if user_input.lower() == "clear":
                try:
                    await session_service.delete_session(
                        app_name="investor_paradise",
                        user_id=user_id,
                        session_id=session_id
                    )
                    await session_service.create_session(
                        app_name="investor_paradise",
                        user_id=user_id,
                        session_id=session_id
                    )
                    query_count = 0
                    console.print("[yellow]🗑️  Session history cleared! Starting fresh.[/yellow]")
                except Exception as e:
                    console.print(f"[red]⚠️  Could not clear session: {e}[/red]")
                continue
            
            console.print()  # Blank line for separation
            
            query_count += 1
            
            user_message = types.Content(role="user", parts=[types.Part(text=user_input)])
            
            # Initialize trackers
            tracker = AgentProgressTracker()
            token_tracker = TokenTracker()
            final_text = ""
            should_analyze = None  # Track routing decision
            displayed_agents = set()  # Track which agents we've shown to avoid repetition
            displayed_tools = set()  # Track displayed tools to avoid repetition
            current_status = "Processing..."
            
            # Spinner frames for smooth animation
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner_index = 0
            
            console.print()  # Always add blank line before processing
            
            # Use Live display for animated spinner
            try:
                final_text = await process_query_with_spinner(
                    runner, user_id, session_id, user_message, 
                    spinner_frames, tracker, token_tracker, 
                    displayed_agents, displayed_tools
                )
            except AttributeError as e:
                if "'dict' object has no attribute 'start_timestamp'" in str(e):
                    console.print("[yellow]⚠️ This session has incompatible data format.[/yellow]")
                    console.print("[yellow]Creating a new session...[/yellow]\n")
                    session_id = await select_or_create_session(session_service, "investor_agent", user_id, force_new=True)
                    console.print(f"[green]✅ New session created: {session_id[:8]}...[/green]\n")
                    # Retry with new session
                    displayed_agents.clear()
                    displayed_tools.clear()
                    final_text = await process_query_with_spinner(
                        runner, user_id, session_id, user_message,
                        spinner_frames, tracker, token_tracker,
                        displayed_agents, displayed_tools
                    )
                else:
                    raise
            
            # Process and display final response
            if final_text and isinstance(final_text, str) and final_text.strip():
                # Check if this is a markdown report (stock analysis)
                is_markdown_report = "# 🚀 Investor Paradise" in final_text
                
                if is_markdown_report:
                    # Stock analysis report - render as markdown
                    console.print("\n")
                    console.print(Panel(
                        Markdown(final_text),
                        title="[bold green]📊 Investment Analysis Report[/bold green]",
                        border_style="green",
                        padding=(1, 2)
                    ))
                else:
                    # Greeting, capability, or other non-analysis response
                    # Determine response type for styling based on content
                    lower_text = final_text.lower()
                    if "hello" in lower_text or "hi" in lower_text or "paradise" in lower_text:
                        title = "[bold cyan]💬 Assistant[/bold cyan]"
                        border = "cyan"
                    elif "can help" in lower_text or "capabilities" in lower_text or "specialize" in lower_text:
                        title = "[bold blue]ℹ️  Capabilities[/bold blue]"
                        border = "blue"
                    elif "cannot" in lower_text or "can't" in lower_text or "don't" in lower_text:
                        title = "[bold yellow]⚠️  Notice[/bold yellow]"
                        border = "yellow"
                    else:
                        title = "[bold green]💬 Assistant[/bold green]"
                        border = "green"
                    
                    # Render as markdown
                    console.print("\n")
                    console.print(Panel(
                        Markdown(final_text),
                        title=title,
                        border_style=border,
                        padding=(1, 2)
                    ))
                
                # Display processing time and token usage
                elapsed_time = tracker.get_summary()  # Returns "Completed in X.Xs"
                token_summary = token_tracker.get_summary(show_cost=True)
                
                if token_summary:
                    console.print(f"[dim]{token_summary}[/dim]")
                console.print(f"[dim]{elapsed_time}[/dim]")
                # console.print(f"[dim]💡 Queries this session: {query_count}[/dim]")
                console.print(f"[dim]To stop, type 'exit', 'quit', or 'bye'.  \nTo switch sessions, type 'switch'.  \nTo clear history, type 'clear'.[/dim]")
            
        except KeyboardInterrupt:
            console.print("\n\n[yellow]👋 Goodbye! Happy investing![/yellow]")
            break
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())