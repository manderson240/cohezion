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

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import PretrainedConfig, PreTrainedModel


logger = logging.getLogger(__name__)


class FlumeConfig(PretrainedConfig):
    """
    Configuration for Flume Autoencoder.
    """

    model_type = "flume"

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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.num_layers = num_layers
        self.z_dim = z_dim
        self.max_seq_len = max_seq_len
        self.dropout = dropout


class ThoughtEncoder(nn.Module):
    """
    Encoder network: text tokens → thought vector z.
    """

    def __init__(self, config: FlumeConfig):
        super().__init__()

        self.embedding = nn.Embedding(config.vocab_size, config.embed_dim)
        self.pos_embedding = nn.Embedding(config.max_seq_len, config.embed_dim)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.embed_dim,
            nhead=config.num_heads,
            dim_feedforward=config.hidden_dim,
            dropout=config.dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, config.num_layers)

        # Project to latent space
        self.to_z = nn.Linear(config.embed_dim, config.z_dim)

    def forward(
        self,
        tokens: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        _batch_size, seq_len = tokens.shape
        positions = torch.arange(seq_len, device=tokens.device).unsqueeze(0)
        x = self.embedding(tokens) + self.pos_embedding(positions)

        src_key_padding_mask = ~attention_mask.bool() if attention_mask is not None else None

        x = self.transformer(x, src_key_padding_mask=src_key_padding_mask)

        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()
            x = (x * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            x = x.mean(dim=1)

        z = self.to_z(x)
        return z


class ThoughtDecoder(nn.Module):
    """
    Decoder network: thought vector z → text tokens.
    """

    def __init__(self, config: FlumeConfig):
        super().__init__()

        self.embedding = nn.Embedding(config.vocab_size, config.embed_dim)
        self.pos_embedding = nn.Embedding(config.max_seq_len, config.embed_dim)
        self.z_proj = nn.Linear(config.z_dim, config.embed_dim)

        decoder_layer = nn.TransformerDecoderLayer(
            d_model=config.embed_dim,
            nhead=config.num_heads,
            dim_feedforward=config.hidden_dim,
            dropout=config.dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerDecoder(decoder_layer, config.num_layers)
        self.to_logits = nn.Linear(config.embed_dim, config.vocab_size)

    def forward(
        self,
        z: torch.Tensor,
        target_tokens: torch.Tensor,
    ) -> torch.Tensor:
        _batch_size, seq_len = target_tokens.shape
        positions = torch.arange(seq_len, device=target_tokens.device).unsqueeze(0)
        tgt = self.embedding(target_tokens) + self.pos_embedding(positions)

        causal_mask = torch.triu(
            torch.ones(seq_len, seq_len, device=target_tokens.device) * float("-inf"),
            diagonal=1,
        )

        # Ensure z is [batch, z_dim] for memory projection
        if z.dim() == 3 and z.size(1) == 1:
            z = z.squeeze(1)

        memory = self.z_proj(z).unsqueeze(1)
        x = self.transformer(tgt, memory, tgt_mask=causal_mask)

        logits = self.to_logits(x)
        return logits


class FlumeEncoder(PreTrainedModel):
    """
    Full autoencoder for thought vector compression.
    """

    config_class = FlumeConfig
    base_model_prefix = "flume"

    def __init__(self, config: FlumeConfig):
        super().__init__(config)
        self.encoder = ThoughtEncoder(config)
        self.decoder = ThoughtDecoder(config)

        # Integration with FlumeTokenizer (for convenience)
        from cohezion.flume.tokenizer import FlumeTokenizer

        self.tokenizer = FlumeTokenizer()
        self.post_init()

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(
                mean=0.0,
                std=self.config.initializer_range if hasattr(self.config, "initializer_range") else 0.02,
            )
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(
                mean=0.0,
                std=self.config.initializer_range if hasattr(self.config, "initializer_range") else 0.02,
            )
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()

    def encode(
        self,
        text: str | list[str],
        max_len: int = 256,
    ) -> torch.Tensor:
        """Encode text(s) to thought vector(s)."""
        if isinstance(text, str):
            text = [text]

        inputs = self.tokenizer(text, padding=True, truncation=True, max_length=max_len, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            z = self.encoder(inputs["input_ids"], inputs["attention_mask"])

        return z

    def decode(
        self,
        z: torch.Tensor,
        max_len: int = 256,
        temperature: float = 1.0,
    ) -> list[str]:
        """Decode thought vector(s) to text."""
        batch_size = z.shape[0]
        device = z.device

        # Start with BOS token
        bos_token_id = getattr(self.tokenizer, "bos_token_id", 1)
        if not isinstance(bos_token_id, int):
            bos_token_id = 1

        tokens = torch.full(
            (batch_size, 1),
            bos_token_id,
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
                eos_token_id = getattr(self.tokenizer, "eos_token_id", 2)
                if not isinstance(eos_token_id, int):
                    eos_token_id = 2

                if (next_token == eos_token_id).all():
                    break

        # Detokenize
        return self.tokenizer.batch_decode(tokens, skip_special_tokens=True)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        **kwargs,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Full forward pass for training."""
        z = self.encoder(input_ids, attention_mask)
        logits = self.decoder(z, input_ids)
        return z, logits

    def reconstruction_loss(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Compute reconstruction loss for training."""
        _z, logits = self.forward(input_ids, attention_mask)

        # Shift for next-token prediction
        shift_logits = logits[:, :-1, :].contiguous()
        shift_labels = input_ids[:, 1:].contiguous()

        pad_token_id = getattr(self.tokenizer, "pad_token_id", -100)
        if not isinstance(pad_token_id, int):
            pad_token_id = -100

        loss = F.cross_entropy(
            shift_logits.view(-1, self.config.vocab_size),
            shift_labels.view(-1),
            ignore_index=pad_token_id,
        )

        return loss

    def get_semantic_vector(self, text: str) -> torch.Tensor:
        """Get high-quality semantic vector using local Ollama (nomic-embed-text)."""
        try:
            import requests

            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=30,
            )
            if response.status_code == 200:
                embedding = response.json()["embedding"]
                return torch.tensor(embedding)
            else:
                logger.warning(f"Ollama error: {response.text}")
        except Exception as e:
            logger.warning(f"Ollama connection failed: {e}")

        # Fallback to internal encoder
        return self.encode(text).squeeze()

    def interpolate(
        self,
        text_a: str,
        text_b: str,
        steps: int = 5,
    ) -> list[str]:
        """Interpolate between two texts in thought-space."""
        z_a = self.encode(text_a)
        z_b = self.encode(text_b)

        results = []
        for i in range(steps):
            alpha = i / (steps - 1) if steps > 1 else 0
            z_interp = (1 - alpha) * z_a + alpha * z_b
            decoded = self.decode(z_interp)
            results.append(decoded[0])

        return results

    def semantic_add(
        self,
        base: str | torch.Tensor,
        direction: str | torch.Tensor,
        scale: float = 1.0,
    ) -> torch.Tensor:
        """Perform semantic addition: base + direction * scale."""
        if isinstance(base, str):
            base = self.encode(base)
        if isinstance(direction, str):
            direction = self.encode(direction)

        return base + direction * scale

    def semantic_direction(
        self,
        from_concept: str | torch.Tensor,
        to_concept: str | torch.Tensor,
    ) -> torch.Tensor:
        """Compute the semantic direction from one concept to another."""
        z_from = self.encode(from_concept) if isinstance(from_concept, str) else from_concept

        z_to = self.encode(to_concept) if isinstance(to_concept, str) else to_concept

        return z_to - z_from

    def cross_domain_bridge(
        self,
        concept_a: str,
        domain_a_example: str,
        domain_b_example: str,
    ) -> str:
        """Apply a cross-domain transformation."""
        domain_direction = self.semantic_direction(domain_a_example, domain_b_example)
        z_concept = self.encode(concept_a)
        z_bridged = z_concept + domain_direction
        decoded = self.decode(z_bridged)
        return decoded[0]

    def similarity(
        self,
        text_a: str | torch.Tensor,
        text_b: str | torch.Tensor,
    ) -> float:
        """Compute cosine similarity between two concepts."""
        if isinstance(text_a, str):
            text_a = self.get_semantic_vector(text_a)
        if isinstance(text_b, str):
            text_b = self.get_semantic_vector(text_b)

        # Ensure 1D tensors
        if text_a.dim() > 1:
            text_a = text_a.flatten()
        if text_b.dim() > 1:
            text_b = text_b.flatten()

        a_norm = F.normalize(text_a, dim=0)
        b_norm = F.normalize(text_b, dim=0)
        return torch.dot(a_norm, b_norm).item()

    def save(self, path: Path | str) -> None:
        """Save model weights."""
        torch.save(self.state_dict(), path)
        logger.info(f"Saved model to {path}")

    def load(self, path: Path | str) -> None:
        """Load model weights."""
        self.load_state_dict(torch.load(path, weights_only=True))
        logger.info(f"Loaded model from {path}")


# Alias for backward compatibility
FlumeAutoEncoder = FlumeEncoder
