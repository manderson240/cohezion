# Plan: Plan Traceability Graph + Webapp Fix + Plan Archival Hook

## Step 0: BMAD-Aligned Plan Traceability (Foundation — Do This First)

Extend BMAD's existing `TraceabilityEngine` with plan lifecycle tracking. Use the same patterns: CSV manifests, invocation tracking, snapshot exports, and the `testarch-trace` workflow for quality gates. Persist to SurrealDB for graph queries.

**Existing BMAD infrastructure we reuse:**
- `_bmad/_config/traceability/traceability_engine.py` — `TraceabilityEngine` (BaseEngine subclass)
- `_bmad/_config/traceability/snapshots/` — timestamped CSV exports
- `_bmad/tea/workflows/testarch/trace/` — requirements traceability workflow
- Data classes: `Agent`, `Workflow`, `Task`, `Invocation`, `WorkflowChain`, `TraceabilityMatrix`

**What we add:**
- `Plan` and `PlanTask` data classes extending the existing model
- `plan-manifest.csv` alongside the existing manifests
- SurrealDB persistence (graph edges for plan→task→file→commit)
- Hooks that automatically track plan events

### 0.0 SurrealDB Schema (`src/cohezion/knowledge_graph/plan_traceability_schema.surql`)

```sql
-- Plan lifecycle
DEFINE TABLE plan SCHEMAFULL;
DEFINE FIELD name ON plan TYPE string;
DEFINE FIELD slug ON plan TYPE string;
DEFINE FIELD status ON plan TYPE string ASSERT $value IN ["draft", "approved", "in_progress", "completed", "abandoned"];
DEFINE FIELD created_at ON plan TYPE datetime DEFAULT time::now();
DEFINE FIELD completed_at ON plan TYPE option<datetime>;
DEFINE FIELD source_file ON plan TYPE string;          -- docs/plans/2026-03-30-webapp-fix.md
DEFINE FIELD archived_from ON plan TYPE option<string>; -- ~/.claude/plans/zazzy-snuggling-corbato.md
DEFINE FIELD tasks_total ON plan TYPE int DEFAULT 0;
DEFINE FIELD tasks_completed ON plan TYPE int DEFAULT 0;
DEFINE FIELD session_id ON plan TYPE option<string>;
DEFINE INDEX idx_plan_slug ON plan FIELDS slug UNIQUE;

-- Task within a plan
DEFINE TABLE task SCHEMAFULL;
DEFINE FIELD title ON task TYPE string;
DEFINE FIELD status ON task TYPE string ASSERT $value IN ["pending", "in_progress", "completed", "skipped"];
DEFINE FIELD step_number ON task TYPE string;           -- "1.2", "3.1"
DEFINE FIELD created_at ON task TYPE datetime DEFAULT time::now();
DEFINE FIELD completed_at ON task TYPE option<datetime>;
DEFINE INDEX idx_task_status ON task FIELDS status;

-- File touched by a task
DEFINE TABLE file SCHEMAFULL;
DEFINE FIELD path ON file TYPE string;
DEFINE FIELD last_modified ON file TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_file_path ON file FIELDS path UNIQUE;

-- Git commit
DEFINE TABLE commit SCHEMAFULL;
DEFINE FIELD hash ON commit TYPE string;
DEFINE FIELD message ON commit TYPE string;
DEFINE FIELD timestamp ON commit TYPE datetime DEFAULT time::now();
DEFINE FIELD author ON commit TYPE string DEFAULT "mike-anderson";
DEFINE INDEX idx_commit_hash ON commit FIELDS hash UNIQUE;

-- Edges (bidirectional by query)
DEFINE TABLE plan_has_task SCHEMAFULL;    -- plan -> task
DEFINE TABLE task_modifies SCHEMAFULL;    -- task -> file
DEFINE TABLE commit_implements SCHEMAFULL; -- commit -> task
DEFINE TABLE commit_touches SCHEMAFULL;   -- commit -> file
```

