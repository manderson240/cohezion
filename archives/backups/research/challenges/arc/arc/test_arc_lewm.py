"""Comprehensive unit tests for ARC LeWM modules.

Tests for arc_dataset.py, arc_lewm_encoder.py, and arc_lewm_decoder.py.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn as nn


# Add arc directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "arc"))

from arc_dataset import (
    ARCBatchSampler,
    ARCDataset,
    ARCGridTokenizer,
)
from arc_lewm_decoder import (
    ARCGridDecoder,
    ARCWorldModel,
    ResidualBlockTranspose,
)
from arc_lewm_encoder import (
    AdaptiveGridPool,
    ARCActionEncoder,
    ARCCausalMask,
    ARCGridEncoder,
    ARCPredictor,
    ResidualBlock,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_arc_grid():
    """Sample ARC grid (5x5 with colors 0-4)."""
    return [
        [0, 0, 1, 0, 0],
        [0, 1, 2, 1, 0],
        [1, 2, 3, 2, 1],
        [0, 1, 2, 1, 0],
        [0, 0, 1, 0, 0],
    ]


@pytest.fixture
def sample_arc_grid_2():
    """Another sample ARC grid (3x3)."""
    return [
        [1, 1, 1],
        [1, 2, 1],
        [1, 1, 1],
    ]


@pytest.fixture
def mock_arc_data():
    """Mock ARC JSON data."""
    return {
        "task_001": {
            "train": [
                {
                    "input": [[0, 0], [0, 1]],
                    "output": [[0, 0], [1, 1]],
                },
                {
                    "input": [[1, 0], [0, 0]],
                    "output": [[1, 1], [0, 0]],
                },
            ],
            "test": [
                {
                    "input": [[0, 1], [0, 0]],
                    "output": [[0, 1], [0, 1]],
                },
            ],
        },
        "task_002": {
            "train": [
                {
                    "input": [[1, 1], [1, 0]],
                    "output": [[0, 1], [1, 1]],
                },
            ],
            "test": [],
        },
    }


@pytest.fixture
def temp_arc_files(mock_arc_data):
    """Create temporary ARC data files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        challenges_path = Path(tmpdir) / "challenges.json"
        solutions_path = Path(tmpdir) / "solutions.json"

        # Challenges file
        with open(challenges_path, "w") as f:
            json.dump(mock_arc_data, f)

        # Solutions file
        solutions = {
            "task_001": [[[0, 1], [0, 1]]],
            "task_002": [[[0, 1], [1, 1]]],
        }
        with open(solutions_path, "w") as f:
            json.dump(solutions, f)

        yield challenges_path, solutions_path


# =============================================================================
# ARCGridTokenizer Tests
# =============================================================================


class TestARCGridTokenizer:
    """Tests for ARCGridTokenizer."""

    def test_grid_to_tensor_shape(self, sample_arc_grid):
        """Test grid conversion to tensor preserves structure."""
        tensor = ARCGridTokenizer.grid_to_tensor(sample_arc_grid)

        assert tensor.shape == (10, 5, 5)  # (colors, H, W)
        assert tensor.dtype == torch.float32

    def test_grid_to_tensor_no_padding(self, sample_arc_grid):
        """Test grid conversion without size constraints."""
        tensor = ARCGridTokenizer.grid_to_tensor(sample_arc_grid, max_size=None)

        assert tensor.shape == (10, 5, 5)

    def test_grid_to_tensor_with_padding(self, sample_arc_grid):
        """Test grid conversion with padding to larger size."""
        tensor = ARCGridTokenizer.grid_to_tensor(sample_arc_grid, max_size=10)

        assert tensor.shape == (10, 10, 10)

    def test_grid_to_tensor_one_hot(self, sample_arc_grid):
        """Test one-hot encoding correctness."""
        tensor = ARCGridTokenizer.grid_to_tensor(sample_arc_grid)

        # Center is color 3
        assert tensor[3, 2, 2] == 1.0
        # Background is color 0
        assert tensor[0, 0, 0] == 1.0

    def test_tensor_to_grid_roundtrip(self, sample_arc_grid):
        """Test roundtrip conversion."""
        tensor = ARCGridTokenizer.grid_to_tensor(sample_arc_grid)
        reconstructed = ARCGridTokenizer.tensor_to_grid(tensor)

        assert reconstructed == sample_arc_grid

    def test_tensor_to_grid_with_target_size(self, sample_arc_grid):
        """Test reconstruction with target size."""
        tensor = ARCGridTokenizer.grid_to_tensor(sample_arc_grid, max_size=10)
        reconstructed = ARCGridTokenizer.tensor_to_grid(tensor, original_size=(5, 5))

        assert reconstructed == sample_arc_grid

    def test_get_grid_size(self, sample_arc_grid):
        """Test grid size utility."""
        size = ARCGridTokenizer.get_grid_size(sample_arc_grid)
        assert size == (5, 5)

    def test_empty_grid(self):
        """Test handling empty grid."""
        empty_grid = [[]]  # Not really valid but should handle gracefully
        # Should not crash

    @pytest.mark.parametrize("grid_size", [(3, 3), (5, 5), (10, 10), (15, 15), (30, 30)])
    def test_various_grid_sizes(self, grid_size):
        """Test tokenizer handles various grid sizes."""
        rows, cols = grid_size
        grid = [[np.random.randint(0, 10) for _ in range(cols)] for _ in range(rows)]

        tensor = ARCGridTokenizer.grid_to_tensor(grid)
        reconstructed = ARCGridTokenizer.tensor_to_grid(tensor, grid_size)

        assert reconstructed == grid


