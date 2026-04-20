from anthropic_challenge.optimizer import OptimizedKernelBuilder
from anthropic_challenge.problem import HASH_STAGES, Input, Tree


def debug_asm():
    builder = OptimizedKernelBuilder()

    # Minimal config to trigger Smart Load R0
    instrs = builder.build_kernel(
        forest_height=2,  # Small tree
        n_nodes=7,
        batch_size=256,  # Large batch
        rounds=1,  # Just 1 round
        hash_stages=HASH_STAGES,
    )

    print(f"Generated {len(instrs)} instructions.")
    print("--- FIRST 50 INSTRUCTIONS ---")
    for i, instr in enumerate(instrs[:50]):
        print(f"{i}: {instr}")

    # Execute
    from anthropic_challenge.problem import (
        DebugInfo,
        Machine,
        build_mem_image,
    )

    t = Tree.generate(2)
    t.values[0] = 12345678  # Force known value
    inp = Input.generate(t, 256, 1)
    inp.values = [0xFFFFFFFF] * 256  # Force known input
    inp.indices = [0] * 256

    mem = build_mem_image(t, inp)
    debug_info = DebugInfo(builder.scratch_names)  # Need scratch map?
    # Builder scratch_names is {name: addr}.
    # DebugInfo needs {addr: (name, len)}.
    rev_map = {v: (k, 1) for k, v in builder.scratch_names.items()}
    # Fix vector lengths
    for k in builder.scratch_names:
        if str(k).startswith("v_"):
            rev_map[builder.scratch_names[k]] = (k, 8)

    di = DebugInfo(rev_map)
    machine = Machine(mem, instrs, di, trace=False)
    machine.run()

    # Check mem for update
    print("Starting verification loop...")
    inp_values_p = mem[6]
    # Check all mem values
    # Expected
    val = 0xFFFFFFFF
    node = 12345678
    from anthropic_challenge.problem import myhash

    expected = myhash(val ^ node)

    failed = False
    for i in range(256):
        if i % 50 == 0:
            print(f"Checking {i}...")
        m_val = machine.mem[inp_values_p + i]
        # Recalc expected for this specific item (all same input)
        # val=FFFFFFFF, node=12345678.
        # But wait, input generation sets all to FFFFFFFF.
        if m_val != expected:
            print(f"Mismatch at index {i}: Got {m_val}, Expected {expected}")
            failed = True
            break

    if not failed:
        print("ALL 256 Items Match!")
    print("Done.")


if __name__ == "__main__":
    debug_asm()
