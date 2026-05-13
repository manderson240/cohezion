"""CLI Bridge for the Cohezion Knowledge Graph and Retrospection Engine."""

from __future__ import annotations

import argparse
import json

from cohezion.core.compound.retrospection import RetrospectionEngine
from cohezion.knowledge_graph.query_engine import KnowledgeGraphQueryEngine


def main():
    parser = argparse.ArgumentParser(description="Cohezion KG CLI Bridge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Search Knowledge Graph
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query", type=str)
    search_parser.add_argument("--top-k", type=int, default=5)

    # Get Execution History
    history_parser = subparsers.add_parser("history")
    history_parser.add_argument("--limit", type=int, default=20)

    # Get Pattern Summary
    subparsers.add_parser("stats")

    # Run Retrospection
    retro_parser = subparsers.add_parser("retro")
    retro_parser.add_argument("--facts", type=str, help="JSON string of session facts")

    args = parser.parse_args()

    # Initialize engines
    kg_engine = KnowledgeGraphQueryEngine()
    retro_engine = RetrospectionEngine()

    if args.command == "search":
        import asyncio

        results = kg_engine.search_knowledge(args.query, top_k=args.top_k)
        print(json.dumps(results))

    elif args.command == "history":
        import asyncio

        results = asyncio.run(kg_engine.query_execution_history(limit=args.limit))
        print(json.dumps(results))

    elif args.command == "stats":
        import asyncio

        results = asyncio.run(kg_engine.get_pattern_summary())
        print(json.dumps(results))

    elif args.command == "retro":
        facts = json.loads(args.facts) if args.facts else {}
        report = retro_engine.generate_session_report(facts)
        print(report)


if __name__ == "__main__":
    main()
