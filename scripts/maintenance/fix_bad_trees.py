import subprocess


def fix_tree(tree_sha):
    print(f"Attempting to fix tree: {tree_sha}")
    try:
        # Get raw tree content
        raw = subprocess.check_output(["git", "cat-file", "tree", tree_sha])

        # Git tree format: [mode] [name]\0[sha]
        # We need to parse this and find entries with empty names
        fixed_entries = []
        i = 0
        while i < len(raw):
            # Find mode and name
            null_idx = raw.find(b"\0", i)
            if null_idx == -1:
                break

            entry_info = raw[i:null_idx]
            mode, name = entry_info.split(b" ", 1)

            # Find SHA (20 bytes after \0)
            sha = raw[null_idx + 1 : null_idx + 21]

            if name:
                fixed_entries.append((mode, name, sha))
            else:
                print(f"  Stripping empty filename entry at offset {i}")

            i = null_idx + 21

        # Reconstruct the tree
        if not fixed_entries:
            print("  No valid entries found!")
            return None

        # Use git mktree to create a new tree object
        input_str = b"".join(
            [
                mode + b" " + b"blob" + b" " + sha.hex().encode() + b"\t" + name + b"\n"
                for mode, name, sha in fixed_entries
            ]
        )
        # Wait, mktree format is: <mode> <type> <sha>\t<file>
        # We need to determine if it's a blob or tree from the mode
        input_lines = []
        for mode, name, sha in fixed_entries:
            m = mode.decode()
            t = "tree" if m.startswith("04") else "blob"
            input_lines.append(f"{m} {t} {sha.hex()}\t{name.decode()}")

        mktree_input = "\n".join(input_lines) + "\n"
        new_tree_sha = (
            subprocess.check_output(["git", "mktree"], input=mktree_input.encode()).decode().strip()
        )
        print(f"  Fixed tree: {new_tree_sha}")
        return new_tree_sha
    except Exception as e:
        print(f"  Error fixing tree: {e}")
        return None


# Find bad trees from fsck
print("Finding bad trees from git fsck...")
try:
    fsck_output = subprocess.check_output(["git", "fsck"], stderr=subprocess.STDOUT).decode()
except subprocess.CalledProcessError as e:
    fsck_output = e.output.decode()

bad_trees = []
for line in fsck_output.splitlines():
    if "error in tree" in line:
        sha = line.split("tree ")[1].split(":")[0]
        bad_trees.append(sha)

print(f"Found {len(bad_trees)} bad trees.")

replacements = []
for tree in bad_trees:
    fixed = fix_tree(tree)
    if fixed:
        replacements.append((tree, fixed))

if replacements:
    print("\nApplying replacements...")
    for old, new in replacements:
        subprocess.call(["git", "replace", old, new])
    print("Done. Standard git tools should now work (traversing through replacements).")
else:
    print("\nNo trees could be fixed.")
