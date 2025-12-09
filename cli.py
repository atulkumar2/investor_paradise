"""CLI entrypoint for the Investor Paradise assistant.

This module wires together the data layer, Google ADK agents, and
a rich-based terminal UI to provide an interactive investing assistant.
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types
from rich.markdown import Markdown
from rich.panel import Panel

from cli_helpers import (
    AgentProgressTracker,
    TokenTracker,
    console,
    get_or_create_user_id,
    select_or_create_session,
)
from investor_agent.api_key_manager import (
    get_or_prompt_api_key,
    reset_api_key,
    show_help,
)
from investor_agent.cache_manager import (
    ensure_cache_available,
    ensure_vector_data_available,
    refresh_cache,
)
from investor_agent.data_engine import NSESTORE
from investor_agent.logger import get_logger
from investor_agent.sub_agents import create_pipeline
from spinner import process_query_with_spinner

load_dotenv()
logger = get_logger(__name__)


def _handle_cli_args() -> bool:
    """Handle simple CLI flags; return True if execution should stop."""
    if "--reset-api-key" in sys.argv:
        reset_api_key()
        return True

    if "--help" in sys.argv or "-h" in sys.argv:
        show_help()
        return True

    if "--refresh-cache" in sys.argv:
        console.print("\n[bold cyan]🔄 Refreshing NSE data cache...[/bold cyan]")
        logger.info("User requested cache refresh")
        if refresh_cache():
            console.print("[bold green]✅ Cache refreshed successfully![/bold green]")
            console.print("[dim]You can now run the CLI normally.[/dim]\n")
        else:
            console.print("[bold red]❌ Cache refresh failed![/bold red]")
            console.print("[yellow]Please check your internet connection and try again.[/yellow]\n")
        return True

    if "--download-vector-data" in sys.argv:
        console.print("\n[bold cyan]📦 Downloading vector data...[/bold cyan]")
        logger.info("User requested vector data download")
        if ensure_vector_data_available():
            console.print("[bold green]✅ Vector data downloaded successfully![/bold green]")
            console.print("[dim]You can now run the CLI normally.[/dim]\n")
        else:
            console.print("[bold red]❌ Vector data download failed![/bold red]")
            console.print("[yellow]Please check your internet connection and try again.[/yellow]\n")
        return True

    return False


def _get_api_key() -> str | None:
    """Retrieve and validate the Google API key.

    Returns the key, or None if it could not be retrieved.
    """
    google_api_key = get_or_prompt_api_key()
    os.environ["GOOGLE_API_KEY"] = google_api_key or ""

    if not google_api_key:
        console.print("[bold red]❌ Failed to retrieve API key[/bold red]")
        console.print(
            "[yellow]Please try again or set GOOGLE_API_KEY environment variable[/yellow]"
        )
        return None

    return google_api_key


def _initialize_data() -> None:
    """Load NSE data and log basic context."""
    # Display ASCII art logo (embedded directly to avoid packaging issues)
    logo = """ _____                    _              ______                   _ _
