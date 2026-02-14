# Session 55 GitHub Cleanup - SurrealDB Query Templates

## Connection Setup

```bash
# Connect to SurrealDB (development)
surreal start --log debug --user root --pass root &
# Or production
surreal sql --endpoint ws://localhost:8000 --user root --pass root --namespace cohezion --database core
```

---

## Initialization Queries

### 1. Create Session Record

```surql
CREATE session_55_cleanup_journey SET
  session_id = "55-github-cleanup-entire-io",
  phase = "PHASE_B",
  status = "planned",
  title = "Session 55: GitHub Cleanup + Entire.io Integration",
  team_members = ["vault-specialist", "devops-lead", "architect", "qa-lead"],
  lead_specialist = "vault-specialist",
  approval_status = "pending",
  completion_percentage = 0.0,
  total_actions_planned = 0,
  total_actions_completed = 0,
  total_actions_failed = 0,
  total_tokens_used = 0,
  total_files_affected = 0,
  total_bytes_freed = 0,
  critical_errors = 0;
```

### 2. Initialize Entire.io Checkpoint (Phase B)

```surql
CREATE session_55_entire_io SET
  checkpoint_id = "entire-io-phase-b",
  phase = "PHASE_B",
  metadata_captured = false,
  journey_data_readable = false,
  journey_data_accessible = false,
  validation_passed = false,
  rollback_possible = true,
  rollback_procedure_documented = true,
  entire_io_status = "unknown";
```

---

## Action Logging Queries

### 3. Insert Action Record (Success)

```surql
CREATE session_55_actions SET
  action_id = "backup-001",
  action_type = "backup-created",
  phase = "PHASE_B",
  specialist = "devops-lead",
  result = "success",
  severity = "low",
  started_at = time::now(),
  completed_at = time::now(),
  duration_seconds = 45,
  description = "Created multi-platform backup of entire repository",
  target_path = "/tmp/cohezion-backup-session-55",
  details = {
    backup_format: "tar.gz",
    files_count: 12847,
    bytes_total: 2_147_483_648,
    platforms: ["linux", "macos", "windows"],
    checksum_algorithm: "sha256",
    verification_status: "complete"
  },
  tokens_used = 250,
  api_calls = 3,
  disk_io_bytes = 2_147_483_648,
  retry_count = 0;
```

### 4. Insert Action Record (With Error)

```surql
CREATE session_55_actions SET
  action_id = "cleanup-file-fail-001",
  action_type = "file-removed",
  phase = "PHASE_C",
  specialist = "devops-lead",
  result = "failure",
  severity = "high",
  started_at = time::now(),
  completed_at = time::now(),
  duration_seconds = 5,
  description = "Failed to remove large cache file (permission denied)",
  target_path = "/home/mike-anderson/dev/cohezion/cache/swarm/large_file.json",
  details = {
    reason: "Permission denied",
    bytes_target: 52_428_800,
    permission_mode: "0o644"
  },
  tokens_used = 50,
  error_message = "Permission denied: /cache/swarm/large_file.json",
  error_stack = "...",
  recovery_attempted = true,
  retry_count = 2;
```

### 5. Update Action Status

```surql
UPDATE session_55_actions
  SET result = "success",
      completed_at = time::now(),
      recovery_successful = true
WHERE action_id = "cleanup-file-fail-001";
```

### 6. Bulk Insert Multiple Actions

```surql
CREATE session_55_actions [
  {
    action_id: "cleanup-cache-001",
    action_type: "directory-compressed",
    phase: "PHASE_C",
    specialist: "devops-lead",
    result: "success",
    severity: "low",
    duration_seconds: 120,
    description: "Compressed cache directory",
    target_path: "/home/mike-anderson/dev/cohezion/cache",
    details: {
      compression_ratio: 0.15,
      original_size: 536_870_912,
      compressed_size: 80_530_636
    },
    tokens_used: 100,
    disk_io_bytes: 617_401_548
  },
  {
    action_id: "cleanup-logs-001",
    action_type: "file-removed",
    phase: "PHASE_C",
    specialist: "devops-lead",
    result: "success",
    severity: "low",
    duration_seconds: 30,
    description: "Removed build and test log files",
    target_path: "/home/mike-anderson/dev/cohezion/data/logs",
    details: {
      files_removed: 847,
      bytes_freed: 268_435_456
    },
    tokens_used: 80,
    disk_io_bytes: 268_435_456
  }
];
```

