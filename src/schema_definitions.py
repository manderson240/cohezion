"""Phase 4A SurrealDB Schema Definitions - Track A, B, C

Schema definitions deferred for runtime creation during implementation.
Each track creates its tables when needed during Steps 2-3.
"""

# Track A: GraphRAG Reasoning Engine
TRACK_A_SCHEMA = {
    "reasoning_chains": {
        "fields": [
            ("id", "string"),
            ("decision_id", "string"),
            ("model", "string"),
            ("reasoning_steps", "array"),
            ("confidence_score", "float"),
            ("citations", "array"),
            ("created_at", "datetime"),
            ("updated_at", "datetime"),
        ],
        "description": "Stores reasoning chains extracted by GraphRAG model",
    },
    "reasoning_citations": {
        "fields": [
            ("id", "string"),
            ("reasoning_id", "string"),
            ("source_paper_id", "string"),
            ("source_text", "string"),
            ("relevance_score", "float"),
            ("created_at", "datetime"),
        ],
        "description": "Citation tracking for reasoning chains",
    },
    "query_results": {
        "fields": [
            ("id", "string"),
            ("query_text", "string"),
            ("reasoning_chains", "array"),
            ("result_score", "float"),
            ("execution_time_ms", "int"),
            ("created_at", "datetime"),
        ],
        "description": "Cached query results for performance",
    },
}

# Track B: Confidence Scoring System
TRACK_B_SCHEMA = {
    "confidence_scores": {
        "fields": [
            ("id", "string"),
            ("decision_id", "string"),
            ("paper_id", "string"),
            ("score", "float"),
            ("calculation_timestamp", "datetime"),
            ("calculation_version", "string"),
            ("valid", "boolean"),
            ("created_at", "datetime"),
            ("updated_at", "datetime"),
        ],
        "description": "Stores confidence scores for decisions (0-100%)",
    },
    "score_factors": {
        "fields": [
            ("id", "string"),
            ("score_id", "string"),
            ("factor_name", "string"),
            ("factor_value", "float"),
            ("weight", "float"),
            ("contribution", "float"),
            ("created_at", "datetime"),
        ],
        "description": "Factor-level audit trail for scoring calculations",
    },
    "historical_scores": {
        "fields": [
            ("id", "string"),
            ("decision_id", "string"),
            ("paper_id", "string"),
            ("scores", "array"),
            ("mean_score", "float"),
            ("trend", "string"),
            ("created_at", "datetime"),
        ],
        "description": "Historical score evolution tracking",
    },
}

# Track C: Impact & Dependency Analyzer
TRACK_C_SCHEMA = {
    "decision_dependencies": {
        "fields": [
            ("id", "string"),
            ("source_decision_id", "string"),
            ("target_decision_id", "string"),
            ("dependency_type", "string"),
            ("strength", "float"),
            ("created_at", "datetime"),
        ],
        "description": "Decision dependency graph edges",
    },
    "impact_cascades": {
        "fields": [
            ("id", "string"),
            ("trigger_decision_id", "string"),
            ("affected_decisions", "array"),
            ("cascade_depth", "int"),
            ("total_impact_score", "float"),
            ("created_at", "datetime"),
            ("updated_at", "datetime"),
        ],
        "description": "Impact cascade analysis results",
    },
    "critical_path_analysis": {
        "fields": [
            ("id", "string"),
            ("start_decision_id", "string"),
            ("end_decision_id", "string"),
            ("path", "array"),
            ("path_length", "int"),
            ("critical_index", "float"),
            ("created_at", "datetime"),
        ],
        "description": "Critical path analysis (PERT-style)",
    },
}

# Combined schema for easy access
PHASE_4A_SCHEMA = {
    **{f"track_a_{k}": v for k, v in TRACK_A_SCHEMA.items()},
    **{f"track_b_{k}": v for k, v in TRACK_B_SCHEMA.items()},
    **{f"track_c_{k}": v for k, v in TRACK_C_SCHEMA.items()},
}


def create_table_sql(table_name: str, fields: list[tuple]) -> str:
    """Generate SurrealDB CREATE TABLE SQL for a given table definition.

    Args:
        table_name: Name of the table to create
        fields: List of (field_name, field_type) tuples

    Returns:
        SurrealDB SQL CREATE TABLE statement
    """
    field_defs = ", ".join(f"`{name}`: {type_}" for name, type_ in fields)
    return f"CREATE TABLE IF NOT EXISTS `{table_name}` {{ {field_defs} }}"


def get_create_statements(track: str = "all") -> list[str]:
    """Get CREATE TABLE statements for specified track(s).

    Args:
        track: "a", "b", "c", or "all"

    Returns:
        List of SurrealDB CREATE TABLE statements
    """
    statements = []

    if track in ("a", "all"):
        for table_name, table_def in TRACK_A_SCHEMA.items():
            statements.append(create_table_sql(table_name, table_def["fields"]))

    if track in ("b", "all"):
        for table_name, table_def in TRACK_B_SCHEMA.items():
            statements.append(create_table_sql(table_name, table_def["fields"]))

    if track in ("c", "all"):
        for table_name, table_def in TRACK_C_SCHEMA.items():
            statements.append(create_table_sql(table_name, table_def["fields"]))

    return statements
