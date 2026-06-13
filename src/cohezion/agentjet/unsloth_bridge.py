"""Unsloth Studio integration for Phase 2 QLoRA training.

Available NOW:  Data Recipes API (convert vault → dataset).
Available SOON: QLoRA training (when AMD ROCm support ships in Unsloth).

Phase 1 (current): Falls back to LocalFinetuner (llama.cpp / llamafactory).
Phase 2 (planned): QLoRA via Unsloth Studio once AMD support is confirmed.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiohttp

from cohezion.agentjet.context_optimizer import MODEL_OLLAMA_KEY_MAP


logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DATA_DIR = _PROJECT_ROOT / "data" / "training"

UNSLOTH_STUDIO_URL = "https://studio.unsloth.ai"

# Data Recipes endpoint (available now — no AMD dependency)
_RECIPES_ENDPOINT = "/api/v1/recipes"


class UnslothBridge:
    """Interface to Unsloth Studio for dataset preparation and QLoRA training.

    Phases
    ------
    Phase 1 (active): LocalFinetuner fallback — llama.cpp / llamafactory config.
    Phase 2 (pending): QLoRA training via Unsloth Studio when AMD support ships.
    Data Recipes (active): ``create_dataset_from_vault`` is available now and
    calls the Unsloth Studio Data Recipes API to convert vault notes to JSONL.

    Parameters
    ----------
    api_key : str, optional
        Unsloth Studio API key. If None, Data Recipes API calls will be
        attempted without auth (may fail for private endpoints).
    studio_url : str
        Base URL for the Unsloth Studio API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        studio_url: str = UNSLOTH_STUDIO_URL,
    ) -> None:
        self._api_key = api_key
        self._studio_url = studio_url.rstrip("/")

    # ------------------------------------------------------------------
    # Capability probes
    # ------------------------------------------------------------------

    def is_training_available(self) -> bool:
        """Return True if Unsloth QLoRA training is supported on current hardware.

        Currently returns False because Unsloth Studio QLoRA training requires
        CUDA (NVIDIA) and AMD ROCm support has not shipped yet.  When AMD support
        arrives this method should be updated to probe the runtime.
        """
        return False

    # ------------------------------------------------------------------
    # Data Recipes (available now)
    # ------------------------------------------------------------------

    async def create_dataset_from_vault(
        self,
        vault_query: str,
        output_path: Path | None = None,
    ) -> Path:
        """Convert vault notes to a JSONL training dataset via Unsloth Data Recipes.

        Attempts to call the Unsloth Studio Data Recipes API.  If the API is
        unavailable (no key, network error, or endpoint not reachable) the
        method falls back to reading the local finetune_journeys.jsonl file
        produced by JourneyToFinetuneConverter.

        Parameters
        ----------
        vault_query : str
            Search query used to select relevant vault notes (forwarded to the
            Data Recipes API as the ``query`` field).
        output_path : Path, optional
            Where to write the output JSONL.  Defaults to
            ``data/training/unsloth_dataset.jsonl``.

        Returns
        -------
        Path
            Absolute path to the generated JSONL dataset file.
        """
        out = output_path if output_path is not None else _DATA_DIR / "unsloth_dataset.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)

        # Try Unsloth Data Recipes API first
        api_data = await self._call_data_recipes_api(vault_query)
        if api_data is not None:
            logger.info(
                "UnslothBridge: received %d records from Data Recipes API",
                len(api_data),
            )
            with out.open("w", encoding="utf-8") as fh:
                for record in api_data:
                    fh.write(json.dumps(record) + "\n")
            logger.info("UnslothBridge: dataset written to %s", out)
            return out

        # Fallback: copy local finetune_journeys.jsonl
        local_source = _DATA_DIR / "finetune_journeys.jsonl"
        if local_source.exists():
            logger.info(
                "UnslothBridge: Data Recipes API unavailable; copying %s → %s",
                local_source,
                out,
            )
            records = _read_jsonl(local_source)
            # Filter records loosely by vault_query in instruction/output text
            if vault_query:
                query_lower = vault_query.lower()
                filtered = [
                    r
                    for r in records
                    if query_lower in str(r.get("instruction", "")).lower()
                    or query_lower in str(r.get("output", "")).lower()
                ]
                # If filter is too aggressive, keep all records
                if not filtered:
                    filtered = records
            else:
                filtered = records

            with out.open("w", encoding="utf-8") as fh:
                for record in filtered:
                    fh.write(json.dumps(record) + "\n")
            logger.info(
                "UnslothBridge: fallback dataset written (%d records) to %s",
                len(filtered),
                out,
            )
            return out

        # Last resort: empty dataset with a warning
        logger.warning(
            "UnslothBridge: no data source available (API down, no local JSONL). Writing empty dataset to %s",
            out,
        )
        out.write_text("", encoding="utf-8")
        return out

    # ------------------------------------------------------------------
    # QLoRA training (Phase 2 — not yet available on AMD)
    # ------------------------------------------------------------------

    async def train_qlora(
        self,
        dataset: Path,
        model: str,
        config: dict[str, Any] | None = None,
    ) -> Path | None:
        """Attempt QLoRA training via Unsloth Studio.

        Returns None when AMD training is not yet supported (current state).
        Phase 2 will implement full QLoRA when Unsloth ships AMD ROCm support.

        Parameters
        ----------
        dataset : Path
            Path to the JSONL training dataset (e.g., from create_dataset_from_vault).
        model : str
            Base model identifier (e.g., "qwen3.5:9b").
        config : dict, optional
            Additional training configuration forwarded to the Unsloth API.

        Returns
        -------
        Path | None
            Path to the trained model checkpoint, or None if training is
            unavailable on the current hardware.
        """
        if not self.is_training_available():
            logger.info(
                "UnslothBridge.train_qlora: AMD QLoRA not available yet (Phase 2). "
                "Falling back to LocalFinetuner for %s.",
                model,
            )
            return await self._llamafactory_fallback(dataset, model, config)

        # Phase 2 placeholder — implement when AMD Unsloth support ships
        raise NotImplementedError(
            "Unsloth QLoRA training on AMD is not yet implemented. "
            "Set is_training_available() → True once AMD support ships."
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _call_data_recipes_api(self, vault_query: str) -> list[dict[str, Any]] | None:
        """Call Unsloth Studio Data Recipes endpoint.

        Returns the parsed list of records on success, or None on any failure.
        """
        url = f"{self._studio_url}{_RECIPES_ENDPOINT}"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {"query": vault_query, "format": "jsonl"}

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30.0),
                ) as resp,
            ):
                if resp.status == 200:
                    data = await resp.json()
                    records: list[dict[str, Any]] = data.get("records", [])
                    return records
                logger.debug(
                    "UnslothBridge: Data Recipes API returned HTTP %d — using fallback",
                    resp.status,
                )
                return None
        except aiohttp.ClientError as exc:
            logger.debug("UnslothBridge: Data Recipes API unreachable: %s", exc)
            return None

    async def _llamafactory_fallback(
        self,
        dataset: Path,
        model: str,
        config: dict[str, Any] | None,
    ) -> Path | None:
        """Generate a llamafactory training config as a Phase 2 fallback."""
        import asyncio

        try:
            from cohezion.flume.local_finetune_pipeline import LocalFinetuner

            base_key = MODEL_OLLAMA_KEY_MAP.get(model, "qwen3.5")
            epochs = int((config or {}).get("epochs", 3))

            finetuner = LocalFinetuner(base_model=base_key, output_name="cohezion_unsloth_phase2")
            loop = asyncio.get_running_loop()
            config_path: Path = await loop.run_in_executor(
                None,
                lambda: finetuner.run_qlora_training(epochs=epochs),
            )
            logger.info("UnslothBridge: llamafactory fallback config written to %s", config_path)
            return config_path
        except Exception as exc:
            logger.error("UnslothBridge._llamafactory_fallback failed: %s", exc, exc_info=True)
            return None


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file and return a list of parsed dicts. Skips invalid lines."""
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning(
                    "_read_jsonl: skipping invalid JSON at line %d in %s: %s",
                    lineno,
                    path,
                    exc,
                )
    return records
