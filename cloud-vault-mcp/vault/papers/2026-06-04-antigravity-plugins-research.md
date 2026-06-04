---
date: 2026-06-04
source_project: cohezion
tags: [paper, antigravity, mcp, plugin, research]
---
# Antigravity CLI (agy) Plugins & Extensions Research

This report analyzes community plugins, extensions, and Model Context Protocol (MCP) servers for the **Antigravity CLI (`agy`)** ecosystem that can help streamline agent orchestration, code analysis, testing, and UI design within the **Cohezion** workspace.

---

## 1. Agent Orchestration

### **Oh-My-Antigravity (OmA)**
*   **Repository:** [Joonghyun-Lee-Frieren/oh-my-antigravity](https://github.com/Joonghyun-Lee-Frieren/oh-my-antigravity)
*   **Domain:** swarms, checkpointing, multi-agent workflows
*   **Key Features:**
    *   **Ultragoal (`$ultragoal` / `/oma:ultragoal`):** Persistent, repo-native, multi-goal workflows that decompose complex, long-running engineering tasks into sequential checkpointed micro-goals. Resumes execution seamlessly after session failures or interruptions.
    *   **Specialized Agent Personas:** Orchestrates role-specific subagents (Architect, Code Reviewer, Tester, Security Specialist) in isolated worktree environments.
*   **Cohezion Integration Plan:**
    > [!TIP]
    > Integrate the OmA checkpointing patterns into Cohezion's compound executor (`src/cohezion/compound/`) and swarm orchestrator (`src/cohezion/swarm/`). Persistent task states can be stored in SurrealDB on port `8001` to enable robust multi-turn recovery during long-running or overnight runs.

### **mcp-operator**
*   **Repository:** [vitorbari/mcp-operator](https://github.com/vitorbari/mcp-operator)
*   **Domain:** microservice orchestration, deployment
*   **Key Features:**
    *   Kubernetes operator for automated validation, horizontal scaling, and observability of Model Context Protocol (MCP) servers.
*   **Cohezion Integration Plan:**
    *   Use `mcp-operator` if we expose Cohezion's internal capabilities (e.g., semantic cache, SurrealDB search tools) to other users or distributed swarms via containerized Kubernetes pods.

---

## 2. Code Analysis

### **jscpd (Copy/Paste Detector MCP)**
*   **Repository:** [awesome-mcp/jscpd-server](https://github.com/awesome-mcp/jscpd-server) (via `@jscpd/mcp-server`)
*   **Domain:** code duplication, static analysis
*   **Key Features:**
    *   Wraps the `jscpd` engine in an AI-ready MCP schema, allowing agents to query code duplicate statistics and locate redundant blocks.
*   **Cohezion Integration Plan:**
    > [!IMPORTANT]
    > Add this tool to our pre-flight checks (`make validate` or git pre-commit hooks) to prevent agents from copy-pasting code blocks. This enforces our strict repository health standards, helping keep the git index size under the **10k tracked files limit**.

### **Sniff-QA**
*   **Repository:** [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)
*   **Domain:** link checking, routing validation
*   **Key Features:**
    *   Performs static vulnerability scanning, link checks, and endpoint discovery.
*   **Cohezion Integration Plan:**
    *   Use this analyzer to validate routes and links in our React/Next.js dashboard (`src/web/anima_dashboard`).

---

## 3. Testing

### **C.H.A.I (Cyber Host Artificial Intelligence)**
*   **Repository:** [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)
*   **Domain:** penetration testing, injection guards
*   **Key Features:**
    *   Security-centric testing server capable of active penetration testing and Nuclei vulnerability scans.
*   **Cohezion Integration Plan:**
    *   Couples with our `ADVERSARIAL_TESTING_PRIME` skill. Testing agents can call C.H.A.I to check for prompt injection vulnerabilities against our local APIs.

---

## 4. UI Design & Knowledge Harvesting

### **Antigravity Awesome Skills**
*   **Repository:** [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)
*   **Domain:** skill templates, visual validation
*   **Key Features:**
    *   A curated library of 1,500+ agentic playbooks. Includes specialized playbooks like `ui-visual-validator` for layout regressions and Android testing.
*   **Cohezion Integration Plan:**
    *   Instead of bulk-syncing the library (which would cause context bloat), configure our `SkillRefiner` to selectively parse and ingest UI-related templates, adding them to `.agents/skills/` on demand.

### **CodePilot**
*   **Repository:** [Rodert/CodePilot](https://github.com/Rodert/CodePilot)
*   **Domain:** workspace visualization, agent dashboards
*   **Key Features:**
    *   Next.js-based desktop application providing a rich graphical interface for active agent sessions, workspace metrics, and MCP server logs.
*   **Cohezion Integration Plan:**
    *   Route Cohezion's event hooks to CodePilot's GUI, allowing us to visualize FLUME VAE trajectories, 12D attractor centroids, and active swarm statuses in a web interface.

---

## Workspace Integration Guide

To install and verify these tools within Cohezion:

### 1. Registering Plugins
Install plugins globally or locally using:
```bash
agy plugin install <plugin-url>
```

### 2. Loading MCP Servers
Add chosen servers (such as `jscpd`) to your local configurations:
```json
// ~/.gemini/antigravity-cli/mcp_config.json
{
  "mcpServers": {
    "jscpd": {
      "command": "npx",
      "args": ["-y", "@jscpd/mcp-server"]
    }
  }
}
```
