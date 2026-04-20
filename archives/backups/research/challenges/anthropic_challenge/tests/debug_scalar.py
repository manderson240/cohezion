# Monkey patch the builder to use N_SCAL=0
def test_n_scal_0():
    print("Testing with N_SCAL=0 (Pure Vector)...")

    # We need to edit the source or mock the class?
    # Optimizer defines N_SCAL inside build_kernel.
    # Hard to patch local variable.
    # But we can patch the file content using sed or just string replace in memory if we loaded it?
    # No, let's just use the file tools to edit optimizer.py to N_SCAL=0, run test, then revert?
    # Or cleaner: Modify optimizer.py to accept N_SCAL as arg?
    pass


if __name__ == "__main__":
    # We will simply execute the test.
    # The agent will use tools to modify the file.
    pass
