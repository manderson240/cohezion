#!/usr/bin/env python3
"""RSNA Knee Abnormality Detection: 5-Fold Multilabel Stratified Split Generator.

Generates data/rsna/rsna_5folds.csv ensuring:
1. Ground truth labels (from train.csv) are prioritized for the 58 verified studies.
2. LLM-extracted labels (from report_labels_v2.csv) provide comprehensive multi-label targets for all 4,406 studies.
3. MultilabelStratifiedKFold ensures identical prevalence across all 12 target injury conditions across folds.
4. Ground-truth studies are evenly partitioned across all 5 folds.
"""

import os
import numpy as np
import pandas as pd
from iterstrat.ml_stratifiers import MultilabelStratifiedKFold

LABELS = [
    "ACL",
    "MCL",
    "Medial Meniscus",
    "Lateral Meniscus",
    "Medial OA",
    "Lateral OA",
    "PF OA",
    "Effusion",
    "Synovitis",
    "Baker's",
    "Contusion",
    "Fracture",
]

def generate_5fold_split():
    train_path = "data/rsna/train.csv"
    llm_path = "data/rsna/llm_labels/report_labels_v2.csv"
    out_path = "data/rsna/rsna_5folds.csv"
    
    if not os.path.exists(train_path) or not os.path.exists(llm_path):
        raise FileNotFoundError(f"Missing train data or LLM labels: {train_path}, {llm_path}")

    df_train = pd.read_csv(train_path)
    df_llm = pd.read_csv(llm_path)
    
    # Base dataframe on train.csv (4,407 studies)
    merged = pd.merge(df_train[["StudyInstanceUID", "Report"]], df_llm, on="StudyInstanceUID", how="left")
    
    # Mark which rows have official ground-truth labels
    merged["is_ground_truth"] = df_train["ACL"].notnull().astype(int)
    
    # Overwrite with official ground truth where present
    for col in LABELS:
        gt_vals = df_train[col]
        merged.loc[df_train[col].notnull(), col] = gt_vals[df_train[col].notnull()]
        # Binarize to 0/1 (any value >= 0.5 is positive)
        merged[col] = (merged[col] >= 0.5).astype(int)
        
    print(f"Total merged studies: {len(merged)}")
    print(f"Ground truth studies: {merged['is_ground_truth'].sum()}")
    
    # Stratify separately or jointly:
    # First, stratify ground truth studies across 5 folds
    mskf = MultilabelStratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    merged["fold"] = -1
    
    gt_mask = merged["is_ground_truth"] == 1
    gt_indices = merged[gt_mask].index.values
    gt_targets = merged.loc[gt_mask, LABELS].values
    
    for fold_idx, (_, val_idx) in enumerate(mskf.split(gt_indices, gt_targets)):
        merged.loc[gt_indices[val_idx], "fold"] = fold_idx
        
    # Second, stratify the remaining ~4,348 LLM-labeled studies across 5 folds
    pseudo_mask = merged["is_ground_truth"] == 0
    pseudo_indices = merged[pseudo_mask].index.values
    pseudo_targets = merged.loc[pseudo_mask, LABELS].values
    
    for fold_idx, (_, val_idx) in enumerate(mskf.split(pseudo_indices, pseudo_targets)):
        merged.loc[pseudo_indices[val_idx], "fold"] = fold_idx
        
    # Verify stratification balance
    print("\n--- FOLD STRATIFICATION VERIFICATION ---")
    fold_counts = merged["fold"].value_counts().sort_index()
    print("Studies per fold:\n", fold_counts)
    
    gt_counts = merged[merged["is_ground_truth"] == 1]["fold"].value_counts().sort_index()
    print("\nGround truth per fold:\n", gt_counts)
    
    print("\nLabel prevalence per fold:")
    summary = []
    for f in range(5):
        fold_df = merged[merged["fold"] == f]
        row = {"fold": f, "total": len(fold_df)}
        for col in LABELS:
            row[col] = fold_df[col].mean()
        summary.append(row)
        
    summary_df = pd.DataFrame(summary)
    print(summary_df.to_string(index=False))
    
    # Save folds to CSV
    save_cols = ["StudyInstanceUID", "fold", "is_ground_truth"] + LABELS
    merged[save_cols].to_csv(out_path, index=False)
    print(f"\n✓ Successfully written 5-fold stratification to {out_path} ({len(merged)} rows)")

if __name__ == "__main__":
    generate_5fold_split()
