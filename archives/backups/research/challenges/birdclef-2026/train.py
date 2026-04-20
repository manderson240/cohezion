"""
Training script for BirdCLEF 2026 baseline
"""

import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from tqdm import tqdm

from submission import BirdCLEFModel, BirdCLEFDataset, CONFIG


def train_epoch(model, loader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0

    for batch_x, batch_y in tqdm(loader, desc="Training"):
        batch_x = batch_x.to(device)
        batch_y = batch_y.to(device)

        optimizer.zero_grad()
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    return total_loss / len(loader)


def validate(model, loader, criterion, device):
    """Validate model."""
    model.eval()
    total_loss = 0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch_x, batch_y in tqdm(loader, desc="Validation"):
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)

            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)

            total_loss += loss.item()
            all_preds.append(torch.sigmoid(outputs).cpu().numpy())
            all_labels.append(batch_y.cpu().numpy())

    avg_loss = total_loss / len(loader)
    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)

    # Calculate ROC-AUC per class
    aucs = []
    for i in range(all_labels.shape[1]):
        try:
            auc = roc_auc_score(all_labels[:, i], all_preds[:, i])
            aucs.append(auc)
        except:
            aucs.append(0.5)  # Default for invalid AUC

    avg_auc = np.mean(aucs)

    return avg_loss, avg_auc


def main():
    """Main training function."""
    device = CONFIG["device"]
    print(f"Training on device: {device}")

    # Load metadata
    # Adjust paths based on actual data location
    train_csv = "/kaggle/input/birdclef-2026/train_metadata.csv"

    if not os.path.exists(train_csv):
        print(f"Error: {train_csv} not found. Please update data paths.")
        return

    df = pd.read_csv(train_csv)
    print(f"Loaded {len(df)} training samples")

    # Prepare file paths and labels
    # This is a placeholder - adjust based on actual data format
    audio_paths = [
        f"/kaggle/input/birdclef-2026/train_audio/{row['filename']}" for _, row in df.iterrows()
    ]

    # Create dummy labels (placeholder)
    # In real scenario, load from taxonomy and create multi-hot encoding
    num_classes = CONFIG["num_classes"]
    labels = np.zeros((len(df), num_classes))

    # Cross-validation
    n_splits = 5
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    # Use primary species for stratification
    stratify = np.argmax(labels, axis=1) if labels.sum() > 0 else np.zeros(len(df))

    best_auc = 0

    for fold, (train_idx, val_idx) in enumerate(skf.split(audio_paths, stratify)):
        print(f"\n{'=' * 50}")
        print(f"Fold {fold + 1}/{n_splits}")
        print(f"{'=' * 50}")

        # Create datasets
        train_paths = [audio_paths[i] for i in train_idx]
        val_paths = [audio_paths[i] for i in val_idx]
        train_labels = labels[train_idx]
        val_labels = labels[val_idx]

        train_dataset = BirdCLEFDataset(train_paths, train_labels, config=CONFIG, augment=True)
        val_dataset = BirdCLEFDataset(val_paths, val_labels, config=CONFIG, augment=False)

        train_loader = DataLoader(
            train_dataset,
            batch_size=CONFIG["batch_size"],
            shuffle=True,
            num_workers=2,
            pin_memory=True,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=CONFIG["batch_size"],
            shuffle=False,
            num_workers=2,
            pin_memory=True,
        )

        # Create model
        model = BirdCLEFModel(num_classes=num_classes, pretrained=True)
        model = model.to(device)

        # Loss and optimizer
        criterion = nn.BCEWithLogitsLoss()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="max", factor=0.5, patience=3, verbose=True
        )

        # Training loop
        num_epochs = 20
        best_fold_auc = 0

        for epoch in range(num_epochs):
            print(f"\nEpoch {epoch + 1}/{num_epochs}")

            train_loss = train_epoch(model, train_loader, criterion, optimizer, device)
            val_loss, val_auc = validate(model, val_loader, criterion, device)

            print(
                f"Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val AUC: {val_auc:.4f}"
            )

            # Update learning rate
            scheduler.step(val_auc)

            # Save best model for this fold
            if val_auc > best_fold_auc:
                best_fold_auc = val_auc
                torch.save(model.state_dict(), f"birdclef_model_fold{fold}.pth")
                print(f"Saved best model for fold {fold} (AUC: {val_auc:.4f})")

            # Update global best
            if val_auc > best_auc:
                best_auc = val_auc
                torch.save(model.state_dict(), "birdclef_model_best.pth")
                print(f"New best model overall (AUC: {val_auc:.4f})")

    print(f"\n{'=' * 50}")
    print(f"Training complete! Best AUC: {best_auc:.4f}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
