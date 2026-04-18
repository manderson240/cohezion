# Coherence MCP Server - Implementation Summary

## What Was Built

### 1. Coherence MCP Server (`src/cohezion/mcp/coherence_server.py`)
An MCP server exposing the existing coherence systems via standardized tools:

**Tools Exposed:**
- `coherence.check_alignment` - HIHO alignment scoring with intent classification
- `coherence.track_journey_step` - 12D FLUME trajectory recording
- `coherence.get_trajectory` - Retrieve recent journey points
- `coherence.detect_degradation` - Coherence degradation alerts
- `coherence.calculate_hiho` - HIHO stability score calculation
- `coherence.extract_pattern` - FLUME pattern encoding
- `coherence.query_patterns` - Vault pattern search
- `coherence.refine_skill` - Append patterns to PRIME skills

**Integration:**
- Uses existing `HihoVectorEngine` from `cohezion.swarm.hiho_vector_engine`
- Uses existing `JourneyTracker` from `cohezion.compound.journey_tracker`
- Uses existing `DegradationDetector` from `cohezion.compound.degradation_detector`
- Uses existing `RequestAlignmentAnalyzer` from `cohezion.compound.request_alignment_analyzer`

### 2. Updated Pi Extension (`.pi/extensions/cohezion-bridge.ts`)
Rewrote the extension to use MCP calls instead of stub implementations:

**Before:** Stub implementations with hardcoded values
**After:** Real coherence calculation via MCP:
- `checkAlignment()` now calls `coherence.check_alignment` MCP tool
- `recordJourneyStep()` now calls `coherence.track_journey_step` MCP tool
- `refineSkill()` now calls `coherence.refine_skill` MCP tool
- Pattern extraction now calls `coherence.extract_pattern` MCP tool

**New Commands:**
- `/cohezion alignment <intent>` - Interactive HIHO alignment check
- `/cohezion trajectory` - Show recent FLUME trajectory
- `/cohezion hiho <coherence>` - Calculate HIHO stability for a value

### 3. MCP Server Registration
Added coherence server to MCP configurations:

**`.gemini/settings.json`:**
```json
"cohezion-coherence": {
  "command": "PYTHONPATH=/home/mike-anderson/dev/cohezion/src /home/mike-anderson/dev/cohezion/.venv/bin/python -m cohezion.mcp.coherence_server",
  "args": [],
  "description": "HIHO coherence calculation and FLUME journey tracking"
}
```

**`.claude/mcp.json`:**
```json
"cohezion-coherence": {
  "name": "Cohezion Coherence Engine",
  "type": "stdio",
  "command": "/home/mike-anderson/dev/cohezion/.venv/bin/python",
  "args": ["-m", "cohezion.mcp.coherence_server"],
  "description": "HIHO coherence calculation, FLUME journey tracking, pattern extraction"
}
```

## How It Works

### HIHO Alignment Flow
```
User Request
    ↓
pi.tool_call event
    ↓
cohezionBridge.checkAlignment()
    ↓
MCP: coherence.check_alignment
    ↓
RequestAlignmentAnalyzer.parse_request()
    ↓
Intent classification + Tool fit + Vault query
    ↓
HIHO score calculation (HihoVectorEngine)
    ↓
Return: coherence, hiho_score, should_proceed, issues
    ↓
pi either blocks or proceeds based on coherence
```

### Journey Tracking Flow
```
Tool execution complete
    ↓
pi.tool_result event
    ↓
cohezionBridge.recordJourneyStep()
    ↓
MCP: coherence.track_journey_step
    ↓
JourneyTracker.track_execution()
    ↓
12D FLUME trajectory point generated
    ↓
Stored to vault (async, non-blocking)
```

## Verification

The coherence systems already exist in the codebase:
- ✅ `HihoVectorEngine` - HIHO stability scoring
- ✅ `JourneyTracker` - 12D FLUME trajectories
- ✅ `DegradationDetector` - Coherence monitoring
- ✅ `RequestAlignmentAnalyzer` - Intent classification

## Next Steps

1. **Start the coherence MCP server:**
   ```bash
   uv run python -m cohezion.mcp.coherence_server
   ```

2. **Test with pi:**
   ```
   /cohezion alignment 'generate code'
   /cohezion trajectory
   /cohezion hiho 0.5
   ```

3. **Monitor:**
   - Check `.pi/trajectories/current.jsonl` for local trajectory
   - Check vault for persisted journey points
   - Check skill files for auto-appended refinements

## Architecture

The coherence server runs as a separate MCP process that:
1. Loads existing coherence modules from `src/cohezion/`
2. Exposes them as MCP tools
3. Maintains state per session via in-memory caches
4. Persists to vault asynchronously (non-blocking)

The pi extension:
1. Calls MCP tools via subprocess
2. Receives JSON responses
3. Makes decisions (block/proceed) based on coherence
4. Records trajectories for future learning

## Files Created/Modified

**New:**
- `src/cohezion/mcp/coherence_server.py` - MCP server implementation
- `scripts/test_coherence_mcp.py` - Test script

**Modified:**
- `.pi/extensions/cohezion-bridge.ts` - Now uses MCP calls
- `.gemini/settings.json` - Added coherence MCP server
- `.claude/mcp.json` - Added coherence MCP server
