from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from cohezion.flume.bridge import HFEmbeddingBridge


@pytest.mark.asyncio
async def test_hf_bridge_initialization():
    """Test that the bridge initializes with a model name."""
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    
    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model) as mock_st:
        bridge = HFEmbeddingBridge(model_name="test-model")
        assert bridge.model_name == "test-model"
        mock_st.assert_called_once_with("test-model")

@pytest.mark.asyncio
async def test_get_embeddings_success():
    """Test that the bridge returns torch tensors from HF model."""
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    # Mocking return value of model.encode (which returns numpy by default)
    mock_model.encode.return_value = np.random.randn(2, 384).astype(np.float32)
    
    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
        bridge = HFEmbeddingBridge()
        texts = ["hello", "world"]
        embeddings = await bridge.get_embeddings(texts)
        
        assert isinstance(embeddings, torch.Tensor)
        assert embeddings.shape == (2, 384)
        mock_model.encode.assert_called_once_with(texts, convert_to_numpy=True)

@pytest.mark.asyncio
async def test_bridge_to_flume_dims():
    """Test that the bridge can project to Flume's required input dimension."""
    # If FlumeVAE expects 256D, but HF is 384D
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_model.encode.return_value = np.random.randn(1, 384).astype(np.float32)
    
    with patch("sentence_transformers.SentenceTransformer", return_value=mock_model):
        bridge = HFEmbeddingBridge(target_dim=256)
        # We need a projection layer in the bridge
        vec = await bridge.get_flume_input("test text")
        
        assert vec.shape == (1, 256)
