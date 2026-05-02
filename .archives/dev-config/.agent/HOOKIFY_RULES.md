# Hookify Rules

## Rule: cosmological_ralph_loop
- **ID**: cosmological_ralph_loop
- **Trigger**: session_start
- **Condition**: goal.matches("cosmology|solver|universe")
- **Action**: ralph_loop.orchestrate
- **Levers**:
  - coherence_threshold: 0.5
  - max_iterations: 20
  - auto_commit: true
  - witness_plate: "vault/hippocampus/changelog-{session_id}.md"
- **Adversarial Tests**:
  - test_cosmological_convergence
  - test_hiho_stability
  - test_witness_plate_creation

## Rule: hiho_stability_gate
- **ID**: hiho_stability_gate
- **Trigger**: pre_execute
- **Condition**: always
- **Action**: block_if_coherence_below_threshold
- **Levers**:
  - threshold: 0.5
  - fallback_action: decompose_request
- **Adversarial Tests**:
  - test_hiho_convergence
  - test_stability_boundary

## Rule: knowledge_persist
- **ID**: knowledge_persist
- **Trigger**: post_execute
- **Condition**: should_persist_learning == true OR retrospection_generated == true
- **Action**: hookify_vault_writer.write_session_learning
- **Levers**:
  - persist_to_vault: true
  - persist_to_surrealdb: true
  - embed_with_flume: true
  - max_content_length: 500
- **Adversarial Tests**:
  - test_vault_file_created
  - test_surrealdb_neuron_inserted
  - test_flume_embedding_non_empty

## Rule: akashic_commit
- **ID**: akashic_commit
- **Trigger**: post_execute
- **Condition**: execution_success
- **Action**: auto_commit_and_push
- **Levers**:
  - commit_message_template: "Session {id}: {summary}\n\nCoherence: {coherence}"
  - require_tests_pass: true
  - push_to_remote: true
- **Adversarial Tests**:
  - test_commit_message_format
  - test_git_coordination
