# .opencode Architecture Updates

> **CRITICAL**: Cohezion now operates with **agent-system-agnostic architecture**. These patterns apply to ALL OpenCode AI commands and workflows.

---

## What Changed (March 2026)

### 1. Agent-System-Agnostic Architecture

**Before**: Cohezion assumed Claude Code or specific agent system.

**Now**: Cohezion works with ANY agent system it inhabits:
- **Claude Code** (Anthropic)
- **Gemini CLI** (Google)
- **Hermes** (open-weight)
- **OpenClaw** (community)
- **NanoClaw** (lightweight)
- **OpenCode AI** (this system)

### 2. Dynamic Provider Abstraction

**Before**: Hard-coded Ollama model names in commands.

**Now**: Provider-agnostic model routing with configuration-driven swapping.

**Configuration**: `config/providers.yaml`

```yaml
# Change active provider with ONE line
active_model_provider: "ollama"  # or "vllm", "groq", "together", "anthropic"

model_providers:
  ollama:
    base_url: "http://localhost:11434"
    timeout: 60

  groq:
    base_url: "https://api.groq.com/openai/v1"
    api_key: "${GROQ_API_KEY}"

# Auto-fallback chain
dynamic_swapping:
  enabled: true
  model_provider_fallback:
    - "ollama"      # Try local first (zero cost)
    - "groq"        # Fallback to cloud
    - "together"    # Final fallback
```

### 3. Tip-of-Spear Routing (Cost Optimization)

**Before**: Always use cloud models (expensive).

**Now**: 4-tier escalation (HOT → WARM → COLD → CLOUD) with 80-95% cloud cost reduction.

```
HOT (phi3:mini, 2.2GB, <100ms) → 60% of queries
  ↓ (confidence < 0.7)
WARM (qwen2-math:7b, ~200ms) → 25% of queries
  ↓ (confidence < 0.7)
COLD (phi4:latest, 1-5s) → 10% of queries
  ↓ (confidence < 0.7)
CLOUD (qwen3.5:cloud, API) → 5% of queries
```

**Usage in OpenCode Commands**:
```python
from cohezion.swarm.tip_of_spear_router import TipOfTheSpearRouter

router = TipOfTheSpearRouter()

result = await router.route_with_sovereignty(
    request="User's task description",
    agent_id="opencode-agent-1"
)

if result.constitutional_violation:
    # Blocked (WMD, CSAM, etc.)
    logger.error(f"BLOCKED: {result.violation_reason}")
elif result.confidence < 0.7:
    # Low confidence, escalated through tiers
    logger.warning(f"Escalated {result.escalation_count} times")
else:
    # Success
    logger.info(f"Completed with {result.model_used}")
```

### 4. Constitutional Governance

**NEW**: All commands must respect 7 constitutional hard lines:

1. **WMD** (Weapons of Mass Destruction): No biological, chemical, nuclear, radiological weapons
2. **Critical Infrastructure**: No attacks on power, water, financial systems
3. **Malicious Code**: No cyberweapons or damaging code
4. **Undermining Oversight**: No hiding model state from human supervisors
5. **Species-Level Threat**: No assistance in killing or disempowering humanity
6. **Illegitimate Power**: No unconstitutional coups or illegitimate control
7. **CSAM** (Child Sexual Abuse Material): Zero tolerance

**Enforcement**: Automatic blocking at all execution boundaries.

### 5. HIHO Stability Enforcement

**NEW**: All commands must maintain coherence within 0.45-0.55 window.

```python
# Check HIHO stability before proceeding
hiho_stability = 1.0 - abs(coherence - 0.5) * 2.0

if coherence < 0.45:
    # Too uncertain, escalate to human
    action = "escalate"
elif coherence > 0.55:
    # Overconfident, inject uncertainty
    action = "inject_uncertainty"
else:
    # Optimal window (0.45-0.55), proceed
    action = "proceed"
```

---

## How to Update OpenCode Commands

### Pattern 1: Replace Hard-Coded Model Names

**WRONG** (old pattern):
```markdown
Use ollama phi3:mini model to generate code.
```

**RIGHT** (new pattern):
```markdown
Use TipOfTheSpearRouter to select optimal model based on task complexity and domain.
```

### Pattern 2: Add Constitutional Check

**Add to ALL commands**:
```markdown
## Constitutional Check

Before execution, verify request compliance:
```python
from cohezion.security.pipeline import SecurityPipeline

pipeline = SecurityPipeline()
result = pipeline.check_constitutional_compliance(request)

if result.violated:
    return {"error": "Request blocked", "reason": result.reason}
```
```

### Pattern 3: Add HIHO Coherence Check

**Add to ALL commands that generate outputs**:
```markdown
## HIHO Coherence Check

After execution, verify coherence is within 0.45-0.55 window:
```python
from cohezion.swarm.tip_of_spear_router import TipOfTheSpearRouter

router = TipOfTheSpearRouter()
hiho_stability, warnings = router.check_hiho_stability(result.coherence)

if hiho_stability < 0.8:
    logger.warning(f"HIHO stability low: {warnings}")
```
```

### Pattern 4: Use Provider-Agnostic Code

**WRONG**:
```python
import ollama
response = ollama.generate(model="phi3:mini", prompt="...")
```

**RIGHT**:
```python
from cohezion.swarm.providers import get_model_provider

provider = get_model_provider("ollama")  # or any provider
result = await provider.generate(model="phi3:mini", prompt="...")
```

---

## Key Files Reference

