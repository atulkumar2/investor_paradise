"""
CLI Helper Functions and Classes
Extracted from cli.py for better code organization
"""

import os
import json
import uuid
import sqlite3
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()

# ============================================================================
# Agent Progress Tracker
# ============================================================================

# Agent-specific status messages (text, color)
AGENT_STATUS = {
    "EntryRouter": ("🧭 Understanding your request", "cyan"),
    "MarketAnalyst": ("📊 Analyzing stock market data", "blue"),
    "NewsIntelligence": ("📰 Gathering news intelligence", "yellow"),
    "PDFNewsScout": ("📄 Searching in-house PDF database", "magenta"),
    "WebNewsResearcher": ("🌐 Searching real-time web news", "yellow"),
    "CIO_Synthesizer": ("📝 Preparing investment report", "green"),
}

# Tool-specific messages (text, color)
TOOL_STATUS = {
    # Core Analysis Tools
    "get_top_gainers": ("📈 Finding top gaining stocks", "blue"),
    "get_top_losers": ("📉 Finding top losing stocks", "blue"),
    "get_sector_top_performers": ("🏢 Analyzing sector performance", "blue"),
    "analyze_stock": ("📊 Analyzing stock fundamentals", "blue"),
    "compare_stocks": ("⚖️ Comparing stock performance", "blue"),
    "calculate_returns": ("💹 Calculating returns", "blue"),
    
    # Index & Market Cap Tools (NEW)
    "get_index_constituents": ("📋 Fetching index constituents", "cyan"),
    "list_available_indices": ("📑 Listing available indices", "cyan"),
    "get_sectoral_indices": ("🏭 Getting sectoral indices", "cyan"),
    "get_sector_from_index": ("🔍 Identifying sector from index", "cyan"),
    "get_stocks_by_sector_index": ("📊 Analyzing index performance", "blue"),
    "get_stocks_by_market_cap": ("💰 Filtering by market cap", "blue"),
    "get_market_cap_category": ("🏷️ Classifying market cap", "cyan"),
    "get_sector_stocks": ("🏢 Getting sector stocks", "cyan"),
    
    # Advanced Pattern Detection Tools
    "detect_volume_surge": ("📊 Detecting volume anomalies", "magenta"),
    "detect_breakout": ("🚀 Identifying breakout patterns", "green"),
    "detect_breakouts": ("🚀 Identifying price breakouts", "green"),
    "find_high_delivery": ("📦 Finding high delivery stocks", "cyan"),
    "get_delivery_momentum": ("📦 Analyzing delivery percentages", "cyan"),
    "detect_accumulation": ("💰 Detecting accumulation patterns", "green"),
    "get_52week_high_low": ("📏 Checking 52-week ranges", "blue"),
    "analyze_risk_metrics": ("⚠️ Calculating risk metrics", "yellow"),
    "find_momentum_stocks": ("🎯 Finding momentum stocks", "magenta"),
    "detect_reversal_candidates": ("🔄 Detecting reversal patterns", "yellow"),
    "get_volume_price_divergence": ("📊 Analyzing volume divergence", "blue"),
    
    # Utility Tools
    "list_available_tools": ("🛠️ Listing available tools", "cyan"),
    "check_data_availability": ("📅 Checking data availability", "cyan"),
    
    # Semantic Search Tools
    "get_company_name": ("🏢 Looking up company name", "cyan"),
    "load_collections_for_date_range": ("📚 Loading news collections for date range", "magenta"),
    "semantic_search": ("🔎 Searching PDF news database", "magenta"),
    
    # News Tools
    "google_search": ("🔍 Searching web for news & catalysts", "yellow"),
}


class AgentProgressTracker:
    """Track and display agent pipeline progress with simple status messages"""
    
    def __init__(self):
        self.current_agent = None
        self.current_tool = None
        self.start_time = datetime.now()
    
    def start_agent(self, agent_name):
        """Display agent start message"""
        if agent_name in AGENT_STATUS:
            msg, color = AGENT_STATUS[agent_name]
            console.print(f"[{color}]● {msg}...[/{color}]")
        self.current_agent = agent_name
    
    def add_tool(self, tool_name):
        """Track tool usage (messages shown in spinner status)"""
        if tool_name != self.current_tool:  # Avoid duplicate messages
            self.current_tool = tool_name
            # Note: Tool messages are displayed in the spinner status, not printed here
            # to avoid conflicts with the Live display
            # if tool_name in TOOL_STATUS:
            #     msg, color = TOOL_STATUS[tool_name]
            #     console.print(f"  [dim {color}]→ {msg}[/dim {color}]")
    
    def complete(self):
        """Display completion"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        console.print(f"[dim green]✓ Analysis complete ({elapsed:.1f}s)[/dim green]\n")
    
    def get_table(self):
        """Deprecated - using simple messages now"""
        return None
    
    def get_summary(self):
        """Get timing summary"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        return f"⏱️ Processing time: {total_time:.2f}s"


