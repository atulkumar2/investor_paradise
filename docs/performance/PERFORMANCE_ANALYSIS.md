# Performance Analysis Report

**Query:** "Which stocks grew more than 25% in recent 6 months. Only Small caps. Top 20."
**Date:** 2025-11-27 23:13:42

---

## ⏱️ Execution Timeline (Total: 66 seconds)

| Time         | Event                                | Duration  | Status          |
| ------------ | ------------------------------------ | --------- | --------------- |
| 23:13:42.551 | Query received                       | -         | ✅ Start        |
| 23:13:42.606 | **LLM Call #1**: Entry Router        | 1.8s      | ✅ Normal       |
| 23:13:44.436 | **LLM Call #2**: Market Analyst init | 2.3s      | ✅ Normal       |
| 23:13:46.694 | **Tool**: check_data_availability    | 0.01s     | ✅ Fast         |
| 23:13:46.705 | **LLM Call #3**: Planning next step  | 2.1s      | ✅ Normal       |
| 23:13:48.795 | **Tool**: get_market_cap_category    | 0.02s     | ✅ Fast         |
| 23:13:48.829 | **LLM Call #4**: Planning data fetch | 2.3s      | ✅ Normal       |
| 23:13:51.173 | **Tool**: get_top_gainers(20 stocks) | 2.4s      | ✅ Acceptable   |
| 23:13:53.581 | **LLM Call #5**: Processing results  | **35.1s** | 🔴 **CRITICAL** |
| 23:14:28.660 | **LLM Call #6**: News Analyst        | 2.5s      | ✅ Normal       |
| 23:14:31.215 | **LLM Call #7**: CIO Synthesizer     | **17.4s** | ⚠️ **SLOW**     |
| 23:14:48.624 | Response logged                      | -         | ✅ Complete     |

---

## 🚨 Critical Performance Issues

### **Issue #1: LLM Call #5 - 35 Second Delay**

**Location:** After `get_top_gainers` returns 20 stocks  
**Time:** 23:13:53.581 → 23:14:28.643 (35.1 seconds)

**Root Cause:**

- `get_top_gainers` returns complete stock data for 20 stocks
- Each stock includes: symbol, return_pct, price_start, price_end, volatility, delivery_pct
- This creates a ~500-1000 token response that the LLM must process
- The LLM then needs to format this into analysis, creating even more tokens

**Impact:** 53% of total execution time spent on a single LLM call

### **Issue #2: LLM Call #7 - 17 Second Delay**

**Location:** Final synthesis by CIO_Synthesizer  
**Time:** 23:14:31.215 → 23:14:48.616 (17.4 seconds)

**Root Cause:**

- SequentialAgent architecture passes ALL context from previous agents
- Context includes:
  - Entry Router output
  - Market Analyst full analysis (with 20 stock details)
  - News Analyst search results
  - All intermediate reasoning
- Large cumulative context (~2000-3000 tokens) forces slow processing

**Impact:** 26% of total execution time

**Combined Impact:** 79% of execution time spent in just 2 LLM calls

---

## 🎯 Optimization Recommendations

### **Priority 1: Reduce Tool Response Verbosity** 🔴 HIGH IMPACT

**Problem:** Tools return excessive data that bloats LLM context

**Solution:** Implement tiered response formats

```python
# Current: Always returns full details
def get_top_gainers(start_date, end_date, top_n=10) -> dict:
    return {
        "gainers": [
            {
                "rank": 1,
                "symbol": "STALLION",
                "return_pct": 224.5,
                "price_start": 45.2,
                "price_end": 146.7,
                "volatility": 12.3,
                "delivery_pct": 45.2
            },
            # ... 19 more stocks with full details
        ],
        "summary": {...}
    }

# Optimized: Return compact format by default
def get_top_gainers(
    start_date,
    end_date,
    top_n=10,
    detail_level="compact"  # NEW: compact|standard|full
) -> dict:
    if detail_level == "compact":
        return {
            "gainers": [
                {"symbol": "STALLION", "return": 224.5},
                {"symbol": "SKMEGGPROD", "return": 156.3},
                # ... compact format, ~50% fewer tokens
            ],
            "summary": {
                "avg_return": 120.45,
                "count": 20
            }
        }
```

**Expected Impact:** Reduce LLM Call #5 from 35s → 15-20s (~40% improvement)

---

