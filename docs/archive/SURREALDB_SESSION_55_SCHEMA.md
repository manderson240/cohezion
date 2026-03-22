# Session 55 GitHub Cleanup Journey - SurrealDB Schema

## Overview

This schema captures the complete Session 55 GitHub cleanup journey throughout Phases B-D:
- **Phase B**: Preparation (validate, backup, plan)
- **Phase C**: Execution (cleanup, compress, verify)
- **Phase D**: Finalization (push, monitor, conclude)

All operations are recorded with timestamps, actor information, and status tracking for full reproducibility and audit trail.

---

## Table 1: Session Metadata

```surql
-- Session-level information
DEFINE TABLE session_55_cleanup_journey SCHEMALESS;

-- Core session info
DEFINE FIELD session_id ON TABLE session_55_cleanup_journey TYPE string ASSERT $value == "55-github-cleanup-entire-io";
DEFINE FIELD phase ON TABLE session_55_cleanup_journey TYPE string;  -- "PHASE_B", "PHASE_C", "PHASE_D"
DEFINE FIELD status ON TABLE session_55_cleanup_journey TYPE string;  -- "planned", "in_progress", "paused", "complete", "failed"
DEFINE FIELD title ON TABLE session_55_cleanup_journey TYPE string;

-- Timeline
DEFINE FIELD started_at ON TABLE session_55_cleanup_journey TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE session_55_cleanup_journey TYPE datetime DEFAULT time::now();
DEFINE FIELD completed_at ON TABLE session_55_cleanup_journey FLEXIBLE TYPE option<datetime>;

-- Progress tracking
DEFINE FIELD completion_percentage ON TABLE session_55_cleanup_journey TYPE float;  -- 0.0 to 100.0
DEFINE FIELD total_actions_planned ON TABLE session_55_cleanup_journey TYPE int;
DEFINE FIELD total_actions_completed ON TABLE session_55_cleanup_journey TYPE int;
DEFINE FIELD total_actions_failed ON TABLE session_55_cleanup_journeyTYPE int;

-- Team info
DEFINE FIELD team_members ON TABLE session_55_cleanup_journey TYPE array<string>;
DEFINE FIELD lead_specialist ON TABLE session_55_cleanup_journey TYPE string;
DEFINE FIELD approval_status ON TABLE session_55_cleanup_journey TYPE string;  -- "pending", "approved", "rejected"

-- Metrics
DEFINE FIELD total_tokens_used ON TABLE session_55_cleanup_journey TYPE int;
DEFINE FIELD total_files_affected ON TABLE session_55_cleanup_journey TYPE int;
DEFINE FIELD total_bytes_freed ON TABLE session_55_cleanup_journey TYPE int;
DEFINE FIELD critical_errors ON TABLE session_55_cleanup_journey TYPE int DEFAULT 0;

-- Indexes
DEFINE INDEX idx_session_id ON TABLE session_55_cleanup_journey COLUMNS session_id UNIQUE;
DEFINE INDEX idx_phase ON TABLE session_55_cleanup_journey COLUMNS phase;
DEFINE INDEX idx_status ON TABLE session_55_cleanup_journey COLUMNS status;
DEFINE INDEX idx_started_at ON TABLE session_55_cleanup_journey COLUMNS started_at;
```

---

## Table 2: Action Log

