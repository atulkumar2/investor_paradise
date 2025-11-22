import pandas as pd
from pathlib import Path
from typing import Dict, Optional
import warnings
import numpy as np
from datetime import datetime, date
import os

warnings.simplefilter(action='ignore', category=FutureWarning)

class MetricsEngine:
    """
    Clean, accurate stock metrics calculator for NSE data.
    Phase 1: Focus on simple, reliable calculations.
    """
    
    @staticmethod
    def calculate_period_stats(df: pd.DataFrame) -> Optional[Dict[str, float]]:
        """
        Calculate stock performance metrics over a period.
        
        Input: DataFrame with columns [DATE, OPEN, CLOSE, HIGH, LOW, VOLUME, DELIV_PER]
        Returns: Dict with return_pct, volatility, avg_delivery, price info, etc.
        """
        if df.empty or len(df) < 2:
            return None
        
        # Sort by date (critical for correct calculations)
        df = df.sort_values("DATE").copy()
        
        # Data validation: Remove invalid prices
        df = df[df['CLOSE'] > 0]
        if len(df) < 2:
            return None
        
        # Basic price metrics
        first_price = df.iloc[0]['CLOSE']
        last_price = df.iloc[-1]['CLOSE']
        period_return = ((last_price - first_price) / first_price) * 100.0
        
        # Volatility (std deviation of daily returns)
        daily_returns = df['CLOSE'].pct_change().dropna()
        volatility = daily_returns.std() * 100.0 if len(daily_returns) > 0 else 0.0
        
        # Volume metrics
        avg_volume = df['VOLUME'].mean()
        total_volume = df['VOLUME'].sum()
        
        # Delivery percentage (indicates institutional buying)
        avg_delivery = df['DELIV_PER'].mean() if 'DELIV_PER' in df.columns else 0.0
        
        # Price range
        period_high = df['HIGH'].max()
        period_low = df['LOW'].min()
        
        # Advanced metrics for professional analysis
        
        # Max Drawdown - largest peak-to-trough decline
        cumulative_returns = (1 + daily_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min() * 100.0 if len(drawdown) > 0 else 0.0
        
        # Moving averages (if enough data)
        sma_20 = df['CLOSE'].tail(20).mean() if len(df) >= 20 else last_price
        sma_50 = df['CLOSE'].tail(50).mean() if len(df) >= 50 else last_price
        
        # Consecutive up/down days
        price_changes = df['CLOSE'].diff()
        consecutive_ups = 0
        consecutive_downs = 0
        current_streak = 0
        
        for change in price_changes.iloc[-10:]:  # Last 10 days
            if pd.isna(change):
                continue
            if change > 0:
                current_streak = current_streak + 1 if current_streak > 0 else 1
                consecutive_ups = max(consecutive_ups, current_streak)
            elif change < 0:
                current_streak = current_streak - 1 if current_streak < 0 else -1
                consecutive_downs = max(consecutive_downs, abs(current_streak))
            else:
                current_streak = 0
        
        # Distance from period high/low (support/resistance)
        distance_from_high = ((last_price - period_high) / period_high) * 100.0
        distance_from_low = ((last_price - period_low) / period_low) * 100.0
        
        # Volume trend (comparing recent vs older volume)
        if len(df) >= 10:
            recent_vol = df['VOLUME'].tail(5).mean()
            older_vol = df['VOLUME'].iloc[:-5].mean() if len(df) > 5 else recent_vol
            volume_trend = ((recent_vol - older_vol) / older_vol * 100.0) if older_vol > 0 else 0.0
        else:
            volume_trend = 0.0
        
        # Price momentum (rate of change)
        momentum = ((last_price - df.iloc[len(df)//2]['CLOSE']) / df.iloc[len(df)//2]['CLOSE'] * 100.0) if len(df) >= 4 else 0.0
        
        return {
            # Basic metrics
            "return_pct": round(period_return, 2),
            "volatility": round(volatility, 2),
            "start_price": round(first_price, 2),
            "end_price": round(last_price, 2),
            "period_high": round(period_high, 2),
            "period_low": round(period_low, 2),
            "avg_volume": int(avg_volume),
            "total_volume": int(total_volume),
            "avg_delivery_pct": round(avg_delivery, 2),
            "days_count": len(df),
            "start_date": df.iloc[0]['DATE'],
            "end_date": df.iloc[-1]['DATE'],
            
            # Advanced trading metrics
            "max_drawdown": round(max_drawdown, 2),
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "consecutive_ups": consecutive_ups,
            "consecutive_downs": consecutive_downs,
            "distance_from_high_pct": round(distance_from_high, 2),
            "distance_from_low_pct": round(distance_from_low, 2),
            "volume_trend_pct": round(volume_trend, 2),
            "momentum_pct": round(momentum, 2)
        }

class NSEDataStore:
    """
    Manages NSE stock data loading and querying.
    Handles bhavdata CSV files with proper schema normalization.
    """
    
    def __init__(self, root_path: str = "investor_agent/data"):
        self.root = Path(root_path)
        self.cache_file = self.root / "cache" / "combined_data.parquet"
        self._combined_cache: Optional[pd.DataFrame] = None
        self.min_date: Optional[date] = None
        self.max_date: Optional[date] = None
        self.total_symbols: int = 0
    

    @property
    def df(self) -> pd.DataFrame:
        """Load and cache all NSE data files."""
        
        if self._combined_cache is not None:
            return self._combined_cache
        
        # Check if parquet cache exists and is fresh
        if self._should_use_cache():
            print("📦 Loading from parquet cache...")
            self._combined_cache = pd.read_parquet(self.cache_file)
            self._update_metadata()
            print(f"✅ Loaded {len(self._combined_cache):,} rows from cache")
            return self._combined_cache
        
        # Cache miss or stale - load from CSVs
        frames = []
        data_path = self.root / "NSE_RawData"
        files = list(data_path.rglob("*.csv"))
        
        print(f"📂 Loading {len(files)} NSE data files from CSV...")
        
        for file_path in files:
            try:
                # Skip non-stock data
                if "news" in file_path.name.lower():
                    continue
                
                # Read CSV with proper handling
                temp_df = pd.read_csv(file_path, on_bad_lines="skip", low_memory=False)
                normalized = self._normalize_schema(temp_df)
                
                if not normalized.empty:
                    frames.append(normalized)
                    
            except Exception as e:
                print(f"⚠️  Skipping {file_path.name}: {e}")
                continue
        
        if frames:
            self._combined_cache = pd.concat(frames, ignore_index=True)
            
            # Data cleaning - keep as datetime for easier filtering
            self._combined_cache["DATE"] = pd.to_datetime(
                self._combined_cache["DATE"], 
                format="%d-%b-%Y",
                errors="coerce"
            )
            
            # Remove invalid rows
            self._combined_cache = self._combined_cache.dropna(subset=["DATE", "CLOSE"])
            
            # Ensure numeric types
            numeric_cols = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME", "DELIV_PER"]
            for col in numeric_cols:
                self._combined_cache[col] = pd.to_numeric(
                    self._combined_cache[col], 
                    errors="coerce"
                )
            
            # Remove rows with invalid prices
            self._combined_cache = self._combined_cache[self._combined_cache["CLOSE"] > 0]
            
            # Sort for efficient querying
            self._combined_cache.sort_values(["SYMBOL", "DATE"], inplace=True)
            
            # Update metadata
            self._update_metadata()
                
            print(f"✅ Loaded {len(self._combined_cache):,} rows")
            print(f"   Date range: {self.min_date} to {self.max_date}")
            print(f"   Unique symbols: {self.total_symbols:,}")
            
            # Save to parquet cache for next time
            self._save_cache()
        else:
            self._combined_cache = pd.DataFrame(
                columns=["SYMBOL", "SERIES", "DATE", "OPEN", "HIGH", "LOW", 
                        "CLOSE", "VOLUME", "DELIV_PER"]
            )
            print("⚠️  No data loaded!")
            
        return self._combined_cache

    def get_data_context(self) -> str:
        """Get human-readable data range summary."""
        _ = self.df  # Ensure loaded
        if self.min_date and self.max_date:
            return f"{self.min_date} to {self.max_date}"
        return "No data loaded."

    def get_stock_data(self, symbol: str, start_date: Optional[date] = None, 
                       end_date: Optional[date] = None) -> pd.DataFrame:
        """Get data for a specific stock, optionally filtered by date range."""
        df = self.df
        stock_df = df[df["SYMBOL"] == symbol.upper()].copy()
        
        if start_date:
            stock_df = stock_df[stock_df["DATE"] >= pd.Timestamp(start_date)]
        if end_date:
            stock_df = stock_df[stock_df["DATE"] <= pd.Timestamp(end_date)]
            
        return stock_df.sort_values("DATE")

    def get_ranked_stocks(self, start_date: date, end_date: date, 
                         top_n: int = 10, metric: str = "return") -> pd.DataFrame:
        """
        Rank stocks by performance metric over a date range.
        
        Args:
            start_date: Period start date
            end_date: Period end date
            top_n: Number of top stocks to return
            metric: 'return' or 'volume'
            
        Returns:
            DataFrame with ranked stocks and their metrics
        """
        df = self.df
        
        # Filter date range - convert date objects to pandas Timestamps
        mask = (df["DATE"] >= pd.Timestamp(start_date)) & (df["DATE"] <= pd.Timestamp(end_date))
        filtered = df[mask].copy()
        
        if filtered.empty:
            return pd.DataFrame()
        
        # Calculate metrics for each stock
        results = []
        for symbol, group in filtered.groupby("SYMBOL"):
            stats = MetricsEngine.calculate_period_stats(group)
            if stats:
                stats['symbol'] = symbol
                results.append(stats)
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame and sort
        results_df = pd.DataFrame(results)
        
        if metric == "return":
            results_df = results_df.sort_values("return_pct", ascending=False)
        elif metric == "volume":
            results_df = results_df.sort_values("total_volume", ascending=False)
        
        return results_df.head(top_n)

    def _normalize_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize different NSE file formats to a common schema.
        Handles both sec_bhavdata and BhavCopy formats.
        """
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        # Strip whitespace from string columns
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()
        
        # Standardize column names
        rename_map = {
            "DATE1": "DATE",
            "CLOSE_PRICE": "CLOSE",
            "OPEN_PRICE": "OPEN",
            "HIGH_PRICE": "HIGH",
            "LOW_PRICE": "LOW",
            "TTL_TRD_QNTY": "VOLUME",
            "DELIV_PER": "DELIV_PER",
            # BhavCopy format
            "TradDt": "DATE",
            "TckrSymb": "SYMBOL",
            "SctySrs": "SERIES",
            "OpnPric": "OPEN",
            "HghPric": "HIGH",
            "LwPric": "LOW",
            "ClsPric": "CLOSE",
            "TtlTradgVol": "VOLUME"
        }
        
        df = df.rename(columns=rename_map)
        
        # Filter to equity stocks only (SERIES = 'EQ')
        if "SERIES" in df.columns:
            df = df[df["SERIES"] == "EQ"].copy()
        
        # Ensure required columns exist
        required = ["SYMBOL", "DATE", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]
        for col in required:
            if col not in df.columns:
                df[col] = pd.NA
        
        # Optional column
        if "DELIV_PER" not in df.columns:
            df["DELIV_PER"] = 0.0
        
        # Select and return only needed columns
        final_cols = ["SYMBOL", "SERIES", "DATE", "OPEN", "HIGH", "LOW", 
                     "CLOSE", "VOLUME", "DELIV_PER"]
        
        return df[[col for col in final_cols if col in df.columns]]
    
    def _should_use_cache(self) -> bool:
        """Check if parquet cache exists and is newer than CSV files."""
        if not self.cache_file.exists():
            return False
        
        cache_mtime = os.path.getmtime(self.cache_file)
        data_path = self.root / "NSE_RawData"
        
        # Check if any CSV is newer than cache
        for csv_file in data_path.rglob("*.csv"):
            if os.path.getmtime(csv_file) > cache_mtime:
                print(f"⚠️  Cache stale: {csv_file.name} is newer")
                return False
        
        return True
    
    def _save_cache(self) -> None:
        """Save combined DataFrame to parquet cache."""
        if self._combined_cache is None or self._combined_cache.empty:
            return
        
        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self._combined_cache.to_parquet(self.cache_file, index=False)
            print(f"💾 Saved cache to {self.cache_file}")
        except Exception as e:
            print(f"⚠️  Failed to save cache: {e}")
    
    def _update_metadata(self) -> None:
        """Update min_date, max_date, total_symbols from cached DataFrame."""
        if self._combined_cache is not None and not self._combined_cache.empty:
            self.min_date = self._combined_cache["DATE"].min().date()
            self.max_date = self._combined_cache["DATE"].max().date()
            self.total_symbols = self._combined_cache["SYMBOL"].nunique()


# Global singleton instance
NSESTORE = NSEDataStore()

# NOTE: Eager loading happens in agent.py to ensure it runs when `adk web` starts
# This keeps data_engine.py importable without side effects for testing