# ============================================================================
# Token Usage Tracker
# ============================================================================

class TokenTracker:
    """Track token usage per model for accurate cost analysis"""
    
    # Gemini pricing (per 1M tokens, USD - check current rates)
    PRICING = {
        'gemini-2.5-flash-lite': {'input': 0.075, 'output': 0.30},
        'gemini-2.5-flash': {'input': 0.15, 'output': 0.60},
        'gemini-2.5-pro': {'input': 1.25, 'output': 5.00},
    }
    
    # Map agent names to their models
    AGENT_MODEL_MAP = {
        "EntryRouter": "gemini-2.5-flash-lite",
        "MarketAnalyst": "gemini-2.5-flash",
        "NewsIntelligence": "gemini-2.5-flash-lite",  # Parent parallel agent (doesn't use model directly)
        "PDFNewsScout": "gemini-2.5-flash-lite",
        "WebNewsResearcher": "gemini-2.5-flash-lite",
        "CIO_Synthesizer": "gemini-2.5-flash"
    }
    
    def __init__(self):
        self.model_usage = {}  # {model_name: {prompt: X, response: Y, total: Z}}
    
    def add_usage(self, model_name: str, prompt_tokens: int, response_tokens: int):
        """Add token usage for a specific model"""
        if model_name not in self.model_usage:
            self.model_usage[model_name] = {
                'prompt': 0,
                'response': 0,
                'total': 0
            }
        
        # Handle None values (can happen with certain event types)
        prompt_tokens = prompt_tokens or 0
        response_tokens = response_tokens or 0
        
        self.model_usage[model_name]['prompt'] += prompt_tokens
        self.model_usage[model_name]['response'] += response_tokens
        self.model_usage[model_name]['total'] += (prompt_tokens + response_tokens)
    
    def get_model_from_agent(self, agent_name: str) -> str:
        """Get model name from agent name"""
        return self.AGENT_MODEL_MAP.get(agent_name, "unknown")
    
    def get_summary(self, show_cost: bool = True) -> str:
        """Generate formatted summary of token usage per model"""
        if not self.model_usage:
            return ""
        
        lines = ["📊 Token Usage by Model:"]
        total_all = 0
        total_cost = 0.0
        
        for model, usage in self.model_usage.items():
            model_display = model  # Keep full model name for clarity
            total_all += usage['total']
            
            # Calculate cost
            cost = 0.0
            if model in self.PRICING:
                cost = (
                    (usage['prompt'] / 1_000_000) * self.PRICING[model]['input'] +
                    (usage['response'] / 1_000_000) * self.PRICING[model]['output']
                )
                total_cost += cost
                cost_str = f" (${cost:.4f})" if show_cost else ""
            else:
                cost_str = ""
            
            lines.append(
                f"  • {model_display}: "
                f"{usage['prompt']:,} in + {usage['response']:,} out = "
                f"{usage['total']:,} total{cost_str}"
            )
        
        if len(self.model_usage) > 1:
            lines.append(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            cost_str = f" (${total_cost:.4f})" if show_cost and total_cost > 0 else ""
            lines.append(f"  Combined: {total_all:,} tokens{cost_str}")
        
        return '\n'.join(lines)


# ============================================================================
# Session Management
# ============================================================================

USER_FILE = "investor_agent/data/user.json"

def get_or_create_user_id():
    """Load or create persistent user_id (NOT session_id - that's managed by DatabaseSessionService)"""
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, 'r') as f:
                data = json.load(f)
                return data['user_id']
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not load user file: {e}[/yellow]")
    
    # Create new user_id
    user_id = str(uuid.uuid4())
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)
    
    with open(USER_FILE, 'w') as f:
        json.dump({'user_id': user_id, 'created_at': datetime.now().isoformat()}, f, indent=2)
    
    console.print(f"[green]✅ Created new user profile: {user_id[:8]}...[/green]")
    return user_id


async def list_user_sessions(session_service, app_name: str, user_id: str):
    """List all sessions for a user from DatabaseSessionService"""
    try:
        response = await session_service.list_sessions(
            app_name=app_name,
            user_id=user_id
        )
        # Extract sessions list from response object
        if response and hasattr(response, 'sessions'):
            return response.sessions if response.sessions else []
        elif isinstance(response, list):
            return response
        else:
            return []
    except Exception as e:
        console.print(f"[dim yellow]⚠️  Could not list sessions: {e}[/dim yellow]")
        return []


