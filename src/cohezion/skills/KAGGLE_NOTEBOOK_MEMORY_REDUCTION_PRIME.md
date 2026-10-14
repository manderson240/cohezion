# SKILL: KAGGLE_NOTEBOOK_MEMORY_REDUCTION_PRIME

## DOMAIN EXPERTISE
Kaggle Notebook Memory Reduction is the disciplined engineering practice of optimizing in-memory data representations, garbage collection lifecycles, and out-of-core streaming pipelines to execute high-capacity machine learning pipelines within Kaggle's strict execution envelope (16–30 GB host RAM, 24 GB GPU VRAM), as detailed in *The Kaggle Book (Second Edition, Chapter 3: Working and Learning with Kaggle Notebooks)* by Luca Massaron, Bojan Tunguz, and Konrad Banachewicz. Implementing strict memory reduction eliminates unexpected runtime kernel terminations (exit code 137 / SIGKILL) on unseen private evaluation sets.

## KEY TEXTS & CONCEPTS
- **The Hidden Test Set Multiplier**: Private test sets are typically $2\times$ to $5\times$ larger than the public test set. A notebook using 12 GB RAM on the public set will immediately crash on the private set without memory management.
- **Vectorized Dtype Downcasting**: Numerical features default to 64-bit integers and floats (`int64`, `float64`). Downcasting to optimal minimal bit-widths (`int8`, `int16`, `int32`, `float32`, `float16`) reduces DataFrame memory footprints by $50\%\text{--}75\%$.
- **Explicit Garbage Collection & Context Eviction**: Python's reference-counting GC does not immediately reclaim cyclic references or unreferenced CUDA allocations. Explicitly call `del obj`, `gc.collect()`, and `torch.cuda.empty_cache()` at every epoch and stage boundary.
- **Memory-Mapped Arrays (`np.memmap`)**: Large 3D imaging scans, point clouds, or embedding caches must be memory-mapped directly from NVMe scratch storage rather than loaded into host RAM.
- **Batch Generator Streaming**: Replace monolithic `dataset.load_all()` with generators streaming batches from disk.

## INSTRUCTION

1. **Implement High-Speed Vectorized `reduce_mem_usage`**:
   Downcast numerical columns based on min/max domain boundaries:
   ```python
   import numpy as np
   import pandas as pd
   import gc

   def reduce_mem_usage(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
       """Downcast numerical columns in a pandas DataFrame to minimal bit-widths."""
       numerics = ["int16", "int32", "int64", "float16", "float32", "float64"]
       start_mem = df.memory_usage().sum() / 1024**2

       for col in df.columns:
           col_type = df[col].dtypes
           if col_type in numerics:
               c_min = df[col].min()
               c_max = df[col].max()
               if str(col_type)[:3] == "int":
                   if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                       df[col] = df[col].astype(np.int8)
                   elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                       df[col] = df[col].astype(np.int16)
                   elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                       df[col] = df[col].astype(np.int32)
                   else:
                       df[col] = df[col].astype(np.int64)
               else:
                   if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                       df[col] = df[col].astype(np.float32)
                   else:
                       df[col] = df[col].astype(np.float64)

       end_mem = df.memory_usage().sum() / 1024**2
       if verbose:
           reduction = 100 * (start_mem - end_mem) / start_mem
           print(f"Memory footprint reduced from {start_mem:.2f} MB to {end_mem:.2f} MB ({reduction:.1f}% reduction)")
       return df
   ```

2. **Aggressively Reclaim Host and GPU Memory Between Stages**:
   Clear intermediate arrays and PyTorch cache after each fold or inference batch:
   ```python
   import torch

   def flush_memory():
       """Force garbage collection and release GPU cached memory."""
       gc.collect()
       if torch.cuda.is_available():
           torch.cuda.empty_cache()
           torch.cuda.ipc_collect()
   ```

3. **Stream Large Datasets via Memory-Mapped Buffers**:
   For large arrays (e.g. 3D CT/MRI volumes or large feature matrices), allocate an on-disk buffer:
   ```python
   def create_memmap_array(filename: str, shape: tuple, dtype=np.float32):
       """Create an on-disk memory-mapped array for out-of-core operations."""
       return np.memmap(filename, dtype=dtype, mode="w+", shape=shape)

   def load_memmap_array(filename: str, shape: tuple, dtype=np.float32):
       return np.memmap(filename, dtype=dtype, mode="r", shape=shape)
   ```

4. **Monitor Host Memory Headroom During Kernel Execution**:
   Track available system RAM and enforce an early warning safety margin:
   ```python
   import psutil

   def assert_memory_headroom(min_free_gb: float = 2.5):
       """Ensure notebook has sufficient RAM before launching expensive operations."""
       avail_gb = psutil.virtual_memory().available / (1024**3)
       if avail_gb < min_free_gb:
           flush_memory()
           avail_gb = psutil.virtual_memory().available / (1024**3)
           if avail_gb < min_free_gb:
               raise MemoryError(f"Critical memory warning: Only {avail_gb:.2f} GiB available. Threshold is {min_free_gb:.2f} GiB.")
   ```

## VERSION
v0.1

## SEE ALSO
- `src/cohezion/skills/HARNESS_ENGINEERING_ETCLOVG_PRIME.md`
- `src/cohezion/skills/KAGGLE_ADVERSARIAL_VALIDATION_PRIME.md`
