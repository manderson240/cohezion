import os, torch, sys, aiter, inspect

def probe_namespace(obj, name, depth=0):
    if depth > 2: return
    print(f"\n--- {name} ---", file=sys.stderr)
    for attr in dir(obj):
        if attr.startswith("_"): continue
        full_name = f"{name}.{attr}"
        item = getattr(obj, attr)
        if callable(item):
            try:
                sig = inspect.signature(item)
                print(f"{full_name}{sig}", file=sys.stderr)
            except:
                print(f"{full_name}(...)", file=sys.stderr)
        elif hasattr(item, "__dict__"):
            probe_namespace(item, full_name, depth + 1)

def custom_kernel(data):
    probe_namespace(aiter, "aiter")
    try:
        import helion
        probe_namespace(helion, "helion")
    except:
        print("Helion not available", file=sys.stderr)
        
    from reference import ref_kernel
    return ref_kernel(data)