---

## Decision Logging Queries

### 7. Record Approval Decision

```surql
CREATE session_55_decisions SET
  decision_id = "cleanup-strategy-001",
  phase = "PHASE_B",
  decision_text = "Approve repository cleanup strategy: remove cache, logs, and build artifacts",
  category = "cleanup-strategy",
  options_considered = [
    "Conservative (cache only)",
    "Moderate (cache + logs)",
    "Aggressive (all non-essential files)"
  ],
  recommended_option = "Moderate (cache + logs)",
  rationale = "Balances space reclamation with minimal risk. Cache and logs are non-essential and can be regenerated.",
  risk_assessment = "Low risk: all changes backed up, rollback procedure tested",
  impact_estimate = {
    estimated_bytes_freed: 805_306_368,
    estimated_recovery_time_seconds: 600,
    risk_level: 1
  },
  approver = "architect",
  approval_status = "approved",
  approval_timestamp = time::now(),
  approval_reason = "Strategy is well-documented and aligns with project goals";
```

### 8. Record Rejection Decision

```surql
CREATE session_55_decisions SET
  decision_id = "aggressive-cleanup-002",
  phase = "PHASE_B",
  decision_text = "Reject aggressive cleanup of documentation and examples",
  category = "cleanup-strategy",
  options_considered = [
    "Keep all docs",
    "Archive old docs",
    "Remove all docs"
  ],
  recommended_option = "Keep all docs",
  rationale = "Documentation provides value and recovery cost is high if needed later",
  approver = "architect",
  approval_status = "rejected",
  approval_timestamp = time::now(),
  approval_reason = "Aggressive approach introduces unnecessary risk";
```

---

## Entire.io Integration Queries

### 9. Update Entire.io Checkpoint (Phase B)

```surql
UPDATE session_55_entire_io
  SET
    metadata_captured = true,
    metadata_checksum = "9c22ff5f21c0bb20646cac0410601ef35ca3da13e1c26f16a42c26a6d0e1e70",
    metadata_size_bytes = 4_096,
    metadata_file_path = "/home/mike-anderson/dev/cohezion/.entire/metadata_phase_b.json",
    journey_data_readable = true,
    journey_data_accessible = true,
    journey_data_format = "json",
    journey_record_count = 1847,
    entire_io_status = "online",
    entire_io_last_sync = time::now(),
    validation_passed = true,
    validation_errors = [],
    validation_warnings = [],
    rollback_possible = true,
    specialist_notes = "Metadata successfully captured. All 1847 journey records readable and validated.",
    specialist_name = "vault-specialist"
WHERE checkpoint_id = "entire-io-phase-b";
```

### 10. Create Phase C Entire.io Checkpoint

```surql
CREATE session_55_entire_io SET
  checkpoint_id = "entire-io-phase-c",
  phase = "PHASE_C",
  metadata_captured = true,
  metadata_checksum = "a9c97e6dcc837f8a33b4e10e5cbe16c5a6dce8a35f2c8f0b3c4e5f6a7b8c9d0e",
  journey_data_readable = true,
  journey_data_accessible = true,
  journey_record_count = 1847,
  validation_passed = true,
  entire_io_status = "online",
  rollback_possible = true,
  specialist_name = "vault-specialist";
```

---

## File Manifest Queries

### 11. Add Removed File to Manifest

