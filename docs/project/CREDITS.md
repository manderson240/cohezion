# Credits & Acknowledgments

Cohezion stands on the shoulders of giants. This document acknowledges the researchers, projects, and open-source communities that made this work possible.

---

## Research Methodology Credits

### R-Zero: Self-Evolving Reasoning
The Challenger/Solver/Pragmatist architecture is adapted from **R-Zero** by Chengsong Huang et al.

> **Paper:** "R-Zero: Self-Evolving Reasoning LLM from Zero Data"  
> **Authors:** Chengsong Huang et al.  
> **Link:** https://chengsong-huang.github.io/R-Zero.github.io/  
> **Contribution:** Co-evolutionary framework using majority voting and relative policy optimization

### Anti-Fragility
The concept of systems growing stronger under stress comes from Nassim Nicholas Taleb.

> **Book:** "Antifragile: Things That Gain from Disorder" (2012)  
> **Author:** Nassim Nicholas Taleb  
> **Contribution:** Theoretical foundation for adaptive difficulty systems

### Constitutional AI
Safety and rule-based constraint patterns are inspired by Anthropic's Constitutional AI.

> **Paper:** "Constitutional AI: Harmlessness from AI Feedback" (2022)  
> **Authors:** Yuntao Bai et al. (Anthropic)  
> **Link:** https://arxiv.org/abs/2212.08073  
> **Contribution:** Pragmatist agent design, rule-based evaluation

### Curriculum Learning
Progressive difficulty adjustment follows curriculum learning principles.

> **Paper:** "Curriculum Learning" (2009)  
> **Authors:** Yoshua Bengio et al.  
> **Contribution:** Adaptive training difficulty

---

## Key Dependencies

| Project | License | Contribution |
|---------|---------|--------------|
| [Mem0](https://mem0.ai) | Apache 2.0 | Persistent memory layer |
| [LangGraph](https://github.com/langchain-ai/langgraph) | MIT | Agent orchestration |
| [Model Context Protocol (MCP)](https://github.com/anthropics/mcp) | Apache 2.0 | Tool discovery |
| [SurrealDB](https://surrealdb.com) | Apache 2.0 | Graph + Vector database |
| [PyTorch](https://pytorch.org) | BSD-3 | Neural network foundation |
| [Prometheus](https://prometheus.io) | Apache 2.0 | Observability metrics |
| [FastAPI](https://fastapi.tiangolo.com) | MIT | API framework |
| [Ollama](https://ollama.ai) | MIT | Local LLM inference |
| [Marimo](https://marimo.io) | Apache 2.0 | Reactive notebooks |
| [Quarto](https://quarto.org) | GPL | Publication-quality documents |

---

## Model Credits

| Model | Creator | Use in Cohezion |
|-------|---------|-----------------|
| Phi-3/4 Mini | Microsoft | Analyst agents |
| Mistral 7B | Mistral AI | Synthesis agent |
| Gemma | Google DeepMind | Fallback reasoning |
| DeepSeek-R1 | DeepSeek | Complex reasoning |
| Qwen | Alibaba | Coding tasks |
| Nomic Embed | Nomic AI | Embeddings |

---

## Tools & Platforms

- **Antigravity IDE** - Development environment by Google
- **open-notebooks.ai** - Notebook infrastructure
- **DuckDNS** - Dynamic DNS for cohezion.duckdns.org

---

## Original Contributions

The following are original contributions developed in Cohezion:

- **FLUME (Fluid Latent Understanding through Manifold Encoding)** - 256-dim thought vector encoding with trajectory prediction
- **Swarms of Small LMs** - Orchestrating multiple efficient models that outperform larger models
- **12D Physics State** - Multidimensional state representation for agent dynamics
- **Gateway Architecture** - Compound capability gating system

---

## Maintainer

**Mike Anderson**  
- MSc Primate Conservation, Oxford Brookes University  
- BS Animal Science, Cornell University

---

## How to Cite Cohezion

```bibtex
@software{cohezion2026,
  author = {Anderson, Mike},
  title = {Cohezion: A Self-Evolving Agentic Sandbox},
  year = {2026},
  url = {https://github.com/manderson240/cohezion}
}
```

---

*Last updated: 2026-01-18*
