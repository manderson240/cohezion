"""
BirdCLEF 2026 Baseline Submission
Transfer learning with EfficientNet-B0 on mel spectrograms
"""

import os
import json
import librosa
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.models as models
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuration
CONFIG = {
    'sample_rate': 32000,
    'duration': 5.0,
    'n_mels': 128,
    'n_fft': 2048,
    'hop_length': 512,
    'f_min': 50,
    'f_max': 16000,
    'batch_size': 32,
    'num_classes': 97,  # Pantanal species count (adjust based on actual data)
    'device': 'cuda' if torch.cuda.is_available() else 'cpu'
}


class AudioAugmenter:
    """Data augmentation for audio spectrograms."""

    @staticmethod
    def time_stretch(audio, rate_range=(0.8, 1.25)):
        """Random time stretching."""
        rate = np.random.uniform(*rate_range)
        try:
            stretched = librosa.effects.time_stretch(audio, rate=rate)
            # Pad or trim to original length
            if len(stretched) > len(audio):
                stretched = stretched[:len(audio)]
            else:
                stretched = np.pad(stretched, (0, len(audio) - len(stretched)))
            return stretched
        except:
            return audio

    @staticmethod
    def pitch_shift(audio, sr, n_steps_range=(-2, 2)):
        """Random pitch shifting."""
        n_steps = np.random.uniform(*n_steps_range)
        try:
            return librosa.effects.pitch_shift(audio, sr=sr, n_steps=n_steps)
        except:
            return audio

    @staticmethod
    def add_noise(audio, noise_factor_range=(0.001, 0.01)):
        """Add random background noise."""
        noise_factor = np.random.uniform(*noise_factor_range)
        noise = np.random.randn(len(audio))
        return audio + noise_factor * noise

    @staticmethod
    def spec_mask(mel_spec, freq_mask_param=20, time_mask_param=20):
        """Spectrogram masking (SpecAugment)."""
        spec = mel_spec.copy()

        # Frequency masking
        if np.random.random() < 0.5:
            num_mel_channels = spec.shape[0]
            f = np.random.randint(0, freq_mask_param)
            f0 = np.random.randint(0, max(1, num_mel_channels - f))
            spec[f0:f0+f, :] = 0

        # Time masking
        if np.random.random() < 0.5:
            len_spectro = spec.shape[1]
            t = np.random.randint(0, time_mask_param)
            t0 = np.random.randint(0, max(1, len_spectro - t))
            spec[:, t0:t0+t] = 0

        return spec


def compute_mel_spectrogram(audio, sr, config):
    """Compute mel spectrogram features."""
    mel_spec = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_fft=config['n_fft'],
        hop_length=config['hop_length'],
        n_mels=config['n_mels'],
        fmin=config['f_min'],
        fmax=config['f_max']
    )
    # Convert to log scale (dB)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    return mel_spec_db


def spectrogram_to_image(mel_spec):
    """Convert mel spectrogram to 3-channel image for CNN."""
    # Normalize to [0, 1]
    spec_norm = (mel_spec - mel_spec.min()) / (mel_spec.max() - mel_spec.min() + 1e-8)

    # Resize to 224x224 for EfficientNet
    from scipy.ndimage import zoom
    h, w = spec_norm.shape
    zoom_h = 224 / h
    zoom_w = 224 / w
    spec_resized = zoom(spec_norm, (zoom_h, zoom_w), order=1)

    # Convert to 3-channel RGB
    spec_rgb = np.stack([spec_resized] * 3, axis=0)
    return spec_rgb.astype(np.float32)


class BirdCLEFDataset(Dataset):
    """Dataset for BirdCLEF audio files."""

    def __init__(self, audio_paths, labels=None, config=None, augment=False):
        self.audio_paths = audio_paths
        self.labels = labels
        self.config = config or CONFIG
        self.augment = augment
        self.augmenter = AudioAugmenter() if augment else None

    def __len__(self):
        return len(self.audio_paths)

    def __getitem__(self, idx):
        # Load audio
        audio_path = self.audio_paths[idx]
        try:
            audio, sr = librosa.load(audio_path, sr=self.config['sample_rate'], duration=self.config['duration'])
        except:
            # Return zeros if file can't be loaded
            audio = np.zeros(int(self.config['sample_rate'] * self.config['duration']))
            sr = self.config['sample_rate']

        # Pad or trim to fixed duration
        target_len = int(self.config['sample_rate'] * self.config['duration'])
        if len(audio) < target_len:
            audio = np.pad(audio, (0, target_len - len(audio)))
        else:
            audio = audio[:target_len]

        # Augmentations
        if self.augment and self.augmenter:
            if np.random.random() < 0.5:
                audio = self.augmenter.time_stretch(audio)
            if np.random.random() < 0.5:
                audio = self.augmenter.pitch_shift(audio, sr)
            if np.random.random() < 0.5:
                audio = self.augmenter.add_noise(audio)

        # Compute mel spectrogram
        mel_spec = compute_mel_spectrogram(audio, sr, self.config)

        # Spec augmentation
        if self.augment and self.augmenter:
            mel_spec = self.augmenter.spec_mask(mel_spec)

        # Convert to image format
        spec_img = spectrogram_to_image(mel_spec)

        if self.labels is not None:
            return torch.FloatTensor(spec_img), torch.FloatTensor(self.labels[idx])
        return torch.FloatTensor(spec_img)


