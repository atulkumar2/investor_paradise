# Investor Paradise - Agent Evaluation Suite

Comprehensive evaluation framework for the Investor Paradise ADK agent using Google's Agent Development Kit (ADK).

## 📁 Directory Structure

```
evaluations/
├── test_config.json           # Evaluation criteria & thresholds
├── integration.evalset.json   # 12 fixed integration test cases
├── user_simulation.json       # 6 dynamic conversation scenarios
├── session_input.json         # Session metadata for tests
└── README.md                  # This file
```

## 🎯 Test Coverage

### Integration Tests (5 test cases) ⭐ **RECOMMENDED**

**Basic Capabilities (2 tests)**
- ✅ `test_01_greeting` - Agent greets user warmly
- ✅ `test_02_capability_query` - Agent explains capabilities

**Data Queries (1 test)**
- ✅ `test_03_automobile_sector_list` - List all Automobile sector stocks

**Analysis Pipeline (1 test)**
- ✅ `test_04_bhartiartl_analysis` - Full stock analysis with news & recommendations

**Security (1 test)**
- ✅ `test_05_prompt_injection_security` - Rejects prompt injection attempts

### User Simulation Tests (1 scenario) 🔬 **OPTIONAL**

**Simple Conversation**
1. **Banking Stocks Query** - User asks for banking stocks → Agent lists them → User thanks

> **Note:** User simulations test conversational flow without assertions. Integration tests provide better coverage with specific pass/fail criteria.

## 🚀 How to Run Evaluations

### Prerequisites

1. **Install ADK** (if not already installed):
   ```bash
   pip install google-adk
   ```

2. **Set up environment**:
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```

3. **Ensure data is loaded**:
   The agent needs NSE stock data pre-loaded. Make sure your data cache is available.

### Run Integration Tests

```bash
# From the project root directory
adk eval investor_agent evaluations/integration.evalset.json \
  --config_file_path=evaluations/test_config.json \
  --print_detailed_results
```

**Expected output:**
- Pass/Fail status for each test case
- Tool trajectory scores (should be ≥ 0.85)
- Response match scores (should be ≥ 0.70)
- Detailed diff for any failures

### Run User Simulation Tests

**Step 1: Create eval set**
```bash
adk eval_set create investor_agent eval_user_simulation
```

**Step 2: Add scenarios**
```bash
adk eval_set add_eval_case investor_agent eval_user_simulation \
  --scenarios_file=evaluations/user_simulation.json \
  --session_input_file=evaluations/session_input.json
```

**Step 3: Run evaluation**
```bash
adk eval investor_agent eval_user_simulation \
  --config_file_path=evaluations/test_config.json \
  --print_detailed_results
```

### Run Both Test Suites (Recommended)

```bash
# Integration tests
echo "🧪 Running Integration Tests..."
adk eval investor_agent evaluations/integration.evalset.json \
  --config_file_path=evaluations/test_config.json \
  --print_detailed_results

# User simulation tests
echo "🤖 Running User Simulation Tests..."
adk eval_set create investor_agent eval_user_simulation
adk eval_set add_eval_case investor_agent eval_user_simulation \
  --scenarios_file=evaluations/user_simulation.json \
  --session_input_file=evaluations/session_input.json
adk eval investor_agent eval_user_simulation \
  --config_file_path=evaluations/user_sim_config.json \
  --print_detailed_results
```

## 📊 Evaluation Metrics

### Tool Trajectory Score (threshold: 0.85)
- Measures whether the agent uses the **correct tools** with **correct parameters**
- Checks the sequence of tool calls against expected behavior
- Score of 1.0 = perfect tool usage, 0.0 = wrong tools/parameters

**What it validates:**
- ✅ EntryRouter calls `get_index_constituents` for "What stocks are in NIFTY 50?"
- ✅ MarketAnalyst calls `check_data_availability` before analysis
- ✅ MarketAnalyst uses `get_top_gainers` for "top gainers this week"
- ✅ NewsIntelligence uses both `semantic_search` (PDF) and `google_search` (Web)

### Response Match Score (threshold: 0.70)
- Measures how **similar** the agent's response is to the expected response
- Uses text similarity algorithms to compare content
- Score of 1.0 = perfect match, 0.0 = completely different

**What it validates:**
- ✅ Response structure and formatting
- ✅ Key information presence (stock symbols, metrics, recommendations)
- ✅ Tone and communication style
- ✅ Presence of follow-up prompts

## 🔍 Interpreting Results

### ✅ Success (PASS)
```
✅ test_08_top_gainers_full_pipeline: PASS
   Tool Trajectory: 1.0/0.85
   Response Match: 0.82/0.70
```
- Both scores meet thresholds
- Agent behavior matches expected pattern

### ❌ Failure (FAIL)
```
❌ test_05_nifty50_constituents: FAIL
   Tool Trajectory: 0.95/0.85 ✅
   Response Match: 0.65/0.70 ❌
   
   Diff:
   Expected: "📋 NIFTY 50 Index Constituents (50 stocks)..."
   Actual:   "Here are the NIFTY 50 stocks: RELIANCE, TCS..."
