"""
IP-SAKTI Chunking Strategy - Wrapper around LangChain's battle-tested text splitters.
Uses langchain-text-splitters for all chunking operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import uuid
import logging

from ip_sakti.config.loader import get_settings
from ip_sakti.core.models import Document, DocumentChunk, DocumentType

logger = logging.getLogger(__name__)


class ChunkingStrategyType(str, Enum):
    """Types of chunking strategies - mapped to LangChain splitters."""
    RECURSIVE = "recursive"  # LangChain's RecursiveCharacterTextSplitter
    FIXED_SIZE = "fixed_size"  # LangChain's CharacterTextSplitter
    SEMANTIC = "semantic"  # Placeholder for future semantic chunking


@dataclass
class ChunkingConfig:
    """Configuration for chunking."""
    chunk_size: int = 512
    chunk_overlap: int = 50
    strategy: ChunkingStrategyType = ChunkingStrategyType.RECURSIVE
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    # Length function can be customized (default: character count)
    length_function: Callable[[str], int] = len
    # Separators for recursive splitting (ordered by priority)
    separators: List[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])


class BaseChunker(ABC):
    """Abstract base class for chunkers."""

    def __init__(self, config: ChunkingConfig):
        self.config = config

    @abstractmethod
    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk text into DocumentChunks."""
        pass

    def _create_chunk(
        self,
        text: str,
        index: int,
        document_id: str,
        start_char: int,
        end_char: int,
        metadata: Dict[str, Any],
    ) -> DocumentChunk:
        """Create a DocumentChunk with standard fields."""
        return DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=text,
            chunk_index=index,
            start_char=start_char,
            end_char=end_char,
            metadata=metadata.copy(),
        )


class RecursiveChunker(BaseChunker):
    """
    Wrapper around LangChain's RecursiveCharacterTextSplitter.
    
    This is the most robust chunking approach:
    1. Tries to split by separators in order (paragraphs, sentences, words, characters)
    2. Recursively splits oversized chunks using the next separator
    3. Merges splits back together respecting chunk_size and chunk_overlap
    """

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        # Import lazily to avoid import issues
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=config.length_function,
            separators=config.separators,
            keep_separator=True,
        )

    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk text using LangChain's recursive splitting strategy."""
        if not text or not text.strip():
            return []

        # Use LangChain's battle-tested implementation
        splits = self._splitter.split_text(text)
        
        # Create DocumentChunk objects
        chunks = []
        document_id = metadata.get('document_id', '')
        char_offset = 0
        
        for i, chunk_text in enumerate(splits):
            if len(chunk_text) >= self.config.min_chunk_size:
                chunk = self._create_chunk(
                    text=chunk_text,
                    index=i,
                    document_id=document_id,
                    start_char=char_offset,
                    end_char=char_offset + len(chunk_text),
                    metadata=metadata,
                )
                chunks.append(chunk)
                char_offset += len(chunk_text)
        
        return chunks


class FixedSizeChunker(BaseChunker):
    """Wrapper around LangChain's CharacterTextSplitter for fixed-size chunking."""

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        from langchain_text_splitters import CharacterTextSplitter
        self._splitter = CharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=config.length_function,
            separator="",  # Character-level
        )

    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        """Chunk text using fixed-size splitting."""
        if not text or not text.strip():
            return []

        splits = self._splitter.split_text(text)
        
        chunks = []
        document_id = metadata.get('document_id', '')
        char_offset = 0
        
        for i, chunk_text in enumerate(splits):
            if len(chunk_text) >= self.config.min_chunk_size:
                chunk = self._create_chunk(
                    text=chunk_text,
                    index=i,
                    document_id=document_id,
                    start_char=char_offset,
                    end_char=char_offset + len(chunk_text),
                    metadata=metadata,
                )
                chunks.append(chunk)
                char_offset += len(chunk_text)
        
        return chunks


class SemanticChunker(BaseChunker):
    """Semantic chunking using embeddings similarity (placeholder - falls back to recursive)."""

    def __init__(self, config: ChunkingConfig):
        super().__init__(config)
        self._recursive = RecursiveChunker(config)

    async def chunk(self, text: str, metadata: Dict[str, Any]) -> List[DocumentChunk]:
        # Fall back to recursive for now
        return await self._recursive.chunk(text, metadata)


class ChunkingStrategy:
    """Main chunking strategy orchestrator."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        self.config = config or ChunkingConfig()
        self._chunker = self._create_chunker()

    def _create_chunker(self) -> BaseChunker:
        strategy_map = {
            ChunkingStrategyType.FIXED_SIZE: FixedSizeChunker,
            ChunkingStrategyType.RECURSIVE: RecursiveChunker,
            ChunkingStrategyType.SEMANTIC: SemanticChunker,
        }

        chunker_class = strategy_map.get(self.config.strategy, RecursiveChunker)
        return chunker_class(self.config)

    async def chunk_document(
        self,
        document: Document,
        text: str,
    ) -> List[DocumentChunk]:
        metadata = {
            'document_id': document.id,
            'document_type': document.metadata.document_type,
            'jurisdiction': document.metadata.jurisdiction,
            'legal_document': True,
        }

        if document.source.authority_tier:
            metadata['authority_tier'] = document.source.authority_tier.value

        return await self._chunker.chunk(text, metadata)

    async def chunk_text(
        self,
        text: str,
        document_id: str,
        document_type: DocumentType = DocumentType.PATENT,
        jurisdiction = None,
    ) -> List[DocumentChunk]:
        metadata = {
            'document_id': document_id,
            'document_type': document_type,
            'jurisdiction': jurisdiction,
            'legal_document': True,
        }
        return await self._chunker.chunk(text, metadata)


def create_chunker(
    strategy: ChunkingStrategyType = ChunkingStrategyType.RECURSIVE,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    **kwargs
) -> ChunkingStrategy:
    """Factory function to create a chunking strategy."""
    config = ChunkingConfig(
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    )
    return ChunkingStrategy(config)