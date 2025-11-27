#!/usr/bin/env python3
"""View conversation history from conversations/conversation_history.jsonl"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format."""
    dt = datetime.fromisoformat(iso_timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def view_all_sessions(log_file: Path):
    """View all sessions with summary statistics."""
    if not log_file.exists():
        print(f"❌ No conversation log found at: {log_file}")
        return

    sessions = {}

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            session_id = entry.get("session_id")

            if session_id not in sessions:
                sessions[session_id] = {
                    "queries": 0,
                    "responses": 0,
                    "errors": 0,
                    "first_seen": entry.get("timestamp"),
                    "last_seen": entry.get("timestamp")
                }

            # Increment counter based on type
            entry_type = entry["type"]
            if entry_type == "query":
                sessions[session_id]["queries"] += 1
            elif entry_type == "response":
                sessions[session_id]["responses"] += 1
            elif entry_type == "error":
                sessions[session_id]["errors"] += 1

            sessions[session_id]["last_seen"] = entry.get("timestamp")

    print(f"\n📊 Conversation History Summary\n{'='*80}")
    print(
        f"{'Session ID':<45} {'Queries':<10} "
        f"{'Responses':<12} {'Errors':<8} {'Duration'}"
    )
    print("="*80)

    for session_id, stats in sorted(sessions.items(), key=lambda x: x[1]["first_seen"]):
        first = format_timestamp(stats["first_seen"])
        last = format_timestamp(stats["last_seen"])
        print(
            f"{session_id:<45} "
            f"{stats['queries']:<10} "
            f"{stats['responses']:<12} "
            f"{stats['errors']:<8} "
            f"{first} → {last}"
        )

    print("="*80)
    print(f"Total sessions: {len(sessions)}\n")


def view_session_details(log_file: Path, session_id: str):
    """View detailed conversation for a specific session."""
    if not log_file.exists():
        print(f"❌ No conversation log found at: {log_file}")
        return

    entries = []

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            if entry.get("session_id") == session_id:
                entries.append(entry)

    if not entries:
        print(f"❌ No entries found for session: {session_id}")
        return

    print(f"\n💬 Session Details: {session_id}\n{'='*80}")

    for entry in entries:
        timestamp = format_timestamp(entry["timestamp"])
        entry_type = entry["type"]

        if entry_type == "query":
            print(f"\n[{timestamp}] 📥 USER QUERY")
            print(f"Query ID: {entry['query_id']}")
            print(f"User ID: {entry['user_id']}")
            print(f"Query: {entry['query']}")

        elif entry_type == "response":
            print(f"\n[{timestamp}] 📤 AGENT RESPONSE")
            print(f"Query ID: {entry['query_id']}")
            tools = entry.get('tools_used', [])
            if tools:
                print(f"Tools Used: {', '.join(tools)}")
            print(f"Response: {entry['response'][:500]}...")

        elif entry_type == "error":
            print(f"\n[{timestamp}] ❌ ERROR")
            if entry.get('query_id'):
                print(f"Query ID: {entry['query_id']}")
            print(f"Error: {entry['error']}")

    print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="View conversation history from investor_paradise agent"
    )
    parser.add_argument(
        "--session",
        "-s",
        help="View details for a specific session ID"
    )
    parser.add_argument(
        "--file",
        "-f",
        default=Path(__file__).parent / "conversation_history.jsonl",
        help=(
            "Path to conversation log file "
            "(default: conversations/conversation_history.jsonl)"
        ),
    )

    args = parser.parse_args()
    log_file = Path(args.file)

    if args.session:
        view_session_details(log_file, args.session)
    else:
        view_all_sessions(log_file)


if __name__ == "__main__":
    main()
