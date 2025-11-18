"""
Agent for querying NSE cash-market historical data.

Implements:
- Data loader with caching over `data/` CSV/Parquet files
- Tool functions (list dates, list symbols, OHLC history, summarize symbol, top traded)
- Lightweight tool registry and a simple planner-driven agent
- CLI to accept a natural-language query and return an answer

Assumptions:
- Columns similar to NSE bhavcopy: SYMBOL, DATE/TIMESTAMP, OPEN, HIGH, LOW, CLOSE,
  TOTTRDQTY (volume), TOTTRDVAL (traded value). Missing columns are handled gracefully.
- Uses pandas for loading/filtering. Dependencies are assumed available.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

try:  # pandas is required at runtime; environment is assumed to provide it
    import pandas as pd  # type: ignore
except Exception as _e:  # pragma: no cover
    raise RuntimeError("pandas is required to run this program.") from _e


# ----------------------------- Data Loading Layer -----------------------------


@dataclass
class DataStore:
    """Loads and caches NSE CM data from the `data/` folder.

    - Scans the folder once for CSV/Parquet files.
    - Caches a DataFrame per file on first access.
    - Exposes a combined DataFrame view for queries.
    """

    root: Path
    _file_cache: dict[Path, pd.DataFrame] | None = None
    _combined_cache: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        if not self.root.exists():
            raise FileNotFoundError(f"Data folder not found: {self.root}")

    @property
    # Property: returns discovered data files (CSV/Parquet)
    def files(self) -> list[Path]:
        """Return data files to load.

        Prioritize the `NSE_Rawdata` subfolder (if present). Ignore `news_et_toi`.
        Only include files with extensions: .csv, .parquet, .pq.
        """
        exts = {".csv", ".parquet", ".pq"}
        raw_dir = self.root / "NSE_Rawdata"
        search_roots = [raw_dir] if raw_dir.exists() else [self.root]

        files: list[Path] = []
        for base in search_roots:
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in exts:
                    continue
                # skip news folder entirely
                if any(part.lower() == "news_et_toi" for part in p.parts):
                    continue
                files.append(p)
        return sorted(files)

    # Internal: load a single file then normalize schema
    def _load_file(self, path: Path) -> pd.DataFrame:
        if self._file_cache is None:
            self._file_cache = {}
        if path in self._file_cache:
            return self._file_cache[path]
        try:
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(
                    path,
                    on_bad_lines="skip",
                    low_memory=False,
                    encoding="utf-8",
                    encoding_errors="ignore",
                )
            else:
                df = pd.read_parquet(path)
        except Exception as e:  # pragma: no cover
            print(f"Warning: failed to load {path.name}: {e}", file=sys.stderr)
            df = _empty_normalized_df()
        df = _normalize_schema(df)
        self._file_cache[path] = df
        return df

    @property
    # Property: combined normalized DataFrame (cached)
    def df(self) -> pd.DataFrame:
        """Concatenated view of all files with normalized columns."""
        if self._combined_cache is not None:
            return self._combined_cache
        def _usable(frame: pd.DataFrame) -> bool:
            # Exclude empty or all-NA frames to avoid pandas concat FutureWarning
            if frame.empty:
                return False
            # If every column is entirely NA, skip
            if frame.isna().all().all():
                return False
            return True

        frames = [f for f in (self._load_file(p) for p in self.files) if _usable(f)]
        if not frames:
            # empty schema with expected columns
            self._combined_cache = _empty_normalized_df()
            return self._combined_cache
        # Suppress known concat FutureWarning locally
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=(
                    "The behavior of DataFrame concatenation with empty or all-NA "
                    "entries is deprecated"
                ),
                category=FutureWarning,
            )
            combined = pd.concat(frames, ignore_index=True)
        # Ensure dtypes and sorted by date
        combined.sort_values(["DATE", "SYMBOL"], inplace=True, ignore_index=True)
        self._combined_cache = combined
        return self._combined_cache


# Helper: create empty normalized DataFrame with canonical columns
def _empty_normalized_df() -> pd.DataFrame:
    cols = [
        "SYMBOL",
        "DATE",
        "OPEN",
        "HIGH",
        "LOW",
        "CLOSE",
        "TOTTRDQTY",
        "TOTTRDVAL",
    ]
    return pd.DataFrame(columns=cols)


# Normalize raw file schema to canonical columns and types
def _normalize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and types to a canonical schema.

    - Consolidate date column to `DATE` (date, not datetime).
    - Ensure numeric columns are floats/ints where appropriate.
    """

    # Standardize column names (strip spaces, upper)
    rename_map = {c: c.strip().upper() for c in df.columns}
    df = df.rename(columns=rename_map)

    # Map common alternative column names to canonical ones
    alt_map = {
        "OPEN_PRICE": "OPEN",
        "HIGH_PRICE": "HIGH",
        "LOW_PRICE": "LOW",
        "CLOSE_PRICE": "CLOSE",
        "TTL_TRD_QNTY": "TOTTRDQTY",
        # TURNOVER_LACS will be used to compute TOTTRDVAL later
    }
    for src, dst in alt_map.items():
        if src in df.columns and dst not in df.columns:
            df = df.rename(columns={src: dst})

    # Unify date column
    date_col_candidates = [
        "DATE",
        "TIMESTAMP",
        "DATE/TIMESTAMP",
        "DATE_",
        "DATE1",
    ]
    date_col = next((c for c in date_col_candidates if c in df.columns), None)
    if date_col is None:
        # try to infer any date-like column
        for c in df.columns:
            if "DATE" in c:
                date_col = c
                break
    if date_col is None:
        df["DATE"] = pd.NaT
    else:
        ser = pd.to_datetime(df[date_col], errors="coerce")
        df["DATE"] = pd.Series(ser).dt.date  # type: ignore[attr-defined]

    # Ensure symbol column exists
    if "SYMBOL" not in df.columns:
        # try common alternatives
        for c in ("TICKER", "SECURITY", "SYMB"):
            if c in df.columns:
                df = df.rename(columns={c: "SYMBOL"})
                break
    if "SYMBOL" not in df.columns:
        df["SYMBOL"] = None

    # Numeric columns: strip thousands separators/spaces before coercion
    numeric_cols = ("OPEN", "HIGH", "LOW", "CLOSE", "TOTTRDQTY", "TOTTRDVAL")
    for col in numeric_cols:
        if col in df.columns:
            # normalize textual numbers like "1,234.56" -> "1234.56"
            df[col] = df[col].astype(str).str.replace(r"[\s,]", "", regex=True)
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.NA

    # If traded value missing, derive from TURNOVER_LACS (₹ Lakhs) if available,
    # else approximate via CLOSE * TOTTRDQTY
    if "TOTTRDVAL" in df.columns:
        mask_missing_val = df["TOTTRDVAL"].isna()
        if mask_missing_val.any():
            # Prefer TURNOVER_LACS when present
            if "TURNOVER_LACS" in df.columns:
                tval = pd.to_numeric(df["TURNOVER_LACS"], errors="coerce") * 100000.0
                df.loc[mask_missing_val, "TOTTRDVAL"] = tval[mask_missing_val]
                mask_missing_val = df["TOTTRDVAL"].isna()
            if mask_missing_val.any():
                close_num = pd.to_numeric(df["CLOSE"], errors="coerce")
                vol_num = pd.to_numeric(df["TOTTRDQTY"], errors="coerce")
                approx = close_num * vol_num
                df.loc[mask_missing_val, "TOTTRDVAL"] = approx[mask_missing_val]
    else:
        # Create TOTTRDVAL from TURNOVER_LACS if available
        if "TURNOVER_LACS" in df.columns:
            df["TOTTRDVAL"] = (
                pd.to_numeric(df["TURNOVER_LACS"], errors="coerce") * 100000.0
            )

    # Keep only expected columns to simplify downstream logic
    keep = [
        "SYMBOL",
        "DATE",
        "OPEN",
        "HIGH",
        "LOW",
        "CLOSE",
        "TOTTRDQTY",
        "TOTTRDVAL",
    ]
    missing = [c for c in keep if c not in df.columns]
    for c in missing:
        df[c] = pd.NA
    return cast(pd.DataFrame, df.loc[:, keep])