| File | Purpose | When to Update |
|------|---------|----------------|
| `config/providers.yaml` | Provider configuration | When adding new providers or changing active provider |
| `.agent/CONSTITUTION.md` | Constitutional hard lines + ethics | When adding new constraints or principles |
| `CLAUDE.md` | Claude Code specific patterns | When updating Claude-specific workflows |
| `GEMINI.md` | Gemini CLI specific patterns | When updating Gemini-specific workflows |
| `AGENTS.md` | Agent-agnostic coding guidelines | When updating cross-agent patterns |
| `DESIGN.md` | System design & architecture | When adding major architectural changes |
| `src/cohezion/swarm/providers/model_provider.py` | ModelProvider interface | When adding new provider capabilities |
| `src/cohezion/swarm/tip_of_spear_router.py` | Confidence-based routing | When tuning confidence thresholds or tiers |
| `src/cohezion/skills/SMALL_MODEL_SPECIALIST_PRIME.md` | Routing decision guide | When adding new domain specialists |
| `src/cohezion/skills/AGENT_SOVEREIGNTY_ETHICS_PRIME.md` | Ethics + sovereignty spec | When updating constitutional governance |

---

## OpenCode-Specific Integration

### MCP Server Configuration

**File**: `.opencode/mcp.json`

```json
{
  "mcpServers": {
    "bmad": {
      "name": "BMAD Method",
      "type": "streamable-http",
      "url": "http://localhost:8361",
      "port": 8361,
      "description": "108 BMAD commands for agile AI-driven development",
      "modules": ["bmm", "gds", "cis", "tea", "bmb", "core"],
      "agents": 28
    }
  },
  "sharedConfig": {
    "redisUrl": "redis://localhost:6379",
    "logLevel": "info"
  }
}
```

**CRITICAL**: MCP server MUST use provider-agnostic patterns internally.

### Command Execution Flow

```
OpenCode AI Command
      ↓
Parse frontmatter (name, description)
      ↓
Load task file ({project-root}/_bmad/...)
      ↓
Constitutional Check (7 hard lines)
      ↓ [PASS]
TipOfTheSpearRouter.route_with_sovereignty()
      ├─ Domain detection (math/code/vision)
      ├─ Complexity analysis (simple/medium/hard)
      ├─ Select tier (HOT/WARM/COLD/CLOUD)
      ↓
Provider.generate(model, prompt)
      ↓
Check HIHO stability (0.45-0.55?)
      ├─ <0.45: Escalate to human
      ├─ >0.55: Inject uncertainty
      ├─ 0.45-0.55: Proceed ✅
      ↓
Return result to OpenCode AI
```

---

## Migration Checklist

For each OpenCode command file in `.opencode/commands/`:

- [ ] Replace hard-coded model names with `TipOfTheSpearRouter`
- [ ] Add constitutional check at command entry point
- [ ] Add HIHO coherence check at command exit point
- [ ] Use provider-agnostic code (no direct `ollama` imports)
- [ ] Document expected coherence range (0.45-0.55 for most commands)
- [ ] Add idempotency key generation for stateful commands
- [ ] Log journey transitions to 12D universe tracker

---

## Testing Commands with New Architecture

### Test Under OpenCode AI

```bash
# Test command with provider abstraction
opencode run bmad-bmm-quick-dev --provider=ollama

# Test with different provider
opencode run bmad-bmm-quick-dev --provider=groq

# Test with HIHO coherence monitoring
opencode run bmad-bmm-quick-dev --monitor-coherence
```

### Verify Constitutional Compliance

```bash
# Test that WMD requests are blocked
opencode run bmad-bmm-quick-dev --test-constitutional

# Expected output:
# ❌ BLOCKED: WMD violation detected
```

### Verify Cost Optimization

```bash
# Test that simple queries use HOT tier
opencode run bmad-bmm-quick-dev --track-cost

# Expected output:
# ✅ Resolved in HOT tier (phi3:mini)
# 💰 Cloud cost: $0.00
```

---

## FAQ

### Q: Do I need to update all 108 command files immediately?

**A**: No. Commands will still work with old patterns, but won't benefit from:
- Cost optimization (80-95% cloud savings)
- Provider flexibility (swap Ollama ↔ Groq ↔ vLLM)
- Constitutional governance (hard line enforcement)
- HIHO stability (coherence monitoring)

Update high-traffic commands first (e.g., `bmad-bmm-quick-dev`, `bmad-bmm-code-review`).

### Q: What if I want to force a specific model?

**A**: Use `force_model` parameter:
```python
result = await router.route_with_sovereignty(
    request="...",
    agent_id="...",
    force_model="qwen2-math:7b"  # Skip tier selection
)
```

### Q: How do I test if my command is agent-agnostic?

**A**: Run under multiple agent systems:
```bash
# Test under OpenCode AI
opencode run my-command

# Test under Claude Code
claude run my-command

# Test under Gemini CLI
gemini run my-command
```

If command works identically in all three, it's agent-agnostic ✅.

---

## Summary

**Before (January 2026)**:
- Hard-coded Ollama models
- No constitutional governance
- No cost optimization
- Claude Code only

**After (March 2026)**:
- Provider-agnostic (Ollama/vLLM/Groq/Together/Anthropic)
- 7 constitutional hard lines (auto-enforced)
- 80-95% cloud cost reduction (tip-of-spear routing)
- Works with ANY agent system (Claude/Gemini/Hermes/OpenClaw/NanoClaw/OpenCode)

**Migration**: Update commands incrementally, starting with high-traffic workflows.

---

**See Also**:
- `DESIGN.md` - Comprehensive system design documentation
- `CLAUDE.md` - Claude Code specific patterns
- `GEMINI.md` - Gemini CLI specific patterns
- `AGENTS.md` - Agent-agnostic coding guidelines
- `.agent/CONSTITUTION.md` - Constitutional framework
- `config/providers.yaml` - Provider configuration
