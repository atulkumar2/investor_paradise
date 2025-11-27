#!/usr/bin/env python3
"""Quick performance test for compact format optimization."""

import json
import time

from investor_agent.tools import get_top_gainers

# Test with the same parameters used in the slow query
print("Testing compact vs full format...")
print("=" * 60)

# Test 1: Compact format (new default)
start = time.time()
result_compact = get_top_gainers(
    start_date="2025-05-25",
    end_date="2025-11-25",
    top_n=20,
    detail_level="compact"
)
compact_time = time.time() - start

# Test 2: Full format (old behavior)
start = time.time()
result_full = get_top_gainers(
    start_date="2025-05-25",
    end_date="2025-11-25",
    top_n=20,
    detail_level="full"
)
full_time = time.time() - start

# Calculate response sizes (rough token estimate)
compact_json = json.dumps(result_compact)
full_json = json.dumps(result_full)

compact_tokens = len(compact_json) // 4  # Rough estimate
full_tokens = len(full_json) // 4

print("\n📊 COMPACT FORMAT:")
print(f"   Execution time: {compact_time:.3f}s")
print(f"   Response size: {len(compact_json):,} chars (~{compact_tokens:,} tokens)")
print(f"   Sample: {result_compact['gainers'][0]}")

print("\n📊 FULL FORMAT:")
print(f"   Execution time: {full_time:.3f}s")
print(f"   Response size: {len(full_json):,} chars (~{full_tokens:,} tokens)")
print(f"   Sample: {result_full['gainers'][0]}")

print("\n✅ IMPROVEMENT:")
print(f"   Token reduction: {full_tokens - compact_tokens:,} fewer ({(1 - compact_tokens/full_tokens)*100:.1f}% smaller)")
print(f"   Expected LLM speedup: ~{(full_tokens/compact_tokens):.1f}x faster processing")

print("\n💡 ESTIMATED PERFORMANCE GAIN:")
print(f"   Previous LLM call #5: 35 seconds (processing {full_tokens:,} tokens)")
print(f"   New LLM call #5: ~{35 * compact_tokens / full_tokens:.1f} seconds (processing {compact_tokens:,} tokens)")
print(f"   Savings: ~{35 - (35 * compact_tokens / full_tokens):.1f} seconds")

print("\n" + "=" * 60)