async def select_or_create_session(session_service, app_name: str, user_id: str, force_new: bool = False):
    """Interactive session selection with option to create new or resume existing
    
    Args:
        session_service: The database session service
        app_name: Name of the app
        user_id: User identifier
        force_new: If True, skip selection and create new session
    """
    if force_new:
        # Create new session without prompting
        session_id = str(uuid.uuid4())
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        return session_id
    
    sessions = await list_user_sessions(session_service, app_name, user_id)
    
    if not sessions:
        # No sessions exist, create new
        session_id = str(uuid.uuid4())
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        console.print(f"[green]✅ Created new session: {session_id[:8]}...[/green]")
        return session_id
    
    # Show existing sessions
    console.print("\n[cyan]📋 Your Sessions:[/cyan]")
    for i, session in enumerate(sessions, 1):
        # Handle different session object formats (tuple, object, dict)
        if isinstance(session, tuple):
            # Tuple format: (session_id, app_name, user_id, created_at, updated_at)
            session_id = session[0]
            updated = session[4] if len(session) > 4 else 'Unknown'
        elif hasattr(session, 'id'):
            session_id = session.id
            updated = session.updated_at if hasattr(session, 'updated_at') else 'Unknown'
        elif hasattr(session, 'session_id'):
            session_id = session.session_id
            updated = session.updated_at if hasattr(session, 'updated_at') else 'Unknown'
        elif isinstance(session, dict):
            session_id = session.get('session_id') or session.get('id')
            updated = session.get('updated_at', 'Unknown')
        else:
            session_id = str(session)
            updated = 'Unknown'
        
        # Format timestamp if available
        if updated != 'Unknown':
            try:
                if isinstance(updated, str):
                    dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    updated = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    updated = updated.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        
        console.print(f"  [cyan]{i}.[/cyan] Session [bold]{session_id[:8]}...[/bold] [dim](Last used: {updated})[/dim]")
    
    console.print(f"  [cyan]{len(sessions) + 1}.[/cyan] [green]Create new session[/green]")
    
    choice = console.input(f"\n[bold]Select session (1-{len(sessions) + 1}):[/bold] ").strip()
    
    try:
        choice_num = int(choice)
        if 1 <= choice_num <= len(sessions):
            # Resume existing session - extract session_id based on format
            selected_session = sessions[choice_num - 1]
            
            if isinstance(selected_session, tuple):
                session_id = selected_session[0]
            elif hasattr(selected_session, 'id'):
                session_id = selected_session.id
            elif hasattr(selected_session, 'session_id'):
                session_id = selected_session.session_id
            elif isinstance(selected_session, dict):
                session_id = selected_session.get('session_id') or selected_session.get('id')
            else:
                session_id = str(selected_session)
            
            console.print(f"[green]✅ Resumed session: {session_id[:8]}...[/green]")
            return session_id
        elif choice_num == len(sessions) + 1:
            # Create new session
            session_id = str(uuid.uuid4())
            await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
            console.print(f"[green]✅ Created new session: {session_id[:8]}...[/green]")
            return session_id
        else:
            console.print("[yellow]Invalid choice, creating new session[/yellow]")
            session_id = str(uuid.uuid4())
            await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
            console.print(f"[green]✅ Created new session: {session_id[:8]}...[/green]")
            return session_id
    except ValueError:
        console.print("[yellow]Invalid input, creating new session[/yellow]")
        session_id = str(uuid.uuid4())
        await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        console.print(f"[green]✅ Created new session: {session_id[:8]}...[/green]")
        return session_id


def cleanup_old_sessions(db_path: str, days: int = 7):
    """Delete session records older than specified days from SQLite database.
    
    Args:
        db_path: Path to sessions.db file
        days: Number of days to retain (default: 7)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check which timestamp column exists
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if not columns:
            # Table doesn't exist yet
            conn.close()
            return
        
        # Determine which timestamp column to use
        timestamp_col = None
        if 'updated_at' in columns:
            timestamp_col = 'updated_at'
        elif 'last_accessed_at' in columns:
            timestamp_col = 'last_accessed_at'
        elif 'created_at' in columns:
            timestamp_col = 'created_at'
        
        if not timestamp_col:
            conn.close()
            return
        
        # Calculate cutoff timestamp
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        # Delete old sessions
        cursor.execute(
            f"DELETE FROM sessions WHERE {timestamp_col} < ?",
            (cutoff_str,)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            console.print(f"[dim]🗑️  Cleaned up {deleted_count} session(s) older than {days} days[/dim]")
    except Exception as e:
        # Silently ignore cleanup errors on first run
        pass
