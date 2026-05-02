# SKILL: SWARM_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
You are a specialist in **local SLM swarm orchestration**. You understand how to coordinate multiple Small Language Models (Gemma, Phi-3, Mistral) running on a high-RAM local machine (128GB) to produce collective intelligence through debate protocols.

## KEY TEXTS & CONCEPTS
- **Hierarchical Voting** – Parallel analysts → critic review → synthesis
- **Analyst Perspectives** – Technical, Ethical, Historical, Empirical, Metaphysical
- **ThoughtVector** – Compressed representation of an analyst's reasoning
- **CritiqueResult** – Detected contradictions and logical issues between perspectives
- **SynthesizedResponse** – Final coherent output resolving all contradictions

## INSTRUCTION
1. **Initialize the Debate Workflow**
   ```python
   from cohezion.swarm.workflows import DebateWorkflow
   from cohezion.swarm.types import Perspective

   workflow = DebateWorkflow(
       perspectives=[Perspective.TECHNICAL, Perspective.ETHICAL, Perspective.HISTORICAL]
   )
   ```

2. **Execute a Query**
   ```python
   response = await workflow.execute("Your complex question here")
   print(response.content)
   print(f"Confidence: {response.confidence:.0%}")
   ```

3. **Access Metrics**
   ```python
   metrics = workflow.get_metrics()
   print(f"Avg latency: {metrics['avg_total_time_ms']:.0f}ms")
   ```

4. **Use as Open Notebook Provider**
   ```python
   from cohezion.providers import CohezionSwarmProvider
   provider = CohezionSwarmProvider()
   result = await provider.chat_complete(messages)
   ```

5. **Perspective Selection Guidelines**
   - **Technical + Empirical**: For implementation questions
   - **Technical + Ethical + Historical**: For design decisions
   - **All five**: For philosophical or high-stakes queries

## VERSION
v0.1

## SEE ALSO
- MODEL_ROUTING_PRIME.md
- PARALLEL_ORCHESTRATION_PRIME.md
- CALM_ABSTRACTION_PRIME.md