```surql
-- Record every action taken during cleanup
DEFINE TABLE session_55_actions SCHEMALESS;

-- Action identification
DEFINE FIELD action_id ON TABLE session_55_actions TYPE string;  -- e.g., "backup-001", "cleanup-file-001"
DEFINE FIELD action_type ON TABLE session_55_actions TYPE string;
-- Types: "backup-created", "backup-verified", "cleanup-started", "file-removed",
-- "directory-compressed", "cleanup-verified", "push-prepared", "push-executed",
-- "decision-approved", "checkpoint-created", "error-logged", "recovery-attempted"

DEFINE FIELD phase ON TABLE session_55_actions TYPE string;  -- "PHASE_B", "PHASE_C", "PHASE_D"
DEFINE FIELD specialist ON TABLE session_55_actions TYPE string;  -- who executed it
DEFINE FIELD result ON TABLE session_55_actions TYPE string;  -- "success", "failure", "warning", "pending"
DEFINE FIELD severity ON TABLE session_55_actions TYPE string;  -- "critical", "high", "medium", "low", "info"

-- Timeline
DEFINE FIELD started_at ON TABLE session_55_actions TYPE datetime DEFAULT time::now();
DEFINE FIELD completed_at ON TABLE session_55_actions FLEXIBLE TYPE option<datetime>;
DEFINE FIELD duration_seconds ON TABLE session_55_actions FLEXIBLE TYPE option<int>;

-- Details
DEFINE FIELD description ON TABLE session_55_actions TYPE string;
DEFINE FIELD target_path ON TABLE session_55_actions FLEXIBLE TYPE option<string>;  -- file/dir affected
DEFINE FIELD details ON TABLE session_55_actions FLEXIBLE TYPE object;  -- flexible metadata
  -- Examples: {files_count: 150, bytes_freed: 1_000_000, error_msg: "..."}

-- Resource tracking
DEFINE FIELD tokens_used ON TABLE session_55_actions TYPE int;
DEFINE FIELD api_calls ON TABLE session_55_actions FLEXIBLE TYPE option<int>;
DEFINE FIELD disk_io_bytes ON TABLE session_55_actions FLEXIBLE TYPE option<int>;

-- Traceability
DEFINE FIELD error_message ON TABLE session_55_actions FLEXIBLE TYPE option<string>;
DEFINE FIELD error_stack ON TABLE session_55_actions FLEXIBLE TYPE option<string>;
DEFINE FIELD recovery_attempted ON TABLE session_55_actions FLEXIBLE TYPE option<bool>;
DEFINE FIELD retry_count ON TABLE session_55_actions TYPE int DEFAULT 0;

-- Indexes
DEFINE INDEX idx_action_type ON TABLE session_55_actions COLUMNS action_type;
DEFINE INDEX idx_phase ON TABLE session_55_actions COLUMNS phase;
DEFINE INDEX idx_specialist ON TABLE session_55_actions COLUMNS specialist;
DEFINE INDEX idx_result ON TABLE session_55_actions COLUMNS result;
DEFINE INDEX idx_started_at ON TABLE session_55_actions COLUMNS started_at;
DEFINE INDEX idx_severity ON TABLE session_55_actions COLUMNS severity;
```

---

## Table 3: Decision Points

```surql
-- Record all significant decisions with rationale
DEFINE TABLE session_55_decisions SCHEMALESS;

-- Decision info
DEFINE FIELD decision_id ON TABLE session_55_decisions TYPE string;
DEFINE FIELD phase ON TABLE session_55_decisions TYPE string;
DEFINE FIELD decision_text ON TABLE session_55_decisions TYPE string;  -- what was decided
DEFINE FIELD category ON TABLE session_55_decisions TYPE string;  -- "cleanup-strategy", "rollback", "approval", "prioritization"

-- Alternatives evaluated
DEFINE FIELD options_considered ON TABLE session_55_decisions TYPE array<string>;
DEFINE FIELD recommended_option ON TABLE session_55_decisions FLEXIBLE TYPE option<string>;

-- Rationale
DEFINE FIELD rationale ON TABLE session_55_decisions TYPE string;
DEFINE FIELD risk_assessment ON TABLE session_55_decisions FLEXIBLE TYPE option<string>;
DEFINE FIELD impact_estimate ON TABLE session_55_decisions FLEXIBLE TYPE option<object>;

-- Authority
DEFINE FIELD approver ON TABLE session_55_decisions TYPE string;
DEFINE FIELD approval_status ON TABLE session_55_decisions TYPE string;  -- "pending", "approved", "rejected", "superseded"
DEFINE FIELD approval_timestamp ON TABLE session_55_decisions FLEXIBLE TYPE option<datetime>;
DEFINE FIELD approval_reason ON TABLE session_55_decisions FLEXIBLE TYPE option<string>;

-- Timeline
DEFINE FIELD created_at ON TABLE session_55_decisions TYPE datetime DEFAULT time::now();
DEFINE FIELD finalized_at ON TABLE session_55_decisions FLEXIBLE TYPE option<datetime>;

-- Indexes
DEFINE INDEX idx_category ON TABLE session_55_decisions COLUMNS category;
DEFINE INDEX idx_approval_status ON TABLE session_55_decisions COLUMNS approval_status;
DEFINE INDEX idx_phase ON TABLE session_55_decisions COLUMNS phase;
```