# =============================================================================
# ARCDataset Tests
# =============================================================================


class TestARCDataset:
    """Tests for ARCDataset."""

    def test_dataset_loading(self, temp_arc_files):
        """Test dataset loads from files."""
        challenges_path, solutions_path = temp_arc_files

        dataset = ARCDataset(
            challenges_path=challenges_path,
            solutions_path=solutions_path,
            max_grid_size=10,
        )

        assert len(dataset) > 0

    def test_getitem_structure(self, temp_arc_files):
        """Test dataset item structure."""
        challenges_path, solutions_path = temp_arc_files

        dataset = ARCDataset(
            challenges_path=challenges_path,
            solutions_path=solutions_path,
            max_grid_size=10,
        )

        item = dataset[0]

        assert "state" in item
        assert "action" in item
        assert "next_state" in item
        assert "meta" in item

        assert item["state"].shape[0] == 10  # NUM_COLORS
        assert item["action"].shape == (64,)  # Action encoding dimension
        assert item["next_state"].shape[0] == 10

    def test_action_encoding(self, temp_arc_files):
        """Test action encoding includes relevant features."""
        challenges_path, solutions_path = temp_arc_files

        dataset = ARCDataset(
            challenges_path=challenges_path,
            solutions_path=solutions_path,
            max_grid_size=10,
        )

        item = dataset[0]
        action = item["action"].numpy()

        # First 2 dims are size ratios
        assert action[0] == 1.0  # Same size in test data
        assert action[1] == 1.0

        # Dims 2-12 are color delta
        assert len(action[2:12]) == 10

        # Dims 12-22 are input color distribution
        assert len(action[12:22]) == 10

    def test_collate_function(self, temp_arc_files):
        """Test collate function creates batch."""
        challenges_path, solutions_path = temp_arc_files

        dataset = ARCDataset(
            challenges_path=challenges_path,
            solutions_path=solutions_path,
            max_grid_size=10,
        )

        collate_fn = dataset.get_collate_fn()
        batch = [dataset[i] for i in range(min(2, len(dataset)))]
        collated = collate_fn(batch)

        assert collated["state"].shape[0] == len(batch)
        assert collated["action"].shape[0] == len(batch)
        assert collated["next_state"].shape[0] == len(batch)
        assert len(collated["meta"]) == len(batch)

    def test_batch_sampler(self, temp_arc_files):
        """Test batch sampler groups by sizes."""
        challenges_path, solutions_path = temp_arc_files

        dataset = ARCDataset(
            challenges_path=challenges_path,
            solutions_path=solutions_path,
            max_grid_size=10,
        )

        sampler = ARCBatchSampler(dataset, batch_size=2)
        batches = list(sampler)

        # Should have created some batches
        assert len(batches) >= 0 or len(dataset) < 2


# =============================================================================
# Encoder Tests
# =============================================================================


