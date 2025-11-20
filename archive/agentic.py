"""Interactive multi-turn agent session for NSE CM data.

Reuses tools and data layer from `main.py` but adds:
- Conversation memory (summaries of prior turns)
- Optional Gemini planning per turn
- Tool execution chain (can execute multiple planned tool calls)
- Simple synthesis of aggregated tool results

Usage:
    uv run -- python agentic.py --data ./data
    (then type questions; Ctrl-D to end on *nix, Ctrl-Z on Windows)

Environment:
- GOOGLE_API_KEY can be supplied via .env or environment for Gemini planning.

Design Notes:
- Importing from main.py to avoid duplication. If circular dependencies grow,
  consider refactoring shared components into a package module.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Reuse implementation details from main
from main import (
    NSEDataStore,
    _render_summary,
    list_available_dates,
    summarize_symbol,
    top_traded_by_value,
)

CONVERSATION_EVENTS_TABLE = "conversation_events"
CONVERSATION_STATE_TABLE = "conversation_state"

# Optional Gemini planner reuse (import guarded)
try:
    from main import GeminiPlanner, execute_plan  # type: ignore
except Exception:  # pragma: no cover
    GeminiPlanner = None  # type: ignore
    execute_plan = None  # type: ignore


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


@dataclass
class AgentTurn:
    """A single user-agent turn.""" 
    user: str
    answer: str
    tools_used: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def summary(self) -> str:
        """Compact one-line summary of the turn. """
        base = self.answer.splitlines()[0] if self.answer else "(empty)"
        used = f" tools={','.join(self.tools_used)}" if self.tools_used else ""
        return f"{self.timestamp} user='{self.user[:40]}' answer='{base[:60]}'{used}"


class AgentRollingMemory:
    """Simple rolling memory limited by max turns."""

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self.turns: list[AgentTurn] = []

    def add(self, turn: AgentTurn) -> None:
        """Add a new turn to memory, evicting oldest if over limit."""
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

    def context_prompt(self) -> str:
        """Render context prompt from recent turns."""
        if not self.turns:
            return "(no prior context)"
        return "Previous turns:\n" + "\n".join(t.summary() for t in self.turns[-10:])


class AgentSession:
    """Interactive session that plans and executes tool calls per user turn."""

    def __init__(self, store: NSEDataStore, use_gemini: bool = True) -> None:
        self.store = store
        self.memory = AgentRollingMemory()
        self.planner = GeminiPlanner() if (GeminiPlanner and use_gemini) else None

    def _available_dates_answer(self) -> str:
        dates = list_available_dates(self.store)
        if not dates:
            return "No trading dates found."
        joined = "\n- ".join(dates)
        return f"Available trading dates:\n- {joined}"

    def _top_traded_answer(self, question: str, lowered: str) -> str:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", question)
        if not match:
            return "Please include a date (YYYY-MM-DD)."
        date_s = match.group(1)
        n_match = re.search(r"top\s+(\d{1,3})", lowered)
        count = int(n_match.group(1)) if n_match else 10
        try:
            results = top_traded_by_value(self.store, date_s, count)
        except Exception as exc:  # pragma: no cover
            return f"Error: {exc}"
        header = f"Top {count} by traded value on {date_s}:"
        rows = [
            f"{i:>2}. {row['symbol']}: {row['total_traded_value']:.2f}"
            for i, row in enumerate(results, start=1)
        ]
        return "\n".join([header, *rows])

    def _summary_answer(self, question: str) -> str:
        dates = re.findall(r"(\d{4}-\d{2}-\d{2})", question)
        start = dates[0] if len(dates) >= 1 else None
        end = dates[1] if len(dates) >= 2 else None

        tokens = re.findall(r"[A-Za-z0-9]{2,10}", question)
        symbols = {
            sym.upper()
            for sym in self.store.df["SYMBOL"].dropna().astype(str)
        }
        chosen = next((tok.upper() for tok in tokens if tok.upper() in symbols), None)
        if not chosen:
            return "Could not determine symbol."
        try:
            summary = summarize_symbol(self.store, chosen, start, end)
        except Exception as exc:  # pragma: no cover
            return f"Error: {exc}"
        return _render_summary(summary)

    def _heuristic_answer(self, question: str) -> str:
        """Cheap routing over a few common intents."""
        lowered = question.lower()
        if "available" in lowered and "date" in lowered:
            return self._available_dates_answer()
        if "top" in lowered and "value" in lowered and "trade" in lowered:
            return self._top_traded_answer(question, lowered)
        if "summarize" in lowered or "summary" in lowered:
            return self._summary_answer(question)
        return (
            "Sorry, I could not determine intent. Try 'Summarize TCS between "
            "YYYY-MM-DD and YYYY-MM-DD'."
        )

    def _synthesize(self, executed: list[dict[str, Any]]) -> str:
        if not executed:
            return "(no tool executions)"
        if (
            len(executed) == 1
            and executed[0]["tool"] == "summarize_symbol"
            and isinstance(executed[0]["result"], dict)
        ):
            return _render_summary(executed[0]["result"])  # type: ignore[arg-type]
        # Provide compact JSON summary
        return json.dumps(executed, indent=2)

    def ask(self, question: str) -> str:
        """Ask a question, plan and execute tool calls, return answer."""
        question = question.strip()
        if not question:
            return "Please enter a non-empty question."
        plan_used: list[str] = []
        if self.planner and self.planner.enabled:
            plan = self.planner.plan(question)
            if plan:
                plan_used = [step.get("name", "?") for step in plan]
                if execute_plan:
                    executed = execute_plan(self.store, plan)
                    answer = self._synthesize(executed)  # type: ignore[arg-type]
                    self.memory.add(
                        AgentTurn(user=question, answer=answer, tools_used=plan_used)
                    )
                    return answer
        # Fallback heuristic
        answer = self._heuristic_answer(question)
        self.memory.add(AgentTurn(user=question, answer=answer, tools_used=plan_used))
        return answer

    def chat_loop(self) -> int:
        """Interactive chat loop."""
        print("Agentic session started. Type questions; Ctrl-D/Z to exit.\n")
        try:
            for line in sys.stdin:
                q = line.strip()
                if not q:
                    continue
                ctx = self.memory.context_prompt()
                print(f"\n[context]\n{ctx}\n")
                ans = self.ask(q)
                print(f"[answer]\n{ans}\n")
        except KeyboardInterrupt:  # pragma: no cover
            print("\nSession interrupted.")
        return 0


# ------------------------------
# Minimal session services + runner (ADK-like)
# ------------------------------

@dataclass
class ConversationSessionEvent:
    """A single event in a conversation session."""
    author: str  # 'user' | 'agent' | 'tool' | 'system'
    content: str
    timestamp: str = field(default_factory=_now_iso)
    tool_name: str | None = None


@dataclass
class ConversationSession:
    """A conversation session with events and state."""
    app_name: str
    user_id: str
    session_id: str
    events: list[ConversationSessionEvent] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)


class InMemoryConversationSessionService:
    """Simple in-memory conversation session service."""
    def __init__(self) -> None:
        self._store: dict[tuple[str, str, str], ConversationSession] = {}

    async def create_conversation_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> ConversationSession:
        """Create a new conversation session."""
        key = (app_name, user_id, session_id)
        if key in self._store:
            return self._store[key]
        conversation_session = ConversationSession(
          app_name=app_name, user_id=user_id, session_id=session_id)
        self._store[key] = conversation_session
        return conversation_session

    async def get_conversation_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> ConversationSession:
        """Retrieve or create a conversation session."""
        conversation_key = (app_name, user_id, session_id)
        if conversation_key not in self._store:
            return await self.create_conversation_session(
              app_name, user_id, session_id)
        return self._store[conversation_key]


class DatabaseSessionService:
    """SQLite-backed session service."""
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure()

    def _ensure(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {CONVERSATION_EVENTS_TABLE} (
                    app_name TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    ts TEXT,
                    author TEXT,
                    content TEXT,
                    tool_name TEXT
                )
                """
            )
            c.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {CONVERSATION_STATE_TABLE} (
                    app_name TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    key TEXT,
                    value TEXT,
                    PRIMARY KEY (app_name, user_id, session_id, key)
                )
                """
            )
            conn.commit()

    async def create_conversation_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> ConversationSession:
        """Create a new conversation session."""
        # For DB service, sessions are virtual; events/state are in tables
        return ConversationSession(
          app_name=app_name, user_id=user_id, session_id=session_id)

    async def get_conversation_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> ConversationSession:
        """Retrieve or create a conversation session."""
        conversation_session = ConversationSession(
          app_name=app_name, user_id=user_id, session_id=session_id)
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            rows = c.execute(
                (
                    "SELECT ts, author, content, tool_name FROM "
                    f"{CONVERSATION_EVENTS_TABLE} "
                    "WHERE app_name=? AND user_id=? AND session_id=? ORDER BY ts ASC"
                ),
                (app_name, user_id, session_id),
            ).fetchall()
            for ts, author, content, tool_name in rows:
                conversation_session.events.append(
                    ConversationSessionEvent(
                        author=author,
                        content=content,
                        timestamp=ts,
                        tool_name=tool_name,
                    )
                )
            # Load state
            srows = c.execute(
                (
                    "SELECT key, value FROM "
                    f"{CONVERSATION_STATE_TABLE} "
                    "WHERE app_name=? AND user_id=? AND session_id=?"
                ),
                (app_name, user_id, session_id),
            ).fetchall()
            for k, v in srows:
                conversation_session.state[k] = v
        return conversation_session

    def append_conversation_event(
      self,
      conversation_session: ConversationSession,
      session_event: ConversationSessionEvent) -> None:
        """Append an event to the session."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                (
                    "INSERT INTO "
                    f"{CONVERSATION_EVENTS_TABLE} "
                    "(app_name, user_id, session_id, ts, author, content, tool_name) "
                    "VALUES (?,?,?,?,?,?,?)"
                ),
                (
                    conversation_session.app_name,
                    conversation_session.user_id,
                    conversation_session.session_id,
                    session_event.timestamp,
                    session_event.author,
                    session_event.content,
                    session_event.tool_name,
                ),
            )
            conn.commit()

    def set_conversation_state(
      self,
      conversation_session: ConversationSession,
      key: str,
      value: str) -> None:
        """Set a state key-value pair for the session."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                (
                    "REPLACE INTO "
                    f"{CONVERSATION_STATE_TABLE} "
                    "(app_name, user_id, session_id, key, value) VALUES (?,?,?,?,?)"
                ),
                (conversation_session.app_name, 
                 conversation_session.user_id, 
                 conversation_session.session_id, key, value),
            )
            conn.commit()


class ToolContext:
    """Context passed to tools for session state access."""

    def __init__(
        self,
        conversation_session: ConversationSession,
        session_service: Any | None,
    ) -> None:
        self.state = conversation_session.state
        self._session = conversation_session
        self._svc = session_service

    def set(self, key: str, value: str) -> None:
        """Set a state key-value pair."""
        self.state[key] = value
        if isinstance(self._svc, DatabaseSessionService):
            self._svc.set_conversation_state(self._session, key, value)


class UserInfoTool:
    """Tool for saving and retrieving basic user info in session state."""

    def __init__(self, tool_context: ToolContext) -> None:
        self._ctx = tool_context

    def save(self, user_name: str, country: str) -> dict[str, Any]:
        """Save user info into session state."""
        self._ctx.set("user:name", user_name)
        self._ctx.set("user:country", country)
        return {"status": "success"}

    def retrieve(self) -> dict[str, Any]:
        """Retrieve user info from session state."""
        return {
            "status": "success",
            "user_name": self._ctx.state.get("user:name", "Unknown"),
            "country": self._ctx.state.get("user:country", "Unknown"),
        }


class Runner:
    """Runner for multi-turn agent sessions with session service."""
    def __init__(
        self,
        agent_session: AgentSession,
        app_name: str,
        session_service: InMemoryConversationSessionService | DatabaseSessionService,
        user_id: str,
        compaction_interval: int = 0,
    ) -> None:
        self.agent_session = agent_session
        self.app_name = app_name
        self.session_service = session_service
        self.user_id = user_id
        self.compaction_interval = compaction_interval

    def _record_user_event(self, session: ConversationSession, text: str) -> None:
        """Append a user event and persist if needed."""
        u_event = ConversationSessionEvent(author="user", content=text)
        session.events.append(u_event)
        if isinstance(self.session_service, DatabaseSessionService):
            self.session_service.append_conversation_event(session, u_event)

    def _maybe_route_state_tools(
        self, session: ConversationSession, ctx: ToolContext, text: str
    ) -> None:
        """Run simple state tools (save/retrieve user info) if applicable."""
        lowered = text.lower()
        user_tool = UserInfoTool(ctx)
        if "my name is" in lowered:
            name = text.split("my name is", 1)[1].strip().split()[0]
            country = ""
            for marker in ["i'm from", "i am from"]:
                if marker in lowered:
                    country = text.lower().split(marker, 1)[1].strip().split(".")[0]
                    break
            user_tool.save(name, country or ctx.state.get("user:country", ""))
            t_event = ConversationSessionEvent(
                author="tool",
                content=f"saved userinfo: {name}, {country}",
                tool_name="save_userinfo",
            )
            session.events.append(t_event)
            if isinstance(self.session_service, DatabaseSessionService):
                self.session_service.append_conversation_event(session, t_event)
        elif "what is my name" in lowered or "which country am i from" in lowered:
            info = user_tool.retrieve()
            t_event = ConversationSessionEvent(
                author="tool",
                content=json.dumps(info),
                tool_name="retrieve_userinfo",
            )
            session.events.append(t_event)
            if isinstance(self.session_service, DatabaseSessionService):
                self.session_service.append_conversation_event(session, t_event)

    def _append_agent_answer(
        self, session: ConversationSession, answer: str
    ) -> None:
        a_event = ConversationSessionEvent(author="agent", content=answer)
        session.events.append(a_event)
        if isinstance(self.session_service, DatabaseSessionService):
            self.session_service.append_conversation_event(session, a_event)

    def _maybe_compact(self, session: ConversationSession) -> None:
        if not self.compaction_interval:
            return
        agent_events = [e for e in session.events if e.author == "agent"]
        if not agent_events or len(agent_events) % self.compaction_interval != 0:
            return
        last = session.events[-6:]
        summary_lines = [
            f"{e.timestamp[:19]}Z {e.author}: {e.content[:80]}" for e in last
        ]
        comp = ConversationSessionEvent(
            author="system", content="COMPACTION:\n" + "\n".join(summary_lines)
        )
        session.events.append(comp)
        if isinstance(self.session_service, DatabaseSessionService):
            self.session_service.append_conversation_event(session, comp)

    async def run_turn(self, session_id: str, text: str) -> str:
        """Run a single user turn in the specified session."""
        conversation_session = await self.session_service.get_conversation_session(
            self.app_name, self.user_id, session_id
        )
        ctx = ToolContext(conversation_session, self.session_service)

        self._record_user_event(conversation_session, text)
        self._maybe_route_state_tools(conversation_session, ctx, text)

        answer = self.agent_session.ask(text)
        self._append_agent_answer(conversation_session, answer)
        self._maybe_compact(conversation_session)

        return answer


def _build_arg_parser() -> argparse.ArgumentParser:
    """Create and return the CLI argument parser for agentic sessions."""
    parser = argparse.ArgumentParser(description="Interactive agentic NSE CM session")
    parser.add_argument("--data", default="data", help="Path to data directory")
    parser.add_argument(
        "--no-gemini",
        action="store_true",
        help="Disable Gemini planning even if available",
    )
    parser.add_argument(
        "--db", default="", help="SQLite DB path to persist sessions (optional)"
    )
    parser.add_argument("--session-id", default="default", help="Session identifier")
    parser.add_argument("--user-id", default="default", help="User identifier")
    parser.add_argument("--app-name", default="default", help="Application name")
    parser.add_argument(
        "--compact", type=int, default=0, help="Compaction interval (0=off)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for interactive agentic session."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    try:
        store = NSEDataStore(Path(args.data))
    except FileNotFoundError as e:
        print(str(e))
        return 2

    agent_session = AgentSession(store, use_gemini=not args.no_gemini)

    # Optional ADK-like session manager
    if args.db:
        session_service: (
            InMemoryConversationSessionService | DatabaseSessionService
        ) = DatabaseSessionService(args.db)
    else:
        session_service = InMemoryConversationSessionService()

    runner = Runner(
        agent_session=agent_session,
        app_name=args.app_name,
        session_service=session_service,
        user_id=args.user_id,
        compaction_interval=max(0, int(args.compact)),
    )

    print("Agentic session started. Type questions; Ctrl-D/Z to exit.\n")
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            q = line.strip()
            if not q:
                continue
            # Echo minimal context from DB/in-memory session
            conversation_session = None
            try:
                conversation_session = asyncio.run(
                    session_service.get_conversation_session(
                        args.app_name, args.user_id, args.session_id
                    )
                )  # type: ignore[arg-type]
            except Exception:
                pass
            if conversation_session and conversation_session.events:
                print("\n[recent events]")
                for e in conversation_session.events[-3:]:
                    print(f"- {e.author}: {e.content[:80]}")
            # Run turn
            try:
                ans = asyncio.run(
                    runner.run_turn(args.session_id, q)
                )  # type: ignore[arg-type]
            except RuntimeError:
                # If an event loop already runs (e.g., some environments),
                # fallback to direct call pattern for InMemory service
                ans = agent_session.ask(q)
            print(f"[answer]\n{ans}\n")
    except KeyboardInterrupt:  # pragma: no cover
        print("\nSession interrupted.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
