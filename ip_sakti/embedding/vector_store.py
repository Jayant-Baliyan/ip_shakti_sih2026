"""
IP-SAKTI Persistent ChromaDB Vector Store
Phase 10: High-performance embedded vector storage replacing the in-memory stub.
"""

from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ip_sakti.core.models import DocumentChunk, DocumentType, JurisdictionCode

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector storage."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connections/collection."""
        pass

    @abstractmethod
    async def upsert(
        self,
        chunks: List[DocumentChunk],
        vectors: Optional[np.ndarray] = None,
    ) -> None:
        """Insert or update chunks with optional vectors."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search nearest chunks by query vector."""
        pass

    @abstractmethod
    async def delete(self, chunk_ids: List[str]) -> None:
        """Delete chunks by IDs."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics of the vector store."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections."""
        pass


class ChromaVectorStore(VectorStore):
    """Persistent ChromaDB vector store."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "ip_sakti_corpus",
    ):
        self.persist_directory = persist_directory or str(
            Path(__file__).resolve().parent.parent.parent / "data" / "chroma_db"
        )
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _ensure_initialized(self):
        if self._collection is None:
            import chromadb
            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB persistent store initialized at '{self.persist_directory}' "
                f"(collection='{self.collection_name}', items={self._collection.count()})"
            )

    async def initialize(self) -> None:
        await asyncio.to_thread(self._ensure_initialized)

    def _sanitize_metadata(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all metadata values are Chroma-supported primitive types."""
        clean = {}
        for k, v in meta.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            elif hasattr(v, "value"):
                clean[k] = str(v.value)
            else:
                clean[k] = str(v)
        return clean

    def _upsert_sync(
        self,
        chunks: List[DocumentChunk],
        vectors: Optional[np.ndarray] = None,
    ) -> None:
        self._ensure_initialized()
        if not chunks:
            return

        batch_size = 500
        total = len(chunks)

        for i in range(0, total, batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_vectors = vectors[i : i + batch_size] if vectors is not None else None

            ids = []
            documents = []
            embeddings = []
            metadatas = []

            for idx, chunk in enumerate(batch_chunks):
                ids.append(chunk.id)
                documents.append(chunk.content or " ")

                if batch_vectors is not None:
                    embeddings.append(batch_vectors[idx].tolist())
                elif chunk.embedding is not None:
                    embeddings.append(chunk.embedding)

                # Construct and sanitize metadata
                jur = chunk.metadata.get("jurisdiction")
                if jur is None and chunk.jurisdiction is not None:
                    jur = (
                        chunk.jurisdiction.value
                        if hasattr(chunk.jurisdiction, "value")
                        else str(chunk.jurisdiction)
                    )
                jur_str = str(jur or "INDIA").upper()
                if "INDIA" in jur_str or "IN-" in jur_str:
                    jur_tag = "INDIA"
                else:
                    jur_tag = "INTL"

                meta = {
                    "jurisdiction": jur_tag,
                    "raw_jurisdiction": str(jur or "INDIA"),
                    "document_id": chunk.document_id or "",
                    "document_type": str(chunk.metadata.get("document_type", "")),
                    "source_path": str(chunk.metadata.get("source_path", "")),
                    "source_authority_tier": str(chunk.metadata.get("source_authority_tier", "tier1")),
                    "authority_score": float(chunk.authority_score or 1.0),
                    "section_title": str(chunk.metadata.get("section_title", "")),
                    "chunk_index": int(chunk.chunk_index or 0),
                    "formulation_class": str(chunk.metadata.get("formulation_class", "any")),
                }
                metadatas.append(self._sanitize_metadata(meta))

            upsert_kwargs: Dict[str, Any] = {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
            }
            if embeddings:
                upsert_kwargs["embeddings"] = embeddings

            self._collection.upsert(**upsert_kwargs)

        logger.info(f"Upserted {total} chunks into ChromaDB '{self.collection_name}'")

    async def upsert(
        self,
        chunks: List[DocumentChunk],
        vectors: Optional[np.ndarray] = None,
    ) -> None:
        await asyncio.to_thread(self._upsert_sync, chunks, vectors)

    def _build_where(self, filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not filters:
            return None

        conditions = []
        # Jurisdiction filter
        if "jurisdiction" in filters and filters["jurisdiction"]:
            jur_val = str(filters["jurisdiction"]).strip().upper()
            if jur_val in ("INDIA", "INTL"):
                conditions.append({"jurisdiction": {"$eq": jur_val}})

        # Formulation classification filter if specific
        if "formulation_class" in filters and filters["formulation_class"]:
            fclass = str(filters["formulation_class"]).strip().lower()
            if fclass and fclass not in ("any", "all", "other"):
                conditions.append({"formulation_class": {"$eq": fclass}})

        # Authority tier filter
        if "authority_tier" in filters and filters["authority_tier"]:
            conditions.append({"source_authority_tier": {"$eq": str(filters["authority_tier"])}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _search_sync(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        self._ensure_initialized()
        count = self._collection.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)
        where = self._build_where(filters)

        query_args: Dict[str, Any] = {
            "query_embeddings": [query_vector.tolist()],
            "n_results": actual_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_args["where"] = where

        try:
            results = self._collection.query(**query_args)
        except Exception as e:
            logger.warning(f"Chroma query with where={where} failed: {e}. Retrying without filter.")
            query_args.pop("where", None)
            results = self._collection.query(**query_args)

        hits: List[Tuple[DocumentChunk, float]] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return hits

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else [""] * len(ids)
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for cid, doc, meta, dist in zip(ids, documents, metadatas, distances):
            # Convert cosine distance to similarity score
            score = max(0.0, min(1.0, 1.0 - float(dist)))
            chunk = DocumentChunk(
                id=cid,
                document_id=meta.get("document_id", ""),
                content=doc,
                chunk_index=int(meta.get("chunk_index", 0)),
                metadata=meta,
                authority_score=float(meta.get("authority_score", 1.0)),
                jurisdiction=JurisdictionCode(meta.get("jurisdiction", "INDIA"))
                if meta.get("jurisdiction") in JurisdictionCode._value2member_map_
                else JurisdictionCode.INDIA,
            )
            hits.append((chunk, score))

        return hits

    async def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        return await asyncio.to_thread(self._search_sync, query_vector, top_k, filters)

    def _delete_sync(self, chunk_ids: List[str]) -> None:
        self._ensure_initialized()
        if chunk_ids:
            self._collection.delete(ids=chunk_ids)

    async def delete(self, chunk_ids: List[str]) -> None:
        await asyncio.to_thread(self._delete_sync, chunk_ids)

    def _get_stats_sync(self) -> Dict[str, Any]:
        self._ensure_initialized()
        return {
            "total_chunks": self._collection.count(),
            "store_type": "chromadb_persistent",
            "persist_directory": self.persist_directory,
            "collection_name": self.collection_name,
        }

    async def get_stats(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._get_stats_sync)

    async def close(self) -> None:
        pass
