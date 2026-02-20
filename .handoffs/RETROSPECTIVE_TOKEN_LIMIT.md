# RETROSPECTIVE: Token Limit Error Prevention

## What Happened
- API benchmark runner failed with "requested too many tokens" error
- Default `max_tokens=2048` exceeded API limits when combined with prompt

## Root Cause
1. Default 2048 tokens too high for API limits
2. No token budget calculation based on prompt size
3. No error handling for token limit errors
4. No retry logic

## Solution Implemented

### All 5 Phases Complete:

1. **Quick Fix**: Reduced default max_tokens from 2048 → 512
2. **Token Budget**: Added `calculate_max_tokens(prompt)` method
3. **Error Handling**: Added auto-retry with token reduction (3 attempts)
4. **CLI**: Added `--max-tokens` and `--token-budget` flags
5. **Integration**: Updated integrated_runner.py with safe defaults

## Files Modified

- `src/cohezion/eval/api_runner.py` - Complete rewrite with all fixes
- `src/cohezion/eval/integrated_runner.py` - Safe defaults

## New Features

| Feature | Implementation |
|----------|---------------|
| Auto token calculation | `calculate_max_tokens()` based on prompt |
| Error handling | Auto-retry with 2x token reduction |
| Rate limiting | Backoff on rate limit errors |
| CLI flags | `--max-tokens`, `--token-budget` |

## Usage

```bash
# Auto-calculate (recommended)
uv run python -m cohezion.eval.api_runner --provider anthropic --limit 10

# Explicit max tokens
uv run python -m cohezion.eval.api_runner --limit 10 --max-tokens 512

# Custom token budget
uv run python -m cohezion.eval.api_runner --limit 10 --token-budget 8192
```

## Next Steps

1. Run benchmark with new API runner
2. Test with different providers (OpenAI)
3. Expand to SWE-bench
4. Integrate with FLUME journey tracking
