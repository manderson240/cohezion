---
type: antigravity-artifact
session_id: bee84f15-8915-4cbf-8400-f5ca9e10c3f2
date: 2026-03-04
title: "Cli Tutorial"
aspect: doer
neural:
  activation: 0.62
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# Cohezion CLI Tutorial

## Getting Started

The Cohezion CLI is your command center for the swarm. It provides access to research, system monitoring, and the "Journey" interactive mode.

### Setup

We have created a convenience script to run the CLI easily.

```bash
# Make sure you are in the project root
cd /home/mike-anderson/dev/cohezion

# Run the CLI
./scripts/cohezion --help
```

## Available Commands

### 1. Dashboard (`dash`)
Launch the "Terminal Nexus" dashboard to see identifying metrics, swarm status, and the current state of the domain expert lattice.

> **Experience Note**: The dashboard now initiates with a "Consciousness Ignition" sequence and displays the "Nexus Singularity" avatar, reflecting the system's active state.

```bash
./scripts/cohezion dash
```

### 2. Research (`research`)
ignite the Nexus Research Miner to perform deep-dive analysis or daily sweeps.

```bash
# Run a specific query
./scripts/cohezion research --query "latest developments in quantum tensor networks"

# Run a daily sweep (default limit 5 per source)
./scripts/cohezion research --limit 10
```

### 3. Journey (`journey`)
Embark on an interactive "Journey" - a guided narrative experience through the Cohezion methodology.

```bash
# List available journeys
./scripts/cohezion journey --list

# Start the HIHO Attractor journey
./scripts/cohezion journey --start "The HIHO Attractor"
```

### 4. Verify (`verify`)
Run the project's validation suite.

```bash
# Run standard verifications
./scripts/cohezion verify

# Run adversarial stress tests
./scripts/cohezion verify --adversarial
```

### 5. Browser (`browser`)
Launch the Cohezion Browser Agent to explore or snapshot a URL.

```bash
./scripts/cohezion browser "https://arxiv.org" --screenshot "arxiv_home.png"
```

## Tips for Power Users

- **Alias**: Add `alias cohezion=~/dev/cohezion/scripts/cohezion` to your `.bashrc` for global access.
- **Logs**: The dashboard watches `logs/lab_driver.log` for real-time updates.

## Related Vault Notes

- [[cohezion]]
