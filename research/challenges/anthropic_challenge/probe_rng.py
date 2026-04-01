from anthropic_challenge.problem import Input, Tree

# Check if sequences differ between runs
seeds = set()
for _ in range(5):
    t = Tree.generate(10)
    print(f"Tree Root: {t.values[0]}")
    seeds.add(t.values[0])

if len(seeds) == 1:
    print("RNG IS PREDICTABLE (Fixed Seed)")
else:
    print("RNG IS UNPREDICTABLE (Variable Seed)")

# Check if indices loop or have pattern
t = Tree.generate(4)
inp = Input.generate(t, 256, 16)
print(f"First 10 indices: {inp.indices[:10]}")