---

## Table 4: Entire.io Integration Checkpoint

```surql
-- Track Entire.io integration validation and state
DEFINE TABLE session_55_entire_io SCHEMALESS;

-- Checkpoint identification
DEFINE FIELD checkpoint_id ON TABLE session_55_entire_io TYPE string;  -- "entire-io-phase-b", "entire-io-phase-c", "entire-io-phase-d"
DEFINE FIELD phase ON TABLE session_55_entire_io TYPE string;
DEFINE FIELD timestamp ON TABLE session_55_entire_io TYPE datetime DEFAULT time::now();

-- Metadata capture
DEFINE FIELD metadata_captured ON TABLE session_55_entire_io TYPE bool;
DEFINE FIELD metadata_checksum ON TABLE session_55_entire_io FLEXIBLE TYPE option<string>;  -- SHA256 of captured metadata
DEFINE FIELD metadata_size_bytes ON TABLE session_55_entire_io FLEXIBLE TYPE option<int>;
DEFINE FIELD metadata_file_path ON TABLE session_55_entire_io FLEXIBLE TYPE option<string>;

-- Journey data readability
DEFINE FIELD journey_data_readable ON TABLE session_55_entire_io TYPE bool;
DEFINE FIELD journey_data_accessible ON TABLE session_55_entire_io TYPE bool;
DEFINE FIELD journey_data_format ON TABLE session_55_entire_io FLEXIBLE TYPE option<string>;  -- "json", "jsonl", "parquet", etc.
DEFINE FIELD journey_record_count ON TABLE session_55_entire_io FLEXIBLE TYPE option<int>;

-- Entire.io system state
DEFINE FIELD entire_io_status ON TABLE session_55_entire_io TYPE string;  -- "online", "offline", "degraded", "unknown"
DEFINE FIELD entire_io_last_sync ON TABLE session_55_entire_io FLEXIBLE TYPE option<datetime>;
DEFINE FIELD entire_io_error_message ON TABLE session_55_entire_io FLEXIBLE TYPE option<string>;

-- Validation results
DEFINE FIELD validation_passed ON TABLE session_55_entire_io TYPE bool;
DEFINE FIELD validation_errors ON TABLE session_55_entire_io FLEXIBLE TYPE option<array<string>>;
DEFINE FIELD validation_warnings ON TABLE session_55_entire_io FLEXIBLE TYPE option<array<string>>;

-- Recovery/Rollback capability
DEFINE FIELD rollback_possible ON TABLE session_55_entire_io TYPE bool;
DEFINE FIELD rollback_procedure_documented ON TABLE session_55_entire_io TYPE bool;
DEFINE FIELD rollback_estimated_duration_seconds ON TABLE session_55_entire_io FLEXIBLE TYPE option<int>;

-- Specialist notes
DEFINE FIELD specialist_notes ON TABLE session_55_entire_io FLEXIBLE TYPE option<string>;
DEFINE FIELD specialist_name ON TABLE session_55_entire_io FLEXIBLE TYPE option<string>;

-- Indexes
DEFINE INDEX idx_checkpoint_id ON TABLE session_55_entire_io COLUMNS checkpoint_id UNIQUE;
DEFINE INDEX idx_phase ON TABLE session_55_entire_io COLUMNS phase;
DEFINE INDEX idx_timestamp ON TABLE session_55_entire_io COLUMNS timestamp;
DEFINE INDEX idx_validation_passed ON TABLE session_55_entire_io COLUMNS validation_passed;
```

