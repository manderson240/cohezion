DEFINE TABLE system_pulse SCHEMAFULL;
DEFINE FIELD timestamp ON system_pulse TYPE datetime DEFAULT time::now() PERMISSIONS FULL;
DEFINE FIELD hardware ON system_pulse TYPE object PERMISSIONS FULL;
DEFINE FIELD software ON system_pulse TYPE object PERMISSIONS FULL;
DEFINE FIELD dilation_factor ON system_pulse TYPE float PERMISSIONS FULL;

-- Index for time-series queries
DEFINE INDEX idx_pulse_time ON system_pulse COLUMNS timestamp;
