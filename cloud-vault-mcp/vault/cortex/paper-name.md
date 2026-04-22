---
title: "Paper Name"
date: 2026-02-19
tags: [concept, meta, template]
aspect: knower
neural:
  activation: 0.78
  stage: mature
  synapse_in: 2
  synapse_out: 11
---
## Definition

This note is a **template artifact** — `[[paper-name]]` appears as a placeholder in vault templates, lesson integration instructions, and skill definitions to indicate where a real paper reference should be inserted. It is not a standalone concept but a meta-documentation node that exists because vault auto-linking created a target for every `[[...]]` reference, including template placeholders.

The note's existence highlights an important distinction in knowledge graph maintenance: not all wiki-link targets represent genuine domain concepts. Template placeholders, example references, and format documentation generate syntactically valid links that resolve to nodes in the graph, but these nodes carry no semantic content. Recognising and handling these "phantom nodes" is essential for maintaining graph quality as vaults scale.

In knowledge graph theory, nodes like `[[paper-name]]` are analogous to dangling references or orphan nodes — they exist in the link structure but contribute no domain knowledge. Graph linting tools can detect them by checking for nodes whose inbound links originate exclusively from template files, instructional documentation, or format examples rather than from substantive cross-references.

## Key Properties

- **Template placeholder** — Used in instructions like "Format: `[[paper-name]] (similarity: 0.XX)`" to show the expected linking pattern in vault templates and skill definitions
- **Non-semantic node** — Unlike other concept notes, this does not represent domain knowledge; its inbound links come from template examples and format documentation
- **Graph quality indicator** — The existence of phantom nodes like this signals the need for link validation tooling in the vault
- **Candidate for deletion** — If the vault adopts a lint rule for broken/placeholder links, this note could be removed or replaced with a redirect
- **Meta-documentation** — Serves as documentation of the vault's auto-linking behaviour and its edge cases

## Examples

- A skill definition template instructs: "Link related papers: `[[paper-name]] (similarity: 0.85)`" — this creates a link to the template artifact rather than to a real paper
- Lesson integration instructions say: "Add to Related Papers section: `[[paper-name]]`" — again creating a phantom link
- A vault lint tool scanning for nodes with only template-origin inbound links would flag this note for review

## Related Papers

- [[2026-02-11-lessons-compound-engineering-phase-1-complete]]
- [[2026-02-12-lessons-compound-engineering-phase-2-complete]]
- [[lessons-graph-integration]]

## Related Concepts

- [[concept-testing]] — link validation would flag `[[paper-name]]` as a non-semantic reference during concept testing
- [[concept-validation]] — phantom node detection is a graph-level validation task complementing content-level validation
- [[knowledge-graph-systems]] — understanding phantom nodes is essential for knowledge graph quality maintenance
- [[concept-automation]] — automated vault tools should distinguish template placeholders from genuine concept links
- [[graphrag-knowledge-graph-with-surrealdb]] — the GraphRAG system inherits phantom nodes from vault auto-linking; cleaning them improves graph query quality

## Relevance to Cohezion

This note exists because vault auto-linking created a node for every `[[...]]` reference, including template placeholders. It serves as a reminder that [[knowledge-graph-systems]] at scale must distinguish semantic links from syntactic ones. Future vault tooling — particularly the [[concept-automation]] pipeline and [[concept-testing]] framework — should include phantom-node detection to prevent template artifacts from polluting graph analytics and [[semantic-search]] results.
