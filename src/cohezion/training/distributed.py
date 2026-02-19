"""Distributed training support for FLUME using FSDP and Accelerate.

Provides seamless scaling from single GPU to multi-node training.
Optimized for Strix Halo (128GB unified memory) with CPU offloading.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.distributed as dist


logger = logging.getLogger(__name__)


@dataclass
class DistributedConfig:
    """Configuration for distributed training."""

    backend: str = "nccl"
    world_size: int = 1
    rank: int = 0
    local_rank: int = 0

    # FSDP config
    fsdp_enabled: bool = False
    sharding_strategy: str = "full"  # "full", "hybrid", "auto"
    cpu_offload: bool = True
    mixed_precision: str = "bf16"  # "fp16", "bf16", "fp32"
    gradient_checkpointing: bool = True

    # DeepSpeed alternative
    deepspeed_enabled: bool = False
    zero_stage: int = 3

    # Training config
    batch_size: int = 32
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-4
    weight_decay: float = 0.01


class DistributedTrainer:
    """Distributed trainer for FLUME models.

    Supports:
    - DDP (DataParallel)
    - FSDP (FullyShardedDataParallel)
    - DeepSpeed ZeRO
    - CPU offloading for memory-constrained devices

    Example:
        config = DistributedConfig(
            fsdp_enabled=True,
            cpu_offload=True,
            mixed_precision="bf16"
        )
        trainer = DistributedTrainer(config)
        trainer.train(model, dataset)
    """

    def __init__(self, config: DistributedConfig | None = None):
        """Initialize distributed trainer.

        Args:
            config: Distributed training configuration
        """
        self.config = config or DistributedConfig()
        self.accelerator = None
        self.model = None
        self.optimizer = None
        self.scheduler = None

        self._is_distributed = False
        self._setup_distributed()

    def _setup_distributed(self) -> None:
        """Initialize distributed training."""
        if self.config.world_size > 1 or self._has_gpu():
            try:
                dist.init_process_group(
                    backend=self.config.backend,
                    init_method="env://",
                    world_size=self.config.world_size,
                    rank=self.config.rank,
                )
                self._is_distributed = True
                logger.info(
                    f"Initialized distributed training: "
                    f"rank={self.config.rank}, world_size={self.config.world_size}"
                )
            except Exception as e:
                logger.warning(f"Distributed init failed, using single process: {e}")
                self._is_distributed = False

    def _has_gpu(self) -> bool:
        """Check if CUDA is available."""
        return torch.cuda.is_available()

    def setup_accelerate(self, model: torch.nn.Module) -> Any:
        """Setup Hugging Face Accelerate for simplified training.

        Args:
            model: PyTorch model to wrap

        Returns:
            Prepared model and accelerator
        """
        try:
            from accelerate import Accelerator

            accelerator = Accelerator(
                mixed_precision=self.config.mixed_precision,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                log_with=None,  # Can add wandb/tensorboard
                project_dir="logs/accelerate",
            )

            self.accelerator = accelerator

            # Prepare model, optimizer, dataloader
            model = accelerator.prepare(model)

            logger.info(f"Accelerate prepared: device={accelerator.device}")
            return accelerator

        except ImportError:
            logger.error("accelerate not installed: pip install accelerate")
            raise

    def setup_fsdp(
        self,
        model: torch.nn.Module,
    ) -> torch.nn.Module:
        """Setup FSDP (FullyShardedDataParallel) for large models.

        Args:
            model: PyTorch model to wrap

        Returns:
            FSDP-wrapped model
        """
        try:
            from torch.distributed.fsdp import (
                BackwardPrefetch,
                FullyShardedDataParallel,
                MixedPrecision,
                ShardingStrategy,
            )
        except ImportError:
            logger.error("FSDP requires PyTorch 2.0+ with CUDA")
            raise

        # Define sharding strategy
        sharding_strategy_map = {
            "full": ShardingStrategy.FULL_SHARD,
            "hybrid": ShardingStrategy.HYBRID_SHARD,
            "auto": ShardingStrategy.SHARD_GRAD_OP,
        }
        sharding_strategy = sharding_strategy_map.get(
            self.config.sharding_strategy, ShardingStrategy.FULL_SHARD
        )

        # Mixed precision config
        if self.config.mixed_precision == "bf16":
            param_dtype = torch.bfloat16
            reduce_dtype = torch.bfloat16
            buffer_dtype = torch.bfloat16
        elif self.config.mixed_precision == "fp16":
            param_dtype = torch.float16
            reduce_dtype = torch.float16
            buffer_dtype = torch.float16
        else:
            param_dtype = torch.float32
            reduce_dtype = torch.float32
            buffer_dtype = torch.float32

        mixed_precision_policy = MixedPrecision(
            param_dtype=param_dtype,
            reduce_dtype=reduce_dtype,
            buffer_dtype=buffer_dtype,
        )

        # Auto-wrap policy for transformers
        def auto_wrap_policy_fn(module):
            return auto_wrap_policy_fn(module)

        # Wrap model with FSDP
        fsdp_model = FullyShardedDataParallel(
            model,
            sharding_strategy=sharding_strategy,
            cpu_offload=self.config.cpu_offload,
            mixed_precision=mixed_precision_policy,
            backward_prefetch=BackwardPrefetch.BACKWARD_PRE,
            device_id=torch.cuda.current_device() if self._has_gpu() else None,
        )

        logger.info(
            f"FSDP initialized: strategy={self.config.sharding_strategy}, "
            f"cpu_offload={self.config.cpu_offload}, "
            f"mixed_precision={self.config.mixed_precision}"
        )

        self.model = fsdp_model
        return fsdp_model

    def setup_deepspeed(
        self,
        config_path: str | None = None,
    ) -> dict[str, Any]:
        """Setup DeepSpeed ZeRO optimization.

        Args:
            config_path: Path to DeepSpeed config JSON

        Returns:
            DeepSpeed configuration dict
        """
        if config_path and Path(config_path).exists():
            import json

            with open(config_path) as f:
                ds_config = json.load(f)
        else:
            # Default config for Strix Halo
            ds_config = {
                "train_batch_size": "auto",
                "train_micro_batch_size_per_gpu": "auto",
                "fp16": {"enabled": False},
                "bf16": {"enabled": self.config.mixed_precision == "bf16"},
                "zero_optimization": {
                    "stage": self.config.zero_stage,
                    "offload_optimizer": {"device": "cpu", "pin_memory": True},
                    "offload_param": {"device": "cpu", "pin_memory": True},
                    "overlap_comm": True,
                    "contiguous_gradients": True,
                },
                "gradient_accumulation_steps": self.config.gradient_accumulation_steps,
                "gradient_clipping": 1.0,
                "steps_per_print": 10,
            }

        logger.info(f"DeepSpeed config: stage={self.config.zero_stage}")
        return ds_config

    def cleanup(self) -> None:
        """Cleanup distributed training."""
        if self._is_distributed:
            dist.destroy_process_group()
            logger.info("Distributed training cleanup complete")

    def is_main_process(self) -> bool:
        """Check if current process is main (rank 0)."""
        return not self._is_distributed or self.config.rank == 0

    def get_world_size(self) -> int:
        """Get total number of processes."""
        return self.config.world_size if self._is_distributed else 1

    def barrier(self) -> None:
        """Synchronize all processes."""
        if self._is_distributed:
            dist.barrier()

    def gather_metrics(self, metric: float) -> dict[int, float] | None:
        """Gather metrics from all processes.

        Args:
            metric: Metric value from current process

        Returns:
            Dict of rank -> metric (only on rank 0)
        """
        if not self._is_distributed:
            return {0: metric}

        tensor = torch.tensor([metric], device="cuda" if self._has_gpu() else "cpu")
        gathered = [torch.zeros_like(tensor) for _ in range(self.config.world_size)]
        dist.all_gather(gathered, tensor)

        if self.config.rank == 0:
            return {i: gathered[i].item() for i in range(self.config.world_size)}
        return None


def setup_from_environment() -> DistributedConfig:
    """Setup config from environment variables.

    Reads from:
    - WORLD_SIZE
    - RANK
    - LOCAL_RANK
    - FSDP_ENABLED
    - DEEPSPEED_ENABLED

    Returns:
        Configured DistributedConfig
    """
    import os

    config = DistributedConfig()

    if "WORLD_SIZE" in os.environ:
        config.world_size = int(os.environ["WORLD_SIZE"])
    if "RANK" in os.environ:
        config.rank = int(os.environ["RANK"])
    if "LOCAL_RANK" in os.environ:
        config.local_rank = int(os.environ["LOCAL_RANK"])

    # Check for GPU
    if torch.cuda.is_available():
        torch.cuda.set_device(config.local_rank)

    return config


def is_available() -> bool:
    """Check if distributed training is available.

    Returns:
        True if GPU(s) available
    """
    return torch.cuda.is_available() or torch.distributed.is_available()
