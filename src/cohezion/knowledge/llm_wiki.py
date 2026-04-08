from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class WikiEntry:
    key: str
    value: Any
    source: str
    timestamp: str
    metadata: Dict[str, Any]

class LLMWiki:
    \"\"\"
    Structured knowledge base for LLM hardware benchmarks and capabilities.
    Grounds hardware claims in documented facts.
    \"\"\"
    def __init__(self, wiki_path: Path = Path("data/llm_wiki")):
        self.wiki_path = wiki_path
        self.entries: Dict[str, WikiEntry] = {}
        self._load()

    def _load(self):
        wiki_file = self.wiki_path / "wiki.json"
        if wiki_file.exists():
            try:
                with open(wiki_file, "r") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.entries[k] = WikiEntry(**v)
            except Exception as e:
                logger.error(f"Failed to load wiki from {wiki_file}: {e}")

    def query(self, key: str) -> Optional[WikiEntry]:
        \"\"\"
        Query the wiki for a specific benchmark or capability.
        \"\"\"
        return self.entries.get(key)

    def update(self, entry: WikiEntry):
        \"\"\"
        Updates the wiki with a new finding.
        \"\"\"
        self.entries[entry.key] = entry
        self._persist()

    def _persist(self):
        wiki_file = self.wiki_path / "wiki.json"
        try:
            with open(wiki_file, "w") as f:
                json.dump({k: v.__dict__ for k, v in self.entries.items()}, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to persist wiki to {wiki_file}: {e}")

    def get_all_entries(self) -> Dict[str, WikiEntry]:
        return self.entries
