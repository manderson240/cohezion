---
title: Agent Journey Tracking
date: 2026-02-23
tags: [agent-workflow, observability, compound-engineering]
status: stub
---

# Agent Journey Tracking

Recording the full execution trace of an agent session — tasks attempted, decisions made, outputs produced — for retrospective analysis and compound learning.

## Related
- [[lesson-19-session-awareness-protocol]]
- [[lesson-37-experience-guided-execution-works-new]]
- [[experiments/session-57-local-finetuning|Session 57: Local Model Finetuning Pipeline]] — converts journey data (from this tracking system) to JSONL format for QLoRA and Ollama Modelfile finetuning
- [[decisions/2026-02-13-experience-vae-training-pipeline-session-58|Experience → VAE Training Pipeline]] — uses journey data to train a VAE on real agentic behavior distributions
- [[universe-simulation]] — the N-body simulation that generates agentic journey traces for compound learning
