from perf_takehome import do_kernel_test

# Run standard test with prints
print("Running diagnostic test...")
try:
    # Use a small batch size to limit output
    do_kernel_test(10, 2, 16, prints=True)
except Exception as e:
    print(f"Failed: {e}")
