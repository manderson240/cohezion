"""Silence third-party library C-extension warnings on ROCm / Strix Halo."""
import logging
import os
import warnings

# Force torchao to skip SO files on PyTorch ROCm
os.environ["TORCHAO_FORCE_SKIP_LOADING_SO_FILES"] = "1"

# Silence torchao's warning logger
logging.getLogger("torchao").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", module="torchao")