```surql
CREATE session_55_file_manifest SET
  file_id = "file-cache-001",
  file_path = "/home/mike-anderson/dev/cohezion/cache/swarm/semantic/index.json",
  phase_removed = "PHASE_C",
  file_size_bytes = 524_288,
  file_type = "cache",
  file_hash_before = "sha256_original_hash_here",
  action_taken = "removed",
  bytes_freed = 524_288,
  backed_up_location = "/tmp/cohezion-backup-session-55/cache/swarm/semantic/index.json",
  removal_timestamp = time::now(),
  specialist_action = "devops-lead",
  recovery_possible = true,
  recovery_location = "/tmp/cohezion-backup-session-55";
```

### 12. Add Compressed File to Manifest

```surql
CREATE session_55_file_manifest SET
  file_id = "file-checkpoint-001",
  file_path = "/home/mike-anderson/dev/cohezion/data/flume/checkpoints",
  phase_removed = "PHASE_C",
  file_size_bytes = 1_073_741_824,
  file_type = "checkpoint",
  file_hash_before = "sha256_before_compression",
  file_hash_after = "sha256_after_compression",
  action_taken = "compressed",
  compressed_size_bytes = 268_435_456,
  bytes_freed = 805_306_368,
  backed_up_location = "/tmp/cohezion-backup-session-55/checkpoints.tar.gz",
  removal_timestamp = time::now(),
  specialist_action = "devops-lead",
  recovery_possible = true,
  recovery_location = "/tmp/cohezion-backup-session-55";
```

---

## Error Tracking Queries

### 13. Log Error with Recovery Attempt

```surql
CREATE session_55_errors SET
  error_id = "error-perm-001",
  timestamp = time::now(),
  severity = "high",
  error_type = "permission",
  error_message = "Permission denied writing to .git directory",
  error_context = {
    operation: "git add .",
    file_affected: ".git/objects/ab/cdef123456",
    current_user: "mike-anderson",
    expected_permission: "0o755"
  },
  phase = "PHASE_D",
  action_type = "push-prepared",
  specialist = "devops-lead",
  recovery_attempted = true,
  recovery_method = "chmod 755 recursively",
  recovery_successful = true,
  escalation_required = false;
```

### 14. Log Unresolved Error (Escalation)

```surql
CREATE session_55_errors SET
  error_id = "error-network-001",
  timestamp = time::now(),
  severity = "critical",
  error_type = "network",
  error_message = "GitHub API rate limit exceeded (60 requests per hour)",
  error_context = {
    operation: "push to GitHub",
    api_endpoint: "https://api.github.com/repos/...",
    retry_attempts: 3,
    next_reset: time::now() + 1h
  },
  phase = "PHASE_D",
  action_type = "push-executed",
  specialist = "devops-lead",
  recovery_attempted = true,
  recovery_method = "exponential backoff with jitter",
  recovery_successful = false,
  escalation_required = true;
```

---

## Update Session Progress Queries

### 15. Update Session Progress (During Execution)

```surql
UPDATE session_55_cleanup_journey
  SET
    phase = "PHASE_C",
    status = "in_progress",
    updated_at = time::now(),
    total_actions_completed = (SELECT count() FROM session_55_actions WHERE result = "success"),
    total_actions_failed = (SELECT count() FROM session_55_actions WHERE result = "failure"),
    completion_percentage = (
      SELECT (count(WHERE result = "success") / count()) * 100
      FROM session_55_actions
    ),
    total_tokens_used = (SELECT math::sum(tokens_used) FROM session_55_actions),
    total_files_affected = (SELECT count() FROM session_55_file_manifest),
    total_bytes_freed = (SELECT math::sum(bytes_freed) FROM session_55_file_manifest),
    critical_errors = (SELECT count() FROM session_55_errors WHERE severity = "critical")
WHERE session_id = "55-github-cleanup-entire-io";
```

### 16. Complete Session

```surql
UPDATE session_55_cleanup_journey
  SET
    phase = "PHASE_D",
    status = "complete",
    completed_at = time::now(),
    completion_percentage = 100.0,
    approval_status = "approved"
WHERE session_id = "55-github-cleanup-entire-io";
```

---

## Query Results

### 17. Get All Actions for Session