### **Priority 2: Implement Context Pruning** 🟡 MEDIUM IMPACT

**Problem:** SequentialAgent passes all previous context to each agent

**Solution:** Add context management in prompts

```python
# In prompts.py - MERGER_AGENT_PROMPT
MERGER_AGENT_PROMPT = """
You are the CIO synthesizing the final report.

CONTEXT AVAILABLE:
- routing_decision: {routing_decision}
- market_analysis: {market_analysis}  # Already summarized
- news_results: {news_results}

DO NOT rehash all stock details. Focus on:
1. Key insights from market_analysis.summary
2. Top 3 stocks with highest conviction
3. Relevant news context
4. Actionable recommendations

Keep response under 500 words.
"""
```

**Expected Impact:** Reduce LLM Call #7 from 17s → 8-10s (~40% improvement)

---

### **Priority 3: Parallel Tool Execution** 🟢 LOW IMPACT (already fast)

**Current Flow:** Sequential tool calls

```
check_data_availability (0.01s)
→ LLM decides next tool
→ get_market_cap_category (0.02s)
→ LLM decides next tool
→ get_top_gainers (2.4s)
```

**Optimized:** Batch tool calls when possible

```python
# In Market Analyst agent configuration
tools_can_run_parallel = [
    "check_data_availability",
    "get_market_cap_category"
]
# Run both, then single LLM call to process results
```

**Expected Impact:** Save ~4s in LLM overhead between tool calls

---

### **Priority 4: Streaming Responses** 🟡 MEDIUM UX IMPACT

**Problem:** User waits 66s with no feedback

**Solution:** Enable streaming for long-running LLM calls

```python
# In sub_agents.py
market_agent = LlmAgent(
    name="MarketAnalyst",
    model=market_model,
    instruction=market_prompt,
    stream=True,  # Enable streaming
    ...
)
```

**Expected Impact:**

- No time savings, but perceived latency reduced
- User sees partial results in ~5s instead of waiting 35s

---

## 📊 Projected Improvements

| Optimization           | Current          | Optimized   | Savings                     |
| ---------------------- | ---------------- | ----------- | --------------------------- |
| Compact tool responses | 35s              | 15-20s      | ~15-20s                     |
| Context pruning        | 17s              | 8-10s       | ~7-9s                       |
| Parallel tools         | 10s LLM overhead | 6s          | ~4s                         |
| **Total**              | **66s**          | **~35-40s** | **~26-31s (40-47% faster)** |

---

## 🔧 Implementation Priority

1. **Week 1:** Implement compact tool responses (Priority 1)

   - Add `detail_level` parameter to all analysis tools
   - Update prompts to request compact format by default
   - Test with current query

2. **Week 2:** Add context pruning (Priority 2)

   - Update MERGER_AGENT_PROMPT with focused instructions
   - Add summary field to MarketAnalysisOutput schema
   - Modify SequentialAgent to pass only summaries

3. **Week 3:** Enable streaming (Priority 4)

   - Add stream=True to LLmAgent configs
   - Update CLI to display streaming responses
   - Test UX improvements

4. **Future:** Investigate parallel tool execution (Priority 3)
   - Requires ADK framework support
   - May need custom agent implementation

---

## 📝 Additional Observations

### LLM Call Patterns

- **7 total LLM calls** for one query
- Entry Router (1) → Market Analyst (4) → News Analyst (1) → CIO (1)
- Market Analyst makes 4 calls due to:
  1. Initial planning
  2. After data availability check
  3. After market cap check
  4. Processing results (the slow one)

### Tool Performance

All tools execute quickly:

- `check_data_availability`: 0.01s ✅
- `get_market_cap_category`: 0.02s ✅
- `get_top_gainers`: 2.4s ✅ (processing 2.9M records)

**Conclusion:** Tools are NOT the bottleneck; LLM processing is.

---

## 🎬 Next Steps

1. **Immediate:** Review `get_top_gainers` and other analysis tools
2. **Immediate:** Add `detail_level="compact"` parameter
3. **Short-term:** Update all tool outputs to use compact format
4. **Short-term:** Revise MERGER_AGENT_PROMPT for focused synthesis
5. **Medium-term:** Enable streaming for better UX

---

**Generated:** 2025-11-27  
**Analysis of:** cli_session_20251127_231304  
**Log Source:** investor_agent_logger.log lines 1160-1194
