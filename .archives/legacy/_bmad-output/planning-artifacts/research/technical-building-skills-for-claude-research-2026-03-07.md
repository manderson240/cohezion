# Technical Research: Anthropic's Complete Guide to Building Skills for Claude

**Research Type:** BMAD Technical Research (6-step workflow)
**Date:** 2026-03-07
**Researcher:** Claude (Session: feat/semver-400-year-physics-hiho-flume)
**Source Document:** "The Complete Guide to Building Skills for Claude" (Anthropic, 29 pages, 6 chapters)
**Source URL:** `https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf`
**Status:** Complete

---

## Executive Summary

Anthropic's official skills guide codifies a portable, folder-based skill architecture with three-level progressive disclosure, YAML frontmatter for triggering, and five reusable design patterns for MCP-enhanced workflows. This research synthesizes all 6 chapters and conducts a gap analysis against Cohezion's existing skill infrastructure (143 PRIME skills, 120 BMAD commands, 1 Claude Code skill).

**Critical finding:** Cohezion's skill system evolved organically into two parallel formats (PRIME flat-file skills and BMAD commands) that diverge significantly from Anthropic's official spec. Neither format uses the canonical `SKILL.md` folder structure, progressive disclosure, or the `[What] + [When] + [Capabilities]` description formula that drives Claude's skill triggering engine.

**Top 5 Recommendations (Priority Order):**

| # | Recommendation | Impact | Effort |
|---|---------------|--------|--------|
| 1 | Adopt Anthropic's folder structure for new skills | High (portability, API compatibility) | Low |
| 2 | Retrofit YAML frontmatter with description formula onto PRIME skills | High (triggering accuracy) | Medium |
| 3 | Implement progressive disclosure (split large skills into references/) | High (token efficiency) | Medium |
| 4 | Create trigger test suites for top 20 skills | Medium (reliability) | Low |
| 5 | Evaluate Skills API for programmatic skill deployment | Medium (distribution) | Low |

---

## Table of Contents

