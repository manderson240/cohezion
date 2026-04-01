# BirdCLEF 2026 Baseline Submission

**Competition:** BirdCLEF 2026 (Audio Classification)
**Dataset:** Pantanal wetland bird recordings
**Metric:** ROC-AUC (multi-label)
**Model:** EfficientNet-B0 with Transfer Learning

---

## Baseline Model Selection

### Model: EfficientNet-B0

**Rationale:**
- **Transfer Learning**: Pre-trained on ImageNet (1.28M images, 1000 classes)
- **Efficiency**: B0 variant provides best speed/accuracy trade-off
- **Mel Spectrogram Input**: Audio converted to 224x224 spectrogram images
- **Multi-label**: Sigmoid activation for multi-species detection

**Architecture:**
```
Input Audio (5s @ 32kHz)
    ↓
Mel Spectrogram (128 bins, 50-16kHz)
    ↓
Log scaling + Resize to 224x224
    ↓
3-channel Image (duplicated spectrogram)
    ↓
EfficientNet-B0 Backbone
    ↓
Custom Classifier (512 hidden + dropout)
    ↓
97-way Sigmoid Output
```

---

## Data Augmentation

### Audio Augmentations (Time Domain)
1. **Time Stretching**: 0.8x - 1.25x random stretch
2. **Pitch Shifting**: ±2 semitones random shift
3. **Noise Injection**: Random background noise (0.1-1% amplitude)

### Spectrogram Augmentations (SpecAugment)
1. **Frequency Masking**: Random vertical band masking (max 20 bins)
2. **Time Masking**: Random horizontal band masking (max 20 frames)

---

## Configuration

| Parameter | Value |
|-----------|-------|
| Sample Rate | 32,000 Hz |
| Duration | 5 seconds |
| Mel Bins | 128 |
| FFT Size | 2,048 |
| Hop Length | 512 |
| Frequency Range | 50 Hz - 16,000 Hz |
| Batch Size | 32 |
| Image Size | 224x224 |

---

## Files Created

| File | Purpose |
|------|---------|
| `submission.py` | Main inference script with `predict()` function |
| `kernel-metadata.json` | Kaggle kernel configuration |
| `requirements.txt` | Python dependencies |
| `README.md` | This documentation |

---

## Usage

### Local Testing
```python
from submission import predict

# Single file prediction
results = predict("path/to/audio.wav")
print(results)  # Dict of species probabilities

# Batch prediction
from submission import predict_batch
probs = predict_batch(["file1.wav", "file2.wav"])
```

### Kaggle Submission
```python
import pandas as pd
from submission import inference

# Load test metadata
test_df = pd.read_csv("/kaggle/input/birdclef-2026/test.csv")

# Run inference
submission = inference(test_df, model_path="birdclef_model.pth")
submission.to_csv("submission.csv", index=False)
```

---

## Expected Performance

| Metric | Expected Range | Notes |
|--------|----------------|-------|
| ROC-AUC | 0.70 - 0.85 | Baseline without hyperparameter tuning |
| Inference Time | ~50ms/file | On GPU (T4) |
| Model Size | ~5.3 MB | EfficientNet-B0 weights |

---

## Validation Strategy

**Recommended:**
- **Stratified K-Fold**: 5 folds with stratification by primary species
- **Time-based Split**: Separate early/late recordings
- **Recording Site Stratification**: Prevent site leakage

**Note:** Local validation ROC-AUC requires downloading the competition dataset.

---

## Ready for Kaggle Submission

**Status: YES** (with model weights)

### Prerequisites for Submission:
1. **Train the model** on BirdCLEF 2026 training data
2. **Save weights** as `birdclef_model.pth`
3. **Upload model** to Kaggle Datasets
4. **Update kernel-metadata.json** with dataset reference

### Quick Training Template:
```python
import torch
from submission import BirdCLEFModel, BirdCLEFDataset, CONFIG

# Create model
model = BirdCLEFModel(num_classes=97, pretrained=True)

# Training loop (standard PyTorch)
# ...

# Save weights
torch.save(model.state_dict(), "birdclef_model.pth")
```

---

## Improvements to Explore

1. **Better Backbone**: EfficientNet-B3/B4, ResNeXt, ConvNeXt
2. **Audio Embeddings**: Use BirdNET embeddings instead of raw spectrograms
3. **Ensembling**: Multi-fold + multi-model averaging
4. **Test-Time Augmentation**: Multi-view inference
5. **Class Imbalance**: Weighted loss or focal loss
6. **Long Audio**: Sliding window with vote aggregation

---

## References

- [BirdCLEF Competition Page](https://www.kaggle.com/competitions/birdclef-2026)
- [EfficientNet Paper](https://arxiv.org/abs/1905.11946)
- [SpecAugment Paper](https://arxiv.org/abs/1904.08779)
- [BirdNET Model](https://github.com/kahst/BirdNET)