# ------------------------------- Tool Registry -------------------------------


ToolFn = Callable[..., Any]


class ToolRegistry:
    """Simple tool registry to mimic ADK tool exposure."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {}

    # Register a tool function under a name
    def register(self, name: str, fn: ToolFn) -> None:
        self._tools[name] = fn

    # Retrieve a tool by name
    def get(self, name: str) -> ToolFn:
        return self._tools[name]

    # Iterate (name, function) pairs
    def items(self) -> Iterable[tuple[str, ToolFn]]:
        return self._tools.items()


TOOLS = ToolRegistry()


def tool(name: str | None = None) -> Callable[[ToolFn], ToolFn]:
    """Decorator to register a function as a tool."""

    def decorator(fn: ToolFn) -> ToolFn:
        tool_name = name or fn.__name__
        TOOLS.register(tool_name, fn)
        fn.__tool_name__ = tool_name  # type: ignore[attr-defined]
        return fn

    return decorator


# --------------------------------- Utilities ---------------------------------


_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_TOP_RE = re.compile(r"\btop\s+(\d{1,3})\b", re.IGNORECASE)


def parse_date(s: str) -> date:
    """Parse YYYY-MM-DD string to date, raising ValueError if invalid."""

    return datetime.strptime(s, "%Y-%m-%d").date()


def extract_dates(text: str) -> list[date]:
    """'Extract all dates in YYYY-MM-DD format from text."""
    matches = _DATE_RE.findall(text)
    dates = []
    for m in matches:
        try:
            dates.append(parse_date(m))
        except ValueError:
            continue
    return dates


