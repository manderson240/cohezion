from problem import N_CORES
from tests.submission_tests import cycles

print(f"Environment N_CORES: {N_CORES}")
loops = cycles()
print(f"Cycles: {loops}")
if hasattr(loops, "cores"):
    print(f"TRACE CORE 1: {loops.cores[1].trace_buf}")
