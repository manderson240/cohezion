# Session Context

## User Prompts

### Prompt 1

[Request interrupted by user for tool use]

### Prompt 2

Implement the following plan:

# SurrealDB Health Check & Recovery Plan

## Context

The vault's SurrealDB graph system has been down for ~22 hours. Two services are failing:
1. `cohezion-vault.service` (Cloud Vault MCP, port 8360) — crashes immediately on import: `ModuleNotFoundError: No module named 'psutil'`
2. `cohezion-vault-sync.service` — restart-looping 7882+ times with `ERROR: SurrealDB not reachable on port 8001`

Root cause: The `surreal` binary is not in PATH and no SurrealDB proc...

### Prompt 3

Let's do that then, we need to make it persistent.

### Prompt 4

# /learn - Online Learning System

**Extract reusable knowledge from this session into skills.** Evaluates what was learned, checks for existing skills, and creates new ones when valuable patterns are discovered.

---

## TABLE OF CONTENTS

| Phase       | Description                                            | Steps   |
| ----------- | ------------------------------------------------------ | ------- |
| **Phase 0** | Reference: triggers, quality criteria, skill structure | 0.1–0.4 |
| **Pha...

### Prompt 5

We need to improve Cohezion's ability to actually use the vault and surrealdb.  How can improve our graph architecture and make it easily operable by humans and agents?

### Prompt 6

Base directory for this skill: /home/mike-anderson/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.5/skills/brainstorming

# Brainstorming Ideas Into Designs

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design and get user approval.

<HARD-GATE>
Do NOT invoke any implementat...

### Prompt 7

a,b,c and we need to be looking towards the future.

### Prompt 8

All 3

### Prompt 9

Can we get party mode democratic consensus for this choice?

### Prompt 10

Yes, we can always change it later

### Prompt 11

we need agentic democratic consensus for this

### Prompt 12

yes

### Prompt 13

The 3d graph is garbage, I thought we we were working on a 12-d plugin?

### Prompt 14

How do you think we should proceed?

### Prompt 15

yes, let's see the approaches

### Prompt 16

Yes

### Prompt 17

yes

### Prompt 18

yes and are we leveraging what others have done?  https://surrealdb.com/docs/labs

### Prompt 19

Proceed

### Prompt 20

Pick a path that unlocks compound engineering and token efficiencies.  Not all tokens are the same.

### Prompt 21

Finish it

### Prompt 22

This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. Primary Request and Intent:
   The session had two major phases:
   
   **Phase 1 — Infrastructure Recovery**: Implement a pre-planned recovery for a vault SurrealDB system that had been down ~22 hours. Three failures needed fixing: (1) SurrealDB not running (binary not in PATH), (2) `cloud-vault-mcp` service crashing on import wi...

