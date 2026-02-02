# Relax to SCHEMALESS to allow arbitrary object nesting
REMOVE TABLE system_pulse;
DEFINE TABLE system_pulse SCHEMALESS;

# Re-define core fields for indexing
DEFINE FIELD timestamp ON system_pulse TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_pulse_time ON system_pulse COLUMNS timestamp;
