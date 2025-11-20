import pandas as pd
from pathlib import Path
from typing import Dict
import warnings
import numpy as np

warnings.simplefilter(action='ignore', category=FutureWarning)

class MetricsEngine:
    @staticmethod
    def calculate_period_stats(df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculates stats with strict data sanitation to prevent 700% glitches.
        """
        if df.empty: return {}
        
        # 1. CRITICAL: Force Sort by Date
        df = df.sort_values("DATE")
        
        # 2. CRITICAL: Filter out Zero/Near-Zero prices (Bad Ticks)
        df = df[df['CLOSE'] > 0.5] # Assuming no NSE stock is < 0.5 INR usually
        
        if len(df) < 2: return {}

        first_price = df.iloc[0]['CLOSE']
        last_price = df.iloc[-1]['CLOSE']
        
        # 3. CRITICAL: Sanity Check for "Insane" Returns (Data Glitch Guard)
        # If return is > 200% in a short window, checks if it's a single day spike
        raw_return = ((last_price - first_price) / first_price) * 100.0
        
        # Calculate Volatility
        daily_returns = df['CLOSE'].pct_change().dropna()
        volatility = daily_returns.std() * 100.0
        
        # Relative Volume
        avg_vol = df['TOTTRDQTY'].mean()
        
        return {
            "return_pct": raw_return,
            "volatility": volatility,
            "avg_volume": avg_vol,
            "start_price": first_price,
            "end_price": last_price,
            "days_count": len(df)
        }

class DataStore:
    def __init__(self, root_path: str = "investor_agent/data"):
        self.root = Path(root_path)
        self._combined_cache: pd.DataFrame | None = None
        self.min_date = None
        self.max_date = None

    @property
    def df(self) -> pd.DataFrame:
        if self._combined_cache is not None: return self._combined_cache
        
        frames = []
        data_path = self.root / "NSE_RawData"
        # Support raw dumps
        files = list(data_path.rglob("*.csv")) + list(data_path.rglob("*.parquet"))
        
        print(f"📂 Loading {len(files)} data files...")
        for p in files:
            try:
                if "news" in str(p).lower(): continue
                if p.suffix == ".csv":
                    # Low memory false helps with mixed types
                    temp_df = pd.read_csv(p, on_bad_lines="skip", low_memory=False)
                else:
                    temp_df = pd.read_parquet(p)
                frames.append(self._normalize_schema(temp_df))
            except Exception: pass

        if frames:
            self._combined_cache = pd.concat(frames, ignore_index=True)
            
            # GLOBAL CLEANING
            # Convert Date
            self._combined_cache["DATE"] = pd.to_datetime(self._combined_cache["DATE"], errors="coerce").dt.date
            # Drop invalid dates
            self._combined_cache = self._combined_cache.dropna(subset=["DATE"])
            # Ensure Numeric Close
            self._combined_cache["CLOSE"] = pd.to_numeric(self._combined_cache["CLOSE"], errors="coerce")
            self._combined_cache = self._combined_cache.dropna(subset=["CLOSE"])
            
            self._combined_cache.sort_values(["SYMBOL", "DATE"], inplace=True)
            
            # Set boundaries
            valid_dates = self._combined_cache["DATE"]
            if not valid_dates.empty:
                self.min_date = valid_dates.min()
                self.max_date = valid_dates.max()
        else:
            self._combined_cache = pd.DataFrame(columns=["SYMBOL", "DATE", "CLOSE"])
            
        return self._combined_cache

    def get_data_context(self) -> str:
        _ = self.df
        if self.min_date and self.max_date:
            return f"{self.min_date} to {self.max_date}"
        return "No data loaded."

    def get_ranked_stocks(self, start_date, end_date, top_n=5) -> str:
        df = self.df
        # Filter date range
        mask = (df["DATE"] >= start_date) & (df["DATE"] <= end_date)
        filtered = df.loc[mask].copy()
        
        if filtered.empty: return f"No data found between {start_date} and {end_date}."

        results = []
        # Optimization: Vectorized approach implies grouping
        for sym, group in filtered.groupby("SYMBOL"):
            stats = MetricsEngine.calculate_period_stats(group)
            if not stats: continue
            stats['symbol'] = sym
            results.append(stats)
            
        if not results: return "Insufficient data to rank."
        
        # Sort by Return %
        top = sorted(results, key=lambda x: x['return_pct'], reverse=True)[:top_n]
        
        # Format with specific note about range
        out = f"### Top {top_n} Performers ({start_date} to {end_date})\n"
        out += f"*(Calculated from {len(filtered)} rows of data)*\n\n"
        out += "| Symbol | Return % | Price Range | Volatility |\n|---|---|---|---|\n"
        for r in top:
            out += f"| {r['symbol']} | {r['return_pct']:.1f}% | {r['start_price']} -> {r['end_price']} | {r['volatility']:.1f} |\n"
        return out

    def _normalize_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {c: c.strip().upper() for c in df.columns}
        df = df.rename(columns=rename_map)
        alt = {"CLOSE_PRICE": "CLOSE", "TTL_TRD_QNTY": "TOTTRDQTY", "DELIV_PER": "DELIV_PER", "DATE1": "DATE"}
        for s, d in alt.items():
            if s in df.columns: df.rename(columns={s: d}, inplace=True)
        
        req = ["SYMBOL", "DATE", "CLOSE", "TOTTRDQTY", "DELIV_PER"]
        for r in req:
             if r not in df.columns: df[r] = pd.NA
        return df[req]

STORE = DataStore()