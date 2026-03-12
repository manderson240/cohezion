import torch
import torch.nn as nn
import logging
from typing import Union, List
import numpy as np

logger = logging.getLogger(__name__)

class HFEmbeddingBridge:
    """
    Bridge for converting Hugging Face embeddings to Flume input.
    """
    
    def __init__(
        self, 
        model_name: str = "all-MiniLM-L6-v2",
        target_dim: int | None = None,
        seed: int = 42
    ):
        """
        Initializes the bridge with a sentence-transformer model.
        
        Args:
            model_name: The name of the model on HF Hub.
            target_dim: Optional dimension to project the embeddings to.
            seed: Random seed for projection layer initialization.
        """
        self.model_name = model_name
        self.target_dim = target_dim
        self.model = None
        self._projection = None
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            
            # If target_dim is provided and different from model dim, 
            # we initialize a projection layer.
            if target_dim:
                model_dim = self.model.get_sentence_embedding_dimension()
                if model_dim != target_dim:
                    self._projection = nn.Linear(model_dim, target_dim)
                    # Use provided seed for stable orthogonal init
                    torch.manual_seed(seed)
                    nn.init.orthogonal_(self._projection.weight)
                    
        except ImportError:
            logger.error("sentence-transformers not installed.")
            raise

    async def get_embeddings(self, texts: Union[str, List[str]]) -> torch.Tensor:
        """
        Fetches raw embeddings from the HF model.
        
        Args:
            texts: A single string or list of strings.
            
        Returns:
            torch.Tensor: The embeddings.
        """
        if isinstance(texts, str):
            texts = [texts]
            
        # sentence-transformers encode is synchronous, but we wrap it 
        # for consistent async interface in the swarm.
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return torch.from_numpy(embeddings).float()

    async def get_flume_input(self, text: str) -> torch.Tensor:
        """
        Gets text embeddings and projects them to Flume target dimension.
        
        Args:
            text: Input text.
            
        Returns:
            torch.Tensor: Projected embedding vector.
        """
        raw_emb = await self.get_embeddings(text)
        
        if self._projection:
            with torch.no_grad():
                return self._projection(raw_emb)
        
        return raw_emb
