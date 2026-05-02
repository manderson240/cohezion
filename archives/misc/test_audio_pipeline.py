from pathlib import Path

import librosa
import numpy as np
import torchaudio


def test_audio_pipeline(audio_path):
    print(f"Testing audio pipeline with: {audio_path}")

    # 1. Load with librosa
    try:
        y, sr = librosa.load(audio_path, sr=32000)
        print(f"Librosa load success: shape={y.shape}, sr={sr}")
    except Exception as e:
        print(f"Librosa load failed: {e}")
        return

    # 2. Compute Mel Spectrogram
    try:
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=16000)
        S_dB = librosa.power_to_db(S, ref=np.max)
        print(f"Mel Spectrogram compute success: shape={S_dB.shape}")
    except Exception as e:
        print(f"Mel Spectrogram compute failed: {e}")

    # 3. Load with torchaudio
    try:
        waveform, sample_rate = torchaudio.load(audio_path)
        print(f"Torchaudio load success: shape={waveform.shape}, sr={sample_rate}")
    except Exception as e:
        print(f"Torchaudio load failed: {e}")


if __name__ == "__main__":
    # Use an existing audio file in the repo
    audio_file = "src/web/anima_dashboard/node_modules/gradio/media_assets/audio/sax.wav"
    if not Path(audio_file).exists():
        # Fallback search
        print("Searching for any wav file...")
        import subprocess

        result = subprocess.run(["find", ".", "-name", "*.wav"], capture_output=True, text=True)
        if result.stdout:
            audio_file = result.stdout.splitlines()[0]
        else:
            print("No wav file found!")
            exit(1)

    test_audio_pipeline(audio_file)