### 0.1 Extend TraceabilityEngine (`_bmad/_config/traceability/traceability_engine.py`)

Add `Plan` and `PlanTask` data classes alongside existing Agent/Workflow/Task:
```python
@dataclass
class Plan:
    slug: str
    name: str
    status: str  # draft, approved, in_progress, completed, abandoned
    source_file: str  # docs/plans/2026-03-30-webapp-fix.md
    tasks_total: int
    tasks_completed: int
    session_id: str
    created_at: str
    completed_at: str | None


@dataclass
class PlanTask:
    plan_slug: str
    step_number: str  # "1.2", "3.1"
    title: str
    status: str  # pending, in_progress, completed, skipped
    files_modified: list[str]
    commits: list[str]
```

Add to `TraceabilityMatrix`:
```python
plan_task: list[dict]  # plan → task mappings
task_file: list[dict]  # task → file mappings
task_commit: list[dict]  # task → commit mappings
```

Add new methods:
- `load_plan_manifest()` — reads `plan-manifest.csv`
- `build_plan_graph()` — builds plan→task→file→commit edges
- `detect_orphan_files()` — files modified outside any plan
- `plan_completeness(slug)` — percentage of tasks completed
- `export_plan_snapshot()` — timestamped CSV to `snapshots/`

### 0.1b SurrealDB Persistence (`src/cohezion/traceability/plan_graph.py`)

Thin async client wrapping SurrealDB operations:
```python
class PlanGraph:
    async def create_plan(slug, name, source_file, tasks) -> str
    async def update_plan_status(slug, status) -> None
    async def complete_task(plan_slug, step_number) -> None
    async def record_file_touch(plan_slug, step_number, file_path) -> None
    async def record_commit(hash, message, task_steps) -> None

    # Queries
    async def plan_completeness(slug) -> dict  # {total, completed, pct}
    async def files_for_plan(slug) -> list[str]
    async def plans_for_file(path) -> list[str]
    async def orphan_files() -> list[str]  # files not linked to any plan
    async def plan_graph(slug) -> dict      # full plan with all edges
```

### 0.2 Hook: Archive + Register Plan (`archive-plan.sh`)
When a plan file is written:
1. Archive previous content to `docs/plans/YYYY-MM-DD-<slug>.md`
2. Parse the new plan for tasks (lines matching `- [ ] **N.N ...`)
3. Register the plan + tasks in SurrealDB via `uv run python -m cohezion.traceability.register_plan`

### 0.3 Hook: Track File Modifications (`track-plan-files.sh`)
PostToolUse on Edit|Write:
1. Check if there's an active plan (query SurrealDB for `status="in_progress"`)
2. Record the file path as `task_modifies` edge from the current active task

### 0.4 Hook: Track Commits (`track-plan-commits.sh`)
PostToolUse on Bash (when command matches `git commit`):
1. Extract commit hash + message
2. Link to active plan tasks via `commit_implements` + `commit_touches` edges

### 0.5 BMAD Trace Workflow Integration
- Extend `testarch-trace` to include plan traceability alongside requirements traceability
- Add `plan-manifest.csv` to `_bmad/_config/` (auto-generated from `docs/plans/`)
- Hook into the existing `traceability_engine.py` snapshot system for timestamped exports

### 0.6 CLI Queries (`cz plan` extensions)
- `cz plan status --graph` — shows plan completeness with file/commit counts per task
- `cz plan trace <file>` — shows which plans/tasks touched a file (SurrealDB query)
- `cz plan orphans` — shows files modified outside any plan
- `cz plan matrix` — generates BMAD-style traceability matrix (plan→task→file→commit)

### 0.7 Update CLAUDE.md + Workflow Rules
- Add traceability section to CLAUDE.md
- Update `workflow-enforcement.md` to require plan registration
- Add to session start: check for active plans, resume from graph state
- New rule: "Every plan must be registered in SurrealDB via the archive-plan hook"

