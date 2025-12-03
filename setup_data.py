#!/usr/bin/env python3
"""
Data Setup Script for Investor Paradise
========================================

This script downloads required data files for running the ADK web interface locally.
Only needed if you're running the agent via 'adk web' command after cloning the repo.

The CLI automatically handles data downloads, so this script is NOT needed for CLI usage.

What it downloads:
- Stock market data (49MB parquet file)
- Index/sector mappings (3 small cache files)
- News vector database (for semantic search)

Data source: GitHub releases
Destination: investor_agent/data/
"""

import sys
from pathlib import Path


def main():
    """Download all required data files for ADK web interface."""
    
    print("=" * 70)
    print("🚀 Investor Paradise - Data Setup")
    print("=" * 70)
    print("\n📦 This will download ~50MB of data from GitHub releases")
    print("📍 Destination: investor_agent/data/\n")
    
    # Check if we're in the right directory
    if not Path("investor_agent").exists():
        print("❌ Error: Run this script from the repository root directory")
        print("   Current directory should contain 'investor_agent' folder\n")
        sys.exit(1)
    
    # Import cache manager
    try:
        from investor_agent.cache_manager import (
            download_all_data_from_github,
            check_data_exists
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure dependencies are installed: uv sync\n")
        sys.exit(1)
    
    # Check if data already exists
    if check_data_exists():
        print("✅ Data files already exist!\n")
        response = input("   Re-download anyway? (y/N): ").strip().lower()
        if response != 'y':
            print("\n✅ Setup complete - data is ready!\n")
            return
        print("\n🔄 Re-downloading data...\n")
    
    # Download data
    print("⬇️  Downloading data from GitHub...\n")
    success = download_all_data_from_github(clean_first=False)
    
    if success:
        print("\n" + "=" * 70)
        print("✅ Data setup complete!")
        print("=" * 70)
        print("\n📂 Downloaded files:")
        print("   • investor_agent/data/cache/combined_data.parquet (49MB)")
        print("   • investor_agent/data/cache/nse_indices_cache.parquet")
        print("   • investor_agent/data/cache/nse_sector_cache.parquet")
        print("   • investor_agent/data/cache/nse_symbol_company_mapping.parquet")
        print("   • investor_agent/data/vector-data/ (news embeddings)")
        print("\n🎉 You can now run: adk web")
        print("   Then open: http://localhost:8000\n")
    else:
        print("\n" + "=" * 70)
        print("❌ Data download failed!")
        print("=" * 70)
        print("\n🔍 Troubleshooting:")
        print("   • Check your internet connection")
        print("   • Verify GitHub is accessible")
        print("   • Try running again in a few minutes")
        print("\n💡 You can still use the CLI - it handles downloads automatically\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