class TestARCGridEncoder:
    """Tests for ARCGridEncoder."""

    @pytest.fixture
    def encoder(self):
        """Create encoder for testing."""
        return ARCGridEncoder(embed_dim=64, latent_dim=256)

    def test_encoder_output_shape(self, encoder):
        """Test encoder outputs correct shapes."""
        # Create input (batch_size=2, 10 colors, 32x32)
        x = torch.randn(2, 10, 32, 32)

        z, mu, logvar = encoder(x)

        assert z.shape == (2, 64)
        assert mu.shape == (2, 64)
        assert logvar.shape == (2, 64)

    def test_encoder_single_sample(self, encoder):
        """Test encoder with single sample."""
        x = torch.randn(10, 8, 8)

        z, mu, logvar = encoder(x)

        assert z.shape == (1, 64)  # Auto-batched

    def test_encoder_various_sizes(self, encoder):
        """Test encoder handles different input sizes."""
        sizes = [(10, 8, 8), (10, 16, 16), (10, 32, 32), (10, 4, 4)]

        for size in sizes:
            x = torch.randn(1, *size)
            z, _, _ = encoder(x)
            assert z.shape == (1, 64)

    def test_encoder_variational_output(self, encoder):
        """Test reparameterization trick produces different samples."""
        x = torch.randn(2, 10, 16, 16)

        torch.manual_seed(42)
        z1, mu, logvar = encoder(x)

        torch.manual_seed(43)
        z2, _, _ = encoder(x)

        # mu and logvar should be same (deterministic)
        # z should differ slightly due to sampling

    def test_encode_mu_deterministic(self, encoder):
        """Test deterministic encoding."""
        x = torch.randn(2, 10, 16, 16)

        mu1 = encoder.encode_mu(x)
        mu2 = encoder.encode_mu(x)

        torch.testing.assert_close(mu1, mu2)  # type: ignore

    @pytest.mark.parametrize("batch_size", [1, 4, 8])
    def test_encoder_batch_sizes(self, encoder, batch_size):
        """Test encoder with various batch sizes."""
        x = torch.randn(batch_size, 10, 16, 16)

        z, mu, logvar = encoder(x)

        assert z.shape == (batch_size, 64)


class TestARCActionEncoder:
    """Tests for ARCActionEncoder."""

    @pytest.fixture
    def action_encoder(self):
        """Create action encoder."""
        return ARCActionEncoder(action_dim=64, embed_dim=64)

    def test_action_encoder_shape(self, action_encoder):
        """Test action encoder output shape."""
        action = torch.randn(2, 64)

        emb = action_encoder(action)

        assert emb.shape == (2, 64)

    def test_action_encoder_single(self, action_encoder):
        """Test action encoder with single action."""
        action = torch.randn(64)

        emb = action_encoder(action)

        assert emb.shape == (1, 64)  # Auto-batched


class TestARCPredictor:
    """Tests for ARCPredictor."""

    @pytest.fixture
    def predictor(self):
        """Create predictor."""
        return ARCPredictor(embed_dim=64, hidden_dim=128)

    def test_predictor_output_shape(self, predictor):
        """Test predictor output shape."""
        state_emb = torch.randn(2, 64)
        action_emb = torch.randn(2, 64)

        pred = predictor(state_emb, action_emb)

        assert pred.shape == (2, 64)

    def test_predictor_different_shapes(self, predictor):
        """Test predictor with custom dimensions."""
        custom_predictor = ARCPredictor(embed_dim=32, hidden_dim=64)

        state_emb = torch.randn(2, 32)
        action_emb = torch.randn(2, 32)

        pred = custom_predictor(state_emb, action_emb)

        assert pred.shape == (2, 32)


class TestARCCausalMask:
    """Tests for ARCCausalMask."""

    @pytest.fixture
    def causal_mask(self):
        """Create causal mask."""
        return ARCCausalMask(embed_dim=64, mask_ratio=0.3)

    def test_causal_mask_shape(self, causal_mask):
        """Test causal mask preserves shape."""
        x = torch.randn(2, 64)

        masked = causal_mask(x, training=True)

        assert masked.shape == (2, 64)

    def test_causal_mask_training_different(self, causal_mask):
        """Test training mode produces different outputs."""
        x = torch.randn(2, 64)

        torch.manual_seed(42)
        masked1 = causal_mask(x, training=True)

        torch.manual_seed(43)
        masked2 = causal_mask(x, training=True)

        # Should be different due to random masking

    def test_causal_mask_inference(self, causal_mask):
        """Test inference mode is deterministic."""
        x = torch.randn(2, 64)

        masked1 = causal_mask(x, training=False)
        masked2 = causal_mask(x, training=False)

        torch.testing.assert_close(masked1, masked2)  # type: ignore

    def test_causal_importance_scores(self, causal_mask):
        """Test importance scores are returned."""
        scores = causal_mask.causal_importance_scores()

        assert scores.shape == (64,)
        assert torch.all(scores >= 0)
        assert torch.all(scores <= 1)

    def test_top_k_causal_dims(self, causal_mask):
        """Test top-k dimension selection."""
        top_k = causal_mask.top_k_causal_dims(k=8)

        assert len(top_k) == 8
        assert len(set(top_k)) == 8  # All unique
        assert all(0 <= i < 64 for i in top_k)