## Step 1: Plan Archival Hook (Part of Step 0)

Create a PreToolUse hook that archives existing plan files before Claude overwrites them.

### 0.1 Create `.claude/hooks/archive-plan.sh`
```bash
#!/usr/bin/env bash
# Archive plan files before they're overwritten by plan mode.
# Triggered by PreToolUse on Write when target is ~/.claude/plans/*.md

set -euo pipefail

# Read stdin (hook input JSON)
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only act on plan files
if [[ "$FILE_PATH" != *"/.claude/plans/"* ]] || [[ "$FILE_PATH" != *.md ]]; then
  exit 0
fi

# Skip if file doesn't exist yet (first write = no archive needed)
if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Skip if file is empty or trivially small (< 50 bytes)
if [[ $(stat -c%s "$FILE_PATH" 2>/dev/null || echo 0) -lt 50 ]]; then
  exit 0
fi

# Extract slug from filename (e.g., "zazzy-snuggling-corbato" from the path)
BASENAME=$(basename "$FILE_PATH" .md)
DATE=$(date +%Y-%m-%d)
ARCHIVE_DIR="/home/mike-anderson/dev/cohezion/docs/plans"
ARCHIVE_PATH="${ARCHIVE_DIR}/${DATE}-${BASENAME}.md"

# Don't archive if we already archived today with the same name
if [[ -f "$ARCHIVE_PATH" ]]; then
  exit 0
fi

# Archive
mkdir -p "$ARCHIVE_DIR"
cp "$FILE_PATH" "$ARCHIVE_PATH"

echo "{\"systemMessage\": \"Archived previous plan to docs/plans/${DATE}-${BASENAME}.md\"}"
```

### 0.2 Add hook to `.claude/settings.json`
Add to the existing `PreToolUse` array:
```json
{
  "matcher": "Write",
  "hooks": [
    {
      "type": "command",
      "command": ".claude/hooks/archive-plan.sh",
      "statusMessage": "Archiving previous plan..."
    }
  ]
}
```

### 0.3 Pipe-test
```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"/home/mike-anderson/.claude/plans/zazzy-snuggling-corbato.md","content":"# New Plan"}}' | .claude/hooks/archive-plan.sh
# Should output: {"systemMessage": "Archived previous plan to docs/plans/2026-03-30-zazzy-snuggling-corbato.md"}
```

### 0.4 Validate
```bash
jq -e '.hooks.PreToolUse[] | select(.matcher == "Write") | .hooks[] | select(.command | contains("archive-plan"))' .claude/settings.json
```

---

## Context

The Cohezion webapp at `https://frameworkdesktop.tail54eb71.ts.net/` looks visually impressive but is functionally broken because:

1. **Port mismatch**: `.env.local` points to `localhost:8888` but the FastAPI backend runs on port `8080`
2. **Missing router registrations**: `anima` and `architecture` services exist but aren't mounted in the FastAPI app
3. **No backend running**: only the Next.js frontend (port 3000) is running as a systemd service
4. **No fallback**: when the backend is unreachable, the frontend shows zeros/defaults instead of simulated data

The home page 3D visualization, Bloch sphere, and cosmogony equations all render correctly — the issue is purely data connectivity.

## Fix Strategy

### Step 1: Fix port configuration
- **File**: `src/web/anima_dashboard/.env.local`
- **Change**: `NEXT_PUBLIC_API_URL=http://localhost:8888` → `NEXT_PUBLIC_API_URL=http://localhost:8080`
- Rebuild Next.js after changing

### Step 2: Mount missing API routers
- **File**: `src/cohezion/api/__init__.py`
- Register the `anima` router (from `src/cohezion/api/services/anima.py`) with `include_router(anima_router, prefix="/api/anima")`
- Register the `architecture` router (from `src/cohezion/api/services/architecture.py`) with `include_router(architecture_router, prefix="/api/architecture")`
- Check if `brand` router is also needed

