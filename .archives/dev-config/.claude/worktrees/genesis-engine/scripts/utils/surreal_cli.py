#!/usr/bin/env python3
import asyncio
import pprint
import sys

from cohezion.core.persistence.surreal_client import SurrealClient


async def run_query(q_str):
    c = SurrealClient()
    try:
        await c.connect()
        res = await c.query(q_str)
        pprint.pprint(res)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await c.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: uv run surreal_cli.py "SELECT * FROM table"')
        sys.exit(1)

    query = sys.argv[1]
    asyncio.run(run_query(query))