---

## Table 5: File Manifest (Phase C & D)

```surql
-- Track files removed/compressed during cleanup
DEFINE TABLE session_55_file_manifest SCHEMALESS;

-- File identification
DEFINE FIELD file_id ON TABLE session_55_file_manifest TYPE string;
DEFINE FIELD file_path ON TABLE session_55_file_manifest TYPE string;
DEFINE FIELD phase_removed ON TABLE session_55_file_manifest TYPE string;  -- "PHASE_C_PRE", "PHASE_C_EXEC", etc.

-- File properties
DEFINE FIELD file_size_bytes ON TABLE session_55_file_manifest TYPE int;
DEFINE FIELD file_type ON TABLE session_55_file_manifest TYPE string;  -- "cache", "checkpoint", "log", "backup", "docs", "build", "other"
DEFINE FIELD file_hash_before ON TABLE session_55_file_manifest TYPE string;  -- SHA256 before removal
DEFINE FIELD file_hash_after ON TABLE session_55_file_manifest FLEXIBLE TYPE option<string>;  -- SHA256 if compressed

-- Action taken
DEFINE FIELD action_taken ON TABLE session_55_file_manifest TYPE string;  -- "removed", "compressed", "archived", "backed_up"
DEFINE FIELD compressed_size_bytes ON TABLE session_55_file_manifest FLEXIBLE TYPE option<int>;
DEFINE FIELD bytes_freed ON TABLE session_55_file_manifest TYPE int;

-- Traceability
DEFINE FIELD backed_up_location ON TABLE session_55_file_manifest FLEXIBLE TYPE option<string>;
DEFINE FIELD removal_timestamp ON TABLE session_55_file_manifest TYPE datetime DEFAULT time::now();
DEFINE FIELD specialist_action ON TABLE session_55_file_manifest TYPE string;

-- Recovery info
DEFINE FIELD recovery_possible ON TABLE session_55_file_manifest TYPE bool;
DEFINE FIELD recovery_location ON TABLE session_55_file_manifest FLEXIBLE TYPE option<string>;

-- Indexes
DEFINE INDEX idx_file_path ON TABLE session_55_file_manifest COLUMNS file_path;
DEFINE INDEX idx_file_type ON TABLE session_55_file_manifest COLUMNS file_type;
DEFINE INDEX idx_phase_removed ON TABLE session_55_file_manifest COLUMNS phase_removed;
```

---

## Table 6: Error Log & Recovery

```surql
-- Track errors and recovery attempts
DEFINE TABLE session_55_errors SCHEMALESS;

-- Error identification
DEFINE FIELD error_id ON TABLE session_55_errors TYPE string;
DEFINE FIELD timestamp ON TABLE session_55_errors TYPE datetime DEFAULT time::now();
DEFINE FIELD severity ON TABLE session_55_errors TYPE string;  -- "critical", "high", "medium", "low"

-- Error details
DEFINE FIELD error_type ON TABLE session_55_errors TYPE string;  -- "filesystem", "permission", "network", "validation", "unexpected"
DEFINE FIELD error_message ON TABLE session_55_errors TYPE string;
DEFINE FIELD error_context ON TABLE session_55_errors FLEXIBLE TYPE object;  -- operation being attempted, file involved, etc.

-- Location in workflow
DEFINE FIELD phase ON TABLE session_55_errors TYPE string;
DEFINE FIELD action_type ON TABLE session_55_errors TYPE string;  -- what was happening when error occurred
DEFINE FIELD specialist ON TABLE session_55_errors TYPE string;

-- Recovery
DEFINE FIELD recovery_attempted ON TABLE session_55_errors TYPE bool;
DEFINE FIELD recovery_method ON TABLE session_55_errors FLEXIBLE TYPE option<string>;  -- "retry", "fallback", "skip", "manual_intervention"
DEFINE FIELD recovery_successful ON TABLE session_55_errors FLEXIBLE TYPE option<bool>;
DEFINE FIELD escalation_required ON TABLE session_55_errors TYPE bool;

-- Indexes
DEFINE INDEX idx_severity ON TABLE session_55_errors COLUMNS severity;
DEFINE INDEX idx_phase ON TABLE session_55_errors COLUMNS phase;
DEFINE INDEX idx_escalation_required ON TABLE session_55_errors COLUMNS escalation_required;
```

