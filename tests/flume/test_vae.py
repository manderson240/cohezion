import pytest
import torch

from cohezion.flume.vae import FlumeVAE, FlumeVAEConfig, ThoughtVector


def test_thought_vector_initialization():
    """Test that ThoughtVector initializes correctly with proper shape."""
    data = torch.randn(256)
    tv = ThoughtVector(vector=data)
    assert torch.equal(tv.vector, data)
    assert tv.vector.shape == (256,)

def test_thought_vector_invalid_shape():
    """Test that ThoughtVector raises validation error for incorrect shape."""
    with pytest.raises(ValueError, match="vector must be 256D"):
        ThoughtVector(vector=torch.randn(255))

def test_flume_vae_initialization():
    """Test that FlumeVAE initializes with correct dimensions."""
    config = FlumeVAEConfig(z_dim=256, embed_dim=128)
    model = FlumeVAE(config)
    assert model.config.z_dim == 256
    assert model.config.embed_dim == 128

def test_flume_vae_forward_pass():
    """Test the VAE forward pass (encode/decode)."""
    config = FlumeVAEConfig(z_dim=256, embed_dim=128, vocab_size=100)
    model = FlumeVAE(config)
    
    batch_size = 4
    seq_len = 16
    input_ids = torch.randint(0, 100, (batch_size, seq_len))
    
    recon_logits, mu, log_var = model(input_ids)
    
    assert recon_logits.shape == (batch_size, seq_len, 100)
    assert mu.shape == (batch_size, 256)
    assert log_var.shape == (batch_size, 256)

def test_flume_vae_encode():
    """Test the VAE encode method returns mu and log_var."""
    config = FlumeVAEConfig(z_dim=256, vocab_size=100)
    model = FlumeVAE(config)
    
    input_ids = torch.randint(0, 100, (2, 10))
    mu, log_var = model.encode(input_ids)
    
    assert mu.shape == (2, 256)
    assert log_var.shape == (2, 256)

def test_flume_vae_reparameterize():
    """Test the reparameterization trick."""
    config = FlumeVAEConfig(z_dim=256)
    model = FlumeVAE(config)
    
    mu = torch.zeros(2, 256)
    log_var = torch.zeros(2, 256)
    
    z = model.reparameterize(mu, log_var)
    assert z.shape == (2, 256)
    # With 0 mu and 0 log_var (1 std), z should be random but shaped right

def test_flume_vae_compute_loss():
    """Test the VAE loss calculation."""
    config = FlumeVAEConfig(z_dim=256, vocab_size=100)
    model = FlumeVAE(config)
    
    batch_size = 2
    seq_len = 10
    input_ids = torch.randint(0, 100, (batch_size, seq_len))
    
    recon_logits, mu, log_var = model(input_ids)
    total_loss, recon_loss, kl_loss = model.compute_loss(input_ids, recon_logits, mu, log_var)
    
    assert total_loss > 0
    assert recon_loss > 0
    assert not torch.isnan(kl_loss)
