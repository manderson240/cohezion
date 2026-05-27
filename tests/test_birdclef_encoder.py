import torch

from src.cohezion.audio.bioacoustic_encoder import BioacousticEncoder


def test_bioacoustic_projection():
    input_dim = 1536  # Perch embedding size
    latent_dim = 256  # FLUME latent size

    encoder = BioacousticEncoder(input_dim=input_dim, latent_dim=latent_dim)

    # Mock Perch embedding
    x = torch.randn(10, input_dim)  # Batch of 10

    z = encoder(x)

    assert z.shape == (10, latent_dim)
    assert torch.all(z >= -1.0) and torch.all(z <= 1.0)  # Tanh normalization

    print("Bioacoustic Encoder Projection Test Passed.")


if __name__ == "__main__":
    test_bioacoustic_projection()
