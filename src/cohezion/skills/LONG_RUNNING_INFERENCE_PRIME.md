---
name: long-running-inference-prime
description: "Enable multi-hour inference tasks with automatic checkpointing, streaming progress, and graceful resumption."
metadata:
  version: "1.0"
  source: "src/cohezion/skills/LONG_RUNNING_INFERENCE_PRIME.md"
---

# PRIME Skill: Long-Running Inference

## Purpose
Enable multi-hour inference tasks with automatic checkpointing, streaming progress, and graceful resumption.

## Instructions

### 1. INIT_SESSION
Create new inference session with checkpoint configuration.

**Input**: Session ID (optional), config (checkpoint interval, timeout)
**Process**:
  - Generate unique session ID if needed
  - Validate checkpoint configuration
  - Initialize session state
  - Register in session registry

**Output**: Session object with ID and config

### 2. LOAD_CHECKPOINT
Resume from vault checkpoint if session exists.

**Input**: Session ID
**Process**:
  - Query vault for checkpoint
  - Fallback to local JSONL if vault unavailable
  - Validate checkpoint integrity
  - Load state (step, context, intermediate results)

**Output**: SessionState if found, None otherwise

### 3. EXECUTE_STEPS
Execute inference steps with streaming progress.

**Input**: Session, skill name, input text, execute_fn
**Process**:
  - Initialize from checkpoint or from start
  - Execute steps sequentially
  - Stream SSE events for each step
  - Handle errors without stopping session
  - Support graceful cancellation

**Output**: Async iterator of event dicts

### 4. CHECKPOINT
Save session state to vault periodically.

**Input**: Session state, step index
**Process**:
  - Create snapshot of current state
  - Serialize intermediate results
  - Try vault persistence first
  - Fallback to local JSONL
  - Clean up old checkpoints
  - Non-blocking to avoid latency

**Output**: Boolean success status

### 5. STREAM_PROGRESS
Emit SSE events for real-time progress tracking.

**Input**: Event type, event data
**Process**:
  - Format event as JSON
  - Prefix with "data: " for SSE protocol
  - Add two newlines for event termination
  - Stream to client immediately
  - Include session ID and step tracking

**Output**: SSE event string

**Event Types**:
- start: Session initialized
- resume: Resumed from checkpoint
- step: Execution step completed
- checkpoint: Checkpoint created
- complete: Execution finished
- error: Error occurred
- cancelled: Cancelled by user
- timeout: Max duration exceeded

### 6. CLEANUP
Delete checkpoint on successful completion.

**Input**: Session ID
**Process**:
  - Remove checkpoint from vault
  - Remove local JSONL file
  - Close and unregister session
  - Release resources

**Output**: Cleanup status

## Success Criteria
- Sessions survive process restart (via checkpointing)
- Checkpoint overhead <5% of execution time
- Streaming latency <100ms per event
- Graceful cancellation in <1 second
- Resume from checkpoint in <100ms
- Support 2+ hour sessions without VRAM bloat
- Intermediate results persist after session end
- Non-blocking vault operations never break execution

## Implementation Details

### State Persistence
Session state includes:
- Current step and total steps
- Skill name and input context
- Intermediate results list
- Model usage statistics
- Cache state snapshot

### Streaming Protocol
SSE format with automatic reconnection:
```
data: {"type": "step", "step_index": 0, "output": "...", "tokens": 50}

data: {"type": "checkpoint", "step_index": 4, "session_id": "..."}

data: {"type": "complete", "final_output": "...", "total_tokens": 200}
```

### Checkpoint Triggers
- Time-based: Every N seconds (default 300s)
- Step-based: Every M steps (default 5 steps)
- Manual: Via /cancel endpoint

### Failure Handling
- Step errors logged but don't stop session
- Checkpoint failures logged but don't block execution
- Vault unavailable: Fallback to JSONL
- Session timeout: Gracefully stops streaming

## Version: 1.0.0
## Keywords: session, checkpoint, streaming, resumption, long-running
## Domain: inference-infrastructure
## Dependencies: SemanticCache, GuardrailPipeline (optional)