│_   _│                  │ │             │ ___ ╲                 │ (_)
  │ │ _ ____   _____  ___│ │_ ___  _ __  │ │_╱ ╱_ _ _ __ __ _  __│ │_ ___  ___
  │ ││ '_ ╲ ╲ ╱ ╱ _ ╲╱ __│ __╱ _ ╲│ '__│ │  __╱ _` │ '__╱ _` │╱ _` │ ╱ __│╱ _ ╲
 _│ ││ │ │ ╲ V ╱  __╱╲__ ╲ ││ (_) │ │    │ │ │ (_│ │ │ │ (_│ │ (_│ │ ╲__ ╲  __╱
 ╲___╱_│ │_│╲_╱ ╲___││___╱╲__╲___╱│_│    ╲_│  ╲__,_│_│  ╲__,_│╲__,_│_│___╱╲___│

                    Your AI-Powered NSE Stock Market Intelligence Platform 📊
                        Data-Driven Insights • News Intelligence • Smart Analysis
"""
    console.print(f"[bold green]{logo}[/bold green]")

    console.print("\n[bold cyan]🚀 Initializing Investor Paradise...[/bold cyan]")
    logger.info("Initializing Investor Paradise CLI")

    # Ensure cache files and vector data are available (download if missing)
    console.print("\n[bold blue]📦 Checking if latest market data parquet cache and Economic Times news vector data is available...[/bold blue]")
    logger.info("Checking data availability")

    if not ensure_cache_available():
        console.print("[bold red]❌ Failed to download cache files![/bold red]")
        console.print("[yellow]Please check your internet connection and try again.[/yellow]")
        logger.error("Cache download failed")
        sys.exit(1)

    if not ensure_vector_data_available():
        console.print("[bold red]❌ Failed to download vector data![/bold red]")
        console.print("[yellow]Please check your internet connection and try again.[/yellow]")
        logger.error("Vector data download failed")
        sys.exit(1)

    with console.status(
        "[bold blue]📂 Loading NSE stock data...[/bold blue]", spinner="dots"
    ):
        _ = NSESTORE.df

    console.print(f"[green]✅ Data loaded: {len(NSESTORE.df):,} rows[/green]")
    logger.info("Data loaded: %d rows", len(NSESTORE.df))
    console.print(f"[cyan]📅 Database Context: {NSESTORE.get_data_context()}[/cyan]")
    logger.info("Database Context: %s", NSESTORE.get_data_context())


def _create_models(api_key: str) -> tuple[Gemini, Gemini, Gemini]:
    """Create Gemini models with retry configuration."""
    retry_config = types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504],
    )

    logger.info("Initializing Gemini models with retry config")
    logger.info(
        "API key present: %s, length: %s",
        bool(api_key),
        len(api_key) if api_key else 0,
    )

    lite_model = Gemini(
        model="gemini-2.5-flash-lite",
        api_key=api_key,
        retry_options=retry_config,
    )
    flash_model = Gemini(
        model="gemini-2.5-flash",
        api_key=api_key,
        retry_options=retry_config,
    )
    pro_model = Gemini(
        model="gemini-2.5-pro",
        api_key=api_key,
        retry_options=retry_config,
    )

    logger.info("Models initialized: flash-lite, flash, pro")
    return lite_model, flash_model, pro_model


def _create_app(lite_model: Gemini, flash_model: Gemini, pro_model: Gemini) -> Tuple[App, Runner]:
    """Create the ADK App and root agent pipeline."""
    logger.info("Creating agent pipeline")
    root_agent = create_pipeline(
        entry_model=lite_model,
        market_model=flash_model,
        news_model=lite_model,
        merger_model=flash_model,
    )
    root_agent.__module__ = "cli"

    logger.info("Creating App with EventsCompactionConfig")
    app = App(
        name="investor_agent",
        root_agent=root_agent,
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=3,
            overlap_size=1,
        ),
    )
    return app, root_agent


def _create_runner(app: App) -> tuple[Runner, SqliteSessionService]:
    """Create the SqliteSessionService and Runner."""
    # Use Path to find the data directory relative to the investor_agent package
    data_dir = Path(__file__).parent / "investor_agent" / "data"
    db_path = str(data_dir / "investor_agent_sessions.db")
    logger.info("Setting up session service with database: %s", db_path)
    session_service = SqliteSessionService(db_path=db_path)
    runner = Runner(app=app, session_service=session_service)
    return runner, session_service


def _print_session_banner(session_id: str) -> None:
    console.print(
        "\n[bold green]💬 Ready! Ask me about NSE stocks or just say hi![/bold green]"
    )
    logger.info("CLI ready for user input")
    console.print(
        f"[dim]Session: {session_id[:8]}... | Commands: 'exit', "
        "'clear', 'switch'[/dim]\n"
    )


async def main() -> None:
    """Main CLI loop for Investor Paradise assistant."""
    if _handle_cli_args():
        return

    google_api_key = _get_api_key()
    if not google_api_key:
        return

    _initialize_data()

    lite_model, flash_model, pro_model = _create_models(google_api_key)
    app, root_agent = _create_app(lite_model, flash_model, pro_model)
    runner, session_service = _create_runner(app)

    user_id = get_or_create_user_id()
    console.print(f"[cyan]👤 User ID: {user_id[:8]}...[/cyan]")
    logger.info("User ID: %s", user_id)

    session_id = await select_or_create_session(
        session_service,
        "investor_agent",
        user_id,
    )
    logger.info("Session selected: %s", session_id)

    _print_session_banner(session_id)

    query_count = 0

    while True:
        try:
            user_input = console.input("\n[bold cyan]💭 You:[/bold cyan] ")

            if user_input.strip().lower() in ["exit", "quit", "bye"]:
                console.print("[yellow]👋 Goodbye! Happy investing![/yellow]")
                logger.info("User exited CLI")
                break

            # Handle switch command - change to different session
            if user_input.lower() == "switch":
                session_id = await select_or_create_session(
                    session_service,
                    "investor_agent",
                    user_id,
                )
                query_count = 0
                # Reset root_agent module to fix session app name mismatch
                root_agent.__module__ = "cli"
                console.print(
                    f"[green]✅ Switched to session: {session_id[:8]}...[/green]"
                )
                logger.info("Switched to session: %s", session_id)
                console.print(
                    f"[dim]Session: {session_id[:8]}... | Commands: 'exit', "
                    "'clear', 'switch'[/dim]\n"
                )
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
                    console.print(
                        "[yellow]🗑️  Session history cleared! Starting fresh.[/yellow]"
                    )
                    logger.info("Session history cleared: %s", session_id)
                except Exception as e:
                    console.print(f"[red]⚠️  Could not clear session: {e}[/red]")
                    logger.error("Could not clear session: %s", e)
                continue

            console.print()  # Blank line for separation

            query_count += 1
            logger.info("Processing query #%s: %s...", query_count, user_input[:50])

            user_message = types.Content(
                role="user",
                parts=[types.Part(text=user_input)],
            )

            # Initialize trackers
            tracker = AgentProgressTracker()
            token_tracker = TokenTracker()
            final_text = ""
            should_analyze = None  # Track routing decision
            displayed_agents = set()  # Track which agents we've shown
            displayed_tools = set()  # Track displayed tools
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
                    console.print(
                        "[yellow]⚠️ This session has incompatible data format.[/yellow]"
                    )
                    logger.warning("Incompatible session format detected: %s", session_id)
                    console.print("[yellow]Creating a new session...[/yellow]\n")
                    session_id = await select_or_create_session(
                        session_service,
                        "investor_agent",
                        user_id,
                        force_new=True,
                    )
                    console.print(
                        f"[green]✅ New session created: {session_id[:8]}...[/green]\n"
                    )
                    logger.info("New session created: %s", session_id)
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
                logger.debug(
                    "Response type: %s",
                    "markdown_report" if is_markdown_report else "simple_response",
                )

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
                    if (
                        "hello" in lower_text
                        or "hi" in lower_text
                        or "paradise" in lower_text
                    ):
                        title = "[bold cyan]💬 Assistant[/bold cyan]"
                        border = "cyan"
                    elif (
                        "can help" in lower_text
                        or "capabilities" in lower_text
                        or "specialize" in lower_text
                    ):
                        title = "[bold blue]ℹ️  Capabilities[/bold blue]"
                        border = "blue"
                    elif (
                        "cannot" in lower_text
                        or "can't" in lower_text
                        or "don't" in lower_text
                    ):
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
                console.print(f"[dim]⏱️  Processed in {elapsed_time}[/dim]")
                console.print(f"[dim]💡 Queries this session: {query_count}[/dim]")
                console.print(
                    "[dim]To stop, type 'exit', 'quit', or 'bye'.  \n"
                    "To switch sessions, type 'switch'.  \n"
                    "To clear history, type 'clear'.[/dim]"
                )

        except KeyboardInterrupt:
            console.print("\n\n[yellow]👋 Goodbye! Happy investing![/yellow]")
            logger.info("User interrupted with Ctrl+C")
            break
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
            logger.error("Error processing query", exc_info=True)
            traceback.print_exc()

def cli_main():
    """Entry point wrapper for the CLI console script."""
    asyncio.run(main())

if __name__ == "__main__":
    cli_main()
