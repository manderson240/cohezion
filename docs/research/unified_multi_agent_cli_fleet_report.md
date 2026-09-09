# Unified Multi-Agent CLI Fleet Execution Report

**Date:** 2026-08-27 13:12:03 UTC  
**Total Agents Invoked:** 5  
**Memory State:** 26.51 GiB Avail / 26.43 GiB Floor  

---

### 🤖 Agent: `Claude Code CLI`
- **Status:** `SUCCESS`
- **Latency:** 18.04s
- **Output:**
```
I can't confirm that — I only verified the module exists (`src/cohezion/reliability/system_wide_fleet_lock.py` plus 5 launcher/test scripts). Safety under concurrent CLI agents needs actually reading the lock semantics and stress-test report.
```

---

### 🤖 Agent: `Hermes Agent CLI`
- **Status:** `SUCCESS`
- **Latency:** 4.98s
- **Output:**
```
HTTP 404: Model 'waslmedia-qwen3-4b-Q4_K_M' was not found. Available models include: 'ACE-Step-Music', 'Anima-Aesthetic', 'Anima-Base', and 146 more. Use 'lemonade list' or GET /api/v1/models?show_all=true to see all available models.
```

---

### 🤖 Agent: `OpenCode CLI`
- **Status:** `EXIT_1`
- **Latency:** 10.86s
- **Output:**
```
[0m
> build · Granite-4.1-8B-GGUF
[0m
[91m[1mError: [0mModel 'Granite-4.1-8B-GGUF' was not found. Available models include: 'ACE-Step-Music', 'Anima-Aesthetic', 'Anima-Base', and 146 more. Use 'lemonade list' or GET /api/v1/models?show_all=true to see all available models.
```

---

### 🤖 Agent: `Pi CLI`
- **Status:** `EXIT_1`
- **Latency:** 2.47s
- **Output:**
```
Warning: No models match pattern "kimi-k2.5:cloud"
Warning: Invalid thinking level "31b-cloud" in pattern "gemma4:31b-cloud". Using default instead.
Warning: No models match pattern "glm-5.1:cloud"
Warning: No models match pattern "minimax-m2.7:cloud"
Warning: No models match pattern "glm-5:cloud"
Warning: No models match pattern "kimi-k2.6:cloud"
404: {"code":"model_not_found","message":"Model 'Liujgoj-Cantonese-Gemma4-12b-Base-i1-GGUF-Q6_K' was not found. Available models include: 'ACE-Step-Music', 'Anima-Aesthetic', 'Anima-Base', and 146 more. Use 'lemonade list' or GET /api/v1/models?show_all=true to see all available models.","param":"model","requested_model":"Liujgoj-Cantonese-Gemma4-12b-Base-i1-GGUF-Q6_K","type":"model_not_found"}
```

---

### 🤖 Agent: `Local Qwen Coder / DeepSeek Harness`
- **Status:** `SUCCESS`
- **Latency:** 0.96s
- **Output:**
```
Qwen Coder parses ARC task logic into an AST, then compiles it to compact bytecode that AMD Strix Halo’s NPU executes directly for fast inference.
```

---

