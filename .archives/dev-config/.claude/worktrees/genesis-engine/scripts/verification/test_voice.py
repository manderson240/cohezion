import os

import soundfile as sf
from pocket_tts import TTSModel
from pocket_tts.modules.stateful_module import init_states


def test_voice():
    print("🎙️ Testing PocketTTS Sovereign Voice...")

    try:
        # Load model using classmethod
        print("Loading weights...")
        model = TTSModel.load_model()

        # Initialize state
        print("Initializing model state...")
        # flow_lm batch_size=1, sequence_length=1000 (standard for generate_audio)
        model_state = init_states(model.flow_lm, batch_size=1, sequence_length=1000)

        text = "Cohezion sovereign narrative initialized. I am Architect Prime, navigating the 512-D latent manifold."

        # Generate audio
        print(f"Generating audio for: '{text}'")
        audio = model.generate_audio(model_state, text)

        # Save to file
        output_path = "voice_test.wav"
        # Ensure audio is on CPU and convert to numpy
        audio_np = audio.cpu().numpy()
        # Flatten channels if mono
        if audio_np.ndim > 1 and audio_np.shape[0] == 1:
            audio_np = audio_np.squeeze(0)

        sf.write(output_path, audio_np, model.sample_rate)

        print(f"✅ Voice generated at {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"❌ Voice generation failed: {e}")


if __name__ == "__main__":
    test_voice()
