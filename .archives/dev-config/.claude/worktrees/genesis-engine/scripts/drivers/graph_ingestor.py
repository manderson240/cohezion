"""
Graph Ingestor: Crystallizing Simulation Chaos into Knowledge.
Watches simulation directories and aggregates results into a persistent graph index.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import aiofiles


logger = logging.getLogger("graph_ingestor")


class GraphIngestor:
    def __init__(self):
        self.root_dir = Path("src/cohezion/knowledge_graph/universe_nodes")
        self.index_file = self.root_dir / "universes.jsonl"
        self.processed_files = set()

        # Directories to watch (Logs are in subfolders)
        self.watch_dirs = [
            self.root_dir / "plasma_theosophy" / "logs",
            self.root_dir / "societal_evolution" / "logs",
            self.root_dir / "linguistic_evolution" / "logs",
        ]

    async def run_forever(self):
        logger.info("Starting Graph Ingestor...")
        while True:
            await self._scan_and_ingest()
            await asyncio.sleep(10)  # Run every 10s

    async def _scan_and_ingest(self):
        new_nodes = []

        for d in self.watch_dirs:
            if not d.exists():
                continue

            # Simple glob for new log files.
            # In production, use os.scandir or watchdog for efficiency.
            for log_file in d.glob("*.txt"):
                if log_file.name in self.processed_files:
                    continue

                node = await self._parse_log(log_file)
                if node:
                    new_nodes.append(node)
                    self.processed_files.add(log_file.name)

        if new_nodes:
            await self._append_to_graph(new_nodes)
            logger.info(f"Ingested {len(new_nodes)} new universe nodes.")

    async def _parse_log(self, file_path: Path) -> dict[str, Any]:
        try:
            async with aiofiles.open(file_path) as f:
                content = await f.read()

            # Basic extraction based on file type
            node = {
                "id": file_path.stem,
                "timestamp": time.time(),
                "source": file_path.parent.name,
                "content": content,
                "coherence": 0.0,  # Default
            }

            # Parsing logic (Pragmatic/Regex-lite)
            if "Outcome: Collapsed" in content:
                node["status"] = "collapsed"
                node["vector"] = "chaos"
            elif "Outcome: Survived" in content:
                node["status"] = "survived"
                node["vector"] = "order"

            return node
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    async def _append_to_graph(self, nodes: list):
        async with aiofiles.open(self.index_file, mode="a") as f:
            for node in nodes:
                await f.write(json.dumps(node) + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingestor = GraphIngestor()
    asyncio.run(ingestor.run_forever())
