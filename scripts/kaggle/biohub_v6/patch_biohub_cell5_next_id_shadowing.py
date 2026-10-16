import json
from pathlib import Path

nb_path = Path("scripts/kaggle/biohub_v6/cohezion-biohub-v6.ipynb")
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

cell5_src = nb["cells"][5]["source"]
if isinstance(cell5_src, list):
    cell5_str = "".join(cell5_src)
else:
    cell5_str = cell5_src

# Replace the two occurrences of successor next_id shadowing
old_block_1 = """                next_id = successor.get(target_id)
                if next_id is not None:
                    p_next = _position_um(nodes_by_id[next_id])
                    next_step = p_next - p_tgt
                    next_norm = float(np.linalg.norm(next_step))
                    if next_norm > 0.05 and gap_norm > 0.05:
                        cos_next = float(np.dot(gap_step, next_step) / (gap_norm * next_norm))
                        if cos_next < 0.40:
                            ok_direction = False"""

new_block_1 = """                succ_id = successor.get(target_id)
                if succ_id is not None:
                    p_next = _position_um(nodes_by_id[succ_id])
                    next_step = p_next - p_tgt
                    next_norm = float(np.linalg.norm(next_step))
                    if next_norm > 0.05 and gap_norm > 0.05:
                        cos_next = float(np.dot(gap_step, next_step) / (gap_norm * next_norm))
                        if cos_next < 0.40:
                            ok_direction = False"""

count = cell5_str.count(old_block_1)
print(f"Found {count} occurrences of old_block_1 in Cell 5.")

if count > 0:
    cell5_str = cell5_str.replace(old_block_1, new_block_1)
    print("✓ Successfully replaced all occurrences of successor next_id shadowing.")
else:
    # Individual line replacement fallback
    cell5_str = cell5_str.replace("next_id = successor.get(target_id)", "succ_id = successor.get(target_id)")
    cell5_str = cell5_str.replace("if next_id is not None:\n                    p_next = _position_um(nodes_by_id[next_id])", "if succ_id is not None:\n                    p_next = _position_um(nodes_by_id[succ_id])")
    print("✓ Replaced with fallback line replacement.")

nb["cells"][5]["source"] = [line + "\n" for line in cell5_str.splitlines()]

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("✓ Saved updated cohezion-biohub-v6.ipynb with clean next_id counter.")
