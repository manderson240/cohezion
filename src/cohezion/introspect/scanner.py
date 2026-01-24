import logging
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Any
import re

logger = logging.getLogger(__name__)

class InternalScanner:
    """
    Internal Signal Scanner (Gateway 30+).

    Scans the 'Akashic Records' (Codebase & Knowledge Graph) for:
    - Codebase Entropy (Churn, TODO density).
    - Context Coherence (Unresolved threads in KEY_LEARNINGS).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InternalScanner, cls).__new__(cls)
            cls._instance._minit()
        return cls._instance

    def _minit(self):
        self.repo_root = Path.cwd()

    def scan_codebase(self) -> Dict[str, Any]:
        """
        Analyze the physical code state.
        """
        signals = {
            "todo_count": 0,
            "high_churn_files": [],
            "file_count": 0
        }

        # 1. TODO Density Scan
        todo_pattern = re.compile(r"TODO|FIXME|HACK")

        for p in self.repo_root.rglob("*.py"):
            if "venv" in str(p) or ".git" in str(p):
                continue

            signals["file_count"] += 1
            try:
                content = p.read_text(errors="ignore")
                count = len(todo_pattern.findall(content))
                signals["todo_count"] += count
            except Exception:
                pass

        # 2. Git Churn (Simulated or Real)
        # We try to run git log --name-only to see top modified files
        try:
            cmd = ["git", "log", "--name-only", "--format=", "-n", "100"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                files = result.stdout.strip().split('\n')
                # Simple frequency count
                from collections import Counter
                ctr = Counter([f for f in files if f])
                signals["high_churn_files"] = ctr.most_common(3)
        except Exception as e:
            logger.warning(f"Git scan failed: {e}")

        return signals

    def scan_history(self) -> Dict[str, Any]:
        """
        Analyze the knowledge graph for recurring themes.
        """
        signals = {"recurring_themes": [], "unresolved_issues": 0}

        # Scan KEY_LEARNINGS.md
        kb_path = self.repo_root / "src/cohezion/knowledge_graph/KEY_LEARNINGS.md"
        if kb_path.exists():
            content = kb_path.read_text(errors="ignore")
            # Simple heuristic checks
            if "FAIL" in content:
                signals["unresolved_issues"] = content.count("FAIL")

            # Check for recurring keywords
            keywords = ["Email", "Quantum", "Stabilizer"]
            for k in keywords:
                if content.count(k) > 5:
                    signals["recurring_themes"].append(k)

        return signals

def get_internal_scanner() -> InternalScanner:
    return InternalScanner()
