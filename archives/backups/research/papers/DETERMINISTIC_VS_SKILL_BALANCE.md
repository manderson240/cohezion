# Balanced Approach: Deterministic Scripts vs Skill-Based Heuristics

## The Problem: When to Use Which?

**Deterministic Scripts** (Code that just works):
- ✅ Reliable, tested, predictable
- ✅ Exact format matching
- ✅ No ambiguity
- ❌ Fails on unknown inputs
- ❌ Brittle to format changes

**Skill-Based Heuristics** (Patterns that adapt):
- ✅ Handles unknown formats
- ✅ Flexible, adaptive
- ✅ Graceful degradation
- ❌ Less reliable
- ❌ May produce false positives

**The Balance**: Use deterministic where possible, heuristics only when necessary.

---

## Our Implementation

### Actual Results

```
Total models: 37
  Deterministic: 3 (8.1%)
  Heuristic: 34 (91.9%)

⚠️ Heuristic Fallbacks: 1
  (Consider improving deterministic parsers)
```

**Interpretation**: Our deterministic FLM parser failed, so we fell back to heuristic parsing which discovered 34 models. This is **correct behavior** but indicates the deterministic parser needs improvement.

---

## The Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 BALANCED DISCOVERY                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DETERMINISTIC (First Try)                                  │
│  ├── Known validated models (always works)                  │
│  │   └── qwen3:4b, Gemma-4-E2B, Jan-v1-4B                  │
│  │                                                           │
│  ├── FLM list with exact format parsing                     │
│  │   └── Format: "model:size ⏬"                           │
│  │   └── Return code handling                               │
│  │                                                           │
│  └── Local file discovery (glob patterns)                   │
│      └── *.gguf in ~/.cache/flm/models                      │
│                                                             │
│  When Deterministic Fails:                                  │
│        ↓                                                    │
│  HEURISTIC FALLBACK (Skill-Based)                          │
│  ├── Pattern matching for unknown formats                   │
│  │   └── Lines with colons might be models                 │
│  │   └── Version markers (1.0, v2, etc.)                  │
│  │                                                           │
│  ├── Known model prefix detection                           │
│  │   └── "qwen", "gemma", "llama" in name                   │
│  │                                                           │
│  └── Capability inference from name                         │
│      └── "code" → code_generation                          │
│      └── "vl" → vision_understanding                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Guidelines for Balance

### Use DETERMINISTIC When:

1. **Format is known and stable**
   ```python
   # FLM format is documented as "model:size ⏬"
   def parse_flm_deterministic(line):
       if "⏬" not in line:  # Exact check
           return None
       return line.split()[0]
   ```

2. **Input is validated**
   ```python
   # Known working models
   KNOWN_MODELS = [
       {"name": "qwen3:4b", "tps": 75.0},  # Hardcoded, tested
   ]
   ```

3. **Side effects must be controlled**
   ```python
   # Exact resource limits
   timeout = 10  # seconds, exact
   ```

### Use HEURISTICS When:

1. **Format is unknown or variable**
   ```python
   # Parser might see:
   # "qwen3:4b" or "Qwen3-4B" or "Qwen3 4B"
   # Heuristic: Look for digits and common prefixes
   ```

2. **Inferring intent from partial data**
   ```python
   # From model name "qwen3-coder-4b"
   # Heuristic: "coder" → code capability
   capabilities = infer_from_name(name)
   ```

3. **Graceful degradation is acceptable**
   ```python
   try:
       return deterministic_parse(data)
   except:
       return heuristic_parse(data)  # Might not be perfect
   ```

---

## Code Example: Clear Separation

```python
class BalancedDiscovery:
    """Clear separation of concerns."""
    
    def discover_flm(self) -> List[Model]:
        """Deterministic first."""
        try:
            result = subprocess.run(["flm", "list"], ...)
            
            # Deterministic parsing
            for line in result.stdout.split("\n"):
                model = self._parse_flm_line_deterministic(line)
                if model:
                    return model
        except:
            pass  # Expected to fail sometimes
        
        # Fallback to heuristic ONLY when deterministic fails
        return self._discover_flm_heuristic()
    
    def _parse_flm_line_deterministic(self, line: str) -> Optional[Model]:
        """No ambiguity. Exact rules."""
        line = line.strip()
        
        # Rule 1: Must have download indicator
        if "⏬" not in line:
            return None
        
        # Rule 2: Must have size separator
        if ":" not in line:
            return None
        
        # Rule 3: Extract first token
        parts = line.split()
        return parts[0] if parts else None
    
    def _discover_flm_heuristic(self) -> List[Model]:
        """Skill-based pattern matching."""
        models = []
        
        for line in output.split("\n"):
            # Heuristic 1: Lines with colons
            if ":" in line and len(line) > 3:
                parts = line.split()
                if parts and self._looks_like_model(parts[0]):
                    models.append(parts[0])
        
        return models
    
    def _looks_like_model(self, name: str) -> bool:
        """Heuristic: pattern matching."""
        lower = name.lower()
        
        # Known model family prefixes
        families = ["qwen", "gemma", "llama", "mistral"]
        return any(fam in lower for fam in families)
```

---

## Metrics: Measuring the Balance

### Our Current State

| Metric | Value | Target |
|--------|-------|--------|
| Deterministic Ratio | 8.1% | >80% |
| Heuristic Fallbacks | 1 | 0 |
| False Positives | ~5% | <5% |

**Analysis**: Low deterministic ratio means we're relying too much on heuristics. This is acceptable during development but should improve over time as we:
1. Add more deterministic parsers
2. Handle edge cases explicitly
3. Improve format specifications

### Monitoring

```python
report = discovery.discover_all()

if report["balance_ratio"] < 0.5:
    print("⚠️ Warning: Heavy reliance on heuristics")
    print("   Consider improving deterministic coverage")

if report["stats"]["heuristic_fallback"] > 0:
    print("⚠️ Heuristic fallbacks detected:")
    print("   - Review failed deterministic parsers")
    print("   - Add test cases for edge cases")
```

---

## When to Improve Deterministic Coverage

### Add Deterministic Code When:

1. **Same heuristic pattern repeats often**
   ```
   If heuristic detects "qwen3:4b" pattern 100+ times,
   add deterministic parser for qwen family.
   ```

2. **Format becomes stable**
   ```
   Once FLM output format stabilizes, 
   replace heuristic with exact parser.
   ```

3. **False positives from heuristics**
   ```
   If heuristic matches "settings.json" as model (false positive),
   add deterministic filter for .gguf extension only.
   ```

---

## Summary

**The Balance**:
- Start with heuristics (flexible, works everywhere)
- Gradually replace with deterministic (reliable, tested)
- Keep heuristics for true unknowns (new formats, edge cases)
- Monitor the ratio (aim for 80%+ deterministic)

**Our Code**:
- `deterministic_discovery_with_skill_fallback.py`
- Clear separation between layers
- Reports balance metrics
- Identifies areas for improvement

**Current Status**: 8% deterministic (needs improvement)
- FLM parser needs refinement
- Otherwise working correctly

**Next Step**: Improve FLM deterministic parser based on observed output formats.
