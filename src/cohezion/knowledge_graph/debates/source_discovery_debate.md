# Source Discovery Swarm Debate

**Date**: 2026-01-20
**Mode**: Creative Intelligence Expansion
**Participants**:
- **Architect (Tier: Gemini 3 Pro)**
- **Engineer (Tier: Qwen3-Coder 30B)**
- **Librarian (Tier: Gemma 3 4B)**

---

### [ARCHITECT]
"Our focus should be on high-entropy, high-signal sources. arXiv is the bedrock, but it's slow. We need **OpenReview** to see the raw peer-review friction—that's where the real 'physics' of the idea is exposed. Also, we must monitor **r/LocalLLaMA**. The community there is faster than academia at quantization and inference optimization, which is critical for our 128GB local machine constraints."

### [ENGINEER]
"I agree on the signal, but we must protect our IP and our API standing. Reddit is notoriously difficult to scrape reliably without a browser subagent, which wastes tokens. I propose focusing on **Hugging Face Hub's 'Daily Papers'** JSON endpoint and **GitHub Trending**. For arXiv, we use the `arxiv` python wrapper with a strict 2-second jittered sleep to prevent IP bans. We also need a 'Content Hash' in SurrealDB to ensure we never process the same abstract twice."

### [LIBRARIAN]
"Documentation density is my priority. Raw papers are noisy. I recommend adding **Researcher Blogs** (Lilian Weng, Andrej Karpathy, etc.) via RSS. Their synthesis saves us thousands of tokens in reasoning. Also, **Semantic Scholar API** allows us to track 'influence'—we should only dig deep into papers that show a rapid upward trajectory in citations or 'highly influential' citations."

---

### Consensus Synthesis (The Nexus Protocol)

1.  **Primary Pulse**: arXiv (AI/CL/LG), HF Daily Papers.
2.  **Code Pulse**: GitHub Trending (Python/C++).
3.  **Efficiency Pulse**: r/LocalLLaMA (via RSS/JSON).
4.  **Deep Signal**: OpenReview & Semantic Scholar.
5.  **Guardrail Alpha**: "Abstract-First" Policy. No full text download unless Rank > 0.85.
6.  **Guardrail Beta**: 24h SurrealDB Cache.