```surql
SELECT action_id, action_type, phase, result, duration_seconds, tokens_used
FROM session_55_actions
WHERE phase = "PHASE_C"
ORDER BY started_at DESC
LIMIT 100;
```

### 18. Get All Actions by Specialist

```surql
SELECT specialist, COUNT(action_id) as total_actions,
       COUNT(WHERE result = "success") as successful,
       COUNT(WHERE result = "failure") as failed,
       SUM(tokens_used) as total_tokens
FROM session_55_actions
GROUP BY specialist;
```

### 19. Get Failed Actions Requiring Attention

```surql
SELECT action_id, action_type, error_message, phase, specialist
FROM session_55_actions
WHERE result = "failure" OR result = "warning"
ORDER BY severity DESC, started_at DESC;
```

### 20. Get File Manifest Summary by Type

```surql
SELECT file_type, COUNT(file_id) as files_count,
       SUM(file_size_bytes) as total_original,
       SUM(compressed_size_bytes) as total_compressed,
       SUM(bytes_freed) as bytes_freed
FROM session_55_file_manifest
GROUP BY file_type;
```

### 21. Get Recovery Status

```surql
SELECT file_id, file_path, recovery_possible, recovery_location
FROM session_55_file_manifest
WHERE action_taken IN ["removed", "compressed"]
AND recovery_possible = true;
```

### 22. Get Session Timeline

```surql
SELECT
  phase,
  status,
  started_at,
  completed_at,
  completion_percentage,
  total_actions_completed,
  total_bytes_freed
FROM session_55_cleanup_journey
WHERE session_id = "55-github-cleanup-entire-io";
```

### 23. Get Active Errors (Unresolved)

```surql
SELECT error_id, severity, error_type, error_message, escalation_required
FROM session_55_errors
WHERE recovery_successful != true
ORDER BY severity DESC;
```

### 24. Get Decision Approvals

```surql
SELECT decision_id, decision_text, approver, approval_status, approval_reason
FROM session_55_decisions
WHERE approval_status IN ["approved", "pending", "rejected"]
ORDER BY created_at DESC;
```

### 25. Entire.io Status Check

```surql
SELECT checkpoint_id, phase, metadata_captured, journey_data_readable,
       validation_passed, entire_io_status
FROM session_55_entire_io
ORDER BY timestamp DESC;
```

---

## Cleanup Queries (Phase D Finalization)

### 26. Archive Session (Read-only)

```surql
-- Mark session as archived after push completes
UPDATE session_55_cleanup_journey
  SET status = "archived", updated_at = time::now()
WHERE session_id = "55-github-cleanup-entire-io";

-- Or keep as "complete" for ongoing reference
UPDATE session_55_cleanup_journey
  SET status = "complete", updated_at = time::now()
WHERE session_id = "55-github-cleanup-entire-io";
```

### 27. Generate Summary Report

```surql
SELECT
  (SELECT count() FROM session_55_actions WHERE result = "success") as actions_successful,
  (SELECT count() FROM session_55_actions WHERE result = "failure") as actions_failed,
  (SELECT count() FROM session_55_errors WHERE severity = "critical") as critical_errors,
  (SELECT sum(bytes_freed) FROM session_55_file_manifest) as total_bytes_freed,
  (SELECT sum(tokens_used) FROM session_55_actions) as total_tokens_used,
  (SELECT count() FROM session_55_decisions WHERE approval_status = "approved") as approvals_granted
;
```

### 28. Export Actions to JSON

```surql
SELECT *
FROM session_55_actions
WHERE phase IN ["PHASE_B", "PHASE_C", "PHASE_D"]
ORDER BY started_at DESC;
-- Export to: session_55_actions_export.json
```

---

## Notes

- All timestamps use `time::now()` (UTC)
- Tokens are tracked per action for cost analysis
- Recovery locations backed up in `/tmp/cohezion-backup-session-55`
- Entire.io integration verified at each phase boundary
- Errors escalated to team-lead if `escalation_required = true`

