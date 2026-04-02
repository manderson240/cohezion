"""
BirdCLEF 2026 AST Baseline Submission
Using Audio Spectrogram Transformer (AST) for improved bioacoustic classification.
"""

import os
import json
import librosa
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from transformers import ASTFeatureExtractor, ASTForAudioClassification, ASTConfig
import warnings
warnings.filterwarnings('ignore')

# Configuration
CONFIG = {
    'sample_rate': 16000, # AST expects 16kHz
    'duration': 5.0,
    'batch_size': 16,
    'num_classes': 207, # Based on train.csv unique primary_labels
    'model_name': "MIT/ast-finetuned-audioset-10-10-0.4593",
    'device': 'cuda' if torch.cuda.is_available() else 'cpu'
}

class BirdCLEFDataset(Dataset):
    """Dataset for BirdCLEF audio files using AST Feature Extractor."""

    def __init__(self, audio_paths, feature_extractor, labels=None, config=None):
        self.audio_paths = audio_paths
        self.labels = labels
        self.config = config or CONFIG
        self.feature_extractor = feature_extractor

    def __len__(self):
        return len(self.audio_paths)

    def __getitem__(self, idx):
        # Load audio
        audio_path = self.audio_paths[idx]
        try:
            # Resample to 16kHz for AST
            audio, sr = librosa.load(audio_path, sr=self.config['sample_rate'], duration=self.config['duration'])
        except:
            audio = np.zeros(int(self.config['sample_rate'] * self.config['duration']))
            sr = self.config['sample_rate']

        # Pad or trim
        target_len = int(self.config['sample_rate'] * self.config['duration'])
        if len(audio) < target_len:
            audio = np.pad(audio, (0, target_len - len(audio)))
        else:
            audio = audio[:target_len]

        # AST Preprocessing
        inputs = self.feature_extractor(audio, sampling_rate=sr, return_tensors="pt")
        # remove batch dim
        input_values = inputs.input_values.squeeze(0)

        if self.labels is not None:
            return input_values, torch.FloatTensor(self.labels[idx])
        return input_values

class BirdASTModel(nn.Module):
    """AST-based bird sound classifier."""

    def __init__(self, ast_model, num_classes=207):
        super().__init__()
        # Use provided pre-loaded AST
        self.ast = ast_model
        
        # Replace the classifier head
        # AST has a 'classifier' attribute which is a Dense layer
        in_features = self.ast.classifier.dense.in_features
        self.ast.classifier.dense = nn.Linear(in_features, num_classes)
        # Remove original out_proj if any or just rely on the new dense layer
        # Transformers classification head is usually more complex, but we will keep it simple.

    def forward(self, x):
        # x shape: [batch, 1024, 128]
        return self.ast(x).logits

def predict(test_audio_path, model_path=None, config=None):
    config = config or CONFIG
    device = config['device']

    # Load components once
    print(f"Loading pre-trained AST components from {config['model_name']}...")
    feature_extractor = ASTFeatureExtractor.from_pretrained(config['model_name'])
    ast_base = ASTForAudioClassification.from_pretrained(config['model_name'])

    # Load model
    model = BirdASTModel(ast_base, num_classes=config['num_classes'])
    if model_path and os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()

    # Get test files
    test_path = Path(test_audio_path)
    if test_path.is_dir():
        test_files = list(test_path.glob('*.ogg')) + list(test_path.glob('*.wav')) + list(test_path.glob('*.mp3'))
    else:
        test_files = [test_path]

    # Species list
    species_codes = [f'species_{i:03d}' for i in range(config['num_classes'])]

    results = {}

    with torch.no_grad():
        for audio_file in test_files:
            dataset = BirdCLEFDataset([str(audio_file)], feature_extractor, config=config)
            loader = DataLoader(dataset, batch_size=1, shuffle=False)

            for batch in loader:
                batch = batch.to(device)
                logits = model(batch)
                probs = torch.sigmoid(logits).cpu().numpy()[0]
                break

            file_id = audio_file.stem
            results[file_id] = {species: float(prob) for species, prob in zip(species_codes, probs)}

    return results

if __name__ == '__main__':
    print("BirdCLEF 2026 AST Baseline")
    print(f"Device: {CONFIG['device']}")
    
    # Simple check
    print(f"Loading pre-trained AST components from {CONFIG['model_name']}...")
    feature_extractor = ASTFeatureExtractor.from_pretrained(CONFIG['model_name'])
    ast_base = ASTForAudioClassification.from_pretrained(CONFIG['model_name'])
    
    model = BirdASTModel(ast_base, num_classes=CONFIG['num_classes'])
    print("Model initialized successfully.")
    
    # Test with dummy data
    dummy_input = torch.randn(1, 1024, 128).to(CONFIG['device'])
    with torch.no_grad():
        model.to(CONFIG['device'])
        output = model(dummy_input)
        print(f"Forward pass successful! Output shape: {output.shape}")
