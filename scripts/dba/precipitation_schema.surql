-- SurrealDB schema: Precipitation Events (Cosmogony Step 10)
-- Every witness mark, phase transition, consensus ratification, healing event,
-- mycelium pattern, training checkpoint, and generation spawn flows here.
--
-- Bi-temporal: `valid_from` captures universe-time; `transaction_time` captures
-- when the sink recorded the event. Both preserve the full audit trail needed
-- for recursive self-improvement.

DEFINE TABLE precipitation_event SCHEMAFULL;

DEFINE FIELD event_id          ON precipitation_event TYPE string;
DEFINE FIELD kind              ON precipitation_event TYPE string
    ASSERT $value IN [
        "witness_mark", "cosmogony_phase", "coherence_peak", "consensus_ratified",
        "healing_event", "mycelium_pattern", "training_checkpoint", "generation_spawn"
    ];
DEFINE FIELD agent_id          ON precipitation_event TYPE option<string>;
DEFINE FIELD universe_id       ON precipitation_event TYPE string;

-- Coherence — HIHO proximity
DEFINE FIELD coherence         ON precipitation_event TYPE float
    ASSERT $value >= 0.0 AND $value <= 1.0;
DEFINE FIELD hiho_delta        ON precipitation_event TYPE float;

-- 12D state
DEFINE FIELD twelve_d          ON precipitation_event TYPE object;
DEFINE FIELD twelve_d.x                ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.y                ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.z                ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.time             ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.physics          ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.biology          ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.logic            ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.quantum          ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.field            ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.control          ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.novelty          ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD twelve_d.precipitation    ON precipitation_event TYPE float DEFAULT 0.5;

-- 4 Fabrics (positional slices over 12D, per fiber_bundle.FABRIC_SLICES)
DEFINE FIELD fabric_breakdown  ON precipitation_event TYPE object;
DEFINE FIELD fabric_breakdown.Space          ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD fabric_breakdown.Field          ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD fabric_breakdown.Control        ON precipitation_event TYPE float DEFAULT 0.5;
DEFINE FIELD fabric_breakdown.Precipitation  ON precipitation_event TYPE float DEFAULT 0.5;

-- SU(2) spinor state (|psi> = alpha|up> + beta|down>)
DEFINE FIELD spinor_state      ON precipitation_event TYPE object;

-- Opaque artifact-specific payload
DEFINE FIELD payload           ON precipitation_event TYPE object;

-- Bi-temporal timestamps
DEFINE FIELD valid_from        ON precipitation_event TYPE datetime;
DEFINE FIELD valid_to          ON precipitation_event TYPE option<datetime>;
DEFINE FIELD transaction_time  ON precipitation_event TYPE datetime DEFAULT time::now();

-- Lineage: parent event_ids (for tracing recursion)
DEFINE FIELD lineage           ON precipitation_event TYPE array<string>;

-- Indexes for typical orchestrator queries
DEFINE INDEX idx_precip_kind        ON precipitation_event COLUMNS kind;
DEFINE INDEX idx_precip_universe    ON precipitation_event COLUMNS universe_id;
DEFINE INDEX idx_precip_agent       ON precipitation_event COLUMNS agent_id;
DEFINE INDEX idx_precip_valid_from  ON precipitation_event COLUMNS valid_from;
DEFINE INDEX idx_precip_coherence   ON precipitation_event COLUMNS coherence;
