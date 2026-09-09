---
name: review-multi-perspective
description: |
  Performs an adversarial code review using Agy, Claude, and an Ollama model. Aggregates findings into a JSON payload and writes to review_report.json in the repo root. Optionally generates a markdown learning card.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [review, adversarial, multi‑LLM, experiential]
prerequisites:
  commands: [agy, claude, ollama, jq]
---
# Implementation

The skill runs a shell script that executes each model's review command, collects their JSON outputs, merges them, and writes the final payload to `review_report.json`.