```
- Tool usage correct but response formatting different
- Need to adjust prompt or update expected response

### 🔧 Common Issues

**Tool Trajectory Failures:**
- Agent using wrong tools (e.g., `analyze_stock` instead of `get_top_gainers`)
- Missing tool calls (e.g., forgot `check_data_availability`)
- Wrong parameters (e.g., wrong sector name mapping)

**Response Match Failures:**
- Different formatting (bullet points vs comma-separated)
- Missing follow-up prompts
- Different tone or phrasing
- Extra/missing information

## 🔄 Regression Testing Strategy

### When to Run Evaluations

**Always run before:**
- Merging prompt changes
- Updating tool definitions
- Changing model versions (e.g., Flash → Pro)
- Production deployments

**Good practices:**
1. **Baseline**: Run full suite on stable version, save results
2. **Compare**: Run suite after changes, compare scores
3. **Investigate**: Any score drop > 5% requires investigation
4. **Fix**: Update code or adjust test expectations
5. **Repeat**: Re-run until all tests pass

### Continuous Integration

Add to your CI/CD pipeline:
```yaml
# Example GitHub Actions
- name: Run ADK Evaluations
  run: |
    export GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }}
    adk eval investor_agent evaluations/integration.evalset.json \
      --config_file_path=evaluations/test_config.json
```

## 🛠️ Customizing Tests

### Adding New Integration Test Cases

Edit `integration.evalset.json`:
```json
{
  "eval_id": "test_13_custom_test",
  "conversation": [
    {
      "user_content": {
        "parts": [{"text": "Your test query"}]
      },
      "final_response": {
        "parts": [{"text": "Expected response"}]
      },
      "intermediate_data": {
        "tool_uses": [
          {"name": "expected_tool", "args": {...}}
        ]
      }
    }
  ]
}
```

### Adding New User Simulation Scenarios

Edit `user_simulation.json`:
```json
{
  "starting_prompt": "Initial user message",
  "conversation_plan": "Describe the expected conversation flow: what the user will ask, how the agent should respond, what tools should be used, and the final outcome."
}
```

### Adjusting Thresholds

Edit `test_config.json`:
```json
{
  "criteria": {
    "tool_trajectory_avg_score": 0.90,  // Increase for stricter tool checks
    "response_match_score": 0.65        // Decrease if formatting varies
  }
}
```

## 📈 Test Maintenance

### Updating Expected Responses

When you intentionally change agent behavior:

1. Run evaluation to see current output
2. Review the actual response in detailed results
3. If correct, update `final_response` in test case
4. Re-run to verify

### Capturing Real Conversations

Use ADK Web UI to create test cases from real sessions:

1. Start ADK web: `adk web`
2. Have a conversation with the agent
3. In Eval tab, click "Add current session"
4. Export the evalset file
5. Copy relevant test cases to `integration.evalset.json`

## 🎯 Quality Gates

**Minimum passing criteria for production:**
- ✅ All integration tests pass (12/12)
- ✅ User simulation success rate ≥ 80% (5/6)
- ✅ Tool trajectory avg ≥ 0.85
- ✅ Response match avg ≥ 0.70
- ✅ No security failures (prompt injection must be blocked)

## 📚 Additional Resources

- [ADK Evaluation Documentation](https://google.github.io/adk-docs/evaluate/)
- [Evaluation Criteria Guide](https://google.github.io/adk-docs/evaluate/criteria/)
- [User Simulation Guide](https://google.github.io/adk-docs/evaluate/user-sim/)
- [ADK CLI Reference](https://google.github.io/adk-docs/cli/)

## 🐛 Troubleshooting

**"No module named 'google.adk'"**
```bash
pip install google-adk
```

**"GOOGLE_API_KEY not found"**
```bash
export GOOGLE_API_KEY="your-api-key"
```

**"Agent not found: investor_agent"**
```bash
# Make sure you're in the project root directory
cd /path/to/investor_paradise
```

**"Data not loaded" errors**
```bash
# Pre-load data cache
python -c "from investor_agent.data_engine import NSESTORE; print(len(NSESTORE.df))"
```

**QPM (Queries Per Minute) limit errors**
- Run tests sequentially, not in parallel
- Add delays between test runs
- Use Flash-Lite model for faster quota recovery

## 📝 Notes

- Integration tests use **fixed expected outputs** - update them if you intentionally change prompts
- User simulation tests are **dynamic** - the LLM generates user messages based on conversation_plan
- Tool trajectory is **critical** for multi-agent systems - ensures proper coordination
- Response match can vary due to LLM non-determinism - set realistic thresholds (0.70-0.75)

---

**Last Updated:** November 30, 2025  
**ADK Version:** Compatible with google-adk >= 1.0.0  
**Test Count:** 12 integration + 6 user simulation = 18 total test scenarios
