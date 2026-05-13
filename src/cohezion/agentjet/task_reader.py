"""JourneyTaskReader: loads training tasks from journey JSONL or ExperienceCollector.

Primary source: ``data/training/finetune_journeys.jsonl`` produced by
``JourneyToFinetuneConverter.run()``.

Fallback source: ``ExperienceCollector.collect_all()`` which pulls from
Parquet shards, SurrealDB, and vault experiment JSON files.

JSONL record schema (from JourneyToFinetuneConverter._to_training_pairs):
  {
    "instruction": str,
    "output": str,
    "metadata": {
      "skill": str,
      "phi_score": float,
      "mission": str,
      "trajectory_12d": list[float]
    }
  }

ExperienceCollector records use a flat schema with fields including:
  phi_score, skill_name, mission_id, input_preview, trajectory, ...

JourneyTaskReader normalises both schemas into a consistent task dict with
top-level ``phi_score``, ``skill_name``, ``instruction``, and ``output``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "training" / "finetune_journeys.jsonl"


class JourneyTaskReader:
    """Reads journey data as task dicts for AgentJet training.

    Loads from ``data/training/finetune_journeys.jsonl`` when available;
    falls back to ``ExperienceCollector`` when the file does not exist or
    cannot be read.

    Parameters
    ----------
    jsonl_path : Path, optional
        Path to the JSONL file produced by ``JourneyToFinetuneConverter``.
        Defaults to ``data/training/finetune_journeys.jsonl``.
    """

    DEFAULT_PATH: Path = _DEFAULT_PATH

    def __init__(self, jsonl_path: Path | None = None) -> None:
        self._jsonl_path: Path = jsonl_path if jsonl_path is not None else self.DEFAULT_PATH

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read(
        self,
        skill_filter: str | None = None,
        min_phi: float = 0.7,
        max_samples: int = 1000,
    ) -> list[dict[str, Any]]:
        """Load tasks, optionally filtered by skill name and minimum phi_score.

        Parameters
        ----------
        skill_filter : str, optional
            If provided, only tasks whose ``skill_name`` matches this string
            (case-insensitive) are returned.
        min_phi : float
            Minimum phi_score threshold. Tasks below this value are excluded.
        max_samples : int
            Maximum number of tasks to return.

        Returns
        -------
        list[dict]
            Normalised task dicts, each containing at minimum:
            ``phi_score``, ``skill_name``, ``instruction``, ``output``.
        """
        records = self._load_records()

        filtered: list[dict[str, Any]] = []
        for rec in records:
            phi = float(rec.get("phi_score", 0.0))
            if phi < min_phi:
                continue
            if skill_filter is not None:
                skill = str(rec.get("skill_name", "")).lower()
                if skill != skill_filter.lower():
                    continue
            filtered.append(rec)
            if len(filtered) >= max_samples:
                break

        logger.info(
            "JourneyTaskReader.read: %d/%d records pass filters (skill_filter=%r, min_phi=%.2f)",
            len(filtered),
            len(records),
            skill_filter,
            min_phi,
        )
        return filtered

    def group_by_skill(self, min_phi: float = 0.7) -> dict[str, list[dict[str, Any]]]:
        """Group tasks by skill name, filtered by minimum phi_score.

        Parameters
        ----------
        min_phi : float
            Only tasks with phi_score >= min_phi are included.

        Returns
        -------
        dict[str, list[dict]]
            Mapping of skill_name → list of task dicts.
        """
        records = self.read(min_phi=min_phi, max_samples=100_000)
        groups: dict[str, list[dict[str, Any]]] = {}
        for rec in records:
            skill = str(rec.get("skill_name", "unknown"))
            groups.setdefault(skill, []).append(rec)

        logger.info(
            "JourneyTaskReader.group_by_skill: %d skills, %d total tasks (min_phi=%.2f)",
            len(groups),
            sum(len(v) for v in groups.values()),
            min_phi,
        )
        return groups

    # ------------------------------------------------------------------
    # Private loaders
    # ------------------------------------------------------------------

    def _load_records(self) -> list[dict[str, Any]]:
        """Load records from JSONL or fall back to ExperienceCollector."""
        if self._jsonl_path.exists():
            try:
                return self._load_from_jsonl()
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "Failed to load JSONL from %s (%s), falling back to collector",
                    self._jsonl_path,
                    exc,
                )
        else:
            logger.debug(
                "JSONL file %s not found, using ExperienceCollector fallback",
                self._jsonl_path,
            )

        return self._load_from_collector()

    def _load_from_jsonl(self) -> list[dict[str, Any]]:
        """Parse JSONL produced by JourneyToFinetuneConverter.

        Each line is a JSON object with schema::

            {
              "instruction": str,
              "output": str,
              "metadata": {"skill": str, "phi_score": float, ...}
            }

        Returns
        -------
        list[dict]
            Normalised records with top-level ``phi_score`` and ``skill_name``.

        Raises
        ------
        OSError
            If the file cannot be opened.
        json.JSONDecodeError
            If a line contains invalid JSON.
        """
        records: list[dict[str, Any]] = []
        with self._jsonl_path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise json.JSONDecodeError(f"Line {lineno}: {exc.msg}", exc.doc, exc.pos) from exc

                records.append(self._normalise_jsonl_record(raw))

        logger.debug("Loaded %d records from %s", len(records), self._jsonl_path)
        return records

    def _load_from_collector(self) -> list[dict[str, Any]]:
        """Load experiences via ExperienceCollector (three-tier fallback).

        Returns
        -------
        list[dict]
            Normalised records. Returns an empty list if collector is
            unavailable or raises an unexpected exception.
        """
        try:
            from cohezion.flume.experience_collector import ExperienceCollector

            collector = ExperienceCollector()
            raw_records = collector.collect_all(max_samples=100_000)
        except ImportError as exc:
            logger.warning("ExperienceCollector import failed: %s", exc)
            return []
        except Exception as exc:
            logger.warning(
                "ExperienceCollector.collect_all() failed (non-blocking): %s",
                exc,
                exc_info=True,
            )
            return []

        records = [self._normalise_collector_record(r) for r in raw_records]
        logger.debug("Loaded %d records from ExperienceCollector", len(records))
        return records

    # ------------------------------------------------------------------
    # Schema normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_jsonl_record(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalise a JSONL record to the canonical task dict schema.

        Parameters
        ----------
        raw : dict
            Raw JSON object from finetune_journeys.jsonl.

        Returns
        -------
        dict
            Canonical task dict with top-level phi_score and skill_name.
        """
        metadata: dict[str, Any] = raw.get("metadata", {})
        return {
            "instruction": raw.get("instruction", ""),
            "output": raw.get("output", ""),
            "phi_score": float(metadata.get("phi_score", 0.0)),
            "skill_name": str(metadata.get("skill", "unknown")),
            "mission_id": str(metadata.get("mission", "")),
            "trajectory_12d": metadata.get("trajectory_12d", []),
            # Preserve original metadata for downstream consumers
            "metadata": metadata,
        }

    @staticmethod
    def _normalise_collector_record(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalise an ExperienceCollector record to the canonical task dict schema.

        Parameters
        ----------
        raw : dict
            Flat experience dict from ExperienceCollector.collect_all().

        Returns
        -------
        dict
            Canonical task dict with top-level phi_score and skill_name.
        """
        return {
            "instruction": str(raw.get("input_preview", "")),
            "output": "",  # Raw collector records may not have formatted output
            "phi_score": float(raw.get("phi_score", 0.0)),
            "skill_name": str(raw.get("skill_name", "unknown")),
            "mission_id": str(raw.get("mission_id", "")),
            "trajectory_12d": raw.get("trajectory", [])[:12] if isinstance(raw.get("trajectory"), list) else [],
            # Preserve all original fields for downstream consumers
            "metadata": raw,
        }