1. [Chapter 1: Fundamentals](#chapter-1-fundamentals)
2. [Chapter 2: Planning and Design](#chapter-2-planning-and-design)
3. [Chapter 3: Testing and Iteration](#chapter-3-testing-and-iteration)
4. [Chapter 4: Distribution and Sharing](#chapter-4-distribution-and-sharing)
5. [Chapter 5: Patterns and Troubleshooting](#chapter-5-patterns-and-troubleshooting)
6. [Chapter 6: Resources and References](#chapter-6-resources-and-references)
7. [Cohezion Gap Analysis](#cohezion-gap-analysis)
8. [Actionable Recommendations](#actionable-recommendations)

---

## Chapter 1: Fundamentals

### 1.1 What Is a Skill?

A skill is a **folder** containing:

| File/Directory | Required | Purpose |
|---------------|----------|---------|
| `SKILL.md` | Yes | Instructions in Markdown with YAML frontmatter |
| `scripts/` | No | Executable code (Python, Bash, etc.) |
| `references/` | No | Documentation loaded as needed |
| `assets/` | No | Templates, fonts, icons used in output |

**Key rule:** The file MUST be named exactly `SKILL.md` (case-sensitive). No variations (`skill.md`, `SKILL.MD`, `README.md`) are accepted.

### 1.2 Progressive Disclosure (Three Levels)

This is the most architecturally significant concept in the guide. Skills use a three-level system to minimize token usage:

| Level | What | When Loaded | Token Impact |
|-------|------|-------------|-------------|
| **Level 1: YAML frontmatter** | Name + description | Always in system prompt | Minimal (~50-100 tokens per skill) |
| **Level 2: SKILL.md body** | Full instructions and guidance | When Claude determines skill is relevant | Moderate (entire SKILL.md content) |
| **Level 3: Linked files** | scripts/, references/, assets/ | On-demand when Claude navigates to them | Variable (only what's needed) |

**Why this matters:** Progressive disclosure means Claude can have hundreds of skills loaded at Level 1 without context bloat. Only the triggered skill's body (Level 2) and referenced files (Level 3) consume significant tokens.

### 1.3 Core Design Principles

**Composability:** Skills coexist simultaneously. A skill should work well alongside others and not assume it's the only capability available. This means avoiding overly broad trigger phrases that would conflict with other skills.

**Portability:** Skills work identically across Claude.ai, Claude Code, and the API. The same skill folder should function on all surfaces without modification, provided the environment supports any required dependencies.

### 1.4 Skills + MCP Relationship

Anthropic uses a "kitchen analogy" to distinguish MCP from Skills:

| MCP (Connectivity) | Skills (Knowledge) |
|--------------------|--------------------|
| Connects Claude to services (Notion, Asana, Linear) | Teaches Claude how to use those services effectively |
| Provides real-time data access and tool invocation | Captures workflows and best practices |
| What Claude **can** do | How Claude **should** do it |

**Key insight:** Without skills, users connect MCP but don't know what to do next. With skills, pre-built workflows activate automatically with consistent results.

### Cohezion Relevance (Chapter 1)

Cohezion's `cloud-vault-mcp/` server (40+ tools) is a strong MCP implementation, but its associated skills (e.g., `SURREALDB_MCP_PRIME.md`) are flat files without the folder structure or progressive disclosure that would let Claude efficiently route to them. The PRIME skills act as monolithic Level 2 content without Level 1 frontmatter for triggering.

---

## Chapter 2: Planning and Design

### 2.1 Start With Use Cases

Before writing any code, identify 2-3 concrete use cases the skill should enable. Anthropic provides a structured format:

```
Use Case: Project Sprint Planning
Trigger: User says "help me plan this sprint" or "create sprint tasks"
Steps:
1. Fetch current project status from Linear (via MCP)
2. Analyze team velocity and capacity
3. Suggest task prioritization
4. Create tasks in Linear with proper labels and estimates
Result: Fully planned sprint with tasks created
```

**Self-assessment questions:**
- What does a user want to accomplish?
- What multi-step workflows does this require?
- Which tools are needed (built-in or MCP)?
- What domain knowledge or best practices should be embedded?

### 2.2 Three Skill Categories

| Category | Purpose | Key Techniques | Real Example |
|----------|---------|---------------|-------------|
| **1. Document & Asset Creation** | Consistent, high-quality output (documents, presentations, apps, designs, code) | Embedded style guides, template structures, quality checklists, no external tools | `frontend-design` skill |
| **2. Workflow Automation** | Multi-step processes with consistent methodology | Step-by-step workflows, validation gates, templates, iterative refinement | `skill-creator` skill |
| **3. MCP Enhancement** | Workflow guidance on top of MCP tool access | Multi-MCP coordination, embedded domain expertise, error handling | `sentry-code-review` skill |

### 2.3 Success Criteria

**Quantitative metrics:**
- Skill triggers on 90% of relevant queries (measure: run 10-20 test queries, track auto vs. manual invocation)
- Completes workflow in X tool calls (measure: compare with/without skill, count tool calls and tokens)
- 0 failed API calls per workflow (measure: monitor MCP server logs for retry rates and error codes)

**Qualitative metrics:**
- Users don't need to prompt Claude about next steps
- Workflows complete without user correction (run same request 3-5 times, compare structural consistency)
- Consistent results across sessions (can a new user accomplish the task on first try with minimal guidance?)

### 2.4 Technical Requirements: File Structure

```
your-skill-name/
|-- SKILL.md                    # Required - main skill file
|-- scripts/                    # Optional - executable code
|   |-- process_data.py
|   |-- validate.sh
|-- references/                 # Optional - documentation
|   |-- api-guide.md
|   |-- examples/
|-- assets/                     # Optional - templates, etc.
    |-- report-template.md
```

**Critical naming rules:**

| Rule | Correct | Wrong |
|------|---------|-------|
| SKILL.md naming | `SKILL.md` (exact case) | `skill.md`, `SKILL.MD`, `Skill.md` |
| Folder naming | `notion-project-setup` (kebab-case) | `Notion Project Setup`, `notion_project_setup`, `NotionProjectSetup` |
| No README.md | All docs go in SKILL.md or references/ | Don't include README.md inside skill folder |

**Note:** When distributing via GitHub, use a repo-level README.md for human visitors, separate from the skill folder's SKILL.md.

### 2.5 YAML Frontmatter: The Most Important Part

The frontmatter is how Claude decides whether to load a skill. It appears in Level 1 (always in system prompt).

**Minimal required format:**
```yaml
---
name: your-skill-name
description: What it does. Use when user asks to [specific phrases].
---
```

**Field requirements:**

| Field | Required | Rules |
|-------|----------|-------|
| `name` | Yes | kebab-case only, no spaces or capitals, should match folder name |
| `description` | Yes | Must include WHAT + WHEN, under 1024 chars, no XML angle brackets (`<` or `>`), include specific trigger phrases, mention file types if relevant |
| `license` | No | Use if open source (MIT, Apache-2.0) |
| `compatibility` | No | 1-500 chars, environment requirements (intended product, system packages, network access) |
| `metadata` | No | Any custom key-value pairs (suggested: author, version, mcp-server) |

**Security restrictions:**
- No XML angle brackets in frontmatter (frontmatter appears in system prompt; malicious content could inject instructions)
- Skills with "claude" or "anthropic" in the name are reserved

### 2.6 The Description Formula

```
[What it does] + [When to use it] + [Key capabilities]
```

**Good examples (from the guide):**

```yaml
# Good - specific and actionable
description: Analyzes Figma design files and generates developer handoff
  documentation. Use when user uploads .fig files, asks for "design specs",
  "component documentation", or "design-to-code handoff".

# Good - includes trigger phrases
description: Manages Linear project workflows including sprint planning,
  task creation, and status tracking. Use when user mentions "sprint",
  "Linear tasks", "project planning", or asks to "create tickets".

# Good - clear value proposition
description: End-to-end customer onboarding workflow for PayFlow. Handles
  account creation, payment setup, and subscription management. Use when
  user says "onboard new customer", "set up subscription", or "create
  PayFlow account".
```

**Bad examples:**
```yaml
# Too vague
description: Helps with projects.

# Missing triggers
description: Creates sophisticated multi-page documentation systems.

# Too technical, no user triggers
description: Implements the Project entity model with hierarchical relationships.
```

### 2.7 Writing Main Instructions

**Recommended SKILL.md structure:**
```markdown
---
name: your-skill
description: [...]
---

# Your Skill Name

## Instructions

### Step 1: [First Major Step]
Clear explanation of what happens.

Example:
```bash
python scripts/fetch_data.py --project-id PROJECT_ID
Expected output: [describe what success looks like]
```

### Step 2: [Next Step]
...

## Examples

### Example 1: [common scenario]
User says: "Set up a new marketing campaign"
Actions:
1. Fetch existing campaigns via MCP
2. Create new campaign with provided parameters
Result: Campaign created with confirmation link

## Troubleshooting

### Error: [Common error message]
Cause: [Why it happens]
Solution: [How to fix]
```

**Best practices for instructions:**

| Practice | Good | Bad |
|----------|------|-----|
| Be specific and actionable | `Run python scripts/validate.py --input {filename}` with common issues listed | `Validate the data before proceeding.` |
| Include error handling | Explicit `## Common Issues` section with MCP connection steps | No error handling mentioned |
| Reference bundled resources | `Before writing queries, consult references/api-patterns.md for rate limiting guidance` | Inline all documentation |
| Use progressive disclosure | Keep SKILL.md focused; move detailed docs to `references/` | One massive file |

### Cohezion Relevance (Chapter 2)

**Naming compliance:** Cohezion's 143 PRIME skills use `SCREAMING_SNAKE_CASE` names (e.g., `COMPOUND_ENGINEERING_PRIME.md`). Anthropic requires `kebab-case` folders. The BMAD commands use kebab-case correctly.

**Description formula:** PRIME skills have a `## DOMAIN EXPERTISE` section that describes what the skill knows, but NOT when to trigger it or what user phrases should invoke it. This is the single biggest gap for triggering accuracy.

**File structure:** All 143 PRIME skills are flat `.md` files in `src/cohezion/skills/`. None use the folder structure with `scripts/`, `references/`, or `assets/`. The BMAD commands in `.claude/commands/` use YAML frontmatter but are commands (slash-invoked), not auto-triggering skills.

---

## Chapter 3: Testing and Iteration

### 3.1 Three Testing Approaches

| Approach | How | Best For |
|----------|-----|----------|
| **Manual (Claude.ai)** | Run queries directly and observe behavior | Fast iteration, no setup |
| **Scripted (Claude Code)** | Automate test cases for repeatable validation | Team skills, CI/CD |
| **Programmatic (Skills API)** | Build evaluation suites against defined test sets | Production, enterprise |

**Pro tip from Anthropic:** Iterate on a single challenging task until Claude succeeds, then extract the winning approach into a skill. This leverages in-context learning for faster signal.

### 3.2 Three Test Areas

#### Area 1: Triggering Tests
**Goal:** Ensure the skill loads at the right times.

```
Should trigger:
- "Help me set up a new ProjectHub workspace"
- "I need to create a project in ProjectHub"
- "Initialize a ProjectHub project for Q4 planning"

Should NOT trigger:
- "What's the weather in San Francisco?"
- "Help me write Python code"
- "Create a spreadsheet" (unless ProjectHub skill handles sheets)
```

**Test cases:** Triggers on obvious tasks, triggers on paraphrased requests, does NOT trigger on unrelated topics.

#### Area 2: Functional Tests
**Goal:** Verify the skill produces correct outputs.

```
Test: Create project with 5 tasks
Given: Project name "Q4 Planning", 5 task descriptions
When: Skill executes workflow
Then:
    - Project created in ProjectHub
    - 5 tasks created with correct properties
    - All tasks linked to project
    - No API errors
```

**Test cases:** Valid outputs generated, API calls succeed, error handling works, edge cases covered.

#### Area 3: Performance Comparison
**Goal:** Prove the skill improves results vs. baseline.

```
Without skill:
- User provides instructions each time
- 15 back-and-forth messages
- 3 failed API calls requiring retry
- 12,000 tokens consumed

With skill:
- Automatic workflow execution
- 2 clarifying questions only
- 0 failed API calls
- 6,000 tokens consumed
```

### 3.3 The skill-creator Tool

Available in Claude.ai (plugin directory) and Claude Code. Capabilities:

**Creating skills:** Generate from natural language descriptions, produce properly formatted SKILL.md with frontmatter, suggest trigger phrases and structure.

**Reviewing skills:** Flag common issues (vague descriptions, missing triggers, structural problems), identify over/under-triggering risks, suggest test cases.

**Iterative improvement:** After encountering edge cases or failures, feed those back to skill-creator to improve handling.

**Usage:** `"Use the skill-creator skill to help me build a skill for [your use case]"`

**Note:** skill-creator helps design and refine skills but does not execute automated test suites or produce quantitative evaluation results.

### 3.4 Iteration Based on Feedback

**Undertriggering signals:**
- Skill doesn't load when it should
- Users manually enabling it
- Support questions about when to use it

**Solution:** Add more detail and nuance to the description, including keywords for technical terms.

**Overtriggering signals:**
- Skill loads for irrelevant queries
- Users disabling it
- Confusion about purpose

**Solution:** Add negative triggers (e.g., "Do NOT use for simple data exploration"), be more specific about scope.

**Execution issues:**
- Inconsistent results
- API call failures
- User corrections needed

**Solution:** Improve instructions, add error handling sections.

### Cohezion Relevance (Chapter 3)

Cohezion has no trigger test suites for any of its 143 PRIME skills. Since PRIME skills lack YAML frontmatter descriptions, there's no triggering mechanism to test in the first place - they're loaded programmatically by the `SkillSelector` rather than by Claude's native skill engine. The BMAD commands have `description` fields but rely on exact slash-command invocation rather than natural language triggering.

---

## Chapter 4: Distribution and Sharing

### 4.1 Current Distribution Model (January 2026)

**Individual users:**
1. Download the skill folder
2. Zip the folder (if needed)
3. Upload via Claude.ai: Settings > Capabilities > Skills
4. Or place in Claude Code skills directory (`.claude/skills/`)

**Organization-level skills:**
- Admins deploy workspace-wide (shipped December 2025)
- Automatic updates across the organization
- Centralized management

**Open standard:** Anthropic published "Agent Skills" as an open standard. Skills are designed to be portable across tools and platforms, not locked to Claude. The `compatibility` field lets authors note platform-specific requirements.

### 4.2 Skills API

For programmatic use cases (applications, agents, automated workflows):

| Capability | Detail |
|-----------|--------|
| **Endpoint** | `/v1/skills` for listing and managing skills |
| **Messages API integration** | `container.skills` parameter to attach skills to API requests |
| **Version control** | Management through the Claude Console |
| **Agent SDK** | Works with Claude Agent SDK for custom agents |

**Note:** Skills in the API require the Code Execution Tool beta for the secure environment.

**When to use API vs. Claude.ai:**

| Use Case | Best Surface |
|----------|-------------|
| End users interacting directly | Claude.ai / Claude Code |
| Manual testing and iteration | Claude.ai / Claude Code |
| Individual, ad-hoc workflows | Claude.ai / Claude Code |
| Applications using skills programmatically | API |
| Production deployments at scale | API |
| Automated pipelines and agent systems | API |

### 4.3 Recommended Distribution Approach

1. **Host on GitHub** - Public repo with clear README, installation instructions, example usage with screenshots
2. **Document in MCP repo** - Link skills from MCP documentation, explain the MCP + skills value together
3. **Create an installation guide** - Step-by-step for both Claude.ai upload and Claude Code directory placement

### 4.4 Positioning Your Skill

**Focus on outcomes, not features:**

```
# Good (outcomes)
"The ProjectHub skill enables teams to set up complete project
workspaces in seconds - including pages, databases, and
templates - instead of spending 30 minutes on manual setup."

# Bad (features)
"The ProjectHub skill is a folder containing YAML frontmatter
and Markdown instructions that calls our MCP server tools."
```

**Highlight the MCP + skills story:**
```
"Our MCP server gives Claude access to your Linear projects.
Our skills teach Claude your team's sprint planning workflow.
Together, they enable AI-powered project management."
```

### Cohezion Relevance (Chapter 4)

Cohezion uses **three distinct distribution mechanisms**, none of which align with Anthropic's canonical model:

| Cohezion Mechanism | Location | Count | Anthropic Equivalent |
|-------------------|----------|-------|---------------------|
| PRIME skills | `src/cohezion/skills/*.md` | 143 | None (flat files, no folder structure) |
| BMAD commands | `.claude/commands/*.md` | 120 | Closest to slash-commands, not skills |
| Claude Code skills | `.claude/skills/*/` | 1 | Matches Anthropic spec |
| Team Vault (`sx`) | Git repo distribution | N/A | Organization-level skills |

The Team Vault (`sx`) system is the most advanced distribution mechanism and partially overlaps with Anthropic's org-level deployment, but distributes rules/commands rather than skills in the Anthropic folder format.

---

## Chapter 5: Patterns and Troubleshooting

### 5.1 Problem-First vs. Tool-First Design

| Approach | User Says | Skill Does |
|----------|-----------|-----------|
| **Problem-first** | "I need to set up a project workspace" | Orchestrates the right MCP calls in the right sequence; user describes outcomes |
| **Tool-first** | "I have Notion MCP connected" | Teaches Claude optimal workflows and best practices; user has access, skill provides expertise |

### 5.2 Five Design Patterns

#### Pattern 1: Sequential Workflow Orchestration

**Use when:** Multi-step processes in a specific order.

```markdown
## Workflow: Onboard New Customer

### Step 1: Create Account
Call MCP tool: `create_customer`
Parameters: name, email, company

### Step 2: Setup Payment
Call MCP tool: `setup_payment_method`
Wait for: payment method verification

### Step 3: Create Subscription
Call MCP tool: `create_subscription`
Parameters: plan_id, customer_id (from Step 1)

### Step 4: Send Welcome Email
Call MCP tool: `send_email`
Template: welcome_email_template
```

**Key techniques:** Explicit step ordering, dependencies between steps, validation at each stage, rollback instructions for failures.

#### Pattern 2: Multi-MCP Coordination

**Use when:** Workflows span multiple services.

```markdown
### Phase 1: Design Export (Figma MCP)
1. Export design assets from Figma
2. Generate design specifications
3. Create asset manifest

### Phase 2: Asset Storage (Drive MCP)
1. Create project folder in Drive
2. Upload all assets
3. Generate shareable links

### Phase 3: Task Creation (Linear MCP)
1. Create development tasks
2. Attach asset links to tasks
3. Assign to engineering team

### Phase 4: Notification (Slack MCP)
1. Post handoff summary to #engineering
2. Include asset links and task references
```

**Key techniques:** Clear phase separation, data passing between MCPs, validation before moving to next phase, centralized error handling.

#### Pattern 3: Iterative Refinement

**Use when:** Output quality improves with iteration.

```markdown
## Iterative Report Creation

### Initial Draft
1. Fetch data via MCP
2. Generate first draft report
3. Save to temporary file

### Quality Check
1. Run validation script: `scripts/check_report.py`
2. Identify issues:
    - Missing sections
    - Inconsistent formatting
    - Data validation errors

### Refinement Loop
1. Address each identified issue
2. Regenerate affected sections
3. Re-validate
4. Repeat until quality threshold met

### Finalization
1. Apply final formatting
2. Generate summary
3. Save final version
```

**Key techniques:** Explicit quality criteria, iterative improvement, validation scripts (deterministic checks), know when to stop iterating.

#### Pattern 4: Context-Aware Tool Selection

**Use when:** Same outcome, different tools depending on context.

```markdown
## Smart File Storage

### Decision Tree
1. Check file type and size
2. Determine best storage location:
    - Large files (>10MB): Use cloud storage MCP
    - Collaborative docs: Use Notion/Docs MCP
    - Code files: Use GitHub MCP
    - Temporary files: Use local storage

### Execute Storage
Based on decision:
- Call appropriate MCP tool
- Apply service-specific metadata
- Generate access link

### Provide Context to User
Explain why that storage was chosen
```

**Key techniques:** Clear decision criteria, fallback options, transparency about choices.

#### Pattern 5: Domain-Specific Intelligence

**Use when:** Skill adds specialized knowledge beyond tool access.

```markdown
## Payment Processing with Compliance

### Before Processing (Compliance Check)
1. Fetch transaction details via MCP
2. Apply compliance rules:
    - Check sanctions lists
    - Verify jurisdiction allowances
    - Assess risk level
3. Document compliance decision

### Processing
IF compliance passed:
    - Call payment processing MCP tool
    - Apply appropriate fraud checks
    - Process transaction
ELSE:
    - Flag for review
    - Create compliance case

### Audit Trail
- Log all compliance checks
- Record processing decisions
- Generate audit report
```

**Key techniques:** Domain expertise embedded in logic, compliance before action, comprehensive documentation, clear governance.

### 5.3 Troubleshooting Guide

| Problem | Symptom | Root Cause | Fix |
|---------|---------|------------|-----|
| **Skill won't upload** | "Could not find SKILL.md" | File not named exactly `SKILL.md` | Rename to `SKILL.md` (case-sensitive); verify with `ls -la` |
| **Invalid frontmatter** | Upload/parse error | YAML formatting issues (missing delimiters `---`, unclosed quotes) | Ensure `---` delimiters on own lines, proper YAML syntax |
| **Invalid skill name** | Name rejected | Name has spaces or capitals | Use kebab-case: `my-cool-skill` not `My Cool Skill` |
| **Skill doesn't trigger** | Never loads automatically | Description too generic or missing trigger phrases | Apply `[What] + [When] + [Capabilities]` formula; include user phrases |
| **Skill triggers too often** | Loads for unrelated queries | Description too broad | Add negative triggers ("Do NOT use for..."), be more specific, clarify scope |
| **MCP connection issues** | Skill loads but MCP calls fail | Server disconnected, auth expired, wrong tool names | Verify connection, check auth, test MCP independently, verify tool name case sensitivity |
| **Instructions not followed** | Correct skill, wrong behavior | Instructions too verbose, buried, or ambiguous | Keep concise, put critical items at top with `## Important` headers, use bullet points |
| **Large context issues** | Slow or degraded responses | Skill content too large or too many skills enabled | Keep SKILL.md under 5,000 words, move docs to `references/`, evaluate if 20-50 simultaneous skills is necessary, consider "packs" |
| **Model "laziness"** | Skips validation steps | No explicit encouragement | Add `## Performance Notes` with "Take your time", "Quality > speed", "Do not skip validation" |

**Advanced technique:** For critical validations, bundle a script in `scripts/` that performs checks programmatically rather than relying on language instructions. Code is deterministic; language interpretation isn't.

**Debugging trigger quality:** Ask Claude "When would you use the [skill name] skill?" and compare the response against your intended use cases. Adjust the description based on what's missing.

### Cohezion Relevance (Chapter 5)

Cohezion's compound engineering loop (CompoundExecutor 11-step pipeline) maps directly to **Pattern 1** (Sequential Workflow Orchestration). The `ExecutionOrchestrator` with its `RequestAlignmentAnalyzer`, `GlobalMetricsAggregator`, `DegradationDetector`, and `JourneyTracker` is a sophisticated implementation of Pattern 5 (Domain-Specific Intelligence) with embedded coherence checks before execution.

The `SkillRefiner` + `RetrospectionEngine` loop is a production implementation of **Pattern 3** (Iterative Refinement) at the meta-level - it refines skills themselves through feedback loops.

However, these patterns are implemented in Python code, not in SKILL.md instructions. They wouldn't be portable to Claude.ai or the Skills API. Converting the key patterns into skill instructions would make them usable across all Claude surfaces.

---

## Chapter 6: Resources and References

### 6.1 Official Documentation
- Best Practices Guide
- Skills Documentation
- API Reference
- MCP Documentation

### 6.2 Blog Posts
- "Introducing Agent Skills"
- "Engineering Blog: Equipping Agents for the Real World"
- "Skills Explained"
- "How to Create Skills for Claude"
- "Building Skills for Claude Code"
- "Improving Frontend Design through Skills"

### 6.3 Example Skills
- Public repository: `anthropic/skills` on GitHub
- Contains Anthropic-created skills that can be customized

### 6.4 Tools and Utilities
- **skill-creator:** Built into Claude.ai and Claude Code. Generate skills from descriptions, review and suggest improvements.
- **Validation:** Ask skill-creator to "Review this skill and suggest improvements"

### 6.5 Support
- General questions: Claude Developers Discord
- Bug reports: `anthropic/skills/issues` on GitHub (include skill name, error message, reproduction steps)

---

## Cohezion Gap Analysis

### Current State Inventory

| Dimension | Cohezion Current State | Anthropic Spec | Gap Severity |
|-----------|----------------------|----------------|-------------|
| **Skill format** | Flat `.md` files (PRIME) + commands (BMAD) | Folder with `SKILL.md` + optional dirs | **Critical** |
| **YAML frontmatter** | PRIME: None. BMAD: `name` + `description` | Required: `name` + `description` with formula | **Critical** |
| **Naming convention** | PRIME: `SCREAMING_SNAKE_CASE`. BMAD: `kebab-case` | `kebab-case` only | **High** |
| **Progressive disclosure** | Not implemented. All content in single file | 3-level system (frontmatter / body / linked files) | **High** |
| **Description formula** | PRIME: `## DOMAIN EXPERTISE` (no triggers). BMAD: brief descriptions | `[What] + [When] + [Capabilities]` with trigger phrases | **High** |
| **Folder structure** | Flat files, no `scripts/` `references/` `assets/` | Structured folders | **Medium** |
| **Trigger testing** | None | 3-area test suite (triggering, functional, performance) | **Medium** |
| **Distribution** | Team Vault (`sx`), git | Claude.ai upload, org-level, Skills API | **Medium** |
| **Composability** | SkillSelector routes programmatically | Claude's native skill engine routes by description | **Medium** |
| **Portability** | Cohezion-only (Python SkillSelector) | Claude.ai, Claude Code, API | **Medium** |
| **Validation scripts** | None bundled with skills | `scripts/` directory for deterministic checks | **Low** |
| **skill-creator usage** | Not used | Built-in tool for generating and reviewing | **Low** |

### Detailed Gap Analysis

#### Gap 1: No YAML Frontmatter on PRIME Skills (Critical)

**Current:** PRIME skills use `# SKILL: COMPOUND_ENGINEERING_PRIME` as a header with `## DOMAIN EXPERTISE`, `## INSTRUCTION`, `## VERSION`, `## SEE ALSO` sections. No YAML frontmatter.

**Impact:** Claude's native skill engine cannot auto-trigger PRIME skills. They're only accessible through Cohezion's custom `SkillSelector` which matches keywords programmatically. This means:
- Skills don't work in Claude.ai or Claude Code natively
- No progressive disclosure (Level 1 frontmatter doesn't exist)
- Token efficiency suffers (entire skill must be loaded to know if it's relevant)

**Example transformation needed:**
```yaml
# Current (PRIME format)
# SKILL: COMPOUND_ENGINEERING_PRIME
## DOMAIN EXPERTISE
Unified technical methodology for cross-platform agentic orchestration...

# Proposed (Anthropic format)
---
name: compound-engineering
description: Unified methodology for agentic orchestration, local model
  optimization, and hallucination mitigation. Use when implementing
  compound AI features, setting up model routing, or debugging coherence
  issues in the Cohezion ecosystem.
metadata:
  author: Cohezion
  version: 1.0
  mcp-server: cohezion-bridge
---
```

#### Gap 2: No Progressive Disclosure (High)

**Current:** All 143 PRIME skills are monolithic files averaging ~83 lines each (11,891 total lines / 143 files). Some are compact (42 lines for COMPOUND_ENGINEERING_PRIME) but others are substantial (95 lines for TESTING_PRIME).

**Impact:** When any PRIME skill is loaded, ALL its content enters context. With 143 skills, even loading 10% means ~1,200 lines of instructions competing for context space.

**Anthropic's recommendation:** Keep SKILL.md under 5,000 words. Move detailed documentation to `references/`. Evaluate if more than 20-50 skills are enabled simultaneously.

**Cohezion concern:** 143 simultaneous skills far exceeds Anthropic's suggested 20-50 limit. The SkillSelector mitigates this by only loading relevant skills, but the lack of progressive disclosure means there's no Level 1 "index" for efficient pre-filtering.

#### Gap 3: Description Quality (High)

**Current PRIME descriptions** (from `## DOMAIN EXPERTISE`):
```
# Typical PRIME
"Unified technical methodology for cross-platform agentic orchestration,
local model optimization, and defensive intelligence within the Cohezion ecosystem."
```

This describes WHAT the skill knows but not WHEN to use it or WHAT trigger phrases should invoke it.

**Anthropic's formula applied:**
```
"Unified methodology for agentic orchestration, local model optimization,
and hallucination mitigation in Cohezion. Use when implementing compound
AI features, debugging coherence drift, setting up model routing, or when
user mentions 'compound engineering', 'skill refinement', or 'orchestration'."
```

The addition of trigger phrases and user language is the single highest-impact improvement for triggering accuracy.

#### Gap 4: Dual Skill System Creates Confusion (Medium)

Cohezion has two parallel systems:
1. **143 PRIME skills** in `src/cohezion/skills/` - loaded by Python `SkillSelector`, not by Claude's native engine
2. **120 BMAD commands** in `.claude/commands/` - invoked by slash commands, not auto-triggered

Neither system produces skills that work through Claude's native triggering. The BMAD commands are the closest (they have YAML frontmatter with `name` and `description`) but they're commands, not skills - they require explicit `/command-name` invocation.

#### Gap 5: Root SKILL.md is a Placeholder (Low but Visible)

The project root contains a `SKILL.md` with placeholder content:
```yaml
---
name: cohezion
description: A brief description of what this skill does
---
# cohezion
Instructions for the agent to follow when this skill is activated.
```

This is the file that represents the entire Cohezion project as a skill when uploaded to Claude.ai. It should be the most polished skill in the repository, not a template placeholder.

---

## Actionable Recommendations

### Recommendation 1: Adopt Folder Structure for New Skills (Priority: High, Effort: Low)

**Action:** All new skills created going forward should use the Anthropic folder structure:

```
.claude/skills/
|-- compound-engineering/
|   |-- SKILL.md
|   |-- references/
|   |   |-- model-routing-patterns.md
|   |   |-- coherence-debugging.md
|   |-- scripts/
|       |-- validate_coherence.py
```

**Rationale:** Low effort (just organize files differently), high payoff (portable to Claude.ai, API, and other platforms). Does not require changing existing PRIME skills.

### Recommendation 2: Add YAML Frontmatter to Top 20 PRIME Skills (Priority: High, Effort: Medium)

**Action:** Identify the 20 most-used PRIME skills and add proper YAML frontmatter with the `[What] + [When] + [Capabilities]` description formula. Priority candidates:
- `COMPOUND_ENGINEERING_PRIME` - core workflow
- `TESTING_PRIME` - used every session
- `SECURITY_GUARDRAILS_PRIME` - safety-critical
- `FLUME_METHODOLOGY_PRIME` - core architecture
- `TOKEN_EFFICIENCY_PRIME` - cost optimization
- `TEAM_ORCHESTRATION_PRIME` - swarm coordination
- `RELIABILITY_PRIME` - system stability
- `SELF_HEALING_PRIME` - autonomic recovery
- `MODEL_ROUTING_PRIME` - model selection
- `SEMANTIC_CACHING_PRIME` - performance

**Rationale:** Enables Claude's native triggering engine. The description formula with trigger phrases dramatically improves auto-invocation accuracy.

### Recommendation 3: Implement Progressive Disclosure (Priority: High, Effort: Medium)

**Action:** For skills exceeding 50 lines, split into:
- SKILL.md: Core instructions only (under 5,000 words)
- `references/`: Detailed documentation, API patterns, examples
- `scripts/`: Validation scripts for deterministic checks

**Rationale:** Anthropic explicitly warns about degraded performance with >20-50 simultaneous skills and large SKILL.md files. With 143 skills, progressive disclosure is essential for token efficiency.

### Recommendation 4: Create Trigger Test Suites (Priority: Medium, Effort: Low)

**Action:** For each skill with YAML frontmatter, create a test file with:
- 5 phrases that SHOULD trigger the skill
- 5 phrases that SHOULD NOT trigger the skill
- 3 paraphrased versions of trigger phrases

**Format:**
```yaml
# tests/skills/test_compound_engineering_triggers.yaml
skill: compound-engineering
should_trigger:
  - "Help me set up a compound engineering pipeline"
  - "Debug coherence drift in the executor"
  - "Configure model routing for the swarm"
should_not_trigger:
  - "What's the weather today?"
  - "Write a Python hello world"
  - "Create a database migration"
```

**Rationale:** Without trigger tests, there's no way to measure or improve triggering accuracy. Anthropic recommends 90% trigger rate as a target.

### Recommendation 5: Fix the Root SKILL.md (Priority: Medium, Effort: Low)

**Action:** Replace the placeholder with a proper skill definition:

```yaml
---
name: cohezion
description: Compound AI orchestration framework with 12D universe
  simulation, FLUME VAE training, multi-agent swarm coordination,
  and autonomous skill refinement. Use when building AI applications,
  orchestrating multi-agent workflows, managing model routing, or
  implementing compound engineering patterns.
metadata:
  author: Cohezion
  version: 1.0.2
  compatibility: Python 3.13+, SurrealDB
---

# Cohezion

## Instructions
[Core workflow instructions for using Cohezion as an AI orchestration skill]
```

**Rationale:** This is the first thing users see when they upload Cohezion as a skill. It should represent the project's capabilities accurately.

### Recommendation 6: Evaluate Skills API Integration (Priority: Medium, Effort: Low)

**Action:** Investigate using the `/v1/skills` endpoint and `container.skills` Messages API parameter for programmatic skill deployment. This could complement or replace the custom `SkillSelector`.

**Rationale:** The Skills API provides version control, centralized management, and works with the Agent SDK. Cohezion's programmatic use case (automated pipelines, agent systems) is exactly the use case Anthropic recommends the API for.

### Recommendation 7: Leverage skill-creator for Quality Improvement (Priority: Low, Effort: Low)

**Action:** Run existing PRIME skills through Claude's built-in `skill-creator` tool with the prompt: "Review this skill and suggest improvements." Batch-process the top 20 skills.

**Rationale:** Free, built-in validation that catches common issues (vague descriptions, missing triggers, structural problems). No custom tooling needed.

### Recommendation 8: Bundle Validation Scripts (Priority: Low, Effort: Medium)

**Action:** For skills that involve data processing, API calls, or compliance checks, create deterministic validation scripts in `scripts/` rather than relying on language instructions alone.

**Rationale:** Anthropic explicitly recommends this as an "advanced technique" - code is deterministic, language interpretation isn't. Cohezion already has validation logic in Python; bundling key validators with their corresponding skills improves reliability.

---

## Migration Path: PRIME to Anthropic-Compatible Skills

For teams wanting to migrate existing PRIME skills, here's a phased approach:

### Phase 1: Frontmatter Addition (No Breaking Changes)

Add YAML frontmatter to existing PRIME skills without changing their structure:

```markdown
---
name: compound-engineering
description: [What + When + Capabilities formula]
metadata:
  version: 1.0
  legacy-name: COMPOUND_ENGINEERING_PRIME
---

# SKILL: COMPOUND_ENGINEERING_PRIME
[... existing content unchanged ...]
```

This enables Claude's native triggering while preserving compatibility with the existing `SkillSelector`.

### Phase 2: Folder Migration (Selective)

Convert high-value skills to folder structure:
```
mv src/cohezion/skills/COMPOUND_ENGINEERING_PRIME.md \
   .claude/skills/compound-engineering/SKILL.md
```

Split large skills, moving detailed content to `references/`.

### Phase 3: Progressive Disclosure Optimization

Audit all skills for token efficiency:
- SKILL.md body: Core instructions only
- references/: Detailed docs, examples, API patterns
- scripts/: Deterministic validation

### Phase 4: Distribution Alignment

Evaluate publishing top skills to:
- Anthropic's public `anthropic/skills` repo
- Claude.ai plugin directory
- Skills API for programmatic consumers
- Team Vault (`sx`) for internal distribution (already in place)

---

## Appendix A: Anthropic's Description Formula Applied to Cohezion Skills

| PRIME Skill | Current Domain Expertise | Proposed Description (Anthropic Formula) |
|------------|------------------------|----------------------------------------|
| COMPOUND_ENGINEERING | "Unified technical methodology for cross-platform agentic orchestration..." | "Compound AI orchestration methodology for multi-agent coordination, local model optimization, and hallucination mitigation. Use when implementing compound features, debugging coherence drift, or when user mentions 'compound engineering', 'skill refinement', or 'orchestration loop'." |
| TESTING_PRIME | "Comprehensive testing strategy..." | "Testing methodology for Cohezion's compound AI system including singleton isolation, mock strategies, and HIHO invariant testing. Use when writing tests, debugging flaky test suites, or when user says 'test isolation', 'conftest', or 'mock at source'." |
| SECURITY_GUARDRAILS | "Security-first design patterns..." | "Security guardrail implementation for AI agent systems including prompt injection defense, credential management, and OWASP LLM Top 10 mitigations. Use when implementing auth, reviewing security, or when user mentions 'security', 'prompt guard', or 'credential rotation'." |

## Appendix B: Pattern Mapping - Cohezion Components to Anthropic Patterns

| Anthropic Pattern | Cohezion Implementation | Status |
|------------------|------------------------|--------|
| 1. Sequential Workflow Orchestration | `CompoundExecutor` 11-step pipeline | Implemented in Python, not as SKILL.md |
| 2. Multi-MCP Coordination | `cloud-vault-mcp` + `cohezion-bridge` + `cohezion-swarm` | Implemented, could benefit from skill instructions for cross-MCP workflows |
| 3. Iterative Refinement | `SkillRefiner` + `RetrospectionEngine` | Implemented as meta-level skill refinement loop |
| 4. Context-Aware Tool Selection | `CostAwareRouter` + `DynamicModelRouter` | Sophisticated implementation with cost optimization |
| 5. Domain-Specific Intelligence | `RequestAlignmentAnalyzer` + `DegradationDetector` | Production implementation with HIHO coherence checks |

## Appendix C: Key Metrics for Tracking Skill Quality

Based on Anthropic's success criteria framework, adapted for Cohezion:

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Trigger accuracy (top 20 skills) | 90% | Run 10-20 test queries per skill, track auto vs. manual invocation |
| Token reduction (progressive disclosure) | 50% reduction | Compare context size before/after splitting skills into references/ |
| Workflow completion (without user intervention) | 80% | Run same request 3-5 times, track user corrections needed |
| API call success rate | 0 failures | Monitor MCP server logs during skill execution |
| Cross-session consistency | 90% structural similarity | Compare outputs across sessions for identical requests |
| SKILL.md size compliance | < 5,000 words | Automated check in CI/CD |
| Enabled skill count | < 50 simultaneous | Monitor context loading, consider skill "packs" |

---

## Research Methodology

**Sources consulted:**
1. "The Complete Guide to Building Skills for Claude" - Anthropic (29 pages, PDF, all 6 chapters read in full)
2. Cohezion codebase analysis: `src/cohezion/skills/` (143 files), `.claude/commands/` (120 files), `.claude/skills/` (1 skill), `SKILL.md` (root), `skill_registry.json`
3. Anthropic's `anthropic/skills` GitHub repository (referenced in guide)

**Verification:** All technical claims are sourced from the PDF pages directly. Cohezion file counts and structures verified via `Glob`, `Read`, and `Bash` against the live codebase. No speculative claims.
