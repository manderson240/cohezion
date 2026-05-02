import os
import shutil

import torch

from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder
from cohezion.flume.tokenizer import FlumeTokenizer


def test_hf_refactor():
    print("Testing HF Refactor...")

    # 1. Config Test
    config = FlumeConfig(vocab_size=100, embed_dim=128, z_dim=128)
    model = FlumeEncoder(config)
    model.eval()  # Ensure deterministic for test
    print("✓ Model initialized with FlumeConfig")

    # 2. Tokenizer Test
    tokenizer = FlumeTokenizer()
    text = "Hello Flume"
    encoded = tokenizer(text, return_tensors="pt")
    decoded = tokenizer.batch_decode(encoded["input_ids"], skip_special_tokens=True)[0]
    print(f"✓ Tokenizer: '{text}' -> {encoded['input_ids'].shape} -> '{decoded}'")
    assert text == decoded

    # 3. Model Encode/Decode Test
    z = model.encode(text)
    print(f"✓ Encoded to z: {z.shape}")
    assert z.shape == (1, 128)

    decoded_text = model.decode(z, max_len=10)
    print(f"✓ Decoded from z: {decoded_text}")

    # 4. Save/Load Test
    save_path = "tests/flume_hf_test"
    if os.path.exists(save_path):
        shutil.rmtree(save_path)

    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    print("✓ Saved pretrained model and tokenizer")

    model2 = FlumeEncoder.from_pretrained(save_path)
    model2.eval()
    FlumeTokenizer.from_pretrained(save_path)
    print("✓ Loaded pretrained model and tokenizer")

    # Weight Diagnostics
    sum1 = sum(p.sum().item() for p in model.parameters())
    sum2 = sum(p.sum().item() for p in model2.parameters())
    print(f"DEBUG: model1 weight sum: {sum1}")
    print(f"DEBUG: model2 weight sum: {sum2}")

    z2 = model2.encode(text)
    print(f"DEBUG: z1[0,:5]: {z[0, :5]}")
    print(f"DEBUG: z2[0,:5]: {z2[0, :5]}")

    assert torch.allclose(z, z2, atol=1e-5)
    print("✓ Loaded model produces identical vectors")

    # Cleanup (Disabled for debugging)
    # shutil.rmtree(save_path)
    print("\n🚀 HF Refactor Verified Successfully!")


if __name__ == "__main__":
    test_hf_refactor()
