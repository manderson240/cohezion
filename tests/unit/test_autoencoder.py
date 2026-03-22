"""Tests for the FlumeEncoder autoencoder (cohezion.flume.autoencoder)."""

from __future__ import annotations

import pytest
import torch

from cohezion.flume.autoencoder import (
    FlumeConfig,
    FlumeEncoder,
    ThoughtDecoder,
    ThoughtEncoder,
)


class TestFlumeConfig:
    def test_defaults(self):
        config = FlumeConfig()
        assert config.vocab_size == 32000
        assert config.embed_dim == 256
        assert config.hidden_dim == 512
        assert config.num_heads == 4
        assert config.num_layers == 2
        assert config.z_dim == 256
        assert config.max_seq_len == 512
        assert config.dropout == 0.1

    def test_custom_config(self):
        config = FlumeConfig(z_dim=128, num_layers=4)
        assert config.z_dim == 128
        assert config.num_layers == 4

    def test_model_type(self):
        assert FlumeConfig.model_type == "flume"


class TestThoughtEncoder:
    def setup_method(self):
        self.config = FlumeConfig(
            vocab_size=100,
            embed_dim=32,
            hidden_dim=64,
            num_heads=2,
            num_layers=1,
            z_dim=16,
            max_seq_len=32,
        )
        self.encoder = ThoughtEncoder(self.config)

    def test_output_shape(self):
        tokens = torch.randint(0, 100, (2, 10))
        z = self.encoder(tokens)
        assert z.shape == (2, 16)  # [batch_size, z_dim]

    def test_output_shape_with_mask(self):
        tokens = torch.randint(0, 100, (3, 8))
        mask = torch.ones(3, 8)
        mask[0, 5:] = 0  # Mask out last 3 tokens for first sample
        z = self.encoder(tokens, attention_mask=mask)
        assert z.shape == (3, 16)

    def test_deterministic_with_eval(self):
        self.encoder.eval()
        tokens = torch.randint(0, 100, (1, 5))
        with torch.no_grad():
            z1 = self.encoder(tokens)
            z2 = self.encoder(tokens)
        assert torch.allclose(z1, z2)


class TestThoughtDecoder:
    def setup_method(self):
        self.config = FlumeConfig(
            vocab_size=100,
            embed_dim=32,
            hidden_dim=64,
            num_heads=2,
            num_layers=1,
            z_dim=16,
            max_seq_len=32,
        )
        self.decoder = ThoughtDecoder(self.config)

    def test_output_shape(self):
        z = torch.randn(2, 16)
        target = torch.randint(0, 100, (2, 10))
        logits = self.decoder(z, target)
        assert logits.shape == (2, 10, 100)  # [batch, seq_len, vocab_size]

    def test_output_shape_single_sample(self):
        z = torch.randn(1, 16)
        target = torch.randint(0, 100, (1, 5))
        logits = self.decoder(z, target)
        assert logits.shape == (1, 5, 100)


class TestFlumeEncoderModel:
    """Test the full FlumeEncoder PreTrainedModel."""

    def setup_method(self):
        self.config = FlumeConfig(
            vocab_size=100,
            embed_dim=32,
            hidden_dim=64,
            num_heads=2,
            num_layers=1,
            z_dim=16,
            max_seq_len=32,
        )

    def test_forward_returns_z_and_logits(self):
        # Patch tokenizer to avoid needing real tokenizer files
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                "cohezion.flume.autoencoder.FlumeEncoder.__init__",
                _patched_init(self.config),
            )
            model = FlumeEncoder(self.config)
            tokens = torch.randint(0, 100, (2, 10))
            z, logits = model(tokens)
            assert z.shape == (2, 16)
            assert logits.shape == (2, 10, 100)

    def test_reconstruction_loss(self):
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                "cohezion.flume.autoencoder.FlumeEncoder.__init__",
                _patched_init(self.config),
            )
            model = FlumeEncoder(self.config)
            tokens = torch.randint(0, 100, (2, 10))
            loss = model.reconstruction_loss(tokens)
            assert loss.shape == ()
            assert loss.item() > 0  # Untrained model should have nonzero loss

    def test_semantic_add(self):
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                "cohezion.flume.autoencoder.FlumeEncoder.__init__",
                _patched_init(self.config),
            )
            model = FlumeEncoder(self.config)
            base = torch.randn(1, 16)
            direction = torch.randn(1, 16)
            result = model.semantic_add(base, direction, scale=0.5)
            expected = base + direction * 0.5
            assert torch.allclose(result, expected)

    def test_semantic_direction(self):
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                "cohezion.flume.autoencoder.FlumeEncoder.__init__",
                _patched_init(self.config),
            )
            model = FlumeEncoder(self.config)
            z_a = torch.randn(1, 16)
            z_b = torch.randn(1, 16)
            direction = model.semantic_direction(z_a, z_b)
            expected = z_b - z_a
            assert torch.allclose(direction, expected)


def _patched_init(config):
    """Create a patched __init__ that skips tokenizer loading."""

    def init(self, cfg):
        from transformers import PreTrainedModel

        PreTrainedModel.__init__(self, cfg)
        self.encoder = ThoughtEncoder(cfg)
        self.decoder = ThoughtDecoder(cfg)

        # Mock tokenizer
        from unittest.mock import MagicMock

        self.tokenizer = MagicMock()
        self.tokenizer.pad_token_id = 0
        self.tokenizer.bos_token_id = 1
        self.tokenizer.eos_token_id = 2
        self.post_init()

    return init
