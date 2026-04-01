import optimizer
import simple_builder
from perf_takehome import do_kernel_test

# Configure Builder injection without touching limits
cfg = simple_builder.KernelConfig(modulo_mode=0, smart_load_depth=0)
optimizer.OptimizedKernelBuilder = lambda: simple_builder.SimpleKernelBuilder(cfg)

print("Running STRICT verification (16 rounds, 256 batch)...")
try:
    cycles = do_kernel_test(10, 16, 256, prints=False)
    print(f"STRICT RESULT: {cycles} cycles")
except Exception as e:
    print(f"STRICT FAILURE: {e}")