---

## Graph Relationships

```surql
-- Link actions to decisions
DEFINE TABLE action_justifies_decision SCHEMALESS;
DEFINE FIELD action_id ON TABLE action_justifies_decision TYPE record<session_55_actions>;
DEFINE FIELD decision_id ON TABLE action_justifies_decision TYPE record<session_55_decisions>;
DEFINE FIELD relationship_type ON TABLE action_justifies_decision TYPE string;
DEFINE INDEX idx_action ON TABLE action_justifies_decision COLUMNS action_id;
DEFINE INDEX idx_decision ON TABLE action_justifies_decision COLUMNS decision_id;

-- Link errors to recovery actions
DEFINE TABLE error_resolved_by_action SCHEMALESS;
DEFINE FIELD error_id ON TABLE error_resolved_by_action TYPE record<session_55_errors>;
DEFINE FIELD action_id ON TABLE error_resolved_by_action TYPE record<session_55_actions>;
DEFINE FIELD resolution_status ON TABLE error_resolved_by_action TYPE string;
DEFINE INDEX idx_error ON TABLE error_resolved_by_action COLUMNS error_id;

-- Link files to cleanup actions
DEFINE TABLE file_removed_by_action SCHEMALESS;
DEFINE FIELD file_id ON TABLE file_removed_by_action TYPE record<session_55_file_manifest>;
DEFINE FIELD action_id ON TABLE file_removed_by_action TYPE record<session_55_actions>;
DEFINE INDEX idx_file ON TABLE file_removed_by_action COLUMNS file_id;
```

---

## Schema Constraints & Defaults

```surql
-- Ensure sessions reference valid phases
DEFINE FUNCTION validate_phase($phase: string) {
  RETURN $phase in ["PHASE_B", "PHASE_C", "PHASE_D"];
};

-- Ensure status values are valid
DEFINE FUNCTION validate_status($status: string) {
  RETURN $status in ["planned", "in_progress", "paused", "complete", "failed", "rolled_back"];
};

-- Calculate progress percentage
DEFINE FUNCTION calculate_progress($completed: int, $planned: int) {
  RETURN IF $planned > 0 THEN ($completed / $planned) * 100 ELSE 0;
};

-- Time tracking
DEFINE FUNCTION calculate_duration($start: datetime, $end: datetime) {
  RETURN math::ceil(($end - $start) / 1000);  -- seconds
};
```

---

## Summary

| Table | Purpose | Records | Key Fields |
|-------|---------|---------|-----------|
| `session_55_cleanup_journey` | Session metadata & progress | 1 | phase, status, completion_percentage |
| `session_55_actions` | All operations executed | 100-500 | action_type, result, duration_seconds, tokens_used |
| `session_55_decisions` | Major decisions with rationale | 10-20 | decision_text, options_considered, approval_status |
| `session_55_entire_io` | Entire.io integration checkpoints | 3-5 | metadata_captured, journey_data_readable, validation_passed |
| `session_55_file_manifest` | Removed/compressed files | 500-2000 | file_path, action_taken, bytes_freed |
| `session_55_errors` | Errors and recovery attempts | 0-50 | error_type, severity, recovery_attempted |
| Graph tables | Relationships between records | - | Links actions→decisions, errors→recovery, files→actions |

---

## Next Steps

1. **Phase C**: Queries (create, update, query operations)
2. **Phase D**: Testing and validation procedures
3. **Post-Cleanup**: Analysis and reporting queries

