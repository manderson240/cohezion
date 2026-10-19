"""Stanford Memorilla: Latent Semantic Memory for LLMs (arXiv:2610.21375).

Implements query-conditioned latent memory extraction from persistent document
embedding stores into a fixed budget of soft memory tokens (K=16 or K=8) for
frozen LLMs, with agentic loop detection and hybrid latent-retrieval fusion.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch
import torch.nn as nn


@dataclass
class DocumentRecord:
    """A single persistent document chunk embedding record."""

    doc_id: str
    text: str
    embedding: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    @property
    def sha256(self) -> str:
        """SHA-256 fingerprint of the document text."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


class MemorillaDocumentStore:
    """Persistent query-independent document embedding store.

    Encodes and stores document chunk representations once into a compact
    matrix Z_D in R^(N x h_e), enabling sub-millisecond reuse across arbitrary queries.
    """

    def __init__(self, embedding_dim: int = 256) -> None:
        self.embedding_dim = embedding_dim
        self._documents: list[DocumentRecord] = []
        self._id_to_idx: dict[str, int] = {}
        self._matrix_cache: np.ndarray | None = None

    def add_document(
        self,
        doc_id: str,
        text: str,
        embedding: np.ndarray,
        metadata: dict[str, Any] | None = None,
        timestamp: float = 0.0,
    ) -> int:
        """Adds a document chunk and its precomputed embedding to the store."""
        emb_arr = np.asarray(embedding, dtype=np.float32)
        if emb_arr.ndim != 1 or emb_arr.shape[0] != self.embedding_dim:
            raise ValueError(
                f"Expected embedding shape ({self.embedding_dim},), got {emb_arr.shape}"
            )

        if doc_id in self._id_to_idx:
            idx = self._id_to_idx[doc_id]
            self._documents[idx] = DocumentRecord(
                doc_id=doc_id,
                text=text,
                embedding=emb_arr,
                metadata=metadata or {},
                timestamp=timestamp,
            )
        else:
            idx = len(self._documents)
            self._documents.append(
                DocumentRecord(
                    doc_id=doc_id,
                    text=text,
                    embedding=emb_arr,
                    metadata=metadata or {},
                    timestamp=timestamp,
                )
            )
            self._id_to_idx[doc_id] = idx

        self._matrix_cache = None
        return idx

    def add_turn(
        self,
        turn_idx: int,
        observation: str,
        action: str,
        embedding: np.ndarray,
        reward: float = 0.0,
    ) -> int:
        """Adds an agent interaction turn to the persistent document store."""
        doc_id = f"turn_{turn_idx:04d}"
        text = f"Turn {turn_idx}: Obs: {observation} | Act: {action} | Reward: {reward}"
        return self.add_document(
            doc_id=doc_id,
            text=text,
            embedding=embedding,
            metadata={"type": "agent_turn", "turn_idx": turn_idx, "reward": reward},
        )

    def get_matrix(self) -> np.ndarray:
        """Returns the stacked document embedding matrix Z_D of shape (N, h_e)."""
        if self._matrix_cache is None:
            if not self._documents:
                return np.empty((0, self.embedding_dim), dtype=np.float32)
            self._matrix_cache = np.stack([d.embedding for d in self._documents], axis=0).astype(
                np.float32
            )
        return self._matrix_cache

    def get_documents(self) -> list[DocumentRecord]:
        """Returns a shallow copy of all stored documents."""
        return list(self._documents)

    def size(self) -> int:
        """Returns the number of stored documents."""
        return len(self._documents)

    def clear(self) -> None:
        """Clears all stored documents."""
        self._documents.clear()
        self._id_to_idx.clear()
        self._matrix_cache = None


