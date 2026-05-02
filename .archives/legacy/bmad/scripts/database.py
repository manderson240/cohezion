import json
import os

import psycopg2
from psycopg2 import sql


def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.
    """
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        database=os.environ.get("DB_NAME", "cohezion"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "password"),
    )
    return conn


def log_hallucination(
    agent_name: str,
    original_request: str,
    hallucinated_output: str,
    correction: str = None,
    notes: str = None,
    metadata: dict = None,
):
    """
    Logs a hallucination to the database.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Convert metadata dict to JSON string
    metadata_json = json.dumps(metadata) if metadata else None

    cur.execute(
        sql.SQL(
            "INSERT INTO hallucinations (agent_name, original_request,"
            " hallucinated_output, correction, notes, metadata)"
            " VALUES (%s, %s, %s, %s, %s, %s)"
        ),
        (
            agent_name,
            original_request,
            hallucinated_output,
            correction,
            notes,
            metadata_json,
        ),
    )

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    # Example usage
    log_hallucination(
        agent_name="test_agent",
        original_request="What is the capital of France?",
        hallucinated_output="Berlin",
        correction="Paris",
        notes="The agent seems to be confusing European capitals.",
        metadata={"model_version": "1.0", "confidence": 0.6},
    )
    print("Hallucination logged successfully.")
