"""
Thought Autoencoder - Compress paragraphs of text to continuous vectors.

The CALM principle: Instead of predicting discrete tokens, we predict
continuous vectors in a high-dimensional semantic space. This turns
information from discrete data into continuous fluid motion.

Architecture:
- Encoder: Text → [tokens] → Transformer → z (256-dim thought vector)
- Decoder: z → Transformer → reconstructed text

This enables:
1. Continuous interpolation between concepts
2. Trajectory prediction in thought-space
3. Semantic arithmetic on ideas
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class ThoughtEncoder(nn.Module):
    """
    Encoder network: text tokens → thought vector z.
    
    Uses a simple transformer + pooling architecture.
    """
    
    def __init__(
        self,
        vocab_size: int = 32000,
        embed_dim: int = 256,
        hidden_dim: int = 512,
        num_heads: int = 4,
        num_layers: int = 2,
        z_dim: int = 256,
        max_seq_len: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.pos_embedding = nn.Embedding(max_seq_len, embed_dim)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        
        # Project to latent space
        self.to_z = nn.Linear(embed_dim, z_dim)
    
    def forward(
        self, 
        tokens: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """
        Encode tokens to thought vector z.
        
        Args:
            tokens: (batch, seq_len) token indices
            attention_mask: Optional mask for padding
            
        Returns:
            z: (batch, z_dim) thought vectors
        """
        batch_size, seq_len = tokens.shape
        
        # Embed tokens
        positions = torch.arange(seq_len, device=tokens.device).unsqueeze(0)
        x = self.embedding(tokens) + self.pos_embedding(positions)
        
        # Create attention mask for transformer
        if attention_mask is not None:
            # Convert to bool mask (True = masked out)
            src_key_padding_mask = ~attention_mask.bool()
        else:
            src_key_padding_mask = None
        
        # Transform
        x = self.transformer(x, src_key_padding_mask=src_key_padding_mask)
        
        # Pool (mean of non-masked positions)
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()
            x = (x * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            x = x.mean(dim=1)
        
        # Project to z
        z = self.to_z(x)
        
        return z


class ThoughtDecoder(nn.Module):
    """
    Decoder network: thought vector z → text tokens.
    
    Autoregressive generation from latent code.
    """
    
    def __init__(
        self,
        vocab_size: int = 32000,
        embed_dim: int = 256,
        hidden_dim: int = 512,
        num_heads: int = 4,
        num_layers: int = 2,
        z_dim: int = 256,
        max_seq_len: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.pos_embedding = nn.Embedding(max_seq_len, embed_dim)
        
        # Project z to initial hidden state
        self.z_proj = nn.Linear(z_dim, embed_dim)
        
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerDecoder(decoder_layer, num_layers)
        
        # Output projection
        self.to_logits = nn.Linear(embed_dim, vocab_size)
    
    def forward(
        self,
        z: torch.Tensor,
        target_tokens: torch.Tensor,
    ) -> torch.Tensor:
        """
        Decode thought vector to token logits.
        
        Args:
            z: (batch, z_dim) thought vectors
            target_tokens: (batch, seq_len) target token indices
            
        Returns:
            logits: (batch, seq_len, vocab_size)
        """
        batch_size, seq_len = target_tokens.shape
        
        # Embed targets
        positions = torch.arange(seq_len, device=target_tokens.device).unsqueeze(0)
        tgt = self.embedding(target_tokens) + self.pos_embedding(positions)
        
        # Create causal mask
        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, device=target_tokens.device) * float('-inf'),
            diagonal=1
        )
        
        # Project z to memory
        memory = self.z_proj(z).unsqueeze(1)  # (batch, 1, embed_dim)
        
        # Decode
        x = self.transformer(tgt, memory, tgt_mask=causal_mask)
        
        # Project to vocabulary
        logits = self.to_logits(x)
        
        return logits


class FlumeEncoder(nn.Module):
    """
    Full autoencoder for thought vector compression.
    
    Implements the FLUME principle: Fluid Latent Understanding through
    Manifold Encoding. Inspired by CALM (Kyutai Labs).
    """
    
    def __init__(
        self,
        vocab_size: int = 32000,
        embed_dim: int = 256,
        hidden_dim: int = 512,
        num_heads: int = 4,
        num_layers: int = 2,
        z_dim: int = 256,
        max_seq_len: int = 512,
        dropout: float = 0.1,
    ):
        super().__init__()
        
        self.z_dim = z_dim
        self.vocab_size = vocab_size
        
        self.encoder = ThoughtEncoder(
            vocab_size, embed_dim, hidden_dim, num_heads, 
            num_layers, z_dim, max_seq_len, dropout
        )
        self.decoder = ThoughtDecoder(
            vocab_size, embed_dim, hidden_dim, num_heads,
            num_layers, z_dim, max_seq_len, dropout
        )
        
        # Simple tokenizer (character-level for demo)
        self._char_to_idx: dict[str, int] = {}
        self._idx_to_char: dict[int, str] = {}
        self._init_tokenizer()
    
    def _init_tokenizer(self) -> None:
        """Initialize a simple character-level tokenizer."""
        chars = list(" abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?;:'\"()-\n")
        for i, c in enumerate(chars):
            self._char_to_idx[c] = i
            self._idx_to_char[i] = c
        
        # Special tokens
        self._char_to_idx["<PAD>"] = len(chars)
        self._char_to_idx["<UNK>"] = len(chars) + 1
        self._char_to_idx["<BOS>"] = len(chars) + 2
        self._char_to_idx["<EOS>"] = len(chars) + 3
    
    def tokenize(self, text: str, max_len: int = 256) -> torch.Tensor:
        """Convert text to token indices."""
        tokens = [self._char_to_idx.get(c, self._char_to_idx["<UNK>"]) for c in text]
        tokens = tokens[:max_len]
        tokens += [self._char_to_idx["<PAD>"]] * (max_len - len(tokens))
        return torch.tensor(tokens, dtype=torch.long)
    
    def detokenize(self, tokens: torch.Tensor) -> str:
        """Convert token indices back to text."""
        chars = []
        for idx in tokens.tolist():
            if idx in self._idx_to_char:
                chars.append(self._idx_to_char[idx])
            elif idx == self._char_to_idx.get("<PAD>", -1):
                break
        return "".join(chars)
    
    def encode(
        self, 
        text: str | list[str],
        max_len: int = 256,
    ) -> torch.Tensor:
        """
        Encode text(s) to thought vector(s).
        
        Args:
            text: Single string or list of strings
            max_len: Maximum sequence length
            
        Returns:
            z: (batch, z_dim) thought vectors
        """
        if isinstance(text, str):
            text = [text]
        
        tokens = torch.stack([self.tokenize(t, max_len) for t in text])
        attention_mask = (tokens != self._char_to_idx["<PAD>"]).float()
        
        with torch.no_grad():
            z = self.encoder(tokens, attention_mask)
        
        return z
    
    def decode(
        self, 
        z: torch.Tensor,
        max_len: int = 256,
        temperature: float = 1.0,
    ) -> list[str]:
        """
        Decode thought vector(s) to text.
        
        Args:
            z: (batch, z_dim) thought vectors
            max_len: Maximum output length
            temperature: Sampling temperature
            
        Returns:
            List of decoded strings
        """
        batch_size = z.shape[0]
        device = z.device
        
        # Start with BOS token
        tokens = torch.full(
            (batch_size, 1), 
            self._char_to_idx.get("<BOS>", 0),
            dtype=torch.long,
            device=device,
        )
        
        # Autoregressive generation
        for _ in range(max_len - 1):
            with torch.no_grad():
                logits = self.decoder(z, tokens)
                next_logits = logits[:, -1, :] / temperature
                probs = F.softmax(next_logits, dim=-1)
                next_token = torch.multinomial(probs, 1)
                tokens = torch.cat([tokens, next_token], dim=1)
                
                # Stop if all sequences hit EOS
                if (next_token == self._char_to_idx.get("<EOS>", -1)).all():
                    break
        
        return [self.detokenize(t[1:]) for t in tokens]  # Skip BOS
    
    def forward(
        self,
        tokens: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Full forward pass for training.
        
        Returns:
            z: Encoded thought vectors
            logits: Decoded token logits
        """
        z = self.encoder(tokens, attention_mask)
        logits = self.decoder(z, tokens)
        return z, logits
    
    def reconstruction_loss(
        self,
        tokens: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Compute reconstruction loss for training."""
        z, logits = self.forward(tokens, attention_mask)
        
        # Shift for next-token prediction
        shift_logits = logits[:, :-1, :].contiguous()
        shift_labels = tokens[:, 1:].contiguous()
        
        loss = F.cross_entropy(
            shift_logits.view(-1, self.vocab_size),
            shift_labels.view(-1),
            ignore_index=self._char_to_idx["<PAD>"],
        )
        
        return loss
    
    def interpolate(
        self,
        text_a: str,
        text_b: str,
        steps: int = 5,
    ) -> list[str]:
        """
        Interpolate between two texts in thought-space.
        
        This is the "fluid motion" of CALM - continuous transitions
        between concepts.
        """
        z_a = self.encode(text_a)
        z_b = self.encode(text_b)
        
        results = []
        for i in range(steps):
            alpha = i / (steps - 1) if steps > 1 else 0
            z_interp = (1 - alpha) * z_a + alpha * z_b
            decoded = self.decode(z_interp)
            results.append(decoded[0])
        
        return results
    
    def save(self, path: Path | str) -> None:
        """Save model weights."""
        torch.save(self.state_dict(), path)
        logger.info(f"Saved model to {path}")
    
    def load(self, path: Path | str) -> None:
        """Load model weights."""
        self.load_state_dict(torch.load(path, weights_only=True))
        logger.info(f"Loaded model from {path}")
