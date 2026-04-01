from problem import Input, Tree, build_mem_image


def debug_mem():
    forest = Tree.generate(10)
    inp = Input.generate(forest, 256, 16)
    mem = build_mem_image(forest, inp)
    print(f"Forest nodes: {len(forest.values)}")
    print(f"Batch size: {len(inp.indices)}")
    print(f"Mem size: {len(mem)}")

    header = 7
    forest_values_p = header
    inp_indices_p = forest_values_p + len(forest.values)
    inp_values_p = inp_indices_p + len(inp.indices)
    inp_values_p + len(inp.values)

    print(f"Indices P: {inp_indices_p}")
    print(f"Values P: {inp_values_p}")
    print(
        f"Expected Size: {header + len(forest.values) + len(inp.indices) + len(inp.values) + (len(forest.values) + len(inp.indices) * 2 + 8 * 2 + 32)}"
    )


if __name__ == "__main__":
    debug_mem()
