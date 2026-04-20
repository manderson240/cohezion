#!/usr/bin/env python3
"""SurrealDB integration for experiment tracking and cross-session learning.

Usage:
    uv run python surreal_tracker.py --log-experiment --kernel gemm --result 12.5
    uv run python surreal_tracker.py --query-best --kernel gemm
    uv run python surreal_tracker.py --query-all-sessions
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("surreal_tracker")


async def get_surreal_client():
    """Get or create SurrealDB client."""
    try:
        from surrealdb import AsyncSurreal
    except ImportError:
        log.error("surrealdb not installed. Run: uv add surrealdb")
        return None

    db = AsyncSurreal("ws://localhost:8001/rpc")
    try:
        await db.connect()
        await db.signin({"username": "root", "password": "root"})
        await db.use("cohezion", "experiments")
        return db
    except Exception as e:
        log.warning(f"Could not connect to SurrealDB: {e}")
        return None


async def log_experiment(
    kernel: str,
    session_id: str,
    cycle: int,
    result_us: float,
    rank_at_time: Optional[int] = None,
    improvement_pct: float = 0.0,
    approach_used: str = "",
    per_shape_results: Optional[dict] = None,
    notes: str = "",
) -> Optional[str]:
    """Log an experiment result to SurrealDB."""
    db = await get_surreal_client()
    if not db:
        return None

    try:
        result = await db.create(
            "experiment",
            {
                "kernel": kernel,
                "session_id": session_id,
                "cycle": cycle,
                "submission_time": datetime.now().isoformat(),
                "result_us": result_us,
                "rank_at_time": rank_at_time,
                "improvement_pct": improvement_pct,
                "approach_used": approach_used,
                "per_shape_results": per_shape_results,
                "notes": notes,
            },
        )
        log.info(f"Logged experiment: {kernel} {result_us}µs (ID: {result['id']})")
        return str(result.get("id", ""))
    except Exception as e:
        log.error(f"Failed to log experiment: {e}")
        return None
    finally:
        await db.close()


async def log_session(
    name: str,
    focus_kernel: str,
    git_worktree: str = "",
    status: str = "active",
) -> Optional[str]:
    """Register a session in SurrealDB."""
    db = await get_surreal_client()
    if not db:
        return None

    try:
        result = await db.create(
            "session",
            {
                "name": name,
                "git_worktree": git_worktree,
                "focus_kernel": focus_kernel,
                "status": status,
                "last_submission": datetime.now().isoformat(),
            },
        )
        log.info(f"Registered session: {name} ({focus_kernel})")
        return str(result.get("id", ""))
    except Exception as e:
        log.error(f"Failed to register session: {e}")
        return None
    finally:
        await db.close()


async def query_best_by_kernel(kernel: str, limit: int = 10) -> list[dict]:
    """Query best experiments for a kernel."""
    db = await get_surreal_client()
    if not db:
        return []

    try:
        result = await db.query(
            f"SELECT * FROM experiment WHERE kernel = '{kernel}' ORDER BY result_us ASC LIMIT {limit}"
        )
        if result and isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict) and "result" in result[0]:
                rows = result[0]["result"]
                # Convert RecordID to string for JSON serialization
                return [_convert_record(r) for r in rows]
            return result
        return []
    except Exception as e:
        log.error(f"Query failed: {e}")
        return []
    finally:
        await db.close()


def _convert_record(obj):
    """Convert SurrealDB RecordID to string for JSON serialization."""
    if obj is None:
        return None
    if hasattr(obj, "__class__") and "RecordID" in str(obj.__class__.__name__):
        return str(obj)
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            result[k] = _convert_record(v)
        return result
    if isinstance(obj, list):
        return [_convert_record(item) for item in obj]
    return obj


async def query_all_sessions() -> list[dict]:
    """Query all sessions."""
    db = await get_surreal_client()
    if not db:
        return []

    try:
        result = await db.query("SELECT * FROM session ORDER BY best_result_us ASC")
        if result and isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict) and "result" in result[0]:
                rows = result[0]["result"]
                return [_convert_record(r) for r in rows]
            return result
        return []
    except Exception as e:
        log.error(f"Query failed: {e}")
        return []
    finally:
        await db.close()


async def query_cross_session_learning(kernel: str) -> dict[str, Any]:
    """Query for cross-session learning insights."""
    db = await get_surreal_client()
    if not db:
        return {}

    try:
        # Get best result per session
        result = await db.query(f"""
            SELECT session_id, approach_used, result_us, improvement_pct 
            FROM experiment 
            WHERE kernel = '{kernel}' 
            AND improvement_pct > 0
            ORDER BY improvement_pct DESC 
            LIMIT 20
        """)
        if result and isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict) and "result" in result[0]:
                return {"top_improvements": _convert_record(result[0]["result"])}
        return {}
    except Exception as e:
        log.error(f"Query failed: {e}")
        return {}
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser(description="SurrealDB experiment tracker")
    parser.add_argument("--log-experiment", action="store_true")
    parser.add_argument("--log-session", action="store_true")
    parser.add_argument("--query-best", action="store_true")
    parser.add_argument("--query-sessions", action="store_true")
    parser.add_argument("--query-learning", action="store_true")
    parser.add_argument("--kernel", choices=["gemm", "moe", "mla"])
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--cycle", type=int, default=0)
    parser.add_argument("--result", type=float, help="Result in µs")
    parser.add_argument("--improvement", type=float, default=0.0)
    parser.add_argument("--approach", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--session-name", default="")
    parser.add_argument("--git-worktree", default="")
    parser.add_argument("--status", default="active")
    args = parser.parse_args()

    if args.log_experiment:
        if not args.kernel or not args.result:
            log.error("--kernel and --result required for --log-experiment")
            sys.exit(1)
        import asyncio

        id = asyncio.run(
            log_experiment(
                kernel=args.kernel,
                session_id=args.session_id,
                cycle=args.cycle,
                result_us=args.result,
                improvement_pct=args.improvement,
                approach_used=args.approach,
                notes=args.notes,
            )
        )
        print(f"Logged: {id}")

    elif args.log_session:
        if not args.session_name or not args.kernel:
            log.error("--session-name and --kernel required for --log-session")
            sys.exit(1)
        import asyncio

        id = asyncio.run(
            log_session(
                name=args.session_name,
                focus_kernel=args.kernel,
                git_worktree=args.git_worktree,
                status=args.status,
            )
        )
        print(f"Registered: {id}")

    elif args.query_best:
        if not args.kernel:
            log.error("--kernel required for --query-best")
            sys.exit(1)
        import asyncio

        results = asyncio.run(query_best_by_kernel(args.kernel))
        print(json.dumps([_convert_record(r) for r in results], indent=2))

    elif args.query_sessions:
        import asyncio

        results = asyncio.run(query_all_sessions())
        print(json.dumps([_convert_record(r) for r in results], indent=2))

    elif args.query_learning:
        if not args.kernel:
            log.error("--kernel required for --query-learning")
            sys.exit(1)
        import asyncio

        results = asyncio.run(query_cross_session_learning(args.kernel))
        print(json.dumps(_convert_record(results), indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