class BirdCLEFModel(nn.Module):
    """EfficientNet-based bird sound classifier."""

    def __init__(self, num_classes=97, pretrained=True):
        super().__init__()

        # Load EfficientNet-B0
        weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = models.efficientnet_b0(weights=weights)

        # Replace classifier
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)


def predict(test_audio_path, model_path=None, config=None):
    """
    Main prediction function for Kaggle submission.

    Args:
        test_audio_path: Path to test audio file or directory
        model_path: Path to trained model weights
        config: Configuration dict

    Returns:
        Dictionary mapping file names to probability arrays
    """
    config = config or CONFIG
    device = config['device']

    # Load model
    model = BirdCLEFModel(num_classes=config['num_classes'], pretrained=False)
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

    # Species list (placeholder - will be loaded from taxonomy file in real scenario)
    species_codes = [f'species_{i:03d}' for i in range(config['num_classes'])]

    results = {}

    with torch.no_grad():
        for audio_file in test_files:
            # Create dataset with single file
            dataset = BirdCLEFDataset([str(audio_file)], config=config, augment=False)
            loader = DataLoader(dataset, batch_size=1, shuffle=False)

            # Get prediction
            for batch in loader:
                batch = batch.to(device)
                logits = model(batch)
                probs = torch.sigmoid(logits).cpu().numpy()[0]  # Multi-label
                break

            # Store results
            file_id = audio_file.stem
            results[file_id] = {species: float(prob) for species, prob in zip(species_codes, probs)}

    return results


def predict_batch(test_audio_paths, model_path=None, config=None):
    """
    Batch prediction for multiple files.

    Args:
        test_audio_paths: List of audio file paths
        model_path: Path to trained model weights
        config: Configuration dict

    Returns:
        List of probability arrays
    """
    config = config or CONFIG
    device = config['device']

    # Load model
    model = BirdCLEFModel(num_classes=config['num_classes'], pretrained=False)
    if model_path and os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()

    # Create dataset
    dataset = BirdCLEFDataset(test_audio_paths, config=config, augment=False)
    loader = DataLoader(dataset, batch_size=config['batch_size'], shuffle=False, num_workers=0)

    all_probs = []

    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits = model(batch)
            probs = torch.sigmoid(logits).cpu().numpy()
            all_probs.extend(probs)

    return all_probs


# Kaggle-specific inference code
def inference(test_df, model_path='birdclef_model.pth'):
    """
    Kaggle inference function.

    Args:
        test_df: DataFrame with 'filename' column
        model_path: Path to model weights

    Returns:
        DataFrame with predictions
    """
    import pandas as pd

    predictions = []
    model = BirdCLEFModel(num_classes=CONFIG['num_classes'], pretrained=False)

    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=CONFIG['device']))

    model.to(CONFIG['device'])
    model.eval()

    # Load taxonomy
    taxonomy_path = '/kaggle/input/birdclef-2026/taxonomy.json'
    if os.path.exists(taxonomy_path):
        with open(taxonomy_path) as f:
            taxonomy = json.load(f)
        species_codes = [item['primary_code'] for item in taxonomy]
    else:
        species_codes = [f'species_{i:03d}' for i in range(CONFIG['num_classes'])]

    with torch.no_grad():
        for _, row in test_df.iterrows():
            filepath = f"/kaggle/input/birdclef-2026/test_soundscapes/{row['filename']}"

            if not os.path.exists(filepath):
                # Return zeros if file not found
                preds = {code: 0.0 for code in species_codes}
                predictions.append(preds)
                continue

            # Load and predict
            dataset = BirdCLEFDataset([filepath], config=CONFIG, augment=False)
            loader = DataLoader(dataset, batch_size=1, shuffle=False)

            for batch in loader:
                batch = batch.to(CONFIG['device'])
                logits = model(batch)
                probs = torch.sigmoid(logits).cpu().numpy()[0]
                preds = {code: float(prob) for code, prob in zip(species_codes, probs)}
                predictions.append(preds)
                break

    # Convert to DataFrame
    pred_df = pd.DataFrame(predictions)
    result = pd.concat([test_df[['filename']], pred_df], axis=1)

    return result


if __name__ == '__main__':
    print("BirdCLEF 2026 Baseline Submission")
    print(f"Device: {CONFIG['device']}")
    print(f"Number of classes: {CONFIG['num_classes']}")

    # Test with dummy data
    print("\nTesting prediction function...")
    dummy_path = "/tmp/test_audio.wav"
    if not os.path.exists(dummy_path):
        # Create dummy audio file for testing
        dummy_audio = np.random.randn(CONFIG['sample_rate'] * 5).astype(np.float32)
        import soundfile as sf
        sf.write(dummy_path, dummy_audio, CONFIG['sample_rate'])

    results = predict(dummy_path)
    print(f"Prediction keys: {list(results.keys())}")
    print(f"Number of species probabilities: {len(list(results.values())[0])}")
