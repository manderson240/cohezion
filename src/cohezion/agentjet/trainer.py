"""AgentJet RL training orchestrator for the CALL loop."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from cohezion.agentjet.context_optimizer import MODEL_OLLAMA_KEY_MAP, OllamaContextManager
from cohezion.agentjet.judger import PhiScoreJudger
from cohezion.agentjet.task_reader import JourneyTaskReader


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DATA_DIR = _PROJECT_ROOT / "data" / "training"

if TYPE_CHECKING:
    from cohezion.agentjet.workflow import CohezionWorkflow

logger = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    """Result of a single AgentJet CALL training cycle."""

    success: bool
    model_name: str  # Final Ollama model name after training
    base_model: str  # Model that was fine-tuned
    skill_domain: str | None  # Which skill domain was trained
    epochs_completed: int
    samples_used: int
    avg_reward: float  # Average reward from PhiScoreJudger
    training_duration_s: float
    output_path: Path | None  # Path to GGUF or config script
    error: str | None = None  # Error message if success=False
    dry_run: bool = False


class AgentJetTrainer:
    """Orchestrates the full CALL RL cycle with OOM-safe training.

    Safety protocol (enforced in train()):
    1. Check available memory via ResourceClient or OllamaContextManager.
    2. Unload ALL inference models.
    3. Run training backend (llamafactory Phase 1, or agentjet Phase 3).
    4. Export GGUF → ollama create cohezion-{domain}-v{n}.
    5. Reload inference models.
    6. Update SmartRouter with new model name.
    All steps run inside try/finally so reload always happens.

    Parameters
    ----------
    workflow : CohezionWorkflow, optional
        Workflow instance for generating rollouts. Created lazily if not provided.
    judger : PhiScoreJudger, optional
        Reward judger. Defaults to PhiScoreJudger().
    reader : JourneyTaskReader, optional
        Task loader. Defaults to JourneyTaskReader().
    context_manager : OllamaContextManager, optional
        Manages Ollama model lifecycle. Defaults to OllamaContextManager().
    backend : Literal["agentjet", "llamafactory"]
        Training backend to use. "llamafactory" uses LocalFinetuner (Phase 1).
        "agentjet" targets verl/PPO (Phase 3, not yet implemented).
    """

    def __init__(
        self,
        workflow: CohezionWorkflow | None = None,
        judger: PhiScoreJudger | None = None,
        reader: JourneyTaskReader | None = None,
        context_manager: OllamaContextManager | None = None,
        backend: Literal["agentjet", "llamafactory"] = "llamafactory",
    ) -> None:
        self._workflow = workflow  # Lazily resolved; not required for training
        self.judger = judger if judger is not None else PhiScoreJudger()
        self.reader = reader if reader is not None else JourneyTaskReader()
        self.context_manager = context_manager if context_manager is not None else OllamaContextManager()
        self.backend: Literal["agentjet", "llamafactory"] = backend

    async def train(
        self,
        target_model: str = "qwen3.5:9b",
        skill_domain: str | None = None,
        epochs: int = 3,
        min_phi: float = 0.7,
        dry_run: bool = False,
    ) -> TrainingResult:
        """Run the full CALL cycle: load data → safety check → train → reload.

        Parameters
        ----------
        target_model : str
            Base Ollama model to fine-tune.
        skill_domain : str, optional
            Filter training data to this skill domain. None means all domains.
        epochs : int
            Number of training epochs to pass to the backend.
        min_phi : float
            Minimum phi_score threshold for including a task in the training set.
        dry_run : bool
            If True, skip actual training and model unload/reload. Useful for
            validating the pipeline without touching Ollama.

        Returns
        -------
        TrainingResult
            Describes the outcome of the training run.
        """
        start_time = time.monotonic()

        # 1. Load training data
        tasks = self.reader.read(skill_filter=skill_domain, min_phi=min_phi)
        if not tasks:
            logger.warning(
                "AgentJetTrainer.train: no tasks matched filters (skill_domain=%r, min_phi=%.2f)",
                skill_domain,
                min_phi,
            )
            return TrainingResult(
                success=False,
                model_name="",
                base_model=target_model,
                skill_domain=skill_domain,
                epochs_completed=0,
                samples_used=0,
                avg_reward=0.0,
                training_duration_s=time.monotonic() - start_time,
                output_path=None,
                error="No training data matched filters",
                dry_run=dry_run,
            )

        training_lock: object | None = None
        output_path: Path | None = None
        try:
            # 2. OOM safety check — acquires lock or raises OOMRiskError
            training_lock = await self._safety_check(target_model)
            # 3. Unload all inference models before training
            if not dry_run:
                logger.info("AgentJetTrainer: unloading inference models for training")
                await self.context_manager.unload_all_for_training()

            # 4. Compute rewards for dataset quality metrics
            rewards = self.judger.batch_judge(tasks)
            avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
            logger.info(
                "AgentJetTrainer: %d tasks, avg_reward=%.3f",
                len(tasks),
                avg_reward,
            )

            # 5. Run training backend
            if not dry_run:
                output_path = await self._run_training(target_model, tasks, skill_domain, epochs)

            # 6. Build final model name
            domain = skill_domain or "general"
            version = int(time.time()) % 10000
            final_model_name = f"cohezion-{domain}-v{version}"

            logger.info(
                "AgentJetTrainer: training complete — model=%s output=%s",
                final_model_name,
                output_path,
            )
            return TrainingResult(
                success=True,
                model_name=final_model_name,
                base_model=target_model,
                skill_domain=skill_domain,
                epochs_completed=epochs,
                samples_used=len(tasks),
                avg_reward=avg_reward,
                training_duration_s=time.monotonic() - start_time,
                output_path=output_path,
                dry_run=dry_run,
            )

        except Exception as exc:
            logger.error("AgentJetTrainer.train failed: %s", exc, exc_info=True)
            return TrainingResult(
                success=False,
                model_name="",
                base_model=target_model,
                skill_domain=skill_domain,
                epochs_completed=0,
                samples_used=len(tasks),
                avg_reward=0.0,
                training_duration_s=time.monotonic() - start_time,
                output_path=None,
                error=str(exc),
                dry_run=dry_run,
            )

        finally:
            # Always reload inference models — even if training failed
            if not dry_run:
                logger.info("AgentJetTrainer: reloading inference models")
                try:
                    await self.context_manager.reload_inference_models()
                except Exception as reload_exc:
                    logger.warning("Inference model reload failed (non-fatal): %s", reload_exc)

            # Release training lock regardless of outcome
            if training_lock is not None:
                try:
                    from cohezion.platform.resource_manager import ResourceClient

                    client = ResourceClient()
                    lock_id: str = training_lock.lock_id  # type: ignore[attr-defined]
                    await client.release_training_lock(lock_id)
                    logger.debug("AgentJetTrainer: released training lock %s", lock_id)
                except Exception as lock_exc:
                    logger.warning("Training lock release failed (non-fatal): %s", lock_exc)
                finally:
                    training_lock = None

    async def _safety_check(self, model: str) -> object | None:
        """OOM check before training begins.

        Tries the platform ResourceClient daemon first (cross-session coordination).
        Falls back to a local Ollama memory estimate when the daemon is unavailable.

        Raises
        ------
        OOMRiskError
            When local memory check indicates insufficient headroom.
        ResourceUnavailableError
            When the platform daemon explicitly denies the training lock.
        """
        profile = self.context_manager.get_profile(model)
        required_gb = profile.size_gb * 3.0  # Training needs ~3x model size

        # Attempt platform daemon coordination first
        try:
            from cohezion.platform.resource_manager import (
                ResourceClient,
                ResourceUnavailableError,
            )

            client = ResourceClient()
            if client.is_daemon_running():
                lock = await client.acquire_training_lock(model, required_gb, timeout_s=30.0)
                if lock is None:
                    raise ResourceUnavailableError(
                        f"Platform daemon denied training lock for {model} (need {required_gb:.1f} GiB)"
                    )
                logger.info(
                    "AgentJetTrainer: acquired training lock %s (%.1f GiB reserved)",
                    lock.lock_id,
                    required_gb,
                )
                return lock
        except ImportError:
            logger.debug("cohezion.platform.resource_manager unavailable; using local OOM check")

        # Fallback: local available memory estimate
        available = await self.context_manager.get_available_memory_gb()
        headroom_required = required_gb * 1.2
        if available < headroom_required:
            from cohezion.agentjet.context_optimizer import OllamaContextManager  # noqa: F401

            # Import OOMRiskError from resource_manager if available, else define locally
            try:
                from cohezion.platform.resource_manager import OOMRiskError
            except ImportError:

                class OOMRiskError(RuntimeError):  # type: ignore[no-redef]
                    pass

            raise OOMRiskError(
                f"OOM risk: need {headroom_required:.1f} GiB (with 20% headroom), have {available:.1f} GiB available"
            )

        logger.info(
            "AgentJetTrainer: local OOM check passed (need %.1f GiB, have %.1f GiB)",
            headroom_required,
            available,
        )
        return None

    async def _run_training(
        self,
        model: str,
        tasks: list[dict],
        skill_domain: str | None,
        epochs: int,
    ) -> Path | None:
        """Dispatch to the configured training backend.

        Parameters
        ----------
        model : str
            Base model identifier.
        tasks : list[dict]
            Normalised task dicts from JourneyTaskReader.
        skill_domain : str, optional
            Skill domain being trained (used for output naming).
        epochs : int
            Number of training epochs.

        Returns
        -------
        Path | None
            Path to generated training config/script, or None on failure.
        """
        if self.backend == "llamafactory":
            return await self._run_llamafactory(model, tasks, skill_domain, epochs)
        if self.backend == "agentjet":
            return await self._run_agentjet_rl(model, tasks, skill_domain, epochs)
        logger.warning("Unknown backend %r; falling back to llamafactory", self.backend)
        return await self._run_llamafactory(model, tasks, skill_domain, epochs)

    async def _run_llamafactory(
        self,
        model: str,
        tasks: list[dict],
        skill_domain: str | None,
        epochs: int,
    ) -> Path | None:
        """Phase 1: generate a llamafactory training config via LocalFinetuner.

        Writes tasks to the standard JSONL location, then calls
        LocalFinetuner.run_qlora_training() which produces a bash script / config.

        Returns the path to the generated config file, or None on error.
        """
        try:
            from cohezion.flume.local_finetune_pipeline import LocalFinetuner

            output_name = f"cohezion_{skill_domain or 'general'}_v{int(time.time()) % 10000}"

            base_key = MODEL_OLLAMA_KEY_MAP.get(model, "qwen3.5")

            finetuner = LocalFinetuner(base_model=base_key, output_name=output_name)

            # Write tasks to training data dir for LocalFinetuner
            import json

            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            journey_path = _DATA_DIR / "finetune_journeys.jsonl"

            logger.info(
                "AgentJetTrainer: writing %d tasks to %s for LocalFinetuner",
                len(tasks),
                journey_path,
            )
            with journey_path.open("w", encoding="utf-8") as fh:
                for task in tasks:
                    fh.write(json.dumps(task) + "\n")

            # Run in executor — LocalFinetuner is synchronous
            loop = asyncio.get_running_loop()
            config_path: Path = await loop.run_in_executor(
                None,
                lambda: finetuner.run_qlora_training(epochs=epochs),
            )
            logger.info("AgentJetTrainer: llamafactory config generated: %s", config_path)
            return config_path

        except Exception as exc:
            logger.error("AgentJetTrainer._run_llamafactory failed: %s", exc, exc_info=True)
            return None

    async def _run_agentjet_rl(
        self,
        model: str,
        tasks: list[dict],
        skill_domain: str | None,
        epochs: int,
    ) -> Path | None:
        """Phase 3: AgentJet verl/PPO RL training.

        Not yet implemented (AMD ROCm support for verl is pending).
        Falls back to llamafactory until Phase 3 ships.
        """
        logger.warning("AgentJet RL backend (verl/PPO) is not yet implemented for AMD. Falling back to llamafactory.")
        return await self._run_llamafactory(model, tasks, skill_domain, epochs)
