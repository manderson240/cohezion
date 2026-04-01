import sys
import os
from pathlib import Path

# Add project root and challenge dir to path
sys.path.append(os.getcwd())
sys.path.append(str(Path("research/challenges/birdclef-2026")))

import torch
from submission import predict, CONFIG

def test_birdclef_baseline(audio_path):
    print(f"Testing BirdCLEF baseline with: {audio_path}")
    
    # Update config for testing (97 classes in baseline script)
    # The actual competition might have more, but we'll use the baseline value for now.
    
    # Run prediction
    try:
        results = predict(audio_path)
        print(f"Prediction successful!")
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
    audio_file = "data/birdclef-2026/train_audio/1161364/iNat1216197.ogg"
    if not Path(audio_file).exists():
        print(f"Audio file not found: {audio_file}")
        exit(1)
        
    test_birdclef_baseline(audio_file)