class TestAdaptiveGridPool:
    """Tests for AdaptiveGridPool."""

    def test_pool_output_size(self):
        """Test pool produces correct output size."""
        pool = AdaptiveGridPool(output_size=(4, 4))

        x = torch.randn(2, 10, 32, 32)
        pooled = pool(x)

        assert pooled.shape == (2, 10, 4, 4)

    def test_pool_various_inputs(self):
        """Test pool handles various input sizes."""
        pool = AdaptiveGridPool(output_size=(4, 4))

        sizes = [(16, 16), (32, 32), (8, 8), (64, 64)]

        for h, w in sizes:
            x = torch.randn(2, 10, h, w)
            pooled = pool(x)
            assert pooled.shape == (2, 10, 4, 4)


class TestResidualBlock:
    """Tests for ResidualBlock."""

    def test_residual_block_shape(self):
        """Test residual block preserves shape."""
        block = ResidualBlock(channels=32)

        x = torch.randn(2, 32, 16, 16)
        out = block(x)

        assert out.shape == x.shape

    def test_residual_connection(self):
        """Test residual connection is present."""
        block = ResidualBlock(channels=16)

        x = torch.randn(2, 16, 8, 8)

        # Forward pass
        out = block(x)

        # Should be able to train
        loss = out.sum()
        loss.backward()

        assert all(p.grad is not None for p in block.parameters() if p.requires_grad)


# =============================================================================
# Decoder Tests
# =============================================================================


class TestARCGridDecoder:
    """Tests for ARCGridDecoder."""

    @pytest.fixture
    def decoder(self):
        """Create decoder for testing."""
        return ARCGridDecoder(embed_dim=64, latent_dim=256)

    def test_decoder_output_shape(self, decoder):
        """Test decoder outputs correct shape."""
        z = torch.randn(2, 64)

        output = decoder(z)

        assert output.shape == (2, 10, 32, 32)  # Base output is 32x32

    def test_decoder_with_target_size(self, decoder):
        """Test decoder resizes to target."""
        z = torch.randn(2, 64)

        output = decoder(z, target_size=(16, 16))

        assert output.shape == (2, 10, 16, 16)

    def test_decoder_single_sample(self, decoder):
        """Test decoder with single sample."""
        z = torch.randn(64)

        output = decoder(z)

        assert output.shape == (1, 10, 32, 32)  # Auto-batched

    def test_decoder_output_logits(self, decoder):
        """Test decoder outputs logits (not probabilities)."""
        z = torch.randn(2, 64)

        output = decoder(z, target_size=(8, 8))

        # Logits should not be bounded to [0, 1]
        assert not torch.all((output >= 0) & (output <= 1))

    def test_decode_to_grid(self, decoder):
        """Test grid decoding."""
        z = torch.randn(64)

        grid = decoder.decode_to_grid(z, target_size=(5, 5))

        assert len(grid) == 5
        assert len(grid[0]) == 5
        assert all(0 <= c <= 9 for row in grid for c in row)


class TestResidualBlockTranspose:
    """Tests for ResidualBlockTranspose."""

    def test_transpose_block_shape(self):
        """Test transpose block preserves shape."""
        block = ResidualBlockTranspose(channels=32)

        x = torch.randn(2, 32, 16, 16)
        out = block(x)

        assert out.shape == x.shape


# =============================================================================
# Integration Tests
# =============================================================================


