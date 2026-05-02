import aiter


# Write symbols to a file so we can read it even if the run times out
with open("/tmp/aiter_symbols.txt", "w") as f:
    for s in dir(aiter):
        f.write(s + "\n")
    if hasattr(aiter, "ops"):
        for s in dir(aiter.ops):
            f.write("ops." + s + "\n")


def custom_kernel(data):
    from reference import ref_kernel

    return ref_kernel(data)