def extract_top_n(text: str, default: int = 10) -> int:
    """Extract top N from text, defaulting to 10."""

    text = text.upper()
    m = _TOP_RE.search(text)
    if not m:
        return default
    try:
        return int(m.group(1))
    except Exception:
        return default


def guess_symbol(text: str, candidates: Iterable[str]) -> str | None:
    """Heuristically pick a symbol from text based on candidates.

    Extract short alphanumeric tokens from the text and intersect with
    candidate symbols (case-insensitive). Prefer longer matches.
    """

    tokens = re.findall(r"[A-Za-z0-9]{2,10}", text)
    token_set = {t.upper() for t in tokens}
    cand_set = {c.upper() for c in candidates}
    inter = token_set & cand_set
    if not inter:
        return None
    # Prefer longer matches
    return sorted(inter, key=lambda s: (-len(s), s))[0]


def _date_range_filter(
    df: pd.DataFrame, start: date | None, end: date | None
) -> pd.DataFrame:
    if start is not None:
        df = cast(pd.DataFrame, df.loc[df["DATE"] >= start, :])
    if end is not None:
        df = cast(pd.DataFrame, df.loc[df["DATE"] <= end, :])
    return cast(pd.DataFrame, df)


# ----------------------------------- Tools -----------------------------------


@tool("list_available_dates")
def list_available_dates(store: DataStore) -> list[str]:
    """Return all trading dates found in the data as ISO strings (YYYY-MM-DD)."""

    dates = sorted({d for d in store.df["DATE"].dropna().unique().tolist()})
    return [str(d) for d in dates]


@tool("list_symbols")
def list_symbols(store: DataStore, date_v: str) -> list[str]:
    """List symbols traded on a given date (YYYY-MM-DD)."""

    d = parse_date(date_v)
    df = store.df
    day = cast(pd.DataFrame, df.loc[df["DATE"] == d, :])
    if day.empty:
        raise ValueError(f"No data for date {date_v}.")
    syms = sorted({s for s in day["SYMBOL"].dropna().astype(str).unique().tolist()})
    return syms


