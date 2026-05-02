# Ollama Gemma4 Integration Guide

## Overview

Offload tasks to **Gemma4** (local/free via Ollama) to extend **kimi-k2.5:cloud** availability.

## Gemma4 Task Allocation

### Tasks for Gemma4 (Fast/Free)
- ✅ Code formatting and linting
- ✅ Documentation and comments
- ✅ Simple refactor suggestions
- ✅ Log analysis and error summarization
- ✅ Submission status checking
- ✅ Parameter variant generation
- ✅ Code review (obvious issues only)
- ✅ Test case generation
- ✅ Summarization tasks

### Tasks for kimi-k2.5:cloud (Reserved)
- 🔥 GPU kernel optimization
- 🔥 Performance breakthrough analysis
- 🔥 Complex architectural decisions
- 🔥 HIP/ROCm low-level code
- 🔥 MFMA instruction optimization
- 🔥 Novel algorithm design

## Setup

### 1. Install Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Pull Gemma4
```bash
ollama pull gemma4
ollama pull gemma4:9b  # Larger variant if needed
```

### 3. Verify
```bash
ollama run gemma4 "Say hello"
```

## Usage

### Direct Command Line
```bash
# Quick analysis
ollama run gemma4 "Review this code: $(cat submission.py)"

# Variant generation
ollama run gemma4 "Generate 3 variants of block size 128, 256, 512"

# Log summary
tail -100 /tmp/overnight.log | ollama run gemma4 "Summarize issues"
```

### Python Integration
```python
# ollama_task_router.py
result = offload_to_gemma("code_review", kernel_code)
result = offload_to_gemma("log_analysis", log_content)
```

### Enhanced Overnight System
```bash
# Start with Gemma4 enhancement
./gemma4_overnight_enhanced.sh

# Gemma4 will:
# - Analyze failed submissions
# - Suggest parameter tweaks
# - Summarize log patterns
```

## Task Router

The `ollama_task_router.py` automatically classifies:

```python
classify_task("Format this code for PEP8")  # -> gemma4
classify_task("Optimize MFMA instructions")  # -> kimik2.5-cloud
classify_task("Count test cases")  # -> gemma4
classify_task("Design breakthough kernel")  # -> kimik2.5-cloud
```

## Benefits

1. **Cost Savings**: Gemma4 is free, runs locally
2. **Speed**: Gemma4 responds in seconds for simple tasks
3. **Extended Cloud**: Reserve kimi-k2.5 for critical tasks
4. **24/7 Operation**: Local models don't have rate limits

## Monitoring

```bash
# Check Gemma4 status
ollama ps

# Monitor overnight logs
tail -f /tmp/overnight_gemma4_$(date +%Y%m%d).log

# See what Gemma4 suggested
grep -A 5 "Gemma4 analysis:" /tmp/overnight_gemma4_*.log
```

## Example Workflow

1. **Overnight system** submits kernel
2. **Submission fails** with error
3. **Gemma4** analyzes error log (seconds)
4. **Gemma4** suggests quick fix
5. **Next iteration** applies suggested fix
6. **kimi-k2.5:cloud** reserved for complex breakthroughs

## Integration with Existing System

```bash
# Option 1: Run standalone
./gemma4_overnight_enhanced.sh

# Option 2: Chain with existing
./PRODUCTION_NIGHTLY.sh &
./ollama_task_router.py monitor &
```

## Verification

Test that everything works:
```bash
echo "Test Gemma4 integration" | ollama run gemma4
# Should respond with text
```
