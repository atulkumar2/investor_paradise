# Copilot Instructions for investor_paradise

Concise guidance for AI coding assistants to work productively in this repo.

## Big Picture
- Minimal Python app: single entry `main.py`, prints a greeting.
- No external deps (`pyproject.toml` has `dependencies = []`). Python >= 3.11.
- Domain is undefined; treat as greenfield, keep changes small and reversible.

## Run & Debug
- Run app: `python main.py`
- Entrypoint: `main()` in `main.py` guarded by `if __name__ == "__main__":`.
- Debug locally with `breakpoint()`; add VS Code launch config only when complexity grows.

## Structure & Growth
- Keep `main.py` thin (<= ~40 lines). Extract logic into modules as it grows.
- When multiple modules appear, create package `investor_paradise/` and support `python -m investor_paradise`.
- Suggested layout (create only when needed): `investor_paradise/{core,services,models}/`, optional `cli.py` for argparse.

## Conventions
- Prefer small, pure functions; pass inputs explicitly (no hidden globals).
- Use `logging` instead of `print` once branching/IO increases.
- Embrace Python 3.11 typing features; keep modules side-effect free on import.

## Dependencies
- Edit `[project].dependencies` in `pyproject.toml` (PEP 621). Example:
  ```toml
  dependencies = ["pydantic>=2", "requests>=2.32"]
  ```
- Install after edits:
  ```bash
  pip install .
  # or, once packaged
  pip install -e .
  ```
 - Using `uv` (preferred here):
   ```bash
   uv add <package>
   uv sync
   ```

## Linting & Formatting
- Use Ruff for linting and import order; Black optional for formatting.
- Defaults: line length 88, target Python 3.11. Commands:
  ```bash
  ruff check .
  ruff format .   # or: black .
  ```
- Avoid `print` in non-CLI code; prefer `logging` with module-level loggers.

## Testing
- Add `pytest` when logic becomes non-trivial; mirror module paths under `tests/`.
- Example path: `tests/core/test_something.py` for `investor_paradise.core.something`.

## Safe Changes for AI
- May: add modules, introduce logging, propose lightweight deps, scaffold tests.
- Ask first: repo-wide refactors, heavy frameworks, persistence/storage.
- Do not: invent domain rules or external integrations without source docs.

## Planned Integrations
- News services: add clients under `investor_paradise/services/news/` with a small `BaseNewsClient` interface.
- PDF ingestion → embeddings → vector DB for RAG:
  - `investor_paradise/services/ingestion/pdf_ingest.py` (PDF -> text/chunks)
  - `investor_paradise/rag/vectorstore.py` (VectorStore interface; backend pluggable)
  - `investor_paradise/rag/retriever.py` (chunk retrieval + ranking)
- Keep vector DB behind an interface (e.g., FAISS/Chroma/Qdrant chosen later) and inject via constructor to keep modules testable.

## Repo Examples
- Current behavior lives in `main.py`:
  ```python
  def main():
      print("Hello from investor-paradise!")
  ```

Keep this file aligned with actual structure as the project evolves.
