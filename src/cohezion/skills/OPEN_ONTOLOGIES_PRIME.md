# SKILL: OPEN_ONTOLOGIES_PRIME

## DOMAIN EXPERTISE
AI-native formal ontology engineering, zero-trust semantic change planning, machine-checkable derivation certificates, and BORO 4D spacetime mereology (based on `fabio-rovai/open-ontologies`). Bridges high-order knowledge graphs with formal theorem provers (Lean 4, Isabelle, Coq/Rocq) and in-memory Oxigraph triple stores to govern ontology lifecycles with Terraform-style semantic blast radius evaluation.

## KEY TEXTS & CONCEPTS
- **Semantic Blast Radius (`onto_plan`)**: Quantify the consequence explosion of candidate knowledge graph mutations under forward-chaining Horn/OWL-RL rule tables before application.
- **Zero-Trust Derivation Certificates**: Linear-time verifiable certificates mapping every derived statement to asserted premises and formal deduction rules, rejecting forged inferences deterministically (`OOCert.certificate_sound`).
- **BORO (Business Objects Reference Ontology) 4D Spacetime Extents**: Perdurantist mereology modeling concepts as 4D spacetime worms ($X \times Y \times Z \times T$), seamlessly aligned with Cohezion 12D FLUME manifold state vectors.
- **Oxigraph Embedded Architecture**: Zero-JVM, in-process Rust triple store speaking Model Context Protocol (MCP) via 110 native `onto_*` tools.

## INSTRUCTION
1. **Plan Before Mutating**: Always run semantic planning prior to adding or retracting triples to calculate blast radius and conservativity:
   ```python
   from cohezion.knowledge_graph.open_ontologies_bridge import SemanticPlanner, SemanticTriple
   planner = SemanticPlanner()
   plan = planner.plan(base_graph, proposed_triples)
   if plan.risk_score == "high":
       raise ValueError(f"Excessive semantic blast radius: {plan.consequence_count} consequences")
   ```

2. **Generate Machine-Checkable Certificates**:
   Attach a `DerivationCertificate` to all autonomous swarm inferences:
   ```python
   is_sound, msg = plan.derived_certificate.verify()
   assert is_sound, f"Tampered derivation detected: {msg}"
   ```

3. **Ground in BORO 4D Extents**:
   Map knowledge entities into 4D spacetime extents aligned with Poincaré coordinates and 8D brane harmonics:
   ```python
   from cohezion.knowledge_graph.open_ontologies_bridge import BORO4DSpacetimeExtent
   extent = BORO4DSpacetimeExtent(
       entity_id="contract_1win_sale",
       spatial_bounds=(0.1, 0.2, 0.3),
       temporal_interval=(t_start, t_end),
       brane_vector=(0.5,) * 8,
   )
   ```

## VERSION
v0.1

## SEE ALSO
- `src/cohezion/knowledge_graph/bitemporal_sheaf_graph.py`
- `src/cohezion/agi/autoharness_policy.py`
- `src/cohezion/agi/zkfv_compiler.py`