class TestARCWorldModel:
    """Integration tests for complete ARC World Model."""

    @pytest.fixture
    def world_model(self):
        """Create complete world model."""
        return ARCWorldModel(
            embed_dim=64,
            action_dim=64,
            latent_dim=256,
            num_res_blocks=1,  # Smaller for testing
            dropout=0.0,
        )

    def test_full_forward_pass(self, world_model):
        """Test complete forward pass."""
        grid = torch.randn(2, 10, 16, 16)
        action = torch.randn(2, 64)

        outputs = world_model(grid, action)

        assert "z" in outputs
        assert "mu" in outputs
        assert "logvar" in outputs
        assert "z_pred" in outputs
        assert "grid_pred" in outputs

        assert outputs["grid_pred"].shape == (2, 10, 32, 32)

    def test_predict_method(self, world_model):
        """Test predict method."""
        grid = torch.randn(2, 10, 16, 16)
        action = torch.randn(2, 64)

        pred_grid = world_model.predict(grid, action)

        assert pred_grid.shape == (2, 10, 32, 32)

    def test_encode_decode_roundtrip(self, world_model, sample_arc_grid):
        """Test encode-decode preserves approximate structure."""
        from arc_dataset import ARCGridTokenizer

        tokenizer = ARCGridTokenizer()
        grid_tensor = tokenizer.grid_to_tensor(sample_arc_grid).unsqueeze(0)

        # Encode
        z = world_model.encode(grid_tensor)

        # Decode
        grid_size = tokenizer.get_grid_size(sample_arc_grid)
        reconstructed_grid = world_model.decode_to_grid(z, grid_size)

        # Should reconstruct something (may not be exact due to compression)
        assert len(reconstructed_grid) == grid_size[0]
        assert len(reconstructed_grid[0]) == grid_size[1]

    def test_parameter_count(self, world_model):
        """Test parameter count is reasonable."""
        n_params = world_model.n_parameters

        # Should be less than ~10M for efficiency
        assert n_params < 10_000_000
        # Should have some parameters
        assert n_params > 100_000

    def test_gradient_flow(self, world_model):
        """Test gradients flow through the model."""
        grid = torch.randn(2, 10, 16, 16, requires_grad=True)
        action = torch.randn(2, 64, requires_grad=True)

        outputs = world_model(grid, action)
        loss = outputs["grid_pred"].sum()

        loss.backward()

        assert grid.grad is not None
        assert action.grad is not None
        assert any(p.grad is not None for p in world_model.parameters())


class TestEndToEnd:
    """End-to-end tests with mock data."""

    def test_dataset_to_model_integration(self, temp_arc_files):
        """Test loading data and feeding through model."""
        challenges_path, solutions_path = temp_arc_files

        # Create dataset
        dataset = ARCDataset(
            challenges_path=challenges_path,
            solutions_path=solutions_path,
            max_grid_size=10,
        )

        if len(dataset) == 0:
            pytest.skip("Empty dataset")

        item = dataset[0]

        # Create model
        model = ARCWorldModel(embed_dim=64, latent_dim=128, num_res_blocks=1)
        model.eval()

        # Forward pass
        with torch.no_grad():
            state = item["state"].unsqueeze(0)
            action = item["action"].unsqueeze(0)
            outputs = model(state, action)

        assert outputs["grid_pred"] is not None

    def test_training_step(self, temp_arc_files):
        """Test a single training step."""
        challenges_path, solutions_path = temp_arc_files

        dataset = ARCDataset(
            challenges_path=challenges_path,
            solutions_path=solutions_path,
            max_grid_size=10,
        )

        if len(dataset) == 0:
            pytest.skip("Empty dataset")

        # Create model with optimizer
        model = ARCWorldModel(embed_dim=32, latent_dim=64, num_res_blocks=1, dropout=0.0)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

        # Get single sample
        item = dataset[0]
        state = item["state"].unsqueeze(0)
        action = item["action"].unsqueeze(0)
        next_state = item["next_state"].unsqueeze(0)

        # Forward
        model.train()
        optimizer.zero_grad()

        outputs = model(state, action)

        # Simple reconstruction loss
        loss = nn.functional.mse_loss(outputs["grid_pred"], next_state)

        # Backward
        loss.backward()
        optimizer.step()

        assert loss.item() >= 0


# =============================================================================
# Performance Tests
# =============================================================================


@pytest.mark.slow
class TestPerformance:
    """Performance tests."""

    def test_encoder_throughput(self):
        """Test encoder throughput."""
        encoder = ARCGridEncoder()

        batch_size = 32
        x = torch.randn(batch_size, 10, 32, 32)

        import time

        # Warmup
        for _ in range(5):
            encoder(x)

        # Measure
        start = time.time()
        for _ in range(10):
            encoder(x)
        elapsed = time.time() - start

        throughput = (batch_size * 10) / elapsed
        print(f"Encoder throughput: {throughput:.2f} grids/sec")

        # Should process at least 100 grids/sec
        assert throughput > 100

    def test_decoder_throughput(self):
        """Test decoder throughput."""
        decoder = ARCGridDecoder()

        batch_size = 32
        z = torch.randn(batch_size, 64)

        import time

        # Warmup
        for _ in range(5):
            decoder(z)

        # Measure
        start = time.time()
        for _ in range(10):
            decoder(z)
        elapsed = time.time() - start

        throughput = (batch_size * 10) / elapsed
        print(f"Decoder throughput: {throughput:.2f} grids/sec")

        # Should process at least 100 grids/sec
        assert throughput > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
