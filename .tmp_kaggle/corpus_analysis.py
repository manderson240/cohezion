import pandas as pd

p = "/home/mike-anderson/cohezion-labs/nemotron_v10/corpus_tokenized.parquet"
df = pd.read_parquet(p)
print("rows:", len(df), "cols:", list(df.columns))
print("\n=== category counts ===")
print(df["category"].value_counts().to_string())

MASK = -100


def comp_len(labels):
    return int(sum(1 for t in labels if t != MASK))


df["comp_len"] = df["labels"].apply(comp_len)
df["tot_len"] = df["input_ids"].apply(len)

print("\n=== completion (unmasked) token length stats ===")
print(df["comp_len"].describe().to_string())
print("\n=== completion length by category (mean, sorted) ===")
print(df.groupby("category")["comp_len"].mean().sort_values().to_string())
print("\n=== total seq length stats ===")
print(df["tot_len"].describe().to_string())
