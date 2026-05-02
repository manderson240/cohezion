import argparse
import os
import sys
from pathlib import Path


# Add project root and challenge dir to path
sys.path.append(os.getcwd())
sys.path.append(str(Path("research/challenges/birdclef-2026")))

try:
    import torch
    from submission import CONFIG, predict
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def test_birdclef_baseline(audio_path, device=None):
    print(f"Testing BirdCLEF baseline with: {audio_path} on {device or 'default device'}")

    # Update config for testing
    config = CONFIG.copy()
    if device:
        config["device"] = device

    # Run prediction
    try:
        results = predict(audio_path, config=config)
        print("Prediction successful!")
        print(f"Number of files processed: {len(results)}")
        for file_id, scores in results.items():
            print(f"File: {file_id}")
            # Show top 5 species
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            print("Top 5 species:")
            for species, score in sorted_scores[:5]:
                print(f"  {species}: {score:.4f}")
    except Exception as e:
        print(f"Prediction failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--audio", type=str, default="data/birdclef-2026/train_audio/1161364/iNat1216197.ogg"
    )
    parser.add_argument("--device", type=str, default=None)
    args = parser.parse_args()

    audio_file = args.audio
    if not Path(audio_file).exists():
        # Try to find any audio file if default doesn't exist
        print(f"Audio file not found: {audio_file}. Searching for alternatives...")
        train_audio_root = Path("data/birdclef-2026/train_audio")
        if train_audio_root.exists():
            found_files = list(train_audio_root.glob("**/*.ogg"))
            if found_files:
                audio_file = str(found_files[0])
                print(f"Using alternative audio: {audio_file}")
            else:
                print("No .ogg files found in data/birdclef-2026/train_audio")
                exit(1)
        else:
            print("data/birdclef-2026/train_audio does not exist")
            exit(1)

    test_birdclef_baseline(audio_file, args.device)
