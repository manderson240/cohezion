from problem import Input, Tree, build_mem_image, reference_kernel2

f = Tree.generate(10)
inp = Input.generate(f, 256, 16)
mem = build_mem_image(f, inp)

print(f"Node 0 value: {f.values[0]}")
print(f"Init hash item 0: {inp.values[0]}")

for i, ref_mem in enumerate(reference_kernel2(mem, {})):
    inp_values_p = ref_mem[6]
    res0 = ref_mem[inp_values_p]
    print(f"Round {i} hash item 0: {res0}")
    if i == 1:
        break