### Step 3: Create FastAPI systemd service
- Create `/etc/systemd/system/cohezion-api.service` running `uv run uvicorn cohezion.api:app --host 127.0.0.1 --port 8080`
- WorkingDirectory: `/home/mike-anderson/dev/cohezion`
- User: `mike-anderson`
- Enable + start alongside `cohezion-genesis.service`

### Step 4: Add client-side fallback physics
For each hook that calls the backend, add graceful degradation that simulates physics locally when the API is unreachable:

- **`useUniverseStream.ts`**: If SSE connection fails, run a local interval that ticks coherence toward HIHO (0.5) with noise, generates synthetic CA grid, and creates mock EVO states. This makes the home page particle visualization and telemetry panels come alive even without the backend.

- **`useUniverseState.ts`**: If POST to `/api/universe/tick` fails, use local state with HIHO-attractor dynamics (same as the WASM stub physics).

- **`useAnima.ts`**: If `/api/anima/status` fails, set status to `{ tier: "offline", online: false }` and show a "Backend offline — showing simulated physics" banner instead of broken "OFFLINE" badge.

- **Genesis page cosmogony**: If POST to `/api/genesis/cosmogony/set-temperature` fails, run the Landau phase transition math locally in the browser (the equations are already rendered via KaTeX — just wire them to the temperature slider directly).

- **SPIN Lab**: Already partially works locally (sliders update the Bloch sphere via React state). Just suppress the failed API calls to `/api/genesis/spinor/rotate`.

### Step 5: Rebuild and restart
- `cd src/web/anima_dashboard && npm run build`
- `sudo systemctl restart cohezion-genesis`
- `sudo systemctl start cohezion-api`
- Verify both services running, then test all pages

### Step 6: Update Caddy to proxy the API too
- **File**: `/etc/caddy/Caddyfile`
- Add `reverse_proxy /api/* localhost:8080` alongside the Next.js proxy
- This makes the API accessible via the public URL too (needed for when `cohezion.duckdns.org` goes live)

## Key Files to Modify

| File | Change |
|------|--------|
| `src/web/anima_dashboard/.env.local` | Port 8888 → 8080 |
| `src/cohezion/api/__init__.py` | Mount anima + architecture routers |
| `/etc/systemd/system/cohezion-api.service` | New file — FastAPI systemd service |
| `/etc/caddy/Caddyfile` | Add API proxy route |
| `src/web/anima_dashboard/src/hooks/useUniverseStream.ts` | Add fallback simulation |
| `src/web/anima_dashboard/src/hooks/useUniverseState.ts` | Add fallback simulation |
| `src/web/anima_dashboard/src/hooks/useAnima.ts` | Graceful offline state |
| `src/web/anima_dashboard/src/components/genesis/GenesisScene.tsx` | Local cosmogony fallback |

## Verification

### Traceability Graph
1. `surreal sql` → `SELECT * FROM plan WHERE slug = 'webapp-fix';` returns the plan with task count
2. `surreal sql` → `SELECT <-plan_has_task<-plan.name, title, status FROM task;` shows tasks linked to plan
3. After editing a file: `surreal sql` → `SELECT ->task_modifies->file.path FROM task;` shows file links
4. `cz plan status --graph` shows completeness percentage
5. Hook fires on plan Write: archived file appears in `docs/plans/`

### Webapp Fix
6. `curl -s http://localhost:8080/health` → 200 (backend running)
7. `curl -s http://localhost:8080/api/universe/state` → JSON with coherence data
8. Open https://frameworkdesktop.tail54eb71.ts.net/ — particle visualization animates with live data
9. Open /genesis — "Click to begin" triggers cosmogony sequence
10. Stop backend → frontend gracefully falls back to simulated physics
11. Restart backend → reconnects and shows live data again
