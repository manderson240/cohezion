"""
Base Scout - Core logic for safe, throttled code analysis agents.
Enforces sequential LLM calls, resource guards, and mandatory cooldowns.
"""

import ast
import asyncio
import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cohezion.reliability import get_circuit
from cohezion.reliability.resource_guard import ResourceGuard


logger = logging.getLogger(__name__)

# Global lock to ensure strictly sequential LLM calls across all scouts
_LLM_LOCK = asyncio.Lock()


@dataclass
class Finding:
    type: str  # 'pattern' | 'anti_pattern'
    name: str
    category: str
    description: str
    file_path: str
    line_range: tuple[int, int]
    confidence: float
    code_snippet: str
    severity: str | None = None  # for anti-patterns
    remediation: str | None = None  # for anti-patterns
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ASTSummary:
    classes: list[str]
    functions: list[str]
    imports: list[str]
    complexity_score: int
    loc: int
    has_type_hints_ratio: float


class BaseScout(ABC):
    """
    Abstract base class for all code scouts.
    """

    def __init__(
        self,
        model: str,
        ollama_url: str = "http://localhost:13305",
        cooldown: float = 2.0,
    ) -> None:
        self.model = model
        self.ollama_url = ollama_url
        self.cooldown = cooldown
        self.guard = ResourceGuard()
        self.cache_path = Path("cache/scout_hashes.json")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_path.exists():
            try:
                self.cache = json.loads(self.cache_path.read_text())
            except Exception:
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self) -> None:
        self.cache_path.write_text(json.dumps(self.cache, indent=2))

    def _get_file_hash(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _parse_python_ast(self, path: Path) -> ASTSummary | None:
        """Structurally analyze file without LLM costs."""
        try:
            tree = ast.parse(path.read_text())
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend([n.name for n in node.names])
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")

            # Simple complexity: count branch nodes
            complexity = 1
            for node in ast.walk(tree):
                if isinstance(
                    node,
                    (
                        ast.If,
                        ast.While,
                        ast.For,
                        ast.AsyncFor,
                        ast.ExceptHandler,
                        ast.With,
                        ast.AsyncWith,
                    ),
                ):
                    complexity += 1

            lines = path.read_text().splitlines()
            return ASTSummary(
                classes=classes,
                functions=functions,
                imports=imports,
                complexity_score=complexity,
                loc=len(lines),
                has_type_hints_ratio=0.0,  # Placeholder
            )
        except SyntaxError:
            logger.warning(f"Syntax error in {path}, skipping AST analysis.")
            return None
        except Exception as e:
            logger.error(f"Failed to parse AST for {path}: {e}")
            return None

    async def _call_local_llm(self, prompt: str) -> str:
        """Call local LLM under global lock and resource guard."""
        async with _LLM_LOCK:
            logger.info(f"LLM Lock acquired. Running {self.model}...")
            # Wait for system stability before calling LLM
            await self.guard.wait_for_stability()

            breaker = get_circuit("ollama")
            if not breaker.allow_request():
                raise RuntimeError("Ollama circuit breaker is open")

            try:
                import httpx

                async with httpx.AsyncClient(timeout=180.0) as client:
                    response = await client.post(
                        f"{self.ollama_url}/v1/chat/completions",
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 2048,
                            "stream": False,
                        },
                    )
                    response.raise_for_status()
                    breaker.record_success()
                    logger.info("LLM call successful.")
                    data = response.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as e:
                breaker.record_failure()
                logger.error(f"LLM call failed: {e}")
                raise

    @abstractmethod
    async def analyze(self, path: Path) -> list[Finding]:
        """To be implemented by specialized scouts."""
        pass

    async def scan_file(self, path: Path) -> list[Finding]:
        """Scan a single file with cooldown and caching."""
        file_hash = self._get_file_hash(path)
        rel_path = str(path)
        cache_key = f"{self.__class__.__name__}:{rel_path}"

        # Cache check
        if cache_key in self.cache and self.cache[cache_key]["hash"] == file_hash:
            logger.debug(f"Skipping cached file: {cache_key}")
            return []

        logger.info(f"Scanning file: {rel_path} ({self.__class__.__name__})...")
        findings = await self.analyze(path)

        # Update cache
        self.cache[cache_key] = {
            "hash": file_hash,
            "last_scan": datetime.now().isoformat(),
            "findings_count": len(findings),
        }
        self._save_cache()

        # Mandatory cooldown to let system breathe
        logger.info(f"Cooldown active ({self.cooldown}s)...")
        await asyncio.sleep(self.cooldown)

        return findings
