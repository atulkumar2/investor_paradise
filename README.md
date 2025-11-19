# investor_paradise

Minimal agent for querying NSE cash-market (CM) historical data.

## Setup (uv + Python 3.11)

Install runtime dependencies with uv (stored in `pyproject.toml`):

```bash
uv add pandas pyarrow
uv sync
```

## Run

Ask a question via CLI (uses `./data` by default for CSV/Parquet files):

```bash
uv run -- python main.py "Available dates"
uv run -- python main.py "List symbols on 2023-01-02"
uv run -- python main.py "Summarize TCS between 2022-01-01 and 2022-12-31"
uv run -- python main.py "What were the top 10 most traded symbols on 2023-01-02 by value?"
```

Use a custom data directory with `--data`:

```bash
uv run -- python main.py --data /path/to/data "Available dates"
```

## Linting/Formatting

Ruff and Black are configured in `pyproject.toml`:

```bash
ruff check .
ruff format .   # or: black .

```

## Dependencies & requirements.txt

Runtime dependencies are declared in `pyproject.toml` (PEP 621). A separate
`requirements.txt` is not required. If you need one for external platforms
that still expect it, you can export the locked environment:

```bash
uv export > requirements.txt  # generates pinned requirements from pyproject
```

Treat `pyproject.toml` as the single source of truth; regenerate the export
when dependencies change.

## Gemini (Google Generative AI) Integration

Optional planner uses Gemini if `google-generativeai` is installed and
`GOOGLE_API_KEY` is set. Install and configure (supports `.env` at project root):

```bash
uv add google-generativeai
echo 'GOOGLE_API_KEY=your-key-here' > .env  # or export in shell profile
```

Run a question (Gemini will attempt JSON planning, else fallback):

```bash
uv run -- python main.py "Summarize TCS between 2024-01-01 and 2024-06-30"
```

If Gemini returns a plan, raw tool results may be emitted as JSON unless a
single `summarize_symbol` is called (rendered nicely). Adjust synthesis logic
in `main.py` if you need richer formatting.

## Agentic Sessions (multi‑turn + persistence)

Interactive, multi‑turn chat with optional session persistence and context compaction lives in `agentic.py`.

Start an in‑memory session:

```bash
uv run -- python agentic.py --data ./data
```

Persist sessions in SQLite and enable periodic compaction (every 3 agent turns):

```bash
uv run -- python agentic.py \
  --data ./data \
  --db my_agent_data.db \
  --app-name default --user-id default --session-id demo \
  --compact 3
```

During the chat, try simple stateful interactions:

```text
My name is Sam. I'm from Poland.
What is my name? Which country am I from?
```

Notes:

- `--db` stores events and session state; omit for in‑memory.
- `--compact N` appends a summary event every N agent turns.
- Gemini planning in `agentic.py` is optional and falls back to heuristics.

## Typing Modernization

The codebase targets Python 3.11+ and uses built‑in generics (`list[str]`,
`dict[str, Any]`, unions via `X | None`) instead of legacy `typing.List`,
`Dict`, `Optional`, etc. ABCs like `Callable` and `Iterable` now come from
`collections.abc`.

## Data Directory

The `data/` folder is git‑ignored to prevent committing large market files.
Place your CSV/Parquet bhavcopy style data under `data/` (or point `--data` to
an external path). Add small mock samples if you need tests.

