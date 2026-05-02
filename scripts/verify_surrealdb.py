#!/usr/bin/env python3
"""Probe all candidate SurrealDB databases for the mass_sim_1777517314 run."""

import base64
import json
import os
import urllib.request


SURREAL_URL = os.environ.get("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = "cohezion"
SURREAL_USER = "root"
SURREAL_PASS = "root"

CANDIDATE_DBS = ["genesis", "universe", "vault", "logs"]


def query_surql(sql: str, db_name: str):
    req = urllib.request.Request(
        SURREAL_URL,
        data=sql.encode(),
        headers={
            "Accept": "application/json",
            "surreal-ns": SURREAL_NS,
            "surreal-db": db_name,
            "Content-Type": "application/json",
        },
    )
    credentials = base64.b64encode(f"{SURREAL_USER}:{SURREAL_PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {credentials}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def main():
    for db_name in CANDIDATE_DBS:
        print(f"\n==================== DB: {db_name} ====================\n")
        # 1. List tables
        info = query_surql("INFO FOR DB;", db_name)
        if isinstance(info, list) and len(info) > 0 and "result" in info[0]:
            tables = info[0]["result"].get("tables", {})
            print(f"Tables ({len(tables)}): {list(tables.keys())}\n")
            # 2. Count rows per table
            for tbl in tables:
                cnt = query_surql(f"SELECT count() FROM {tbl} GROUP ALL;", db_name)
                # Extract count if present
                count_val = "N/A"
                try:
                    count_val = cnt[0]["result"][0]["count"]
                except Exception:
                    count_val = str(cnt)[:120]
                print(f"  {tbl}: {count_val}")

            # 3. Check for run mass_sim_1777517314 across candidate tables
            candidate_tables = [
                "mass_sim_run",
                "sim_universe_summary",
                "sim_checkpoint",
                "trajectory",
                "vitals",
            ]
            print("\n--- Run lookup (mass_sim_1777517314) ---")
            for tbl in candidate_tables:
                if tbl in tables:
                    res = query_surql(
                        f"SELECT count() FROM {tbl} WHERE run_id = 'mass_sim_1777517314' GROUP ALL;",
                        db_name,
                    )
                    count_val = "N/A"
                    try:
                        count_val = res[0]["result"][0]["count"]
                    except Exception:
                        count_val = str(res)[:120]
                    print(f"  {tbl}: {count_val}")
                else:
                    print(f"  {tbl}: TABLE NOT FOUND")
        else:
            print(f"Could not retrieve DB info or error: {info}")


if __name__ == "__main__":
    main()