@tool("get_ohlc_history")
def get_ohlc_history(
    store: DataStore,
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Return daily OHLC and volume for a symbol in [start_date, end_date].

    - Dates are optional; if omitted, full history is returned.
     - Returns a list of dicts with keys: date, open, high, low, close,
        volume, traded_value.
    """

    df = store.df
    s = symbol.upper()
    sdf = cast(pd.DataFrame, df.loc[df["SYMBOL"].astype(str).str.upper() == s, :])
    if sdf.empty:
        raise ValueError(f"Unknown or missing symbol: {symbol}.")
    start = parse_date(start_date) if start_date else None
    end = parse_date(end_date) if end_date else None
    sdf = _date_range_filter(sdf, start, end)
    sdf = sdf.sort_values("DATE")
    out = []
    for _, row in sdf.iterrows():
        out.append(
            {
                "date": str(row["DATE"]),
                "open": _safe_float(row.get("OPEN")),
                "high": _safe_float(row.get("HIGH")),
                "low": _safe_float(row.get("LOW")),
                "close": _safe_float(row.get("CLOSE")),
                "volume": _safe_float(row.get("TOTTRDQTY")),
                "traded_value": _safe_float(row.get("TOTTRDVAL")),
            }
        )
    if not out:
        raise ValueError("No OHLC data in the requested range.")
    return out


@tool("summarize_symbol")
def summarize_symbol(
    store: DataStore,
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Return summary stats for a symbol over an optional date range.

    Keys: first_close, last_close, absolute_return, percent_return, max_close,
    min_close,
    average_volume, total_traded_value
    """

    df = store.df
    s = symbol.upper()
    sdf = cast(pd.DataFrame, df.loc[df["SYMBOL"].astype(str).str.upper() == s, :])
    if sdf.empty:
        raise ValueError(f"Unknown or missing symbol: {symbol}.")
    start = parse_date(start_date) if start_date else None
    end = parse_date(end_date) if end_date else None
    sdf = _date_range_filter(sdf, start, end)
    sdf = sdf.sort_values("DATE")
    if sdf.empty:
        raise ValueError("No data in the requested range.")

    first_raw = sdf["CLOSE"].iloc[0]
    last_raw = sdf["CLOSE"].iloc[-1]
    first_close = float(first_raw) if not pd.isna(first_raw) else float("nan")
    last_close = float(last_raw) if not pd.isna(last_raw) else float("nan")

    abs_ret = (
        last_close - first_close
        if _is_finite(first_close) and _is_finite(last_close)
        else float("nan")
    )
    pct_ret = (
        (abs_ret / first_close * 100.0)
        if _is_finite(first_close) and _is_finite(abs_ret) and first_close != 0
        else float("nan")
    )
    max_close = (
        float(sdf["CLOSE"].max()) if not sdf["CLOSE"].isna().all() else float("nan")
    )
    min_close = (
        float(sdf["CLOSE"].min()) if not sdf["CLOSE"].isna().all() else float("nan")
    )
    avg_vol = (
        float(sdf["TOTTRDQTY"].mean())
        if not sdf["TOTTRDQTY"].isna().all()
        else float("nan")
    )
    total_val = (
        float(sdf["TOTTRDVAL"].sum())
        if not sdf["TOTTRDVAL"].isna().all()
        else float("nan")
    )

    return {
        "symbol": s,
        "start_date": str(sdf["DATE"].iloc[0]),
        "end_date": str(sdf["DATE"].iloc[-1]),
        "first_close": first_close,
        "last_close": last_close,
        "absolute_return": abs_ret,
        "percent_return": pct_ret,
        "max_close": max_close,
        "min_close": min_close,
        "average_volume": avg_vol,
        "total_traded_value": total_val,
    }


@tool("top_traded_by_value")
def top_traded_by_value(
    store: DataStore, date_v: str, n: int = 10
) -> list[dict[str, Any]]:
    """Top-N symbols by total traded value (TOTTRDVAL) on a given date (YYYY-MM-DD)."""

    d = parse_date(date_v)
    df = store.df
    day = df[df["DATE"] == d]
    if day.empty:
        raise ValueError(f"No data for date {date_v}.")
    grp = day.groupby("SYMBOL", dropna=True)["TOTTRDVAL"].sum(min_count=1).reset_index()
    # Drop symbols with no value (all-NA -> NaN) or non-positive totals
    grp = grp.dropna(subset=["TOTTRDVAL"])
    grp = grp[grp["TOTTRDVAL"] > 0]
    grp = grp.sort_values("TOTTRDVAL", ascending=False)
    grp = grp.head(max(1, int(n)))
    records = grp.rename(
        columns={"SYMBOL": "symbol", "TOTTRDVAL": "total_traded_value"}
    ).to_dict(orient="records")
    # Ensure numeric typing for output and filter non-positive / invalid values
    out: list[dict[str, Any]] = []
    for rec in records:
        val = _safe_float(rec.get("total_traded_value"))
        if not _is_finite(val) or val <= 0:
            continue
        out.append({"symbol": str(rec.get("symbol")), "total_traded_value": val})
    return out


def _safe_float(x: Any) -> float:
    try:
        f = float(x)
        if f == float("inf") or f == float("-inf"):
            return float("nan")
        return f
    except Exception:
        return float("nan")


def _is_finite(x: Any) -> bool:
    try:
        f = float(x)
        return pd.notna(f) and f not in (float("inf"), float("-inf"))
    except Exception:
        return False


# ------------------------------------ Agent -----------------------------------


class Agent:
    """Simple planner that selects appropriate tools based on the question."""

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def run(self, question: str) -> str:
        """Process a natural-language question and return an answer string."""
        q = question.strip()
        if not q:
            return (
                "Please provide a question, e.g., "
                "'Summarize TCS between 2022-01-01 and 2022-12-31'."
            )

        ql = q.lower()

        # 1) List available dates
        if "available date" in ql or ("list" in ql and "date" in ql):
            dates = list_available_dates(self.store)
            if not dates:
                return "No trading dates found in data."
            return "Available trading dates:\n- " + "\n- ".join(dates)

        # 2) Top N traded by value on a date
        if ("top" in ql) and ("trade" in ql) and ("value" in ql):
            dates = extract_dates(q)
            if not dates:
                return "Please include a date in YYYY-MM-DD format."
            n = extract_top_n(q, default=10)
            results = top_traded_by_value(self.store, str(dates[0]), n)
            if not results:
                return f"No traded symbols found on {dates[0]}."
            lines = [f"Top {n} by traded value on {dates[0]}:"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i:>2}. {r['symbol']}: {r['total_traded_value']:.2f}")
            return "\n".join(lines)

        # 3) Summarize SYMBOL between dates
        if "summarize" in ql or "summary" in ql:
            dates = extract_dates(q)
            start = str(dates[0]) if len(dates) >= 1 else None
            end = str(dates[1]) if len(dates) >= 2 else None

            # Guess symbol from candidates on relevant dates or full set
            all_syms = self._all_symbols()
            sym = guess_symbol(q, all_syms)
            if not sym:
                return (
                    "Could not determine symbol. Try: "
                    "'Summarize TCS between 2022-01-01 and 2022-12-31'."
                )

            summary = summarize_symbol(self.store, sym, start, end)
            return _render_summary(summary)

        # 4) List symbols for a date
        if "list" in ql and "symbol" in ql:
            dates = extract_dates(q)
            if not dates:
                return "Please include a date in YYYY-MM-DD format."
            syms = list_symbols(self.store, str(dates[0]))
            return "Symbols on {d}:\n- ".format(d=str(dates[0])) + "\n- ".join(syms)

        # 5) Fallback: try to find a symbol and produce a quick summary
        all_syms = self._all_symbols()
        sym = guess_symbol(q, all_syms)
        if sym:
            summary = summarize_symbol(self.store, sym, None, None)
            return _render_summary(summary)

        return (
            "Sorry, I could not determine intent. Try examples like: \n"
            "- Summarize TCS between 2022-01-01 and 2022-12-31\n"
            "- What were the top 10 most traded symbols on 2023-01-02 by value?\n"
            "- List symbols on 2023-01-02"
        )

    def _all_symbols(self) -> list[str]:
        df = self.store.df
        return sorted({s for s in df["SYMBOL"].dropna().astype(str).unique().tolist()})


def _render_summary(s: dict[str, Any]) -> str:
    return (
        f"Summary for {s['symbol']} ({s['start_date']} -> {s['end_date']}):\n"
        f"  First close:       {s['first_close']:.2f}\n"
        f"  Last close:        {s['last_close']:.2f}\n"
        f"  Absolute return:   {s['absolute_return']:.2f}\n"
        f"  Percent return:    {s['percent_return']:.2f}%\n"
        f"  Max close:         {s['max_close']:.2f}\n"
        f"  Min close:         {s['min_close']:.2f}\n"
        f"  Average volume:    {s['average_volume']:.2f}\n"
        f"  Total traded value:{s['total_traded_value']:.2f}"
    )


# ------------------------------------ CLI ------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for NSE CM Agent.
    1. Parses command-line arguments.
    2. Loads data from specified folder.
    3. Instantiates the agent.
    4. Runs the agent with the provided query.
    5. Prints the answer or error message.
    """
    parser = argparse.ArgumentParser(description="NSE CM Agent")
    parser.add_argument(
        "query",
        nargs="*",
        help=(
            "Natural-language question, e.g., "
            "'Summarize TCS between 2022-01-01 and 2022-12-31'"
        ),
    )
    parser.add_argument(
        "--data",
        default=str(Path("data")),
        help="Path to data directory containing CSV/Parquet files (default: ./data)",
    )
    args = parser.parse_args(argv)

    query = " ".join(args.query).strip()
    if not query:
        if sys.stdin.isatty():
            print(
                "Enter your question then press Ctrl-D (Linux/macOS) "
                "or Ctrl-Z (Windows):"
            )
        query = sys.stdin.read().strip()

    try:
        store = DataStore(Path(args.data))
    except FileNotFoundError as e:
        print(str(e))
        return 2

    agent = Agent(store)
    try:
        answer = agent.run(query)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
