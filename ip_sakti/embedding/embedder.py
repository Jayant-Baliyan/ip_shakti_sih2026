"""
IP-SAKTI Embedding Provider
SentenceTransformer embedding provider using all-MiniLM-L6-v2 for fast, high-quality local embeddings.
Replaces MockEmbeddingProvider for real semantic retrieval.
"""

from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding vector dimension."""
        pass


class SentenceTransformerEmbedder(EmbeddingProvider):
    """SentenceTransformers embedding provider using all-MiniLM-L6-v2."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self._dimension = dimension
        self.device = device
        self._model = None

    def _get_model(self):
        if self._model is None:
            logger.info(f"Loading SentenceTransformer model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_sync(self, texts: List[str]) -> np.ndarray:
        """Synchronously encode texts into embeddings."""
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)
        model = self._get_model()
        embeddings = model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)

    def embed_query_sync(self, query: str) -> np.ndarray:
        """Synchronously encode a single query string."""
        embeddings = self.embed_sync([query])
        return embeddings[0]

    async def embed(self, texts: List[str]) -> np.ndarray:
        """Asynchronously encode texts using an executor thread."""
        return await asyncio.to_thread(self.embed_sync, texts)

    async def embed_batch_async(self, texts: List[str]) -> np.ndarray:
        """Alias for embed for compatibility."""
        return await self.embed(texts)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Alias for embed_sync for compatibility."""
        return self.embed_sync(texts)

    async def embed_query(self, query: str) -> np.ndarray:
        """Asynchronously encode a single query."""
        return await asyncio.to_thread(self.embed_query_sync, query)


# Backwards compatibility alias for components expecting MockEmbeddingProvider
MockEmbeddingProvider = SentenceTransformerEmbedder
