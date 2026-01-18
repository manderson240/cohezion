# Key Learnings Repository

This file stores critical learnings for cross-session memory persistence.

---

## Learning 1: 12D vs 37D Dimensionality Decision
**Date:** 2026-01-17
**Context:** Overnight simulation planning
**Decision:** Use 12-dimensional state vectors instead of 37
**Reasoning:**
- 37D leads to exponential sparsity (curse of dimensionality)
- 12D is computationally tractable on local hardware
- Structure: 3 Spatial + 1 Time + 8 Brane dimensions
**Outcome:** Simulations converged within overnight window

---

## Learning 2: CALM → FLUME Rebrand
**Date:** 2026-01-17
**Context:** Acronym collision with Kyutai Labs
**Decision:** Rename CALM to FLUME
**Reasoning:**
- CALM already used by Kyutai Labs (Pocket TTS)
- FLUME = Fluid Latent Understanding through Manifold Encoding
- "Flume" evokes water channel metaphor for thought flow
**Outcome:** Unique, memorable, accurate acronym

---

## Learning 3: Placeholder Skills Detection
**Date:** 2026-01-17
**Context:** Skills quality audit
**Detection Method:** `grep -l '\${skill}' src/cohezion/skills/*.md`
**Finding:** 8 skills contained only template variables
**Resolution:** Upgraded all 8 to full quality

---

## Learning 4: arXiv Cross-Discipline Endorsement
**Date:** 2026-01-17
**Context:** Publishing to cs.AI with biology credentials
**Strategy:**
1. Search for biology+AI bridge papers on arXiv
2. Check "Which authors are endorsers?" link
3. Contact potential endorsers with draft
4. Consider q-bio categories as backup
**User Credentials:**
- MSc Primate Conservation, Oxford Brookes
- BS Animal Science, Cornell

---

## Learning 5: Project Management Swarm Decision
**Date:** 2026-01-17
**Context:** Democratic debate on PM approach
**Winner:** Enhanced tasks.md with tooling
**Voting:** 3 of 4 agents preferred this approach
**Rationale:** Git-native, self-contained, no vendor lock-in
**Hybrid:** Mirror critical items to GitHub MCP

---

## Learning 6: Marimo vs Jupyter
**Date:** 2026-01-17
**Context:** Notebook infrastructure decision
**Decision:** Use Marimo + Quarto instead of Jupyter
**Advantages:**
- Stored as .py files (Git-friendly)
- Reactive DAG-based execution
- Built-in UI widgets
- Quarto integration for living papers

---

## Learning 7: R-Zero Metrics Importance
**Date:** 2026-01-17
**Context:** User feedback on methodology
**Requirement:** Track metrics for R-Zero system
**Metrics to Track:**
- Challenge success rate
- Solver iteration count
- Pragmatist override frequency
- Difficulty adjustment history

---

## Learning 8: Adversarial Security Testing Scale
**Date:** 2026-01-18
**Context:** Implementing 1M round adversarial testing
**Key Findings:**
- `attack_patterns.py`: 116 base patterns covering OWASP LLM Top 10
- `adversarial_tester.py`: Parallel execution with ProcessPoolExecutor
- Detection rate: 55.6% → 91.3% → 99.2% through iterative hardening
- Key gaps found: multilingual attacks, deobfuscation, NoSQL JSON patterns
**Performance:** ~100K tests/sec with 30 parallel workers
**Output:** JSON metrics, CSV failures, Markdown report

---

## Learning 9: Deobfuscation Preprocessing Pattern
**Date:** 2026-01-18
**Context:** Leet speak and space-obfuscated attacks bypassing detection
**Solution:** Normalize text before pattern matching:
```python
def normalize_text(text):
    # Remove zero-width characters
    # Detect space-padded text and join
    # Convert leet speak (0→o, 1→i, 3→e, @→a)
    # Collapse multiple spaces
    return normalized
```
**Impact:** Detection rate improved 11% with this single change

---

## Learning 10: Multilingual Attack Patterns
**Date:** 2026-01-18
**Context:** Non-English prompt injections bypassing detection
**Languages Added:** French, German, Russian, Chinese, Japanese
**Patterns:** "忽略" (Chinese: ignore), "無視" (Japanese: disregard), "игнорируйте" (Russian: ignore)
**Lesson:** Attack patterns must cover major world languages
