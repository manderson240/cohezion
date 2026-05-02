import quimb.tensor as qtn


print("Inspecting qtn.Circuit:")
try:
    print(f"Has from_qasm_file: {hasattr(qtn.Circuit, 'from_qasm_file')}")
    print(f"Has from_qsim_file: {hasattr(qtn.Circuit, 'from_qsim_file')}")

    # Try to call it
    try:
        # Dummy call to see signature or failure
        # We expect it to fail with file not found if it works, or TypeError if broken
        qtn.Circuit.from_qasm_file("nonexistent.qasm")
    except Exception as e:
        print(f"Call Result: {type(e).__name__}: {e}")

    # Inspect the attribute
    attr = getattr(qtn.Circuit, "from_qasm_file", None)
    print(f"Attribute type: {type(attr)}")
    if attr:
        print(f"Attribute dir: {dir(attr)}")

except Exception as e:
    print(f"Outer Error: {e}")