class MemorillaMemoryModule(nn.Module):
    """Trainable latent memory module f_mem (arXiv:2610.21375).

    Reads stored document embeddings Z_D and query embedding z_q, producing
    K soft memory tokens M in R^(K x h_L) for a frozen target LLM.

    Stages:
    1. Slot initialization: Learned vectors Q_0 in R^(K x h_e).
    2. Query conditioning: Q_c = Q_0 + CrossAttention(Q_0, z_q, z_q).
    3. Document retrieval: Perceiver iterative cross-attention over Z_D.
    4. Projection: M = LayerNorm(W_proj * R_L + b_proj) in R^(K x h_L).
    """

    def __init__(
        self,
        encoder_dim: int = 256,
        llm_dim: int = 512,
        num_memory_tokens: int = 16,
        num_refinement_blocks: int = 2,
        num_heads: int = 4,
        ffn_dim: int | None = None,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.encoder_dim = encoder_dim
        self.llm_dim = llm_dim
        self.num_memory_tokens = num_memory_tokens
        self.num_refinement_blocks = num_refinement_blocks
        self.num_heads = num_heads
        actual_ffn_dim = ffn_dim or (encoder_dim * 4)

        # Stage 1: Learned slot vectors Q_0 in R^(K x h_e)
        self.q0 = nn.Parameter(torch.randn(num_memory_tokens, encoder_dim) / math.sqrt(encoder_dim))

        # Stage 2: Query conditioning cross-attention
        self.query_norm_q = nn.LayerNorm(encoder_dim)
        self.query_norm_kv = nn.LayerNorm(encoder_dim)
        self.query_attn = nn.MultiheadAttention(
            embed_dim=encoder_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True,
        )

        # Stage 3: Perceiver iterative cross-attention refinement blocks
        self.doc_norm = nn.LayerNorm(encoder_dim)
        self.ref_blocks = nn.ModuleList()
        for _ in range(num_refinement_blocks):
            block = nn.ModuleDict(
                {
                    "norm_q": nn.LayerNorm(encoder_dim),
                    "attn": nn.MultiheadAttention(
                        embed_dim=encoder_dim,
                        num_heads=num_heads,
                        dropout=dropout,
                        batch_first=True,
                    ),
                    "norm_ffn": nn.LayerNorm(encoder_dim),
                    "ffn": nn.Sequential(
                        nn.Linear(encoder_dim, actual_ffn_dim),
                        nn.GELU(),
                        nn.Dropout(dropout),
                        nn.Linear(actual_ffn_dim, encoder_dim),
                    ),
                }
            )
            self.ref_blocks.append(block)

        # Stage 4: Projection to LLM input embedding space
        self.proj_norm = nn.LayerNorm(encoder_dim)
        self.proj = nn.Linear(encoder_dim, llm_dim)
        self.output_norm = nn.LayerNorm(llm_dim)

    def forward(
        self,
        z_query: torch.Tensor,
        z_docs: torch.Tensor,
    ) -> torch.Tensor:
        """Computes K query-conditioned soft memory tokens.

        Parameters
        ----------
        z_query : torch.Tensor
            Query embedding of shape (B, 1, h_e) or (B, h_e).
        z_docs : torch.Tensor
            Document embeddings matrix of shape (B, N, h_e) or (N, h_e).

        Returns
        -------
        torch.Tensor
            Soft memory tokens of shape (B, K, h_L) for input embedding injection.
        """
        # Reshape query to (B, 1, h_e)
        if z_query.ndim == 2:
            z_query = z_query.unsqueeze(1)
        batch_size = z_query.size(0)

        # Reshape docs to (B, N, h_e)
        if z_docs.ndim == 2:
            z_docs = z_docs.unsqueeze(0).expand(batch_size, -1, -1)

        # Stage 1: Expand Q_0 to batch (B, K, h_e)
        q = self.q0.unsqueeze(0).expand(batch_size, -1, -1)

        # Stage 2: Query conditioning
        q_norm = self.query_norm_q(q)
        kv_norm = self.query_norm_kv(z_query)
        q_delta, _ = self.query_attn(q_norm, kv_norm, kv_norm)
        q_c = q + q_delta  # Residual preserves slot identities

        # Stage 3: Iterative Perceiver cross-attention over document matrix Z_D
        if z_docs.size(1) == 0:
            # Empty collection fallback: rely on query-conditioned slots
            r = q_c
        else:
            z_docs_norm = self.doc_norm(z_docs)
            r = q_c
            for block in self.ref_blocks:
                r_norm = block["norm_q"](r)
                attn_out, _ = block["attn"](r_norm, z_docs_norm, z_docs_norm)
                r = r + attn_out
                ffn_norm = block["norm_ffn"](r)
                r = r + block["ffn"](ffn_norm)

        # Stage 4: Projection to LLM input embedding space
        r_proj = self.proj(self.proj_norm(r))
        m = self.output_norm(r_proj)
        return m


class AgenticLoopDetector:
    """Detects cyclic navigation and entrapment in agent trajectories (Section 6).

    Memorilla prevents agents from wandering endlessly in explored rooms or
    repeating fruitless action sequences by tracking state revisit entropy and
    signaling when to inject loop-breaking memory vectors.
    """

    def __init__(self, loop_threshold: int = 3, similarity_threshold: float = 0.92) -> None:
        self.loop_threshold = loop_threshold
        self.similarity_threshold = similarity_threshold
        self.state_history: list[np.ndarray] = []
        self.action_history: list[str] = []

    def record_step(self, state_embedding: np.ndarray, action: str) -> bool:
        """Records a step and evaluates whether the agent has entered a cyclic loop."""
        emb = np.asarray(state_embedding, dtype=np.float32)
        emb_norm = emb / (np.linalg.norm(emb) + 1e-9)

        # Calculate cosine similarity against prior states
        revisit_count = 0
        for prior_emb in self.state_history[-15:]:  # Check sliding window of 15 turns
            prior_norm = prior_emb / (np.linalg.norm(prior_emb) + 1e-9)
            sim = float(np.dot(emb_norm, prior_norm))
            if sim >= self.similarity_threshold:
                revisit_count += 1

        self.state_history.append(emb)
        self.action_history.append(action)

        # Total visits to similar states in the sliding window
        total_visits = 1 + revisit_count
        is_loop = total_visits >= self.loop_threshold
        return is_loop

    def get_loop_penalty_bias(self) -> float:
        """Returns an exploration boost penalty based on loop severity."""
        if len(self.state_history) < 2:
            return 0.0
        # Compute recent repetition rate
        recent_actions = self.action_history[-6:]
        unique_ratio = len(set(recent_actions)) / max(1, len(recent_actions))
        return float(1.0 - unique_ratio)

    def reset(self) -> None:
        """Resets the detector state."""
        self.state_history.clear()
        self.action_history.clear()


class HybridMemorillaRAG:
    """Hybrid Latent-Retrieval Router (Section 5).

    Synthesizes the complementary strengths of Memorilla (global relational
    reasoning, multi-hop facts, implicit personalization) and RAG (verbatim
    exact surface tokens and entity names).
    """

    def __init__(
        self,
        document_store: MemorillaDocumentStore,
        memory_module: MemorillaMemoryModule,
        top_k_text_chunks: int = 2,
    ) -> None:
        self.document_store = document_store
        self.memory_module = memory_module
        self.top_k_text_chunks = top_k_text_chunks

    def retrieve_text_chunks(self, query_embedding: np.ndarray) -> list[DocumentRecord]:
        """Performs cosine retrieval over stored documents for exact surface tokens."""
        q_emb = np.asarray(query_embedding, dtype=np.float32)
        q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)

        docs = self.document_store.get_documents()
        if not docs:
            return []

        z_d = self.document_store.get_matrix()
        norms = np.linalg.norm(z_d, axis=1, keepdims=True) + 1e-9
        z_d_norm = z_d / norms
        sims = np.dot(z_d_norm, q_norm)

        top_indices = np.argsort(sims)[::-1][: self.top_k_text_chunks]
        return [docs[idx] for idx in top_indices]

    def build_hybrid_context(
        self,
        query_text: str,
        query_embedding: np.ndarray,
        device: str = "cpu",
    ) -> dict[str, Any]:
        """Constructs hybrid memory payload: K soft memory tokens + top-k verbatim chunks.

        Parameters
        ----------
        query_text : str
            The input query or prompt string.
        query_embedding : np.ndarray
            Embedding vector for the query.
        device : str
            PyTorch compute device.

        Returns
        -------
        dict[str, Any]
            Dictionary containing:
            - "memory_tokens": torch.Tensor of shape (1, K, h_L)
            - "retrieved_passages": list of top-k text strings
            - "compression_ratio": token reduction ratio vs full-text
            - "query_text": original prompt
        """
        # 1. Compute Memorilla latent memory tokens
        q_t = torch.from_numpy(query_embedding).float().unsqueeze(0).to(device)
        z_d = self.document_store.get_matrix()
        z_d_t = torch.from_numpy(z_d).float().to(device)

        with torch.no_grad():
            memory_tokens = self.memory_module(q_t, z_d_t)

        # 2. Retrieve top-k verbatim text chunks
        top_chunks = self.retrieve_text_chunks(query_embedding)
        retrieved_texts = [c.text for c in top_chunks]

        # 3. Compute compression ratio
        total_chars = sum(len(d.text) for d in self.document_store.get_documents())
        estimated_doc_tokens = max(1, total_chars // 4)
        k_tokens = self.memory_module.num_memory_tokens
        compression_ratio = float(estimated_doc_tokens / max(1, k_tokens))

        return {
            "memory_tokens": memory_tokens,
            "retrieved_passages": retrieved_texts,
            "compression_ratio": compression_ratio,
            "query_text": query_text,
            "num_stored_docs": self.document_store.size(),
        }


class MemorillaEngine:
    """Master Orchestrator for Stanford Memorilla Latent Memory Architecture.

    Coordinates document storage, query conditioning, soft memory injection,
    agent loop prevention, and hybrid retrieval.
    """

    def __init__(
        self,
        encoder_dim: int = 256,
        llm_dim: int = 512,
        num_memory_tokens: int = 16,
        num_refinement_blocks: int = 2,
    ) -> None:
        self.store = MemorillaDocumentStore(embedding_dim=encoder_dim)
        self.module = MemorillaMemoryModule(
            encoder_dim=encoder_dim,
            llm_dim=llm_dim,
            num_memory_tokens=num_memory_tokens,
            num_refinement_blocks=num_refinement_blocks,
        )
        self.loop_detector = AgenticLoopDetector()
        self.hybrid = HybridMemorillaRAG(
            document_store=self.store,
            memory_module=self.module,
            top_k_text_chunks=2,
        )

    def extract_memory_tokens(
        self,
        query_embedding: np.ndarray,
        device: str = "cpu",
    ) -> np.ndarray:
        """Returns K soft memory tokens as a NumPy array of shape (K, h_L)."""
        q_t = torch.from_numpy(query_embedding).float().unsqueeze(0).to(device)
        z_d = self.store.get_matrix()
        z_d_t = torch.from_numpy(z_d).float().to(device)

        self.module.eval()
        with torch.no_grad():
            m_t = self.module(q_t, z_d_t)
        return m_t.squeeze(0).cpu().numpy()

    def process_agent_turn(
        self,
        turn_idx: int,
        observation: str,
        action: str,
        obs_embedding: np.ndarray,
        reward: float = 0.0,
    ) -> dict[str, Any]:
        """Ingests an agent interaction step, updates store, and checks for cyclic loops."""
        # 1. Check for cyclic loop
        is_loop = self.loop_detector.record_step(obs_embedding, action)
        loop_penalty = self.loop_detector.get_loop_penalty_bias()

        # 2. Add turn to persistent memory store
        doc_idx = self.store.add_turn(
            turn_idx=turn_idx,
            observation=observation,
            action=action,
            embedding=obs_embedding,
            reward=reward,
        )

        # 3. Extract updated soft memory tokens
        memory_tokens = self.extract_memory_tokens(obs_embedding)

        return {
            "turn_idx": turn_idx,
            "doc_idx": doc_idx,
            "is_loop": is_loop,
            "loop_penalty": loop_penalty,
            "num_memory_tokens": self.module.num_memory_tokens,
            "memory_tokens": memory_tokens,
        }
