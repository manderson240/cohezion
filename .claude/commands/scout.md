Run the Daily Model Research scout for Cohezion.

You are a Market Scout. Find "Tip of the Spear" small language models (SLMs) that could outperform the current roster (deepseek-r1:70b, qwen3-coder:30b, phi3:mini).

Criteria:
- Under 20B parameters
- License: Apache 2.0 or MIT
- Available on Ollama or HuggingFace

Steps:
1. Search HuggingFace trending text-generation models under 20B params
2. Check Ollama for new models: `ollama list` to see current roster
3. Compare against existing models in the project
4. Rank by novelty and community sentiment
5. Report top 3 candidates with parameter count, license, and reasoning
6. **Write findings to graph**: For each top candidate, use `mcp__cohezion-vault__graph_annotate_neuron` or create a neuron via the graph_writer API:
   - Create neuron: `neuron:model_{slugified_name}_md` in cluster `"scout"` with tags `["model-candidate", "scout", license]`
   - If a related concept exists in cortex (e.g. `agentic-ai`, `code-generation`), create a latent synapse via `mcp__cohezion-vault__graph_write_latent_synapse` linking the model neuron to the concept
   - This makes scout findings queryable via `graph_search("model candidate")` in future sessions
