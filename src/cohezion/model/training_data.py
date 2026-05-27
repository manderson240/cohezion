"""Training data collection for Cohezion HIHO-LM.

Sources:
  1. autoresearch.jsonl — 80,000+ compound loop iterations (task, guidance, output, quality)
  2. autodqa_results — SurrealDB quality evaluations (filtered: score >= 0.45)
  3. stealthskater corpus — physics concept descriptions for embedding alignment
  4. vault memory observations — high-value session discoveries

HIHO quality filter: only include examples with quality_score >= 0.45
(HIHO entry threshold). This prevents the model from learning sycophantic
or low-quality patterns. The model trains on the HIHO attractor's basin.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)

_HIHO_THRESHOLD: float = 0.45  # minimum quality score for training inclusion
_DEFAULT_AUTORESEARCH_PATH = Path("autoresearch.jsonl")
_VAULT_PATH = Path.home() / "vaults" / "cohezion-vault" / "memory" / "observations.jsonl"


@dataclass
class TrainingExample:
    """A single (instruction, response) training pair.

    Parameters
    ----------
    instruction : str
        Task description or prompt.
    response : str
        Desired output (guidance or synthesis text).
    quality_score : float
        HIHO quality gate score [0, 1]. Only ≥ 0.45 used for training.
    source : str
        Data source label.
    """

    instruction: str
    response: str
    quality_score: float = 0.5
    source: str = "unknown"

    @property
    def hiho_weight(self) -> float:
        """HIHO training weight: γ(q) = 4q(1-q). Max at q=0.5."""
        q = self.quality_score
        return 4.0 * q * (1.0 - q)

    @property
    def is_valid(self) -> bool:
        """True when quality meets HIHO threshold."""
        return (
            self.quality_score >= _HIHO_THRESHOLD
            and len(self.instruction.strip()) >= 10
            and len(self.response.strip()) >= 20
        )

    def to_dict(self) -> dict:
        return {
            "instruction": self.instruction,
            "response": self.response,
            "quality_score": self.quality_score,
            "hiho_weight": self.hiho_weight,
            "source": self.source,
        }


@dataclass
class TrainingDataset:
    """Collection of HIHO-filtered training examples.

    Parameters
    ----------
    examples : list[TrainingExample]
    """

    examples: list[TrainingExample] = field(default_factory=list)

    def add(self, example: TrainingExample) -> None:
        """Add example if it passes HIHO quality gate."""
        if example.is_valid:
            self.examples.append(example)

    def __len__(self) -> int:
        return len(self.examples)

    @property
    def mean_quality(self) -> float:
        if not self.examples:
            return 0.0
        return sum(e.quality_score for e in self.examples) / len(self.examples)

    @property
    def hiho_engaged(self) -> bool:
        """True when mean quality is in the HIHO band."""
        return 0.45 <= self.mean_quality <= 0.55

    def stats(self) -> dict:
        return {
            "total": len(self.examples),
            "mean_quality": self.mean_quality,
            "hiho_engaged": self.hiho_engaged,
            "sources": {
                src: sum(1 for e in self.examples if e.source == src)
                for src in {e.source for e in self.examples}
            },
        }

    def iter_batches(self, batch_size: int = 32) -> Iterator[list[TrainingExample]]:
        """Yield batches of training examples."""
        for i in range(0, len(self.examples), batch_size):
            yield self.examples[i : i + batch_size]


def load_autoresearch_data(
    path: Path = _DEFAULT_AUTORESEARCH_PATH,
    max_examples: int = 10_000,
) -> TrainingDataset:
    """Load training data from autoresearch.jsonl.

    Filters for winner=True entries with quality_score >= 0.45.
    """
    dataset = TrainingDataset()
    if not path.exists():
        logger.warning("autoresearch.jsonl not found at %s", path)
        return dataset

    count = 0
    with open(path) as f:
        for line in f:
            if count >= max_examples:
                break
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            # Winner entries have quality-validated outputs
            if not entry.get("winner", False):
                continue

            # Support compound loop, autoresearch, and direct instruction/response formats
            instruction = (
                entry.get("task_description")
                or entry.get("prompt")
                or entry.get("hypothesis")
                or entry.get("instruction")
                or ""
            )
            _response = (
                entry.get("output")
                or entry.get("notes")  # notes is always a string in our experiments
                or entry.get("response")
                or entry.get("finding")
                or ""
            )
            # Ensure response is a string (result field may be a dict)
            response = _response if isinstance(_response, str) else ""
            quality = float(entry.get("quality_score", entry.get("score", 0.5)))

            example = TrainingExample(
                instruction=instruction,
                response=response,
                quality_score=quality,
                source="autoresearch",
            )
            dataset.add(example)
            count += 1

    logger.info("Loaded %d autoresearch examples from %s", len(dataset), path)
    return dataset


def load_stealthskater_corpus(
    corpus_path: Path | None = None,
) -> TrainingDataset:
    """Load stealthskater physics concepts as training examples.

    Each concept becomes an (instruction="Explain X", response=description) pair.
    All stealthskater corpus examples are treated as high-quality (q=0.75).
    """
    dataset = TrainingDataset()

    if corpus_path is None:
        corpus_path = Path("src/cohezion/skills/STEALTHSKATER_CORPUS.md")

    if not corpus_path.exists():
        logger.info("Stealthskater corpus not found at %s — skipping", corpus_path)
        return dataset

    import re as _re

    text = corpus_path.read_text()
    sections = []

    # Primary: parse ## or ### section headers
    current_title = ""
    current_body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            if current_title and current_body:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = line.lstrip("#").strip()
            current_body = []
        elif current_title:
            current_body.append(line)
    if current_title and current_body:
        sections.append((current_title, "\n".join(current_body).strip()))

    # Secondary: extract - **Title**: description bullet points (stealthskater corpus format)
    _bullet_pat = _re.compile(r"^-\s+\*\*([^*]+)\*\*:\s+(.+)$")
    for line in text.splitlines():
        m = _bullet_pat.match(line.strip())
        if m:
            title_raw, body_raw = m.group(1).strip(), m.group(2).strip()
            # Skip duplicate short descriptions that duplicate a section title
            if len(body_raw) >= 80:
                sections.append((title_raw, body_raw))

    for title, body in sections:
        if len(body) >= 50:
            dataset.add(
                TrainingExample(
                    instruction=f"Explain the concept of {title} in the context of Cohezion physics.",
                    response=body[:2000],  # cap to avoid bloating
                    quality_score=0.75,  # high quality, expert content
                    source="stealthskater_corpus",
                )
            )

    logger.info("Loaded %d stealthskater corpus examples", len(dataset))
    return dataset


def build_training_dataset(
    autoresearch_path: Path = _DEFAULT_AUTORESEARCH_PATH,
    include_stealthskater: bool = True,
    max_autoresearch: int = 10_000,
) -> TrainingDataset:
    """Merge all data sources into a single HIHO-filtered dataset."""
    combined = TrainingDataset()

    # Source 1: autoresearch loop (main data source)
    ar_data = load_autoresearch_data(autoresearch_path, max_autoresearch)
    combined.examples.extend(ar_data.examples)

    # Source 2: stealthskater corpus (physics grounding)
    if include_stealthskater:
        ss_data = load_stealthskater_corpus()
        combined.examples.extend(ss_data.examples)

    logger.info(
        "Built training dataset: %d examples | mean_quality=%.3f | HIHO=%s",
        len(combined),
        combined.mean_quality,
        combined.hiho_engaged,
    )
    return combined


# HIHO-band synthetic examples for training diversity (exp_PPPP1 finding)
# These examples have quality=0.5 (w=1.0) to maximize HIHO learning gradient
_HIHO_BAND_EXAMPLES = [
    TrainingExample(
        instruction="Explain why HIHO equilibrium is important for compound loop quality.",
        response=(
            "HIHO equilibrium matters because the 4c(1-c) kernel peaks at c=0.5, "
            "where the compound loop maximizes entropy while maintaining structured contact "
            "between exploration (trying new approaches) and exploitation (using proven ones)."
        ),
        quality_score=0.5,
        source="hiho_band_synthetic",
    ),
    TrainingExample(
        instruction="What is the connection between LENR and the compound loop quality gate?",
        response=(
            "Both use the same 4x(1-x) kernel: LENR reaction rate peaks at coherence=0.5 "
            "and compound loop quality peaks at score=0.5. The HIHO threshold (0.5) governs "
            "phase transitions at both nuclear scale and AI evaluation scale."
        ),
        quality_score=0.5,
        source="hiho_band_synthetic",
    ),
    TrainingExample(
        instruction="Why does perfect output quality (score=1.0) produce zero learning in HIHO-LM?",
        response=(
            "HIHO weighting 4q(1-q) = 0 when q=1.0. A perfect score means the system already "
            "knows exactly what to do — there is no gradient to learn from. The most informative "
            "training comes from q=0.5 outputs where the system is exactly at the HIHO fixed point."
        ),
        quality_score=0.5,
        source="hiho_band_synthetic",
    ),
]


# Python code corpus (exp_EEEE2): 20 snippets from src/cohezion/model/*.py
# Goal: reduce P3_code PPL from ~33-37 toward P1_domain ~16-22.
# These cover: functions, dataclasses, methods, type hints, decorators.
_CODE_EXAMPLES = [
    TrainingExample(
        instruction="Write a Python function that computes the HIHO kernel.",
        response="def hiho_kernel(x: float) -> float:\n    s = 1.0 / (1.0 + (-(x)).__class__.__mro__[0].__init__)\n    return 4.0 * s * (1.0 - s)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show a Python dataclass for model configuration.",
        response="@dataclass\nclass CohezionLMConfig:\n    d_model: int = 256\n    n_layers: int = 4\n    n_heads: int = 4\n    d_ff: int = 1024\n    vocab_size: int = 8192\n    dropout: float = 0.1",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write a Python classmethod factory.",
        response="@classmethod\ndef mini(cls) -> 'CohezionLMConfig':\n    return cls(d_model=256, n_layers=4, n_heads=4, d_ff=1024)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show a PyTorch forward method with causal masking.",
        response="def forward(self, x: 'torch.Tensor', mask=None) -> 'torch.Tensor':\n    x = self.norm1(x)\n    attn = self.attention(x, x, x, mask)\n    x = x + self.dropout(attn)\n    return x + self.ff(self.norm2(x))",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write a Python function that generates causal attention mask.",
        response="def _causal_mask(self, seq_len: int, device) -> 'torch.Tensor':\n    mask = torch.triu(torch.ones(seq_len, seq_len, device=device), diagonal=1)\n    return mask.bool()",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python weight initialization for a neural network.",
        response="def _init_weights(self, module) -> None:\n    if isinstance(module, (nn.Linear, nn.Embedding)):\n        nn.init.normal_(module.weight, mean=0.0, std=0.02)\n    if hasattr(module, 'bias') and module.bias is not None:\n        nn.init.zeros_(module.bias)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write a Python perplexity computation function.",
        response="def hiho_perplexity(self, text: str) -> float:\n    import torch, math\n    ids = self._tokenize(text)\n    with torch.no_grad():\n        loss = self.loss(ids[:-1].unsqueeze(0), ids[1:].unsqueeze(0))\n    return math.exp(loss.item())",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python RMSprop optimizer configuration.",
        response="optimizer = torch.optim.RMSprop(\n    model.parameters(),\n    lr=5e-4,\n    alpha=0.95,\n    momentum=0.5,\n    weight_decay=0.0,\n)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write a Python training loop with gradient clipping.",
        response="for step in range(max_steps):\n    optimizer.zero_grad()\n    loss = model.loss(inputs, targets)\n    loss.backward()\n    torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)\n    optimizer.step()\n    scheduler.step()",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show a Python context manager for no_grad.",
        response="def evaluate(model, text: str) -> float:\n    model.eval()\n    with torch.no_grad():\n        ids = tokenize(text)\n        loss = model.loss(ids[:-1], ids[1:])\n    return math.exp(loss.item())",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write a Python dataclass with field defaults.",
        response="@dataclass\nclass TrainingExample:\n    instruction: str\n    response: str\n    quality_score: float = 0.5\n    source: str = 'unknown'\n\n    def hiho_weight(self) -> float:\n        q = self.quality_score\n        return 4.0 * q * (1.0 - q)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python cosine annealing learning rate schedule.",
        response="scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(\n    optimizer,\n    T_max=steps,\n    eta_min=lr * 0.01,\n)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write a Python function with type hints and docstring.",
        response='def build_balanced_dataset(\n    path: Path,\n    max_examples: int = 10_000,\n) -> TrainingDataset:\n    """Load and filter training data from autoresearch history."""\n    dataset = TrainingDataset()\n    return dataset',
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python embedding lookup and projection.",
        response="def forward(self, input_ids: 'torch.Tensor') -> 'torch.Tensor':\n    x = self.token_embed(input_ids)  # (B, T, d_model)\n    x = self.pos_embed(x)\n    for layer in self.layers:\n        x = layer(x)\n    return self.head(self.norm(x))",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python code for best-of-N seed selection.",
        response="best_model, best_ppl = None, float('inf')\nfor seed in seeds:\n    torch.manual_seed(seed)\n    model = CohezionLM(config)\n    train(model, dataset)\n    ppl = model.hiho_perplexity(eval_text)\n    if ppl < best_ppl:\n        best_model, best_ppl = model, ppl",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python class with __repr__ and __len__.",
        response="class TrainingDataset:\n    def __init__(self):\n        self.examples: list = []\n\n    def __len__(self) -> int:\n        return len(self.examples)\n\n    def __repr__(self) -> str:\n        return f'TrainingDataset({len(self)} examples)'",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python code for shuffled batch sampling.",
        response="import random\nrng = random.Random(seed)\npool = list(range(len(dataset)))\nfor step in range(max_steps):\n    batch_ids = rng.sample(pool, batch_size)\n    batch = [dataset[i] for i in batch_ids]",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python HIHO attention weight computation.",
        response="def _hiho_weights(self, q, k):\n    scale = self.d_head ** -0.5\n    scores = torch.matmul(q, k.transpose(-2, -1)) * scale\n    sigmoid = torch.sigmoid(scores)\n    return 4.0 * sigmoid * (1.0 - sigmoid)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write a Python singleton pattern with threading lock.",
        response="import threading\n_model = None\n_lock = threading.Lock()\n\ndef get_model():\n    global _model\n    if _model is None:\n        with _lock:\n            if _model is None:\n                _model = build_model()\n    return _model",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python logger configuration.",
        response="import logging\nlogger = logging.getLogger(__name__)\n\nlogger.info('Training model: steps=%d lr=%.4f', steps, lr)\nlogger.warning('No training data found at %s', path)",
        quality_score=0.5,
        source="code_corpus",
    ),
    # exp_TTTT2: 20 additional distinct code patterns for exp_PPPP2 validation
    TrainingExample(
        instruction="Write Python async function with timeout.",
        response="async def fetch_with_timeout(url: str, timeout: float = 5.0) -> str:\n    async with httpx.AsyncClient(timeout=timeout) as client:\n        response = await client.get(url)\n        response.raise_for_status()\n        return response.text",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python context manager protocol.",
        response="class ManagedResource:\n    def __enter__(self):\n        self._resource = acquire_resource()\n        return self._resource\n\n    def __exit__(self, exc_type, exc_val, tb):\n        release_resource(self._resource)\n        return False",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write a Python generator function.",
        response="def batched(iterable, n: int):\n    batch = []\n    for item in iterable:\n        batch.append(item)\n        if len(batch) == n:\n            yield batch\n            batch = []\n    if batch:\n        yield batch",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python property descriptor pattern.",
        response="class Temperature:\n    def __init__(self, celsius: float = 0.0):\n        self._celsius = celsius\n\n    @property\n    def fahrenheit(self) -> float:\n        return self._celsius * 9/5 + 32\n\n    @fahrenheit.setter\n    def fahrenheit(self, value: float) -> None:\n        self._celsius = (value - 32) * 5/9",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python abstract base class with abstract methods.",
        response="from abc import ABC, abstractmethod\n\nclass BaseExecutor(ABC):\n    @abstractmethod\n    async def execute(self, task: str) -> str: ...\n\n    @abstractmethod\n    def get_cost(self) -> float: ...",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python type annotation with generics.",
        response="from typing import TypeVar, Generic\n\nT = TypeVar('T')\n\nclass Registry(Generic[T]):\n    def __init__(self) -> None:\n        self._items: dict[str, T] = {}\n\n    def register(self, name: str, item: T) -> None:\n        self._items[name] = item\n\n    def get(self, name: str) -> T | None:\n        return self._items.get(name)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python exception handling with retry logic.",
        response="import time\n\ndef with_retry(fn, max_attempts: int = 3, delay: float = 1.0):\n    for attempt in range(max_attempts):\n        try:\n            return fn()\n        except Exception as exc:\n            if attempt == max_attempts - 1:\n                raise\n            time.sleep(delay * (2 ** attempt))\n            logger.warning('Attempt %d failed: %s', attempt + 1, exc)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python pathlib file operations.",
        response="from pathlib import Path\n\ndef read_jsonl(path: Path) -> list[dict]:\n    records = []\n    with path.open('r', encoding='utf-8') as f:\n        for line in f:\n            line = line.strip()\n            if line:\n                records.append(json.loads(line))\n    return records",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python iterator protocol implementation.",
        response="class RingBuffer:\n    def __init__(self, capacity: int):\n        self._buf: list = []\n        self._capacity = capacity\n\n    def __iter__(self):\n        return iter(self._buf)\n\n    def __len__(self) -> int:\n        return len(self._buf)\n\n    def push(self, item) -> None:\n        if len(self._buf) >= self._capacity:\n            self._buf.pop(0)\n        self._buf.append(item)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python list comprehension with filtering.",
        response="def filter_winners(experiments: list[dict]) -> list[dict]:\n    return [\n        exp for exp in experiments\n        if exp.get('winner') is True\n        and exp.get('quality_score', 0.0) >= 0.5\n    ]",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python dataclass with validation.",
        response="from dataclasses import dataclass\n\n@dataclass\nclass TrainingConfig:\n    steps: int = 320\n    lr: float = 5e-4\n    batch_size: int = 8\n\n    def __post_init__(self):\n        if self.steps <= 0:\n            raise ValueError(f'steps must be > 0, got {self.steps}')\n        if not (0 < self.lr < 1):\n            raise ValueError(f'lr must be in (0, 1), got {self.lr}')",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python class with __slots__ for memory efficiency.",
        response="class CostRecord:\n    __slots__ = ('timestamp', 'model', 'tokens', 'cost_usd')\n\n    def __init__(self, timestamp: float, model: str, tokens: int, cost_usd: float):\n        self.timestamp = timestamp\n        self.model = model\n        self.tokens = tokens\n        self.cost_usd = cost_usd",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python function using functools.lru_cache.",
        response="from functools import lru_cache\n\n@lru_cache(maxsize=256)\ndef encode_text(text: str, vocab_size: int = 256) -> tuple[int, ...]:\n    return tuple(b % vocab_size for b in text.encode('utf-8'))",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python asyncio.gather for parallel execution.",
        response="import asyncio\n\nasync def run_parallel(tasks: list[str], executor) -> list[str]:\n    coros = [executor.execute(task) for task in tasks]\n    results = await asyncio.gather(*coros, return_exceptions=True)\n    return [\n        r if not isinstance(r, Exception) else f'ERROR: {r}'\n        for r in results\n    ]",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python enum class with methods.",
        response="from enum import Enum\n\nclass InferenceNode(Enum):\n    NPU = 'npu'\n    IGPU = 'igpu'\n    CPU = 'cpu'\n    CLOUD = 'cloud'\n\n    def cost_per_token(self) -> float:\n        rates = {self.NPU: 0.0, self.IGPU: 0.0, self.CPU: 0.0, self.CLOUD: 3e-6}\n        return rates[self]",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python pydantic model validation.",
        response="from pydantic import BaseModel, field_validator\n\nclass APIResult(BaseModel):\n    success: bool\n    output: str\n    cost_usd: float\n    cache_read_tokens: int = 0\n\n    @field_validator('cost_usd')\n    @classmethod\n    def cost_nonnegative(cls, v: float) -> float:\n        if v < 0:\n            raise ValueError(f'cost_usd cannot be negative: {v}')\n        return v",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python function with keyword-only arguments.",
        response="def train_model(\n    dataset,\n    *,\n    steps: int,\n    lr: float,\n    batch_size: int = 8,\n    seed: int = 42,\n) -> 'CohezionLM':\n    model = CohezionLM(CohezionLMConfig.byte_level())\n    optimizer = torch.optim.RMSprop(model.parameters(), lr=lr)\n    return _run_training_loop(model, optimizer, dataset, steps, batch_size, seed)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python dict comprehension and merging.",
        response="def merge_metrics(base: dict, updates: dict) -> dict:\n    return {\n        k: updates.get(k, v)\n        for k, v in base.items()\n    } | {k: v for k, v in updates.items() if k not in base}",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Write Python function that computes cosine similarity.",
        response="import math\n\ndef cosine_similarity(a: list[float], b: list[float]) -> float:\n    dot = sum(x * y for x, y in zip(a, b))\n    norm_a = math.sqrt(sum(x * x for x in a))\n    norm_b = math.sqrt(sum(x * x for x in b))\n    if norm_a == 0 or norm_b == 0:\n        return 0.0\n    return dot / (norm_a * norm_b)",
        quality_score=0.5,
        source="code_corpus",
    ),
    TrainingExample(
        instruction="Show Python class with __call__ method.",
        response="class Tokenizer:\n    def __init__(self, vocab_size: int = 256):\n        self.vocab_size = vocab_size\n\n    def __call__(self, text: str) -> list[int]:\n        return [b % self.vocab_size for b in text.encode('utf-8')]",
        quality_score=0.5,
        source="code_corpus",
    ),
]


def build_balanced_training_dataset(
    autoresearch_path: Path = _DEFAULT_AUTORESEARCH_PATH,
    include_stealthskater: bool = True,
    max_autoresearch: int = 10_000,
    include_code: bool = True,
    n_code: int = 20,
) -> TrainingDataset:
    """Build training dataset with HIHO-band examples for balanced HIHO weighting.

    Extends build_training_dataset() with synthetic q=0.5 examples (HIHO-band)
    to ensure the HIHO-weighted loss has meaningful gradients at the ideal point.

    Finding from exp_PPPP1: high-quality (q=0.9+) examples have HIHO weight ~0.36,
    while q=0.5 examples have weight 1.0. Including HIHO-band examples prevents
    the model from being trained only on the low-gradient region.

    include_code: exp_EEEE2 — add 20 Python code snippets to close P3_code PPL gap.
    P3_code was ~33-37 vs P1_domain ~16-22 with no code in training data.

    n_code: exp_PPPP2 — number of code snippets to include (default 20; can use
    multiples to expand vocabulary with weighted-pool compensation in from_autoresearch).
    """
    combined = build_training_dataset(autoresearch_path, include_stealthskater, max_autoresearch)

    # Add HIHO-band synthetic examples
    for ex in _HIHO_BAND_EXAMPLES:
        combined.add(ex)

    # Add Python code corpus (exp_EEEE2); n_code controls how many are included
    if include_code:
        # Cycle through _CODE_EXAMPLES to reach n_code total
        for i, ex in enumerate((_CODE_EXAMPLES * ((n_code // len(_CODE_EXAMPLES)) + 1))[:n_code]):
            combined.add(ex)

    logger.info(
        "Built balanced dataset: %d examples | mean_quality=%.3f | HIHO=%s",
        len(combined),
        combined.mean_quality,
        combined.hiho_engaged,
    )
    return combined
