import os
import gc
import json
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from cohezion.models.birdclef_baseline import BirdCLEFBaseline

class BirdDataset(Dataset):
    def __init__(self, df, transform=None):
        self.df = df
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        # Placeholder for real spectrogram loading logic
        # In a real Kaggle kernel, we'd load .ogg or .npy files here
        data = torch.randn(1, 128, 256) # Mock spectrogram
        label = self.df.iloc[idx]['species_id']
        return data, label

def train_baseline():
    print("=== 🦜 BIRDCLEF 2026: BASELINE TRAINING ===")
    
    # Configuration
    BATCH_SIZE = 8 # Reduced for T4 stability
    EPOCHS = 1
    LR = 1e-3
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"Using device: {DEVICE}")
    if torch.cuda.is_available():
        print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
    
    # Load metadata (Mock for local testing, would be /kaggle/input/birdclef-2026/train_metadata.csv)
    # Using dummy data if file not found
    try:
        df = pd.read_csv("/kaggle/input/birdclef-2026/train_metadata.csv")
        num_classes = df['primary_label'].nunique()
        df['species_id'] = pd.factorize(df['primary_label'])[0]
    except:
        print("Kaggle input not found, using dummy metadata.")
        df = pd.DataFrame({'primary_label': ['species_a', 'species_b'], 'species_id': [0, 1]})
        num_classes = 2

    # Initialize model explicitly on device
    model = BirdCLEFBaseline(num_classes=num_classes, pretrained=True).to(DEVICE)
    print(f"Model initialized on {DEVICE}")

    dataset = BirdDataset(df)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    model.train()
    for epoch in range(EPOCHS):
        running_loss = 0.0
        for i, (inputs, labels) in enumerate(loader):
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            if i % 10 == 0:
                print(f"Batch {i} | Loss: {loss.item():.4f}")
                # Artificial limit for baseline verification
                if i > 50: break 

    print("Training finished.")
    torch.save(model.state_dict(), "birdclef_baseline.pth")
    print("Model saved to birdclef_baseline.pth")

if __name__ == "__main__":
    train_baseline()
