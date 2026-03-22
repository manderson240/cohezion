import problem
import simple_builder


def do_full_verify():
    print("Verifying 16 Rounds Bit-Exact...")
    forest = problem.Tree.generate(10)
    inp = problem.Input.generate(forest, 256, 16)
    mem = problem.build_mem_image(forest, inp)

    cfg = simple_builder.KernelConfig()
    okb = simple_builder.SimpleKernelBuilder(cfg)
    instrs = okb.build_kernel(
        forest.height, len(forest.values), len(inp.indices), 16, problem.HASH_STAGES
    )

    print(f"DEBUG: Rounds={mem[0]}, N_Nodes={mem[1]}, Batch={mem[2]}, Height={mem[3]}")
    print(f"DEBUG: ForestPtr={mem[4]}, IdxPtr={mem[5]}, ValPtr={mem[6]}")
    print(f"DEBUG: Idx[0]={mem[mem[5]]}, Val[0]={mem[mem[6]]}")

    debug = problem.DebugInfo(okb.scratch_names)
    machine = problem.Machine(mem, instrs, debug)

    ref_gen = problem.reference_kernel2(problem.build_mem_image(forest, inp))
    next(ref_gen)  # Initial

    inp_values_p = mem[6]
    inp_indices_p = mem[5]

    machine.run()  # Setup

    for r in range(16):
        machine.run()
        ref_mem = next(ref_gen)

        res_v = machine.mem[inp_values_p : inp_values_p + 256]
        ref_v = ref_mem[inp_values_p : inp_values_p + 256]
        res_i = machine.mem[inp_indices_p : inp_indices_p + 256]
        ref_i = ref_mem[inp_indices_p : inp_indices_p + 256]

        if res_v == ref_v and res_i == ref_i:
            print(f"Round {r} SUCCESS")
        else:
            print(f"Round {r} FAILURE")
            if res_v != ref_v:
                print(f"  Values mismatch at index 0: {res_v[0]} != {ref_v[0]}")
            if res_i != ref_i:
                print(f"  Indices mismatch at index 0: {res_i[0]} != {ref_i[0]}")
            return False

    print("KERNEL FULLY VERIFIED (16 rounds, 256 items)")
    print(f"Total machine cycles: {machine.cycle}")
    return True


if __name__ == "__main__":
    do_full_verify()
